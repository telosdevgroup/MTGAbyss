import os
import sys
import argparse
import datetime
from db_mongo import get_mongo_db, ensure_indexes

def main():
    parser = argparse.ArgumentParser(description="Repair stuck generation jobs.")
    parser.add_argument("--timeout-seconds", type=int, default=300, help="Heartbeat stale threshold in seconds.")
    args = parser.parse_args()

    db = get_mongo_db()
    ensure_indexes(db)

    now = datetime.datetime.now(datetime.timezone.utc)
    threshold = now - datetime.timedelta(seconds=args.timeout_seconds)

    # Find claimed jobs that have a heartbeat older than threshold
    stale_jobs = list(db["generation_jobs"].find({
        "status": "claimed",
        "$or": [
            {"heartbeat_at": {"$lt": threshold}},
            {"heartbeat_at": None}
        ]
    }))

    if not stale_jobs:
        print("No stale jobs found.")
        return

    print(f"Found {len(stale_jobs)} stale jobs. Repairing...")

    repaired = 0
    failed = 0

    for job in stale_jobs:
        oracle_id = job.get("oracle_id")
        lang = job.get("language")
        sec_type = job.get("section_type")
        attempts = job.get("attempts", 0)
        max_attempts = job.get("max_attempts", 3)

        if attempts >= max_attempts:
            # Mark failed
            db["generation_jobs"].update_one(
                {"_id": job["_id"]},
                {"$set": {
                    "status": "failed",
                    "error": "Max attempts exceeded after worker crash/heartbeat timeout",
                    "updated_at": now
                }}
            )
            print(f"Job failed (max attempts exceeded): {job.get('card_name')} ({sec_type or 'N/A'})")
            failed += 1
        else:
            # Reset to pending
            db["generation_jobs"].update_one(
                {"_id": job["_id"]},
                {"$set": {
                    "status": "pending",
                    "claimed_by": None,
                    "claimed_at": None,
                    "heartbeat_at": None,
                    "updated_at": now
                }}
            )
            print(f"Reset job to pending: {job.get('card_name')} ({sec_type or 'N/A'})")
            repaired += 1

    print(f"\nRepair Run Finished:")
    print(f"  Reset to Pending: {repaired}")
    print(f"  Marked Failed:    {failed}")

if __name__ == "__main__":
    main()
