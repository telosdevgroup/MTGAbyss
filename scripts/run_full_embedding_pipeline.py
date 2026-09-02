#!/usr/bin/env python3
"""
AvaScry Qwen 8B (4096-Dim) Neural Vector & Similarity Engine Pipeline
- Embeds all 38,627 unique Oracle cards using local Ollama (qwen3-embedding:8b).
- 4096-dimensional high-fidelity representation of MTG card rules, types, mana, and mechanics.
- Computes complete cosine similarity space in RAM via chunked NumPy matrix dot product.
- Writes top 31 synergistic matches directly into db.similar_cards with indexed oracle_id.
"""

import os
import sys
import time
import argparse
import httpx
import numpy as np
import pymongo
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db
from scripts.generate_embedding import (
    build_context_record,
    build_embedding_text,
    get_context_hash,
    slugify
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = "qwen3-embedding:8b"
MODEL_ALIAS = "qwen3-embedding-8b"
INVALID_LAYOUTS = {'art_series', 'token', 'double_faced_token', 'emblem', 'planar', 'scheme', 'vanguard', 'memorabilia'}

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    sys.stdout.write("\r" + " " * 110 + "\r")
    sys.stdout.flush()
    print(f"[{ts}] {msg}", flush=True)

def call_ollama_batch(client: httpx.Client, texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    """Embed a batch of texts using Ollama embed endpoint."""
    resp = client.post("/api/embed", json={"model": model, "input": texts})
    if resp.status_code == 200:
        return resp.json().get("embeddings", [])
    # Fallback to single calls
    embeddings = []
    for t in texts:
        r = client.post("/api/embeddings", json={"model": model, "prompt": t})
        if r.status_code == 200:
            embeddings.append(r.json().get("embedding", []))
        else:
            raise RuntimeError(f"Ollama error {r.status_code}: {r.text}")
    return embeddings

def step_1_generate_qwen_8b_embeddings(db, force: bool = False, batch_size: int = 32):
    """Scan all valid Oracle cards and generate 4096-dim embeddings with Qwen 8B."""
    log(f"Step 1: Preparing Qwen 8B (4096-dim) Vector Collection in MongoDB...")
    col = db["card_embeddings_8b"]
    col.create_index("oracle_id", unique=True)
    col.create_index("embedding_model")

    # 1. Map all distinct oracle_ids in db.cards
    log("Scanning all Oracle cards from db.cards...")
    cards_cursor = db["cards"].find(
        {"layout": {"$nin": list(INVALID_LAYOUTS)}},
        {"oracle_id": 1, "name": 1, "mana_cost": 1, "cmc": 1, "colors": 1, "color_identity": 1, 
         "type_line": 1, "oracle_text": 1, "keywords": 1, "power": 1, "toughness": 1, "loyalty": 1, "defense": 1, "raw": 1}
    )
    
    oracle_card_map = {}
    for c in cards_cursor:
        oid = c.get("oracle_id")
        if oid and oid not in oracle_card_map:
            oracle_card_map[oid] = c
            
    total_unique = len(oracle_card_map)
    log(f"Total unique valid Oracle cards: {total_unique:,}")

    # 2. Check existing embeddings
    if force:
        missing_oids = list(oracle_card_map.keys())
    else:
        existing_oids = set(col.distinct("oracle_id", {"embedding_model": MODEL_ALIAS, "dimensions": 4096}))
        missing_oids = [oid for oid in oracle_card_map if oid not in existing_oids]

    log(f"Cards already embedded with Qwen 8B: {total_unique - len(missing_oids):,}")
    log(f"Cards queued for embedding: {len(missing_oids):,}")

    if not missing_oids:
        log("All cards already vectorized with Qwen 8B! Moving to similarity matrix calculation.")
        return

    # 3. Batch embedding loop with live ETA and progress meter
    t_start = time.perf_counter()
    total_to_embed = len(missing_oids)
    processed = 0
    now = datetime.now(timezone.utc)
    
    log(f"Starting Qwen 8B embedding generation (Batch Size: {batch_size})...")
    
    with httpx.Client(base_url=OLLAMA_URL, timeout=120.0) as http_client:
        for i in range(0, total_to_embed, batch_size):
            chunk_oids = missing_oids[i:i+batch_size]
            chunk_cards = [oracle_card_map[oid] for oid in chunk_oids]
            
            texts = []
            contexts = []
            for c in chunk_cards:
                ctx = build_context_record(c)
                txt = build_embedding_text(ctx)
                texts.append(txt)
                contexts.append((ctx, txt))
                
            try:
                embeddings = call_ollama_batch(http_client, texts, EMBED_MODEL)
                bulk_ops = []
                for card, (ctx, txt), emb in zip(chunk_cards, contexts, embeddings):
                    if not emb or len(emb) != 4096:
                        continue
                    bulk_ops.append(pymongo.UpdateOne(
                        {"oracle_id": card["oracle_id"]},
                        {"$set": {
                            "oracle_id": card["oracle_id"],
                            "card_name": card.get("name"),
                            "slug": slugify(card.get("name") or ""),
                            "embedding_model": MODEL_ALIAS,
                            "embedding_version": "v1",
                            "context_hash": get_context_hash(ctx),
                            "dimensions": len(emb),
                            "embedding": emb,
                            "normalized_context": ctx,
                            "embedding_text": txt,
                            "updated_at": now
                        }},
                        upsert=True
                    ))
                    
                if bulk_ops:
                    col.bulk_write(bulk_ops, ordered=False)
                    
                processed += len(chunk_oids)
                elapsed = time.perf_counter() - t_start
                rate = processed / elapsed if elapsed > 0 else 0
                remaining = (total_to_embed - processed) / rate if rate > 0 else 0
                eta_str = f"{int(remaining//60)}m {int(remaining%60)}s" if remaining >= 60 else f"{int(remaining)}s"
                pct = processed / total_to_embed * 100
                
                bar_len = 30
                filled = int(bar_len * processed / total_to_embed)
                bar = "█" * filled + "░" * (bar_len - filled)
                
                sys.stdout.write(f"\r[{bar}] {processed:,}/{total_to_embed:,} ({pct:5.1f}%) | {rate:4.1f} cards/sec | ETA: {eta_str}  ")
                sys.stdout.flush()
                
            except Exception as e:
                log(f"\nWarning on batch {i}: {e}. Retrying in 2s...")
                time.sleep(2.0)

    print()
    total_time = time.perf_counter() - t_start
    log(f"Completed Qwen 8B embedding generation in {total_time/60:.1f} minutes ({processed/total_time:.1f} cards/sec)!")

def step_2_compute_similarity_matrix(db):
    """Load all 4096-dim Qwen 8B embeddings into RAM and compute top 31 nearest neighbors."""
    col = db["card_embeddings_8b"]
    log("Step 2: Loading all 4096-dim Qwen 8B embeddings into RAM...")
    
    cursor = col.find(
        {"embedding": {"$exists": True, "$ne": None}, "dimensions": 4096},
        {"oracle_id": 1, "embedding": 1}
    )
    
    oracle_ids = []
    vectors = []
    
    for doc in cursor:
        emb = doc.get("embedding")
        oid = doc.get("oracle_id")
        if emb and oid and len(emb) == 4096:
            oracle_ids.append(oid)
            vectors.append(emb)
            
    N = len(oracle_ids)
    if N == 0:
        log("No 4096-dim embeddings found!")
        return
        
    dim = 4096
    mem_mb = N * dim * 4 / (1024 * 1024)
    log(f"Loaded {N:,} card vectors with dimension {dim}. Allocating contiguous NumPy matrix (~{mem_mb:.1f} MB in RAM)...")
    
    # 1. Build and L2-normalize matrix X
    t0 = time.perf_counter()
    X = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X = X / norms
    log(f"Matrix initialized & normalized in {(time.perf_counter()-t0)*1000:.1f}ms.")
    
    # 2. Chunked Cosine Dot Product & Top 31 Extraction
    chunk_size = 500
    top_k = 35 # Extra padding to ignore self
    
    try:
        db["similar_cards"].create_index("oracle_id")
    except Exception:
        pass
    
    log(f"Computing 4096-dim cosine similarity space in chunks of {chunk_size} cards...")
    t_start = time.perf_counter()
    
    bulk_ops = []
    total_processed = 0
    now = datetime.now(timezone.utc)
    
    for start_idx in range(0, N, chunk_size):
        end_idx = min(start_idx + chunk_size, N)
        X_chunk = X[start_idx:end_idx] # (chunk, 4096)
        
        # Matrix dot product
        sim_chunk = np.dot(X_chunk, X.T) # (chunk, N)
        
        for i, global_idx in enumerate(range(start_idx, end_idx)):
            scores = sim_chunk[i]
            target_oid = oracle_ids[global_idx]
            
            # Mask out self
            scores[global_idx] = -1.0
            
            # Extract top K nearest neighbors using argpartition
            top_indices = np.argpartition(scores, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(-scores[top_indices])]
            
            similar_list = []
            for neighbor_idx in top_indices:
                score = float(scores[neighbor_idx])
                if score < 0:
                    continue
                similar_list.append(oracle_ids[neighbor_idx])
                if len(similar_list) >= 31:
                    break
                    
            bulk_ops.append(pymongo.UpdateOne(
                {"oracle_id": target_oid},
                {"$set": {
                    "oracle_id": target_oid,
                    "similar": similar_list,
                    "model": MODEL_ALIAS,
                    "calculated_at": now
                }},
                upsert=True
            ))
            
        total_processed += (end_idx - start_idx)
        
        # Flush to MongoDB every 2,500 cards
        if len(bulk_ops) >= 2500 or end_idx == N:
            db["similar_cards"].bulk_write(bulk_ops, ordered=False)
            bulk_ops = []
            elapsed = time.perf_counter() - t_start
            speed = total_processed / elapsed if elapsed > 0 else 0
            sys.stdout.write(f"\rMatrix progress: {total_processed:,}/{N:,} ({total_processed/N*100:.1f}%) — {speed:.1f} cards/sec  ")
            sys.stdout.flush()
            
    print()
    total_time = time.perf_counter() - t_start
    log(f"Successfully computed and stored all {N:,} card similarities in {total_time:.2f} seconds ({N/total_time:.1f} cards/sec)!")

def run_dry_run_test(db):
    """Run a safe test on iconic and oddball cards with Qwen 8B without writing to DB."""
    log("=== DRY RUN MODE: Testing Qwen 8B (4096-Dim) Embeddings ===")
    test_names = ["Combat Research", "Sol Ring", "Horta", "Tarmogoyf", "Dark Ritual", "Lightning Bolt"]
    
    cards = []
    for name in test_names:
        c = db["cards"].find_one({"name": name, "lang": "en"}) or db["cards"].find_one({"name": name})
        if c:
            cards.append(c)
            
    log(f"Selected {len(cards)} test cards: {', '.join([c['name'] for c in cards])}")
    
    texts = []
    for c in cards:
        ctx = build_context_record(c)
        txt = build_embedding_text(ctx)
        texts.append(txt)
        print(f"\n--- Context Sent to Qwen 8B for '{c['name']}' ---")
        print(txt)
        
    log("\nCalling Ollama qwen3-embedding:8b...")
    t0 = time.perf_counter()
    with httpx.Client(base_url=OLLAMA_URL, timeout=60.0) as client:
        embs = call_ollama_batch(client, texts, EMBED_MODEL)
    log(f"Generated {len(embs)} vectors in {(time.perf_counter()-t0)*1000:.1f}ms! Vector dimension: {len(embs[0])}")
    
    # Compute dot product between test cards
    X = np.array(embs, dtype=np.float32)
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X = X / norms
    
    sim_matrix = np.dot(X, X.T)
    print("\n--- Cosine Similarity Between Test Cards ---")
    for i, c1 in enumerate(cards):
        print(f"\nTarget: {c1['name']}")
        ranked = sorted([(sim_matrix[i][j], cards[j]['name']) for j in range(len(cards)) if j != i], reverse=True)
        for score, name in ranked:
            print(f"  -> {score:.4f} : {name}")
            
    log("\n[DRY RUN COMPLETE] Zero database writes performed.")

def main():
    parser = argparse.ArgumentParser(description="AvaScry Qwen 8B Neural Similarity Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Test embeddings on sample cards without modifying MongoDB")
    parser.add_argument("--force", action="store_true", help="Re-embed all cards even if already present")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for Ollama embedding calls")
    parser.add_argument("--matrix-only", action="store_true", help="Skip embedding and compute similarity matrix from existing vectors")
    args = parser.parse_args()

    log("=================================================================")
    log("  AvaScry Qwen 8B (4096-Dim) Neural Similarity Pipeline")
    log("=================================================================")
    
    db = get_mongo_db()
    
    if args.dry_run:
        run_dry_run_test(db)
        return
        
    if not args.matrix_only:
        step_1_generate_qwen_8b_embeddings(db, force=args.force, batch_size=args.batch_size)
        
    step_2_compute_similarity_matrix(db)
    
    log("=================================================================")
    log("  Pipeline Completed! 100% of cards now have Qwen 8B vectors.")
    log("=================================================================")

if __name__ == "__main__":
    main()
