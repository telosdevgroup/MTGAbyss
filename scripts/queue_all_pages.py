import sys
import os
import pymongo

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery_app import app
from tasks import generate_and_deploy_page
from db_mongo import get_mongo_db

def log(msg):
    print(f"[QueueAll] {msg}", flush=True)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Queue all MTGAbyss cards for page generation and deployment")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of cards queued for testing")
    parser.add_argument("--no-deploy", action="store_true", help="Queue tasks with deploy=False (local build only)")
    args = parser.parse_args()

    log("Connecting to MongoDB...")
    db = get_mongo_db()
    
    log("Fetching list of all card names from database...")
    # Only fetch cards that have names and oracle IDs
    cards_cursor = db["cards"].find(
        {"oracle_id": {"$exists": True}, "name": {"$exists": True}},
        {"name": 1, "base_priority": 1}
    )
    
    name_prios = {}
    for c in cards_cursor:
        name = c.get("name")
        if name:
            prio = c.get("base_priority", 0) or 0
            name_prios[name] = max(name_prios.get(name, 0), prio)
            
    card_names = sorted(name_prios.keys(), key=lambda n: (-name_prios[n], n))
    total_cards = len(card_names)
    log(f"Found {total_cards:,} unique cards.")
    
    if args.limit:
        card_names = card_names[:args.limit]
        log(f"Limiting to first {args.limit:,} cards for testing.")
        
    deploy_flag = not args.no_deploy
    log(f"Queueing tasks with deploy={deploy_flag}...")
    
    count = 0
    for name in card_names:
        generate_and_deploy_page.delay(name, deploy=deploy_flag)
        count += 1
        if count % 1000 == 0:
            log(f"Queued {count:,} / {len(card_names):,} tasks...")
            
    log(f"Success! Finished queuing {count:,} card page building tasks to Celery.")

if __name__ == "__main__":
    main()
