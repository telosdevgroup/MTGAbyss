import os
import sys
import re
import urllib.request
import urllib.parse
import json
import datetime
import argparse
import concurrent.futures
import threading

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

def clean_hook_text(text):
    text = text.strip()
    # Remove surrounding quotes if the whole hook is wrapped in quotes
    while (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
        
    # Reject obvious preambles
    preambles = [
        "here is the hook:",
        "here is a hook:",
        "here is the mtgabyss hook:",
        "here is the hook for this card:",
        "here is the hook text:",
        "here is the generated hook:",
        "sure, here is",
        "sure, here's",
        "here is one short mtgabyss hook:",
        "here is a short mtgabyss hook:"
    ]
    text_lower = text.lower()
    for preamble in preambles:
        if text_lower.startswith(preamble):
            text = text[len(preamble):].strip()
            # Strip quotes again in case they were inside the preamble
            while (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                text = text[1:-1].strip()
            break
    return text

def get_sanitized_context(card):
    raw_ctx = {
        "name": card.get("name"),
        "mana_cost": card.get("mana_cost") or card.get("raw", {}).get("mana_cost"),
        "mana_value": card.get("raw", {}).get("mana_value") if card.get("raw", {}).get("mana_value") is not None else card.get("cmc"),
        "colors": card.get("raw", {}).get("colors"),
        "color_identity": card.get("color_identity") or card.get("raw", {}).get("color_identity"),
        "type_line": card.get("type_line") or card.get("raw", {}).get("type_line"),
        "oracle_text": card.get("oracle_text") or card.get("raw", {}).get("oracle_text"),
        "keywords": card.get("keywords") or card.get("raw", {}).get("keywords"),
        "power": card.get("power") or card.get("raw", {}).get("power"),
        "toughness": card.get("toughness") or card.get("raw", {}).get("toughness"),
        "loyalty": card.get("raw", {}).get("loyalty"),
        "defense": card.get("raw", {}).get("defense"),
    }
    
    # Omit null/empty fields, and normalize string values
    context = {}
    for k, v in raw_ctx.items():
         if v is None or v == "" or (isinstance(v, list) and not v):
             continue
         if isinstance(v, str):
             v = re.sub(r'\s+', ' ', v).strip()
         elif isinstance(v, list):
             v = [re.sub(r'\s+', ' ', item).strip() if isinstance(item, str) else item for item in v]
         context[k] = v
    return context

def build_prompt(context):
    facts_lines = []
    for k, v in context.items():
        if isinstance(v, list):
            v_str = ", ".join(v)
        else:
            v_str = str(v)
        facts_lines.append(f"{k}: {v_str}")
    facts_str = "\n".join(facts_lines)

    prompt = f"""Write one MTGAbyss Abyss Hook for this card.

MTGAbyss pages are Card X-rays: visual examinations of cards. The Hook is one short generated line or tiny paragraph that makes the card feel alive.

Use the source facts, but do not explain them.

Length:
1–3 sentences.
12–45 words.

Voice:
Sharp, strange, atmospheric, specific.

Write like:
- a strange museum label
- a tiny myth
- an object description from a cursed archive
- a sentence that makes the viewer stare at the card longer

Do not:
- mention Magic: The Gathering
- mention deckbuilding
- mention Commander
- mention EDHREC
- mention popularity
- mention rankings
- use strategy language
- explain the rules text
- mechanically list abilities
- say “this card”
- say “powerful”
- say “iconic”
- say “synergy”
- start with generic gothic filler like “Beneath,” “In the shadows,” “The air hums,” or “At the edge”

Prefer:
- one concrete image
- one sharp idea
- fewer words
- specificity over fog

Output only the Hook text.

Source facts:
{facts_str}
"""
    return prompt

def generate_hook_via_ollama(model, prompt, temperature):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": temperature
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=120) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        raw_text = res_data.get("response", "").strip()
        
    cleaned = clean_hook_text(raw_text)
    if not cleaned:
        raise ValueError("Ollama returned empty output or output cleaned to empty string.")
    return cleaned
 
class ProgressTracker:
    def __init__(self, total):
        self.total = total
        self.completed = 0
        self.lock = threading.Lock()

    def increment(self):
        with self.lock:
            self.completed += 1
            return self.completed, self.total - self.completed

def process_card_hook(db, card, args, tracker=None):
    name = card.get("name")
    oracle_id = card.get("oracle_id")
    slug = card.get("slug") or slugify(name)
    
    context = get_sanitized_context(card)
    prompt = build_prompt(context)
    
    prefix = ""
    if tracker:
        comp, rem = tracker.increment()
        prefix = f"({comp}/{rem}) "

    if args.dry_run:
        print(f"{prefix}[Dry Run] Would generate hook for '{name}' (oracle_id: {oracle_id})")
        return None
        
    try:
        cleaned_text = generate_hook_via_ollama(args.model, prompt, args.temperature)
    except Exception as e:
        print(f"{prefix}Error generating hook for '{name}': {e}")
        return None

    # Store in Mongo
    now = datetime.datetime.now(datetime.timezone.utc)
    now_str = now.isoformat() + "Z" if now.tzinfo else now.isoformat()
    
    # Read existing doc first
    existing_doc = db["abysses"].find_one({"entity_type": "card", "oracle_id": oracle_id})
    if existing_doc:
        db["abysses"].update_one(
            {"entity_type": "card", "oracle_id": oracle_id},
            {
                "$set": {
                    "content.hook": {
                        "status": "generated",
                        "text": cleaned_text,
                        "model": args.model,
                        "temperature": args.temperature,
                        "prompt_version": "abyss_hook_v1",
                        "created_at": existing_doc.get("content", {}).get("hook", {}).get("created_at") or now_str,
                        "updated_at": now_str
                    },
                    "updated_at": now_str
                }
            }
        )
    else:
        new_doc = {
            "entity_type": "card",
            "oracle_id": oracle_id,
            "card_name": name,
            "slug": slug,
            "content": {
                "hook": {
                    "status": "generated",
                    "text": cleaned_text,
                    "model": args.model,
                    "temperature": args.temperature,
                    "prompt_version": "abyss_hook_v1",
                    "created_at": now_str,
                    "updated_at": now_str
                }
            },
            "created_at": now_str,
            "updated_at": now_str
        }
        db["abysses"].insert_one(new_doc)
        
    print(f"{prefix}{name}: {cleaned_text}")
    return cleaned_text

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Python versions prior to 3.7 do not have reconfigure

    parser = argparse.ArgumentParser(description="Generate one or more Abyss Hooks.")
    parser.add_argument("card_name", nargs="?", default=None, help="Name of the card to generate a hook for.")
    parser.add_argument("--all", action="store_true", help="Generate hooks for all cards lacking one.")
    parser.add_argument("--model", default="mistral-small3.2:24b", help="Ollama model to use.")
    parser.add_argument("--temperature", type=float, default=0.75, help="Temperature for generation (0.70 to 0.80 recommended).")
    parser.add_argument("--force", action="store_true", help="Force regeneration and overwrite existing hook.")
    parser.add_argument("--dry-run", action="store_true", help="Print details without making Ollama calls or database writes.")
    parser.add_argument("--candidates", type=int, default=1, help="Number of candidate hooks to generate (only valid for single card, does not store if > 1).")
    parser.add_argument("--workers", type=int, default=1, help="Number of concurrent workers to use in bulk mode.")
    
    args = parser.parse_args()
    
    if not args.card_name and not args.all:
        parser.error("Either card_name or --all must be specified.")
        
    if args.all and args.candidates > 1:
        parser.error("--candidates mode is only supported when generating a hook for a single card.")
        
    if not (0.70 <= args.temperature <= 0.80):
        print(f"Warning: temperature {args.temperature} is outside the standard range of 0.75 +/- 0.05.")
        
    db = get_mongo_db()
    ensure_indexes(db)
    
    if args.all:
        print("Fetching cards from MongoDB...")
        # Get all cards
        all_cards = list(db["cards"].find({}, {
            "name": 1, "oracle_id": 1, "slug": 1, "mana_cost": 1, "cmc": 1, 
            "color_identity": 1, "type_line": 1, "oracle_text": 1, "keywords": 1, 
            "power": 1, "toughness": 1, "raw": 1
        }))
        
        # Get existing hooks to find what's already generated
        existing_abysses = {doc["oracle_id"]: doc for doc in db["abysses"].find({"entity_type": "card"})}
        
        cards_to_process = []
        for card in all_cards:
            oracle_id = card.get("oracle_id")
            if not oracle_id:
                continue
            has_hook = oracle_id in existing_abysses and existing_abysses[oracle_id].get("content", {}).get("hook", {}).get("text")
            if not has_hook or args.force:
                cards_to_process.append(card)
                
        print(f"Found {len(all_cards)} total cards. {len(cards_to_process)} cards need hook generation.")
        
        if not cards_to_process:
            print("No cards require hook generation.")
            return
            
        print(f"Starting bulk generation with {args.workers} workers...")
        tracker = ProgressTracker(len(cards_to_process))
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            # Map process_card_hook across all cards to process
            futures = {executor.submit(process_card_hook, db, card, args, tracker): card for card in cards_to_process}
            for future in concurrent.futures.as_completed(futures):
                card = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"Task for card '{card.get('name')}' raised an exception: {e}")
                    
        print("Bulk generation completed.")
        
    else:
        # Find single card
        card_name = args.card_name
        card = db["cards"].find_one({"name": card_name})
        if not card:
            card = db["cards"].find_one({"slug": slugify(card_name)})
        if not card:
            card = db["cards"].find_one({"name": {"$regex": f"^{re.escape(card_name)}$", "$options": "i"}})
            
        if not card:
            print(f"Error: Card '{card_name}' not found in MongoDB.")
            sys.exit(1)
            
        oracle_id = card.get("oracle_id")
        slug = card.get("slug") or slugify(card.get("name"))
        
        # Check existing hook
        existing_doc = db["abysses"].find_one({"entity_type": "card", "oracle_id": oracle_id})
        has_existing_hook = False
        if existing_doc and existing_doc.get("content", {}).get("hook", {}).get("text"):
            has_existing_hook = True
            
        if has_existing_hook and not args.force and args.candidates == 1:
            print(f"Hook already exists for '{card.get('name')}' (oracle_id: {oracle_id}). Use --force to regenerate.")
            print(f"Existing Hook: {existing_doc['content']['hook']['text']}")
            return
            
        # Build context and prompt
        context = get_sanitized_context(card)
        prompt = build_prompt(context)
        
        if args.dry_run:
            print("=== DRY RUN ===")
            print(f"Matched Card: {card.get('name')} (oracle_id: {oracle_id})")
            print("\nSanitized Context:")
            print(json.dumps(context, indent=2))
            print("\nFinal Prompt:")
            print("-" * 50)
            print(prompt)
            print("-" * 50)
            return
            
        if args.candidates > 1:
            print(f"Generating {args.candidates} candidate hooks for '{card.get('name')}' using model '{args.model}'...")
            for i in range(args.candidates):
                try:
                    hook = generate_hook_via_ollama(args.model, prompt, args.temperature)
                    print(f"{i + 1}. {hook}")
                except Exception as e:
                    print(f"Candidate {i + 1} failed: {e}")
            return
            
        # Standard single generation and storage
        process_card_hook(db, card, args)

if __name__ == "__main__":
    main()
