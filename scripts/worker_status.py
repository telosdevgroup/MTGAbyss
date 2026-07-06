import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

def main():
    db = get_mongo_db()
    ensure_indexes(db)

    # Job counts
    pending = db["generation_jobs"].count_documents({"status": "pending"})
    claimed = db["generation_jobs"].count_documents({"status": "claimed"})
    completed = db["generation_jobs"].count_documents({"status": "completed"})
    failed = db["generation_jobs"].count_documents({"status": "failed"})

    print("=== Queue Status ===")
    print(f"Pending Jobs:   {pending}")
    print(f"Claimed Jobs:   {claimed}")
    print(f"Completed Jobs: {completed}")
    print(f"Failed Jobs:    {failed}")

    # Unique active workers (from claimed jobs)
    active_workers = db["generation_jobs"].distinct("claimed_by", {"status": "claimed"})
    print(f"\nActive Workers: {len(active_workers)}")
    for w in active_workers:
        if w:
            print(f"  - {w}")

    # Sections counts by language/type
    print("\n=== Generated Sections ===")
    pipeline = [
        {"$group": {
            "_id": {"language": "$language", "section_type": "$section_type"},
            "count": {"$sum": 1}
        }}
    ]
    results = list(db["generated_sections"].aggregate(pipeline))
    if not results:
        print("No generated sections found yet.")
    else:
        for r in results:
            lang = r["_id"]["language"]
            sec_type = r["_id"]["section_type"]
            count = r["count"]
            print(f"  {lang} / {sec_type}: {count}")

if __name__ == "__main__":
    main()
