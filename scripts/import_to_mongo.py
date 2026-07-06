import os
import sys
import json
import argparse
import hashlib
import datetime
import collections
import pymongo
from pymongo import ReplaceOne, UpdateOne

# Add root folder to sys.path so we can import db_mongo
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

def parse_line_with_hash(line):
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        source_hash = hashlib.md5(line.encode('utf-8')).hexdigest()
        return data, source_hash
    except:
        return None

def parse_lines_sequential(lines, limit=None):
    if limit:
        lines = lines[:limit]
    results = []
    for line in lines:
        parsed = parse_line_with_hash(line)
        if parsed:
            results.append(parsed)
    return results

def main():
    parser = argparse.ArgumentParser(description="Import Scryfall data to MongoDB.")
    parser.add_argument("--limit", type=int, help="Limit number of imported documents.")
    parser.add_argument("--dry-run", action="store_true", help="Read data without inserting into MongoDB.")
    args = parser.parse_args()

    # Find files
    files = os.listdir('.')
    cards_file = next((f for f in files if f.startswith('oracle-cards') and f.endswith('.jsonl')), None)
    tags_file = next((f for f in files if f.startswith('oracle-tags') and f.endswith('.jsonl')), None)
    rulings_file = next((f for f in files if f.startswith('rulings') and f.endswith('.jsonl')), None)

    if not (cards_file and tags_file and rulings_file):
        print("Missing one or more Scryfall JSONL files in project root!")
        sys.exit(1)

    print(f"Cards File: {cards_file}")
    print(f"Tags File: {tags_file}")
    print(f"Rulings File: {rulings_file}")

    db = None
    if not args.dry_run:
        db = get_mongo_db()
        ensure_indexes(db)
        print("Connected to MongoDB and ensured indexes.")

    now = datetime.datetime.now(datetime.timezone.utc)

    # 1. Load tags file into memory and parse
    print("\nLoading tags file into memory...")
    with open(tags_file, 'r', encoding='utf-8') as f:
        tags_lines = f.readlines()

    print("Parsing oracle tags...")
    parsed_tags = parse_lines_sequential(tags_lines, limit=args.limit)

    tags_by_oracle = collections.defaultdict(list)
    tags_total = 0

    for tag_obj, source_hash in parsed_tags:
        tag_slug = tag_obj.get("slug") or tag_obj.get("label")
        namespace = tag_obj.get("type")
        category = tag_obj.get("category")
        source = tag_obj.get("uri")
        taggings = tag_obj.get("taggings", [])

        for tagging in taggings:
            oracle_id = tagging.get("oracle_id")
            if not oracle_id:
                continue

            tag_doc = {
                "tag": tag_slug,
                "namespace": namespace,
                "category": category,
                "source": source,
                "source_hash": source_hash
            }
            tags_by_oracle[oracle_id].append(tag_doc)
            tags_total += 1

    print(f"Loaded {tags_total} tags mapped to {len(tags_by_oracle)} unique oracle_ids.")


    # 2. Load cards file into memory and parse
    print("\nLoading cards file into memory...")
    with open(cards_file, 'r', encoding='utf-8') as f:
        cards_lines = f.readlines()

    print("Parsing cards...")
    parsed_cards = parse_lines_sequential(cards_lines, limit=args.limit)

    print("Importing cards (with embedded tags) to MongoDB...")
    cards_ops = []
    card_counts = {"inserted": 0, "updated": 0, "unchanged": 0, "failed": 0}
    
    # Pre-fetch existing source_hashes to count updates vs inserts vs unchanged
    existing_hashes = {}
    if db is not None:
        for c in db["cards"].find({}, {"id": 1, "source_hash": 1}):
            existing_hashes[c["id"]] = c.get("source_hash")

    total_count = 0
    for card, source_hash in parsed_cards:
        cid = card.get("id")
        if not cid:
            card_counts["failed"] += 1
            continue

        oracle_id = card.get("oracle_id")
        card_tags = tags_by_oracle.get(oracle_id, [])

        # Promoted fields
        doc = {
            "id": cid,
            "oracle_id": oracle_id,
            "name": card.get("name"),
            "slug": slugify(card.get("name")),
            "lang": card.get("lang"),
            "type_line": card.get("type_line"),
            "oracle_text": card.get("oracle_text"),
            "mana_cost": card.get("mana_cost"),
            "cmc": card.get("cmc"),
            "color_identity": card.get("color_identity", []),
            "keywords": card.get("keywords", []),
            "legalities": card.get("legalities", {}),
            "reserved": card.get("reserved", False),
            "set": card.get("set"),
            "set_name": card.get("set_name"),
            "collector_number": card.get("collector_number"),
            "rarity": card.get("rarity"),
            "artist": card.get("artist"),
            "released_at": card.get("released_at"),
            "scryfall_uri": card.get("scryfall_uri"),
            "raw": card,  # Store full scryfall doc intact
            "source_hash": source_hash,
            "tags": card_tags, # Embedded tags
            "imported_at": now,
            "updated_at": now
        }

        # Track status
        if cid in existing_hashes:
            if existing_hashes[cid] == source_hash:
                card_counts["unchanged"] += 1
            else:
                card_counts["updated"] += 1
        else:
            card_counts["inserted"] += 1

        if db is not None:
            cards_ops.append(ReplaceOne({"id": cid}, doc, upsert=True))

            if len(cards_ops) >= 2000:
                db["cards"].bulk_write(cards_ops)
                cards_ops = []

        total_count += 1
        if total_count % 5000 == 0:
            print(f"Importing cards {total_count}...")

    if db is not None and cards_ops:
        db["cards"].bulk_write(cards_ops)

    print(f"Cards Ingestion Summary:")
    print(f"  Total Processed: {total_count}")
    print(f"  Inserted: {card_counts['inserted']}")
    print(f"  Updated: {card_counts['updated']}")
    print(f"  Unchanged: {card_counts['unchanged']}")
    print(f"  Failed: {card_counts['failed']}")


    # 3. Load rulings file into memory and parse
    print("\nLoading rulings file into memory...")
    with open(rulings_file, 'r', encoding='utf-8') as f:
        rulings_lines = f.readlines()

    print("Parsing rulings...")
    parsed_rulings = parse_lines_sequential(rulings_lines, limit=args.limit)

    print("Importing rulings to MongoDB...")
    rulings_ops = []
    ruling_total = 0
    for ruling, source_hash in parsed_rulings:
        oracle_id = ruling.get("oracle_id")
        if not oracle_id:
            continue

        doc = {
            "oracle_id": oracle_id,
            "source": ruling.get("source"),
            "published_at": ruling.get("published_at"),
            "comment": ruling.get("comment"),
            "source_hash": source_hash,
            "raw": ruling
        }

        if db is not None:
            ruling_uid = hashlib.md5(f"{oracle_id}:{ruling.get('comment')}".encode('utf-8')).hexdigest()
            doc["uid"] = ruling_uid
            rulings_ops.append(ReplaceOne({"uid": ruling_uid}, doc, upsert=True))

            if len(rulings_ops) >= 2000:
                db["rulings"].bulk_write(rulings_ops)
                rulings_ops = []

        ruling_total += 1
        if ruling_total % 10000 == 0:
            print(f"Importing rulings {ruling_total}...")

    if db is not None and rulings_ops:
        db["rulings"].bulk_write(rulings_ops)
    print(f"Rulings Ingested: {ruling_total}")

if __name__ == "__main__":
    main()
