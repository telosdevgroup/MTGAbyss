"""
Enrich avascry_dominion with 1st Edition (Old) card scans.
Downloads {slug}-1e.jpg locally into public/images/dominion/
and updates MongoDB card_versions to distinguish 1e vs 2e artwork.
"""

import os
import re
import json
import asyncio
import httpx
import urllib.parse
from pymongo import MongoClient

DOMINION_IMAGE_DIR = os.path.join("public", "images", "dominion")
os.makedirs(DOMINION_IMAGE_DIR, exist_ok=True)

def slugify(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

async def fetch_all_old_images(client: httpx.AsyncClient):
    print("Querying Fandom MediaWiki for all *Old.jpg card images...")
    base_url = "https://dominioncg.fandom.com/api.php"
    params = {
        "action": "query",
        "list": "allimages",
        "aiprefix": "",
        "ailimit": "500",
        "format": "json"
    }
    
    all_images = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    while True:
        resp = await client.get(base_url, params=params, headers=headers, timeout=15.0)
        data = resp.json()
        imgs = data.get("query", {}).get("allimages", [])
        all_images.extend(imgs)

        if "continue" in data:
            params.update(data["continue"])
        else:
            break

    old_images = [img for img in all_images if "old" in img.get("name", "").lower() and img.get("name", "").endswith(".jpg")]
    print(f"Found {len(old_images)} 1st Edition (*Old.jpg) card scans on Fandom.")
    return old_images

async def download_old_image(client: httpx.AsyncClient, sem: asyncio.Semaphore, name: str, url: str, slug: str):
    dest = os.path.join(DOMINION_IMAGE_DIR, f"{slug}-1e.jpg")
    if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
        return slug, dest, url

    async with sem:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = await client.get(url, headers=headers, follow_redirects=True, timeout=12.0)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(dest, "wb") as f:
                    f.write(resp.content)
                return slug, dest, url
        except Exception:
            pass
    return None

async def main():
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo["avascry_dominion"]

    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20)) as client:
        old_images = await fetch_all_old_images(client)

        tasks = []
        for img in old_images:
            raw_name = img.get("name", "")
            # Extract card base name: e.g. "MilitiaOld.jpg" -> "Militia"
            base_card = re.sub(r'Old\d*\.jpg$', '', raw_name, flags=re.IGNORECASE)
            base_card = base_card.replace("_", " ").strip()
            slug = slugify(base_card)
            tasks.append(download_old_image(client, sem, raw_name, img.get("url"), slug))

        results = await asyncio.gather(*tasks)

    updated = 0
    for r in results:
        if r:
            slug, local_path, url = r
            # Update 1e card_versions with 1e image
            res = db.card_versions.update_many(
                {"card_id": f"card:{slug}", "edition": "1e"},
                {"$set": {"image_url": f"/dominion/images/{slug}-1e.jpg", "cdn_url": url}}
            )
            # Also record 1e image on parent card document
            db.cards.update_one(
                {"slug": slug},
                {"$set": {"image_1e_url": f"/dominion/images/{slug}-1e.jpg"}}
            )
            if res.matched_count > 0:
                updated += 1

    print(f"Enriched and downloaded {len([r for r in results if r])} 1st Edition images!")
    print(f"Updated {updated} 1st Edition versions in MongoDB.")

if __name__ == "__main__":
    asyncio.run(main())
