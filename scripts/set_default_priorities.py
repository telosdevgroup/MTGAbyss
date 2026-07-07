import os
import sys
import json
import datetime
from pymongo import UpdateOne

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    db = get_mongo_db()

    # Step 1: Find the default-cards JSONL file
    files = os.listdir('.')
    default_cards_file = next((f for f in files if f.startswith('default-cards') and f.endswith('.jsonl')), None)
    
    if not default_cards_file:
        print("Error: No default-cards JSONL file found in the project root.")
        sys.exit(1)

    print(f"Reading printings from: {default_cards_file}...")

    # Step 2: Scan default-cards.jsonl line-by-line to find the oldest printing for each oracle_id
    # Map: oracle_id -> { "id": scryfall_id, "released_at": date_str }
    oldest_prints = {}
    processed_lines = 0

    with open(default_cards_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("[") or line_str.startswith("]"):
                continue
            if line_str.endswith(","):
                line_str = line_str[:-1]

            try:
                card = json.loads(line_str)
            except Exception:
                continue

            # Only consider English printings (to align with import_prints_to_mongo)
            if card.get("lang") != "en":
                continue

            oracle_id = card.get("oracle_id")
            scryfall_id = card.get("id")
            released_at = card.get("released_at")

            if not oracle_id or not scryfall_id or not released_at:
                continue

            processed_lines += 1

            if oracle_id not in oldest_prints:
                oldest_prints[oracle_id] = {"id": scryfall_id, "released_at": released_at}
            else:
                # Compare release dates
                existing_release = oldest_prints[oracle_id]["released_at"]
                if released_at < existing_release:
                    oldest_prints[oracle_id] = {"id": scryfall_id, "released_at": released_at}

    print(f"Scan finished. Processed {processed_lines} printings.")
    print(f"Found oldest printings for {len(oldest_prints)} unique oracle_ids.")

    # Step 3: Fetch all oracle_ids with a generated Lure
    print("Fetching oracle_ids that already have lures...")
    completed_lures = set(db["abysses"].distinct("oracle_id", {"content.lure.status": "generated"}))
    print(f"Found {len(completed_lures)} cards with completed lures.")

    # Step 4: Fetch all oracle cards and their release dates from 'cards' collection
    print("Fetching card release dates from 'cards' collection...")
    cards_cursor = db["cards"].find({}, {"oracle_id": 1, "name": 1, "released_at": 1})
    
    oracle_popularity = []
    for card in cards_cursor:
        oracle_id = card.get("oracle_id")
        if not oracle_id:
            continue
        
        released_at = card.get("released_at")
        if not released_at:
            released_at = "9999-12-31"  # Default to far future if missing
        
        oracle_popularity.append({
            "oracle_id": oracle_id,
            "name": card.get("name"),
            "released_at": released_at,
            "has_lure": oracle_id in completed_lures
        })

    # Step 5: Sort oracle cards:
    # 1. Cards with a lure first (has_lure=True comes before has_lure=False)
    # 2. Sorted by release date ascending (oldest first)
    oracle_popularity.sort(key=lambda x: (not x["has_lure"], x["released_at"]))

    # Step 6: Assign priorities.
    # The most popular card's oldest print gets the highest priority value (N).
    # The least popular card's oldest print gets priority 1.
    print("Preparing bulk update operations for 'card_prints' and 'cards' collections...")
    
    total_cards = len(oracle_popularity)
    card_updates = []
    prints_updates = []
    updated_count = 0

    for index, item in enumerate(oracle_popularity):
        oracle_id = item["oracle_id"]
        # Priority goes from total_cards down to 1
        priority_val = total_cards - index

        # Update the main card document in 'cards'
        card_updates.append(UpdateOne(
            {"oracle_id": oracle_id},
            {"$set": {"base_priority": priority_val}}
        ))

        # Update the oldest print in 'card_prints'
        if oracle_id in oldest_prints:
            scryfall_id = oldest_prints[oracle_id]["id"]
            prints_updates.append(UpdateOne(
                {"id": scryfall_id},
                {"$set": {"base_priority": priority_val}}
            ))
            updated_count += 1

    # Step 7: Write updates to database
    if card_updates:
        print(f"Updating base_priority on {len(card_updates)} documents in 'cards' collection...")
        db["cards"].bulk_write(card_updates)

    if prints_updates:
        print(f"Updating base_priority on {len(prints_updates)} documents in 'card_prints' collection...")
        db["card_prints"].bulk_write(prints_updates)

    print(f"\nSuccessfully assigned base_priority to {updated_count} oldest printings based on popularity!")

if __name__ == "__main__":
    main()
