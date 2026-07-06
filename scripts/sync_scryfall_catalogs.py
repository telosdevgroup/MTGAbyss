import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

CATALOGS = [
    "card-names", "artist-names", "word-bank", "supertypes", "card-types",
    "artifact-types", "battle-types", "creature-types", "enchantment-types",
    "land-types", "planeswalker-types", "spell-types", "powers", "toughnesses",
    "loyalties", "keyword-abilities", "keyword-actions", "ability-words",
    "flavor-words", "watermarks"
]

def main():
    db = get_mongo_db()
    # Drop legacy collection to ensure new unique indexes can be created cleanly
    db["scryfall_catalogs"].drop()
    ensure_indexes(db)
    
    print("Starting Scryfall catalog synchronization...")
    
    total = len(CATALOGS)
    for index, catalog_key in enumerate(CATALOGS, 1):
        endpoint = f"/catalog/{catalog_key}"
        uri = f"https://api.scryfall.com{endpoint}"
        
        print(f"Fetching {catalog_key} {index}/{total} ...")
        
        try:
            req = urllib.request.Request(
                uri, 
                headers={
                    "User-Agent": "MTGAbyss/1.0 (contact: dev@mtgabyss.com)",
                    "Accept": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as res:
                response_data = json.loads(res.read().decode("utf-8"))
            
            if response_data.get("object") != "catalog":
                raise ValueError(f"Expected object type 'catalog', got '{response_data.get('object')}'")
            
            data_array = response_data.get("data", [])
            total_values = response_data.get("total_values", len(data_array))
            
            doc = {
                "catalog_key": catalog_key,
                "endpoint": endpoint,
                "uri": uri,
                "object": "catalog",
                "total_values": total_values,
                "data": data_array,
                "source": "scryfall",
                "synced_at": datetime.now(timezone.utc)
            }
            
            # Upsert into scryfall_catalogs collection by catalog_key
            db["scryfall_catalogs"].replace_one(
                {"catalog_key": catalog_key},
                doc,
                upsert=True
            )
            
        except Exception as e:
            print(f"Error fetching catalog {catalog_key} from {uri}: {e}")
            sys.exit(1)
            
        # Polite delay
        if index < total:
            time.sleep(0.15)
            
    print(f"Successfully synced {total} catalogs.")

if __name__ == "__main__":
    main()
