#!/usr/bin/env python3
"""
minecraft_generate_functional_embeddings.py — Functional & Semantic Intent Vector Embeddings.

Extracts Minecraft objects (items, blocks, entities) from 'avascry_minecraft',
builds rich mechanical context (durability, mining tiers, combat stats, redstone behavior,
recipe inputs/outputs, loot targets), computes vector embeddings via Ollama
or offline deterministic dense vectors, stores them in 'embeddings_functional',
and precomputes top-K similar items in 'similar_functional'.

Usage:
    python scripts/minecraft_generate_functional_embeddings.py --limit 20
    python scripts/minecraft_generate_functional_embeddings.py --dry-run
    python scripts/minecraft_generate_functional_embeddings.py --model qwen3-embedding:8b
"""

import os
import sys
import json
import time
import hashlib
import argparse
import urllib.request
from typing import Dict, Any, List, Optional
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db_mongo import get_mongo_db

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.environ.get("MINECRAFT_EMBEDDING_MODEL", "qwen3-embedding:8b")
EDITION = "java"
VERSION = "1.21.4"


def get_minecraft_db():
    return get_mongo_db().client["avascry_minecraft"]


def build_functional_context(doc: Dict[str, Any], doc_type: str) -> str:
    """
    Constructs a dense semantic text representation highlighting mechanics, utility,
    combat/harvest roles, and relational recipe graph ties.
    """
    slug = doc.get("slug", "")
    entity_id = doc.get("entity_id", "")
    facts = doc.get("facts", {})
    derived = doc.get("derived", {})

    display_name = facts.get("display_name") or slug.replace("-", " ").title()
    parts = [f"Object: {display_name} ({entity_id})", f"Type: Minecraft {doc_type}"]

    if doc_type == "item":
        stack = facts.get("stack_size", 64)
        parts.append(f"Stack Limit: {stack}")
        if facts.get("durability"):
            parts.append(f"Durability: {facts['durability']} uses")
        if facts.get("mining_tier"):
            parts.append(f"Mining Tier: {facts['mining_tier']}")
        if facts.get("food_points"):
            parts.append(f"Restores: {facts['food_points']} hunger")

        # Relations
        if derived.get("crafted_from_recipes"):
            parts.append(f"Crafted from recipes: {', '.join(derived['crafted_from_recipes'][:6])}")
        if derived.get("used_in_recipes"):
            parts.append(f"Ingredient in: {', '.join(derived['used_in_recipes'][:6])}")
        if derived.get("can_mine_blocks"):
            parts.append(f"Effective harvest tool for: {', '.join(derived['can_mine_blocks'][:8])}")
        if derived.get("compatible_enchantments"):
            parts.append(f"Compatible enchantments: {', '.join(derived['compatible_enchantments'][:6])}")

    elif doc_type == "block":
        parts.append(f"Hardness: {facts.get('hardness')} | Blast Resistance: {facts.get('resistance')}")
        parts.append(f"Requires Tool to Harvest: {'Yes' if facts.get('tool_required') else 'No'}")
        if derived.get("harvest_tools"):
            parts.append(f"Can be harvested by: {', '.join(derived['harvest_tools'][:6])}")
        if derived.get("drops_summary"):
            drop_targets = [d.get("target_id", "") for d in derived["drops_summary"] if d.get("target_id")]
            if drop_targets:
                parts.append(f"Drops items: {', '.join(drop_targets[:4])}")

    elif doc_type == "entity":
        if facts.get("max_health"):
            parts.append(f"Max Health: {facts['max_health']} HP")
        if facts.get("category"):
            parts.append(f"Mob Classification: {facts['category']}")
        if facts.get("immune_to_fire"):
            parts.append("Immune to Fire and Lava")

    tags = facts.get("tags") or []
    if tags:
        parts.append(f"Vanilla Tags: {', '.join(tags[:8])}")

    return " | ".join(parts)


def call_ollama_embed(text: str, model: str) -> Optional[List[float]]:
    """Calls local Ollama embedding API if running."""
    url = f"{OLLAMA_URL}/api/embeddings"
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("embedding")
    except Exception:
        return None


def deterministic_pseudo_embedding(text: str, dim: int = 128) -> List[float]:
    """
    High-quality deterministic token-hashed vector for offline / testing execution.
    Preserves n-gram similarity even when external LLM vector daemon is absent.
    """
    tokens = text.lower().replace("|", " ").replace(":", " ").replace(",", " ").split()
    vec = np.zeros(dim, dtype=np.float32)
    for token in tokens:
        h = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
        idx = h % dim
        sign = 1.0 if (h & 1) else -1.0
        vec[idx] += sign

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def precompute_top_similar(db, collection_name: str = "embeddings_functional", target_col: str = "similar_functional", top_k: int = 8):
    """Calculates cosine similarity matrix and saves top-K links."""
    docs = list(db[collection_name].find({"edition": EDITION, "version": VERSION}, {"_id": 1, "slug": 1, "type": 1, "embedding": 1}))
    if len(docs) < 2:
        return 0

    slugs = [d["slug"] for d in docs]
    matrix = np.array([d["embedding"] for d in docs], dtype=np.float32)
    
    # Cosine similarity matrix (assumes vectors normalized)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = matrix / norms
    sim_matrix = np.dot(normalized, normalized.T)

    updated = 0
    for i, doc in enumerate(docs):
        scores = sim_matrix[i]
        top_indices = np.argsort(-scores)
        top_neighbors = []
        for idx in top_indices:
            if idx == i:
                continue
            top_neighbors.append({
                "slug": slugs[idx],
                "type": docs[idx].get("type", "item"),
                "score": round(float(scores[idx]), 4)
            })
            if len(top_neighbors) >= top_k:
                break

        db[target_col].update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "slug": doc["slug"],
                    "type": doc.get("type", "item"),
                    "edition": EDITION,
                    "version": VERSION,
                    "neighbors": top_neighbors,
                    "updated_at": time.time()
                }
            },
            upsert=True
        )
        updated += 1

    return updated


def main():
    parser = argparse.ArgumentParser(description="Generate functional vector embeddings for Minecraft Atlas")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama embedding model")
    parser.add_argument("--limit", type=int, default=0, help="Max entities to process (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Print context texts without writing to DB")
    parser.add_argument("--precompute", action="store_true", default=True, help="Compute top-K similarity graph")
    args = parser.parse_args()

    db = get_minecraft_db()
    items = list(db.items.find({"edition": EDITION, "version": VERSION}))
    blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION}))
    entities = list(db.entities.find({"edition": EDITION, "version": VERSION}))

    combined = []
    for itm in items:
        combined.append((itm, "item"))
    for blk in blocks:
        combined.append((blk, "block"))
    for ent in entities:
        combined.append((ent, "entity"))

    if args.limit > 0:
        combined = combined[:args.limit]

    print(f"[*] Processing {len(combined)} objects for functional embeddings...")

    saved = 0
    for doc, doc_type in combined:
        slug = doc.get("slug")
        context_text = build_functional_context(doc, doc_type)
        if args.dry_run:
            print(f"\n[{doc_type.upper()}] {slug}:")
            print(f"  {context_text}")
            continue

        # Attempt Ollama vector or fall back to normalized hash vector
        vec = call_ollama_embed(context_text, args.model)
        source = "ollama"
        if not vec:
            vec = deterministic_pseudo_embedding(context_text, dim=128)
            source = "deterministic"

        doc_id = f"{EDITION}|{VERSION}|{slug}|{doc_type}"
        db.embeddings_functional.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "slug": slug,
                    "type": doc_type,
                    "edition": EDITION,
                    "version": VERSION,
                    "context_text": context_text,
                    "embedding": vec,
                    "source": source,
                    "updated_at": time.time()
                }
            },
            upsert=True
        )
        saved += 1

    if not args.dry_run:
        print(f"[+] Successfully saved {saved} functional vector records.")
        if args.precompute:
            print("[*] Precomputing top similarity graph...")
            links = precompute_top_similar(db, "embeddings_functional", "similar_functional")
            print(f"[+] Precomputed similarity links for {links} objects.")


if __name__ == "__main__":
    main()
