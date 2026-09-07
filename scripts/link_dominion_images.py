"""
Link Dominion cards to image URLs from tempfillernamegithq/dominion-cards.
Updates 'avascry_dominion' MongoDB with direct CDN image URLs.
"""

import json
import urllib.request
from pymongo import MongoClient

def main():
    print("Fetching image tree from GitHub...")
    url = "https://api.github.com/repos/tempfillernamegithq/dominion-cards/git/trees/master?recursive=1"
    req = urllib.request.Request(url, headers={"User-Agent": "AvaScry-Image-Linker/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode('utf-8'))
    tree = data.get("tree", [])

    images = [item["path"] for item in tree if item["path"].endswith(".jpg")]
    print(f"Found {len(images)} card images.")

    client = MongoClient("mongodb://localhost:27017")
    db = client["avascry_dominion"]

    matched = 0
    for p in images:
        filename = p.split("/")[-1]
        slug = filename[:-4]
        cdn_url = f"https://raw.githubusercontent.com/tempfillernamegithq/dominion-cards/master/{p}"
        update_op = {"$set": {"image_url": cdn_url, "image_path": p}}
        res = db.cards.update_one({"slug": slug}, update_op)
        if res.matched_count > 0:
            matched += 1

    print(f"Successfully linked {matched} Dominion cards with CDN image URLs.")

if __name__ == "__main__":
    main()
