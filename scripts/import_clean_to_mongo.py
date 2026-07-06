import os
import sys
import json
import hashlib
import datetime
import re
from pymongo import ReplaceOne

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def clean_card(card):
    # Strip price data
    if "prices" in card:
        del card["prices"]
    
    # Strip purchase URIs / TCGPlayer URLs
    if "purchase_uris" in card:
        del card["purchase_uris"]
        
    # Strip TCGPlayer or other buy/deck links from related_uris
    if "related_uris" in card:
        related = card["related_uris"]
        cleaned_related = {}
        for k, v in related.items():
            if "tcgplayer" not in k.lower() and "tcgplayer" not in str(v).lower():
                cleaned_related[k] = v
        card["related_uris"] = cleaned_related
        
    # Clean card faces if present
    if "card_faces" in card:
        for face in card["card_faces"]:
            if "tcgplayer" in face:
                del face["tcgplayer"]
                
    return card

def main():
    db = get_mongo_db()
    ensure_indexes(db)
    
    files = os.listdir('.')
    cards_file = next((f for f in files if f.startswith('oracle-cards') and f.endswith('.jsonl')), None)
    if not cards_file:
        print("Missing oracle-cards JSONL file!")
        sys.exit(1)
        
    print(f"Reading and importing cards from {cards_file}...")
    
    now = datetime.datetime.now(datetime.timezone.utc)
    bulk_ops = []
    processed = 0
    
    # Pre-fetch existing hashes to check for changes
    existing_hashes = {}
    for c in db["cards"].find({}, {"id": 1, "source_hash": 1}):
        existing_hashes[c["id"]] = c.get("source_hash")
        
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "failed": 0}
    
    with open(cards_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
                
            try:
                card = json.loads(line_str)
            except Exception as e:
                counts["failed"] += 1
                continue
                
            cid = card.get("id")
            if not cid:
                counts["failed"] += 1
                continue
                
            card = clean_card(card)
            
            # Recalculate source hash on clean card
            source_hash = hashlib.md5(json.dumps(card, sort_keys=True).encode("utf-8")).hexdigest()
            
            doc = {
                "id": cid,
                "scryfall_id": cid,
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
                "reserved": card.get("reserved", False),
                "set": card.get("set"),
                "set_name": card.get("set_name"),
                "collector_number": card.get("collector_number"),
                "rarity": card.get("rarity"),
                "artist": card.get("artist"),
                "released_at": card.get("released_at"),
                "scryfall_uri": card.get("scryfall_uri"),
                "image_uris": card.get("image_uris"),
                "card_faces": card.get("card_faces"),
                "raw": card, # Clean raw JSON
                "source_hash": source_hash,
                "imported_at": now,
                "updated_at": now
            }
            
            processed += 1
            if processed % 5000 == 0 or processed == 1:
                print(f"Building clean cards database {processed}: {doc['name']}")
                
            if cid in existing_hashes:
                if existing_hashes[cid] == source_hash:
                    counts["unchanged"] += 1
                else:
                    counts["updated"] += 1
                    bulk_ops.append(ReplaceOne({"id": cid}, doc, upsert=True))
            else:
                counts["inserted"] += 1
                bulk_ops.append(ReplaceOne({"id": cid}, doc, upsert=True))
                
            if len(bulk_ops) >= 1000:
                db["cards"].bulk_write(bulk_ops)
                bulk_ops = []
                
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
