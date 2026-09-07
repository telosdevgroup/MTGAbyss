"""
Download all Dominion card images locally into public/images/dominion/{slug}.jpg.
Once downloaded, AvaScry serves images 100% locally from disk with immutable caching,
eliminating any external CDN dependencies or anti-hotlinking issues.
"""

import os
import asyncio
import httpx
from pymongo import MongoClient

DOMINION_IMAGE_DIR = os.path.join("public", "images", "dominion")
os.makedirs(DOMINION_IMAGE_DIR, exist_ok=True)

async def download_image(client: httpx.AsyncClient, sem: asyncio.Semaphore, card: dict):
    slug = card.get("slug")
    url = card.get("image_url")
    if not slug or not url:
        return False

    dest = os.path.join(DOMINION_IMAGE_DIR, f"{slug}.jpg")
    if os.path.isfile(dest) and os.path.getsize(dest) > 1000:
        return True

    async with sem:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            }
            resp = await client.get(url, headers=headers, follow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(dest, "wb") as f:
                    f.write(resp.content)
                return True
        except Exception as e:
            pass
    return False

async def main():
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo["avascry_dominion"]
    cards = list(db.cards.find({"image_url": {"$exists": True, "$ne": None}}))
    print(f"Starting bulk download for {len(cards)} Dominion card images into {DOMINION_IMAGE_DIR}...")

    sem = asyncio.Semaphore(10) # 10 concurrent polite downloads
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
    timeout = httpx.Timeout(15.0, connect=8.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        tasks = [download_image(client, sem, c) for c in cards]
        results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r)
    print(f"\nDone! Downloaded/Verified {success_count} / {len(cards)} card images locally.")

if __name__ == "__main__":
    asyncio.run(main())
