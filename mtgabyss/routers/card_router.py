import re
import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import Optional
from fastapi import APIRouter, Request, Query, BackgroundTasks, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from db_mongo import get_mongo_db
from mtgabyss.shared.helpers import (
    slugify, safe_header_segment, slug_to_name_regex, find_card_by_slug,
    resolve_card_images, build_card_view_model, templates
)
from mtgabyss.shared.cache import RAM_CACHE, set_ram_cache

card_router = APIRouter()

KNOWN_LANG_CODES = {'ja', 'de', 'fr', 'es', 'it', 'pt', 'ru', 'ko', 'zhs', 'zht'}
_MECHANICS_MAP = None
_KNOWN_SET_CODES: Optional[set] = None

def _get_known_set_codes(db) -> set:
    global _KNOWN_SET_CODES
    if _KNOWN_SET_CODES is None:
        try:
            _KNOWN_SET_CODES = set(s["code"].lower() for s in db["sets"].find({}, {"code": 1}))
        except Exception:
            _KNOWN_SET_CODES = set()
    return _KNOWN_SET_CODES

@card_router.get("/vector/{identifier}", include_in_schema=False)
@card_router.get("/vector/{identifier}.json", include_in_schema=False)
async def vector_embedding(identifier: str):
    """Expose raw 4096-dimensional Qwen 8B vector embedding for a card."""
    clean_id = identifier.lower().replace(".json", "").strip()
    if not clean_id or clean_id in ("", ".", "..", ".md", ".json"):
        raise HTTPException(status_code=404, detail="Vector embedding not found")

    db = get_mongo_db()

    # 1. Match by oracle_id or slug in card_embeddings_8b
    doc = db["card_embeddings_8b"].find_one({
        "$or": [
            {"oracle_id": clean_id},
            {"slug": clean_id},
            {"card_name": {"$regex": f"^{re.escape(clean_id.replace('-', ' '))}$", "$options": "i"}}
        ]
    })

    # 2. Resolve oracle_id via cards prints collection if identifier was printing-slug or name
    if not doc:
        card_doc = find_card_by_slug(db, clean_id)
        if card_doc and card_doc.get("oracle_id"):
            doc = db["card_embeddings_8b"].find_one({"oracle_id": card_doc["oracle_id"]})

    if not doc:
        raise HTTPException(status_code=404, detail="Vector embedding not found")

    oracle_id = doc.get("oracle_id")
    card_name = doc.get("card_name") or clean_id.replace('-', ' ').title()
    card_slug = doc.get("slug") or slugify(card_name)
    embedding = doc.get("embedding", [])

    return JSONResponse(
        content={
            "name": card_name,
            "oracle_id": oracle_id,
            "slug": card_slug,
            "model": doc.get("embedding_model") or "qwen3-embedding-8b",
            "dimensions": len(embedding) or 4096,
            "version": doc.get("embedding_version") or "1.0",
            "links": {
                "vector": f"https://avascry.com/vector/{card_slug}.json",
                "similar": f"https://avascry.com/similar/{card_slug}.json",
                "html": f"https://avascry.com/card/{card_slug}",
                "markdown": f"https://avascry.com/similar/{card_slug}.md"
            },
            "embedding": embedding
        },
        headers={
            "Vary": "Accept",
            "Link": f'</similar/{safe_header_segment(card_slug)}.json>; rel="related"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@card_router.get("/card/{slug}")
@card_router.head("/card/{slug}")
async def card_name_shortcut(request: Request, slug: str):
    """Clean shortcut redirecting /card/<name> to the primary/earliest Oracle printing of that card."""
    slug_clean = slug.strip().lower()
    if slug_clean in ("null", "undefined", "none") or slug_clean.startswith(("null.", "undefined.", "none.")):
        return RedirectResponse(url="/", status_code=301)

    # 0. Check in-memory RAM cache for previously resolved redirect target (<0.05ms)
    cache_key = f"card_redirect:{slug_clean}"
    if cache_key in RAM_CACHE:
        return RedirectResponse(url=RAM_CACHE[cache_key], status_code=303)

    ext = ""
    for check_ext in (".json", ".md", ".xml", ".csv"):
        if slug.lower().endswith(check_ext):
            ext = check_ext
            slug = slug[:-len(check_ext)]
            break

    db = get_mongo_db()
    card = None
    known_sets = _get_known_set_codes(db)

    # 1. Check if slug has a REAL set code suffix (e.g. "fractured-identity-c17" -> base="fractured-identity", set="c17")
    # Validating against known sets prevents treating card words like "ring" in "sol-ring" as a set code!
    if '-' in slug:
        parts = slug.split('-')
        potential_set = parts[-1].lower()
        if len(parts) >= 2 and potential_set in known_sets:
            card_slug = "-".join(parts[:-1])
            base_card = find_card_by_slug(db, card_slug)
            if base_card and base_card.get("oracle_id"):
                card = (
                    db["cards"].find_one({"oracle_id": base_card["oracle_id"], "set": potential_set, "lang": "en"})
                    or db["cards"].find_one({"oracle_id": base_card["oracle_id"], "set": potential_set})
                    or base_card
                )

    # 2. Fast direct lookup by slug, printing_slug, or card name (prefer English)
    if not card:
        card = (
            db["cards"].find_one({"slug": slug, "lang": "en"})
            or db["cards"].find_one({"printing_slug": slug, "lang": "en"})
            or db["cards"].find_one({"slug": slug})
            or db["cards"].find_one({"printing_slug": slug})
        )

    # 3. Fast lookup by full card name slug (e.g. "water-wurm" is the actual card name!)
    if not card:
        card = find_card_by_slug(db, slug)

    if card:
        oracle_id = card.get("oracle_id")
        if oracle_id:
            # Find canonical / earliest original Oracle printing in English
            oracle_card = db["cards"].find_one(
                {"oracle_id": oracle_id, "lang": "en"},
                sort=[("released_at", 1)]
            )
            if not oracle_card:
                # If no English print exists, fall back to earliest release
                oracle_card = db["cards"].find_one(
                    {"oracle_id": oracle_id},
                    sort=[("released_at", 1)]
                ) or card
            c_slug = slugify(oracle_card.get("name") or "")
            c_set = (oracle_card.get("set") or "").lower()
            target_url = f"/printing/{c_slug}-{c_set}{ext}"
            set_ram_cache(cache_key, target_url)
            return RedirectResponse(url=target_url, status_code=303)

    # Fallback to direct printing route
    fallback_url = f"/printing/{slug}{ext}"
    set_ram_cache(cache_key, fallback_url)
    return RedirectResponse(url=fallback_url, status_code=303)

def format_card_markdown(card_doc: dict, printings_count: int = 1, rulings: list = None, similar_cards: list = None, visual_artwork: dict = None) -> str:
    """Format structured, machine-native Markdown with YAML frontmatter for AI agents and LLMs."""
    name = card_doc.get("name", "Unknown Card")
    mana_cost = card_doc.get("mana_cost") or "N/A"
    cmc = card_doc.get("cmc", 0.0)
    type_line = card_doc.get("type_line", "")
    oracle_text = card_doc.get("oracle_text") or "(No Oracle text)"
    flavor_text = card_doc.get("flavor_text")
    power = card_doc.get("power")
    toughness = card_doc.get("toughness")
    loyalty = card_doc.get("loyalty")
    defense = card_doc.get("defense")
    set_name = card_doc.get("set_name", "")
    set_code = (card_doc.get("set") or "").upper()
    collector_number = card_doc.get("collector_number", "")
    rarity = (card_doc.get("rarity") or "common").lower()
    artist = card_doc.get("artist", "Unknown")
    legalities = card_doc.get("legalities", {})
    keywords = card_doc.get("keywords", [])
    colors = card_doc.get("colors") or []
    color_identity = card_doc.get("color_identity") or []
    oracle_id = card_doc.get("oracle_id", "")
    slug = card_doc.get("slug") or slugify(name)
    set_lower = (card_doc.get("set") or "").lower()
    printing_slug = f"{slug}-{set_lower}" if set_lower else slug

    # Construct YAML Frontmatter
    frontmatter_lines = [
        "---",
        f'name: "{name}"',
        f'mana_cost: "{mana_cost}"',
        f'cmc: {cmc:g}',
        f'type_line: "{type_line}"',
        f'colors: {json.dumps(colors)}',
        f'color_identity: {json.dumps(color_identity)}',
        f'keywords: {json.dumps(keywords)}',
        f'set: "{set_code}"',
        f'set_name: "{set_name}"',
        f'collector_number: "{collector_number}"',
        f'rarity: "{rarity}"',
        f'artist: "{artist}"',
        f'oracle_id: "{oracle_id}"',
        f'printings_count: {printings_count}',
        f'canonical_url: "https://avascry.com/printing/{printing_slug}"',
        "legalities:"
    ]
    key_formats = ["commander", "standard", "modern", "pioneer", "legacy", "vintage", "pauper", "penny"]
    for f in key_formats:
        status = legalities.get(f, "not_legal")
        frontmatter_lines.append(f'  {f}: "{status}"')
    frontmatter_lines.append("---")
    frontmatter_text = "\n".join(frontmatter_lines)

    lines = [
        frontmatter_text,
        f"\n# {name}",
        f"- **Mana Cost:** `{mana_cost}` (CMC: {cmc:g})",
        f"- **Type:** {type_line}",
    ]

    if power is not None and toughness is not None:
        lines.append(f"- **Power/Toughness:** {power}/{toughness}")
    if loyalty is not None:
        lines.append(f"- **Starting Loyalty:** {loyalty}")
    if defense is not None:
        lines.append(f"- **Defense:** {defense}")

    if keywords:
        lines.append(f"- **Keywords:** {', '.join(keywords)}")

    lines.append(f"\n## Oracle Text\n{oracle_text}\n")

    if flavor_text:
        lines.append(f"> *{flavor_text}*\n")

    if visual_artwork and visual_artwork.get("vision_observations"):
        obs = visual_artwork["vision_observations"]
        lines.append("## Visual Art Observations (Qwen3-VL 8B)")
        if obs.get("visual_summary"):
            lines.append(f"> *{obs['visual_summary']}*\n")
        if obs.get("subjects"):
            lines.append(f"- **Subjects:** {', '.join(obs['subjects'])}")
        if obs.get("setting"):
            lines.append(f"- **Setting:** {', '.join(obs['setting'])}")
        if obs.get("dominant_colors"):
            lines.append(f"- **Dominant Colors:** {', '.join(obs['dominant_colors'])}")
        if obs.get("style_descriptors"):
            lines.append(f"- **Style Descriptors:** {', '.join(obs['style_descriptors'])}")
        if obs.get("lighting"):
            lines.append(f"- **Lighting:** {obs['lighting']}")
        if obs.get("composition"):
            lines.append(f"- **Composition:** {obs['composition']}")
        if obs.get("mood_keywords"):
            lines.append(f"- **Atmospheric Mood:** {', '.join(obs['mood_keywords'])}")
        lines.append("")

    if visual_artwork and visual_artwork.get("top_neighbors"):
        sub_neighbors = visual_artwork["top_neighbors"].get("by_subject", [])
        if sub_neighbors:
            lines.append("## Top 7 Nearest Visual Neighbors (Qwen3-Embedding 4096-d)")
            for idx, vn in enumerate(sub_neighbors[:7], 1):
                vn_name = vn.get("card_name", "Card")
                vn_slug = vn.get("slug", "")
                vn_set = vn.get("set", "")
                vn_art = vn.get("artist", "")
                lines.append(f"{idx}. [{vn_name}](/printing/{vn_slug}.md) ({vn_set}) by {vn_art}")
            lines.append("")

    if similar_cards:
        lines.append("## Top 4096-Dim Neural Synergies")
        for idx, sc in enumerate(similar_cards[:6], 1):
            sc_n = sc.get("name")
            sc_slug = sc.get("slug")
            sc_type = sc.get("type_line", "")
            lines.append(f"{idx}. [{sc_n}](/printing/{sc_slug}.md) — {sc_type}")
        lines.append("")

    lines.append("## Printing Details")
    lines.append(f"- **Set:** {set_name} ({set_code}) #{collector_number}")
    lines.append(f"- **Rarity:** {rarity.capitalize()}")
    lines.append(f"- **Artist:** {artist}")
    if printings_count > 1:
        lines.append(f"- **Total Printings:** {printings_count} across all historical editions")

    # Format Key Legalities Table
    leg_list = [f"{f.capitalize()}: `{legalities.get(f, 'not_legal')}`" for f in key_formats if f in legalities]
    if leg_list:
        lines.append(f"\n## Format Legalities\n" + " | ".join(leg_list))

    if rulings:
        lines.append(f"\n## Official Rulings")
        for r in rulings[:6]:
            pub = r.get("published_at", "")
            comment = r.get("comment", "")
            lines.append(f"- *({pub})* {comment}")

    return "\n".join(lines)

def format_card_cockatrice_xml(card: dict) -> bytes:
    """Export single card printing as Cockatrice v4 XML database for desktop MTG simulators."""
    set_code = (card.get("set") or "unk").strip().upper()
    set_name = card.get("set_name") or set_code
    released_at = card.get("released_at") or "2026-01-01"

    root = ET.Element("cockatrice_carddatabase", version="4")
    sets_elem = ET.SubElement(root, "sets")
    set_elem = ET.SubElement(sets_elem, "set")
    ET.SubElement(set_elem, "name").text = set_code
    ET.SubElement(set_elem, "longname").text = set_name
    ET.SubElement(set_elem, "settype").text = "Expansion"
    ET.SubElement(set_elem, "releasedate").text = str(released_at)

    cards_elem = ET.SubElement(root, "cards")
    card_elem = ET.SubElement(cards_elem, "card")
    c_name = card.get("printed_name") or card.get("name") or "Card"
    ET.SubElement(card_elem, "name").text = c_name

    text = card.get("oracle_text") or card.get("printed_text")
    if not text and card.get("card_faces"):
        text = "\n//\n".join(f.get("oracle_text", "") or f.get("printed_text", "") for f in card["card_faces"])
    ET.SubElement(card_elem, "text").text = text or ""

    prop = ET.SubElement(card_elem, "prop")
    type_line = card.get("type_line") or ""
    ET.SubElement(prop, "type").text = type_line
    main_type = type_line.split("—")[0].strip().split()[-1] if type_line else "Card"
    ET.SubElement(prop, "maintype").text = main_type

    mana_cost = card.get("mana_cost")
    if not mana_cost and card.get("card_faces"):
        mana_cost = " // ".join(f.get("mana_cost", "") for f in card["card_faces"])
    ET.SubElement(prop, "manacost").text = mana_cost or ""
    ET.SubElement(prop, "cmc").text = str(int(card.get("cmc", 0.0)))
    ET.SubElement(prop, "colors").text = "".join(card.get("colors") or [])

    pt = f"{card.get('power')}/{card.get('toughness')}" if card.get("power") is not None else ""
    ET.SubElement(prop, "pt").text = pt
    ET.SubElement(prop, "loyalty").text = str(card.get("loyalty") or "")

    legalities = card.get("legalities") or {}
    for fmt in ["standard", "commander", "modern", "pioneer", "legacy", "vintage", "pauper"]:
        status = legalities.get(fmt, "not_legal")
        ET.SubElement(prop, f"format-{fmt}").text = "legal" if status == "legal" else ("banned" if status == "banned" else "not_legal")

    c_slug = card.get("slug") or slugify(card.get("name") or c_name)
    img_slug = card.get("image_slug") or f"{c_slug}-{set_code.lower()}"
    img_url = f"https://avascry.com/images/normal/{img_slug}.jpg"
    set_tag = ET.SubElement(card_elem, "set", picURL=img_url)
    set_tag.text = set_code

    t_low = type_line.lower()
    if "land" in t_low:
        tablerow = "0"
    elif "creature" in t_low:
        tablerow = "2"
    elif "planeswalker" in t_low or "battle" in t_low:
        tablerow = "3"
    else:
        tablerow = "1"
    ET.SubElement(card_elem, "tablerow").text = tablerow

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

def format_card_csv(card: dict) -> str:
    """Format single card printing as standard RFC 4180 CSV."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    headers = [
        "name", "set", "set_name", "collector_number", "rarity",
        "mana_cost", "cmc", "type_line", "oracle_text",
        "power", "toughness", "loyalty", "artist",
        "image_url", "canonical_url"
    ]
    writer.writerow(headers)

    c_name = card.get("name") or "Card"
    set_code = (card.get("set") or "").upper()
    set_name = card.get("set_name") or set_code
    collector_number = card.get("collector_number") or ""
    rarity = (card.get("rarity") or "common").capitalize()
    mana_cost = card.get("mana_cost") or ""
    if not mana_cost and card.get("card_faces"):
        mana_cost = " // ".join(f.get("mana_cost", "") for f in card["card_faces"])
    cmc = card.get("cmc", 0.0)
    type_line = card.get("type_line") or ""
    oracle_text = card.get("oracle_text") or ""
    if not oracle_text and card.get("card_faces"):
        oracle_text = " // ".join(f.get("oracle_text", "") for f in card["card_faces"])
    power = str(card.get("power") or "")
    toughness = str(card.get("toughness") or "")
    loyalty = str(card.get("loyalty") or "")
    artist = card.get("artist") or "Unknown"

    slug = card.get("slug") or slugify(c_name)
    set_lower = set_code.lower()
    printing_slug = f"{slug}-{set_lower}" if set_lower else slug
    img_slug = card.get("image_slug") or printing_slug
    img_url = f"https://avascry.com/images/normal/{img_slug}.jpg"
    canonical_url = f"https://avascry.com/printing/{printing_slug}"

    writer.writerow([
        c_name, set_code, set_name, collector_number, rarity,
        mana_cost, cmc, type_line, oracle_text,
        power, toughness, loyalty, artist,
        img_url, canonical_url
    ])
    return output.getvalue()

@card_router.get("/printing/{identifier}")
@card_router.head("/printing/{identifier}")
async def printing_detail(request: Request, identifier: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    card = None

    is_md = False
    is_json = False
    is_xml = False
    is_csv = False
    if identifier.lower().endswith(".md"):
        identifier = identifier[:-3]
        is_md = True
    elif identifier.lower().endswith(".json"):
        identifier = identifier[:-5]
        is_json = True
    elif identifier.lower().endswith(".xml"):
        identifier = identifier[:-4]
        is_xml = True
    elif identifier.lower().endswith(".csv"):
        identifier = identifier[:-4]
        is_csv = True

    identifier = identifier.strip()
    if identifier.lower() in ("null", "undefined", "none"):
        return RedirectResponse(url="/", status_code=301)
    if not identifier or identifier in ("", ".", "..", "-"):
        raise HTTPException(status_code=404, detail="Card printing not found")
    # Guard against punctuation-only strings unless it's the genuine unhinged card '_____'
    if not re.search(r'[a-zA-Z0-9]', identifier) and identifier != "_____":
        raise HTTPException(status_code=404, detail="Card printing not found")

    # Check RAM Cache first for resolved printing detail
    cache_key = f"print_card:{identifier.lower()}"
    if cache_key in RAM_CACHE:
        card = RAM_CACHE[cache_key]

    # 1. Direct indexed match by printing_slug or id or slug (prefer English)
    if not card:
        card = db["cards"].find_one({"printing_slug": identifier, "lang": "en"}) or db["cards"].find_one({"printing_slug": identifier})
    if not card:
        card = db["cards"].find_one({"id": identifier})
    if not card:
        card = db["cards"].find_one({"slug": identifier, "lang": "en"}) or db["cards"].find_one({"slug": identifier})

    # 2. Fast lookup by full slug before de-duplication (preserves double-named cards like Art Series and Reversible cards)
    # Skip if last token is a known language code (e.g., -fr, -de, -ko, -es, -zhs) to avoid 500ms regex scans on set codes
    if not card and '-' in identifier:
        parts = identifier.split('-')
        if len(parts) >= 3 and parts[-1].lower() in KNOWN_LANG_CODES:
            pass  # Handled directly by step 4 (3a) in 1ms!
        elif len(parts) >= 2:
            card_slug, set_code = "-".join(parts[:-1]), parts[-1].lower()
            base_card = find_card_by_slug(db, card_slug)
            if base_card:
                oid = base_card.get("oracle_id")
                if not oid and base_card.get("card_faces"):
                    oid = base_card["card_faces"][0].get("oracle_id")
                if oid:
                    card = db["cards"].find_one({"oracle_id": oid, "set": set_code, "lang": "en"}) or db["cards"].find_one({"oracle_id": oid, "set": set_code}) or db["cards"].find_one({"card_faces.oracle_id": oid, "set": set_code})
                if not card and base_card.get("set") == set_code:
                    card = base_card

    # 3. De-duplicate repeated double-slugs (e.g. urabrasks-forge-urabrasks-forge-aone -> urabrasks-forge-aone)
    clean_ident = identifier
    if not card and '-' in clean_ident:
        tokens = clean_ident.split('-')
        half = len(tokens) // 2
        for l in range(half, 0, -1):
            if tokens[:l] == tokens[l:2*l]:
                clean_ident = "-".join(tokens[l:])
                break

    # 4. Fast indexed lookup by oracle_id: <slug>-<set>-<lang> or <slug>-<set>
    if not card and '-' in clean_ident:
        parts = clean_ident.split('-')
        
        # 3a. Check <slug>-<set>-<lang>
        if len(parts) >= 3 and parts[-1].lower() in KNOWN_LANG_CODES:
            possible_lang = parts[-1].lower()
            possible_set = parts[-2].lower()
            card_slug = "-".join(parts[:-2])
            
            # Fast-path: Resolve base card via indexed slug/name to get oracle_id in 1ms
            base_card = find_card_by_slug(db, card_slug)
            if base_card and base_card.get("oracle_id"):
                oid = base_card["oracle_id"]
                # 1. Direct match on cards (indexed oracle_id + lang)
                card = db["cards"].find_one({"oracle_id": oid, "set": possible_set, "lang": possible_lang})
                if not card:
                    # 2. Match on card_prints (contains historical / localized prints)
                    cp_doc = db["card_prints"].find_one({"oracle_id": oid, "set": possible_set, "lang": possible_lang})
                    if cp_doc:
                        card = dict(base_card)
                        for k in ["id", "set", "set_name", "collector_number", "released_at", "lang", "image_uris", "image_slug", "card_faces", "printed_name", "flavor_text", "printed_text", "rarity", "artist"]:
                            if k in cp_doc and cp_doc[k] is not None:
                                card[k] = cp_doc[k]
                if not card:
                    # 3. Fallback to English print in that set
                    card = db["cards"].find_one({"oracle_id": oid, "set": possible_set, "lang": "en"})

        # 3b. Check <slug>-<set> (prefer English)
        if not card and len(parts) >= 2:
            card_slug, set_code = "-".join(parts[:-1]), parts[-1].lower()
            base_card = find_card_by_slug(db, card_slug)
            if base_card and base_card.get("oracle_id"):
                oid = base_card["oracle_id"]
                card = db["cards"].find_one({"oracle_id": oid, "set": set_code, "lang": "en"}) or db["cards"].find_one({"oracle_id": oid, "set": set_code})
                if not card:
                    cp_doc = db["card_prints"].find_one({"oracle_id": oid, "set": set_code})
                    if cp_doc:
                        card = dict(base_card)
                        for k in ["id", "set", "set_name", "collector_number", "released_at", "lang", "image_uris", "image_slug", "card_faces", "printed_name", "flavor_text", "printed_text", "rarity", "artist"]:
                            if k in cp_doc and cp_doc[k] is not None:
                                card[k] = cp_doc[k]
                if not card:
                    card = base_card

        # 3c. Fallback regex match if slug didn't resolve to known card
        if not card and len(parts) >= 2:
            possible_lang = parts[-1].lower() if len(parts) >= 3 and parts[-1].lower() in KNOWN_LANG_CODES else None
            set_code = parts[-2].lower() if possible_lang else parts[-1].lower()
            card_slug = "-".join(parts[:-2]) if possible_lang else "-".join(parts[:-1])
            pattern = slug_to_name_regex(card_slug)

            if possible_lang:
                card = db["cards"].find_one({"set": set_code, "lang": possible_lang, "name": pattern})
            if not card:
                card = db["cards"].find_one({"set": set_code, "lang": "en", "name": pattern})

            if not card:
                cp_query = {"set": set_code, "name": pattern}
                if possible_lang:
                    cp_query["lang"] = possible_lang
                cp_doc = db["card_prints"].find_one(cp_query)
                if not cp_doc and possible_lang:
                    cp_doc = db["card_prints"].find_one({"set": set_code, "name": pattern, "lang": "en"})

                if cp_doc and cp_doc.get("oracle_id"):
                    oracle_card = db["cards"].find_one({"oracle_id": cp_doc["oracle_id"], "lang": "en"}) or db["cards"].find_one({"oracle_id": cp_doc["oracle_id"]})
                    if oracle_card:
                        merged = dict(oracle_card)
                        for k in ["id", "set", "set_name", "collector_number", "released_at", "lang", "image_uris", "image_slug", "card_faces", "printed_name", "flavor_text", "printed_text", "rarity", "artist"]:
                            if k in cp_doc and cp_doc[k] is not None:
                                merged[k] = cp_doc[k]
                        card = merged

    # 4. Fallback match by stripping set/lang tokens and searching card name / slug (prefer English)
    if not card and '-' in clean_ident:
        parts = clean_ident.split('-')
        # Try progressively stripping trailing set / language codes
        for num_trailing in (2, 1):
            if len(parts) > num_trailing:
                base_slug = "-".join(parts[:-num_trailing])
                base_card = find_card_by_slug(db, base_slug)
                if base_card:
                    card = base_card
                    break
                pattern = slug_to_name_regex(base_slug)
                card = db["cards"].find_one({
                    "lang": "en",
                    "$or": [
                        {"slug": base_slug},
                        {"name": pattern},
                        {"card_faces.0.name": pattern}
                    ]
                }) or db["cards"].find_one({
                    "$or": [
                        {"slug": base_slug},
                        {"name": pattern},
                        {"card_faces.0.name": pattern}
                    ]
                })
                if card:
                    break

    # 5. Whole collection search by name (prefer English)
    if not card:
        pattern = slug_to_name_regex(clean_ident)
        card = db["cards"].find_one({
            "lang": "en",
            "$or": [
                {"name": pattern},
                {"card_faces.0.name": pattern}
            ]
        }) or db["cards"].find_one({
            "$or": [
                {"name": pattern},
                {"card_faces.0.name": pattern}
            ]
        })

    # 6. Fallback match via Scryfall API on-demand for newly spoiled or missing cards
    if not card and '-' in clean_ident:
        try:
            parts = clean_ident.split('-')
            guessed_set = parts[-1].lower() if len(parts) >= 2 else ""
            guessed_slug = "-".join(parts[:-1]) if len(parts) >= 2 else clean_ident
            guessed_name = " ".join(w.capitalize() for w in guessed_slug.split('-'))
            
            import urllib.request, urllib.parse
            from datetime import datetime, timezone
            scryfall_url = f"https://api.scryfall.com/cards/named?exact={urllib.parse.quote(guessed_name)}"
            if guessed_set and len(guessed_set) in (3, 4):
                scryfall_url += f"&set={guessed_set}"
            
            req = urllib.request.Request(
                scryfall_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            if data and data.get("id"):
                now = datetime.now(timezone.utc)
                set_code = (data.get("set") or "").lower()
                c_name = data.get("name")
                coll_num = data.get("collector_number", "")
                set_name = data.get("set_name", "")
                artist = data.get("artist", "Unknown")
                img_slug = f"{slugify(c_name)}-{slugify(set_name)}-{slugify(artist)}-{coll_num}"
                
                card_doc = {
                    "id": data["id"],
                    "oracle_id": data.get("oracle_id"),
                    "name": c_name,
                    "slug": slugify(c_name),
                    "printing_slug": f"{slugify(c_name)}-{set_code}",
                    "set": set_code,
                    "set_name": set_name,
                    "collector_number": coll_num,
                    "mana_cost": data.get("mana_cost"),
                    "cmc": data.get("cmc", 0),
                    "type_line": data.get("type_line"),
                    "oracle_text": data.get("oracle_text"),
                    "flavor_text": data.get("flavor_text"),
                    "power": data.get("power"),
                    "toughness": data.get("toughness"),
                    "loyalty": data.get("loyalty"),
                    "colors": data.get("colors", []),
                    "color_identity": data.get("color_identity", []),
                    "keywords": data.get("keywords", []),
                    "legalities": data.get("legalities", {}),
                    "rarity": data.get("rarity", ""),
                    "artist": artist,
                    "released_at": data.get("released_at", ""),
                    "lang": data.get("lang", "en"),
                    "image_slug": img_slug,
                    "imported_at": now,
                    "updated_at": now,
                    "source_hash": "",
                    "scryfall_uri": data.get("scryfall_uri"),
                    "layout": data.get("layout", "normal"),
                    "prices": data.get("prices", {})
                }
                cp_doc = {
                    "id": data["id"],
                    "oracle_id": data.get("oracle_id"),
                    "name": c_name,
                    "printed_name": data.get("printed_name"),
                    "lang": data.get("lang", "en"),
                    "set": set_code,
                    "set_name": set_name,
                    "collector_number": coll_num,
                    "rarity": data.get("rarity", ""),
                    "artist": artist,
                    "released_at": data.get("released_at", ""),
                    "image_uris": data.get("image_uris"),
                    "flavor_text": data.get("flavor_text"),
                    "printed_text": data.get("printed_text"),
                    "card_faces": data.get("card_faces"),
                    "imported_at": now,
                    "updated_at": now,
                    "source_hash": "",
                    "image_slug": img_slug
                }
                db["cards"].update_one({"id": data["id"]}, {"$set": card_doc}, upsert=True)
                db["card_prints"].update_one({"id": data["id"]}, {"$set": cp_doc}, upsert=True)
                card = card_doc

                # Also fetch and sync all multilingual prints for this newly imported card
                if data.get("oracle_id"):
                    try:
                        prints_url = f"https://api.scryfall.com/cards/search?q=oracleid:{data['oracle_id']}+include:multilingual&unique=prints"
                        p_req = urllib.request.Request(prints_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"})
                        with urllib.request.urlopen(p_req, timeout=4.0) as p_resp:
                            p_data = json.loads(p_resp.read().decode('utf-8'))
                        for item in p_data.get("data", []):
                            i_name = item.get("name")
                            i_set = item.get("set", "").lower()
                            i_coll = item.get("collector_number", "")
                            i_set_name = item.get("set_name", "")
                            i_artist = item.get("artist", "Unknown")
                            i_slug = f"{slugify(i_name)}-{slugify(i_set_name)}-{slugify(i_artist)}-{i_coll}"
                            db["card_prints"].update_one(
                                {"id": item["id"]},
                                {"$set": {
                                    "id": item["id"],
                                    "oracle_id": item.get("oracle_id"),
                                    "name": i_name,
                                    "printed_name": item.get("printed_name"),
                                    "lang": item.get("lang", "en"),
                                    "set": i_set,
                                    "set_name": i_set_name,
                                    "collector_number": i_coll,
                                    "rarity": item.get("rarity", ""),
                                    "artist": i_artist,
                                    "released_at": item.get("released_at", ""),
                                    "image_uris": item.get("image_uris"),
                                    "flavor_text": item.get("flavor_text"),
                                    "printed_text": item.get("printed_text"),
                                    "card_faces": item.get("card_faces"),
                                    "imported_at": now,
                                    "updated_at": now,
                                    "source_hash": "",
                                    "image_slug": i_slug
                                }},
                                upsert=True
                            )
                    except Exception:
                        pass
        except Exception:
            pass

    if not card:
        raise HTTPException(status_code=404, detail="Printing not found in the Abyss")
        
    set_ram_cache(cache_key, card)
    oracle_id = card.get("oracle_id")
    card_vm = build_card_view_model(card, db, background_tasks)
    
    # Load All Other Printings for this Oracle ID (cached by oracle_id in RAM_CACHE)
    printings = []
    sorted_lang_groups = []
    if oracle_id:
        raw_p_cache_key = f"raw_printings:{oracle_id}"
        if raw_p_cache_key in RAM_CACHE:
            raw_printings = RAM_CACHE[raw_p_cache_key]
        else:
            # If a card has thousands of printings (e.g. Basic Lands), cap cursor to the most recent 120 per language
            p_cursor = list(db["card_prints"].find({"oracle_id": oracle_id}).sort("released_at", -1))
            if not p_cursor:
                p_cursor = list(db["cards"].find({"oracle_id": oracle_id}).sort("released_at", -1))
            
            # Capping printings per language to prime 31 (16 newest + 15 classic vintage) for massive print lists (e.g. Forest, Island)
            by_lang = {}
            for p in p_cursor:
                l = (p.get("lang") or "en").lower()
                if l not in by_lang:
                    by_lang[l] = []
                by_lang[l].append(p)

            filtered_cursor = []
            for l, prints in by_lang.items():
                if len(prints) > 31:
                    filtered_cursor.extend(prints[:16] + prints[-15:])
                else:
                    filtered_cursor.extend(prints)

            raw_printings = []
            for p in filtered_cursor:
                p_name = p.get("name") or card.get("name") or "card"
                p_printed_name = p.get("printed_name") or p_name
                p_set = (p.get("set") or "").lower()
                p_slug = slugify(p_name)
                p_lang = (p.get("lang") or "en").lower()
                p_printing_slug = f"{p_slug}-{p_set}-{p_lang}" if p_lang != "en" else (f"{p_slug}-{p_set}" if p_set else p.get("id"))
                p_small_url, p_img_url, p_large_url = resolve_card_images(p, None)
                p_rarity = p.get("rarity") or card.get("rarity") or ""
                p_artist = p.get("artist") or card.get("artist") or "Unknown"
                FLAGS = {
                    'en': '🇺🇸', 'ja': '🇯🇵', 'fr': '🇫🇷', 'de': '🇩🇪',
                    'es': '🇪🇸', 'it': '🇮🇹', 'zhs': '🇨🇳', 'zht': '🇹🇼',
                    'pt': '🇧🇷', 'ru': '🇷🇺', 'ko': '🇰🇷'
                }
                raw_printings.append({
                    "id": p.get("id"),
                    "printing_slug": p_printing_slug,
                    "name": p_name,
                    "printed_name": p_printed_name,
                    "set_name": p.get("set_name", "Unknown"),
                    "set": p_set,
                    "collector_number": p.get("collector_number", "N/A"),
                    "rarity": p_rarity,
                    "lang": p_lang,
                    "lang_flag": FLAGS.get(p_lang, '🌐'),
                    "artist": p_artist,
                    "artist_slug": slugify(p_artist),
                    "released_at": p.get("released_at", ""),
                    "image_url": p_img_url,
                    "large_image_url": p_large_url or p_img_url,
                })
            set_ram_cache(raw_p_cache_key, raw_printings)

        # Make copy and assign is_current for this specific printing
        card_id = card.get("id")
        current_lang = (card.get("lang") or "en").lower()
        LANG_NAMES = {
            "en": "🇺🇸 English",
            "ja": "🇯🇵 日本語 (Japanese)",
            "de": "🇩🇪 Deutsch (German)",
            "fr": "🇫🇷 Français (French)",
            "it": "🇮🇹 Italiano (Italian)",
            "es": "🇪🇸 Español (Spanish)",
            "pt": "🇧🇷 Português (Portuguese)",
            "ru": "🇷🇺 Русский (Russian)",
            "ko": "🇰🇷 한국어 (Korean)",
            "zhs": "🇨🇳 简体中文 (Simplified Chinese)",
            "zht": "🇹🇼 繁體中文 (Traditional Chinese)"
        }

        lang_groups = {}
        for rp in raw_printings:
            p = dict(rp)
            p["is_current"] = (p["id"] == card_id)
            printings.append(p)
            l_code = p["lang"]
            if l_code not in lang_groups:
                lang_groups[l_code] = {
                    "lang_code": l_code,
                    "lang_name": LANG_NAMES.get(l_code, l_code.upper()),
                    "printings_list": [],
                    "has_current": False
                }
            lang_groups[l_code]["printings_list"].append(p)
            if p["is_current"]:
                lang_groups[l_code]["has_current"] = True

        # Sort language groups: active viewing language first, then English, then alphabetical
        sorted_lang_groups = sorted(
            lang_groups.values(),
            key=lambda g: (
                0 if g["has_current"] or g["lang_code"] == current_lang else (1 if g["lang_code"] == "en" else 2),
                g["lang_name"]
            )
        )
            
    # Load Rulings
    rulings = []
    if oracle_id:
        rulings = list(db["rulings"].find({"oracle_id": oracle_id}).sort("published_at", 1))

    # Mechanics & Tooltips (In-Memory Cache)
    mechanics = []
    try:
        global _MECHANICS_MAP
        if _MECHANICS_MAP is None:
            mech_cursor = list(db["mechanics"].find({}))
            _MECHANICS_MAP = {m["slug"]: m for m in mech_cursor}
        mechanics_map = _MECHANICS_MAP
        for kw in card.get("keywords", []):
            kw_slug = slugify(kw)
            mech_doc = mechanics_map.get(kw_slug)
            clean_kw_name = " ".join(w.capitalize() for w in kw.replace('-', ' ').replace('_', ' ').split())
            mechanics.append({
                "name": clean_kw_name,
                "definition": mech_doc.get("definition") if mech_doc else None
            })
    except Exception:
        pass

    # Lure
    lure = None
    try:
        abyss_doc = db["abysses"].find_one({"oracle_id": oracle_id})
        if abyss_doc:
            lure_data = abyss_doc.get("content", {}).get("lure", {})
            if lure_data.get("status") == "generated" and lure_data.get("text"):
                lure = {
                    "text": lure_data.get("text").strip(),
                    "persona": lure_data.get("persona", "Oracle")
                }
    except Exception:
        pass

    # Find Top 6 Highly Relevant Synergistic Cards from the 4096-Dim Neural Vector Brain
    similar_cards = []
    try:
        sim_doc = db["similar_cards"].find_one({"oracle_id": oracle_id})
        if sim_doc:
            similar_raw = sim_doc.get("similar", [])
            sim_oids = [s if isinstance(s, str) else s.get("oracle_id") for s in similar_raw]
            sim_oids = [oid for oid in sim_oids if oid and oid != oracle_id][:15]
            
            sim_cursor = list(db["cards"].find(
                {"oracle_id": {"$in": sim_oids}, "lang": "en"},
                {"name": 1, "slug": 1, "set": 1, "set_name": 1, "collector_number": 1, "image_uris": 1, "card_faces": 1, "type_line": 1, "mana_cost": 1, "oracle_id": 1, "image_slug": 1, "raw": 1}
            ))
            doc_map = {}
            for sc in sim_cursor:
                sc_oid = sc.get("oracle_id")
                if sc_oid and sc_oid not in doc_map:
                    doc_map[sc_oid] = sc
            
            for sc_oid in sim_oids:
                if sc_oid in doc_map:
                    sc = doc_map[sc_oid]
                    sc_name = sc.get("name") or "Card"
                    sc_set = (sc.get("set") or "").lower()
                    sc_slug = slugify(sc_name)
                    sc_p_slug = f"{sc_slug}-{sc_set}" if sc_set else sc_slug
                    _, sc_img_url, sc_large_url = resolve_card_images(sc, None)
                    sc_norm = sc_img_url
                    sc_large = sc_large_url

                    similar_cards.append({
                        "name": sc_name,
                        "slug": sc_p_slug,
                        "set_name": sc.get("set_name") or "",
                        "type_line": sc.get("type_line") or "",
                        "mana_cost": sc.get("mana_cost") or "",
                        "image_url": sc_norm,
                        "large_image_url": sc_large,
                        "image_uris": {
                            "normal": sc_norm,
                            "large": sc_large
                        },
                        "links": {
                            "html": f"https://avascry.com/printing/{sc_p_slug}",
                            "markdown": f"https://avascry.com/printing/{sc_p_slug}.md",
                            "json": f"https://avascry.com/printing/{sc_p_slug}.json",
                            "xml": f"https://avascry.com/printing/{sc_p_slug}.xml",
                            "csv": f"https://avascry.com/printing/{sc_p_slug}.csv"
                        }
                    })
                    if len(similar_cards) >= 8:
                        break
    except Exception as e:
        pass

    # Load Visual Artwork Analysis & Top 7 Nearest Visual Neighbors (Qwen3-VL & 4096-dim Qwen3-Embedding)
    visual_artwork = None
    visual_similarities = None
    illustration_id = card.get("illustration_id") or (card.get("raw") or {}).get("illustration_id")
    if illustration_id:
        try:
            analysis_doc = db["vl_art_analysis"].find_one({"illustration_id": illustration_id, "status": "complete"})
            sim_art_doc = db["vl_art_similarities"].find_one({"illustration_id": illustration_id})
            if analysis_doc or sim_art_doc:
                raw_neighbors = (sim_art_doc.get("top_neighbors") if sim_art_doc else {}) or {}
                formatted_neighbors = {}
                for category in ["by_subject", "by_vibe", "by_scene"]:
                    cat_list = raw_neighbors.get(category, [])
                    formatted_cat = []
                    for n in cat_list:
                        n_name = n.get("card_name", "Card")
                        n_set = (n.get("set") or "").lower()
                        n_slug = slugify(n_name)
                        n_pslug = f"{n_slug}-{n_set}" if n_set else n_slug
                        formatted_cat.append({
                            "card_name": n_name,
                            "slug": n_pslug,
                            "artist": n.get("artist", "Unknown"),
                            "set": n_set.upper(),
                            "image_url": n.get("image_url", ""),
                            "score": round(float(n.get("score", 0)), 4),
                            "illustration_id": n.get("illustration_id", "")
                        })
                    formatted_neighbors[category] = formatted_cat

                visual_similarities = formatted_neighbors
                visual_artwork = {
                    "illustration_id": illustration_id,
                    "artist": card.get("artist") or "Unknown",
                    "vision_observations": (analysis_doc.get("vision_observations") if analysis_doc else {}) or {},
                    "top_neighbors": formatted_neighbors,
                    "links": {
                        "art_json": f"https://avascry.com/art/{illustration_id}.json",
                        "art_markdown": f"https://avascry.com/art/{illustration_id}.md"
                    }
                }
        except Exception:
            pass

    # Content Negotiation: Check for AI Agent / LLM requesting Markdown, JSON, XML, or CSV
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()
    canonical_printing_slug = card.get("printing_slug") or card_vm.get("printing_slug") or identifier
    safe_canonical_slug = safe_header_segment(canonical_printing_slug)
    link_header_val = (
        f'</printing/{safe_canonical_slug}.md>; rel="alternate"; type="text/markdown", '
        f'</printing/{safe_canonical_slug}.json>; rel="alternate"; type="application/json", '
        f'</printing/{safe_canonical_slug}.xml>; rel="alternate"; type="application/xml", '
        f'</printing/{safe_canonical_slug}.csv>; rel="alternate"; type="text/csv"'
    )
    if visual_artwork and illustration_id:
        safe_ill_id = safe_header_segment(str(illustration_id))
        link_header_val += (
            f', </art/{safe_ill_id}.json>; rel="related"; type="application/json"'
            f', </art/{safe_ill_id}.md>; rel="related"; type="text/markdown"'
        )

    # ONLY return raw data formats if explicitly requested via extension (.json, .md, .xml, .csv) or ?format=
    if is_json or requested_format == "json":
        card_set = (card.get("set") or "").lower()
        card_set_name = card.get("set_name") or card_set.upper()
        card_norm = card_vm.get("image_url") or f"/images/normal/{canonical_printing_slug}.jpg"
        if card_norm.startswith("/"):
            card_norm = f"https://avascry.com{card_norm}"
        card_large = card_vm.get("large_image_url") or card_norm
        if card_large.startswith("/"):
            card_large = f"https://avascry.com{card_large}"

        card_json = {
            "name": card.get("name"),
            "mana_cost": card.get("mana_cost"),
            "cmc": float(card.get("cmc") or 0.0),
            "type_line": card.get("type_line"),
            "oracle_text": card.get("oracle_text"),
            "layout": card.get("layout", "normal"),
            "card_faces": card.get("card_faces"),
            "power": card.get("power"),
            "toughness": card.get("toughness"),
            "loyalty": card.get("loyalty"),
            "colors": card.get("colors") or [],
            "color_identity": card.get("color_identity") or [],
            "keywords": card.get("keywords") or [],
            "set": card_set,
            "set_name": card_set_name,
            "collector_number": card.get("collector_number") or "",
            "rarity": card.get("rarity") or "",
            "artist": card.get("artist") or "",
            "oracle_id": oracle_id,
            "illustration_id": illustration_id,
            "image_uris": {
                "normal": card_norm,
                "large": card_large
            },
            "links": {
                "html": f"https://avascry.com/printing/{canonical_printing_slug}",
                "markdown": f"https://avascry.com/printing/{canonical_printing_slug}.md",
                "json": f"https://avascry.com/printing/{canonical_printing_slug}.json",
                "xml": f"https://avascry.com/printing/{canonical_printing_slug}.xml",
                "csv": f"https://avascry.com/printing/{canonical_printing_slug}.csv"
            },
            "legalities": card.get("legalities") or {},
            "rulings": [
                {
                    "source": r.get("source", "wotc"),
                    "published_at": r.get("published_at", ""),
                    "comment": r.get("comment", "")
                }
                for r in rulings
            ],
            "printings_count": len(printings),
            "similar_cards": similar_cards[:6],
            "visual_artwork": visual_artwork
        }
        return JSONResponse(
            content=card_json,
            headers={
                "Vary": "Accept",
                "Link": link_header_val,
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_md or requested_format in ("md", "markdown"):
        md_text = format_card_markdown(card, printings_count=len(printings), rulings=rulings, similar_cards=similar_cards, visual_artwork=visual_artwork)
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Vary": "Accept",
                "X-Markdown-Tokens": str(len(md_text.split())),
                "Link": link_header_val,
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_xml or requested_format in ("xml", "cockatrice"):
        xml_bytes = format_card_cockatrice_xml(card)
        return Response(
            content=xml_bytes,
            media_type="application/xml",
            headers={
                "Vary": "Accept",
                "Link": link_header_val,
                "Content-Disposition": f'inline; filename="{safe_canonical_slug}_cockatrice.xml"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_csv or requested_format == "csv":
        csv_text = format_card_csv(card)
        return Response(
            content=csv_text,
            media_type="text/csv; charset=utf-8",
            headers={
                "Vary": "Accept",
                "Link": link_header_val,
                "Content-Disposition": f'inline; filename="{safe_canonical_slug}.csv"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    # Check if card is saved in user stash
    user = request.session.get("user") if "session" in request.scope else None
    is_saved = False
    if user and oracle_id:
        try:
            is_saved = bool(db["saved_cards"].find_one({"user_id": user["id"], "oracle_id": oracle_id}))
        except Exception:
            is_saved = False

    return templates.TemplateResponse(
        request=request,
        name="card.html",
        context={
            "active_nav": "explore",
            "card": card_vm,
            "badges": card_vm.get("badges", []),
            "printings": printings,
            "lang_groups": sorted_lang_groups,
            "rulings": rulings,
            "mechanics": mechanics,
            "lure": lure,
            "similar_cards": similar_cards,
            "visual_artwork": visual_artwork,
            "visual_similarities": visual_similarities,
            "is_saved": is_saved
        },
        headers={
            "Link": link_header_val
        }
    )

@card_router.get("/printing/{slug}.md")
@card_router.head("/printing/{slug}.md")
async def printing_detail_markdown(request: Request, slug: str, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=md"
    return await printing_detail(request, slug, background_tasks)

@card_router.get("/printing/{slug}.json")
@card_router.head("/printing/{slug}.json")
async def printing_detail_json(request: Request, slug: str, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=json"
    return await printing_detail(request, slug, background_tasks)

@card_router.get("/printing/{slug}.xml")
@card_router.head("/printing/{slug}.xml")
async def printing_detail_xml(request: Request, slug: str, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=xml"
    return await printing_detail(request, slug, background_tasks)

@card_router.get("/printing/{slug}.csv")
@card_router.head("/printing/{slug}.csv")
async def printing_detail_csv(request: Request, slug: str, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=csv"
    return await printing_detail(request, slug, background_tasks)

@card_router.head("/printing/{identifier}")
async def printing_detail_head(request: Request, identifier: str, background_tasks: BackgroundTasks):
    return await printing_detail(request, identifier, background_tasks)

@card_router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, background_tasks: BackgroundTasks, q: Optional[str] = Query(None)):
    query_str = (q or "").strip()
    if not query_str:
        return RedirectResponse(url="/", status_code=303)
        
    db = get_mongo_db()
    # Check exact card match first
    exact = db["cards"].find_one({
        "$or": [
            {"slug": slugify(query_str)},
            {"name": {"$regex": f"^{re.escape(query_str)}$", "$options": "i"}}
        ]
    })
    if exact and exact.get("slug"):
        return RedirectResponse(url=f"/card/{exact['slug']}", status_code=303)

    # Otherwise find matches prioritizing English printings first
    pattern = re.compile(re.escape(query_str), re.IGNORECASE)
    matches = list(db["cards"].find(
        {"name": pattern, "lang": "en"},
        {"name": 1, "slug": 1, "set": 1, "lang": 1, "image_slug": 1, "raw": 1, "image_uris": 1, "card_faces": 1, "type_line": 1, "mana_cost": 1, "set_name": 1, "rarity": 1, "released_at": 1}
    ).sort("released_at", -1).limit(40))

    # If fewer than 24 English matches, backfill with non-English
    if len(matches) < 24:
        extra_matches = list(db["cards"].find(
            {"name": pattern, "lang": {"$ne": "en"}},
            {"name": 1, "slug": 1, "set": 1, "lang": 1, "image_slug": 1, "raw": 1, "image_uris": 1, "card_faces": 1, "type_line": 1, "mana_cost": 1, "set_name": 1, "rarity": 1, "released_at": 1}
        ).limit(24 - len(matches)))
        matches.extend(extra_matches)

    results = []
    for m in matches:
        _, img_url, _ = resolve_card_images(m, background_tasks)
        m_name = m.get("name") or "card"
        m_set = (m.get("set") or "").lower()
        m_slug = slugify(m_name)
        m_printing_slug = f"{m_slug}-{m_set}" if m_set else m_slug
        results.append({
            "name": m_name,
            "slug": m_printing_slug,
            "image_url": img_url,
            "type_line": m.get("type_line"),
            "mana_cost": m.get("mana_cost")
        })

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "active_nav": "home",
            "featured_cards": results,
            "q": query_str,
            "noindex": True
        },
        headers={"X-Robots-Tag": "noindex, follow"}
    )

@card_router.get("/similar/{slug}", response_class=HTMLResponse)
@card_router.head("/similar/{slug}")
async def similar_cards_page(slug: str, request: Request, background_tasks: BackgroundTasks):
    """Deep similarity search: finds top 31 mechanically similar cards from the 38k embedding graph."""
    db = get_mongo_db()

    is_md = False
    is_json = False
    if slug.lower().endswith(".md"):
        slug = slug[:-3]
        is_md = True
    elif slug.lower().endswith(".json"):
        slug = slug[:-5]
        is_json = True

    slug_clean = slug.strip().lower()
    if slug_clean in ("null", "undefined", "none") or slug_clean.startswith(("null.", "undefined.", "none.")):
        return RedirectResponse(url="/", status_code=301)

    slug = slug.strip()
    if not slug or slug in ("", ".", "..", "-"):
        raise HTTPException(status_code=404, detail="Card not found")

    card = find_card_by_slug(db, slug)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
        
    oracle_id = card.get("oracle_id")
    card_name = card.get("name") or "Card"
    card_set = (card.get("set") or "").lower()
    card_slug = card.get("slug") or slugify(card_name)
    safe_similar_slug = safe_header_segment(card_slug)
    card_printing_slug = card.get("printing_slug") or (f"{card_slug}-{card_set}" if card_set else card_slug)
    
    # Resolve target card image
    _, target_img, _ = resolve_card_images(card, background_tasks)

    # Fetch precomputed cosine similarity from 38k embedding collection
    sim_doc = db["similar_cards"].find_one({"oracle_id": oracle_id})
    similar_items = sim_doc.get("similar", []) if sim_doc else []
    
    results = []
    seen_oracles = {oracle_id}
    
    if similar_items:
        sim_oids = [s if isinstance(s, str) else s.get("oracle_id") for s in similar_items if (s if isinstance(s, str) else s.get("oracle_id"))]
        
        c_docs = list(db["cards"].find(
            {"oracle_id": {"$in": sim_oids[:60]}, "lang": "en"},
            {"name": 1, "slug": 1, "set": 1, "set_name": 1, "collector_number": 1, "image_uris": 1, "card_faces": 1, "type_line": 1, "mana_cost": 1, "oracle_id": 1, "image_slug": 1, "raw": 1}
        ))
        
        doc_by_oid = {}
        for d in c_docs:
            oid = d.get("oracle_id")
            if oid and oid not in doc_by_oid:
                doc_by_oid[oid] = d
                
        for oid in sim_oids:
            if oid in doc_by_oid and oid not in seen_oracles:
                seen_oracles.add(oid)
                sc = doc_by_oid[oid]
                sc_name = sc.get("name") or "Card"
                sc_set = (sc.get("set") or "").lower()
                sc_slug = slugify(sc_name)
                sc_printing_slug = f"{sc_slug}-{sc_set}" if sc_set else sc_slug
                _, sc_img_url, _ = resolve_card_images(sc, None)
                
                results.append({
                    "name": sc_name,
                    "slug": sc_printing_slug,
                    "image_url": sc_img_url,
                    "type_line": sc.get("type_line"),
                    "mana_cost": sc.get("mana_cost")
                })
                if len(results) >= 31:
                    break

    if not results:
        # Dynamic fallback for custom/playtest/unvectorized cards (e.g. Star Trek, Universes Beyond)
        keywords = card.get("keywords", [])
        colors = card.get("color_identity", [])
        type_line = card.get("type_line", "")
        
        fallback_query = {
            "oracle_id": {"$ne": oracle_id},
            "lang": "en"
        }
        clauses = []
        if keywords:
            clauses.append({"keywords": {"$in": keywords[:3]}})
        if colors:
            clauses.append({"color_identity": {"$in": colors}})
            
        main_type = "Creature" if "Creature" in type_line else ("Artifact" if "Artifact" in type_line else ("Enchantment" if "Enchantment" in type_line else ("Instant" if "Instant" in type_line else "Sorcery")))
        clauses.append({"type_line": {"$regex": main_type}})
        fallback_query["$or"] = clauses
        
        fallback_cursor = list(db["cards"].find(
            fallback_query,
            {"name": 1, "slug": 1, "set": 1, "image_uris": 1, "card_faces": 1, "type_line": 1, "mana_cost": 1, "oracle_id": 1, "image_slug": 1, "raw": 1}
        ).limit(60))
        
        for sc in fallback_cursor:
            sc_oid = sc.get("oracle_id")
            if sc_oid and sc_oid not in seen_oracles:
                seen_oracles.add(sc_oid)
                sc_name = sc.get("name") or "Card"
                sc_set = (sc.get("set") or "").lower()
                sc_slug = slugify(sc_name)
                sc_printing_slug = f"{sc_slug}-{sc_set}" if sc_set else sc_slug
                _, sc_img_url, _ = resolve_card_images(sc, None)
                
                results.append({
                    "name": sc_name,
                    "slug": sc_printing_slug,
                    "image_url": sc_img_url,
                    "type_line": sc.get("type_line"),
                    "mana_cost": sc.get("mana_cost"),
                    "score": 0.70
                })
                if len(results) >= 31:
                    break

    # Content Negotiation for AI Agents (Accept: text/markdown, application/json, or ?format=)
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()

    if is_json or "application/json" in accept_header or requested_format == "json":
        target_norm = target_img
        if target_norm.startswith("/"):
            target_norm = f"https://avascry.com{target_norm}"
            
        formatted_results = []
        for sc in results:
            sc_img = sc.get("image_url") or ""
            if sc_img.startswith("/"):
                sc_img = f"https://avascry.com{sc_img}"
            sc_slug = sc.get("slug") or ""
            formatted_results.append({
                "name": sc.get("name"),
                "slug": sc_slug,
                "type_line": sc.get("type_line"),
                "mana_cost": sc.get("mana_cost"),
                "score": sc.get("score"),
                "image_uris": {
                    "normal": sc_img
                },
                "links": {
                    "html": f"https://avascry.com/printing/{sc_slug}",
                    "markdown": f"https://avascry.com/printing/{sc_slug}.md",
                    "json": f"https://avascry.com/printing/{sc_slug}.json"
                }
            })

        sim_json = {
            "target_card": {
                "name": card_name,
                "slug": card_slug,
                "printing_slug": card_printing_slug,
                "type_line": card.get("type_line", ""),
                "mana_cost": card.get("mana_cost", ""),
                "image_uris": {
                    "normal": target_norm
                },
                "links": {
                    "html": f"https://avascry.com/printing/{card_printing_slug}",
                    "markdown": f"https://avascry.com/printing/{card_printing_slug}.md",
                    "json": f"https://avascry.com/printing/{card_printing_slug}.json"
                }
            },
            "algorithm": "4096-dimensional Qwen 8B Cosine Similarity",
            "links": {
                "html": f"https://avascry.com/similar/{card_slug}",
                "markdown": f"https://avascry.com/similar/{card_slug}.md",
                "json": f"https://avascry.com/similar/{card_slug}.json"
            },
            "total_similar": len(formatted_results),
            "similar_cards": formatted_results
        }
        return JSONResponse(
            content=sim_json,
            headers={
                "Vary": "Accept",
                "Link": f'</similar/{safe_similar_slug}.md>; rel="alternate"; type="text/markdown", </similar/{safe_similar_slug}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_md or "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
        md_lines = [
            "---",
            f"target_card: {card_name}",
            f"mana_cost: \"{card.get('mana_cost', '')}\"",
            f"type_line: \"{card.get('type_line', '')}\"",
            f"algorithm: \"4096-dimensional Qwen 8B Cosine Similarity over 38,000 Oracle embeddings\"",
            f"canonical_url: https://avascry.com/similar/{card_slug}",
            f"json_api: https://avascry.com/similar/{card_slug}.json",
            "---",
            f"\n# Cards Similar & Synergistic to {card_name}\n",
            f"- **Target Card:** [{card_name}](https://avascry.com/printing/{card_printing_slug}) ({card.get('type_line', '')}) `{card.get('mana_cost', '')}`",
            f"- **Algorithm:** 4096-dimensional Qwen 8B Cosine Similarity over 38,000 Oracle embeddings",
            f"- **JSON API:** https://avascry.com/similar/{card_slug}.json",
            f"\n## Top 31 Synergistic Matches\n"
        ]
        for idx, sc in enumerate(results, 1):
            sc_p_slug = sc.get("slug") or slugify(sc.get("name") or "card")
            md_lines.append(f"{idx}. [**{sc['name']}**](https://avascry.com/printing/{sc_p_slug}) `{sc.get('mana_cost') or 'N/A'}` — *{sc.get('type_line') or ''}*")
        
        md_text = "\n".join(md_lines)
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Vary": "Accept",
                "X-Markdown-Tokens": str(len(md_text.split())),
                "Link": f'</similar/{safe_similar_slug}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="similar.html",
        context={
            "active_nav": "explore",
            "card": {
                "name": card_name,
                "slug": card_slug,
                "printing_slug": card_printing_slug,
                "type_line": card.get("type_line", ""),
                "mana_cost": card.get("mana_cost", "")
            },
            "target_image": target_img,
            "similar_cards": results
        },
        headers={
            "Link": f'</similar/{safe_similar_slug}.md>; rel="alternate"; type="text/markdown", </similar/{safe_similar_slug}.json>; rel="alternate"; type="application/json"'
        }
    )

@card_router.get("/similar/{slug}.md")
@card_router.head("/similar/{slug}.md")
async def similar_cards_markdown(slug: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=md"
    return await similar_cards_page(slug, request, background_tasks)

@card_router.get("/similar/{slug}.json")
@card_router.head("/similar/{slug}.json")
async def similar_cards_json(slug: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=json"
    return await similar_cards_page(slug, request, background_tasks)

@card_router.head("/similar/{slug}")
async def similar_cards_head(slug: str, request: Request, background_tasks: BackgroundTasks):
    return await similar_cards_page(slug, request, background_tasks)

# =====================================================================
# ART OBSERVATIONS & VISUAL NEIGHBORS (SELLMO & MULTIMODAL MACHINE FOOD)
# =====================================================================

@card_router.get("/art/{illustration_id}.md", include_in_schema=False)
async def art_detail_markdown(request: Request, illustration_id: str):
    clean_id = illustration_id.replace(".md", "").strip()
    db = get_mongo_db()
    analysis_doc = db["vl_art_analysis"].find_one({"illustration_id": clean_id, "status": "complete"})
    sim_doc = db["vl_art_similarities"].find_one({"illustration_id": clean_id})
    if not analysis_doc and not sim_doc:
        raise HTTPException(status_code=404, detail="Art analysis not found")

    source = (analysis_doc.get("source") if analysis_doc else {}) or {}
    card_name = source.get("card_name") or "Unknown"
    artist = source.get("artist") or "Unknown"
    obs = (analysis_doc.get("vision_observations") if analysis_doc else {}) or {}
    top_n = (sim_doc.get("top_neighbors") if sim_doc else {}) or {}

    lines = [
        "---",
        f'illustration_id: "{clean_id}"',
        f'card_name: "{card_name}"',
        f'artist: "{artist}"',
        f'vl_model: "{analysis_doc.get("model", "qwen3-vl:latest") if analysis_doc else "unknown"}"',
        f'embedding_model: "{sim_doc.get("model", "qwen3-embedding:8b") if sim_doc else "unknown"}"',
        f'canonical_url: "https://avascry.com/art/{clean_id}.json"',
        "---",
        f"\n# Visual Artwork Analysis: {card_name}",
        f"**Artist:** {artist} | **Set:** {(source.get('set') or '').upper()} #{source.get('collector_number', '')}\n",
        f"## Literal Visual Summary\n{obs.get('visual_summary', 'N/A')}\n",
        "## Visual Elements Breakdown",
        f"- **Primary Subjects:** {', '.join(obs.get('subjects', [])) or 'None'}",
        f"- **Setting & Environment:** {', '.join(obs.get('setting', [])) or 'None'}",
        f"- **Dominant Palette:** {', '.join(obs.get('dominant_colors', [])) or 'None'}",
        f"- **Style Descriptors:** {', '.join(obs.get('style_descriptors', [])) or 'None'}",
        f"- **Lighting:** {obs.get('lighting', 'N/A')}",
        f"- **Composition:** {obs.get('composition', 'N/A')}",
        f"- **Atmospheric Mood:** {', '.join(obs.get('mood_keywords', [])) or 'None'}\n",
    ]

    if top_n:
        lines.append("## Top 7 Nearest Visual Neighbors (Prime Qwen3-Embedding:8B)")
        for category, label in [("by_subject", "By Subject & Entities"), ("by_vibe", "By Vibe & Aesthetic"), ("by_scene", "By Scene & Composition")]:
            neighbors = top_n.get(category, [])
            if neighbors:
                lines.append(f"\n### {label}")
                for idx, n in enumerate(neighbors, 1):
                    n_name = n.get("card_name", "Unknown")
                    n_art = n.get("artist", "Unknown")
                    n_set = (n.get("set") or "").upper()
                    n_ill = n.get("illustration_id", "")
                    lines.append(f"{idx}. **{n_name}** ({n_set}) by {n_art} ([Art Report](/art/{n_ill}.md))")

    md_content = "\n".join(lines)
    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Vary": "Accept",
            "Link": f'</art/{clean_id}.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@card_router.get("/art/{illustration_id}", include_in_schema=False)
@card_router.get("/art/{illustration_id}.json", include_in_schema=False)
async def art_detail_json(request: Request, illustration_id: str):
    if illustration_id.lower().endswith(".md"):
        return await art_detail_markdown(request, illustration_id)
    clean_id = illustration_id.replace(".json", "").strip()
    db = get_mongo_db()
    analysis_doc = db["vl_art_analysis"].find_one({"illustration_id": clean_id, "status": "complete"})
    sim_doc = db["vl_art_similarities"].find_one({"illustration_id": clean_id})
    if not analysis_doc and not sim_doc:
        raise HTTPException(status_code=404, detail="Art analysis not found")

    source = (analysis_doc.get("source") if analysis_doc else {}) or {}
    card_name = source.get("card_name") or "Unknown"
    artist = source.get("artist") or "Unknown"
    raw_neighbors = (sim_doc.get("top_neighbors") if sim_doc else {}) or {}

    formatted_neighbors = {}
    for category in ["by_subject", "by_vibe", "by_scene"]:
        cat_list = raw_neighbors.get(category, [])
        formatted_cat = []
        for n in cat_list:
            n_name = n.get("card_name", "Card")
            n_set = (n.get("set") or "").lower()
            n_slug = slugify(n_name)
            n_pslug = f"{n_slug}-{n_set}" if n_set else n_slug
            formatted_cat.append({
                "card_name": n_name,
                "slug": n_pslug,
                "artist": n.get("artist", "Unknown"),
                "set": n_set.upper(),
                "image_url": n.get("image_url", ""),
                "score": round(float(n.get("score", 0)), 4),
                "illustration_id": n.get("illustration_id", "")
            })
        formatted_neighbors[category] = formatted_cat

    content = {
        "illustration_id": clean_id,
        "card_name": card_name,
        "artist": artist,
        "set": source.get("set", "").lower(),
        "collector_number": source.get("collector_number", ""),
        "image_url": source.get("image_url", ""),
        "model_vl": (analysis_doc.get("model") if analysis_doc else "qwen3-vl:latest"),
        "model_embedding": (sim_doc.get("model") if sim_doc else "qwen3-embedding:8b"),
        "vision_observations": (analysis_doc.get("vision_observations") if analysis_doc else {}) or {},
        "top_neighbors": formatted_neighbors,
        "links": {
            "json": f"https://avascry.com/art/{clean_id}.json",
            "markdown": f"https://avascry.com/art/{clean_id}.md"
        }
    }
    return JSONResponse(
        content=content,
        headers={
            "Vary": "Accept",
            "Link": f'</art/{clean_id}.md>; rel="alternate"; type="text/markdown"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )
