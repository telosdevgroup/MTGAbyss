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

    try:
        # Find oracle_ids that already have lures in abysses
        # Unless force is True
        excluded_ids = []
        if not force:
            completed_lures = mongo_db["abysses"].find(
                {"content.lure.text": {"$exists": True}},
                {"oracle_id": 1}
            )
            excluded_ids = [doc["oracle_id"] for doc in completed_lures]

        # Also exclude currently active claims
        active_claims = mongo_db["active_claims"].find({}, {"_id": 1})
        locked_ids = [doc["_id"] for doc in active_claims]
        excluded_ids.extend(locked_ids)

        # Build pipeline to find a random card not in excluded_ids
        pipeline = []
        if excluded_ids:
            pipeline.append({"$match": {"oracle_id": {"$nin": excluded_ids}}})
        pipeline.append({"$sample": {"size": 1}})

        cards = list(mongo_db["cards"].aggregate(pipeline))
        if not cards:
            return jsonify({"job_id": None, "message": "No cards available"}), 200

        card = cards[0]
        oracle_id = card["oracle_id"]

        # Lock the card by inserting into active_claims
        try:
            mongo_db["active_claims"].insert_one({
                "_id": oracle_id,
                "claimed_by": worker_id,
                "claimed_at": now
            })
        except pymongo.errors.DuplicateKeyError:
            return jsonify({"job_id": None, "message": "Race condition on claim, retry"}), 200

        # Build prompt using build_lure_prompt
        prompt, facts = build_lure_prompt(card)

        return jsonify({
            "job_id": oracle_id,
            "oracle_id": oracle_id,
            "card_name": card.get("name"),
            "slug": card.get("slug") or slugify(card.get("name")),
            "prompt": prompt,
            "facts": facts
        })

    except Exception as e:
        print(f"Error claiming job: {e}")
        return jsonify({"job_id": None, "error": str(e)}), 500

@app.route("/jobs/<job_id>/complete", methods=["POST"])
def complete_job(job_id):
    # job_id is the oracle_id
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
        # Verify the claim exists in active_claims
        claim = mongo_db["active_claims"].find_one({"_id": job_id})
        if not claim:
            return jsonify({"error": f"No active claim found for card: {job_id}"}), 404

        # Retrieve card facts to save
        card = mongo_db["cards"].find_one({"oracle_id": job_id})
        if not card:
            return jsonify({"error": f"Card not found in database: {job_id}"}), 404

        card_name = card.get("name")
        slug = card.get("slug") or slugify(card_name)

        # Write to abysses collection
        mongo_db["abysses"].update_one(
            {"entity_type": "commander", "oracle_id": job_id},
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
                        "temperature": 0.4,
                        "created_at": now_str,
                        "updated_at": now_str
                    },
                    "created_at": now_str,
                    "updated_at": now_str
                }
            },
            upsert=True
        )

        # Delete the active claim lock
        mongo_db["active_claims"].delete_one({"_id": job_id})

        return jsonify({"status": "completed", "job_id": job_id, "oracle_id": job_id})

    except Exception as e:
        print(f"Error completing job {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/jobs/<job_id>/fail", methods=["POST"])
def fail_job(job_id):
    # job_id is the oracle_id
    mongo_db = get_db()

    try:
        # Simply delete the active claim lock. Do not record failure in DB!
        mongo_db["active_claims"].delete_one({"_id": job_id})
        return jsonify({"status": "failed_recorded", "job_id": job_id, "new_status": "pending"})

    except Exception as e:
        print(f"Error failing job {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def get_stats():
    mongo_db = get_db()

    total_cards = mongo_db["cards"].count_documents({})
    completed = mongo_db["abysses"].count_documents({"content.lure.text": {"$exists": True}})
    claimed = mongo_db["active_claims"].count_documents({})
    failed = 0

    remaining = max(0, total_cards - completed)

    return jsonify({
        "total_commanders": total_cards,
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
