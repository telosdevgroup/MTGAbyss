import os
import sys
import datetime
import argparse
import json
from flask import Flask, request, jsonify
import pymongo

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

def find_next_prioritized_card(mongo_db, collection_name, id_field, excluded_ids):
    """
    Finds the next card from the specified collection, prioritizing cards with
    'base_priority' > 0.
    To minimize race conditions among multiple workers:
    1. Checks if any non-excluded cards have base_priority > 0.
    2. If so, finds the maximum base_priority among those.
    3. Randomly samples 1 card from all eligible cards matching that highest base_priority tier.
    4. If no prioritized cards are available, falls back to randomly sampling 1 from all eligible cards.
    """
    match_stage = {}
    if excluded_ids:
        match_stage[id_field] = {"$nin": excluded_ids}

    # Query to check for any eligible cards with base_priority > 0
    priority_query = {
        "$and": [
            match_stage,
            {"base_priority": {"$gt": 0}}
        ]
    } if match_stage else {
        "base_priority": {"$gt": 0}
    }

    # Find the top base_priority value present
    highest_cards = list(
        mongo_db[collection_name]
        .find(priority_query, {"base_priority": 1})
        .sort([("base_priority", -1)])
        .limit(1)
    )

    if highest_cards:
        highest_card = highest_cards[0]
        p = highest_card.get("base_priority", 0) or 0

        # Match all eligible cards with this exact base_priority
        sample_query = dict(match_stage)
        sample_query["base_priority"] = p

        pipeline = [
            {"$match": sample_query},
            {"$sample": {"size": 1}}
        ]
        sampled = list(mongo_db[collection_name].aggregate(pipeline))
        if sampled:
            return sampled[0]

    # Fallback to random sample of all eligible cards
    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})
    pipeline.append({"$sample": {"size": 1}})

    sampled = list(mongo_db[collection_name].aggregate(pipeline))
    return sampled[0] if sampled else None

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

    # Release stale active claims first
    mongo_db["active_claims"].delete_many({
        "claimed_at": {"$lt": expiry_time}
    })

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

        card = find_next_prioritized_card(mongo_db, "cards", "oracle_id", excluded_ids)
        if not card:
            return jsonify({"job_id": None, "message": "No cards available"}), 200

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
                        "temperature": data.get("temperature", 0.7),
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

@app.route("/jobs/claim_image", methods=["POST"])
def claim_image_job():
    data = request.json or {}
    worker_id = data.get("worker_id", "unknown_worker")
    force = data.get("force", False)

    mongo_db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)
    expiry_time = now - datetime.timedelta(seconds=LOCK_TIMEOUT_SECONDS)

    # Release stale active claims
    mongo_db["active_image_claims"].delete_many({
        "claimed_at": {"$lt": expiry_time}
    })

    try:
        excluded_ids = []
        if not force:
            completed_images = mongo_db["image_metadata"].distinct("scryfall_id")
            excluded_ids = list(completed_images)

        # Also exclude active image claims
        active_claims = mongo_db["active_image_claims"].find({}, {"_id": 1})
        locked_ids = [doc["_id"] for doc in active_claims]
        excluded_ids.extend(locked_ids)

        card = find_next_prioritized_card(mongo_db, "card_prints", "id", excluded_ids)
        if not card:
            return jsonify({"job_id": None, "message": "No cards need image downloading"}), 200

        scryfall_id = card["id"]
        oracle_id = card.get("oracle_id")

        # Lock the card image job
        try:
            mongo_db["active_image_claims"].insert_one({
                "_id": scryfall_id,
                "claimed_by": worker_id,
                "claimed_at": now
            })
        except pymongo.errors.DuplicateKeyError:
            return jsonify({"job_id": None, "message": "Race condition on claim, retry"}), 200

        # Retrieve image URLs
        image_jobs = []
        target_sizes = ["normal", "large", "art_crop"]
        
        raw_card = card.get("raw", {})
        image_uris = raw_card.get("image_uris") or card.get("image_uris") or {}
        card_faces = raw_card.get("card_faces") or card.get("card_faces") or []
        
        if image_uris:
            for size in target_sizes:
                if size in image_uris:
                    image_jobs.append({
                        "size": size,
                        "face_index": 0,
                        "url": image_uris[size]
                    })
        elif card_faces:
            for face_idx, face in enumerate(card_faces):
                face_uris = face.get("image_uris", {})
                if face_uris:
                    for size in target_sizes:
                        if size in face_uris:
                            image_jobs.append({
                                "size": size,
                                "face_index": face_idx,
                                "url": face_uris[size]
                            })

        # Calculate remaining card image downloads
        completed_count = len(mongo_db["image_metadata"].distinct("scryfall_id"))
        total_cards = mongo_db["card_prints"].count_documents({})
        remaining = max(0, total_cards - completed_count)

        return jsonify({
            "job_id": scryfall_id,
            "scryfall_id": scryfall_id,
            "oracle_id": oracle_id,
            "card_name": card.get("name"),
            "image_jobs": image_jobs,
            "remaining": remaining
        })

    except Exception as e:
        print(f"Error claiming image job: {e}")
        return jsonify({"job_id": None, "error": str(e)}), 500

@app.route("/jobs/complete_image/<scryfall_id>", methods=["POST"])
def complete_image_job(scryfall_id):
    mongo_db = get_db()
    now = datetime.datetime.now(datetime.timezone.utc)
    
    metadata_raw = request.form.get("metadata")
    if not metadata_raw:
        return jsonify({"error": "Missing 'metadata' parameter"}), 400
    
    try:
        metadata_dict = json.loads(metadata_raw)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON in metadata: {e}"}), 400

    claim = mongo_db["active_image_claims"].find_one({"_id": scryfall_id})
    if not claim:
        return jsonify({"error": f"No active claim found for card images: {scryfall_id}"}), 404

    card = mongo_db["card_prints"].find_one({"id": scryfall_id})
    if not card:
        return jsonify({"error": f"Card not found in database: {scryfall_id}"}), 404

    oracle_id = card.get("oracle_id")
    card_name = card.get("name")

    saved_records = []
    try:
        for file_key, file_obj in request.files.items():
            r_idx = file_key.rfind("_")
            if r_idx == -1:
                continue
            size = file_key[:r_idx]
            face_idx_str = file_key[r_idx+1:]
            try:
                face_idx = int(face_idx_str)
            except ValueError:
                continue
            
            raw_card = card.get("raw", {})
            is_multifaced = bool(raw_card.get("card_faces") or card.get("card_faces"))
            if is_multifaced:
                filename = f"{scryfall_id}_{face_idx}.jpg"
            else:
                filename = f"{scryfall_id}.jpg"
            
            dest_dir = os.path.join("data", "images", size)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)
            
            file_obj.save(dest_path)
            actual_size = os.path.getsize(dest_path)
            
            job_meta = metadata_dict.get(file_key, {})
            source_url = job_meta.get("source_url", "")
            
            record = {
                "scryfall_id": scryfall_id,
                "oracle_id": oracle_id,
                "name": card_name,
                "size": size,
                "face_index": face_idx,
                "local_path": f"data/images/{size}/{filename}",
                "source_url": source_url,
                "file_size": actual_size,
                "downloaded_at": now
            }
            
            mongo_db["image_metadata"].update_one(
                {"scryfall_id": scryfall_id, "size": size, "face_index": face_idx},
                {"$set": record},
                upsert=True
            )
            saved_records.append({
                "size": size,
                "face_index": face_idx,
                "local_path": record["local_path"]
            })
            
        mongo_db["active_image_claims"].delete_one({"_id": scryfall_id})
        
        return jsonify({
            "status": "completed",
            "scryfall_id": scryfall_id,
            "saved": saved_records
        })
        
    except Exception as e:
        print(f"Error saving image files: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/jobs/fail_image/<scryfall_id>", methods=["POST"])
def fail_image_job(scryfall_id):
    mongo_db = get_db()
    try:
        mongo_db["active_image_claims"].delete_one({"_id": scryfall_id})
        return jsonify({"status": "failed_recorded", "scryfall_id": scryfall_id})
    except Exception as e:
        print(f"Error failing image job {scryfall_id}: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monolith Job Controller Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to run server on")
    args = parser.parse_args()

    print(f"Starting Monolith Job Controller on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
