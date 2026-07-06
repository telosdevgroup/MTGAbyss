import os
import sys
import datetime
import argparse
from flask import Flask, request, jsonify
import pymongo
from bson import ObjectId

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db, ensure_indexes
from scripts.lure_shared import build_lure_prompt, slugify

app = Flask(__name__)
db = None

LOCK_TIMEOUT_SECONDS = 300  # 5 minutes

def get_db():
    global db
    if db is None:
        db = get_mongo_db()
        ensure_indexes(db)
    return db

def auto_scan_and_enqueue():
    mongo_db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Get all oracle_ids that already have a generated lure
    generated_cursor = mongo_db["abysses"].find(
        {
            "entity_type": "commander",
            "content.lure.status": "generated"
        },
        {"oracle_id": 1}
    )
    completed_oracle_ids = {doc["oracle_id"] for doc in generated_cursor if "oracle_id" in doc}
    
    # Query all legendary creatures
    cards_cursor = mongo_db["cards"].find(
        {"type_line": {"$regex": "Legendary.*Creature"}},
        {"oracle_id": 1, "name": 1, "slug": 1}
    )
    
    enqueued = 0
    for card in cards_cursor:
        oracle_id = card.get("oracle_id")
        if not oracle_id or oracle_id in completed_oracle_ids:
            continue
            
        # Check if a job already exists in generation_jobs
        existing_job = mongo_db["generation_jobs"].find_one({
            "oracle_id": oracle_id,
            "job_type": "generate_lure"
        })
        
        # If it doesn't exist, or if it was completed but we somehow don't have it in abysses (or want to force reset),
        # we can enqueue it.
        if not existing_job:
            name = card.get("name")
            slug = card.get("slug") or slugify(name)
            job_doc = {
                "job_type": "generate_lure",
                "oracle_id": oracle_id,
                "card_slug": slug,
                "card_name": name,
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
            mongo_db["generation_jobs"].replace_one(
                {
                    "oracle_id": oracle_id,
                    "job_type": "generate_lure"
                },
                job_doc,
                upsert=True
            )
            enqueued += 1
            
    if enqueued > 0:
        print(f"Auto-scan enqueued {enqueued} new Lure generation jobs.")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()})

@app.route("/jobs/claim", methods=["POST"])
def claim_job():
    data = request.json or {}
    worker_id = data.get("worker_id", "unknown_worker")
    force = data.get("force", False)

    mongo_db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)
    expiry_time = now - datetime.timedelta(seconds=LOCK_TIMEOUT_SECONDS)

    # Clean/Reset stale claimed lure jobs first if heartbeat older than threshold
    mongo_db["generation_jobs"].update_many(
        {
            "job_type": "generate_lure",
            "status": "claimed",
            "heartbeat_at": {"$lt": expiry_time}
        },
        {
            "$set": {
                "status": "pending",
                "claimed_by": None,
                "claimed_at": None,
                "heartbeat_at": None,
                "updated_at": now
            }
        }
    )

    # Force auto-scan if force=True or if there are no pending/claimed lure jobs
    pending_count = mongo_db["generation_jobs"].count_documents({
        "job_type": "generate_lure",
        "status": "pending"
    })
    
    if pending_count == 0 or force:
        auto_scan_and_enqueue()

    # Find the next job to claim
    query_filter = {
        "job_type": "generate_lure",
        "status": "pending"
    }

    try:
        job = mongo_db["generation_jobs"].find_one_and_update(
            query_filter,
            {
                "$set": {
                    "status": "claimed",
                    "claimed_by": worker_id,
                    "claimed_at": now,
                    "heartbeat_at": now,
                    "updated_at": now
                }
            },
            sort=[("priority", -1), ("created_at", 1)],
            return_document=pymongo.ReturnDocument.AFTER
        )

        if not job:
            return jsonify({"job_id": None, "message": "No jobs available"}), 200

        # Retrieve card facts to build prompt
        oracle_id = job.get("oracle_id")
        card = mongo_db["cards"].find_one({"oracle_id": oracle_id})
        if not card:
            # Job exists but card missing? Fail job
            mongo_db["generation_jobs"].update_one(
                {"_id": job["_id"]},
                {"$set": {"status": "failed", "error": "Card not found in cards collection", "updated_at": now}}
            )
            return jsonify({"job_id": None, "message": "Card missing, job failed"}), 400

        prompt, facts = build_lure_prompt(card)

        return jsonify({
            "job_id": str(job["_id"]),
            "oracle_id": oracle_id,
            "card_name": job.get("card_name"),
            "slug": job.get("card_slug"),
            "prompt": prompt,
            "facts": facts
        })

    except Exception as e:
        print(f"Error claiming job: {e}")
        return jsonify({"job_id": None, "error": str(e)}), 500

@app.route("/jobs/<job_id>/complete", methods=["POST"])
def complete_job(job_id):
    data = request.json or {}
    text = data.get("text")
    model = data.get("model", "unknown")
    worker_id = data.get("worker_id", "unknown")

    if not text:
        return jsonify({"error": "Missing 'text' in payload"}), 400

    mongo_db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)
    now_str = now.isoformat() + "Z"

    try:
        # Find the job in polymorphic generation_jobs
        job = mongo_db["generation_jobs"].find_one_and_update(
            {"_id": ObjectId(job_id), "status": "claimed"},
            {
                "$set": {
                    "status": "completed",
                    "error": None,
                    "updated_at": now
                }
            },
            return_document=pymongo.ReturnDocument.AFTER
        )

        if not job:
            return jsonify({"error": f"No claimed job found for job_id: {job_id}"}), 404

        # For generate_lure job type, store it in the abysses collection
        oracle_id = job.get("oracle_id")
        card_name = job.get("card_name")
        slug = job.get("card_slug")

        mongo_db["abysses"].update_one(
            {"entity_type": "commander", "oracle_id": oracle_id},
            {
                "$set": {
                    "card_name": card_name,
                    "slug": slug,
                    "content.lure": {
                        "status": "generated",
                        "text": text,
                        "model_provider": "ollama",
                        "model": model,
                        "worker_id": worker_id,
                        "prompt_version": "abyss_lure_v1",
                        "temperature": 0.7,
                        "created_at": now_str,
                        "updated_at": now_str
                    },
                    "created_at": now_str,
                    "updated_at": now_str
                }
            },
            upsert=True
        )

        return jsonify({"status": "completed", "job_id": job_id, "oracle_id": oracle_id})

    except Exception as e:
        print(f"Error completing job {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/jobs/<job_id>/fail", methods=["POST"])
def fail_job(job_id):
    data = request.json or {}
    error_msg = data.get("error", "Unknown error")
    worker_id = data.get("worker_id", "unknown")

    mongo_db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)

    try:
        # Find job to increment attempts
        job = mongo_db["generation_jobs"].find_one({"_id": ObjectId(job_id)})
        if not job:
            return jsonify({"error": f"No job found for job_id: {job_id}"}), 404

        attempts = job.get("attempts", 0) + 1
        max_attempts = job.get("max_attempts", 3)
        new_status = "pending" if attempts < max_attempts else "failed"

        mongo_db["generation_jobs"].update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": new_status,
                    "attempts": attempts,
                    "error": error_msg,
                    "claimed_by": None,
                    "claimed_at": None,
                    "heartbeat_at": None,
                    "updated_at": now
                }
            }
        )

        return jsonify({"status": "failed_recorded", "job_id": job_id, "new_status": new_status})

    except Exception as e:
        print(f"Error failing job {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def get_stats():
    mongo_db = get_db()

    total_commanders = mongo_db["cards"].count_documents({"type_line": {"$regex": "Legendary.*Creature"}})
    
    completed = mongo_db["generation_jobs"].count_documents({
        "job_type": "generate_lure",
        "status": "completed"
    })
    
    claimed = mongo_db["generation_jobs"].count_documents({
        "job_type": "generate_lure",
        "status": "claimed"
    })
    
    failed = mongo_db["generation_jobs"].count_documents({
        "job_type": "generate_lure",
        "status": "failed"
    })

    remaining = max(0, total_commanders - completed)

    return jsonify({
        "total_commanders": total_commanders,
        "completed": completed,
        "claimed": claimed,
        "failed": failed,
        "remaining": remaining
    })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lure Controller Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to run server on")
    args = parser.parse_args()

    print(f"Starting Lure Controller on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
