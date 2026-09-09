#!/usr/bin/env python3
"""
test_minecraft_embeddings.py — Query and inspect multi-space Minecraft embeddings.

Tests and prints top nearest neighbors across all 3 embedding modalities:
1. Functional & Semantic Intent ('similar_functional')
2. Building Palette & Aesthetic Matches ('palette_neighbors')
3. Crafting Tech Progression ('graph_neighbors')

Usage:
    python scripts/test_minecraft_embeddings.py --slug diamond-pickaxe
    python scripts/test_minecraft_embeddings.py --block deepslate-tiles
"""

import os
import sys
import argparse
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db_mongo import get_mongo_db


def test_slug(slug: str):
    db = get_mongo_db().client["avascry_minecraft"]

    print(f"\n=======================================================")
    print(f" Multi-Vector Embedding Inspection: '{slug}'")
    print(f"=======================================================")

    # 1. Functional Similarity
    func = db.similar_functional.find_one({"slug": slug})
    if func and func.get("neighbors"):
        print("\n1. FUNCTIONAL & SEMANTIC NEIGHBORS (Mechanics / Utility / Combat):")
        for idx, n in enumerate(func["neighbors"][:5], 1):
            print(f"   {idx}. {n['slug']} ({n.get('type')}) — similarity: {n['score']}")
    else:
        print("\n1. FUNCTIONAL & SEMANTIC NEIGHBORS: (No vectors generated yet. Run scripts/minecraft_generate_functional_embeddings.py)")

    # 2. Building Palette Matches
    palette = db.palette_neighbors.find_one({"slug": slug})
    if palette and palette.get("palette_matches"):
        print("\n2. VISUAL BUILDING PALETTE MATCHES (Textures / Materials / Colors):")
        for idx, p in enumerate(palette["palette_matches"][:5], 1):
            print(f"   {idx}. {p['slug']} — palette match score: {p['score']}")
    else:
        print("\n2. VISUAL BUILDING PALETTE MATCHES: (No block palette record found for this slug)")

    # 3. Graph & Progression Neighbors
    graph = db.graph_neighbors.find_one({"slug": slug})
    if graph and graph.get("progression_neighbors"):
        print("\n3. CRAFTING & PROGRESSION NEIGHBORS (Tech Tier / DAG Relations):")
        for idx, g in enumerate(graph["progression_neighbors"][:5], 1):
            print(f"   {idx}. {g['slug']} — graph progression match: {g['score']}")
    else:
        print("\n3. CRAFTING & PROGRESSION NEIGHBORS: (No graph vector found for this slug)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Test multi-type Minecraft embeddings")
    parser.add_argument("--slug", default="diamond-pickaxe", help="Item or block slug to inspect")
    parser.add_argument("--block", default="", help="Block slug for palette inspection")
    args = parser.parse_args()

    target = args.block if args.block else args.slug
    test_slug(target)


if __name__ == "__main__":
    main()
