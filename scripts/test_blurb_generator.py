import os
import sys
import json
import re
from datetime import datetime
import urllib.request
from collections import Counter

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db

# ==========================================
# CONFIGURATION
# ==========================================
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "mistral-small3.2:24b")
SAMPLE_SETS_COUNT = 3
SAMPLE_ARTISTS_COUNT = 3

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

def call_ollama(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.4) -> str:
    """Send prompt to local Ollama instance and return stripped text."""
    url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": temperature,
            "num_predict": 350
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
    
    # Derive tense from release date
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
    
    # Track cards for popularity ranking
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

    # Sort Commander-legal vs non-Commander-legal
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

    # Prioritize signature / set-defining mechanics over generic evergreen keywords
    top_mechanics = [k for k, _ in signature_mechanics.most_common(5)]
    if not top_mechanics:
        top_mechanics = [k for k, _ in keywords.most_common(5)]

    top_artists = [a for a, _ in artists.most_common(5)]

    # Query total physical printings if available in card_prints
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

def format_set_facts_sentence(context: dict) -> str:
    """Deterministic factual sentence for set numbers."""
    y = context['released_at'][:4] if context['released_at'] != "Unknown" else ""
    verb = "released in" if context['is_released'] else "releasing in"
    time_clause = f"{context['set_name']} ({context['set_code']}), {verb} {y}" if y else f"{context['set_name']} ({context['set_code']})"

    counts_clause = f"contains {context['unique_oracle_cards']} unique Oracle cards across {context['total_physical_printings']} physical printings"
    
    r_dict = context.get('rarity_distribution', {})
    r_parts = []
    for r in ("Common", "Uncommon", "Rare", "Mythic"):
        if r in r_dict:
            r_parts.append(f"{r_dict[r]} {r.lower()}s")
    
    if len(r_parts) > 1:
        rarity_str = f", including {', '.join(r_parts[:-1])}, and {r_parts[-1]}"
    elif len(r_parts) == 1:
        rarity_str = f", including {r_parts[0]}"
    else:
        rarity_str = ""

    return f"{time_clause}, {counts_clause}{rarity_str}."

def possessive(name: str) -> str:
    """Deterministic possessive handling (e.g., Staples' vs Behm's)."""
    return f"{name}'" if name.endswith("s") else f"{name}'s"

def format_artist_facts_sentence(context: dict) -> str:
    """Deterministic factual sentence for artist numbers."""
    y1 = context['first_appearance'][:4] if context['first_appearance'] != "Unknown" else ""
    y2 = context['latest_appearance'][:4] if context['latest_appearance'] != "Unknown" else ""
    span_str = f"from {y1} to {y2}" if (y1 and y2 and y1 != y2) else (f"in {y1}" if y1 else "")
    
    timeline_clause = f"span {span_str}" if span_str else "span the Magic catalog"
    cards_label = "cards" if context['total_illustrations'] == context['unique_cards_count'] else f"card printings ({context['unique_cards_count']} unique cards)"
    name_pos = possessive(context['artist_name'])
    return f"{name_pos} Magic illustrations in AvaScry {timeline_clause}, encompassing {context['total_illustrations']} {cards_label} across {context['sets_count']} sets."

def generate_set_blurb(context: dict, model: str) -> str:
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

def generate_artist_blurb(context: dict, model: str) -> str:
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

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test AvaScry set & artist blurbs via local Ollama.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--sets", type=int, default=SAMPLE_SETS_COUNT, help="Number of sets to test")
    parser.add_argument("--artists", type=int, default=SAMPLE_ARTISTS_COUNT, help="Number of artists to test")
    parser.add_argument("--set-codes", nargs="*", help="Explicit set codes to test (e.g. gtc ori tdc)")
    parser.add_argument("--artist-names", nargs="*", help="Explicit artist names to test")
    parser.add_argument("--dry-run", action="store_true", help="Print context without calling Ollama")
    args = parser.parse_args()

    print(f"Connecting to MongoDB...")
    db = get_mongo_db()

    if args.set_codes:
        sampled_set_codes = [c.lower() for c in args.set_codes]
    else:
        print(f"Sampling {args.sets} sets with substantial card counts...")
        set_pipeline = [
            {"$match": {"lang": "en"}},
            {"$group": {"_id": "$set", "count": {"$sum": 1}, "name": {"$first": "$set_name"}}},
            {"$match": {"count": {"$gte": 80}}},
            {"$sample": {"size": args.sets}}
        ]
        sampled_set_codes = [s["_id"] for s in db["cards"].aggregate(set_pipeline)]

    if args.artist_names:
        sampled_artist_names = args.artist_names
    else:
        print(f"Sampling {args.artists} artists with substantial card counts...")
        artist_pipeline = [
            {"$match": {"artist": {"$ne": None, "$nin": ["", "Unknown"]}}},
            {"$group": {"_id": "$artist", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gte": 30}}},
            {"$sample": {"size": args.artists}}
        ]
        sampled_artist_names = [a["_id"] for a in db["cards"].aggregate(artist_pipeline)]

    print(f"\nTarget Ollama Model: {args.model}")
    print(f"Dry Run: {args.dry_run}")

    if not args.dry_run:
        print(f"Warming up {args.model} (keep_alive: 1h)...")
        try:
            call_ollama("Hello", model=args.model)
            print("Model loaded and warm in VRAM.")
        except Exception as e:
            print(f"Warning: Could not warm up model: {e}")
    print("")

    # ==========================================
    # SET EVALUATION
    # ==========================================
    for set_code in sampled_set_codes:
        ctx = build_set_context(db, set_code)
        if not ctx:
            continue

        print("=" * 60)
        print(f"SET: {ctx['set_name']} ({ctx['set_code']})")
        print("=" * 60)
        print("STRUCTURED SOURCE CONTEXT:")
        notable_summary = [f"{c['name']} (EDH rank: {c['edh_rank']}, Pri: {c['priority']})" for c in ctx['notable_cards']]
        ctx_display = dict(ctx)
        ctx_display['notable_cards'] = notable_summary
        print(json.dumps(ctx_display, indent=2))
        print("\nGENERATED 2-PARAGRAPH BLURB:")
        if args.dry_run:
            p2 = format_notable_cards_paragraph(ctx['notable_cards'], mode=ctx.get('notable_mode', 'generic'))
            print(f"[DRY RUN - Paragraph 1 via Ollama skipped]\n\n{p2}")
        else:
            blurb = generate_set_blurb(ctx, model=args.model)
            print(blurb)
            word_count = len(blurb.split())
            print(f"\n[Total Word Count: {word_count}]")
        print("\n")

    # ==========================================
    # ARTIST EVALUATION
    # ==========================================
    for artist_name in sampled_artist_names:
        ctx = build_artist_context(db, artist_name)
        if not ctx:
            continue

        print("=" * 60)
        print(f"ARTIST: {ctx['artist_name']}")
        print("=" * 60)
        print("STRUCTURED SOURCE CONTEXT:")
        notable_summary = [f"{c['name']} (EDH rank: {c['edh_rank']}, Pri: {c['priority']})" for c in ctx['notable_cards']]
        ctx_display = dict(ctx)
        ctx_display['notable_cards'] = notable_summary
        print(json.dumps(ctx_display, indent=2))
        print("\nGENERATED 2-PARAGRAPH BLURB:")
        if args.dry_run:
            p2 = format_notable_cards_paragraph(ctx['notable_cards'], mode=ctx.get('notable_mode', 'generic'))
            print(f"[DRY RUN - Paragraph 1 via Ollama skipped]\n\n{p2}")
        else:
            blurb = generate_artist_blurb(ctx, model=args.model)
            print(blurb)
            word_count = len(blurb.split())
            print(f"\n[Total Word Count: {word_count}]")
        print("\n")

if __name__ == "__main__":
    main()
