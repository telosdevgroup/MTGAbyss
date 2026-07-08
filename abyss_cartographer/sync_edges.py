import os
import sys
import time
import pymongo
import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abyss_cartographer.db import init_db, get_db, save_stat

MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://192.168.1.213:27017")
DB_NAME = os.environ.get("MONGODB_DB", "mtgabyss")

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [SyncEdges] {msg}", flush=True)

def main():
    init_db()
    
    log("Connecting to Beast MongoDB...")
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    
    try:
        client.admin.command('ping')
        log("Connected to MongoDB successfully.")
    except Exception as e:
        log(f"Connection failed: {e}")
        sys.exit(1)
        
    log("Caching card metadata (names/slugs) from Mongo...")
    cards_cursor = db["cards"].find({}, {
        "oracle_id": 1,
        "name": 1,
        "slug": 1
    })
    card_metadata = {}
    for c in cards_cursor:
        oid = c.get("oracle_id")
        if oid:
            card_metadata[oid] = {
                "name": c.get("name"),
                "slug": c.get("slug")
            }
            
    log(f"Loaded metadata for {len(card_metadata)} cards.")
    
    log("Fetching precomputed similar cards from Mongo...")
    save_stat("sync_status", "Syncing edges...")
    
    # Fetch from the precomputed similar_cards collection
    similar_cursor = db["similar_cards"].find({}, {
        "oracle_id": 1,
        "similar": 1
    })
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Clear old local edges and cards table
    cursor.execute("DELETE FROM edges")
    cursor.execute("DELETE FROM cards")
    
    count = 0
    start_time = time.time()
    
    for doc in similar_cursor:
        source_oid = doc.get("oracle_id")
        similar_list = doc.get("similar") or []
        if not source_oid:
            continue
            
        c_meta = card_metadata.get(source_oid)
        if not c_meta:
            continue
            
        # Insert target card metadata
        cursor.execute("INSERT OR REPLACE INTO cards (oracle_id, name, slug) VALUES (?, ?, ?)",
                       (source_oid, c_meta["name"], c_meta["slug"]))
                       
        # Insert edges (similarity links)
        for item in similar_list:
            target_oid = item.get("oracle_id")
            sim = item.get("similarity")
            if target_oid and sim is not None:
                cursor.execute("INSERT OR REPLACE INTO edges (source_oracle_id, target_oracle_id, similarity) VALUES (?, ?, ?)",
                               (source_oid, target_oid, sim))
                               
        count += 1
        if count % 1000 == 0:
            conn.commit()
            elapsed = time.time() - start_time
            rate = count / elapsed
            log(f"Synced similar cards for {count} nodes. Rate: {rate:.2f} cards/sec.")
            save_stat("edges_built", count)
            
    conn.commit()
    conn.close()
    
    save_stat("sync_status", "Idle")
    log(f"Sync complete. Cached {count} card edge maps in local SQLite.")

if __name__ == "__main__":
    main()
