#!/usr/bin/env python3
"""
Seed script to submit AvaScry's core URLs, public decks, and top card pages to IndexNow / Bing.
"""
import os
import re
import unicodedata
import requests
import pymongo
from dotenv import load_dotenv

load_dotenv()

INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b3901b0f58d0445bb8d15a9e334df58a")
HOST = "avascry.com"
KEY_LOCATION = f"https://{HOST}/{INDEXNOW_KEY}.txt"

def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text

def main():
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    client = pymongo.MongoClient(mongo_uri)
    db = client["mtgabyss_next"]

    urls = set()

    # 1. Core static pages
    core_pages = [
        f"https://{HOST}/",
        f"https://{HOST}/commander",
        f"https://{HOST}/dashboard",
        f"https://{HOST}/auth/login"
    ]
    urls.update(core_pages)

    # 2. Public Decks
    decks = list(db["decks"].find({"is_public": {"$ne": False}}, {"deck_id": 1}))
    print(f"Found {len(decks)} public decks...")
    for d in decks:
        if d.get("deck_id"):
            urls.add(f"https://{HOST}/deck/{d['deck_id']}")

    # 3. Top Distinct Oracle Cards sorted by EDHREC popularity rank
    print("Querying top 3,500 popular Oracle cards from MongoDB...")
    pipeline = [
        {"$match": {"lang": "en"}},
        {"$sort": {"edhrec_rank": 1}},
        {
            "$group": {
                "_id": "$oracle_id",
                "name": {"$first": "$name"},
                "set": {"$first": "$set"}
            }
        },
        {"$limit": 3500}
    ]
    cards = list(db["cards"].aggregate(pipeline))
    print(f"Extracted {len(cards)} distinct cards.")

    for c in cards:
        name = c.get("name", "")
        c_set = (c.get("set") or "").lower()
        if not name:
            continue
        base_slug = slugify(name)
        # Add clean canonical name route and specific printing route
        urls.add(f"https://{HOST}/card/{base_slug}")
        if c_set:
            urls.add(f"https://{HOST}/card/{base_slug}-{c_set}")

    url_list = sorted(list(urls))
    print(f"\n==========================================")
    print(f"Total Unique URLs to Submit: {len(url_list)}")
    print(f"IndexNow Key: {INDEXNOW_KEY}")
    print(f"Key Location: {KEY_LOCATION}")
    print(f"==========================================\n")

    # Batch submit (IndexNow supports up to 10,000 URLs per POST)
    batch_size = 5000
    for i in range(0, len(url_list), batch_size):
        chunk = url_list[i:i + batch_size]
        payload = {
            "host": HOST,
            "key": INDEXNOW_KEY,
            "keyLocation": KEY_LOCATION,
            "urlList": chunk
        }
        
        print(f"Submitting Batch {i//batch_size + 1} ({len(chunk)} URLs) to api.indexnow.org...")
        try:
            r1 = requests.post("https://api.indexnow.org/indexnow", json=payload, timeout=15)
            print(f"  -> api.indexnow.org Response: HTTP {r1.status_code} ({r1.text or 'OK/Accepted'})")
        except Exception as e:
            print(f"  -> Error pinging api.indexnow.org: {e}")

        print(f"Submitting Batch {i//batch_size + 1} to www.bing.com/indexnow...")
        try:
            r2 = requests.post("https://www.bing.com/indexnow", json=payload, timeout=15)
            print(f"  -> www.bing.com/indexnow Response: HTTP {r2.status_code} ({r2.text or 'OK/Accepted'})")
        except Exception as e:
            print(f"  -> Error pinging bing.com: {e}")

    print("\n[OK] IndexNow URL submission process completed!")

if __name__ == "__main__":
    main()
