import os
import sys
import argparse
import datetime
import pymongo
import threading
import time
import subprocess
import concurrent.futures
import multiprocessing

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes
from scripts.generate_embedding import (
    build_context_record,
    build_embedding_text,
    get_context_hash,
    call_ollama_embed,
    call_ollama_embed_batch,
    ensure_embeddings_indexes,
    slugify
)

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

class HeartbeatThread(threading.Thread):
    def __init__(self, db, job_id, interval=10):
        super().__init__()
        self.db = db
        self.job_id = job_id
        self.interval = interval
        self.stop_event = threading.Event()
        self.daemon = True

    def run(self):
        while not self.stop_event.wait(self.interval):
            try:
                now = datetime.datetime.now(datetime.timezone.utc)
                self.db["generation_jobs"].update_one(
                    {"_id": self.job_id, "status": "claimed"},
                    {"$set": {"heartbeat_at": now, "updated_at": now}}
                )
            except Exception:
                pass

    def stop(self):
        self.stop_event.set()

def process_card_embedding(db, card, model, version, mock_mode, worker_id, now, force=False):
    oracle_id = card.get("oracle_id")
    card_name = card.get("name")
    
    if not oracle_id:
        raise ValueError(f"Card '{card_name}' has no oracle_id.")

    normalized_context = build_context_record(card)
    embedding_text = build_embedding_text(normalized_context)
    context_hash = get_context_hash(normalized_context)

    # Check existing embedding to avoid redundant work
    embeddings_col = db["card_embeddings"]
    existing = embeddings_col.find_one({
        "oracle_id": oracle_id,
        "embedding_model": model,
        "embedding_version": version
    })

    if existing and existing.get("context_hash") == context_hash and existing.get("embedding") is not None and not force:
        log(f"Skipping: Embedding for '{card_name}' is up to date (hash matches).")
        return True

    if mock_mode:
        embedding = [0.0] * 768
    else:
        embedding = call_ollama_embed(embedding_text, model)

    dimensions = len(embedding)
    doc = {
        "oracle_id": oracle_id,
        "card_name": card_name,
        "slug": card.get("slug") or slugify(card_name),
        "embedding_model": model,
        "embedding_version": version,
        "context_hash": context_hash,
        "context": normalized_context,
        "embedding": embedding,
        "dimensions": dimensions,
        "updated_at": now
    }

    if existing:
        embeddings_col.update_one(
            {"_id": existing["_id"]},
            {"$set": doc}
        )
        log(f"Updated embedding for '{card_name}' in MongoDB.")
    else:
        doc["created_at"] = now
        embeddings_col.insert_one(doc)
        log(f"Stored embedding for '{card_name}' in MongoDB.")

    return True

def process_card_embeddings_batch(db, cards, model, version, mock_mode, worker_id, now, force=False):
    if not cards:
        return {}

    oracle_ids = []
    card_by_oracle = {}
    for card in cards:
        oracle_id = card.get("oracle_id")
        if oracle_id:
            oracle_ids.append(oracle_id)
            card_by_oracle[oracle_id] = card

    # Bulk fetch existing embeddings
    existing_embeddings = {
        e["oracle_id"]: e 
        for e in db["card_embeddings"].find({
            "oracle_id": {"$in": oracle_ids},
            "embedding_model": model,
            "embedding_version": version
        })
    }

    cards_to_generate = []
    texts_to_generate = []
    results = {}  # oracle_id -> success status

    for card in cards:
        oracle_id = card.get("oracle_id")
        card_name = card.get("name")
        if not oracle_id:
            results[oracle_id] = False
            continue

        normalized_context = build_context_record(card)
        embedding_text = build_embedding_text(normalized_context)
        context_hash = get_context_hash(normalized_context)

        existing = existing_embeddings.get(oracle_id)
        if existing and existing.get("context_hash") == context_hash and existing.get("embedding") is not None and not force:
            log(f"Skipping: Embedding for '{card_name}' is up to date (hash matches).")
            results[oracle_id] = True
            continue

        cards_to_generate.append((card, normalized_context, context_hash))
        texts_to_generate.append(embedding_text)

    # Initialize results for those to generate to True, and update to False if they fail
    for card, _, _ in cards_to_generate:
        results[card["oracle_id"]] = True

    if cards_to_generate:
        embeddings = []
        if mock_mode:
            embeddings = [[0.0] * 768] * len(cards_to_generate)
        else:
            try:
                embeddings = call_ollama_embed_batch(texts_to_generate, model)
            except Exception as e:
                log(f"Batch embedding generation failed: {e}")
                for card, _, _ in cards_to_generate:
                    results[card["oracle_id"]] = False
                raise e

        # Prepare bulk write operations
        bulk_ops = []
        for idx, (card, normalized_context, context_hash) in enumerate(cards_to_generate):
            oracle_id = card["oracle_id"]
            card_name = card["name"]
            
            # Ensure we got back matching number of embeddings
            if idx < len(embeddings):
                embedding = embeddings[idx]
            else:
                log(f"Error: Missing embedding for '{card_name}' in batch response.")
                results[oracle_id] = False
                continue
                
            dimensions = len(embedding)

            existing = existing_embeddings.get(oracle_id)
            doc = {
                "oracle_id": oracle_id,
                "card_name": card_name,
                "slug": card.get("slug") or slugify(card_name),
                "embedding_model": model,
                "embedding_version": version,
                "context_hash": context_hash,
                "context": normalized_context,
                "embedding": embedding,
                "dimensions": dimensions,
                "updated_at": now
            }
            if not existing:
                doc["created_at"] = now

            bulk_ops.append(
                pymongo.UpdateOne(
                    {
                        "oracle_id": oracle_id,
                        "embedding_model": model,
                        "embedding_version": version
                    },
                    {"$set": doc},
                    upsert=True
                )
            )

        if bulk_ops:
            db["card_embeddings"].bulk_write(bulk_ops)
            for card, _, _ in cards_to_generate:
                if results[card["oracle_id"]]:
                    log(f"Saved embedding for '{card['name']}' in MongoDB via bulk write.")

    return results


def run_batch_worker(batch, index, worker_id, model, version, mock_mode, force, completed_counter, remaining_counter, progress_lock):
    try:
        # Re-initialize DB client in the child process to avoid connection pooling issues
        db = get_mongo_db()
        thread_worker_id = f"{worker_id}-w{index}"
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        oracle_ids = [job.get("oracle_id") for job in batch if job.get("oracle_id")]

        with progress_lock:
            log(f"[{completed_counter.value} completed / {remaining_counter.value} left] Worker {index}: Starting batch of {len(batch)} cards...")

        # Bulk query card documents from cards collection
        cards_cursor = db["cards"].find({"oracle_id": {"$in": oracle_ids}})
        cards_by_oracle = {c["oracle_id"]: c for c in cards_cursor}

        cards_to_process = []
        valid_jobs = []

        for job in batch:
            oid = job.get("oracle_id")
            card_doc = cards_by_oracle.get(oid)
            if not card_doc:
                db["generation_jobs"].update_one(
                    {"_id": job["_id"]},
                    {"$set": {"status": "failed", "error": "Card not found in database", "updated_at": now_utc}}
                )
                with progress_lock:
                    remaining_counter.value -= 1
            else:
                cards_to_process.append(card_doc)
                valid_jobs.append(job)

        if not cards_to_process:
            return

        # Start heartbeats for all valid jobs in the batch
        heartbeat_threads = []
        for job in valid_jobs:
            hb = HeartbeatThread(db, job["_id"])
            hb.start()
            heartbeat_threads.append(hb)

        success_results = {}
        error_msg = None
        try:
            success_results = process_card_embeddings_batch(
                db, cards_to_process, model, version, 
                mock_mode, thread_worker_id, now_utc, force=force
            )
        except Exception as e:
            error_msg = str(e)

        # Stop all heartbeats
        for hb in heartbeat_threads:
            hb.stop()
        for hb in heartbeat_threads:
            hb.join(timeout=0.2)

        # Bulk write job status updates
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        bulk_job_updates = []
        batch_completed = 0
        batch_remaining_decrement = 0

        for job in valid_jobs:
            oid = job.get("oracle_id")
            success = success_results.get(oid, False) if not error_msg else False

            if success:
                bulk_job_updates.append(
                    pymongo.UpdateOne(
                        {"_id": job["_id"]},
                        {"$set": {"status": "completed", "error": None, "updated_at": now_utc}}
                    )
                )
                batch_completed += 1
            else:
                attempts = job.get("attempts", 0) + 1
                max_attempts = job.get("max_attempts", 3)
                new_status = "pending" if attempts < max_attempts else "failed"
                bulk_job_updates.append(
                    pymongo.UpdateOne(
                        {"_id": job["_id"]},
                        {
                            "$set": {
                                "status": new_status,
                                "attempts": attempts,
                                "error": error_msg or "Unknown embedding generation failure",
                                "updated_at": now_utc
                            }
                        }
                    )
                )
            batch_remaining_decrement += 1

        if bulk_job_updates:
            db["generation_jobs"].bulk_write(bulk_job_updates)

        with progress_lock:
            completed_counter.value += batch_completed
            remaining_counter.value -= batch_remaining_decrement
            log(f"[{completed_counter.value} completed / {remaining_counter.value} left] Worker {index}: Finished batch of {len(batch)} cards.")
    except Exception as e:
        log(f"Worker {index} encountered error: {e}")



def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Worker to claim and generate card embeddings.")
    parser.add_argument("--worker-id", type=str, default="local-worker-1", help="Identifier for this worker.")
    parser.add_argument("--model", type=str, default="qwen3-embedding:0.6b", help="Embedding model name.")
    parser.add_argument("--version", type=str, default="card_context_v1", help="Embedding pipeline version.")
    parser.add_argument("--mock", action="store_true", default=True, help="Force mock generation without calling Ollama.")
    parser.add_argument("--no-mock", dest="mock", action="store_false", help="Disable mock generation (call Ollama).")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of jobs to process.")
    parser.add_argument("--force", action="store_true", help="Force regeneration of embeddings (bypass context hash matching).")
    parser.add_argument("--random", action="store_true", help="Pull a random pending job instead of the priority queue order.")
    parser.add_argument("--card", type=str, default=None, help="Generate for a specific card directly, bypassing the queue.")
    parser.add_argument("--workers", type=int, default=1, help="Number of concurrent workers to spawn.")
    parser.add_argument("--skip-scan", action="store_true", help="Bypass the database auto-scan phase.")
    parser.add_argument("--batch-size", type=int, default=31, help="Number of cards to process in a batch per worker.")
    args = parser.parse_args()

    db = get_mongo_db()
    ensure_indexes(db)
    ensure_embeddings_indexes(db)

    now = datetime.datetime.now(datetime.timezone.utc)

    if args.card:
        card = db["cards"].find_one({
            "$or": [
                {"name": args.card},
                {"slug": slugify(args.card)}
            ]
        })
        if not card:
            log(f"Card not found: '{args.card}'")
            sys.exit(1)
            
        log(f"Generating embedding directly for card '{card['name']}' using model '{args.model}' (mock: {args.mock})...")
        try:
            process_card_embedding(db, card, args.model, args.version, args.mock, args.worker_id, now, force=args.force)
            log("Successfully processed embedding.")
        except Exception as e:
            log(f"Error processing card: {e}")
            sys.exit(1)
        return

    if args.skip_scan:
        log("Skipping database auto-scan as requested.")
    else:
        # Check if there are already pending jobs in the queue
        pending_count = db["generation_jobs"].count_documents({
            "job_type": "generate_embedding",
            "status": "pending"
        })

        if pending_count > 0 and not args.force:
            log(f"Queue already has {pending_count} pending embedding jobs. Skipping database auto-scan.")
        else:
            # Clean up old pending embedding jobs from the queue first
            log("Cleaning up old pending embedding jobs from the queue...")
            db["generation_jobs"].delete_many({
                "job_type": "generate_embedding",
                "status": "pending"
            })

            # Auto-scan database to enqueue missing card embedding jobs
            log("Scanning database for cards missing embeddings...")
            cards_cursor = db["cards"].find({})
            
            enqueued_count = 0
            skipped_count = 0
            
            for card in cards_cursor:
                oracle_id = card.get("oracle_id")
                card_slug = card.get("slug")
                card_name = card.get("name")
                
                if not oracle_id or not card_slug or not card_name:
                    continue
                    
                # Check if embedding already exists or is already claimed/completed
                if not args.force:
                    existing_job = db["generation_jobs"].find_one({
                        "oracle_id": oracle_id,
                        "job_type": "generate_embedding",
                        "status": {"$in": ["claimed", "completed"]}
                    })
                    existing_embedding = db["card_embeddings"].find_one({
                        "oracle_id": oracle_id,
                        "embedding_model": args.model,
                        "embedding_version": args.version,
                        "embedding": {"$exists": True, "$ne": None}
                    })
                    if existing_job or existing_embedding:
                        skipped_count += 1
                        continue
                        
                # Build embedding job document
                job_doc = {
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
                    job_doc,
                    upsert=True
                )
                enqueued_count += 1
                
            if enqueued_count > 0:
                log(f"Auto-scan complete: Enqueued {enqueued_count} new embedding jobs (skipped {skipped_count} existing/queued).")
            else:
                log(f"Auto-scan complete: All cards have up-to-date embeddings (skipped {skipped_count}).")

    if args.workers > 1:
        log(f"Orchestrator: Starting ProcessPoolExecutor with {args.workers} workers...")
        
        # Load all pending jobs
        pending_jobs = list(db["generation_jobs"].find({
            "status": "pending",
            "job_type": "generate_embedding"
        }).sort([("priority", -1), ("created_at", 1)]))

        if args.random:
            import random
            random.shuffle(pending_jobs)

        if args.limit is not None:
            pending_jobs = pending_jobs[:args.limit]

        if not pending_jobs:
            log("No pending embedding jobs found. Orchestrator exiting.")
            return

        log(f"Orchestrator: Found {len(pending_jobs)} pending jobs. Claiming them in bulk...")
        # Bulk claim jobs
        db["generation_jobs"].update_many(
            {"_id": {"$in": [job["_id"] for job in pending_jobs]}},
            {
                "$set": {
                    "status": "claimed",
                    "claimed_by": args.worker_id,
                    "claimed_at": datetime.datetime.now(datetime.timezone.utc),
                    "heartbeat_at": datetime.datetime.now(datetime.timezone.utc),
                    "updated_at": datetime.datetime.now(datetime.timezone.utc)
                }
            }
        )

        # Chunk pending jobs into batches
        batch_size = args.batch_size
        job_batches = [pending_jobs[i:i + batch_size] for i in range(0, len(pending_jobs), batch_size)]

        # Multiprocessing Manager for shared counters
        manager = multiprocessing.Manager()
        completed_count = db["generation_jobs"].count_documents({
            "status": "completed",
            "job_type": "generate_embedding"
        })
        completed_counter = manager.Value('i', completed_count)
        remaining_counter = manager.Value('i', len(pending_jobs))
        progress_lock = manager.Lock()

        # Submit batches to ProcessPoolExecutor
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=args.workers)
        futures = []
        try:
            for idx, batch in enumerate(job_batches):
                futures.append(executor.submit(
                    run_batch_worker, 
                    batch, 
                    idx + 1, 
                    args.worker_id, 
                    args.model, 
                    args.version, 
                    args.mock, 
                    args.force, 
                    completed_counter, 
                    remaining_counter, 
                    progress_lock
                ))
            
            # Wait for all futures to complete
            concurrent.futures.wait(futures)
        except KeyboardInterrupt:
            log("Orchestrator: Received KeyboardInterrupt. Shutting down process pool...")
            for f in futures:
                f.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            
            log("Orchestrator: Resetting unfinished claimed jobs back to pending...")
            db["generation_jobs"].update_many(
                {
                    "_id": {"$in": [job["_id"] for job in pending_jobs]},
                    "status": "claimed"
                },
                {
                    "$set": {
                        "status": "pending",
                        "claimed_by": None,
                        "claimed_at": None,
                        "heartbeat_at": None,
                        "updated_at": datetime.datetime.now(datetime.timezone.utc)
                    }
                }
            )
            log("Orchestrator: All workers stopped and unfinished jobs reset.")
        finally:
            manager.shutdown()
        return

    processed = 0
    log(f"Worker '{args.worker_id}' started. Mock mode: {args.mock} (force: {args.force}, random: {args.random})")

    while True:
        if args.limit and processed >= args.limit:
            break

        now = datetime.datetime.now(datetime.timezone.utc)
        
        job = None
        if args.random:
            pipeline = [
                {"$match": {"status": "pending", "job_type": "generate_embedding"}},
                {"$sample": {"size": 1}}
            ]
            random_candidates = list(db["generation_jobs"].aggregate(pipeline))
            if random_candidates:
                candidate = random_candidates[0]
                job = db["generation_jobs"].find_one_and_update(
                    {"_id": candidate["_id"], "status": "pending"},
                    {
                        "$set": {
                            "status": "claimed",
                            "claimed_by": args.worker_id,
                            "claimed_at": now,
                            "heartbeat_at": now,
                            "updated_at": now
                        }
                    },
                    return_document=pymongo.ReturnDocument.AFTER
                )
        else:
            job = db["generation_jobs"].find_one_and_update(
                {"status": "pending", "job_type": "generate_embedding"},
                {
                    "$set": {
                        "status": "claimed",
                        "claimed_by": args.worker_id,
                        "claimed_at": now,
                        "heartbeat_at": now,
                        "updated_at": now
                    }
                },
                sort=[("priority", -1), ("created_at", 1)],
                return_document=pymongo.ReturnDocument.AFTER
            )

        if not job:
            log("No pending embedding jobs found. Worker exiting.")
            break

        oracle_id = job.get("oracle_id")
        card_name = job.get("card_name")
        embedding_model = job.get("model") or args.model
        embedding_version = job.get("version") or args.version

        completed_count = db["generation_jobs"].count_documents({
            "status": "completed",
            "job_type": "generate_embedding"
        })
        remaining_count = db["generation_jobs"].count_documents({
            "status": "pending",
            "job_type": "generate_embedding"
        })
        log(f"[{completed_count} completed / {remaining_count} left] Generating embedding for '{card_name}' ({embedding_model})")

        card = db["cards"].find_one({"oracle_id": oracle_id})
        if not card:
            db["generation_jobs"].update_one(
                {"_id": job["_id"]},
                {"$set": {"status": "failed", "error": "Card not found in database", "updated_at": now}}
            )
            log(f"Failed: Card details not found for '{card_name}'")
            processed += 1
            continue

        attempts = job.get("attempts", 0) + 1
        db["generation_jobs"].update_one(
            {"_id": job["_id"]},
            {"$set": {"attempts": attempts, "heartbeat_at": now, "updated_at": now}}
        )

        # Start background heartbeat thread
        heartbeat_thread = HeartbeatThread(db, job["_id"])
        heartbeat_thread.start()

        success = False
        error_msg = None

        try:
            success = process_card_embedding(db, card, embedding_model, embedding_version, args.mock, args.worker_id, now, force=args.force)
        except Exception as e:
            error_msg = str(e)
        finally:
            # Stop background heartbeat thread
            heartbeat_thread.stop()
            heartbeat_thread.join(timeout=1.0)

        if success:
            db["generation_jobs"].update_one(
                {"_id": job["_id"]},
                {"$set": {"status": "completed", "error": None, "updated_at": now}}
            )
            log(f"'{card_name}' successful.")
        else:
            max_attempts = job.get("max_attempts", 3)
            new_status = "pending" if attempts < max_attempts else "failed"
            db["generation_jobs"].update_one(
                {"_id": job["_id"]},
                {
                    "$set": {
                        "status": new_status,
                        "error": error_msg or "Unknown embedding generation failure",
                        "updated_at": now
                    }
                }
            )
            log(f"Failed attempt {attempts}/{max_attempts} for '{card_name}'. Status: {new_status}. Error: {error_msg}")

        processed += 1
        print()

    log(f"Worker complete. Processed {processed} jobs.")

if __name__ == "__main__":
    main()
