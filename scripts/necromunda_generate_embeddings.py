#!/usr/bin/env python3
"""
necromunda_generate_embeddings.py — Rich Contextual Embedding & Ballistic Alternative Precomputer for Necromunda.

Extracts all weapons from MongoDB ('avascry_necromunda.weapons'), hydrates full weapon trait
rules descriptions (e.g., Template mechanics, Rapid Fire dice, Blast markers, Ammo check rerolls),
generates 4096-dimensional embeddings using local Ollama ('qwen3-embedding:8b'), stores them
in 'avascry_necromunda.embeddings', and precomputes the top-7 tactical ballistic alternatives
into 'avascry_necromunda.similar_weapons'.
"""

import sys
import os
import time
import json
import hashlib
import urllib.request
import numpy as np
import pymongo
from typing import List, Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from mtgabyss.routers.necromunda_router import get_necromunda_db

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
EMBEDDING_MODEL = os.environ.get("NECROMUNDA_EMBEDDING_MODEL", "qwen3-embedding:8b")

def build_weapon_context(weapon: Dict[str, Any], traits_lookup: Dict[str, Dict[str, Any]]) -> str:
    name = weapon.get("name") or ""
    category = weapon.get("category") or ""
    cost = weapon.get("cost_credits")
    rarity = weapon.get("rarity") or ""
    description = weapon.get("description") or ""

    r_s = weapon.get("range_short") or "-"
    r_l = weapon.get("range_long") or "-"
    acc_s = weapon.get("accuracy_short") or "-"
    acc_l = weapon.get("accuracy_long") or "-"
    str_val = weapon.get("strength") or "-"
    dmg = weapon.get("damage") or "-"
    ap = weapon.get("armor_piercing") or "-"
    ammo = weapon.get("ammo") or "-"

    parts = [
        f"Game: Necromunda: Underhive",
        f"Armory Weapon: {name}",
        f"Category: {category}",
        f"Cost: {cost} credits (Rarity: {rarity})",
        f"Ballistics Profile: Short Range: {r_s}, Long Range: {r_l}, Short Acc: {acc_s}, Long Acc: {acc_l}, Strength: {str_val}, Damage: {dmg}, AP: {ap}, Ammo Check: {ammo}",
    ]

    # Hydrate weapon traits with their official rules and tactical implications
    raw_traits = weapon.get("traits") or []
    trait_details = []
    for t_name in raw_traits:
        t_clean = t_name.strip()
        t_doc = traits_lookup.get(t_clean.lower())
        if t_doc:
            rules_snippet = t_doc.get("rules_text") or ""
            faq_snippet = t_doc.get("faq") or ""
            trait_details.append(f"- {t_clean}: {rules_snippet} (Tactical note: {faq_snippet})")
        else:
            trait_details.append(f"- {t_clean}")

    if trait_details:
        parts.append("Traits & Special Rules:\n" + "\n".join(trait_details))

    if description:
        parts.append(f"Technical Lore & Usage: {description}")

    availability = weapon.get("availability") or []
    if availability:
        parts.append(f"Gang Availability: {', '.join(availability)}")

    return "\n".join(parts)

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

def derive_tactical_reason(source: Dict[str, Any], target: Dict[str, Any]) -> str:
    """Human-friendly tactical badge for why two Underhive weapons compare."""
    s_traits = set([t.lower() for t in source.get("traits") or []])
    t_traits = set([t.lower() for t in target.get("traits") or []])
    shared_traits = s_traits.intersection(t_traits)

    # High-impact mechanic traits
    if any("template" in t for t in shared_traits):
        return "Template & Area Denial Alternative"
    if any("rapid fire" in t for t in shared_traits):
        return "High-Volume Sustained Firepower"
    if any("blast" in t for t in shared_traits):
        return "Blast Radius Explosive"
    if any("plentiful" in t for t in shared_traits):
        return "Reliable Ammo Profile"
    if any("knockback" in t for t in shared_traits):
        return "Tactical Repositioning"
    if any("melta" in t or "plasma" in t or "unstable" in t for t in shared_traits):
        return "High-Energy Armor Melter"

    s_cat = source.get("category") or ""
    t_cat = target.get("category") or ""
    if s_cat == t_cat and s_cat:
        s_cost = source.get("cost_credits") or 0
        t_cost = target.get("cost_credits") or 0
        if abs(s_cost - t_cost) <= 20:
            return f"Underhive {s_cat} Equivalent"
        return f"{s_cat} Alternative"

    return "Tactical Ballistic Match"

def main():
    db = get_necromunda_db()
    print(f"[*] Connected to MongoDB: {db.name}")

    # Build traits lookup
    traits_lookup = {}
    for t in db.traits.find():
        traits_lookup[t.get("name", "").strip().lower()] = t

    weapons = list(db.weapons.find().sort("name", 1))
    print(f"[*] Loaded {len(weapons)} weapons and {len(traits_lookup)} trait definitions.")

    # Create collection indexes
    db.embeddings.create_index("slug", unique=True)
    db.similar_weapons.create_index("slug", unique=True)

    # Build contexts
    contexts = []
    hashes = []
    for w in weapons:
        ctx = build_weapon_context(w, traits_lookup)
        contexts.append(ctx)
        hashes.append(hashlib.sha256(ctx.encode("utf-8")).hexdigest())

    # Check cached embeddings
    existing_embs = {e["slug"]: e for e in db.embeddings.find({"model": EMBEDDING_MODEL}, {"slug": 1, "context_hash": 1})}
    needed_indices = [i for i, w in enumerate(weapons) if w["slug"] not in existing_embs or existing_embs[w["slug"]].get("context_hash") != hashes[i]]

    if needed_indices:
        print(f"[*] Generating embeddings for {len(needed_indices)} weapons using '{EMBEDDING_MODEL}'...")
        batch_size = 32
        total_batches = (len(needed_indices) + batch_size - 1) // batch_size
        t0 = time.time()

        for b in range(total_batches):
            sub_indices = needed_indices[b * batch_size : (b + 1) * batch_size]
            batch_texts = [contexts[i] for i in sub_indices]
            batch_weapons = [weapons[i] for i in sub_indices]
            batch_hashes = [hashes[i] for i in sub_indices]

            embs = call_ollama_batch_embed(batch_texts, model=EMBEDDING_MODEL)
            ops = []
            for w, text, chash, emb in zip(batch_weapons, batch_texts, batch_hashes, embs):
                ops.append(
                    pymongo.UpdateOne(
                        {"slug": w["slug"]},
                        {"$set": {
                            "slug": w["slug"],
                            "name": w["name"],
                            "category": w.get("category", ""),
                            "embedding": emb,
                            "dimension": len(emb),
                            "model": EMBEDDING_MODEL,
                            "context_hash": chash,
                            "updated_at": time.time()
                        }},
                        upsert=True
                    )
                )
            db.embeddings.bulk_write(ops, ordered=False)
            print(f"    Batch [{b+1}/{total_batches}] {len(sub_indices)} weapons processed.")

        print(f"[+] Finished embedding in {time.time() - t0:.1f}s.")
    else:
        print("[*] All weapon embeddings up to date in MongoDB.")

    # Compute pairwise similarities for top-7 alternatives
    all_embs = list(db.embeddings.find({"model": EMBEDDING_MODEL}, {"slug": 1, "embedding": 1}))
    n = len(all_embs)
    dim = len(all_embs[0]["embedding"])
    matrix = np.empty((n, dim), dtype=np.float32)
    slug_to_idx = {}
    weapons_by_slug = {w["slug"]: w for w in weapons}

    for idx, doc in enumerate(all_embs):
        matrix[idx] = doc["embedding"]
        slug_to_idx[doc["slug"]] = idx

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    norm_matrix = matrix / norms
    sim_matrix = np.dot(norm_matrix, norm_matrix.T)

    top_k = 7
    print(f"[*] Precomputing top-{top_k} tactical alternatives per weapon...")
    sim_ops = []
    for i in range(n):
        scores = sim_matrix[i].copy()
        scores[i] = -1.0
        top_indices = np.argpartition(scores, -top_k)[-top_k:]
        sorted_top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        source_slug = all_embs[i]["slug"]
        source_w = weapons_by_slug.get(source_slug, {})

        similar_items = []
        for j in sorted_top_indices:
            target_slug = all_embs[j]["slug"]
            target_w = weapons_by_slug.get(target_slug, {})
            similar_items.append({
                "slug": target_slug,
                "name": target_w.get("name") or target_slug,
                "category": target_w.get("category", ""),
                "cost_credits": target_w.get("cost_credits"),
                "rarity": target_w.get("rarity"),
                "range_short": target_w.get("range_short"),
                "range_long": target_w.get("range_long"),
                "strength": target_w.get("strength"),
                "damage": target_w.get("damage"),
                "armor_piercing": target_w.get("armor_piercing"),
                "ammo": target_w.get("ammo"),
                "traits": target_w.get("traits", []),
                "tactical_reason": derive_tactical_reason(source_w, target_w)
            })

        sim_ops.append(
            pymongo.UpdateOne(
                {"slug": source_slug},
                {"$set": {
                    "slug": source_slug,
                    "name": source_w.get("name"),
                    "category": source_w.get("category"),
                    "similar": similar_items,
                    "updated_at": time.time()
                }},
                upsert=True
            )
        )

    if sim_ops:
        db.similar_weapons.bulk_write(sim_ops, ordered=False)
        print(f"[+] Successfully upserted {len(sim_ops)} similar weapon graphs into avascry_necromunda.similar_weapons.")

if __name__ == "__main__":
    main()
