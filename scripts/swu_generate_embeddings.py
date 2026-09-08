#!/usr/bin/env python3
"""
swu_generate_embeddings.py — Neural Vector Embedding & Similarity Precomputer for SWU.

Extracts unique canonical cards from MongoDB ('avascry_swu'), builds rich semantic context,
generates 4096-dimensional embeddings using local Ollama ('qwen3-embedding:8b'),
stores vectors into 'avascry_swu.embeddings_swu', and precomputes the top-10 pairwise
cosine similarity graph into 'avascry_swu.similar_cards'.

Usage:
    python scripts/swu_generate_embeddings.py
    python scripts/swu_generate_embeddings.py --batch-size 32
    python scripts/swu_generate_embeddings.py --force
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

from mtgabyss.swu_router import get_swu_db

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
EMBEDDING_MODEL = os.environ.get("SWU_EMBEDDING_MODEL", "qwen3-embedding:8b")


def normalize_whitespace(text: Optional[str]) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    return " ".join(line for line in lines if line)


def build_card_context_text(card: Dict[str, Any]) -> str:
    title = card.get("title") or card.get("name") or ""
    subtitle = card.get("subtitle") or ""
    card_type = card.get("type") or ""
    aspects = card.get("aspects") or []
    traits = card.get("traits") or []
    arenas = card.get("arenas") or []
    cost = card.get("cost")
    power = card.get("power")
    hp = card.get("hp")
    rules_text = normalize_whitespace(card.get("text") or card.get("rules") or "")
    front_text = normalize_whitespace(card.get("front_text") or "")
    back_text = normalize_whitespace(card.get("back_text") or "")
    deploy_box = normalize_whitespace(card.get("deploy_box") or "")
    epic_action = normalize_whitespace(card.get("epic_action") or "")

    parts = [
        f"Game: Star Wars Unlimited",
        f"Card: {title}",
    ]
    if subtitle:
        parts.append(f"Subtitle: {subtitle}")
    if card_type:
        parts.append(f"Type: {card_type}")
    if aspects:
        parts.append(f"Aspects: {', '.join(aspects)}")
    if traits:
        parts.append(f"Traits: {', '.join(traits)}")
    if arenas:
        parts.append(f"Arenas: {', '.join(arenas)}")
    if cost is not None:
        parts.append(f"Cost: {cost}")
    if power is not None:
        parts.append(f"Power: {power}")
    if hp is not None:
        parts.append(f"HP: {hp}")
    if rules_text:
        parts.append(f"Rules Text: {rules_text}")
    if front_text and front_text != rules_text:
        parts.append(f"Front Text: {front_text}")
    if back_text:
        parts.append(f"Back Text: {back_text}")
    if deploy_box:
        parts.append(f"Deploy Ability: {deploy_box}")
    if epic_action:
        parts.append(f"Epic Action: {epic_action}")

    return "\n".join(parts)


def get_context_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def call_ollama_batch_embed(texts: List[str], model: str = EMBEDDING_MODEL) -> List[List[float]]:
    url = f"{OLLAMA_URL}/api/embed"
    payload = {
        "model": model,
        "input": texts,
        "keep_alive": "1h"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        embeddings = data.get("embeddings")
        if not embeddings:
            raise ValueError(f"No embeddings returned from Ollama: {data}")
        return embeddings


def main():
    parser = argparse.ArgumentParser(description="Generate SWU 4096-dim card embeddings and precompute similar cards")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size (default: 32)")
    parser.add_argument("--force", action="store_true", help="Force re-embedding even if cached")
    parser.add_argument("--top-k", type=int, default=10, help="Number of similar cards to store per card (default: 10)")
    args = parser.parse_args()

    db = get_swu_db()
    print(f"[*] Connected to MongoDB: {db.name}")

    # Ensure indexes
    db.embeddings_swu.create_index("slug", unique=True)
    db.embeddings_swu.create_index("title")
    db.embeddings_swu.create_index("context_hash")
    db.similar_cards.create_index("slug", unique=True)
    db.similar_cards.create_index("title")

    # Step 1: Collect unique canonical cards across SWU
    print("[*] Grouping canonical cards by (title, subtitle)...")
    cards_cursor = db.cards.find({}, {
        "_id": 0, "slug": 1, "title": 1, "name": 1, "subtitle": 1, "type": 1,
        "aspects": 1, "traits": 1, "arenas": 1, "cost": 1, "power": 1, "hp": 1,
        "text": 1, "rules": 1, "front_text": 1, "back_text": 1, "deploy_box": 1,
        "epic_action": 1, "variant_type": 1, "card_number": 1, "number": 1,
        "art_front": 1, "front_image": 1
    }).sort([("variant_type", -1), ("card_number", 1)])

    canonical_map: Dict[str, Dict[str, Any]] = {}
    family_slugs: Dict[str, List[str]] = {}

    for c in cards_cursor:
        t = (c.get("title") or c.get("name") or "").strip()
        sub = (c.get("subtitle") or "").strip()
        if not t:
            continue
        c["title"] = t
        c["subtitle"] = sub
        key = f"{t.lower()}::{sub.lower()}"
        slug = c.get("slug")

        if key not in canonical_map:
            canonical_map[key] = c
            family_slugs[key] = [slug]
        else:
            # Prefer Normal or base variant as canonical representation
            existing_var = str(canonical_map[key].get("variant_type", "")).lower()
            new_var = str(c.get("variant_type", "")).lower()
            if new_var in ("normal", "none", "") and existing_var not in ("normal", "none", ""):
                canonical_map[key] = c
            family_slugs[key].append(slug)

    unique_cards = list(canonical_map.values())
    print(f"[+] Identified {len(unique_cards)} unique canonical cards across SWU.")

    # Step 2: Check existing embeddings
    existing_hashes = {}
    if not args.force:
        for doc in db.embeddings_swu.find({"model": EMBEDDING_MODEL}, {"slug": 1, "context_hash": 1}):
            existing_hashes[doc["slug"]] = doc.get("context_hash")

    cards_to_embed = []
    card_contexts = []
    card_hashes = []

    for c in unique_cards:
        slug = c["slug"]
        context_text = build_card_context_text(c)
        chash = get_context_hash(context_text)
        if args.force or slug not in existing_hashes or existing_hashes.get(slug) != chash:
            cards_to_embed.append(c)
            card_contexts.append(context_text)
            card_hashes.append(chash)

    print(f"[*] Cards requiring embedding: {len(cards_to_embed)} / {len(unique_cards)} (Cached: {len(unique_cards) - len(cards_to_embed)})")

    # Step 3: Batch embed via Ollama
    batch_size = args.batch_size
    now_ts = time.time()

    if cards_to_embed:
        print(f"[*] Embedding {len(cards_to_embed)} cards using '{EMBEDDING_MODEL}' via Ollama...")
        total_batches = (len(cards_to_embed) + batch_size - 1) // batch_size
        t0 = time.time()

        for b_idx in range(total_batches):
            start = b_idx * batch_size
            end = min(start + batch_size, len(cards_to_embed))
            batch_cards = cards_to_embed[start:end]
            batch_texts = card_contexts[start:end]
            batch_hashes = card_hashes[start:end]

            t_b0 = time.time()
            embeddings = call_ollama_batch_embed(batch_texts, model=EMBEDDING_MODEL)
            t_b1 = time.time()

            ops = []
            for c, text, chash, emb in zip(batch_cards, batch_texts, batch_hashes, embeddings):
                ops.append(
                    pymongo.UpdateOne(
                        {"slug": c["slug"]},
                        {"$set": {
                            "slug": c["slug"],
                            "title": c["title"],
                            "subtitle": c.get("subtitle", ""),
                            "card_type": c.get("type", ""),
                            "aspects": c.get("aspects", []),
                            "traits": c.get("traits", []),
                            "embedding": emb,
                            "dimension": len(emb),
                            "model": EMBEDDING_MODEL,
                            "context_text": text,
                            "context_hash": chash,
                            "updated_at": now_ts
                        }},
                        upsert=True
                    )
                )

            if ops:
                db.embeddings_swu.bulk_write(ops, ordered=False)

            speed = len(batch_cards) / max(0.01, t_b1 - t_b0)
            print(f"    Batch [{b_idx+1}/{total_batches}] {len(batch_cards)} cards ({t_b1 - t_b0:.1f}s, {speed:.1f} cards/s)")

        elapsed = time.time() - t0
        print(f"[+] Finished embedding in {elapsed:.1f}s.")

    # Step 4: Compute pairwise cosine similarities across all unique cards
    print("[*] Loading all embeddings for similarity graph precomputation...")
    all_embeddings_docs = list(db.embeddings_swu.find({"model": EMBEDDING_MODEL}, {
        "slug": 1, "title": 1, "subtitle": 1, "embedding": 1
    }))

    if not all_embeddings_docs:
        print("[!] No embeddings found. Exiting.")
        return

    n_cards = len(all_embeddings_docs)
    dim = len(all_embeddings_docs[0]["embedding"])
    print(f"[*] Building normalized vector matrix: {n_cards} cards x {dim} dimensions...")

    matrix = np.empty((n_cards, dim), dtype=np.float32)
    card_meta = []
    card_index_by_slug = {}

    for idx, doc in enumerate(all_embeddings_docs):
        matrix[idx] = doc["embedding"]
        slug = doc["slug"]
        card_index_by_slug[slug] = idx
        # Find matching full card doc for rich metadata
        full_card = next((c for c in unique_cards if c["slug"] == slug), None) or {}
        card_meta.append({
            "slug": slug,
            "title": doc.get("title") or full_card.get("title") or full_card.get("name") or slug,
            "subtitle": doc.get("subtitle") or full_card.get("subtitle") or "",
            "type": full_card.get("type") or "",
            "aspects": full_card.get("aspects") or [],
            "traits": full_card.get("traits") or [],
            "cost": full_card.get("cost"),
            "power": full_card.get("power"),
            "hp": full_card.get("hp"),
            "art_front": full_card.get("art_front") or full_card.get("front_image")
        })

    # L2 row normalization
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    norm_matrix = matrix / norms

    print("[*] Computing full cosine similarity matrix...")
    sim_matrix = np.dot(norm_matrix, norm_matrix.T)

    # Step 5: Upsert top-K similar cards into 'similar_cards'
    print(f"[*] Precomputing top-{args.top_k} similar cards per entity...")
    top_k = args.top_k
    bulk_sim_ops = []

    for i in range(n_cards):
        scores = sim_matrix[i].copy()
        scores[i] = -1.0  # Exclude self-similarity

        # Get top K indices
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        sorted_top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        source_meta = card_meta[i]
        source_slug = source_meta["slug"]
        source_key = f"{source_meta['title'].lower()}::{source_meta['subtitle'].lower()}"

        similar_items = []
        for j in sorted_top_indices:
            target_meta = card_meta[j]
            score = round(float(scores[j]), 4)
            similar_items.append({
                "slug": target_meta["slug"],
                "title": target_meta["title"],
                "subtitle": target_meta["subtitle"],
                "score": score,
                "type": target_meta["type"],
                "aspects": target_meta["aspects"],
                "traits": target_meta["traits"],
                "cost": target_meta["cost"],
                "power": target_meta["power"],
                "hp": target_meta["hp"],
                "art_front": target_meta["art_front"]
            })

        # Save record for the canonical card
        doc_body = {
            "slug": source_slug,
            "title": source_meta["title"],
            "subtitle": source_meta["subtitle"],
            "canonical_slug": source_slug,
            "similar": similar_items,
            "updated_at": now_ts
        }
        bulk_sim_ops.append(
            pymongo.UpdateOne({"slug": source_slug}, {"$set": doc_body}, upsert=True)
        )

        # Also populate for all variant slugs belonging to this card family
        all_family = family_slugs.get(source_key, [])
        for var_slug in all_family:
            if var_slug != source_slug:
                var_doc = {
                    "slug": var_slug,
                    "title": source_meta["title"],
                    "subtitle": source_meta["subtitle"],
                    "canonical_slug": source_slug,
                    "similar": similar_items,
                    "updated_at": now_ts
                }
                bulk_sim_ops.append(
                    pymongo.UpdateOne({"slug": var_slug}, {"$set": var_doc}, upsert=True)
                )

    if bulk_sim_ops:
        db.similar_cards.bulk_write(bulk_sim_ops, ordered=False)
        print(f"[+] Successfully wrote {len(bulk_sim_ops)} similarity graph records to 'avascry_swu.similar_cards'.")

    print("\n[SUCCESS] SWU Embeddings & Similarity Precomputation Completed.")


if __name__ == "__main__":
    main()
