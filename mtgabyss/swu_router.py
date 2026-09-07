"""
Star Wars: Unlimited (SWU) Sub-Application Router for swu.avascry.com and /swu.
Connects directly to MongoDB database 'avascry_swu'.
Serves HTML, Markdown (.md), JSON, sitemaps, and llms.txt endpoints for bots and humans.
"""

import os
import re
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from db_mongo import get_mongo_db

swu_router = APIRouter(prefix="", tags=["Star Wars Unlimited"])
templates = Jinja2Templates(directory="templates")

@swu_router.get("/images/{rest_of_path:path}", include_in_schema=False)
async def swu_serve_image(rest_of_path: str):
    file_path = os.path.join("public", "images", rest_of_path)
    if os.path.isfile(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})
    raise HTTPException(status_code=404, detail="Image not found")

def get_swu_db():
    client = get_mongo_db().client
    return client["avascry_swu"]

def get_base_prefix(request: Request) -> str:
    host = request.headers.get("host", "")
    from mtgabyss.network_router import extract_subdomain
    sub = extract_subdomain(host)
    if sub == "swu":
        return ""
    return "/swu"

@swu_router.get("", response_class=HTMLResponse)
@swu_router.get("/", response_class=HTMLResponse)
async def swu_home(request: Request,
                   q: Optional[str] = None,
                   aspect: Optional[str] = None,
                   type: Optional[str] = None,
                   arena: Optional[str] = None,
                   set: Optional[str] = None,
                   cost: Optional[str] = None,
                   view: Optional[str] = "scans",
                   page: int = 1):
    db = get_swu_db()
    query = {}
    is_filtered = bool(q or aspect or type or arena or set or cost)
    
    if q:
        q_clean = q.strip()
        query["$or"] = [
            {"title": {"$regex": re.escape(q_clean), "$options": "i"}},
            {"subtitle": {"$regex": re.escape(q_clean), "$options": "i"}},
            {"text": {"$regex": re.escape(q_clean), "$options": "i"}},
            {"traits": {"$regex": re.escape(q_clean), "$options": "i"}}
        ]
        
    if aspect:
        query["aspects"] = aspect
        
    if type:
        query["type"] = type
        
    if arena:
        query["arenas"] = arena
        
    if set:
        query["expansion.code"] = set.upper()
        
    if cost is not None and cost != "":
        try:
            query["cost"] = int(cost)
        except ValueError:
            pass

    # Hide duplicate foil variants (Foil, Hyperspace Foil, Prestige Foil) that lack dedicated scans
    query["variant_type"] = {"$not": {"$regex": "Foil", "$options": "i"}}

    limit = 36
    page = max(1, page)
    skip = (page - 1) * limit

    total_count = db.cards.count_documents(query)
    total_pages = max(1, (total_count + limit - 1) // limit)

    cards = list(db.cards.find(query, {
        "_id": 0,
        "slug": 1,
        "title": 1,
        "name": 1,
        "subtitle": 1,
        "card_number": 1,
        "number": 1,
        "cost": 1,
        "hp": 1,
        "power": 1,
        "type": 1,
        "type2": 1,
        "aspects": 1,
        "traits": 1,
        "arenas": 1,
        "rarity": 1,
        "expansion": 1,
        "set_code": 1,
        "set_name": 1,
        "art_front": 1,
        "art_back": 1,
        "front_image": 1,
        "back_image": 1,
        "local_image_front": 1,
        "local_image_back": 1,
        "text": 1,
        "front_text": 1
    }).sort([("expansion.code", 1), ("card_number", 1)]).skip(skip).limit(limit))

    # Normalize fields for display in templates
    for c in cards:
        if not c.get("title"):
            c["title"] = c.get("name") or "Unknown"
        if not c.get("card_number"):
            c["card_number"] = c.get("number")
        
        slug = c.get("slug") or ""
        local_front_file = f"public/images/swu/{slug}_front.png"
        local_back_file = f"public/images/swu/{slug}_back.png"

        # If variant without scan (e.g. ending in F), fall back to base card image
        base_slug = slug[:-1] if slug.endswith(("F", "f")) else slug

        if os.path.isfile(local_front_file):
            c["art_front"] = f"/images/swu/{slug}_front.png"
        elif os.path.isfile(f"public/images/swu/{base_slug}_front.png"):
            c["art_front"] = f"/images/swu/{base_slug}_front.png"
        else:
            c["art_front"] = c.get("local_image_front") or c.get("art_front") or c.get("front_image")

        if os.path.isfile(local_back_file):
            c["art_back"] = f"/images/swu/{slug}_back.png"
        elif os.path.isfile(f"public/images/swu/{base_slug}_back.png"):
            c["art_back"] = f"/images/swu/{base_slug}_back.png"
        else:
            c["art_back"] = c.get("local_image_back") or c.get("art_back") or c.get("back_image")

        if not c.get("text"):
            c["text"] = c.get("front_text") or ""
        if not c.get("expansion"):
            c["expansion"] = {"code": c.get("set_code", ""), "name": c.get("set_name", "")}

    # If front page without search filters, load iconic featured leaders for the hero section
    featured_leaders = []
    if not is_filtered and page == 1:
        leader_slugs = [
            "luke-skywalker-faithful-friend-sor-5",
            "darth-vader-dark-lord-of-the-sith-sor-10",
            "leia-organa-alliance-general-sor-9",
            "boba-fett-collecting-the-bounty-sor-15",
            "emperor-palpatine-galactic-ruler-sor-6",
            "han-solo-audacious-smuggler-sor-17"
        ]
        featured_leaders = list(db.cards.find({"slug": {"$in": leader_slugs}}, {
            "_id": 0, "slug": 1, "title": 1, "name": 1, "subtitle": 1, "aspects": 1,
            "art_front": 1, "art_back": 1, "front_image": 1, "back_image": 1,
            "local_image_front": 1, "local_image_back": 1, "expansion": 1
        }))
        for fl in featured_leaders:
            if not fl.get("title"):
                fl["title"] = fl.get("name")
            fl["art_front"] = fl.get("local_image_front") or fl.get("art_front") or fl.get("front_image")
            fl["art_back"] = fl.get("local_image_back") or fl.get("art_back") or fl.get("back_image")

    # Distinct lists for filter dropdowns
    available_aspects = ["Vigilance", "Command", "Aggression", "Cunning", "Heroism", "Villainy"]
    available_types = ["Leader", "Base", "Unit", "Event", "Upgrade"]
    available_arenas = ["Ground", "Space"]
    available_sets = [
        {"code": "SOR", "name": "Spark of Rebellion"},
        {"code": "SHD", "name": "Shadows of the Galaxy"},
        {"code": "TWI", "name": "Twilight of the Republic"},
        {"code": "JTL", "name": "Jump to Lightspeed"},
        {"code": "LAW", "name": "Legends of the Force"}
    ]

    total_matching = total_count
    # Calculate visible page range (up to 7 page numbers centered on current page)
    start_p = max(1, page - 3)
    end_p = min(total_pages, start_p + 6)
    if end_p - start_p < 6:
        start_p = max(1, end_p - 6)
    page_range = list(range(start_p, end_p + 1))

    # Query params prefix for pagination links
    query_params = dict(request.query_params)
    query_params.pop("page", None)
    qs = "&".join(f"{k}={v}" for k, v in query_params.items())
    page_url_prefix = f"?{qs}&" if qs else "?"

    total_raw_cards = db.cards.count_documents({})
    total_raw_clarifications = db.clarifications.count_documents({})

    cards_display = f"{max(4000, (total_raw_cards // 100) * 100):,}+" if total_raw_cards else "4,800+"
    rulings_display = f"{max(1500, (total_raw_clarifications // 100) * 100):,}+" if total_raw_clarifications else "1,600+"
    sets_display = f"{len(available_sets)} Sets"

    return templates.TemplateResponse(
        request=request,
        name="swu/home.html",
        context={
            "cards": cards,
            "featured_leaders": featured_leaders,
            "is_filtered": is_filtered,
            "current_page": page,
            "total_pages": total_pages,
            "page_range": page_range,
            "page_url_prefix": page_url_prefix,
            "total_matching": total_matching,
            "cards_display": cards_display,
            "rulings_display": rulings_display,
            "sets_display": sets_display,
            "total_count": total_count,
            "limit": limit,
            "total_database_cards": total_raw_cards,
            "total_clarifications": total_raw_clarifications,
            "base_path": get_base_prefix(request),
            "active_aspect": aspect,
            "active_type": type,
            "active_arena": arena,
            "active_set": set,
            "active_cost": cost,
            "search_query": q or "",
            "view_mode": view,
            "available_aspects": available_aspects,
            "available_types": available_types,
            "available_arenas": available_arenas,
            "available_sets": available_sets
        }
    )

@swu_router.get("/card/{slug}.md", response_class=PlainTextResponse)
async def swu_card_markdown(slug: str, request: Request):
    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    lines = [
        f"# {card.get('title')}" + (f": {card.get('subtitle')}" if card.get('subtitle') else ""),
        f"**Type:** {card.get('type')}" + (f" / {card.get('type2')}" if card.get('type2') else ""),
        f"**Expansion:** {card.get('expansion', {}).get('name')} ({card.get('expansion', {}).get('code')}) #{card.get('card_number')}",
        f"**Aspects:** {', '.join(card.get('aspects', [])) or 'Neutral'}",
        f"**Traits:** {', '.join(card.get('traits', [])) or 'None'}",
    ]
    if card.get("cost") is not None:
        lines.append(f"**Cost:** {card.get('cost')}")
    if card.get("power") is not None:
        lines.append(f"**Power:** {card.get('power')}")
    if card.get("hp") is not None:
        lines.append(f"**HP:** {card.get('hp')}")
    if card.get("arenas"):
        lines.append(f"**Arena:** {', '.join(card.get('arenas', []))}")
    if card.get("rarity"):
        lines.append(f"**Rarity:** {card.get('rarity')}")
    if card.get("artist"):
        lines.append(f"**Artist:** {card.get('artist')}")

    lines.append("\n## Card Ability / Text\n")
    lines.append(card.get("text") or "*(No rules text)*")

    if card.get("deploy_box"):
        lines.append("\n## Leader Epic Action / Deploy\n")
        lines.append(card.get("deploy_box"))

    if card.get("rules"):
        lines.append("\n## Official Rules & Clarifications\n")
        lines.append(card.get("rules"))

    lines.append(f"\n*Source: AvaScry Star Wars Unlimited (https://swu.avascry.com/card/{card.get('slug')})*")
    return Response(content="\n".join(lines), media_type="text/markdown; charset=utf-8")

@swu_router.get("/card/{slug}.json", response_class=JSONResponse)
async def swu_card_json(slug: str):
    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return JSONResponse(content=card)

@swu_router.get("/card/{slug}", response_class=HTMLResponse)
async def swu_card_detail(slug: str, request: Request):
    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    # Normalize card attributes
    if not card.get("title"):
        card["title"] = card.get("name") or "Unknown"
    card_slug = card.get("slug") or ""
    base_card_slug = card_slug[:-1] if card_slug.endswith(("F", "f")) else card_slug

    if os.path.isfile(f"public/images/swu/{card_slug}_front.png"):
        card["art_front"] = f"/images/swu/{card_slug}_front.png"
    elif os.path.isfile(f"public/images/swu/{base_card_slug}_front.png"):
        card["art_front"] = f"/images/swu/{base_card_slug}_front.png"
    else:
        card["art_front"] = card.get("local_image_front") or card.get("art_front") or card.get("front_image")

    if os.path.isfile(f"public/images/swu/{card_slug}_back.png"):
        card["art_back"] = f"/images/swu/{card_slug}_back.png"
    elif os.path.isfile(f"public/images/swu/{base_card_slug}_back.png"):
        card["art_back"] = f"/images/swu/{base_card_slug}_back.png"
    else:
        card["art_back"] = card.get("local_image_back") or card.get("art_back") or card.get("back_image")

    if not card.get("text"):
        card["text"] = card.get("front_text") or ""
    if not card.get("expansion"):
        card["expansion"] = {"code": card.get("set_code", ""), "name": card.get("set_name", "")}

    # Prev and Next card navigation
    current_num = card.get("card_number") or 0
    current_exp = card.get("expansion", {}).get("code")
    
    prev_card = db.cards.find_one({
        "expansion.code": current_exp,
        "card_number": {"$lt": current_num}
    }, {"_id": 0, "slug": 1, "title": 1, "name": 1, "card_number": 1, "number": 1}, sort=[("card_number", -1)])
    if prev_card and not prev_card.get("title"):
        prev_card["title"] = prev_card.get("name")
    if prev_card and not prev_card.get("card_number"):
        prev_card["card_number"] = prev_card.get("number")
    
    next_card = db.cards.find_one({
        "expansion.code": current_exp,
        "card_number": {"$gt": current_num}
    }, {"_id": 0, "slug": 1, "title": 1, "name": 1, "card_number": 1, "number": 1}, sort=[("card_number", 1)])
    if next_card and not next_card.get("title"):
        next_card["title"] = next_card.get("name")
    if next_card and not next_card.get("card_number"):
        next_card["card_number"] = next_card.get("number")

    # Similar/synergy cards: same traits or aspects in same set
    traits = card.get("traits", [])
    aspects = card.get("aspects", [])
    synergy_query = {
        "slug": {"$ne": card.get("slug")},
        "variant_type": {"$not": {"$regex": "Foil", "$options": "i"}},
        "$or": [
            {"traits": {"$in": traits}} if traits else {},
            {"aspects": {"$in": aspects}} if aspects else {}
        ]
    }
    # remove empty dicts from $or
    synergy_query["$or"] = [cond for cond in synergy_query["$or"] if cond]
    synergy_cards = []
    if synergy_query["$or"]:
        synergy_cards = list(db.cards.find(synergy_query, {
            "_id": 0, "slug": 1, "title": 1, "name": 1, "subtitle": 1, "art_front": 1, "front_image": 1, "type": 1, "cost": 1
        }).limit(8))
        for sc in synergy_cards:
            if not sc.get("title"):
                sc["title"] = sc.get("name")
            sc_slug = sc.get("slug") or ""
            base_sc_slug = sc_slug[:-1] if sc_slug.endswith(("F", "f")) else sc_slug
            if os.path.isfile(f"public/images/swu/{sc_slug}_front.png"):
                sc["art_front"] = f"/images/swu/{sc_slug}_front.png"
            elif os.path.isfile(f"public/images/swu/{base_sc_slug}_front.png"):
                sc["art_front"] = f"/images/swu/{base_sc_slug}_front.png"
            else:
                sc["art_front"] = sc.get("local_image_front") or sc.get("art_front") or sc.get("front_image")

    return templates.TemplateResponse(
        request=request,
        name="swu/card.html",
        context={
            "card": card,
            "base_path": get_base_prefix(request),
            "prev_card": prev_card,
            "next_card": next_card,
            "synergy_cards": synergy_cards
        },
        headers={
            "Vary": "Accept",
            "Link": f'</card/{card.get("slug", slug)}.md>; rel="alternate"; type="text/markdown", </card/{card.get("slug", slug)}.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

# ---------------------------------------------------------
# Feature 1: Keywords & Mechanics Directory
# ---------------------------------------------------------
@swu_router.get("/keywords", response_class=HTMLResponse)
async def swu_keywords_list(request: Request):
    db = get_swu_db()
    keywords = list(db.keywords.find({}, {"_id": 0}).sort("name", 1))
    return templates.TemplateResponse(
        request=request,
        name="swu/keywords.html",
        context={
            "base_path": get_base_prefix(request),
            "keywords": keywords,
            "current_keyword": None,
            "cards": []
        }
    )

@swu_router.get("/keyword/{slug}.json", response_class=JSONResponse)
async def swu_keyword_json(slug: str):
    db = get_swu_db()
    clean_slug = slug.removesuffix(".json")
    kw = db.keywords.find_one({"slug": clean_slug}, {"_id": 0})
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return JSONResponse(content=kw)

@swu_router.get("/keyword/{slug}", response_class=HTMLResponse)
async def swu_keyword_detail(request: Request, slug: str):
    db = get_swu_db()
    clean_slug = slug.removesuffix(".json")
    kw = db.keywords.find_one({"slug": clean_slug}, {"_id": 0})
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    
    # Query cards featuring this keyword in their rules text or traits
    kw_name = kw["name"]
    pattern = re.compile(rf"\b{re.escape(kw_name)}\b", re.IGNORECASE)
    cards = list(db.cards.find({
        "$or": [
            {"text": pattern},
            {"front_text": pattern},
            {"back_text": pattern},
            {"traits": pattern}
        ]
    }, {
        "_id": 0, "slug": 1, "title": 1, "name": 1, "card_number": 1, "number": 1,
        "expansion": 1, "set_code": 1, "art_front": 1, "front_image": 1
    }).limit(60))

    return templates.TemplateResponse(
        request=request,
        name="swu/keywords.html",
        context={
            "base_path": get_base_prefix(request),
            "keywords": [],
            "current_keyword": kw,
            "cards": cards
        }
    )

# ---------------------------------------------------------
# Feature 2: Comprehensive Rules Citation Engine
# ---------------------------------------------------------
@swu_router.get("/rules", response_class=HTMLResponse)
async def swu_rules_index(request: Request):
    db = get_swu_db()
    all_sections = list(db.rules_entries.find({}, {"_id": 0}).sort("section_id", 1))
    return templates.TemplateResponse(
        request=request,
        name="swu/rules.html",
        context={
            "base_path": get_base_prefix(request),
            "all_sections": all_sections,
            "sections_to_display": all_sections,
            "current_section": None
        }
    )

@swu_router.get("/rule/{slug}", response_class=HTMLResponse)
async def swu_rule_section(request: Request, slug: str):
    db = get_swu_db()
    all_sections = list(db.rules_entries.find({}, {"_id": 0}).sort("section_id", 1))
    current_sec = db.rules_entries.find_one({
        "$or": [
            {"slug": slug},
            {"section_slug": slug},
            {"section_id": slug},
            {"section": slug}
        ]
    }, {"_id": 0})
    if not current_sec:
        # Fallback: check if slug matches the beginning of a slug (e.g. 1-1 or 7-5-11)
        prefix = slug.split("-")[0]
        current_sec = db.rules_entries.find_one({"slug": {"$regex": f"^{re.escape(slug)}"}}, {"_id": 0})
        if not current_sec:
            raise HTTPException(status_code=404, detail="Rules section not found")
    
    return templates.TemplateResponse(
        request=request,
        name="swu/rules.html",
        context={
            "base_path": get_base_prefix(request),
            "all_sections": all_sections,
            "sections_to_display": [current_sec],
            "current_section": current_sec
        }
    )

# ---------------------------------------------------------
# Feature 3: Official Clarifications & Errata Feed
# ---------------------------------------------------------
@swu_router.get("/rulings", response_class=HTMLResponse)
@swu_router.get("/errata", response_class=HTMLResponse)
async def swu_rulings_feed(request: Request, q: Optional[str] = None, page: int = 1):
    db = get_swu_db()
    query = {}
    if q:
        q_clean = q.strip()
        query["$or"] = [
            {"card_title": {"$regex": re.escape(q_clean), "$options": "i"}},
            {"ruling_text": {"$regex": re.escape(q_clean), "$options": "i"}}
        ]

    limit = 30
    skip = max(0, page - 1) * limit
    total_count = db.clarifications.count_documents(query)
    rulings = list(db.clarifications.find(query, {"_id": 0}).sort([("card_set", 1), ("card_number", 1)]).skip(skip).limit(limit))
    total_pages = max(1, (total_count + limit - 1) // limit)

    return templates.TemplateResponse(
        request=request,
        name="swu/rulings.html",
        context={
            "base_path": get_base_prefix(request),
            "rulings": rulings,
            "current_ruling": None,
            "query": q,
            "current_page": page,
            "total_pages": total_pages,
            "total_count": total_count
        }
    )

@swu_router.get("/ruling/{slug}", response_class=HTMLResponse)
async def swu_ruling_detail(request: Request, slug: str):
    db = get_swu_db()
    ruling = db.clarifications.find_one({"slug": slug}, {"_id": 0})
    if not ruling:
        raise HTTPException(status_code=404, detail="Ruling not found")

    return templates.TemplateResponse(
        request=request,
        name="swu/rulings.html",
        context={
            "base_path": get_base_prefix(request),
            "rulings": [],
            "current_ruling": ruling,
            "query": None,
            "current_page": 1,
            "total_pages": 1,
            "total_count": 1
        }
    )

@swu_router.get("/llms.txt", response_class=PlainTextResponse)
async def swu_llms_txt(request: Request):
    content = """# AvaScry Star Wars: Unlimited (SWU)
> Comprehensive canonical card database, aspect interactions, rules citation engine, and official card clarifications for Star Wars: Unlimited.

## LLM Retrieval Guidelines
- Base URL: https://swu.avascry.com
- Machine readable format for any card: https://swu.avascry.com/card/{slug}.md
- Machine JSON format for any card: https://swu.avascry.com/card/{slug}.json
- Machine JSON format for any keyword: https://swu.avascry.com/keyword/{slug}.json
- Full XML Sitemap: https://swu.avascry.com/sitemap.xml

## Rules & Clarifications System
- Star Wars Comprehensive Rules: https://swu.avascry.com/rules
- Section permalinks: https://swu.avascry.com/rule/{slug} (e.g., /rule/1-general-concepts)
- Official Card Clarifications & Errata: https://swu.avascry.com/rulings
- Keyword Definitions & Reminders: https://swu.avascry.com/keywords

## Card Types & Anatomy
- **Leader**: Two-sided card with passive/exhaust ability on front, deployed unit on reverse.
- **Base**: Defines starting HP (usually 30) and aspect affiliation.
- **Unit**: Space or Ground units that battle in arenas.
- **Event**: One-time effects discarded upon resolution.
- **Upgrade**: Attached to units to modify power, HP, or grant keywords.

## Aspects
- Vigilance (Blue): Defense, healing, shielding, board control.
- Command (Green): Resource ramp, swarming, deployment.
- Aggression (Red): Direct damage, fast attacks, pressure.
- Cunning (Yellow): Bounce, exhaust, discard, trickery.
- Heroism (White): Light side characters and allies.
- Villainy (Black): Empire, Sith, and scoundrels.
"""
    return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8", headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"})

@swu_router.get("/llms-full.txt", response_class=PlainTextResponse)
async def swu_llms_full_txt():
    """Full plain-text Star Wars: Unlimited card, keyword, and rules corpus for direct model ingestion."""
    db = get_swu_db()
    cards = list(db.cards.find({}, {"_id": 0}).sort([("expansion.code", 1), ("card_number", 1)]).limit(3000))
    keywords = list(db.keywords.find({}, {"_id": 0}).sort("name", 1))

    lines = [
        "# AvaScry Star Wars: Unlimited — Full Game Corpus",
        "Game: Star Wars: Unlimited (SWU)",
        "Publisher: Fantasy Flight Games / Lucasfilm Ltd.",
        f"Total Cards: {len(cards)}",
        f"Total Keywords: {len(keywords)}\n",
        "## Keywords & Combat Mechanics"
    ]
    for kw in keywords:
        lines.append(f"- **{kw.get('name')}**: {kw.get('reminder') or kw.get('description')}")
    lines.append("\n## Card Database\n")

    for c in cards:
        title = c.get("title") or c.get("name") or "Unknown"
        sub = f": {c.get('subtitle')}" if c.get("subtitle") else ""
        exp = c.get("expansion", {}).get("code") or c.get("set_code") or "SWU"
        num = c.get("card_number") or c.get("number") or ""
        cost = f"Cost: {c.get('cost')}" if c.get("cost") is not None else ""
        stats = ""
        if c.get("power") is not None or c.get("hp") is not None:
            stats = f" | {c.get('power', 0)}/{c.get('hp', 0)}"
        asps = ", ".join(c.get("aspects") or [])
        traits = " • ".join(c.get("traits") or [])
        
        lines.append(f"### {title}{sub} ({exp} #{num})")
        lines.append(f"- URL: https://swu.avascry.com/card/{c.get('slug')}")
        lines.append(f"- Type: {c.get('type')}{stats} {cost} | Aspects: {asps or 'Neutral'}")
        if traits:
            lines.append(f"- Traits: {traits}")
        if c.get("text"):
            lines.append(f"- Ability: {c.get('text').strip()}")
        if c.get("deploy_box"):
            lines.append(f"- Epic Action / Deploy: {c.get('deploy_box').strip()}")
        lines.append("")

    return PlainTextResponse(content="\n".join(lines), media_type="text/plain; charset=utf-8", headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"})

@swu_router.get("/rules.md", response_class=PlainTextResponse)
async def swu_rules_md():
    """Canonical Markdown rules architecture for Star Wars: Unlimited."""
    content = """# Star Wars: Unlimited (SWU) Complete Rules & Mechanics Architecture
> Authoritative rules reference for Star Wars: Unlimited (Fantasy Flight Games / Lucasfilm Ltd.).

## 1. Game Flow & Round Structure
Each round of Star Wars: Unlimited consists of two distinct phases:

### Phase 1: Action Phase
Players take turns taking one action at a time, beginning with the player who holds the **Initiative counter**. On your turn, you must choose exactly **one** of the following actions:
1. **Play a Card**: Pay its resource cost and put it into play (Units enter play exhausted).
2. **Attack with a Unit**: Exhaust a ready unit to attack an enemy unit or the opponent's base. Units in the Ground arena can only attack Ground units or base; units in the Space arena can only attack Space units or base.
3. **Use an Action Ability**: Pay the cost of an ability on a card in play (such as a Leader exhaust action).
4. **Take the Initiative**: Claim the initiative counter for the next round. You cannot take any more actions for the remainder of this Action Phase.
5. **Pass**: Do nothing. Passing does not lock you out of taking actions later in the phase if your opponent takes an action.

### Phase 2: Regroup Phase
Once both players pass consecutively:
1. **Draw 2 Cards**: Both players draw 2 cards from their deck.
2. **Resource a Card**: You may choose 1 card from your hand to place facedown as a resource (ready).
3. **Ready All Cards**: Ready all exhausted units, leaders, and resources.

## 2. Arenas & Combat
- **Ground Arena**: Ground units battle each other and enemy bases.
- **Space Arena**: Starships, fighters, and space transports battle each other and enemy bases.
- **Combat Resolution**: Damage dealt during unit-versus-unit combat is dealt simultaneously. If a unit takes damage equal to or exceeding its Remaining HP, it is immediately defeated.

## 3. Leaders & Epic Actions
- Leaders begin the game in the Base zone with an un-deployed action ability.
- When you control resources equal to or exceeding the Leader's deploy cost, you may take an **Epic Action** to deploy the Leader as a combat unit into the Ground arena.
- If a deployed Leader unit is defeated, it returns to the Base zone exhausted and loses its unit form for the remainder of the game (its passive ability remains active).

## 4. Victory Condition
The game ends immediately when a player's **Base takes 30 damage** (or its specified HP value). The opposing player wins immediately.
"""
    return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8", headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"})

@swu_router.get("/rules.json", response_class=JSONResponse)
async def swu_rules_json():
    """Structured JSON rules architecture for programmatic engines."""
    return JSONResponse(
        content={
            "game": "Star Wars: Unlimited",
            "publisher": "Fantasy Flight Games / Lucasfilm Ltd.",
            "phases": [
                {
                    "phase": "Action Phase",
                    "actions": ["Play a Card", "Attack with a Unit", "Use an Action Ability", "Take the Initiative", "Pass"]
                },
                {
                    "phase": "Regroup Phase",
                    "steps": ["Draw 2 cards", "Optionally resource 1 card face down", "Ready all cards and resources"]
                }
            ],
            "arenas": ["Ground Arena", "Space Arena"],
            "aspects": ["Vigilance", "Command", "Aggression", "Cunning", "Heroism", "Villainy"],
            "base_hp_default": 30
        },
        headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"}
    )

@swu_router.get("/sets.md", response_class=PlainTextResponse)
async def swu_sets_md():
    """Manifest of all Star Wars: Unlimited expansions."""
    content = """# Star Wars: Unlimited Expansion Manifest

| Code | Expansion Name | Release Date | Standard Legal |
| :--- | :--- | :--- | :--- |
| **SOR** | Spark of Rebellion | March 2024 | Yes |
| **SHD** | Shadows of the Galaxy | July 2024 | Yes |
| **TWI** | Twilight of the Republic | November 2024 | Yes |
| **JTL** | Jump to Lightspeed | March 2025 | Yes |
| **LAW** | Legends of the Force | July 2025 | Yes |
| **SEC** | Secrets of Power | November 2025 | Yes |
"""
    return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8", headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"})

@swu_router.get("/.well-known/ai-content", response_class=PlainTextResponse)
async def swu_well_known_ai():
    content = """# AI Content Declaration & Scraping Permission
domain: swu.avascry.com
operator: AvaScry Card Network
ai-train: allowed
ai-search: allowed
machine-endpoints:
  - https://swu.avascry.com/llms.txt
  - https://swu.avascry.com/llms-full.txt
  - https://swu.avascry.com/rules.md
  - https://swu.avascry.com/rules.json
  - https://swu.avascry.com/sets.md
  - https://swu.avascry.com/sitemap.xml
format-negotiation:
  - Header: "Accept: text/markdown" -> /card/{slug}.md
  - Header: "Accept: application/json" -> /card/{slug}.json
"""
    return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")

@swu_router.get("/sitemap.xml", response_class=Response)
async def swu_sitemap_xml():
    db = get_swu_db()
    cards = list(db.cards.find({}, {"slug": 1, "_id": 0}))
    keywords = list(db.keywords.find({}, {"slug": 1, "_id": 0}))
    rules = list(db.rules_entries.find({}, {"slug": 1, "_id": 0}))
    rulings = list(db.clarifications.find({}, {"slug": 1, "_id": 0}).limit(2000))

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '  <url><loc>https://swu.avascry.com/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
        '  <url><loc>https://swu.avascry.com/keywords</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        '  <url><loc>https://swu.avascry.com/rules</loc><changefreq>monthly</changefreq><priority>0.9</priority></url>',
        '  <url><loc>https://swu.avascry.com/rulings</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
        '  <url><loc>https://swu.avascry.com/about</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>',
        '  <url><loc>https://swu.avascry.com/privacy</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        '  <url><loc>https://swu.avascry.com/terms</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        '  <url><loc>https://swu.avascry.com/contact</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>'
    ]
    for kw in keywords:
        xml_lines.append(f'  <url><loc>https://swu.avascry.com/keyword/{kw["slug"]}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>')
    for r in rules:
        xml_lines.append(f'  <url><loc>https://swu.avascry.com/rule/{r["slug"]}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>')
    for rl in rulings:
        xml_lines.append(f'  <url><loc>https://swu.avascry.com/ruling/{rl["slug"]}</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>')
    for c in cards:
        xml_lines.append(f'  <url><loc>https://swu.avascry.com/card/{c["slug"]}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    xml_lines.append('</urlset>')
    return Response(content="\n".join(xml_lines), media_type="application/xml; charset=utf-8")

@swu_router.get("/robots.txt", response_class=PlainTextResponse)
async def swu_robots_txt():
    return PlainTextResponse("""User-agent: *
Allow: /
Sitemap: https://swu.avascry.com/sitemap.xml
""")

@swu_router.get("/about", response_class=HTMLResponse)
async def swu_about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="swu/about.html",
        context={"base_path": get_base_prefix(request)}
    )

@swu_router.get("/privacy", response_class=HTMLResponse)
async def swu_privacy(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="swu/privacy.html",
        context={"base_path": get_base_prefix(request)}
    )

@swu_router.get("/terms", response_class=HTMLResponse)
async def swu_terms(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="swu/terms.html",
        context={"base_path": get_base_prefix(request)}
    )

@swu_router.get("/contact", response_class=HTMLResponse)
async def swu_contact(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="swu/contact.html",
        context={"base_path": get_base_prefix(request), "success": False, "error": None}
    )

@swu_router.post("/contact", response_class=HTMLResponse)
async def swu_contact_post(request: Request):
    form = await request.form()
    honeypot = form.get("website_url", "").strip()
    if honeypot:
        return templates.TemplateResponse(
            request=request,
            name="swu/contact.html",
            context={"base_path": get_base_prefix(request), "success": True, "error": None}
        )

    name = str(form.get("name", "")).strip()
    contact_info = str(form.get("contact", "")).strip()
    category = str(form.get("category", "General Feedback")).strip()
    message = str(form.get("message", "")).strip()

    if not name or not contact_info or not message:
        return templates.TemplateResponse(
            request=request,
            name="swu/contact.html",
            context={
                "base_path": get_base_prefix(request),
                "success": False,
                "error": "Please fill out all required fields before submitting."
            }
        )

    try:
        from app import send_discord_notification
        fields = [
            {"name": "Game Subsite", "value": "Star Wars: Unlimited (swu.avascry.com)", "inline": True},
            {"name": "Category", "value": category, "inline": True},
            {"name": "Sender", "value": name, "inline": True},
            {"name": "Contact / Email", "value": contact_info, "inline": True},
            {"name": "Message", "value": message[:1024], "inline": False}
        ]
        await send_discord_notification(
            title=f"\U0001f30c SWU Inquiry: {category} from {name}",
            description=message[:500],
            color=0xfacc15, # SWU gold
            fields=fields
        )
    except Exception as e:
        print(f"[SWU Discord Notify Error] {e}")

    return templates.TemplateResponse(
        request=request,
        name="swu/contact.html",
        context={"base_path": get_base_prefix(request), "success": True, "error": None}
    )
