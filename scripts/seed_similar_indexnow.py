#!/usr/bin/env python3
"""
Seed script to submit 1,237 long-tail commander /similar/ URLs to IndexNow / Bing.
Targets least-printed, high-obscurity legendary creatures for maximum search & citation capture.
"""
import os
import re
import unicodedata
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from dotenv import load_dotenv
from db_mongo import get_mongo_db

load_dotenv()

INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b3901b0f58d0445bb8d15a9e334df58a")
HOST = "avascry.com"
KEY_LOCATION = f"https://{HOST}/{INDEXNOW_KEY}.txt"
TARGET_PRIME = 1237

def slugify(text: str) -> str:
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text

def main():
    db = get_mongo_db()

    print(f"Selecting the deepest long-tail commanders (Target prime count: {TARGET_PRIME})...")
    pat = re.compile(r'Legendary.*Creature', re.IGNORECASE)
    cursor = db['cards'].find(
        {'type_line': pat, 'lang': 'en'},
        {'name': 1, 'oracle_id': 1, 'set': 1, 'released_at': 1}
    )

    counts = {}
    sample = {}
    for c in cursor:
        oid = c.get('oracle_id')
        if not oid:
            continue
        counts[oid] = counts.get(oid, 0) + 1
        if oid not in sample or (c.get('released_at') and not sample[oid].get('released_at')):
            sample[oid] = c

    # Sort least-printed first, breaking ties by earliest release date (vintage obscurity)
    sorted_commanders = sorted(
        counts.items(),
        key=lambda x: (x[1], sample[x[0]].get('released_at') or '9999')
    )

    selected_cohort = sorted_commanders[:TARGET_PRIME]
    print(f"Extracted exactly {len(selected_cohort)} long-tail commanders.")
    
    urls = []
    for oid, cnt in selected_cohort:
        c = sample[oid]
        name = c.get('name', '')
        if not name:
            continue
        slug = slugify(name)
        urls.append(f"https://{HOST}/similar/{slug}")
        urls.append(f"https://{HOST}/similar/{slug}.md")

    urls = sorted(list(set(urls)))
    print(f"\n==========================================")
    print(f"Total /similar/ URLs to Submit: {len(urls)} ({len(selected_cohort)} commanders x 2 formats)")
    print(f"IndexNow Key: {INDEXNOW_KEY}")
    print(f"Key Location: {KEY_LOCATION}")
    print(f"Sample First 5: {[sample[oid].get('name') for oid, _ in selected_cohort[:5]]}")
    print(f"Sample Last 5:  {[sample[oid].get('name') for oid, _ in selected_cohort[-5:]]}")
    print(f"==========================================\n")

    # Batch submit in chunks of 5,000 (IndexNow max is 10,000 per request)
    batch_size = 5000
    for i in range(0, len(urls), batch_size):
        chunk = urls[i:i + batch_size]
        payload = {
            "host": HOST,
            "key": INDEXNOW_KEY,
            "keyLocation": KEY_LOCATION,
            "urlList": chunk
        }

        print(f"Submitting Batch {i//batch_size + 1} ({len(chunk)} URLs) to api.indexnow.org...")
        try:
            r1 = requests.post("https://api.indexnow.org/indexnow", json=payload, timeout=20)
            print(f"  -> api.indexnow.org: HTTP {r1.status_code} ({r1.text or 'Accepted'})")
        except Exception as e:
            print(f"  -> Error pinging api.indexnow.org: {e}")

        print(f"Submitting Batch {i//batch_size + 1} to www.bing.com/indexnow...")
        try:
            r2 = requests.post("https://www.bing.com/indexnow", json=payload, timeout=20)
            print(f"  -> www.bing.com/indexnow: HTTP {r2.status_code} ({r2.text or 'Accepted'})")
        except Exception as e:
            print(f"  -> Error pinging bing.com: {e}")

    print("\n[OK] Long-tail commander /similar/ sync with IndexNow completed!")

if __name__ == "__main__":
    main()
