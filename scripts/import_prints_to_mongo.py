import os
import sys
import json
import argparse
import hashlib
import datetime
from pymongo import ReplaceOne

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Import lite prints from Default Cards JSONL into MongoDB.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of imported printings.")
    args = parser.parse_args()

    # Find default cards jsonl file
    files = os.listdir('.')
    default_cards_file = next((f for f in files if f.startswith('default-cards') and f.endswith('.jsonl')), None)
    
    if not default_cards_file:
        print("Error: No default-cards JSONL file found in the project root.")
        sys.exit(1)

    print(f"Using default cards file: {default_cards_file}")

    db = get_mongo_db()
    ensure_indexes(db)

    # Pre-load existing hashes in card_prints to skip unchanged prints
    print("Loading existing print hashes from database...")
    existing_hashes = {}
    for p in db["card_prints"].find({}, {"id": 1, "source_hash": 1}):
        existing_hashes[p["id"]] = p.get("source_hash")

    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "failed": 0, "skipped_non_en": 0}
    bulk_ops = []
    processed = 0

    now = datetime.datetime.now(datetime.timezone.utc)

    print(f"Starting import from {default_cards_file}...")
    with open(default_cards_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue

            try:
                if line_str.startswith("[") or line_str.startswith("]"):
                    continue
                if line_str.endswith(","):
                    line_str = line_str[:-1]

                card = json.loads(line_str)
            except Exception:
                counts["failed"] += 1
                continue

            # Check language - only ingest English printings
            if card.get("lang") != "en":
                counts["skipped_non_en"] += 1
                continue

            scryfall_id = card.get("id")
            if not scryfall_id:
                counts["failed"] += 1
                continue

            # Extract a minimal/lite structure for images and matching
            image_uris = card.get("image_uris")
            card_faces = card.get("card_faces")
            
            # Keep only the image URIs inside card faces to minimize document size
            lite_faces = []
            if card_faces:
                for face in card_faces:
                    lite_faces.append({
                        "name": face.get("name"),
                        "image_uris": face.get("image_uris")
                    })

            doc = {
                "id": scryfall_id,
                "oracle_id": card.get("oracle_id"),
                "name": card.get("name"),
                "lang": card.get("lang"),
                "set": card.get("set"),
                "set_name": card.get("set_name"),
                "collector_number": card.get("collector_number"),
                "image_uris": image_uris,
                "card_faces": lite_faces if lite_faces else None,
                "imported_at": now,
                "updated_at": now
            }

            # Generate source hash from clean doc representation
            source_hash = hashlib.md5(json.dumps(doc, sort_keys=True, default=str).encode("utf-8")).hexdigest()
            doc["source_hash"] = source_hash

            processed += 1
            if processed % 5000 == 0:
                print(f"Processed {processed} English printings...")

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
            if len(bulk_ops) >= 1000:
                db["card_prints"].bulk_write(bulk_ops)
                bulk_ops = []

            if args.limit and processed >= args.limit:
                break

    if bulk_ops:
        db["card_prints"].bulk_write(bulk_ops)

    print("\n--- Ingestion Summary ---")
    print(f"Total English prints processed: {processed}")
    print(f"Inserted: {counts['inserted']}")
    print(f"Updated: {counts['updated']}")
    print(f"Unchanged: {counts['unchanged']}")
    print(f"Skipped non-English: {counts['skipped_non_en']}")
    print(f"Failed: {counts['failed']}")

if __name__ == "__main__":
    main()
