import os
import sys
import datetime
import argparse
import urllib.request
import json
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

OLLAMA_URL = "http://localhost:11434"
JUDGE_MODEL = "mistral-nemo"

def get_db():
    global db
    if db is None:
        db = get_mongo_db()
        ensure_indexes(db)
    return db

def validate_lure_with_ai(ollama_url, model, card_name, card_type, card_text, generated_lure):
    url = f"{ollama_url.rstrip('/')}/api/generate"
    
    prompt = f"""Evaluate this generated short story/introduction text (Lure) for a Magic: The Gathering card named '{card_name}' ({card_type}).

Card Text:
{card_text}

Generated Lure Text:
"{generated_lure}"

Verify if the Lure text is good. It should feel evocative, mystical, or strange, and avoid dry rules review tone.
You must respond with a JSON object.

Your JSON response must match this format exactly:
{{
  "status": "PASSED" | "FAILED"
}}

Do not include any other text, markdown, or explanation outside the JSON.
Response:"""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0
        }
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw_response = res_data.get("response", "").strip()
            parsed = json.loads(raw_response)
            status = parsed.get("status", "FAILED").upper()
            return status == "PASSED"
    except Exception as e:
        print(f"Error calling Ollama judge: {e}")
        return False

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
        # Find oracle_ids that already have lures or hooks in abysses
        # Unless force is True
        excluded_ids = []
        if not force:
            completed_lures = mongo_db["abysses"].find(
                {"$or": [{"content.lure": {"$exists": True}}, {"content.hook": {"$exists": True}}]},
                {"oracle_id": 1}
            )
            excluded_ids = [doc["oracle_id"] for doc in completed_lures if "oracle_id" in doc]

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

        # Calculate remaining cards without a lure or hook dynamically
        completed_count = mongo_db["abysses"].count_documents(
            {"$or": [{"content.lure": {"$exists": True}}, {"content.hook": {"$exists": True}}]}
        )
        total_cards = mongo_db["cards"].count_documents({})
        remaining = max(0, total_cards - completed_count)

        return jsonify({
            "job_id": oracle_id,
            "oracle_id": oracle_id,
            "card_name": card.get("name"),
            "slug": card.get("slug") or slugify(card.get("name")),
            "prompt": prompt,
            "facts": facts,
            "remaining": remaining
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

        # Retrieve card facts to validate and save
        card = mongo_db["cards"].find_one({"oracle_id": job_id})
        if not card:
            return jsonify({"error": f"Card not found in database: {job_id}"}), 404

        card_name = card.get("name")
        card_type = card.get("type_line", "")
        card_text = card.get("oracle_text", "")
        slug = card.get("slug") or slugify(card_name)

        # Validate with Ollama judge
        print(f"Controller: Validating Lure for '{card_name}' using model '{JUDGE_MODEL}'...")
        is_valid = validate_lure_with_ai(OLLAMA_URL, JUDGE_MODEL, card_name, card_type, card_text, text)

        if not is_valid:
            print(f"Controller: Validation failed for '{card_name}'!")
            # Release the lock so it can be retried
            mongo_db["active_claims"].delete_one({"_id": job_id})
            return jsonify({"status": "validation_failed", "message": "AI validation failed."}), 422

        print(f"Controller: Validation passed for '{card_name}'!")

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
    completed = mongo_db["abysses"].count_documents(
        {"$or": [{"content.lure": {"$exists": True}}, {"content.hook": {"$exists": True}}]}
    )
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
    parser.add_argument("--judge-model", default="mistral-nemo", help="Ollama model to use as validation judge")
    args = parser.parse_args()

    JUDGE_MODEL = args.judge_model
    print(f"Starting Lure Controller on http://{args.host}:{args.port} using judge model '{JUDGE_MODEL}'")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
