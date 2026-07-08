import os
import sys
import time
import random
import json
import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abyss_cartographer.db import init_db, get_db, save_stat

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [WalkWorker] {msg}", flush=True)

def get_top_4_edges(conn, oracle_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT target_oracle_id, similarity FROM edges 
        WHERE source_oracle_id = ? 
        ORDER BY similarity DESC LIMIT 4
    """, (oracle_id,))
    return [row[0] for row in cursor.fetchall()]

def get_card_name(conn, oracle_id):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM cards WHERE oracle_id = ?", (oracle_id,))
    row = cursor.fetchone()
    return row[0] if row else oracle_id

def run_walk(conn, start_oid, steps=6):
    path = [start_oid]
    current = start_oid
    
    for _ in range(steps):
        next_nodes = get_top_4_edges(conn, current)
        if not next_nodes:
            break
        current = random.choice(next_nodes)
        path.append(current)
        
    return path

def main():
    init_db()
    log("Walk Worker started.")
    
    while True:
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Pick a random starting card that has edges
            cursor.execute("SELECT DISTINCT source_oracle_id FROM edges ORDER BY RANDOM() LIMIT 1")
            row = cursor.fetchone()
            if not row:
                log("No edges found in local database. Waiting for sync_edges.py to run...")
                conn.close()
                time.sleep(10)
                continue
                
            start_oid = row[0]
            start_name = get_card_name(conn, start_oid)
            
            log(f"Starting random walk from '{start_name}'...")
            
            # Run 100 trials to build a histogram
            histogram = {}
            sample_path_names = []
            
            # Run first walk to get a nice path to display
            sample_path = run_walk(conn, start_oid)
            sample_path_names = [get_card_name(conn, oid) for oid in sample_path]
            
            for _ in range(100):
                path = run_walk(conn, start_oid)
                # Count only the final destination
                if path:
                    dest = path[-1]
                    histogram[dest] = histogram.get(dest, 0) + 1
                    
            # Save destination histogram to travel_profiles
            cursor.execute("""
                INSERT OR REPLACE INTO travel_profiles (oracle_id, profile_data, simulations_run)
                VALUES (?, ?, ?)
            """, (start_oid, json.dumps(histogram), 100))
            
            # Save walk to history
            path_text = " -> ".join(sample_path_names)
            cursor.execute("""
                INSERT INTO walk_history (start_name, path_text)
                VALUES (?, ?)
            """, (start_name, path_text))
            
            # Keep walk history under 50 items
            cursor.execute("DELETE FROM walk_history WHERE id NOT IN (SELECT id FROM walk_history ORDER BY id DESC LIMIT 50)")
            
            # Update stats
            cursor.execute("SELECT COUNT(*) FROM travel_profiles")
            save_stat("profiles_count", cursor.fetchone()[0])
            
            conn.commit()
            conn.close()
            
            log(f"Walk completed. Path: {path_text}")
            time.sleep(1) # sleep between walks
            
        except Exception as e:
            log(f"Error in walk worker: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
