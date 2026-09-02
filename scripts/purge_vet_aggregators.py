import os
import re
from datetime import datetime, timezone
import pymongo
from dotenv import load_dotenv

load_dotenv()

DOMAINS_TO_PURGE = [
    "remax.com",
    "alignable.com",
    "rocketreach.co",
    "scratchpay.com",
    "texaslandcan.org",
    "massvet.org",
    "us.placedigger.com",
    "justanswer.com",
    "livma.org",
    "us.bebee.com",
    "newsbreak.com",
    "hotfrog.com",
    "directionus.com",
    "furryland.us",
    "alphagroomingpetsalon.com",
    "louisianalandcan.org",
    "poultrydvm.com",
    "apartmentfinder.com",
    "iowarealty.com",
    "cpt-training.com",
    "florida.intercreditreport.com",
    "directoryplus.com",
    "lensa.com",
    "ahvma.org"
]

def main():
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    client = pymongo.MongoClient(mongo_uri)
    now = datetime.now(timezone.utc).isoformat()

    # 1. Update vetgems_fishing.denylist_domains
    db_fishing = client["vetgems_fishing"]
    denylist_col = db_fishing["denylist_domains"]

    added_to_denylist = 0
    for d in DOMAINS_TO_PURGE:
        res = denylist_col.update_one(
            {"$or": [{"domain": d}, {"normalized_domain": d}]},
            {
                "$set": {
                    "domain": d,
                    "normalized_domain": d,
                    "reason": "aggregator_or_non_vet_purge",
                    "updated_at": now
                },
                "$setOnInsert": {
                    "created_at": now
                }
            },
            upsert=True
        )
        if res.upserted_id or res.modified_count:
            added_to_denylist += 1

    print(f"[STEP 1] Denylist updated: {added_to_denylist} domains in vetgems_fishing.denylist_domains (Total: {denylist_col.count_documents({})})")

    # 2. Build regex query pattern
    regex_pattern = "|".join(re.escape(d) for d in DOMAINS_TO_PURGE)
    
    query = {
        "$or": [
            {"domain": {"$in": DOMAINS_TO_PURGE}},
            {"normalized_domain": {"$in": DOMAINS_TO_PURGE}},
            {"host": {"$in": DOMAINS_TO_PURGE}},
            {"website": {"$in": DOMAINS_TO_PURGE}},
            {"url": {"$regex": regex_pattern, "$options": "i"}},
            {"practice_url": {"$regex": regex_pattern, "$options": "i"}}
        ]
    }

    # 3. Purge across collections
    targets = [
        ("vetgems_fishing", "candidate_practices"),
        ("vetgems_fishing", "practice_pages"),
        ("vetgems_fishing", "search_observations"),
        ("vetgems_lake", "raw_observations"),
        ("vetgems_lake", "domain_watch"),
        ("vetgems_lake", "singleton_observations"),
        ("vetgems_lake", "practice_pages"),
        ("vetgems_dev", "practice_pages")
    ]

    print("\n[STEP 2] Executing database purges...")
    total_deleted = 0

    for db_name, col_name in targets:
        try:
            db = client[db_name]
            if col_name not in db.list_collection_names():
                continue
            col = db[col_name]
            del_res = col.delete_many(query)
            if del_res.deleted_count > 0:
                print(f"  -> Deleted {del_res.deleted_count} records from {db_name}.{col_name}")
                total_deleted += del_res.deleted_count
            else:
                print(f"  -> {db_name}.{col_name}: 0 matching records")
        except Exception as e:
            print(f"  [ERROR] Failed to purge from {db_name}.{col_name}: {e}")

    print(f"\n[COMPLETE] Successfully purged {total_deleted} total garbage aggregator records!")

if __name__ == "__main__":
    main()
