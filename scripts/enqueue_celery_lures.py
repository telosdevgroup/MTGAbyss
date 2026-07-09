import os
import sys

# Add parent directory to path to allow importing db_mongo and tasks
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_mongo import get_mongo_db
from tasks import generate_lure

def main():
    db = get_mongo_db()
    
    print("Fetching completed lures from 'abysses' collection...")
    completed_cursor = db["abysses"].find(
        {"content.lure.status": "generated"},
        {"oracle_id": 1}
    )
    completed_ids = {doc["oracle_id"] for doc in completed_cursor if doc.get("oracle_id")}
    print(f"Found {len(completed_ids)} completed lures.")
    
    print("Fetching all cards from 'cards' collection...")
    cards_cursor = db["cards"].find({}, {"oracle_id": 1, "name": 1})
    all_cards = list(cards_cursor)
    print(f"Found {len(all_cards)} total cards.")
    
    pending_cards = [c for c in all_cards if c.get("oracle_id") and c["oracle_id"] not in completed_ids]
    print(f"Cards needing lures: {len(pending_cards)}")
    
    if not pending_cards:
        print("All cards already have generated lures!")
        return
        
    import time
    print(f"\nEnqueuing {len(pending_cards)} lure tasks to the 'ai-lures' queue in Celery...")
    start_time = time.time()
    total = len(pending_cards)
    
    for idx, card in enumerate(pending_cards):
        generate_lure.delay(card["oracle_id"])
        completed = idx + 1
        
        if completed % 50 == 0 or completed == total:
            elapsed = time.time() - start_time
            speed = completed / elapsed if elapsed > 0 else 0.0
            eta_str = "N/A"
            if speed > 0:
                eta_sec = (total - completed) / speed
                eta_str = f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s"
            
            bar_len = 30
            percent = completed / total
            arrow_len = int(round(percent * bar_len))
            arrow = '=' * (arrow_len - 1) + '>' if arrow_len > 0 else ''
            if len(arrow) > bar_len:
                arrow = '=' * bar_len
            spaces = ' ' * (bar_len - len(arrow))
            sys.stdout.write(f"\rQueueing: [{arrow}{spaces}] {completed}/{total} ({percent*100:.1f}%, {speed:.1f} tasks/sec, ETA: {eta_str})")
            sys.stdout.flush()
            
    print(f"\nFinished enqueuing all {total} tasks successfully!")

if __name__ == "__main__":
    main()
