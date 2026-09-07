"""
Downloads official Star Wars: Unlimited (SWU) card scans into local cache: public/images/swu/
Uses a ThreadPoolExecutor with exponential backoff, rate limiting, and skips existing files.
Updates MongoDB 'avascry_swu.cards' documents with 'local_image_front' and 'local_image_back'.
"""

import os
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo import MongoClient

SWU_DIR = os.path.join("public", "images", "swu")
os.makedirs(SWU_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://starwarsunlimited.com/"
}

def download_file(url: str, local_path: str, retries: int = 3) -> bool:
    if not url or not url.startswith("http"):
        return False
    if os.path.isfile(local_path) and os.path.getsize(local_path) > 1024:
        return True

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if len(data) > 500:
                        tmp_path = local_path + ".tmp"
                        with open(tmp_path, "wb") as f:
                            f.write(data)
                        os.replace(tmp_path, local_path)
                        return True
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return False
            time.sleep(1.0 * (attempt + 1))
        except Exception:
            time.sleep(1.0 * (attempt + 1))
    return False

def process_card(card: dict, db):
    slug = card.get("slug")
    if not slug:
        return 0

    updates = {}
    downloaded = 0

    # Front art
    front_url = card.get("art_front") or card.get("front_image")
    if front_url and front_url.startswith("http"):
        front_filename = f"{slug}_front.png"
        front_path = os.path.join(SWU_DIR, front_filename)
        if download_file(front_url, front_path):
            updates["local_image_front"] = f"/images/swu/{front_filename}"
            downloaded += 1

    # Back art (dual-sided leaders / tokens)
    back_url = card.get("art_back") or card.get("back_image")
    if back_url and back_url.startswith("http"):
        back_filename = f"{slug}_back.png"
        back_path = os.path.join(SWU_DIR, back_filename)
        if download_file(back_url, back_path):
            updates["local_image_back"] = f"/images/swu/{back_filename}"
            downloaded += 1

    if updates:
        db.cards.update_one({"_id": card["_id"]}, {"$set": updates})

    return downloaded

def run_download(batch_size: int = None, workers: int = 8):
    client = MongoClient("mongodb://localhost:27017")
    db = client["avascry_swu"]

    query = {
        "$or": [
            {"local_image_front": {"$exists": False}},
            {"art_back": {"$exists": True, "$ne": "", "$ne": None}, "local_image_back": {"$exists": False}}
        ]
    }
    
    total_needed = db.cards.count_documents(query)
    print(f"Cards needing image download: {total_needed}")

    cursor = db.cards.find(query)
    if batch_size:
        cursor = cursor.limit(batch_size)

    cards = list(cursor)
    print(f"Starting download of {len(cards)} cards using {workers} worker threads...")

    completed = 0
    total_imgs = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_card, card, db): card for card in cards}
        for future in as_completed(futures):
            try:
                cnt = future.result()
                total_imgs += cnt
            except Exception as e:
                pass
            completed += 1
            if completed % 50 == 0 or completed == len(cards):
                elapsed = time.time() - t0
                rate = completed / max(0.1, elapsed)
                print(f"[{completed}/{len(cards)}] ({completed/len(cards)*100:.1f}%) - {total_imgs} images saved ({rate:.1f} cards/sec)")

    print(f"Done! Downloaded {total_imgs} images in {time.time()-t0:.1f}s.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=None, help="Batch limit (default all)")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent workers")
    args = parser.parse_args()
    run_download(batch_size=args.batch, workers=args.workers)
