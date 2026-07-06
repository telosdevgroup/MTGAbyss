import os
import sys
import json
import argparse
import hashlib
import datetime
from pymongo import ReplaceOne

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

def slugify(s):
    import re
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Import cards from JSONL file into MongoDB.")
    parser.add_argument("--file", type=str, required=True, help="Path to cards JSONL file.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of imported cards.")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        sys.exit(1)

    db = get_mongo_db()
    ensure_indexes(db)

    # Pre-load existing source hashes to verify changes
    existing_hashes = {}
    for c in db["cards"].find({}, {"id": 1, "source_hash": 1}):
        existing_hashes[c["id"]] = c.get("source_hash")

    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "failed": 0}
    bulk_ops = []
    processed = 0

    now = datetime.datetime.now(datetime.timezone.utc)

    print(f"Starting import from {args.file}...")
    with open(args.file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue

            try:
                # Handle possible trailing commas in case of an array or just clean JSON
                if line_str.startswith("[") or line_str.startswith("]"):
                    continue
                if line_str.endswith(","):
                    line_str = line_str[:-1]

                card = json.loads(line_str)
            except Exception as e:
                counts["failed"] += 1
                continue

            scryfall_id = card.get("id")
            if not scryfall_id:
                counts["failed"] += 1
                continue

            # Calculate source hash of the raw card JSON
            source_hash = hashlib.md5(json.dumps(card, sort_keys=True).encode("utf-8")).hexdigest()

            # Prepare card document with promoted/normalized fields
            doc = {
                "id": scryfall_id,
                "scryfall_id": scryfall_id,
                "oracle_id": card.get("oracle_id"),
                "name": card.get("name"),
                "slug": slugify(card.get("name")),
                "lang": card.get("lang"),
                "type_line": card.get("type_line"),
                "oracle_text": card.get("oracle_text"),
                "mana_cost": card.get("mana_cost"),
                "cmc": card.get("cmc") if card.get("cmc") is not None else card.get("mana_value"),
                "color_identity": card.get("color_identity", []),
                "keywords": card.get("keywords", []),
                "legalities": card.get("legalities", {}),
                "reserved": card.get("reserved"),
                "set": card.get("set"),
                "set_name": card.get("set_name"),
                "collector_number": card.get("collector_number"),
                "rarity": card.get("rarity"),
                "artist": card.get("artist"),
                "released_at": card.get("released_at"),
                "scryfall_uri": card.get("scryfall_uri"),
                "source_hash": source_hash,
                "imported_at": now,
                "updated_at": now
            }

            # Print progress: "Importing cards 12/1000: Black Lotus" (limit or running total)
            processed += 1
            limit_str = f"/{args.limit}" if args.limit else ""
            print(f"Importing cards {processed}{limit_str}: {doc['name']}")

            # Track status (inserted, updated, unchanged)
            if scryfall_id in existing_hashes:
                if existing_hashes[scryfall_id] == source_hash:
                    counts["unchanged"] += 1
                else:
                    counts["updated"] += 1
                    bulk_ops.append(ReplaceOne({"id": scryfall_id}, doc, upsert=True))
            else:
                counts["inserted"] += 1
                bulk_ops.append(ReplaceOne({"id": scryfall_id}, doc, upsert=True))

            # Batch write
            if len(bulk_ops) >= 500:
                db["cards"].bulk_write(bulk_ops)
                bulk_ops = []

            if args.limit and processed >= args.limit:
                break

    if bulk_ops:
        db["cards"].bulk_write(bulk_ops)

    print("\n--- Ingestion Summary ---")
    print(f"Total Processed: {processed}")
    print(f"Inserted: {counts['inserted']}")
    print(f"Updated: {counts['updated']}")
    print(f"Unchanged: {counts['unchanged']}")
    print(f"Failed: {counts['failed']}")

if __name__ == "__main__":
    main()
