import os
import sys
import time
import re
import json
import pymongo
import datetime
import urllib.request
import urllib.error

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abyss_cartographer.db import init_db, get_db, save_stat

MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://192.168.1.213:27017")
DB_NAME = os.environ.get("MONGODB_DB", "mtgabyss")
DEFAULT_BASE_URL = "http://192.168.1.213:8080" # Beast preview server

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [SyncEdges] {msg}", flush=True)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pi edge sync by crawling Beast preview server")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the Beast preview server")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cards to crawl for testing")
    args = parser.parse_args()
    
    init_db()
    
    log("Connecting to Beast MongoDB (read-only) for card slugs...")
    client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    
    try:
        client.admin.command('ping')
        log("Connected to MongoDB successfully.")
    except Exception as e:
        log(f"Connection failed: {e}")
        sys.exit(1)
        
    log("Loading card metadata...")
    cards_cursor = db["cards"].find({}, {
        "oracle_id": 1,
        "name": 1,
        "slug": 1
    })
    
    card_metadata = {}
    slug_to_oid = {}
    for c in cards_cursor:
        oid = c.get("oracle_id")
        slug = c.get("slug")
        if oid and slug:
            card_metadata[oid] = {
                "name": c.get("name"),
                "slug": slug
            }
            slug_to_oid[slug] = oid
            
    log(f"Loaded {len(card_metadata)} cards.")
    
    # Save base card definitions into SQLite
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards")
    for oid, meta in card_metadata.items():
        cursor.execute("INSERT OR REPLACE INTO cards (oracle_id, name, slug) VALUES (?, ?, ?)",
                       (oid, meta["name"], meta["slug"]))
    conn.commit()
    
    # Get processed cards
    cursor.execute("SELECT DISTINCT source_oracle_id FROM edges")
    processed_sources = {row[0] for row in cursor.fetchall()}
    conn.close()
    
    log(f"Already synced edges for {len(processed_sources)} cards.")
    save_stat("sync_status", "Crawling preview server...")
    
    count = 0
    start_time = time.time()
    
    # Iterate over all cards to crawl them
    for oid, meta in card_metadata.items():
        if oid in processed_sources:
            continue
            
        slug = meta["slug"]
        url = f"{args.base_url.rstrip('/')}/card/{slug}/index.html"
        
        # Crawl the page
        try:
            # Add user agent to prevent any blocks
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (AbyssCartographer)'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode('utf-8')
        except urllib.error.URLError as e:
            log(f"Error crawling card '{slug}': {e}. Is the preview server running on Beast?")
            # Stop if server is not reachable
            break
        except Exception as e:
            log(f"Unexpected error crawling '{slug}': {e}")
            continue
            
        # Extract similar cards JSON
        # Pattern: const similarCards = [ ... ];
        match = re.search(r'const similarCards = (\[.*?\]);', html_content)
        if not match:
            log(f"Warning: could not find similarCards JSON in page for '{slug}'.")
            continue
            
        try:
            similar_list = json.loads(match.group(1))
        except Exception as e:
            log(f"Error parsing similarCards JSON for '{slug}': {e}")
            continue
            
        # Write edges to SQLite
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM edges WHERE source_oracle_id = ?", (oid,))
        
        # Save outgoing edges
        edge_count = 0
        for item in similar_list:
            t_slug = item.get("slug")
            sim = item.get("similarity")
            if t_slug and sim is not None:
                t_oid = slug_to_oid.get(t_slug)
                if t_oid:
                    cursor.execute("INSERT OR REPLACE INTO edges (source_oracle_id, target_oracle_id, similarity) VALUES (?, ?, ?)",
                                   (oid, t_oid, sim))
                    edge_count += 1
                    
        conn.commit()
        conn.close()
        
        count += 1
        if count % 100 == 0:
            elapsed = time.time() - start_time
            rate = count / elapsed
            log(f"Crawled and synced edges for {count} cards. Rate: {rate:.2f} cards/sec.")
            save_stat("edges_built", len(processed_sources) + count)
            
        if args.limit and count >= args.limit:
            log(f"Reached crawl limit of {args.limit} cards.")
            break
            
    save_stat("sync_status", "Idle")
    log(f"Crawling completed. Sync of {count} card edge maps complete.")

if __name__ == "__main__":
    main()
