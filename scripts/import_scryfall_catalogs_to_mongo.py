import os
import sys
import json
import argparse
import re
import hashlib
import datetime
from pymongo import ASCENDING

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

# Catalog list from scryfall_catalog_sync.py
CATALOGS = [
    "card-names", "artist-names", "word-bank", "supertypes", "card-types",
    "artifact-types", "battle-types", "creature-types", "enchantment-types",
    "land-types", "planeswalker-types", "spell-types", "powers", "toughnesses",
    "loyalties", "keyword-abilities", "keyword-actions", "ability-words",
    "flavor-words", "watermarks"
]

CATEGORY_MAPPING = {
    "card-names": "card_name",
    "artist-names": "artist_name",
    "word-bank": "word",
    "supertypes": "supertype",
    "card-types": "card_type",
    "artifact-types": "artifact_type",
    "battle-types": "battle_type",
    "creature-types": "creature_type",
    "enchantment-types": "enchantment_type",
    "land-types": "land_type",
    "planeswalker-types": "planeswalker_type",
    "spell-types": "spell_type",
    "powers": "power",
    "toughnesses": "toughness",
    "loyalties": "loyalty",
    "keyword-abilities": "keyword_ability",
    "keyword-actions": "keyword_action",
    "ability-words": "ability_word",
    "flavor-words": "flavor_word",
    "watermarks": "watermark"
}

def make_slug(value):
    if not isinstance(value, str):
        value = str(value)
    # lowercase and trim
    s = value.lower().strip()
    # replace apostrophes/quotes
    s = s.replace("'", "").replace('"', "")
    # replace non-alphanumeric runs with hyphen
    s = re.sub(r'[^a-z0-9]+', '-', s)
    # trim hyphens
    s = s.strip('-')
    if not s:
        # deterministic fallback based on a hash of the raw value
        h = hashlib.sha256(value.encode('utf-8')).hexdigest()[:8]
        s = f"hash-{h}"
    return s

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Import Scryfall catalogs to MongoDB.")
    parser.add_argument("--input-dir", default="data/scryfall/catalogs", help="Directory containing catalog JSONs.")
    parser.add_argument("--only", help="Comma-separated list of catalogs to import.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run (no db writes).")
    parser.add_argument("--force", action="store_true", help="Force update of existing documents.")
    parser.add_argument("--clear-catalog", help="Clear a specific catalog from database before import.")
    parser.add_argument("--clear-all-catalogs", action="store_true", help="Clear all catalogs from database before import.")

    args = parser.parse_args()

    # Determine database connection
    db = get_mongo_db()

    # Initialize/ensure indexes
    if not args.dry_run:
        ensure_indexes(db)

    collection = db["scryfall_catalogs"]

    # Handle clear flags
    if not args.dry_run:
        if args.clear_all_catalogs:
            print("Clearing all documents in scryfall_catalogs collection...")
            res = collection.delete_many({})
            print(f"Deleted {res.deleted_count} documents.")
        elif args.clear_catalog:
            target_clear = args.clear_catalog.strip()
            print(f"Clearing catalog '{target_clear}' from scryfall_catalogs collection...")
            res = collection.delete_many({"catalog": target_clear})
            print(f"Deleted {res.deleted_count} documents.")

    # Filter catalogs to process
    targets = CATALOGS
    if args.only:
        only_list = [c.strip() for c in args.only.split(",") if c.strip()]
        targets = [c for c in CATALOGS if c in only_list]
        invalid = [c for c in only_list if c not in CATALOGS]
        if invalid:
            print(f"Warning: Ignored invalid catalog names: {', '.join(invalid)}")

    if not targets:
        print("No valid catalogs to import.")
        return

    # Load metadata.json if present
    metadata_path = os.path.join(args.input_dir, "metadata.json")
    metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read metadata.json: {e}")

    summary = []

    for catalog in targets:
        file_path = os.path.join(args.input_dir, f"{catalog}.json")
        if not os.path.exists(file_path):
            print(f"Skipping missing file: {file_path}")
            summary.append({
                "catalog": catalog,
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
                "failed": 1,
                "total": 0,
                "status": "Missing file"
            })
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                catalog_data = json.load(f)
        except Exception as e:
            print(f"Skipping invalid JSON file {file_path}: {e}")
            summary.append({
                "catalog": catalog,
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
                "failed": 1,
                "total": 0,
                "status": "Invalid JSON"
            })
            continue

        if "data" not in catalog_data or not isinstance(catalog_data["data"], list):
            print(f"Skipping file {file_path}: Missing 'data' array.")
            summary.append({
                "catalog": catalog,
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
                "failed": 1,
                "total": 0,
                "status": "Invalid catalog structure"
            })
            continue

        data_list = catalog_data["data"]
        total_items = len(data_list)
        
        inserted = 0
        updated = 0
        unchanged = 0
        failed = 0

        catalog_meta = metadata.get(catalog, {})
        downloaded_at = catalog_meta.get("downloaded_at", datetime.datetime.now(datetime.timezone.utc).isoformat())

        # Pre-load existing items for this catalog to optimize comparisons and lookups
        existing_docs = {}
        for doc in collection.find({"catalog": catalog}):
            existing_docs[doc["slug"]] = doc

        for idx, val in enumerate(data_list, start=1):
            slug = make_slug(val)
            category = CATEGORY_MAPPING.get(catalog, catalog)
            relative_source_file = os.path.relpath(file_path, start=os.getcwd()).replace("\\", "/")

            doc = {
                "catalog": catalog,
                "endpoint": f"/catalog/{catalog}",
                "value": val,
                "slug": slug,
                "category": category,
                "source": "scryfall_catalog",
                "source_file": relative_source_file,
                "downloaded_at": downloaded_at,
                "imported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "raw": {}
            }

            print(f"Importing {catalog} {idx}/{total_items}: {val}")

            if args.dry_run:
                # In dry-run, we simulate insert or update. Use the existing_docs dictionary too
                existing = existing_docs.get(slug)

                if not existing:
                    inserted += 1
                    # Update dry-run cache
                    existing_docs[slug] = doc
                else:
                    # Compare core fields
                    is_different = (
                        existing.get("value") != doc["value"] or
                        existing.get("category") != doc["category"] or
                        existing.get("source_file") != doc["source_file"] or
                        existing.get("downloaded_at") != doc["downloaded_at"]
                    )
                    if args.force or is_different:
                        updated += 1
                        if "_id" in existing:
                            doc["_id"] = existing["_id"]
                        existing_docs[slug] = doc
                    else:
                        unchanged += 1
                continue

            # Actual db writes
            existing = existing_docs.get(slug)
            if not existing:
                try:
                    res = collection.insert_one(doc)
                    doc["_id"] = res.inserted_id
                    existing_docs[slug] = doc
                    inserted += 1
                except Exception as e:
                    print(f"Failed to insert {val} in {catalog}: {e}")
                    failed += 1
            else:
                is_different = (
                    existing.get("value") != doc["value"] or
                    existing.get("category") != doc["category"] or
                    existing.get("source_file") != doc["source_file"] or
                    existing.get("downloaded_at") != doc["downloaded_at"]
                )
                if args.force or is_different:
                    try:
                        doc["_id"] = existing["_id"]
                        collection.replace_one({"_id": existing["_id"]}, doc)
                        existing_docs[slug] = doc
                        updated += 1
                    except Exception as e:
                        print(f"Failed to update {val} in {catalog}: {e}")
                        failed += 1
                else:
                    unchanged += 1

        summary.append({
            "catalog": catalog,
            "inserted": inserted,
            "updated": updated,
            "unchanged": unchanged,
            "failed": failed,
            "total": total_items,
            "status": "Success"
        })

    # Print summary
    print("\nImport Summary:")
    print(f"{'Catalog':<25} {'Inserted':<10} {'Updated':<10} {'Unchanged':<10} {'Failed':<10} {'Total':<10}")
    print("-" * 71)
    for s in summary:
        print(f"{s['catalog']:<25} {s['inserted']:<10} {s['updated']:<10} {s['unchanged']:<10} {s['failed']:<10} {s['total']:<10}")

if __name__ == "__main__":
    main()
