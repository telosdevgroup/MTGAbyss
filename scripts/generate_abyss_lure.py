import os
import sys
import urllib.request
import urllib.parse
import json
import datetime

# Add parent directory and scripts directory to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db, ensure_indexes
from scripts.lure_shared import slugify, clean_lure_text, build_lure_prompt, validate_lure_text

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_abyss_lure.py <commander_name>")
        sys.exit(1)
        
    card_name = sys.argv[1]
    db = get_mongo_db()
    ensure_indexes(db)
    
    # 1. Look up the named card in the existing Mongo cards collection.
    card = db["cards"].find_one({
        "$or": [
            {"name": card_name},
            {"slug": slugify(card_name)}
        ]
    })
    
    if not card:
        print(f"Error: Card '{card_name}' not found in MongoDB.")
        sys.exit(1)
        
    prompt, facts = build_lure_prompt(card)

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "mistral-small3.2:24b",
        "prompt": prompt,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": 0.7
        }
    }
    
    print(f"Calling Ollama at {url} to generate Lure for '{facts['name']}'...")
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw_text = res_data.get("response", "").strip()
    except Exception as e:
        print(f"Error calling local Ollama: {e}")
        sys.exit(1)
        
    cleaned_text = clean_lure_text(raw_text)
    
    # Run validation check as well (informative/warning for single script)
    is_valid, validation_err = validate_lure_text(cleaned_text, facts['name'])
    if not is_valid:
        print(f"Warning: Lure text failed validation check: {validation_err}")
    
    # Store in Mongo
    now = datetime.datetime.now(datetime.timezone.utc)
    oracle_id = card.get("oracle_id")
    slug = card.get("slug") or slugify(facts['name'])
    
    lure_doc = {
        "entity_type": "commander",
        "oracle_id": oracle_id,
        "card_name": facts['name'],
        "slug": slug,
        "content": {
            "lure": {
                "status": "generated",
                "text": cleaned_text,
                "model_provider": "ollama",
                "model": "mistral-small3.2:24b",
                "prompt_version": "abyss_lure_v1",
                "temperature": 0.7,
                "created_at": now.isoformat() + "Z" if now.tzinfo else now.isoformat(),
                "updated_at": now.isoformat() + "Z" if now.tzinfo else now.isoformat()
            }
        },
        "created_at": now.isoformat() + "Z" if now.tzinfo else now.isoformat(),
        "updated_at": now.isoformat() + "Z" if now.tzinfo else now.isoformat()
    }
    
    # Upsert by entity_type + oracle_id
    db["abysses"].update_one(
        {"entity_type": "commander", "oracle_id": oracle_id},
        {"$set": lure_doc},
        upsert=True
    )
    
    print("\nGenerated Lure:")
    print("-" * 40)
    print(cleaned_text)
    print("-" * 40)

if __name__ == "__main__":
    main()
