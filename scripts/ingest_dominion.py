"""
Standalone ingestion script for Dominion data into MongoDB 'avascry_dominion'.
Fetches data from canonical sumpfork/dominiontabs repository:
- cards_db.json (metadata, types, costs, sets)
- en_us/cards_en_us.json (rules text, descriptions, extra interaction rules, notes)
- sets_db.json and en_us/sets_en_us.json (expansions)
"""

import os
import re
import json
import urllib.request
import argparse
from typing import Dict, Any, List
from pymongo import MongoClient, ASCENDING

BASE_RAW_URL = "https://raw.githubusercontent.com/sumpfork/dominiontabs/master/card_db_src"

def slugify(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def fetch_json(endpoint: str) -> Any:
    url = f"{BASE_RAW_URL}/{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "AvaScry-Dominion-Ingester/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))

def parse_cost(cost_str: str) -> Dict[str, Any]:
    if not cost_str:
        return {"coins": 0, "potion": False, "debt": 0}
    
    coins = 0
    potion = "P" in cost_str
    debt = 0

    m_debt = re.search(r'(\d+)D', cost_str)
    if m_debt:
        debt = int(m_debt.group(1))

    # Coins is usually the first digit or digit not followed by D
    m_coin = re.search(r'^(\d+)', cost_str)
    if m_coin:
        coins = int(m_coin.group(1))

    return {"coins": coins, "potion": potion, "debt": debt, "raw": cost_str}

def main():
    parser = argparse.ArgumentParser(description="Ingest Dominion card data into MongoDB")
    parser.add_argument("--dry-run", action="store_true", help="Print sample card without inserting into DB")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017"), help="MongoDB URI")
    args = parser.parse_args()

    print("Fetching Dominion data from repository...")
    cards_db = fetch_json("cards_db.json")
    cards_text = fetch_json("en_us/cards_en_us.json")
    sets_db = fetch_json("sets_db.json")
    sets_text = fetch_json("en_us/sets_en_us.json")

    print(f"Loaded {len(cards_db)} card entries, {len(cards_text)} text entries, {len(sets_db)} sets.")

    # Build expansion records
    expansions = []
    for set_tag, sdata in sets_db.items():
        stext = sets_text.get(set_tag, {})
        name = stext.get("set_name", set_tag)
        expansions.append({
            "_id": f"expansion:{slugify(set_tag)}",
            "set_tag": set_tag,
            "name": name,
            "slug": slugify(name),
            "short_name": stext.get("short_name", name),
            "raw": sdata
        })

    # Build cards and card_versions
    cards: Dict[str, Dict[str, Any]] = {}
    card_versions: List[Dict[str, Any]] = []
    rulings: List[Dict[str, Any]] = []

    for item in cards_db:
        card_tag = item.get("card_tag")
        if not card_tag:
            continue

        c_slug = slugify(card_tag)
        card_id = f"card:{c_slug}"

        text_info = cards_text.get(card_tag, {})
        name = text_info.get("name", card_tag)
        description = text_info.get("description", "")
        extra_rules = text_info.get("extra", "")
        notes = text_info.get("notes", [])

        cost_info = parse_cost(str(item.get("cost", "")))
        types = item.get("types", [])
        is_kingdom = "Action" in types or "Treasure" in types or "Victory" in types

        # Canonical Card record
        if card_id not in cards:
            cards[card_id] = {
                "_id": card_id,
                "slug": c_slug,
                "name": name,
                "normalized_name": name.lower(),
                "card_kinds": [t.lower() for t in types],
                "is_kingdom_card": is_kingdom,
                "status": "active"
            }

        # Each set tag is a version/printing
        set_tags = item.get("cardset_tags", ["base"])
        for stag in set_tags:
            edition = "1e" if "1stEdition" in stag else ("2e" if "2ndEdition" in stag else "standard")
            version_id = f"card-version:{c_slug}:{slugify(stag)}"

            card_versions.append({
                "_id": version_id,
                "card_id": card_id,
                "name": name,
                "expansion_id": f"expansion:{slugify(stag)}",
                "expansion_tag": stag,
                "edition": edition,
                "cost": cost_info,
                "types": types,
                "printed_rules_text": description,
                "notes": notes,
                "status": "current"
            })

        # Official interaction / FAQ ruling if available in 'extra'
        if extra_rules:
            rulings.append({
                "_id": f"ruling:{c_slug}:official-rules",
                "card_id": card_id,
                "question": f"Official rules & interaction notes for {name}",
                "answer": extra_rules.replace("<n>", "\n\n"),
                "authority": {
                    "name": "Rio Grande Games / Donald X. Vaccarino",
                    "authority_type": "official"
                },
                "status": "confirmed",
                "indexable": True
            })

    if args.dry_run:
        print("\n--- DRY RUN SAMPLE ---")
        sample_card_id = list(cards.keys())[0]
        print("Card:", json.dumps(cards[sample_card_id], indent=2))
        sample_versions = [v for v in card_versions if v["card_id"] == sample_card_id]
        print("Version:", json.dumps(sample_versions[0], indent=2))
        sample_ruling = [r for r in rulings if r["card_id"] == sample_card_id]
        if sample_ruling:
            print("Ruling:", json.dumps(sample_ruling[0], indent=2))
        print(f"\nTotals: {len(cards)} canonical cards, {len(card_versions)} versions, {len(expansions)} expansions, {len(rulings)} rulings.")
        return

    print("\nConnecting to MongoDB database: avascry_dominion ...")
    client = MongoClient(args.mongo_uri)
    db = client["avascry_dominion"]

    # Indexes
    db.cards.create_index([("slug", ASCENDING)], unique=True)
    db.cards.create_index([("normalized_name", ASCENDING)])
    db.card_versions.create_index([("card_id", ASCENDING), ("expansion_tag", ASCENDING)], unique=True)
    db.card_versions.create_index([("expansion_id", ASCENDING)])
    db.expansions.create_index([("slug", ASCENDING)], unique=True)
    db.rulings.create_index([("card_id", ASCENDING)])

    # Upsert data cleanly
    print("Writing expansions...")
    for exp in expansions:
        db.expansions.update_one({"_id": exp["_id"]}, {"$set": exp}, upsert=True)

    print("Writing cards...")
    for card in cards.values():
        db.cards.update_one({"_id": card["_id"]}, {"$set": card}, upsert=True)

    print("Writing card versions...")
    for ver in card_versions:
        db.card_versions.update_one({"_id": ver["_id"]}, {"$set": ver}, upsert=True)

    print("Writing rulings...")
    for rul in rulings:
        db.rulings.update_one({"_id": rul["_id"]}, {"$set": rul}, upsert=True)

    print("\nSuccessfully ingested Dominion data into avascry_dominion:")
    print(f"  - cards: {db.cards.count_documents({})}")
    print(f"  - card_versions: {db.card_versions.count_documents({})}")
    print(f"  - expansions: {db.expansions.count_documents({})}")
    print(f"  - rulings: {db.rulings.count_documents({})}")

if __name__ == "__main__":
    main()
