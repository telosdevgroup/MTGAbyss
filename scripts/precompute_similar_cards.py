import os
import sys
import time
import datetime
import numpy as np
import pymongo

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_mongo import get_mongo_db

MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://192.168.1.213:27017")
DB_NAME = os.environ.get("MONGODB_DB", "mtgabyss")

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [PrecomputeSimilar] {msg}", flush=True)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Precompute similar cards")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cards to process for testing")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB, just print results")
    args = parser.parse_args()

    log("Connecting to Beast MongoDB...")
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Ensure indexes on similar_cards unless it is a dry run
    if not args.dry_run:
        db["similar_cards"].create_index("oracle_id", unique=True)
    
    log("Caching card layouts from MongoDB...")
    cards_cursor = db["cards"].find({}, {
        "oracle_id": 1,
        "raw.layout": 1
    })
    
    card_layouts = {}
    invalid_layouts = {'art_series', 'token', 'double_faced_token', 'emblem', 'planar', 'scheme', 'vanguard', 'memorabilia'}
    
    for c in cards_cursor:
        oid = c.get("oracle_id")
        if not oid:
            continue
        raw = c.get("raw") or {}
        layout = raw.get("layout", "normal")
        card_layouts[oid] = layout
        
    log(f"Cached layouts for {len(card_layouts)} cards.")
    
    log("Fetching all embeddings from MongoDB...")
    all_embeddings = list(db["card_embeddings"].find({}, {
        "oracle_id": 1,
        "embedding": 1
    }))
    num_cards = len(all_embeddings)
    log(f"Loaded {num_cards} embeddings. Grouping by dimension...")
    
    # Group by dimension length
    groups = {}
    for item in all_embeddings:
        v = item["embedding"]
        if not v or not isinstance(v, list):
            continue
        d = len(v)
        groups[d] = groups.get(d, [])
        groups[d].append(item)
        
    total_processed = 0
    start_time = time.time()
    
    for dim, group in groups.items():
        dim_num_cards = len(group)
        log(f"Processing dimension group {dim} containing {dim_num_cards} cards...")
        
        oracle_ids = [item["oracle_id"] for item in group]
        X = np.empty((dim_num_cards, dim), dtype=np.float32)
        for idx, item in enumerate(group):
            X[idx] = item["embedding"]
            
        # Normalize rows
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        X_normalized = X / norms
        
        # We precompute similarity edges
        bulk_operations = []
        
        for idx, source_oid in enumerate(oracle_ids):
            v = X_normalized[idx]
            
            # Compute dot product
            sims = np.dot(X_normalized, v)
            
            # We want top 31 standard cards. 
            # We fetch more candidates first (e.g. 100) because some might be filtered by layout
            k = min(len(sims), 100)
            candidate_indices = np.argpartition(sims, - k)[-k:]
            candidate_indices = candidate_indices[np.argsort(sims[candidate_indices])[::-1]]
            
            similar_list = []
            for c_idx in candidate_indices:
                target_oid = oracle_ids[c_idx]
                if target_oid == source_oid:
                    continue
                
                # Check layout
                layout = card_layouts.get(target_oid, "normal")
                if layout in invalid_layouts:
                    continue
                    
                sim = float(sims[c_idx])
                similar_list.append({
                    "oracle_id": target_oid,
                    "similarity": round(sim, 4)
                })
                
                if len(similar_list) >= 31:
                    break
                    
            # Handle dry-run printing
            if args.dry_run:
                log(f"[DryRun] Card: {source_oid} -> top similar: {[(item['oracle_id'], item['similarity']) for item in similar_list[:3]]}")
            else:
                # Add update operation
                bulk_operations.append(
                    pymongo.UpdateOne(
                        {"oracle_id": source_oid},
                        {"$set": {
                            "oracle_id": source_oid,
                            "similar": similar_list,
                            "updated_at": datetime.datetime.now(datetime.timezone.utc)
                        }},
                        upsert=True
                    )
                )
            
            total_processed += 1
            if args.limit and total_processed >= args.limit:
                log(f"Reached test limit of {args.limit} cards. Stopping.")
                break
                
            if len(bulk_operations) >= 1000:
                if not args.dry_run:
                    db["similar_cards"].bulk_write(bulk_operations)
                bulk_operations = []
                elapsed = time.time() - start_time
                rate = total_processed / elapsed
                log(f"Precomputed {total_processed}/{num_cards} cards. Speed: {rate:.2f} cards/sec.")
                
        if args.limit and total_processed >= args.limit:
            break
            
        if bulk_operations and not args.dry_run:
            db["similar_cards"].bulk_write(bulk_operations)
            
    log(f"Completed precomputing similar cards. Total processed: {total_processed}.")

if __name__ == "__main__":
    main()
