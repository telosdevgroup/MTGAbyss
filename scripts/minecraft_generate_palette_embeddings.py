#!/usr/bin/env python3
"""
minecraft_generate_palette_embeddings.py — Visual & Aesthetic Block Palette Embeddings.

Extracts Minecraft blocks and decor items from 'avascry_minecraft',
builds visual, color, texture, sound, luminance, and architectural contexts,
computes vector embeddings via Ollama or dense color/texture hashing,
stores them in 'embeddings_palette', and precomputes building palette matches
in 'palette_neighbors'.

Usage:
    python scripts/minecraft_generate_palette_embeddings.py --limit 20
    python scripts/minecraft_generate_palette_embeddings.py --dry-run
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
DEFAULT_MODEL = os.environ.get("MINECRAFT_PALETTE_MODEL", "qwen3-embedding:8b")
EDITION = "java"
VERSION = "1.21.4"


def get_minecraft_db():
    return get_mongo_db().client["avascry_minecraft"]


def infer_color_and_texture_family(name: str, tags: List[str]) -> List[str]:
    """Infers hue and architectural material family from names and vanilla tags."""
    descriptors = []
    n = name.lower()
    
    # Material / Texture feel
    if any(k in n for k in ["deepslate", "blackstone", "basalt", "obsidian", "coal_block"]):
        descriptors.extend(["dark charcoal black", "deep stone", "matte gothic"])
    elif any(k in n for k in ["stone", "andesite", "cobblestone", "gravel", "tuff"]):
        descriptors.extend(["neutral gray", "natural stone", "rocky texture"])
    elif any(k in n for k in ["diorite", "calcite", "quartz", "white", "snow", "marble"]):
        descriptors.extend(["bright white", "clean pale", "smooth polished"])
    elif any(k in n for k in ["granite", "brick", "terracotta", "copper", "red_sandstone"]):
        descriptors.extend(["warm terracotta red orange", "earthen clay", "warm masonry"])
    elif any(k in n for k in ["sandstone", "sand", "birch", "end_stone", "bone"]):
        descriptors.extend(["warm cream beige pale yellow", "desert limestone"])
    elif any(k in n for k in ["prismarine", "dark_prismarine", "sea_lantern", "cyan"]):
        descriptors.extend(["vibrant teal cyan aquatic", "oceanic monument"])
    elif any(k in n for k in ["purpur", "amethyst", "obsidian_crying"]):
        descriptors.extend(["mystic violet magenta purple", "crystalline"])
    elif any(k in n for k in ["nether_brick", "crimson", "netherrack", "wart"]):
        descriptors.extend(["blood crimson dark maroon", "nether organic"])
    elif any(k in n for k in ["warped", "soul_sand", "soul_soil", "soul_lantern"]):
        descriptors.extend(["spectral cyan teal ghostly", "eerie nether"])

    # Wood species
    woods = ["oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo"]
    for w in woods:
        if w in n:
            descriptors.append(f"{w} timber organic wood grain")

    # Structural forms
    if "stairs" in n:
        descriptors.append("sloped architectural trim")
    elif "slab" in n:
        descriptors.append("half-block horizontal plate")
    elif "wall" in n or "fence" in n:
        descriptors.append("vertical boundary barrier")
    elif "glass" in n:
        descriptors.append("transparent reflective window")

    return descriptors


def build_palette_context(doc: Dict[str, Any]) -> str:
    """Constructs visual, architectural, and palette text representation."""
    slug = doc.get("slug", "")
    entity_id = doc.get("entity_id", "")
    facts = doc.get("facts", {})
    derived = doc.get("derived", {})

    display_name = facts.get("display_name") or slug.replace("-", " ").title()
    tags = facts.get("tags") or []

    descriptors = infer_color_and_texture_family(display_name, tags)

    parts = [
        f"Block Palette Asset: {display_name}",
        f"Namespaced ID: {entity_id}",
        f"Hardness Density: {facts.get('hardness', 1.5)}",
        f"Blast Resistance: {facts.get('resistance', 6.0)}"
    ]

    if descriptors:
        parts.append(f"Visual Palette & Texture Feel: {', '.join(descriptors)}")

    if tags:
        parts.append(f"Material Tags: {', '.join(tags[:6])}")

    return " | ".join(parts)


def call_ollama_embed(text: str, model: str) -> Optional[List[float]]:
    url = f"{OLLAMA_URL}/api/embeddings"
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("embedding")
    except Exception:
        return None


def deterministic_palette_embedding(text: str, dim: int = 128) -> List[float]:
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


def precompute_palette_neighbors(db, top_k: int = 8):
    docs = list(db.embeddings_palette.find({"edition": EDITION, "version": VERSION}, {"_id": 1, "slug": 1, "embedding": 1}))
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
        palette_matches = []
        for idx in top_indices:
            if idx == i:
                continue
            palette_matches.append({
                "slug": slugs[idx],
                "score": round(float(scores[idx]), 4)
            })
            if len(palette_matches) >= top_k:
                break

        db.palette_neighbors.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "slug": doc["slug"],
                    "edition": EDITION,
                    "version": VERSION,
                    "palette_matches": palette_matches,
                    "updated_at": time.time()
                }
            },
            upsert=True
        )
        updated += 1

    return updated


def main():
    parser = argparse.ArgumentParser(description="Generate visual palette embeddings for Minecraft blocks")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama embedding model")
    parser.add_argument("--limit", type=int, default=0, help="Max blocks to process (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Print context texts without writing to DB")
    parser.add_argument("--precompute", action="store_true", default=True, help="Precompute palette graph")
    args = parser.parse_args()

    db = get_minecraft_db()
    blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION}))

    if args.limit > 0:
        blocks = blocks[:args.limit]

    print(f"[*] Processing {len(blocks)} blocks for palette embeddings...")

    saved = 0
    for blk in blocks:
        slug = blk.get("slug")
        context_text = build_palette_context(blk)
        if args.dry_run:
            print(f"\n[PALETTE] {slug}:")
            print(f"  {context_text}")
            continue

        vec = call_ollama_embed(context_text, args.model)
        source = "ollama"
        if not vec:
            vec = deterministic_palette_embedding(context_text, dim=128)
            source = "deterministic"

        doc_id = f"{EDITION}|{VERSION}|{slug}|block_palette"
        db.embeddings_palette.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "slug": slug,
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
        print(f"[+] Successfully saved {saved} block palette vector records.")
        if args.precompute:
            print("[*] Precomputing block palette neighbor graph...")
            links = precompute_palette_neighbors(db)
            print(f"[+] Precomputed palette matches for {links} blocks.")


if __name__ == "__main__":
    main()
