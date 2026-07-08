import os
import sys
import time
import math
import argparse
import datetime

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [Abyss Walker] {msg}", flush=True)

def cosine_similarity(v1, v2):
    if HAS_NUMPY:
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    else:
        dot_product = sum(x * y for x, y in zip(v1, v2))
        norm_a = math.sqrt(sum(x * x for x in v1))
        norm_b = math.sqrt(sum(y * y for y in v2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

def process_single_card(db, target_doc, all_embeddings_cached, threshold=0.82):
    """
    Processes a single card embedding incrementally, finding its top synergies.
    """
    target_oid = target_doc["oracle_id"]
    target_vector = target_doc["embedding"]
    target_name = target_doc.get("card_name")
    
    if not target_vector:
        return
        
    target_dim = len(target_vector)
    similar_candidates = []
    
    # Vectorized similarity check against all cached embeddings
    if HAS_NUMPY:
        vectors = [emb["embedding"] for emb in all_embeddings_cached if len(emb["embedding"]) == target_dim]
        oracle_ids = [emb["oracle_id"] for emb in all_embeddings_cached if len(emb["embedding"]) == target_dim]
        
        if vectors:
            X = np.array(vectors, dtype=np.float32)
            # Normalize target vector
            v_norm = np.array(target_vector, dtype=np.float32)
            v_norm_len = np.linalg.norm(v_norm)
            if v_norm_len > 0:
                v_norm = v_norm / v_norm_len
                
            # Normalize candidate vectors
            norms = np.linalg.norm(X, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            X_norm = X / norms
            
            # Dot product for all similarities
            sims = np.dot(X_norm, v_norm)
            
            for idx, sim in enumerate(sims):
                cand_oid = oracle_ids[idx]
                if cand_oid == target_oid:
                    continue
                if sim >= threshold:
                    similar_candidates.append((float(sim), cand_oid))
    else:
        # Fallback comparison loop
        for emb in all_embeddings_cached:
            cand_oid = emb["oracle_id"]
            if cand_oid == target_oid:
                continue
            vector = emb["embedding"]
            if not vector or len(vector) != target_dim:
                continue
            sim = cosine_similarity(target_vector, vector)
            if sim >= threshold:
                similar_candidates.append((sim, cand_oid))
                
    # Sort and take top matches (e.g. up to 10)
    similar_candidates.sort(key=lambda x: x[0], reverse=True)
    top_links = similar_candidates[:10]
    
    # Store synergies for this card
    synergy_doc = {
        "oracle_id": target_oid,
        "card_name": target_name,
        "slug": target_doc.get("slug"),
        "synergies": [{"oracle_id": oid, "similarity": round(sim, 4)} for sim, oid in top_links],
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    
    db["card_synergies"].replace_one(
        {"oracle_id": target_oid},
        synergy_doc,
        upsert=True
    )
    
    # Print discoveries to console
    if top_links:
        log(f"Processed '{target_name}' -> found {len(top_links)} synergies (best: {top_links[0][0]:.2f})")

def rebuild_dashboard_insights(db):
    """
    Compiles a lightweight global dashboard view from precalculated synergies
    without loading full vectors.
    """
    log("Compiling lightweight dashboard insights...")
    
    # Fetch card details to map name/slugs
    card_cursor = db["cards"].find({}, {
        "oracle_id": 1, "name": 1, "slug": 1, "colors": 1, "type_line": 1, "priority": 1, "base_priority": 1
    })
    card_meta = {c["oracle_id"]: c for c in card_cursor if c.get("oracle_id")}
    
    synergies_cursor = list(db["card_synergies"].find({}))
    
    nodes = []
    links = []
    degree_counts = {}
    synergy_candidates = []
    
    for doc in synergies_cursor:
        oid = doc["oracle_id"]
        meta = card_meta.get(oid)
        if not meta:
            continue
            
        nodes.append({
            "id": oid,
            "name": meta["name"],
            "slug": meta["slug"],
            "colors": meta.get("colors") or [],
            "type": meta.get("type_line") or "",
            "cluster_id": 0 # Default cluster
        })
        
        degree_counts[oid] = len(doc.get("synergies", []))
        
        for link in doc.get("synergies", []):
            target_oid = link["oracle_id"]
            sim = link["similarity"]
            
            # Avoid duplicate links
            if oid < target_oid:
                links.append({
                    "source": oid,
                    "target": target_oid,
                    "similarity": sim
                })
                
            # Check for hidden/low-priority synergy
            target_meta = card_meta.get(target_oid)
            if target_meta:
                is_low_priority = (meta.get("base_priority", 0) < 10 or meta.get("priority", 0) < 10) or \
                                   (target_meta.get("base_priority", 0) < 10 or target_meta.get("priority", 0) < 10)
                if is_low_priority:
                    synergy_candidates.append({
                        "card_a": {"name": meta["name"], "slug": meta["slug"], "oracle_id": oid},
                        "card_b": {"name": target_meta["name"], "slug": target_meta["slug"], "oracle_id": target_oid},
                        "similarity": sim
                    })
                    
    # Format hot cards list
    hot_cards = []
    for oid, deg in degree_counts.items():
        meta = card_meta.get(oid)
        if meta:
            hot_cards.append({
                "oracle_id": oid,
                "name": meta["name"],
                "slug": meta["slug"],
                "degree": deg,
                "avg_similarity": 0.85, # placeholder
                "priority": meta.get("priority", 0)
            })
    hot_cards.sort(key=lambda x: x["degree"], reverse=True)
    
    # Sort synergies
    synergy_candidates.sort(key=lambda x: x["similarity"], reverse=True)
    
    stats = {
        "total_nodes": len(nodes),
        "total_edges": len(links),
        "average_similarity": 0.85,
        "clusters_count": 0,
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    
    db["research_insights"].replace_one(
        {"_id": "global_insights"},
        {
            "_id": "global_insights",
            "stats": stats,
            "nodes": nodes[:1000], # Cap graph nodes to keep visualizer fast
            "links": links[:3000],
            "clusters": [],
            "hot_cards": hot_cards[:30],
            "little_known_synergies": synergy_candidates[:30]
        },
        upsert=True
    )
    log("Dashboard insights compiled.")

def run_incremental_mode(interval=5, threshold=0.82):
    db = get_mongo_db()
    
    # Ensure index on card_synergies
    db["card_synergies"].create_index("oracle_id", unique=True)
    
    log("Abyss Walker running in 24/7 incremental stream mode.")
    
    # Cache all embeddings once to compare against new arrivals
    log("Caching active embeddings from database...")
    all_embeddings = list(db["card_embeddings"].find({}, {"oracle_id": 1, "embedding": 1, "card_name": 1, "slug": 1}))
    log(f"Cached {len(all_embeddings)} embeddings. Listening for new cards...")
    
    while True:
        try:
            # Find oracle_ids that already have calculated synergies
            processed_cursor = db["card_synergies"].find({}, {"oracle_id": 1})
            processed_ids = {doc["oracle_id"] for doc in processed_cursor}
            
            # Find embeddings that have not been processed yet
            unprocessed_docs = []
            for emb in all_embeddings:
                if emb["oracle_id"] not in processed_ids:
                    unprocessed_docs.append(emb)
                    
            if unprocessed_docs:
                log(f"Found {len(unprocessed_docs)} unprocessed cards. Chewing incrementally...")
                
                processed_count = 0
                for doc in unprocessed_docs:
                    process_single_card(db, doc, all_embeddings, threshold)
                    processed_count += 1
                    
                    # Yield thread execution
                    time.sleep(0.05)
                    
                log(f"Finished batch of {processed_count} cards.")
                rebuild_dashboard_insights(db)
                
            # Periodically poll for newly imported embeddings that aren't in our local cache
            # (Checking for embeddings created in the last day, or simply syncing count)
            if len(all_embeddings) < db["card_embeddings"].count_documents({}):
                log("New embeddings detected in database. Reloading local cache...")
                all_embeddings = list(db["card_embeddings"].find({}, {"oracle_id": 1, "embedding": 1, "card_name": 1, "slug": 1}))
                
        except Exception as e:
            log(f"Error during incremental processing loop: {e}")
            
        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="Abyss Walker - 24/7 Incremental Card Synergy Daemon")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval for new cards in seconds (default: 5)")
    parser.add_argument("--threshold", type=float, default=0.82, help="Cosine similarity threshold (default: 0.82)")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild global dashboard insights and exit")
    args = parser.parse_args()
    
    db = get_mongo_db()
    if args.rebuild:
        rebuild_dashboard_insights(db)
    else:
        run_incremental_mode(interval=args.interval, threshold=args.threshold)

if __name__ == "__main__":
    main()
