#!/usr/bin/env python3
"""
dominion_generate_embeddings.py — Neural Vector Embedding & Similarity Precomputer for Dominion.

Extracts all 819 canonical Dominion cards, compiles rich context (name, card kinds, cost,
rules text across editions, and official Donald X. Vaccarino rulings), generates 4096-dimensional
embeddings via Ollama ('qwen3-embedding:8b'), stores vectors into 'avascry_dominion.embeddings_dominion',
and precomputes top-11 (prime number) related cards into 'avascry_dominion.similar_cards' and
enriches 'avascry_dominion.cards.related_cards'.

Usage:
    python scripts/dominion_generate_embeddings.py
    python scripts/dominion_generate_embeddings.py --force
"""

import sys
import os
import time
import json
import hashlib
import argparse
import urllib.request
import numpy as np
import pymongo
from typing import List, Dict, Any, Optional

# Ensure repository root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mtgabyss.dominion_router import get_dominion_db

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
EMBEDDING_MODEL = os.environ.get("DOMINION_EMBEDDING_MODEL", "qwen3-embedding:8b")


def normalize_whitespace(text: Optional[str]) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    return " ".join(line for line in lines if line)


def build_card_context_text(card: Dict[str, Any], versions: List[Dict[str, Any]], rulings: List[Dict[str, Any]]) -> str:
    name = card.get("name") or ""
    kinds = ", ".join(card.get("card_kinds", []))
    
    cost_str = ""
    rules_texts = []
    for v in versions:
        c = v.get("cost") or {}
        coins = c.get("coins", 0)
        debt = c.get("debt", 0)
        potion = c.get("potion", False)
        parts = []
        if coins:
            parts.append(f"{coins} Coins")
        if debt:
            parts.append(f"{debt} Debt")
        if potion:
            parts.append("1 Potion")
        if not parts:
            parts.append("0 Coins")
        cost_str = " + ".join(parts)
        
        rt = normalize_whitespace(v.get("printed_rules_text"))
        if rt and rt not in rules_texts:
            rules_texts.append(rt)

    rulings_texts = []
    for r in rulings[:5]:
        q = normalize_whitespace(r.get("question"))
        a = normalize_whitespace(r.get("answer"))
        if q or a:
            rulings_texts.append(f"FAQ: {q} Answer: {a}")

    parts = [
        f"Card: {name}",
        f"Types: {kinds}" if kinds else "",
        f"Cost: {cost_str}" if cost_str else "",
        f"Rules: {' | '.join(rules_texts)}" if rules_texts else "",
        f"Rulings: {' | '.join(rulings_texts)}" if rulings_texts else ""
    ]
    return " | ".join(p for p in parts if p)


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def call_ollama_embeddings_batch(texts: List[str], model: str = EMBEDDING_MODEL) -> List[List[float]]:
    url = f"{OLLAMA_URL}/api/embed"
    payload = {
        "model": model,
        "input": texts
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("embeddings", [])
    except urllib.error.HTTPError:
        # Fallback to single /api/embeddings endpoint if /api/embed batch is not supported
        results = []
        fallback_url = f"{OLLAMA_URL}/api/embeddings"
        for t in texts:
            fb_payload = json.dumps({"model": model, "prompt": t}).encode("utf-8")
            fb_req = urllib.request.Request(fallback_url, data=fb_payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(fb_req, timeout=60) as fb_resp:
                fb_body = json.loads(fb_resp.read().decode("utf-8"))
                results.append(fb_body.get("embedding", []))
        return results


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings & top-11 similarity graph for Dominion cards.")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for Ollama embeddings")
    parser.add_argument("--force", action="store_true", help="Force re-generation of all embeddings")
    parser.add_argument("--top-k", type=int, default=11, help="Top-K similar cards to precompute (default 11, prime)")
    args = parser.parse_args()

    db = get_dominion_db()
    cards_coll = db["cards"]
    versions_coll = db["card_versions"]
    rulings_coll = db["rulings"]
    embeddings_coll = db["embeddings_dominion"]
    similar_coll = db["similar_cards"]

    # Ensure indexes
    embeddings_coll.create_index([("slug", pymongo.ASCENDING)], unique=True)
    similar_coll.create_index([("slug", pymongo.ASCENDING)], unique=True)

    print("=== AvaScry Dominion Neural Vector Pipeline ===")
    all_cards = list(cards_coll.find({}).sort("slug", 1))
    print(f"Total canonical cards: {len(all_cards)}")

    # Pre-fetch versions and rulings for fast assembly
    all_versions = list(versions_coll.find({}))
    versions_by_card = {}
    for v in all_versions:
        cid = v.get("card_id")
        if cid:
            versions_by_card.setdefault(cid, []).append(v)

    all_rulings = list(rulings_coll.find({}))
    rulings_by_card = {}
    for r in all_rulings:
        cid = r.get("card_id")
        if cid:
            rulings_by_card.setdefault(cid, []).append(r)

    # Compile card contexts
    items_to_process = []
    slug_to_context = {}

    for c in all_cards:
        slug = c.get("slug")
        if not slug:
            continue
        c_versions = versions_by_card.get(f"card:{slug}", [])
        c_rulings = rulings_by_card.get(f"card:{slug}", [])
        ctx = build_card_context_text(c, c_versions, c_rulings)
        slug_to_context[slug] = ctx
        c_hash = compute_content_hash(ctx)

        existing = embeddings_coll.find_one({"slug": slug}, {"content_hash": 1})
        if args.force or not existing or existing.get("content_hash") != c_hash:
            items_to_process.append({
                "slug": slug,
                "name": c.get("name"),
                "context_text": ctx,
                "content_hash": c_hash,
                "card_kinds": c.get("card_kinds", [])
            })

    print(f"Cards needing embeddings: {len(items_to_process)} / {len(all_cards)}")

    # Generate embeddings in batches
    if items_to_process:
        start_time = time.time()
        for i in range(0, len(items_to_process), args.batch_size):
            batch = items_to_process[i:i + args.batch_size]
            texts = [b["context_text"] for b in batch]
            print(f"Embedding batch {i + 1} to {min(i + len(batch), len(items_to_process))} of {len(items_to_process)}...")
            
            emb_vectors = call_ollama_embeddings_batch(texts, model=EMBEDDING_MODEL)
            if len(emb_vectors) != len(batch):
                raise RuntimeError(f"Mismatch: expected {len(batch)} embeddings, got {len(emb_vectors)}")

            bulk_ops = []
            for item, vec in zip(batch, emb_vectors):
                bulk_ops.append(
                    pymongo.UpdateOne(
                        {"slug": item["slug"]},
                        {
                            "$set": {
                                "slug": item["slug"],
                                "name": item["name"],
                                "model": EMBEDDING_MODEL,
                                "dimensions": len(vec),
                                "embedding": vec,
                                "context_text": item["context_text"],
                                "content_hash": item["content_hash"],
                                "card_kinds": item["card_kinds"],
                                "updated_at": time.time()
                            }
                        },
                        upsert=True
                    )
                )
            if bulk_ops:
                embeddings_coll.bulk_write(bulk_ops)
        elapsed = time.time() - start_time
        print(f"Embeddings generated in {elapsed:.2f}s")
    else:
        print("All card embeddings are up to date.")

    # --- Precompute Top-11 Similarity Matrix ---
    print("\n--- Computing Top-11 Similarity Graph ---")
    all_emb_docs = list(embeddings_coll.find({"embedding": {"$exists": True, "$ne": []}}, {"slug": 1, "name": 1, "embedding": 1}))
    total_embedded = len(all_emb_docs)
    print(f"Loaded {total_embedded} embeddings from MongoDB.")

    if total_embedded == 0:
        print("No embeddings found. Exiting.")
        return

    # Build matrix
    slugs = [d["slug"] for d in all_emb_docs]
    names = [d.get("name") or d["slug"] for d in all_emb_docs]
    matrix = np.array([d["embedding"] for d in all_emb_docs], dtype=np.float32)

    # L2 normalize
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    norm_matrix = matrix / norms

    # Cosine similarity
    print("Computing dot-product cosine similarity matrix...")
    sim_matrix = np.dot(norm_matrix, norm_matrix.T)

    # Pre-fetch card metadata for enriched cards.related_cards
    card_meta_map = {}
    for c in all_cards:
        slug = c.get("slug")
        c_versions = versions_by_card.get(f"card:{slug}", [])
        cost = c_versions[0].get("cost", {}) if c_versions else {}
        card_meta_map[slug] = {
            "name": c.get("name"),
            "slug": slug,
            "cost": cost,
            "card_kinds": c.get("card_kinds", []),
            "image_url": f"https://dominion.avascry.com/images/{slug}.jpg"
        }

    k = min(args.top_k, total_embedded - 1)
    similar_bulk_ops = []
    card_update_bulk_ops = []

    print(f"Extracting top {k} nearest neighbors per card...")
    for idx, slug in enumerate(slugs):
        sim_scores = sim_matrix[idx]
        # Sort descending, skipping self at rank 0
        top_indices = np.argsort(sim_scores)[::-1]
        top_indices = [i for i in top_indices if i != idx][:k]

        similar_cards = []
        related_for_card_doc = []
        for rank, neighbor_idx in enumerate(top_indices, start=1):
            n_slug = slugs[neighbor_idx]
            score = float(sim_scores[neighbor_idx])
            meta = card_meta_map.get(n_slug, {})
            sim_item = {
                "rank": rank,
                "slug": n_slug,
                "name": names[neighbor_idx],
                "score": round(score, 6),
                "cost": meta.get("cost", {}),
                "card_kinds": meta.get("card_kinds", []),
                "image_url": meta.get("image_url", f"https://dominion.avascry.com/images/{n_slug}.jpg")
            }
            similar_cards.append(sim_item)
            related_for_card_doc.append(sim_item)

        similar_bulk_ops.append(
            pymongo.UpdateOne(
                {"slug": slug},
                {
                    "$set": {
                        "slug": slug,
                        "name": names[idx],
                        "model": EMBEDDING_MODEL,
                        "top_k": k,
                        "similar": similar_cards,
                        "updated_at": time.time()
                    }
                },
                upsert=True
            )
        )

        card_update_bulk_ops.append(
            pymongo.UpdateOne(
                {"slug": slug},
                {
                    "$set": {
                        "related_cards": related_for_card_doc
                    }
                }
            )
        )

    if similar_bulk_ops:
        similar_coll.bulk_write(similar_bulk_ops)
        print(f"Wrote {len(similar_bulk_ops)} similarity graph records to 'avascry_dominion.similar_cards'.")
    if card_update_bulk_ops:
        cards_coll.bulk_write(card_update_bulk_ops)
        print(f"Updated {len(card_update_bulk_ops)} card records with related_cards in 'avascry_dominion.cards'.")

    print("\n[SUCCESS] Dominion embeddings & top-11 similarity graph precomputation complete!")


if __name__ == "__main__":
    main()
