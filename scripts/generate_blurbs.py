import os
import sys
import json
import re
from datetime import datetime, timezone
import urllib.request
from collections import Counter
import argparse
import threading

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db

# ==========================================
# CONFIGURATION
# ==========================================
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "mistral-nemo:latest")

# Generic evergreen mechanics to exclude from "signature set mechanics"
GENERIC_KEYWORDS = {
    "flying", "enchant", "equip", "flash", "first strike", "double strike",
    "deathtouch", "lifelink", "trample", "vigilance", "reach", "defender",
    "haste", "indestructible", "hexproof", "shroud", "menace", "ward",
    "fight", "mill", "scry", "protection", "crew", "double"
}

def slugify(text: str) -> str:
    """Standard AvaScry card slugifier."""
    text = text.lower().strip()
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

def call_ollama(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.2) -> str:
    """Send prompt to local Ollama instance and return stripped text."""
    url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "num_ctx": 2048,
            "temperature": temperature,
            "num_predict": 250
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data.get("response", "").strip()

def format_notable_cards_paragraph(notable_cards: list, mode: str = "generic", artist_name: str = None) -> str:
    """Format Paragraph 2 with canonical AvaScry markdown links and conditional Commander copy."""
    if not notable_cards:
        return ""
    links = [f"[{c['name']}](https://avascry.com/card/{c['slug']})" for c in notable_cards]
    if len(links) == 1:
        cards_str = links[0]
    elif len(links) == 2:
        cards_str = f"{links[0]} and {links[1]}"
    else:
        cards_str = ", ".join(links[:-1]) + f", and {links[-1]}"

    by_artist = f" illustrated by {artist_name}" if artist_name else ""
    if mode in ("commander_4plus", "commander_partial"):
        return f"Notable Commander cards{by_artist} include {cards_str}."
    return f"Notable cards{by_artist} include {cards_str}."

def build_set_context(db, set_code: str) -> dict:
    """Aggregate structured corpus data for a set from cards collection."""
    cards_cursor = list(db["cards"].find(
        {"set": set_code, "lang": "en"},
        {"name": 1, "set": 1, "set_name": 1, "released_at": 1, "rarity": 1, "type_line": 1, "legalities": 1, 
         "keywords": 1, "color_identity": 1, "artist": 1, "base_priority": 1, "raw.edhrec_rank": 1}
    ))
    if not cards_cursor:
        cards_cursor = list(db["cards"].find(
            {"set": set_code},
            {"name": 1, "set": 1, "set_name": 1, "released_at": 1, "rarity": 1, "type_line": 1, "legalities": 1, 
             "keywords": 1, "color_identity": 1, "artist": 1, "base_priority": 1, "raw.edhrec_rank": 1}
        ))
    if not cards_cursor:
        return None

    set_name = cards_cursor[0].get("set_name") or set_code.upper()
    released_at = cards_cursor[0].get("released_at") or "Unknown"
    
    is_released = True
    if released_at != "Unknown":
        try:
            rel_date = datetime.strptime(released_at[:10], "%Y-%m-%d").date()
            if rel_date > datetime.now().date():
                is_released = False
        except Exception:
            pass

    rarities = Counter()
    keywords = Counter()
    signature_mechanics = Counter()
    colors = Counter()
    artists = Counter()
    
    cards_pool = {}
    for c in cards_cursor:
        name = c.get("name")
        if not name:
            continue
        rarities[(c.get("rarity") or "common").capitalize()] += 1
        t_line = c.get("type_line") or ""
        if "Adventure" in t_line:
            signature_mechanics["Adventure"] += 1
        for kw in (c.get("keywords") or []):
            keywords[kw] += 1
            if kw.lower() not in GENERIC_KEYWORDS:
                signature_mechanics[kw] += 1
        for col in (c.get("color_identity") or []):
            colors[col] += 1
        art = c.get("artist")
        if art:
            artists[art] += 1
            
        edh_rank = (c.get("raw") or {}).get("edhrec_rank")
        priority = c.get("base_priority", 0)
        is_cmdr = (c.get("legalities") or {}).get("commander") == "legal"
        
        if name not in cards_pool:
            cards_pool[name] = {
                "name": name,
                "slug": slugify(name),
                "edh_rank": edh_rank if edh_rank is not None else 999999,
                "priority": priority,
                "is_commander": is_cmdr
            }
        else:
            if is_cmdr:
                cards_pool[name]["is_commander"] = True
            if edh_rank is not None and edh_rank < cards_pool[name]["edh_rank"]:
                cards_pool[name]["edh_rank"] = edh_rank
            if priority > cards_pool[name]["priority"]:
                cards_pool[name]["priority"] = priority

    cmdr_legal = [c for c in cards_pool.values() if c["is_commander"]]
    cmdr_legal_sorted = sorted(cmdr_legal, key=lambda x: (x["edh_rank"], -x["priority"]))

    if len(cmdr_legal_sorted) >= 4:
        notable_cards = cmdr_legal_sorted[:4]
        notable_mode = "commander_4plus"
    elif len(cmdr_legal_sorted) >= 1:
        notable_cards = cmdr_legal_sorted
        notable_mode = "commander_partial"
    else:
        all_sorted = sorted(cards_pool.values(), key=lambda x: (x["edh_rank"], -x["priority"]))
        notable_cards = all_sorted[:4]
        notable_mode = "generic"

    top_mechanics = [k for k, _ in signature_mechanics.most_common(5)]
    if not top_mechanics:
        top_mechanics = [k for k, _ in keywords.most_common(5)]

    top_artists = [a for a, _ in artists.most_common(5)]

    total_physical_prints = db["card_prints"].count_documents({"set": set_code, "lang": "en"})
    if total_physical_prints == 0:
        total_physical_prints = db["card_prints"].count_documents({"set": set_code})

    return {
        "set_code": set_code.upper(),
        "set_name": set_name,
        "released_at": released_at,
        "is_released": is_released,
        "unique_oracle_cards": len(cards_cursor),
        "total_physical_printings": total_physical_prints if total_physical_prints > 0 else len(cards_cursor),
        "rarity_distribution": dict(rarities),
        "signature_mechanics": top_mechanics,
        "color_representation": dict(colors),
        "top_artists": top_artists,
        "notable_cards": notable_cards,
        "notable_mode": notable_mode
    }

def generate_set_blurb(context: dict, model: str = DEFAULT_MODEL) -> str:
    r_at = context.get('released_at') or "Unknown"
    y = r_at[:4] if r_at != "Unknown" else "Unknown"
    date_str = f"released in {y}" if (y != "Unknown" and context['is_released']) else (f"scheduled for release in {y}" if y != "Unknown" else "available in AvaScry")
    total_cards = context.get('total_physical_printings') or context.get('unique_oracle_cards') or 0
    mechanics_str = ', '.join(context['signature_mechanics'][:3]) if context['signature_mechanics'] else 'standard gameplay'
    artists_str = ', '.join(context['top_artists'][:3])

    prompt = f"""Rewrite AvaScry set introductions to feel like compact destination-page introductions rather than database summaries.

Use only the supplied structured facts. Do not invent biography, reputation, art style, design intent, historical significance, gameplay quality, or subjective criticism.
Do not infer significance, popularity, visual quality, gameplay quality, historical importance, set classification, or design intent.
If a relationship or characterization is not explicitly present in the structured context, do not state it.
Prefer plain factual connective prose over embellishment.

Tone: knowledgeable, concise, natural, MTG-native.
Length: roughly 35 to 55 words (2 actual sentences).

Context:
- Set Name: {context['set_name']}
- Set Code: {context['set_code']}
- Release Timing: {date_str}
- Card Printings: {total_cards}
- Signature Mechanics: {mechanics_str}
- Prominent Illustrators: {artists_str}

Rules:
1. Write exactly 2 natural, factual sentences for paragraph 1.
2. Sentence 1 should state the set name, set code, release year, and number of cards represented in AvaScry (e.g. "{context['set_name']} ({context['set_code']}), {date_str}, contains {total_cards} cards in AvaScry's catalog.").
3. Sentence 2 should plainly state the mechanics and mention 2 or 3 of the supplied illustrators.
4. BANNED PHRASES (DO NOT USE ANY OF THESE):
   - "visually striking"
   - "mechanically rich"
   - "fresh gameplay twists"
   - "designed for"
   - "standout"
   - "spanning from"
   - "cataloged works"
   - "brought to life"
   - "showcasing"
   - "renowned"
   - "iconic"
   - "popular expansions"
5. Output ONLY the 2 sentences. No headings, no quotes, no markdown, no second paragraph.
"""
    p1 = call_ollama(prompt, model=model, temperature=0.2).strip('"').strip()
    p2 = format_notable_cards_paragraph(context['notable_cards'], mode=context.get('notable_mode', 'generic'))
    return f"{p1}\n\n{p2}"

def build_artist_context(db, artist_name: str) -> dict:
    """Aggregate structured corpus data for an artist from cards collection."""
    cards_cursor = list(db["cards"].find(
        {"artist": artist_name, "lang": "en"},
        {"name": 1, "set": 1, "set_name": 1, "released_at": 1, "rarity": 1, "base_priority": 1, "legalities": 1, "raw.edhrec_rank": 1}
    ).sort("released_at", 1))

    if not cards_cursor:
        cards_cursor = list(db["cards"].find(
            {"artist": artist_name},
            {"name": 1, "set": 1, "set_name": 1, "released_at": 1, "rarity": 1, "base_priority": 1, "legalities": 1, "raw.edhrec_rank": 1}
        ).sort("released_at", 1))

    if not cards_cursor:
        return None

    total_printings = len(cards_cursor)
    sets_counter = Counter()
    release_dates = []
    cards_pool = {}

    for c in cards_cursor:
        s_name = c.get("set_name") or c.get("set", "").upper()
        sets_counter[s_name] += 1
        r_at = c.get("released_at")
        if r_at and r_at != "Unknown":
            release_dates.append(r_at)
        name = c.get("name")
        if not name:
            continue
        edh_rank = (c.get("raw") or {}).get("edhrec_rank")
        priority = c.get("base_priority", 0)
        is_cmdr = (c.get("legalities") or {}).get("commander") == "legal"

        if name not in cards_pool:
            cards_pool[name] = {
                "name": name,
                "slug": slugify(name),
                "edh_rank": edh_rank if edh_rank is not None else 999999,
                "priority": priority,
                "is_commander": is_cmdr
            }
        else:
            if is_cmdr:
                cards_pool[name]["is_commander"] = True
            if edh_rank is not None and edh_rank < cards_pool[name]["edh_rank"]:
                cards_pool[name]["edh_rank"] = edh_rank
            if priority > cards_pool[name]["priority"]:
                cards_pool[name]["priority"] = priority

    earliest_date = release_dates[0] if release_dates else "Unknown"
    latest_date = release_dates[-1] if release_dates else "Unknown"

    cmdr_legal = [c for c in cards_pool.values() if c["is_commander"]]
    cmdr_legal_sorted = sorted(cmdr_legal, key=lambda x: (x["edh_rank"], -x["priority"]))

    if len(cmdr_legal_sorted) >= 4:
        notable_cards = cmdr_legal_sorted[:4]
        notable_mode = "commander_4plus"
    elif len(cmdr_legal_sorted) >= 1:
        notable_cards = cmdr_legal_sorted
        notable_mode = "commander_partial"
    else:
        all_sorted = sorted(cards_pool.values(), key=lambda x: (x["edh_rank"], -x["priority"]))
        notable_cards = all_sorted[:4]
        notable_mode = "generic"

    top_sets = [f"{s} ({cnt})" for s, cnt in sets_counter.most_common(5)]

    return {
        "artist_name": artist_name,
        "total_illustrations": total_printings,
        "unique_cards_count": len(cards_pool),
        "sets_count": len(sets_counter),
        "first_appearance": earliest_date,
        "latest_appearance": latest_date,
        "top_sets": top_sets,
        "notable_cards": notable_cards,
        "notable_mode": notable_mode
    }

def generate_artist_blurb(context: dict, model: str = DEFAULT_MODEL) -> str:
    y1 = context['first_appearance'][:4] if context['first_appearance'] != "Unknown" else ""
    y2 = context['latest_appearance'][:4] if context['latest_appearance'] != "Unknown" else ""
    span_str = f"dating from {y1} through {y2}" if (y1 and y2 and y1 != y2) else (f"dating from {y1}" if y1 else "")
    
    top_sets_clean = [s.split(" (")[0] for s in context['top_sets'][:4]]
    top_sets_str = ", ".join(top_sets_clean)

    prompt = f"""Rewrite AvaScry artist introductions to feel like compact destination-page introductions rather than database summaries.

Use only the supplied structured facts. Do not invent biography, reputation, art style, design intent, historical significance, or subjective criticism.
Do not infer significance, popularity, artistic diversity, visual quality, or career scope.
If a relationship or characterization is not explicitly present in the structured context, do not state it.
Prefer plain factual connective prose over embellishment.

Tone: knowledgeable, concise, natural, MTG-native.
Length: roughly 35 to 55 words (2 actual sentences).

Context:
- Artist Name: {context['artist_name']}
- Representation: {context['total_illustrations']} illustrations across {context['sets_count']} sets
- Date Span: {span_str}
- Top Sets Represented: {top_sets_str}

Rules:
1. Write exactly 2 natural, well-metered sentences for paragraph 1.
2. Sentence 1 should state the artist name, number of sets, number of illustrations, and date span naturally (e.g. "{context['artist_name']}'s Magic artwork appears across {context['sets_count']} sets, with {context['total_illustrations']} illustrations {span_str}.").
3. Sentence 2 should naturally state their most represented sets using proper conjunctions (e.g. "Most represented sets include {top_sets_str[:-len(top_sets_clean[-1])]}and {top_sets_clean[-1]}." or "{context['artist_name']}'s most represented sets include...").
4. Do not infer pronouns (no 'he', 'she', 'his', 'her', or 'their'). Prefer '{context['artist_name']}' or the artist's surname.
5. BANNED PHRASES (DO NOT USE ANY OF THESE):
   - "reflecting a diverse range"
   - "key contributions"
   - "popular expansions"
   - "diverse range of creative work"
   - "spanning both core sets"
   - "visually striking"
   - "standout"
   - "cataloged works"
   - "spanning from"
   - "brought to life"
   - "showcasing"
   - "notable art by"
   - "prolific artist"
   - "renowned"
   - "iconic"
   - generic SEO filler
6. Output ONLY the 2 sentences. No headings, no quotes, no markdown, no second paragraph.
"""
    p1 = call_ollama(prompt, model=model, temperature=0.2).strip('"').strip()
    p2 = format_notable_cards_paragraph(context['notable_cards'], mode=context.get('notable_mode', 'generic'), artist_name=context['artist_name'])
    return f"{p1}\n\n{p2}"

def process_sets(db, limit: int = None, dry_run: bool = False, model: str = DEFAULT_MODEL, as_json: bool = False, force: bool = False, concurrency: int = 1):
    """Iterate over sets missing blurbs (or all sets if force=True) and populate."""
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    pipeline = [
        {"$group": {"_id": "$set", "name": {"$first": "$set_name"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    set_aggregates = list(db["cards"].aggregate(pipeline))
    
    pending = []
    for item in set_aggregates:
        set_code = (item["_id"] or "").lower().strip()
        if not set_code:
            continue
        if not force:
            existing = db["sets"].find_one({"code": set_code, "blurb": {"$exists": True, "$ne": None, "$ne": ""}})
            if existing:
                continue
        pending.append((set_code, item.get("name") or set_code.upper()))

    if limit:
        pending = pending[:limit]

    total_pending = len(pending)
    print(f"\nFound {total_pending} sets to process{' (force overwrite active)' if force else ''} with concurrency={concurrency}.")
    
    completed_count = 0
    lock = threading.Lock()

    def worker(idx, set_code, fallback_name):
        nonlocal completed_count
        t0 = time.time()
        try:
            ctx = build_set_context(db, set_code)
            if not ctx:
                return
            blurb = generate_set_blurb(ctx, model=model)
            elapsed = time.time() - t0
            now_iso = datetime.now(timezone.utc).isoformat()

            with lock:
                completed_count += 1
                curr_done = completed_count
                remaining = total_pending - curr_done

            commander_staples = [
                {
                    "name": c["name"],
                    "slug": c["slug"],
                    "url": f"https://avascry.com/card/{c['slug']}"
                }
                for c in ctx.get("notable_cards", [])
            ]

            result_obj = {
                "code": set_code,
                "name": ctx["set_name"],
                "blurb": blurb,
                "commander_staples": commander_staples,
                "blurb_model": model,
                "blurb_generated_at": now_iso
            }

            if as_json:
                out_msg = f"[BLURB {curr_done}/{total_pending} - {elapsed:.3f} sec | {remaining} left]:\n{json.dumps(result_obj, indent=2)}\n"
            else:
                out_msg = f"[BLURB {curr_done}/{total_pending} - {elapsed:.3f} sec | {remaining} left]:\n{blurb}\n"

            if not dry_run:
                db["sets"].update_one(
                    {"code": set_code},
                    {"$set": result_obj},
                    upsert=True
                )
                out_msg += f"[OK] Saved blurb for set {ctx['set_code']}\n"

            with lock:
                print(out_msg, flush=True)

        except Exception as e:
            elapsed = time.time() - t0
            with lock:
                print(f"[ERROR] Error generating blurb for set {set_code} ({elapsed:.3f} sec): {e}", flush=True)

    if concurrency > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker, i, sc, fn) for i, (sc, fn) in enumerate(pending, 1)]
            for f in as_completed(futures):
                pass
    else:
        for i, (sc, fn) in enumerate(pending, 1):
            worker(i, sc, fn)

def process_artists(db, limit: int = None, dry_run: bool = False, model: str = DEFAULT_MODEL, as_json: bool = False, force: bool = False, concurrency: int = 1):
    """Iterate over artists missing blurbs (or all artists if force=True) and populate."""
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    pipeline = [
        {"$match": {"artist": {"$exists": True, "$ne": None, "$ne": ""}}},
        {"$group": {"_id": "$artist", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    artist_aggregates = list(db["cards"].aggregate(pipeline))

    pending = []
    for item in artist_aggregates:
        artist_name = item["_id"]
        if not artist_name or re.search(r'unknown', artist_name, re.IGNORECASE):
            continue
        artist_slug = slugify(artist_name)
        if not force:
            existing = db["artists"].find_one({"slug": artist_slug, "blurb": {"$exists": True, "$ne": None, "$ne": ""}})
            if existing:
                continue
        pending.append((artist_name, artist_slug))

    if limit:
        pending = pending[:limit]

    total_pending = len(pending)
    print(f"\nFound {total_pending} artists to process{' (force overwrite active)' if force else ''} with concurrency={concurrency}.")
    
    completed_count = 0
    lock = threading.Lock()

    def worker(idx, artist_name, artist_slug):
        nonlocal completed_count
        t0 = time.time()
        try:
            ctx = build_artist_context(db, artist_name)
            if not ctx:
                return
            blurb = generate_artist_blurb(ctx, model=model)
            elapsed = time.time() - t0
            now_iso = datetime.now(timezone.utc).isoformat()

            with lock:
                completed_count += 1
                curr_done = completed_count
                remaining = total_pending - curr_done

            commander_staples = [
                {
                    "name": c["name"],
                    "slug": c["slug"],
                    "url": f"https://avascry.com/card/{c['slug']}"
                }
                for c in ctx.get("notable_cards", [])
            ]

            result_obj = {
                "name": artist_name,
                "slug": artist_slug,
                "blurb": blurb,
                "commander_staples": commander_staples,
                "blurb_model": model,
                "blurb_generated_at": now_iso
            }

            if as_json:
                out_msg = f"[BLURB {curr_done}/{total_pending} - {elapsed:.3f} sec | {remaining} left]:\n{json.dumps(result_obj, indent=2)}\n"
            else:
                out_msg = f"[BLURB {curr_done}/{total_pending} - {elapsed:.3f} sec | {remaining} left]:\n{blurb}\n"

            if not dry_run:
                db["artists"].update_one(
                    {"slug": artist_slug},
                    {"$set": result_obj},
                    upsert=True
                )
                out_msg += f"[OK] Saved blurb for artist {ctx['artist_name']}\n"

            with lock:
                print(out_msg, flush=True)

        except Exception as e:
            elapsed = time.time() - t0
            with lock:
                print(f"[ERROR] Error generating blurb for artist {artist_name} ({elapsed:.3f} sec): {e}", flush=True)

    if concurrency > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(worker, i, an, aslug) for i, (an, aslug) in enumerate(pending, 1)]
            for f in as_completed(futures):
                pass
    else:
        for i, (an, aslug) in enumerate(pending, 1):
            worker(i, an, aslug)

def main():
    parser = argparse.ArgumentParser(description="Lean, durable blurb generator for sets & artists.")
    parser.add_argument("--mode", choices=["sets", "artists", "all"], default="all", help="Target entity type")
    parser.add_argument("--limit", type=int, default=None, help="Stop after generating N blurbs")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true", help="Print blurb to console without updating MongoDB")
    parser.add_argument("--json", action="store_true", help="Display final generated blurb payload as JSON")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing blurbs")
    parser.add_argument("-c", "--concurrency", type=int, default=1, help="Number of concurrent workers (e.g. 2 or 3)")
    args = parser.parse_args()

    print(f"Connecting to MongoDB...", flush=True)
    db = get_mongo_db()

    print(f"Target Model: {args.model}", flush=True)
    print(f"Mode: {args.mode}", flush=True)
    print(f"Dry Run: {args.dry_run}", flush=True)
    print(f"Limit: {args.limit}", flush=True)
    print(f"Format: {'JSON' if args.json else 'Text'}", flush=True)
    print(f"Force Overwrite: {args.force}", flush=True)
    print(f"Concurrency: {args.concurrency}", flush=True)

    if args.mode in ("sets", "all"):
        process_sets(db, limit=args.limit, dry_run=args.dry_run, model=args.model, as_json=args.json, force=args.force, concurrency=args.concurrency)

    if args.mode in ("artists", "all"):
        process_artists(db, limit=args.limit, dry_run=args.dry_run, model=args.model, as_json=args.json, force=args.force, concurrency=args.concurrency)

    print("\nProcessing complete.", flush=True)

if __name__ == "__main__":
    main()