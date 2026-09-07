import os
import sys
import time
import argparse
import numpy as np
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db, ensure_indexes

def normalize_vectors(arr):
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms

def main():
    parser = argparse.ArgumentParser(description="Compute Top 7 Nearest Neighbors across subject, vibe, and scene dimensions.")
    parser.add_argument("--model", default="qwen3-embedding:8b", help="Embedding model name to query")
    parser.add_argument("--top-k", type=int, default=7, help="Number of nearest neighbors to compute (default: 7)")
    args = parser.parse_args()

    db = get_mongo_db()
    ensure_indexes(db)

    print("=" * 60)
    print(f"Visual Similarity Matrix Builder (Top {args.top_k} Neighbors)")
    print("=" * 60)

    # 1. Load all embeddings into memory
    print("[*] Loading visual embeddings from MongoDB...")
    cursor = db.vl_art_embeddings.find({"model": args.model})
    
    ids = []
    card_meta = {}
    subject_vectors = []
    vibe_vectors = []
    scene_vectors = []

    for doc in cursor:
        iid = doc.get("illustration_id")
        vecs = doc.get("vectors", {})
        if not iid or "subject" not in vecs or "vibe" not in vecs or "scene" not in vecs:
            continue
        
        ids.append(iid)
        source = doc.get("source", {})
        card_meta[iid] = {
            "card_name": source.get("card_name", "Unknown"),
            "artist": source.get("artist", "Unknown"),
            "set": source.get("set", ""),
            "image_url": source.get("image_url")
        }
        subject_vectors.append(vecs["subject"])
        vibe_vectors.append(vecs["vibe"])
        scene_vectors.append(vecs["scene"])

    total = len(ids)
    print(f"[*] Loaded {total:,} illustrations.")
    if total < 2:
        print("[!] Need at least 2 illustrations with embeddings to compute similarity.")
        return

    # Convert to NumPy arrays and normalize for dot-product cosine similarity
    t0 = time.time()
    subj_mat = normalize_vectors(np.array(subject_vectors, dtype=np.float32))
    vibe_mat = normalize_vectors(np.array(vibe_vectors, dtype=np.float32))
    scene_mat = normalize_vectors(np.array(scene_vectors, dtype=np.float32))
    print(f"[*] Matrices normalized in {time.time() - t0:.2f}s.")

    # Compute cosine similarity dot products in blocks to be memory friendly
    print(f"[*] Computing Top {args.top_k} neighbors across all 3 dimensions...")
    t_sim = time.time()

    k = min(args.top_k, total - 1)
    
    # We will compute similarities and save to MongoDB
    now = datetime.now(timezone.utc)
    bulk_ops = []

    for i in range(total):
        curr_id = ids[i]
        
        # 1. Subject similarity
        subj_sims = np.dot(subj_mat, subj_mat[i])
        subj_sims[i] = -1.0 # exclude self
        top_subj_indices = np.argpartition(subj_sims, -k)[-k:]
        top_subj_indices = top_subj_indices[np.argsort(-subj_sims[top_subj_indices])]
        
        subj_neighbors = [
            {
                "illustration_id": ids[idx],
                "score": round(float(subj_sims[idx]), 4),
                "card_name": card_meta[ids[idx]]["card_name"],
                "artist": card_meta[ids[idx]]["artist"],
                "set": card_meta[ids[idx]]["set"],
                "image_url": card_meta[ids[idx]]["image_url"]
            }
            for idx in top_subj_indices
        ]

        # 2. Vibe similarity
        vibe_sims = np.dot(vibe_mat, vibe_mat[i])
        vibe_sims[i] = -1.0
        top_vibe_indices = np.argpartition(vibe_sims, -k)[-k:]
        top_vibe_indices = top_vibe_indices[np.argsort(-vibe_sims[top_vibe_indices])]
        
        vibe_neighbors = [
            {
                "illustration_id": ids[idx],
                "score": round(float(vibe_sims[idx]), 4),
                "card_name": card_meta[ids[idx]]["card_name"],
                "artist": card_meta[ids[idx]]["artist"],
                "set": card_meta[ids[idx]]["set"],
                "image_url": card_meta[ids[idx]]["image_url"]
            }
            for idx in top_vibe_indices
        ]

        # 3. Scene similarity
        scene_sims = np.dot(scene_mat, scene_mat[i])
        scene_sims[i] = -1.0
        top_scene_indices = np.argpartition(scene_sims, -k)[-k:]
        top_scene_indices = top_scene_indices[np.argsort(-scene_sims[top_scene_indices])]
        
        scene_neighbors = [
            {
                "illustration_id": ids[idx],
                "score": round(float(scene_sims[idx]), 4),
                "card_name": card_meta[ids[idx]]["card_name"],
                "artist": card_meta[ids[idx]]["artist"],
                "set": card_meta[ids[idx]]["set"],
                "image_url": card_meta[ids[idx]]["image_url"]
            }
            for idx in top_scene_indices
        ]

        db.vl_art_similarities.update_one(
            {"illustration_id": curr_id, "model": args.model},
            {
                "$set": {
                    "illustration_id": curr_id,
                    "model": args.model,
                    "top_neighbors": {
                        "by_subject": subj_neighbors,
                        "by_vibe": vibe_neighbors,
                        "by_scene": scene_neighbors
                    },
                    "updated_at": now
                },
                "$setOnInsert": {
                    "created_at": now
                }
            },
            upsert=True
        )

        if (i + 1) % 500 == 0 or (i + 1) == total:
            print(f"    Computed {i + 1:,}/{total:,} similarity profiles...")

    print(f"\n[+] Successfully computed Top {args.top_k} visual neighbors for {total:,} illustrations in {time.time() - t_sim:.2f}s!")

if __name__ == "__main__":
    main()
