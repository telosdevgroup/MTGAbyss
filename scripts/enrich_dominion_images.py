"""
Enrich avascry_dominion cards with official images from Dominion Fandom Wiki.
Covers expansions not present in legacy repos (Prosperity 2E like Anvil, Allies, Plunder, etc.).
"""

import json
import time
import urllib.request
import urllib.parse
from pymongo import MongoClient

def main():
    client = MongoClient("mongodb://localhost:27017")
    db = client["avascry_dominion"]

    cards = list(db.cards.find({}, {"name": 1, "slug": 1, "image_url": 1}))
    missing = [c for c in cards if not c.get("image_url")]
    print(f"Total cards: {len(cards)}, Cards without image: {len(missing)}")

    batch_size = 30
    added = 0
    for i in range(0, len(missing), batch_size):
        chunk = missing[i:i + batch_size]
        titles = "|".join(c["name"] for c in chunk)
        encoded_titles = urllib.parse.quote(titles)
        url = f"https://dominioncg.fandom.com/api.php?action=query&titles={encoded_titles}&prop=pageimages&pithumbsize=500&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                title = pdata.get("title")
                thumb = pdata.get("thumbnail", {}).get("source")
                if thumb and title:
                    res = db.cards.update_one({"name": title}, {"$set": {"image_url": thumb}})
                    if res.matched_count > 0:
                        added += 1
                        print(f"  + Added image for {title}")
        except Exception as e:
            print(f"Error on chunk {i}: {e}")
        time.sleep(0.2)

    total_with_img = len([c for c in db.cards.find({}, {"image_url": 1}) if c.get("image_url")])
    print(f"Enrichment complete! Added {added} new card images.")
    print(f"Total cards with images now: {total_with_img} / {len(cards)}")

if __name__ == "__main__":
    main()
