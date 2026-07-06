import os
import sys
import argparse
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Enqueue card embedding jobs.")
    parser.add_argument("--model", type=str, default="qwen3-embedding:0.6b", help="Embedding model name.")
    parser.add_argument("--version", type=str, default="card_context_v1", help="Embedding pipeline version.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of jobs to enqueue.")
    parser.add_argument("--force", action="store_true", help="Enqueue even if job or embedding already exists.")
    args = parser.parse_args()

    db = get_mongo_db()
    ensure_indexes(db)

    now = datetime.datetime.now(datetime.timezone.utc)
    enqueued_count = 0
    skipped_count = 0

    # Retrieve cards
    cards_cursor = db["cards"].find({})
    
    for card in cards_cursor:
        if enqueued_count >= args.limit:
            break
            
        oracle_id = card.get("oracle_id")
        card_slug = card.get("slug")
        card_name = card.get("name")
        
        if not oracle_id or not card_slug or not card_name:
            continue
            
        # Check for existing job or embedding
        if not args.force:
            existing_job = db["generation_jobs"].find_one({
                "oracle_id": oracle_id,
                "job_type": "generate_embedding",
                "status": {"$in": ["pending", "claimed", "completed"]}
            })
            existing_embedding = db["card_embeddings"].find_one({
                "oracle_id": oracle_id,
                "embedding_model": args.model,
                "embedding_version": args.version
            })
            if existing_job or existing_embedding:
                skipped_count += 1
                continue

        # Build embedding job document
        job = {
            "job_type": "generate_embedding",
            "oracle_id": oracle_id,
            "card_slug": card_slug,
            "card_name": card_name,
            "model": args.model,
            "version": args.version,
            "priority": 1,
            "status": "pending",
            "claimed_by": None,
            "claimed_at": None,
            "heartbeat_at": None,
            "attempts": 0,
            "max_attempts": 3,
            "error": None,
            "created_at": now,
            "updated_at": now
        }
        
        db["generation_jobs"].replace_one(
            {
                "oracle_id": oracle_id,
                "job_type": "generate_embedding"
            },
            job,
            upsert=True
        )
        enqueued_count += 1
        print(f"Enqueued embedding job: {card_name} (Model: {args.model})")

    print(f"\nEnqueue Run Finished:")
    print(f"  Enqueued: {enqueued_count}")
    print(f"  Skipped (already exists): {skipped_count}")

if __name__ == "__main__":
    main()
