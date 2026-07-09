import os
import sys
import re
import urllib.request
import json
import datetime
import hashlib
import argparse

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db

def slugify(s):
    if not s:
        return ""
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def normalize_whitespace(val):
    if not isinstance(val, str):
        return val
    # Normalize internal whitespaces, strip leading/trailing, keep lines clean
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in val.splitlines()]
    return "\n".join(line for line in lines if line)

def build_context_record(card):
    # Fields to include (only those useful for similarity)
    fields = [
        ("name", card.get("name")),
        ("mana_cost", card.get("mana_cost")),
        ("mana_value", card.get("cmc")),
        ("colors", card.get("colors") or card.get("raw", {}).get("colors")),
        ("color_identity", card.get("color_identity")),
        ("type_line", card.get("type_line")),
        ("oracle_text", card.get("oracle_text")),
        ("keywords", card.get("keywords")),
        ("power", card.get("power") or card.get("raw", {}).get("power")),
        ("toughness", card.get("toughness") or card.get("raw", {}).get("toughness")),
        ("loyalty", card.get("loyalty") or card.get("raw", {}).get("loyalty")),
        ("defense", card.get("defense") or card.get("raw", {}).get("defense")),
    ]
    
    context = {}
    for key, val in fields:
        if val is None:
            continue
        
        if isinstance(val, list):
            if not val:
                continue
            val = sorted([normalize_whitespace(str(item)) for item in val if item is not None])
            if not val:
                continue
        elif isinstance(val, str):
            val = normalize_whitespace(val)
            if not val:
                continue
        elif isinstance(val, (int, float)):
            if key == "mana_value":
                val = int(val)
        
        context[key] = val
        
    return context

def build_embedding_text(context):
    text_parts = []
    if "name" in context:
        text_parts.append(f"Name: {context['name']}")
    if "mana_cost" in context:
        text_parts.append(f"Mana Cost: {context['mana_cost']}")
    if "mana_value" in context:
        text_parts.append(f"Mana Value: {context['mana_value']}")
    
    # colors & color_identity special handling if empty
    colors = context.get("colors")
    if colors:
        text_parts.append(f"Colors: {', '.join(colors)}")
    else:
        text_parts.append("Colors: Colorless")
        
    color_identity = context.get("color_identity")
    if color_identity:
        text_parts.append(f"Color Identity: {', '.join(color_identity)}")
    else:
        text_parts.append("Color Identity: Colorless")
        
    if "type_line" in context:
        text_parts.append(f"Type Line: {context['type_line']}")
    if "oracle_text" in context:
        text_parts.append(f"Oracle Text: {context['oracle_text']}")
    if "keywords" in context:
        text_parts.append(f"Keywords: {', '.join(context['keywords'])}")
    if "power" in context:
        text_parts.append(f"Power: {context['power']}")
    if "toughness" in context:
        text_parts.append(f"Toughness: {context['toughness']}")
    if "loyalty" in context:
        text_parts.append(f"Loyalty: {context['loyalty']}")
    if "defense" in context:
        text_parts.append(f"Defense: {context['defense']}")
        
    return "\n".join(text_parts)

def get_context_hash(context):
    context_json = json.dumps(context, sort_keys=True)
    return hashlib.sha256(context_json.encode("utf-8")).hexdigest()

def ensure_embeddings_indexes(db):
    collection = db["card_embeddings"]
    collection.create_index(
        [("oracle_id", 1), ("embedding_model", 1), ("embedding_version", 1)],
        unique=True
    )
    collection.create_index("slug")
    collection.create_index("embedding_model")
    collection.create_index("embedding_version")
    collection.create_index("context_hash")

def _send_embed_request(url, text, model):
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
    with urllib.request.urlopen(req, timeout=60) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        embeddings = res_data.get("embeddings", [])
        if embeddings:
            return embeddings[0]
        embedding = res_data.get("embedding")
        if embedding:
            return embedding
        raise ValueError(f"Unexpected response structure from Ollama: {res_data}")

def call_ollama_embed(text, model):
    ollama_host = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    url = f"{ollama_host}/api/embed"
    try:
        return _send_embed_request(url, text, model)
    except urllib.error.HTTPError as e:
        if model == "qwen3-embedding" and e.code == 404:
            print("Model 'qwen3-embedding' not found. Retrying with 'qwen3-embedding:0.6b' fallback...")
            return _send_embed_request(url, text, "qwen3-embedding:0.6b")
        raise e
    except Exception as e:
        print(f"Error calling local Ollama embed: {e}")
        raise e

def _send_embed_batch_request(url, texts, model):
    data = {
        "model": model,
        "input": texts,
        "keep_alive": "1h"
    }
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode("utf-8"), 
        headers=headers, 
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        embeddings = res_data.get("embeddings", [])
        if embeddings:
            return embeddings
        embedding = res_data.get("embedding")
        if embedding:
            return [embedding]
        raise ValueError(f"Unexpected response structure from Ollama batch: {res_data}")

def call_ollama_embed_batch(texts, model):
    ollama_host = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    url = f"{ollama_host}/api/embed"
    try:
        return _send_embed_batch_request(url, texts, model)
    except urllib.error.HTTPError as e:
        if model == "qwen3-embedding" and e.code == 404:
            print("Model 'qwen3-embedding' not found. Retrying batch with 'qwen3-embedding:0.6b' fallback...")
            return _send_embed_batch_request(url, texts, "qwen3-embedding:0.6b")
        if e.code == 400 and len(texts) > 1:
            print(f"Ollama batch failed with 400 Bad Request (likely size/context limit exceeded for {len(texts)} items). Splitting batch in half...")
            mid = len(texts) // 2
            left = call_ollama_embed_batch(texts[:mid], model)
            right = call_ollama_embed_batch(texts[mid:], model)
            return left + right
        raise e
    except Exception as e:
        print(f"Error calling local Ollama batch embed: {e}")
        raise e


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Generate embeddings for one Oracle card.")
    parser.add_argument("card_name", type=str, help="Name of the card.")
    parser.add_argument("--model", type=str, default="qwen3-embedding:0.6b", help="Embedding model name.")
    parser.add_argument("--version", type=str, default="card_context_v1", help="Embedding pipeline version.")
    parser.add_argument("--force", action="store_true", help="Force regeneration of the embedding.")
    parser.add_argument("--dry-run", action="store_true", help="Print dry run details without writing to Mongo or calling Ollama.")
    args = parser.parse_args()

    db = get_mongo_db()
    ensure_embeddings_indexes(db)

    # Lookup card
    card = db["cards"].find_one({
        "$or": [
            {"name": args.card_name},
            {"slug": slugify(args.card_name)},
            {"name": {"$regex": f"^{re.escape(args.card_name)}$", "$options": "i"}}
        ]
    })

    if not card:
        print(f"Error: Card '{args.card_name}' not found in MongoDB.")
        sys.exit(1)

    oracle_id = card.get("oracle_id")
    if not oracle_id:
        print(f"Error: Card '{card['name']}' has no oracle_id.")
        sys.exit(1)

    normalized_context = build_context_record(card)
    embedding_text = build_embedding_text(normalized_context)
    context_hash = get_context_hash(normalized_context)

    if args.dry_run:
        print(f"Matched Card: {card['name']}")
        print("Normalized Context JSON:")
        print(json.dumps(normalized_context, indent=2))
        print("Embedding Text:")
        print(embedding_text)
        print(f"Context Hash: {context_hash}")
        # Print exit summary info for the user
        print("\n--- Dry Run Summary ---")
        print(f"Card Name: {card['name']}")
        print(f"Oracle ID: {oracle_id}")
        print(f"Context Hash: {context_hash}")
        return

    # Check existing embedding
    embeddings_col = db["card_embeddings"]
    existing = embeddings_col.find_one({
        "oracle_id": oracle_id,
        "embedding_model": args.model,
        "embedding_version": args.version
    })

    if existing and not args.force:
        if existing.get("context_hash") == context_hash:
            print(f"Skipping: Embedding for '{card['name']}' is up to date (hash matches).")
            print("\n--- Summary ---")
            print(f"Card Name: {card['name']}")
            print(f"Oracle ID: {oracle_id}")
            print(f"Context Hash: {context_hash}")
            print("Status: skipped")
            return
        else:
            print(f"Context hash changed for '{card['name']}'. Regenerating...")

    # Call Ollama
    print(f"Generating embedding using Ollama model '{args.model}'...")
    embedding = call_ollama_embed(embedding_text, args.model)
    dimensions = len(embedding)

    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "oracle_id": oracle_id,
        "card_name": card["name"],
        "slug": card["slug"],
        "embedding_model": args.model,
        "embedding_version": args.version,
        "context_hash": context_hash,
        "context": normalized_context,
        "embedding": embedding,
        "dimensions": dimensions,
        "updated_at": now
    }

    if existing:
        embeddings_col.update_one(
            {"_id": existing["_id"]},
            {"$set": doc}
        )
        status = "updated"
        print(f"Updated embedding for '{card['name']}' in MongoDB.")
    else:
        doc["created_at"] = now
        embeddings_col.insert_one(doc)
        status = "created"
        print(f"Stored embedding for '{card['name']}' in MongoDB.")

    print("\n--- Summary ---")
    print(f"Card Name: {card['name']}")
    print(f"Oracle ID: {oracle_id}")
    print(f"Context Hash: {context_hash}")
    print(f"Embedding Dimensions: {dimensions}")
    print(f"Status: {status}")

if __name__ == "__main__":
    main()
