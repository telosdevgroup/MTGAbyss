#!/usr/bin/env python3
"""
generate_dominion_embeddings.py — Compute semantic embeddings for Dominion cards using Qwen-Embedding 8B (Ollama).

Calculates 4096-dimensional embeddings for all 819 cards, computes pairwise cosine similarity,
and stores the top 10 most synergistic/related cards directly into the MongoDB 'cards' collection.
"""

import os
import sys
import json
import time
import urllib.request
import numpy as np

# Add repository root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db_mongo import get_mongo_db

OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "qwen3-embedding:8b"

def get_embedding(text: str) -> list:
    payload = json.dumps({"model": MODEL_NAME, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("embedding", [])

def main():
    print("Connecting to MongoDB avascry_dominion...")
    db = get_mongo_db().client["avascry_dominion"]
    cards = list(db.cards.find({}).sort("name", 1))
    total_cards = len(cards)
    print(f"Loaded {total_cards} cards from database.")

    # Load versions & rulings to construct rich semantic documents
    versions = list(db.card_versions.find({}))
    versions_by_card = {}
    for v in versions:
        cid = v.get("card_id")
        if cid:
            versions_by_card.setdefault(cid, []).append(v)

    rulings = list(db.rulings.find({}))
    rulings_by_card = {}
    for r in rulings:
        cid = r.get("card_id", "")
        if cid:
            rulings_by_card.setdefault(cid, []).append(r)

    print("Constructing card representations...")
    slugs = []
    card_meta = {}
    documents = []

    for c in cards:
        slug = c.get("slug")
        name = c.get("name", slug)
        kinds = ", ".join(c.get("card_kinds", []))
        is_kg = "Yes" if c.get("is_kingdom_card") else "No"
        
        cvs = versions_by_card.get(f"card:{slug}", [])
        rules_text = " ".join([v.get("printed_rules_text", "") for v in cvs if v.get("printed_rules_text")])
        cost = cvs[0].get("cost", {}) if cvs else {}
        cost_coins = cost.get("coins", 0)
        
        card_rulings = rulings_by_card.get(f"card:{slug}", []) or rulings_by_card.get(c.get("_id"), [])
        faq_text = " ".join([f"Q: {r.get('question')} A: {r.get('answer')}" for r in card_rulings])

        doc = (
            f"Card: {name}\n"
            f"Types: {kinds}\n"
            f"Kingdom Card: {is_kg}\n"
            f"Cost: {cost_coins} Coins\n"
            f"Rules Text: {rules_text}\n"
            f"FAQ & Interactions: {faq_text}"
        )
        slugs.append(slug)
        card_meta[slug] = {
            "name": name,
            "slug": slug,
            "cost": cost,
            "card_kinds": c.get("card_kinds", []),
            "is_kingdom_card": c.get("is_kingdom_card", False)
        }
        documents.append(doc)

    print(f"Generating embeddings using {MODEL_NAME} for {total_cards} cards...")
    embeddings = []
    start_t = time.time()
    for idx, (slug, doc) in enumerate(zip(slugs, documents)):
        emb = get_embedding(doc)
        if not emb:
            print(f"Warning: empty embedding for {slug}")
            emb = [0.0] * 4096
        embeddings.append(emb)
        if (idx + 1) % 50 == 0 or idx == total_cards - 1:
            elapsed = time.time() - start_t
            rate = (idx + 1) / elapsed
            print(f"  [{idx + 1}/{total_cards}] embedded ({rate:.1f} cards/sec)...")

    print("Computing cosine similarity matrix...")
    matrix = np.array(embeddings, dtype=np.float32)
    # L2 normalize rows
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    matrix_norm = matrix / norms

    # Similarity matrix: (N, N)
    sims = np.dot(matrix_norm, matrix_norm.T)

    print("Finding top 10 most similar cards for each card and writing to MongoDB...")
    for i, slug in enumerate(slugs):
        # Sort indices descending by similarity score
        # Ignore self (index i)
        row_sims = sims[i]
        top_indices = np.argsort(-row_sims)
        related = []
        for idx in top_indices:
            if idx == i:
                continue
            neighbor_slug = slugs[idx]
            meta = card_meta[neighbor_slug]
            score = float(row_sims[idx])
            related.append({
                "slug": neighbor_slug,
                "name": meta["name"],
                "similarity": round(score, 3),
                "cost": meta["cost"],
                "card_kinds": meta["card_kinds"],
                "is_kingdom_card": meta["is_kingdom_card"]
            })
            if len(related) == 10:
                break

        # Persist to Mongo
        db.cards.update_one(
            {"slug": slug},
            {"$set": {"related_cards": related}}
        )

    # Test sample inspection: Chapel, Village, Smithy
    test_slugs = ["chapel", "village", "smithy", "witch", "militia"]
    print("\n--- SAMPLE SYNERGIES VERIFICATION ---")
    for ts in test_slugs:
        c = db.cards.find_one({"slug": ts})
        rel = c.get("related_cards", [])
        rel_str = ", ".join([f"{r['name']} ({r['similarity']})" for r in rel[:5]])
        print(f"{c['name']:<10} -> {rel_str}")

    print("\nEmbeddings & related cards successfully computed and stored in MongoDB!")

if __name__ == "__main__":
    main()
