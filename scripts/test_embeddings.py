import os
import sys
import re
import math
import urllib.request
import urllib.error
import json
import argparse
import random

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def slugify(s):
    if not s:
        return ""
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

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

def get_ollama_embedding(text, model="qwen3-embedding:0.6b"):
    url = "http://localhost:11434/api/embed"
    data = {
        "model": model,
        "input": text,
        "keep_alive": "1h"
    }
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            embeddings = res_data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
            embedding = res_data.get("embedding")
            if embedding:
                return embedding
            raise ValueError(f"Unexpected response structure from Ollama: {res_data}")
    except urllib.error.HTTPError as e:
        if model == "qwen3-embedding" and e.code == 404:
            return get_ollama_embedding(text, "qwen3-embedding:0.6b")
        raise e

def find_card(db, name_or_query):
    slug = slugify(name_or_query)
    card = db["cards"].find_one({"name": name_or_query})
    if not card:
        card = db["cards"].find_one({"slug": slug})
    if not card:
        card = db["cards"].find_one({"name": {"$regex": f"^{re.escape(name_or_query)}$", "$options": "i"}})
    return card

def find_nearest_neighbors(target_embedding, target_oracle_id, all_embeddings, top_n):
    results = []
    skipped_count = 0
    target_dim = len(target_embedding)
    
    for emb_doc in all_embeddings:
        if emb_doc.get("oracle_id") == target_oracle_id:
            continue
            
        vector = emb_doc.get("embedding")
        if not vector or not isinstance(vector, list):
            skipped_count += 1
            continue
            
        if len(vector) != target_dim:
            skipped_count += 1
            continue
            
        sim = cosine_similarity(target_embedding, vector)
        results.append((sim, emb_doc))
        
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_n], len(results), skipped_count

def format_card_type(card):
    return card.get("type_line") or card.get("raw", {}).get("type_line") or "Unknown"

def get_card_name_by_oracle_id(db, oracle_id):
    card = db["cards"].find_one({"oracle_id": oracle_id})
    return card.get("name") if card else "Unknown Card"

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Embeddings test & playground script.")
    parser.add_argument("--stats", action="store_true", help="Print stats about cards and embeddings.")
    parser.add_argument("--card", type=str, help="Find nearest neighbors for a card.")
    parser.add_argument("--query", type=str, help="Find nearest neighbors for a text query using Ollama.")
    parser.add_argument("--compare", nargs=2, metavar=("CARD1", "CARD2"), help="Compare cosine similarity between two cards.")
    parser.add_argument("--random", type=int, help="Sample N random cards and print their nearest neighbors.")
    parser.add_argument("--top", type=int, default=5, help="Number of nearest neighbors to print.")
    args = parser.parse_args()

    db = get_mongo_db()

    if args.stats:
        print("Calculating stats...")
        all_card_oracle_ids = set(db["cards"].distinct("oracle_id"))
        total_oracle_cards = len(all_card_oracle_ids)
        
        embeddings_cursor = db["card_embeddings"].find({}, {"oracle_id": 1, "dimensions": 1, "embedding_model": 1})
        embedded_oracle_ids = set()
        duplicate_oracle_ids = set()
        dimensions = set()
        models = set()
        
        for emb in embeddings_cursor:
            oid = emb.get("oracle_id")
            if oid in embedded_oracle_ids:
                duplicate_oracle_ids.add(oid)
            embedded_oracle_ids.add(oid)
            
            dim = emb.get("dimensions")
            if dim:
                dimensions.add(dim)
            model = emb.get("embedding_model")
            if model:
                models.add(model)

        missing_oracle_ids = all_card_oracle_ids - embedded_oracle_ids
        
        print(f"Total Oracle cards: {total_oracle_cards}")
        print(f"Total embeddings: {len(embedded_oracle_ids)}")
        print(f"Missing embeddings count: {len(missing_oracle_ids)}")
        print(f"Duplicate oracle_id embeddings count: {len(duplicate_oracle_ids)}")
        print(f"Embedding dimension(s) found: {list(dimensions)}")
        print(f"Model values found: {list(models)}")
        
        if missing_oracle_ids:
            print("\nFirst 5 missing card names:")
            missing_cards = db["cards"].find({"oracle_id": {"$in": list(missing_oracle_ids)[:5]}})
            seen_names = set()
            count = 0
            for card in missing_cards:
                name = card.get("name")
                if name not in seen_names:
                    seen_names.add(name)
                    print(f"- {name}")
                    count += 1
                    if count >= 5:
                        break

    elif args.card:
        print(f"Looking up card: {args.card}")
        card = find_card(db, args.card)
        if not card:
            print(f"Error: Card '{args.card}' not found.")
            sys.exit(1)
            
        oracle_id = card.get("oracle_id")
        emb_doc = db["card_embeddings"].find_one({"oracle_id": oracle_id})
        if not emb_doc or not emb_doc.get("embedding"):
            print(f"Error: Embedding for card '{card['name']}' not found.")
            sys.exit(1)
            
        target_embedding = emb_doc["embedding"]
        print(f"Selected: {card['name']}")
        print(f"oracle_id: {oracle_id}")
        print(f"Embedding dimension: {len(target_embedding)}")
        
        print("Loading candidate embeddings...")
        all_embeddings = list(db["card_embeddings"].find({}, {"oracle_id": 1, "embedding": 1, "card_name": 1}))
        
        neighbors, candidate_count, skipped_count = find_nearest_neighbors(
            target_embedding, oracle_id, all_embeddings, args.top
        )
        
        print(f"Compared against: {candidate_count} embeddings")
        if skipped_count > 0:
            print(f"Warning: Skipped {skipped_count} invalid or incompatible embeddings.")
            
        print("\nNearby in the Abyss:")
        for idx, (score, emb) in enumerate(neighbors, 1):
            c_detail = db["cards"].find_one({"oracle_id": emb["oracle_id"]})
            type_line = format_card_type(c_detail) if c_detail else "Unknown"
            name = c_detail.get("name") if c_detail else emb.get("card_name", "Unknown")
            print(f"{idx}. {score:.4f} | {name} | {type_line}")

    elif args.query:
        print(f"Querying Ollama for embedding of: '{args.query}'")
        try:
            query_embedding = get_ollama_embedding(args.query)
        except Exception as e:
            print(f"Error calling local Ollama: {e}")
            sys.exit(1)
            
        print(f"Query embedding dimension: {len(query_embedding)}")
        
        print("Loading candidate embeddings...")
        all_embeddings = list(db["card_embeddings"].find({}, {"oracle_id": 1, "embedding": 1, "card_name": 1}))
        
        neighbors, candidate_count, skipped_count = find_nearest_neighbors(
            query_embedding, None, all_embeddings, args.top
        )
        
        print(f"Compared against: {candidate_count} embeddings")
        if skipped_count > 0:
            print(f"Warning: Skipped {skipped_count} invalid or incompatible embeddings.")
            
        print("\nNearby in the Abyss:")
        for idx, (score, emb) in enumerate(neighbors, 1):
            c_detail = db["cards"].find_one({"oracle_id": emb["oracle_id"]})
            type_line = format_card_type(c_detail) if c_detail else "Unknown"
            name = c_detail.get("name") if c_detail else emb.get("card_name", "Unknown")
            print(f"{idx}. {score:.4f} | {name} | {type_line}")

    elif args.compare:
        card1_name, card2_name = args.compare
        print(f"Comparing: '{card1_name}' vs '{card2_name}'")
        
        c1 = find_card(db, card1_name)
        c2 = find_card(db, card2_name)
        
        if not c1:
            print(f"Error: Card '{card1_name}' not found.")
            sys.exit(1)
        if not c2:
            print(f"Error: Card '{card2_name}' not found.")
            sys.exit(1)
            
        emb1_doc = db["card_embeddings"].find_one({"oracle_id": c1["oracle_id"]})
        emb2_doc = db["card_embeddings"].find_one({"oracle_id": c2["oracle_id"]})
        
        if not emb1_doc or not emb1_doc.get("embedding"):
            print(f"Error: Embedding for card '{c1['name']}' not found.")
            sys.exit(1)
        if not emb2_doc or not emb2_doc.get("embedding"):
            print(f"Error: Embedding for card '{c2['name']}' not found.")
            sys.exit(1)
            
        v1 = emb1_doc["embedding"]
        v2 = emb2_doc["embedding"]
        
        if len(v1) != len(v2):
            print(f"Error: Vector dimensions do not match ({len(v1)} vs {len(v2)})")
            sys.exit(1)
            
        score = cosine_similarity(v1, v2)
        print(f"Similarity between '{c1['name']}' and '{c2['name']}': {score:.4f}")

    elif args.random:
        print("Loading candidate embeddings...")
        all_embeddings = list(db["card_embeddings"].find({}, {"oracle_id": 1, "embedding": 1, "card_name": 1}))
        if not all_embeddings:
            print("Error: No embeddings found in database.")
            sys.exit(1)
            
        sample_size = min(args.random, len(all_embeddings))
        samples = random.sample(all_embeddings, sample_size)
        
        print(f"Selected {sample_size} random sample(s):\n")
        for i, target_emb in enumerate(samples, 1):
            target_name = target_emb.get("card_name") or get_card_name_by_oracle_id(db, target_emb["oracle_id"])
            print(f"Sample {i}: {target_name} ({target_emb['oracle_id']})")
            
            neighbors, candidate_count, skipped_count = find_nearest_neighbors(
                target_emb["embedding"], target_emb["oracle_id"], all_embeddings, 5
            )
            
            for idx, (score, emb) in enumerate(neighbors, 1):
                c_detail = db["cards"].find_one({"oracle_id": emb["oracle_id"]})
                type_line = format_card_type(c_detail) if c_detail else "Unknown"
                name = c_detail.get("name") if c_detail else emb.get("card_name", "Unknown")
                print(f"  {idx}. {score:.4f} | {name} | {type_line}")
            print()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
