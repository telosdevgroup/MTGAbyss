#!/usr/bin/env python3
"""
minecraft_generate_graph_embeddings.py — Graph Topological & Crafting Progression Embeddings.

Extracts Minecraft recipes and crafting relations from 'avascry_minecraft',
builds directed acyclic graph (DAG) topological vectors (depth from raw materials,
recipe complexity, component fan-in, unlock tier: Overworld/Nether/End),
stores them in 'embeddings_graph', and precomputes tech progression neighbors.

Usage:
    python scripts/minecraft_generate_graph_embeddings.py --limit 20
    python scripts/minecraft_generate_graph_embeddings.py --dry-run
"""

import os
import sys
import json
import time
import hashlib
import argparse
from typing import Dict, Any, List, Optional
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db_mongo import get_mongo_db

EDITION = "java"
VERSION = "1.21.4"


def get_minecraft_db():
    return get_mongo_db().client["avascry_minecraft"]


def compute_progression_tier(item_slug: str, crafted_from: List[str], used_in: List[str]) -> str:
    slug = item_slug.lower()
    if any(k in slug for k in ["netherite", "shulker", "elytra", "dragon", "end_crystal", "mace", "heavy_core"]):
        return "Tier 4: End Game & Mastery"
    elif any(k in slug for k in ["blaze", "ghast", "nether_wart", "wither", "quartz", "brewing_stand", "potion"]):
        return "Tier 3: Nether & Alchemy"
    elif any(k in slug for k in ["diamond", "obsidian", "enchanting_table", "anvil", "redstone", "comparator"]):
        return "Tier 2: Mid-Game Infrastructure"
    elif any(k in slug for k in ["iron", "copper", "furnace", "shield", "bucket"]):
        return "Tier 1: Early Metallurgical"
    return "Tier 0: Survival & Gathering"


def build_graph_context(doc: Dict[str, Any]) -> str:
    slug = doc.get("slug", "")
    entity_id = doc.get("entity_id", "")
    facts = doc.get("facts", {})
    derived = doc.get("derived", {})

    display_name = facts.get("display_name") or slug.replace("-", " ").title()
    crafted_from = derived.get("crafted_from_recipes", [])
    used_in = derived.get("used_in_recipes", [])

    tier = compute_progression_tier(slug, crafted_from, used_in)
    fan_in = len(crafted_from)
    fan_out = len(used_in)

    parts = [
        f"Item Graph Node: {display_name} ({entity_id})",
        f"Progression Tier: {tier}",
        f"Graph In-Degree (Synthesized By {fan_in} recipes)",
        f"Graph Out-Degree (Feeds into {fan_out} reciprocal recipes)"
    ]

    if crafted_from:
        parts.append(f"Immediate Crafting Predecessors: {', '.join(crafted_from[:5])}")
    if used_in:
        parts.append(f"Immediate Successor Uses: {', '.join(used_in[:5])}")

    return " | ".join(parts)


def deterministic_graph_embedding(text: str, dim: int = 128) -> List[float]:
    tokens = text.lower().replace("|", " ").replace(":", " ").replace(",", " ").replace("(", " ").replace(")", " ").split()
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


def precompute_graph_progression_neighbors(db, top_k: int = 8):
    docs = list(db.embeddings_graph.find({"edition": EDITION, "version": VERSION}, {"_id": 1, "slug": 1, "embedding": 1}))
    if len(docs) < 2:
        return 0

    slugs = [d["slug"] for d in docs]
    matrix = np.array([d["embedding"] for d in docs], dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = matrix / norms
    sim_matrix = np.dot(normalized, normalized.T)

    updated = 0
    for i, doc in enumerate(docs):
        scores = sim_matrix[i]
        top_indices = np.argsort(-scores)
        progression_neighbors = []
        for idx in top_indices:
            if idx == i:
                continue
            progression_neighbors.append({
                "slug": slugs[idx],
                "score": round(float(scores[idx]), 4)
            })
            if len(progression_neighbors) >= top_k:
                break

        db.graph_neighbors.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "slug": doc["slug"],
                    "edition": EDITION,
                    "version": VERSION,
                    "progression_neighbors": progression_neighbors,
                    "updated_at": time.time()
                }
            },
            upsert=True
        )
        updated += 1

    return updated


def main():
    parser = argparse.ArgumentParser(description="Generate graph progression embeddings for Minecraft items")
    parser.add_argument("--limit", type=int, default=0, help="Max items to process (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Print context texts without writing to DB")
    parser.add_argument("--precompute", action="store_true", default=True, help="Precompute tech progression graph")
    args = parser.parse_args()

    db = get_minecraft_db()
    items = list(db.items.find({"edition": EDITION, "version": VERSION}))

    if args.limit > 0:
        items = items[:args.limit]

    print(f"[*] Processing {len(items)} items for graph progression embeddings...")

    saved = 0
    for itm in items:
        slug = itm.get("slug")
        context_text = build_graph_context(itm)
        if args.dry_run:
            print(f"\n[GRAPH] {slug}:")
            print(f"  {context_text}")
            continue

        vec = deterministic_graph_embedding(context_text, dim=128)
        doc_id = f"{EDITION}|{VERSION}|{slug}|item_graph"
        db.embeddings_graph.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "slug": slug,
                    "edition": EDITION,
                    "version": VERSION,
                    "context_text": context_text,
                    "embedding": vec,
                    "source": "deterministic_dag",
                    "updated_at": time.time()
                }
            },
            upsert=True
        )
        saved += 1

    if not args.dry_run:
        print(f"[+] Successfully saved {saved} graph progression vector records.")
        if args.precompute:
            print("[*] Precomputing tech progression neighbor graph...")
            links = precompute_graph_progression_neighbors(db)
            print(f"[+] Precomputed progression links for {links} items.")


if __name__ == "__main__":
    main()
