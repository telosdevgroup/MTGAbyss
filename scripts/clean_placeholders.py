import os
import sys
import argparse
import pymongo

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db

def main():
    parser = argparse.ArgumentParser(description="Safely clear Celery 'vl' queue and purge placeholder vectors/analyses.")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without deleting anything")
    args = parser.parse_args()

    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://192.168.1.213:27017")
    client = pymongo.MongoClient(mongo_uri)
    db = client["mtgabyss_next"]
    broker_db = client["celery_broker"]

    print("=" * 60)
    print("AvaScry: Queue & Placeholder Vector Cleaner")
    print("=" * 60)

    # 1. Count Celery VL queue items
    vl_queue_count = broker_db["messages"].count_documents({"queue": "vl"})
    other_queue_count = broker_db["messages"].count_documents({"queue": {"$ne": "vl"}})
    print(f"[*] Celery 'vl' queue items: {vl_queue_count:,}")
    print(f"[*] Other Celery queue items (untouched): {other_queue_count:,}")

    # 2. Collect placeholder image URLs from cards
    print("[*] Identifying placeholder image URLs from Scryfall cards...")
    placeholder_urls = set(
        c.get("image_uris", {}).get("art_crop")
        for c in db["cards"].find({"image_status": "placeholder"}, {"image_uris.art_crop": 1})
    )
    placeholder_urls.discard(None)
    print(f"[*] Found {len(placeholder_urls):,} known placeholder art_crop URLs.")

    # 3. Find matching documents in vl_art_analysis
    vl_query = {"source.image_url": {"$in": list(placeholder_urls)}}
    matching_vl_docs = list(db["vl_art_analysis"].find(vl_query, {"illustration_id": 1}))
    matching_ill_ids = [d["illustration_id"] for d in matching_vl_docs if "illustration_id" in d]
    
    sim_count = db["vl_art_similarities"].count_documents({"illustration_id": {"$in": matching_ill_ids}})

    print(f"[*] 'vl_art_analysis' docs with placeholder scans: {len(matching_ill_ids):,}")
    print(f"[*] 'vl_art_similarities' docs with placeholder scans: {sim_count:,}")

    if args.dry_run:
        print("-" * 60)
        print("[*] DRY RUN complete. No items were deleted.")
        return

    # 4. Perform deletions
    print("-" * 60)
    print("[*] Proceeding with purge...")
    
    # 4a. Clear Celery VL queue
    del_queue = broker_db["messages"].delete_many({"queue": "vl"})
    print(f"[+] Deleted {del_queue.deleted_count:,} messages from Celery 'vl' queue.")

    # 4b. Delete from vl_art_analysis
    del_vl = db["vl_art_analysis"].delete_many({"illustration_id": {"$in": matching_ill_ids}})
    print(f"[+] Deleted {del_vl.deleted_count:,} documents from 'vl_art_analysis'.")

    # 4c. Delete from vl_art_similarities
    del_sim = db["vl_art_similarities"].delete_many({"illustration_id": {"$in": matching_ill_ids}})
    print(f"[+] Deleted {del_sim.deleted_count:,} documents from 'vl_art_similarities'.")

    remaining_vl = db["vl_art_analysis"].count_documents({"status": "complete"})
    print(f"[*] Clean analyzed illustrations remaining: {remaining_vl:,}")
    print("[+] Purge completed successfully.")

if __name__ == "__main__":
    main()
