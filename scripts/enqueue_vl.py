import os
import sys
import argparse
from datetime import datetime

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db, ensure_indexes
from tasks import process_art_vl

def main():
    parser = argparse.ArgumentParser(description="Enqueue unique MTG illustration IDs for blinded VL processing into Celery queue 'vl'.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of illustrations to queue (for testing/gradual rollouts)")
    parser.add_argument("--no-shuffle", action="store_true", help="Do not shuffle illustrations before enqueuing")
    parser.add_argument("--model", default="qwen3-vl:latest", help="VL model identifier (default: qwen3-vl:latest)")
    parser.add_argument("--prompt-version", type=int, default=1, help="Prompt version (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Print counts and exit without enqueuing")
    args = parser.parse_args()

    print("[*] Connecting to MongoDB and ensuring indexes...")
    db = get_mongo_db()
    ensure_indexes(db)

    print("[*] Querying unique English illustration IDs...")
    # Find all distinct illustration_ids that have an English printing and an art_crop
    pipeline = [
        {
            "$match": {
                "lang": "en",
                "$or": [
                    {"illustration_id": {"$exists": True, "$ne": None}},
                    {"raw.illustration_id": {"$exists": True, "$ne": None}}
                ],
                "$or": [
                    {"image_uris.art_crop": {"$exists": True}},
                    {"raw.image_uris.art_crop": {"$exists": True}},
                    {"card_faces.image_uris.art_crop": {"$exists": True}},
                    {"raw.card_faces.image_uris.art_crop": {"$exists": True}}
                ]
            }
        },
        {
            "$project": {
                "illustration_id": {
                    "$ifNull": ["$illustration_id", "$raw.illustration_id"]
                }
            }
        },
        {
            "$match": {
                "illustration_id": {"$ne": None, "$ne": ""}
            }
        },
        {
            "$group": {
                "_id": "$illustration_id"
            }
        }
    ]

    cursor = db.cards.aggregate(pipeline, allowDiskUse=True)
    all_illustration_ids = {doc["_id"] for doc in cursor if doc.get("_id")}
    total_found = len(all_illustration_ids)

    print(f"[*] Found {total_found:,} unique illustrations with English art crops.")

    # Find already completed illustration_ids in vl_art_analysis
    completed_cursor = db.vl_art_analysis.find(
        {
            "model": args.model,
            "prompt_version": args.prompt_version,
            "status": "complete"
        },
        {"illustration_id": 1, "_id": 0}
    )
    completed_ids = {doc["illustration_id"] for doc in completed_cursor if doc.get("illustration_id")}
    already_done = len(completed_ids)

    # Remaining to queue
    remaining_ids = list(all_illustration_ids - completed_ids)
    
    # Shuffle for varied visual distribution across nodes
    if not args.no_shuffle:
        import random
        random.seed()
        random.shuffle(remaining_ids)

    if args.limit:
        remaining_ids = remaining_ids[:args.limit]

    to_queue = len(remaining_ids)

    print("-" * 50)
    print(f"Unique English illustrations : {total_found:,}")
    print(f"Already analyzed             : {already_done:,}")
    print(f"Queued                       : {to_queue:,}")
    print("-" * 50)

    if args.dry_run:
        print("[*] Dry run enabled. No jobs were dispatched to Celery.")
        return

    if not remaining_ids:
        print("[+] All unique illustrations have already been analyzed!")
        return

    print(f"[*] Enqueuing {to_queue:,} jobs to Celery queue 'vl'...")
    for idx, ill_id in enumerate(remaining_ids, 1):
        process_art_vl.apply_async(
            args=[ill_id],
            kwargs={
                "model": args.model,
                "prompt_version": args.prompt_version
            },
            queue="vl"
        )
        if idx % 1000 == 0 or idx == to_queue:
            print(f"    Enqueued {idx:,}/{to_queue:,}...")

    print("\n[+] Enqueued {to_queue:,} jobs to Celery queue 'vl'.")
    print("GO FEED THE MACHINES.\n")

if __name__ == "__main__":
    main()
