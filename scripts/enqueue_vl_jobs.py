#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from typing import Set

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_mongo import get_mongo_db
from tasks import process_art_vl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("enqueue_vl_jobs")


def enqueue_vl_tasks(limit: int = 0, force: bool = False, dry_run: bool = False):
    db = get_mongo_db()
    cards_coll = db["cards"]
    vl_coll = db["art_vl"]

    log.info("Fetching existing completed illustrations from 'art_vl'...")
    completed_ids: Set[str] = set()
    if not force:
        completed_cursor = vl_coll.find({"status": "completed"}, {"illustration_id": 1})
        for doc in completed_cursor:
            iid = doc.get("illustration_id")
            if iid:
                completed_ids.add(str(iid))
        log.info(f"Found {len(completed_ids):,} already completed illustrations.")

    log.info("Scanning cards for unique illustration_id values...")
    pipeline = [
        {
            "$project": {
                "illustration_id": {
                    "$ifNull": ["$illustration_id", "$raw.illustration_id"]
                }
            }
        },
        {
            "$match": {
                "illustration_id": {"$exists": True, "$ne": None, "$ne": ""}
            }
        },
        {
            "$group": {
                "_id": "$illustration_id"
            }
        }
    ]

    all_ids = [doc["_id"] for doc in cards_coll.aggregate(pipeline)]
    log.info(f"Discovered {len(all_ids):,} total unique illustration_ids in DB.")

    pending_ids = [iid for iid in all_ids if force or str(iid) not in completed_ids]
    log.info(f"Pending illustrations to process: {len(pending_ids):,}")

    if limit > 0:
        pending_ids = pending_ids[:limit]
        log.info(f"Applied limit: processing {len(pending_ids):,} jobs.")

    if dry_run:
        log.info(f"[DRY-RUN] Would enqueue {len(pending_ids):,} tasks to queue 'vl'. Exiting.")
        return len(pending_ids)

    enqueued = 0
    for iid in pending_ids:
        process_art_vl.delay(illustration_id=iid, force=force)
        enqueued += 1
        if enqueued % 1000 == 0:
            log.info(f"Enqueued {enqueued:,}/{len(pending_ids):,} tasks to 'vl' queue...")

    log.info(f"Successfully enqueued {enqueued:,} tasks to Celery queue 'vl'!")
    return enqueued


def main():
    parser = argparse.ArgumentParser(description="Enqueue artwork VL analysis tasks to Celery 'vl' queue.")
    parser.add_argument("--limit", type=int, default=0, help="Max number of illustrations to enqueue (0 = all pending)")
    parser.add_argument("--force", action="store_true", help="Re-enqueue even if already completed in DB")
    parser.add_argument("--dry-run", action="store_true", help="Count pending illustrations without queueing Celery tasks")
    args = parser.parse_args()

    enqueue_vl_tasks(limit=args.limit, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

