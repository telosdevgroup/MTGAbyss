import os
import sys
import re
import urllib.request
import urllib.parse
import json
import datetime

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db, ensure_indexes

def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def clean_lure_text(text):
    text = text.strip()
    # Remove outer quotes if the model wrapped the entire answer in quotes
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    # Reject obvious preambles
    preambles = [
        "here is the lure:",
        "here is a lure:",
        "here is the mtgabyss lure:",
        "here is the lure for this magic commander:",
        "here is the lure text:",
        "here is the generated lure:"
    ]
    text_lower = text.lower()
    for preamble in preambles:
        if text_lower.startswith(preamble):
            text = text[len(preamble):].strip()
            # Also clean again for quotes if they were inside the preamble
            if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                text = text[1:-1].strip()
            break
    return text

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
        
    # Build a source facts packet from the card
    facts = {
        "name": card.get("name"),
        "type_line": card.get("type_line"),
        "oracle_text": card.get("oracle_text"),
        "keywords": card.get("keywords", []),
        "color_identity": card.get("color_identity", []),
        "power": card.get("power") or card.get("raw", {}).get("power"),
        "toughness": card.get("toughness") or card.get("raw", {}).get("toughness")
    }
    
    # Format facts as a nice text block
    facts_str = f"Name: {facts['name']}\n"
    facts_str += f"Type: {facts['type_line']}\n"
    if facts['oracle_text']:
        facts_str += f"Oracle Text:\n{facts['oracle_text']}\n"
    if facts['keywords']:
        facts_str += f"Keywords: {', '.join(facts['keywords'])}\n"
    if facts['color_identity']:
        facts_str += f"Color Identity: {', '.join(facts['color_identity'])}\n"
    if facts['power'] is not None and facts['toughness'] is not None:
        facts_str += f"Power/Toughness: {facts['power']}/{facts['toughness']}\n"
        
    prompt = f"""Write an MTGAbyss Lure for this Magic commander.

The Lure is the first short AI-written text on a visual commander archive page. It should pull the reader into the commander’s Abyss.

Use the source facts, but do not mechanically list them.

Length:
2–4 sentences.
40–90 words.

Tone:
mystical, human, strange, elegant, ominous, intimate.

Voice:
Write like a quiet myth, a witness account, or a strange archive entry.

Do not:
- mention Magic: The Gathering
- mention EDHREC
- mention Commander format
- mention deckbuilding
- mention popularity
- mention rankings
- sound like a card review
- sound like a rules explanation
- claim this is official lore
- mechanically list abilities
- use phrases like “powerful commander,” “strategic value,” “game-changing,” “iconic,” or “synergy”

You may imply mechanics through imagery.
You may use exact mechanic words only if they feel natural.
Output only the Lure text.

Source facts:
{facts_str}
"""

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
