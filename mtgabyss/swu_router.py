"""
Star Wars: Unlimited (SWU) Sub-Application Router for swu.avascry.com and /swu.
Connects directly to MongoDB database 'avascry_swu'.
Serves HTML, Markdown (.md), JSON, sitemaps, and llms.txt endpoints for bots and humans.
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse, FileResponse, RedirectResponse
from db_mongo import get_mongo_db
from mtgabyss.shared.helpers import templates
from mtgabyss.shared.cache import get_page_cache, set_page_cache

def trait_slug_filter(val: str) -> str:
    if not val:
        return ""
    return re.sub(r'[^a-z0-9]+', '-', str(val).lower()).strip('-')

templates.env.filters["trait_slug"] = trait_slug_filter

def determine_swu_synergy_reason(source_card: dict, target_card: dict) -> str:
    """Derives a human-friendly gameplay relationship badge without exposing raw embedding math."""
    s_traits = set(source_card.get("traits") or [])
    t_traits = set(target_card.get("traits") or [])
    shared_traits = s_traits.intersection(t_traits)
    if shared_traits:
        primary_trait = sorted(list(shared_traits))[0]
        return f"{primary_trait} Synergy"

    s_type = source_card.get("type", "")
    t_type = target_card.get("type", "")
    if s_type == "Leader" and t_type == "Leader":
        s_aspects = set(source_card.get("aspects") or [])
        t_aspects = set(target_card.get("aspects") or [])
        shared_asp = s_aspects.intersection(t_aspects)
        if shared_asp:
            return f"Alternative {'/'.join(sorted(list(shared_asp)))} Leader"
        return "Alternative Commander"

    # Check shared keywords / mechanics
    s_text = (source_card.get("text") or source_card.get("rules") or "").lower()
    t_text = (target_card.get("text") or target_card.get("rules") or "").lower()
    for kw in ("sentinel", "shield", "experience", "saboteur", "bounty", "smuggle", "ambush", "restore", "grit", "coordinate", "exploit", "indirect damage"):
        if kw in s_text and kw in t_text:
            return f"{kw.title()} Synergy"

    s_aspects = set(source_card.get("aspects") or [])
    t_aspects = set(target_card.get("aspects") or [])
    shared_aspects = s_aspects.intersection(t_aspects)
    if shared_aspects:
        return f"{'/'.join(sorted(list(shared_aspects)))} Ally"

    if source_card.get("cost") is not None and target_card.get("cost") is not None:
        if abs(int(source_card.get("cost")) - int(target_card.get("cost"))) <= 1:
            return "Curve Option"

    return "Archetype Pair"

swu_router = APIRouter(prefix="", tags=["Star Wars Unlimited"])

@swu_router.get("/images/{rest_of_path:path}", include_in_schema=False)
async def swu_serve_image(rest_of_path: str):
    file_path = os.path.join("public", "images", rest_of_path)
    if os.path.isfile(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})
    raise HTTPException(status_code=404, detail="Image not found")

SWU_STATIC_IMAGES = set()

def get_swu_static_images():
    """Lazily load the set of existing SWU local scan filenames into RAM for O(1) checks."""
    global SWU_STATIC_IMAGES
    if not SWU_STATIC_IMAGES:
        folder = os.path.join("public", "images", "swu")
        if os.path.isdir(folder):
            try:
                SWU_STATIC_IMAGES = set(os.listdir(folder))
            except Exception:
                pass
    return SWU_STATIC_IMAGES

def resolve_swu_image(slug: str, suffix: str, remote_url: Optional[str] = None) -> Optional[str]:
    """O(1) in-memory resolution of local card scans with non-foil fallback."""
    local_files = get_swu_static_images()
    filename = f"{slug}_{suffix}.png"
    if filename in local_files:
        return f"/images/swu/{filename}"
    base_slug = slug[:-1] if slug.endswith(("F", "f")) else slug
    base_filename = f"{base_slug}_{suffix}.png"
    if base_filename in local_files:
        return f"/images/swu/{base_filename}"
    return remote_url

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

    # Hide duplicate foil variants (Foil, Hyperspace Foil, Prestige Foil) using indexed $nin
    query["variant_type"] = {"$nin": ["Foil", "Hyperspace Foil", "Prestige Foil", "Prestige Serialized"]}

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

    # Normalize fields for display in templates using O(1) in-memory image resolution
    for c in cards:
        if not c.get("title"):
            c["title"] = c.get("name") or "Unknown"
        if not c.get("card_number"):
            c["card_number"] = c.get("number")
        
        slug = c.get("slug") or ""
        c["art_front"] = resolve_swu_image(slug, "front", c.get("local_image_front") or c.get("art_front") or c.get("front_image"))
        c["art_back"] = resolve_swu_image(slug, "back", c.get("local_image_back") or c.get("art_back") or c.get("back_image"))

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
            fl_slug = fl.get("slug") or ""
            fl["art_front"] = resolve_swu_image(fl_slug, "front", fl.get("local_image_front") or fl.get("art_front") or fl.get("front_image"))
            fl["art_back"] = resolve_swu_image(fl_slug, "back", fl.get("local_image_back") or fl.get("art_back") or fl.get("back_image"))

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

    total_raw_cards = db.cards.estimated_document_count()
    total_raw_clarifications = db.clarifications.estimated_document_count()

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
        },
        headers={
            "Vary": "Accept",
            "Link": '</sitemap.xml>; rel="alternate"; type="application/xml", </llms.txt>; rel="alternate"; type="text/plain", </rules.md>; rel="alternate"; type="text/markdown", </rules.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )


@swu_router.get("/random.json", response_class=JSONResponse)
async def swu_random_json(aspect: Optional[str] = None,
                          type: Optional[str] = None,
                          arena: Optional[str] = None):
    db = get_swu_db()
    match_filter = {}
    if aspect:
        match_filter["aspects"] = {"$regex": f"^{re.escape(aspect)}$", "$options": "i"}
    if type:
        match_filter["type"] = {"$regex": f"^{re.escape(type)}$", "$options": "i"}
    if arena:
        match_filter["arenas"] = {"$regex": f"^{re.escape(arena)}$", "$options": "i"}

    pipeline = []
    if match_filter:
        pipeline.append({"$match": match_filter})
    pipeline.append({"$sample": {"size": 1}})
    pipeline.append({"$project": {"_id": 0}})

    sample = list(db.cards.aggregate(pipeline))
    if not sample:
        raise HTTPException(status_code=404, detail="No matching SWU cards found")
    return JSONResponse(sample[0], headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@swu_router.get("/random.md")
async def swu_random_markdown(request: Request,
                              aspect: Optional[str] = None,
                              type: Optional[str] = None,
                              arena: Optional[str] = None):
    db = get_swu_db()
    match_filter = {}
    if aspect:
        match_filter["aspects"] = {"$regex": f"^{re.escape(aspect)}$", "$options": "i"}
    if type:
        match_filter["type"] = {"$regex": f"^{re.escape(type)}$", "$options": "i"}
    if arena:
        match_filter["arenas"] = {"$regex": f"^{re.escape(arena)}$", "$options": "i"}

    pipeline = []
    if match_filter:
        pipeline.append({"$match": match_filter})
    pipeline.append({"$sample": {"size": 1}})
    pipeline.append({"$project": {"slug": 1, "_id": 0}})

    sample = list(db.cards.aggregate(pipeline))
    if not sample:
        raise HTTPException(status_code=404, detail="No matching SWU cards found")
    slug = sample[0]["slug"]
    base_path = get_base_prefix(request)
    return RedirectResponse(url=f"{base_path}/card/{slug}.md", status_code=307, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@swu_router.get("/random")
async def swu_random_card(request: Request,
                          aspect: Optional[str] = None,
                          type: Optional[str] = None,
                          arena: Optional[str] = None):
    db = get_swu_db()
    match_filter = {}
    if aspect:
        match_filter["aspects"] = {"$regex": f"^{re.escape(aspect)}$", "$options": "i"}
    if type:
        match_filter["type"] = {"$regex": f"^{re.escape(type)}$", "$options": "i"}
    if arena:
        match_filter["arenas"] = {"$regex": f"^{re.escape(arena)}$", "$options": "i"}

    pipeline = []
    if match_filter:
        pipeline.append({"$match": match_filter})
    pipeline.append({"$sample": {"size": 1}})
    pipeline.append({"$project": {"slug": 1, "_id": 0}})

    sample = list(db.cards.aggregate(pipeline))
    if not sample:
        raise HTTPException(status_code=404, detail="No matching SWU cards found")
    slug = sample[0]["slug"]
    base_path = get_base_prefix(request)
    return RedirectResponse(url=f"{base_path}/card/{slug}", status_code=307, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

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

    # Append mechanically similar cards from neural similarity graph
    sim_doc = db.similar_cards.find_one({"$or": [{"slug": card.get("slug")}, {"slug": slug}]})
    if sim_doc and sim_doc.get("similar"):
        lines.append("\n## Mechanically Similar Cards\n")
        for sc in sim_doc["similar"][:6]:
            t = sc.get("title") or sc.get("slug")
            sub = f": {sc.get('subtitle')}" if sc.get("subtitle") else ""
            pct = int(round(sc.get("score", 0) * 100))
            lines.append(f"- [{t}{sub}](https://swu.avascry.com/card/{sc.get('slug')}) — {pct}% match ({sc.get('type')}, {', '.join(sc.get('aspects', [])) or 'Neutral'})")
        lines.append(f"\n[View all similar cards and neural similarity graph](https://swu.avascry.com/similar/{card.get('slug')})")

    lines.append(f"\n*Source: AvaScry Star Wars Unlimited (https://swu.avascry.com/card/{card.get('slug')})*")
    return Response(
        content="\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Link": f'</card/{card.get("slug", slug)}>; rel="canonical", </similar/{card.get("slug", slug)}.md>; rel="related"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/card/{slug}.json", response_class=JSONResponse)
async def swu_card_json(slug: str):
    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return JSONResponse(
        content=card,
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/card/{slug}.xml", response_class=Response)
async def swu_card_xml(slug: str):
    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    root = ET.Element("card")
    ET.SubElement(root, "slug").text = str(card.get("slug") or "")
    ET.SubElement(root, "title").text = str(card.get("title") or card.get("name") or "")
    if card.get("subtitle"):
        ET.SubElement(root, "subtitle").text = str(card.get("subtitle"))
    
    exp_el = ET.SubElement(root, "expansion")
    exp_code = card.get("expansion", {}).get("code") if isinstance(card.get("expansion"), dict) else card.get("set_code")
    exp_name = card.get("expansion", {}).get("name") if isinstance(card.get("expansion"), dict) else card.get("set_name")
    if exp_code:
        exp_el.set("code", str(exp_code))
    exp_el.text = str(exp_name or "")
    
    ET.SubElement(root, "cardNumber").text = str(card.get("card_number") or card.get("number") or "")
    ET.SubElement(root, "type").text = str(card.get("type") or "")
    if card.get("type2"):
        ET.SubElement(root, "type2").text = str(card.get("type2"))
    if card.get("cost") is not None:
        ET.SubElement(root, "cost").text = str(card.get("cost"))
    if card.get("power") is not None:
        ET.SubElement(root, "power").text = str(card.get("power"))
    if card.get("hp") is not None:
        ET.SubElement(root, "hp").text = str(card.get("hp"))
    
    aspects_el = ET.SubElement(root, "aspects")
    for a in card.get("aspects") or []:
        ET.SubElement(aspects_el, "aspect").text = str(a)
        
    traits_el = ET.SubElement(root, "traits")
    for t in card.get("traits") or []:
        ET.SubElement(traits_el, "trait").text = str(t)
        
    arenas_el = ET.SubElement(root, "arenas")
    for ar in card.get("arenas") or []:
        ET.SubElement(arenas_el, "arena").text = str(ar)
        
    if card.get("rarity"):
        ET.SubElement(root, "rarity").text = str(card.get("rarity"))
    if card.get("artist"):
        ET.SubElement(root, "artist").text = str(card.get("artist"))
    if card.get("text"):
        ET.SubElement(root, "text").text = str(card.get("text"))
    if card.get("deploy_box"):
        ET.SubElement(root, "deployBox").text = str(card.get("deploy_box"))
    if card.get("rules"):
        ET.SubElement(root, "rules").text = str(card.get("rules"))

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return Response(
        content=xml_bytes,
        media_type="application/xml; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/card/{slug}", response_class=HTMLResponse)
async def swu_card_detail(slug: str, request: Request):
    cache_key = f"swu:card:{slug.lower()}"
    cached_html = get_page_cache(cache_key)
    if cached_html:
        return HTMLResponse(
            content=cached_html,
            headers={
                "Vary": "Accept",
                "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
                "Link": f'</card/{slug}.md>; rel="alternate"; type="text/markdown", </card/{slug}.json>; rel="alternate"; type="application/json", </card/{slug}.xml>; rel="alternate"; type="application/xml"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes",
                "X-Cache": "HIT"
            }
        )

    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
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

    # Hydrate official rulings and clarifications from db.clarifications
    rulings_query = {"$or": []}
    if card_slug:
        rulings_query["$or"].append({"card_slug": card_slug})
    if slug and slug != card_slug:
        rulings_query["$or"].append({"card_slug": slug})
    if current_num and current_exp:
        rulings_query["$or"].append({"card_number": current_num, "card_set": current_exp})
        if str(current_num).isdigit():
            rulings_query["$or"].append({"card_number": int(current_num), "card_set": current_exp})

    official_rulings = []
    if rulings_query["$or"]:
        raw_rulings = list(db.clarifications.find(
            rulings_query, 
            {"_id": 0, "question": 1, "answer": 1, "ruling_text": 1, "source": 1, "authority": 1, "slug": 1, "status": 1}
        ))
        seen_texts = set()
        for r in raw_rulings:
            txt = (r.get("ruling_text") or r.get("answer") or "").strip()
            if txt and txt not in seen_texts:
                seen_texts.add(txt)
                official_rulings.append({
                    "question": r.get("question") or f"How does {card.get('title')} interact with other cards?",
                    "answer": txt,
                    "source": r.get("source") or "Official Fantasy Flight Games Rulings & Errata Document",
                    "authority": r.get("authority") or "official",
                    "slug": r.get("slug")
                })
    card["official_rulings"] = official_rulings

    # Similar/synergy cards: query precomputed neural similarity graph, with fallback to trait/aspect query
    synergy_cards = []
    alternate_leaders = []
    current_type = card.get("type", "")
    current_title = (card.get("title") or card.get("name") or "").strip().lower()

    sim_doc = db.similar_cards.find_one({"$or": [{"slug": card_slug}, {"slug": slug}]})
    if sim_doc and sim_doc.get("similar"):
        for sc in sim_doc["similar"]:
            sc_copy = dict(sc)
            sc_slug = sc_copy.get("slug") or ""
            base_sc_slug = sc_slug[:-1] if sc_slug.endswith(("F", "f")) else sc_slug
            if os.path.isfile(f"public/images/swu/{sc_slug}_front.png"):
                sc_copy["art_front"] = f"/images/swu/{sc_slug}_front.png"
            elif os.path.isfile(f"public/images/swu/{base_sc_slug}_front.png"):
                sc_copy["art_front"] = f"/images/swu/{base_sc_slug}_front.png"
            else:
                sc_copy["art_front"] = sc_copy.get("art_front")

            sc_type = sc_copy.get("type", "")
            sc_title = (sc_copy.get("title") or sc_copy.get("name") or "").strip().lower()

            # For Leaders: segment into playable deck cards vs alternate leaders
            if current_type == "Leader":
                if sc_type == "Leader":
                    if sc_title != current_title and len(alternate_leaders) < 6:
                        alternate_leaders.append(sc_copy)
                else:
                    if len(synergy_cards) < 6:
                        synergy_cards.append(sc_copy)
            else:
                if len(synergy_cards) < 6:
                    synergy_cards.append(sc_copy)

    # Fallback if synergy cards insufficient
    if len(synergy_cards) < 6:
        traits = card.get("traits", [])
        aspects = card.get("aspects", [])
        synergy_query = {
            "slug": {"$ne": card.get("slug")},
            "variant_type": {"$nin": ["Foil", "Hyperspace Foil", "Prestige Foil", "Prestige Serialized"]},
            "$or": [
                {"traits": {"$in": traits}} if traits else {},
                {"aspects": {"$in": aspects}} if aspects else {}
            ]
        }
        if current_type == "Leader":
            synergy_query["type"] = {"$ne": "Leader"}
        synergy_query["$or"] = [cond for cond in synergy_query["$or"] if cond]
        if synergy_query["$or"]:
            raw_synergy = list(db.cards.find(synergy_query, {
                "_id": 0, "slug": 1, "title": 1, "name": 1, "subtitle": 1, "art_front": 1, "front_image": 1, "type": 1, "cost": 1, "aspects": 1, "variant_type": 1
            }).limit(30))
            seen_slugs = {sc["slug"] for sc in synergy_cards}
            seen_slugs.add(card.get("slug"))
            for sc in raw_synergy:
                s_slug = sc.get("slug") or ""
                if s_slug in seen_slugs:
                    continue
                seen_slugs.add(s_slug)
                t = sc.get("title") or sc.get("name")
                sc["title"] = t
                base_sc_slug = s_slug[:-1] if s_slug.endswith(("F", "f")) else s_slug
                if os.path.isfile(f"public/images/swu/{s_slug}_front.png"):
                    sc["art_front"] = f"/images/swu/{s_slug}_front.png"
                elif os.path.isfile(f"public/images/swu/{base_sc_slug}_front.png"):
                    sc["art_front"] = f"/images/swu/{base_sc_slug}_front.png"
                else:
                    sc["art_front"] = sc.get("local_image_front") or sc.get("art_front") or sc.get("front_image")
                synergy_cards.append(sc)
                if len(synergy_cards) >= 6:
                    break

    # Tag each card with its human-friendly gameplay synergy relationship badge
    for sc in synergy_cards:
        sc["synergy_reason"] = determine_swu_synergy_reason(card, sc)
    for al in alternate_leaders:
        al["synergy_reason"] = determine_swu_synergy_reason(card, al)

    response = templates.TemplateResponse(
        request=request,
        name="swu/card.html",
        context={
            "card": card,
            "base_path": get_base_prefix(request),
            "prev_card": prev_card,
            "next_card": next_card,
            "synergy_cards": synergy_cards,
            "alternate_leaders": alternate_leaders
        },
        headers={
            "Vary": "Accept",
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Link": f'</card/{card.get("slug", slug)}.md>; rel="alternate"; type="text/markdown", </card/{card.get("slug", slug)}.json>; rel="alternate"; type="application/json", </card/{card.get("slug", slug)}.xml>; rel="alternate"; type="application/xml", </similar/{card.get("slug", slug)}>; rel="related", </similar/{card.get("slug", slug)}.json>; rel="related"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes",
            "X-Cache": "MISS"
        }
    )
    try:
        set_page_cache(cache_key, response.body.decode("utf-8"))
    except Exception:
        pass
    return response

# ---------------------------------------------------------
# Feature: Neural Embeddings & Similarity Graph Endpoints
# ---------------------------------------------------------
@swu_router.get("/vector/{identifier}", include_in_schema=False)
@swu_router.get("/vector/{identifier}.json", include_in_schema=False)
@swu_router.head("/vector/{identifier}", include_in_schema=False)
@swu_router.head("/vector/{identifier}.json", include_in_schema=False)
async def swu_vector_embedding(identifier: str):
    """Expose raw 4096-dimensional Qwen 8B vector embedding for a Star Wars: Unlimited card."""
    clean_id = identifier.lower().replace(".json", "").strip()
    if not clean_id or clean_id in ("", ".", "..", ".md", ".json"):
        raise HTTPException(status_code=404, detail="Vector embedding not found")

    db = get_swu_db()

    # 1. Match directly in embeddings_swu by slug or title
    doc = db.embeddings_swu.find_one({
        "$or": [
            {"slug": clean_id},
            {"title": {"$regex": f"^{re.escape(clean_id.replace('-', ' '))}$", "$options": "i"}}
        ]
    })

    # 2. If not found, resolve canonical card via similar_cards or cards collection
    if not doc:
        sim_doc = db.similar_cards.find_one({"slug": clean_id})
        if sim_doc and sim_doc.get("canonical_slug"):
            doc = db.embeddings_swu.find_one({"slug": sim_doc["canonical_slug"]})
        if not doc:
            card_doc = db.cards.find_one({"$or": [{"slug": clean_id}, {"name_slug": clean_id}]})
            if card_doc:
                t = (card_doc.get("title") or card_doc.get("name") or "").strip()
                sub = (card_doc.get("subtitle") or "").strip()
                doc = db.embeddings_swu.find_one({"title": t, "subtitle": sub})

    if not doc:
        raise HTTPException(status_code=404, detail="Vector embedding not found")

    slug = doc.get("slug") or clean_id
    title = doc.get("title") or clean_id.replace('-', ' ').title()
    embedding = doc.get("embedding", [])

    return JSONResponse(
        content={
            "name": title,
            "subtitle": doc.get("subtitle", ""),
            "slug": slug,
            "model": doc.get("model") or "qwen3-embedding:8b",
            "dimensions": len(embedding) or 4096,
            "version": "1.0",
            "context_text": doc.get("context_text", ""),
            "links": {
                "vector": f"https://swu.avascry.com/vector/{slug}.json",
                "similar": f"https://swu.avascry.com/similar/{slug}.json",
                "html": f"https://swu.avascry.com/card/{slug}",
                "markdown": f"https://swu.avascry.com/similar/{slug}.md"
            },
            "embedding": embedding
        },
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Access-Control-Allow-Origin": "*",
            "Link": f'</similar/{slug}.json>; rel="related"; type="application/json", </card/{slug}>; rel="up"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/similar/{slug}.md", response_class=PlainTextResponse)
@swu_router.head("/similar/{slug}.md")
async def swu_similar_cards_markdown(slug: str, request: Request):
    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    title = card.get("title") or card.get("name") or "Card"
    subtitle = f": {card.get('subtitle')}" if card.get("subtitle") else ""

    lines = [
        f"# Mechanically Similar Cards to {title}{subtitle}",
        f"**Source Card:** [{title}{subtitle}](https://swu.avascry.com/card/{card.get('slug')})",
        f"**Aspects:** {', '.join(card.get('aspects', [])) or 'Neutral'} | **Traits:** {', '.join(card.get('traits', [])) or 'None'}",
        "\nComputed via 4096-dimensional neural vector embeddings (`qwen3-embedding:8b`) across all unique Star Wars Unlimited cards.\n",
        "## Top Similar Cards\n"
    ]

    sim_doc = db.similar_cards.find_one({"$or": [{"slug": card.get("slug")}, {"slug": slug}]})
    similar = sim_doc.get("similar", []) if sim_doc else []

    if not similar:
        lines.append("*(No similarity records precomputed for this card)*")
    else:
        for idx, sc in enumerate(similar, 1):
            sc_title = sc.get("title") or sc.get("slug")
            sc_sub = f": {sc.get('subtitle')}" if sc.get("subtitle") else ""
            pct = int(round(sc.get("score", 0) * 100))
            aspects = ", ".join(sc.get("aspects", [])) or "Neutral"
            traits = ", ".join(sc.get("traits", [])) or "None"
            stats = []
            if sc.get("cost") is not None:
                stats.append(f"Cost: {sc.get('cost')}")
            if sc.get("power") is not None:
                stats.append(f"Power: {sc.get('power')}")
            if sc.get("hp") is not None:
                stats.append(f"HP: {sc.get('hp')}")
            stat_str = f" | {', '.join(stats)}" if stats else ""
            lines.append(f"{idx}. **[{sc_title}{sc_sub}](https://swu.avascry.com/card/{sc.get('slug')})** — **{pct}% match**")
            lines.append(f"   - Type: {sc.get('type', 'Unknown')} | Aspects: {aspects} | Traits: {traits}{stat_str}")

    lines.append(f"\n*Source: AvaScry Star Wars Unlimited Neural Graph (https://swu.avascry.com/similar/{card.get('slug')})*")

    return Response(
        content="\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Link": f'</similar/{card.get("slug", slug)}>; rel="canonical", </similar/{card.get("slug", slug)}.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/similar/{slug}.json", response_class=JSONResponse)
@swu_router.head("/similar/{slug}.json")
async def swu_similar_cards_json(slug: str, request: Request):
    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    sim_doc = db.similar_cards.find_one({"$or": [{"slug": card.get("slug")}, {"slug": slug}]})
    similar = sim_doc.get("similar", []) if sim_doc else []
    card_slug = card.get("slug", slug)

    data = {
        "card": {
            "slug": card.get("slug"),
            "title": card.get("title") or card.get("name"),
            "subtitle": card.get("subtitle") or "",
            "type": card.get("type"),
            "aspects": card.get("aspects", []),
            "traits": card.get("traits", []),
            "cost": card.get("cost"),
            "power": card.get("power"),
            "hp": card.get("hp")
        },
        "algorithm": "4096-dimensional Qwen 8B Cosine Similarity",
        "model": "qwen3-embedding:8b",
        "dimension": 4096,
        "count": len(similar),
        "links": {
            "vector": f"https://swu.avascry.com/vector/{card_slug}.json",
            "similar": f"https://swu.avascry.com/similar/{card_slug}.json",
            "html": f"https://swu.avascry.com/card/{card_slug}",
            "markdown": f"https://swu.avascry.com/similar/{card_slug}.md"
        },
        "similar": similar
    }

    return JSONResponse(
        content=data,
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Access-Control-Allow-Origin": "*",
            "Link": f'</similar/{card_slug}>; rel="canonical", </similar/{card_slug}.md>; rel="alternate"; type="text/markdown", </vector/{card_slug}.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/similar/{slug}", response_class=HTMLResponse)
@swu_router.head("/similar/{slug}")
async def swu_similar_cards_page(slug: str, request: Request):
    db = get_swu_db()
    card = db.cards.find_one({"$or": [{"slug": slug}, {"name_slug": slug}]}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

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

    similar_cards = []
    sim_doc = db.similar_cards.find_one({"$or": [{"slug": card_slug}, {"slug": slug}]})
    if sim_doc and sim_doc.get("similar"):
        for sc in sim_doc["similar"]:
            sc_copy = dict(sc)
            sc_slug = sc_copy.get("slug") or ""
            base_sc_slug = sc_slug[:-1] if sc_slug.endswith(("F", "f")) else sc_slug
            if os.path.isfile(f"public/images/swu/{sc_slug}_front.png"):
                sc_copy["art_front"] = f"/images/swu/{sc_slug}_front.png"
            elif os.path.isfile(f"public/images/swu/{base_sc_slug}_front.png"):
                sc_copy["art_front"] = f"/images/swu/{base_sc_slug}_front.png"
            else:
                sc_copy["art_front"] = sc_copy.get("art_front")
            similar_cards.append(sc_copy)

    return templates.TemplateResponse(
        request=request,
        name="swu/similar.html",
        context={
            "card": card,
            "similar_cards": similar_cards,
            "base_path": get_base_prefix(request),
        },
        headers={
            "Vary": "Accept",
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Link": f'</similar/{card.get("slug", slug)}.md>; rel="alternate"; type="text/markdown", </similar/{card.get("slug", slug)}.json>; rel="alternate"; type="application/json", </card/{card.get("slug", slug)}>; rel="up"',
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
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/keyword/{slug}.json", response_class=JSONResponse)
async def swu_keyword_json(slug: str):
    db = get_swu_db()
    clean_slug = slug.removesuffix(".json")
    kw = db.keywords.find_one({"slug": clean_slug}, {"_id": 0})
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return JSONResponse(
        content=kw,
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/keyword/{slug}.md", response_class=PlainTextResponse)
async def swu_keyword_markdown(slug: str):
    db = get_swu_db()
    clean_slug = slug.removesuffix(".md")
    kw = db.keywords.find_one({"slug": clean_slug}, {"_id": 0})
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    lines = [
        f"# {kw.get('name')}",
        f"**Slug:** {kw.get('slug')}",
    ]
    if kw.get("reminder"):
        lines.append(f"**Reminder:** {kw.get('reminder')}")
    if kw.get("description"):
        lines.append(f"\n## Definition\n{kw.get('description')}")
    if kw.get("rules_reference"):
        lines.append(f"\n## Rules Reference\n{kw.get('rules_reference')}")
    lines.append(f"\n*Source: AvaScry Star Wars Unlimited (https://swu.avascry.com/keyword/{kw.get('slug')})*")
    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/keyword/{slug}", response_class=HTMLResponse)
async def swu_keyword_detail(request: Request, slug: str):
    db = get_swu_db()
    clean_slug = slug.removesuffix(".json").removesuffix(".md")
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
        },
        headers={
            "Vary": "Accept",
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Link": f'</keyword/{kw["slug"]}.md>; rel="alternate"; type="text/markdown", </keyword/{kw["slug"]}.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

# ---------------------------------------------------------
# Feature 1B: Traits & Tribal Lexicon Directory
# ---------------------------------------------------------
@swu_router.get("/traits", response_class=HTMLResponse)
async def swu_traits_list(request: Request):
    db = get_swu_db()
    # Distinct traits across all cards
    traits_raw = [t for t in db.cards.distinct("traits") if t]
    
    # Aggregate counts and canonical naming
    pipeline = [
        {"$match": {"traits": {"$exists": True, "$ne": []}}},
        {"$unwind": "$traits"},
        {"$group": {"_id": "$traits", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}}
    ]
    aggr = list(db.cards.aggregate(pipeline))
    
    # Merge case variants like "Twi'Lek" vs "Twi'lek"
    slug_map = {}
    for item in aggr:
        raw_name = item["_id"]
        if not raw_name:
            continue
        slug = re.sub(r'[^a-z0-9]+', '-', raw_name.lower()).strip('-')
        count = item.get("count", 0)
        if slug not in slug_map:
            slug_map[slug] = {"name": raw_name, "slug": slug, "count": count}
        else:
            slug_map[slug]["count"] += count
            if raw_name == "Twi'lek":
                slug_map[slug]["name"] = raw_name

    traits = sorted(slug_map.values(), key=lambda x: x["name"].lower())

    return templates.TemplateResponse(
        request=request,
        name="swu/traits.html",
        context={
            "base_path": get_base_prefix(request),
            "traits": traits,
            "current_trait": None,
            "cards": []
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/trait/{slug}.json", response_class=JSONResponse)
async def swu_trait_json(slug: str):
    db = get_swu_db()
    clean_slug = slug.removesuffix(".json")
    
    # Find matching trait name
    traits_raw = [t for t in db.cards.distinct("traits") if t]
    matched_names = [t for t in traits_raw if re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-') == clean_slug]
    if not matched_names:
        raise HTTPException(status_code=404, detail="Trait not found")
    
    canonical_name = "Twi'lek" if "Twi'lek" in matched_names else matched_names[0]
    
    cards = list(db.cards.find(
        {"traits": {"$in": matched_names}},
        {"_id": 0, "slug": 1, "title": 1, "name": 1, "subtitle": 1, "card_number": 1, "number": 1,
         "expansion": 1, "set_code": 1, "type": 1, "cost": 1, "aspects": 1, "traits": 1, "arenas": 1}
    ).sort([("card_number", 1)]))

    return JSONResponse(
        content={
            "name": canonical_name,
            "slug": clean_slug,
            "card_count": len(cards),
            "cards": cards,
            "links": {
                "self": f"https://swu.avascry.com/trait/{clean_slug}.json",
                "html": f"https://swu.avascry.com/trait/{clean_slug}",
                "markdown": f"https://swu.avascry.com/trait/{clean_slug}.md"
            }
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/trait/{slug}.md", response_class=PlainTextResponse)
async def swu_trait_markdown(slug: str):
    db = get_swu_db()
    clean_slug = slug.removesuffix(".md")
    
    traits_raw = [t for t in db.cards.distinct("traits") if t]
    matched_names = [t for t in traits_raw if re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-') == clean_slug]
    if not matched_names:
        raise HTTPException(status_code=404, detail="Trait not found")
    
    canonical_name = "Twi'lek" if "Twi'lek" in matched_names else matched_names[0]
    
    cards = list(db.cards.find(
        {"traits": {"$in": matched_names}},
        {"_id": 0, "slug": 1, "title": 1, "name": 1, "subtitle": 1, "card_number": 1, "number": 1,
         "expansion": 1, "set_code": 1, "type": 1, "cost": 1, "aspects": 1}
    ).sort([("card_number", 1)]))

    lines = [
        f"# {canonical_name} — Star Wars: Unlimited Trait Cards",
        f"> Complete directory of canonical Star Wars: Unlimited cards possessing the {canonical_name} trait.",
        f"\n- **Trait Name:** {canonical_name}",
        f"- **Slug:** {clean_slug}",
        f"- **Total Cards:** {len(cards)}",
        f"- **Canonical HTML:** https://swu.avascry.com/trait/{clean_slug}",
        f"- **JSON Endpoint:** https://swu.avascry.com/trait/{clean_slug}.json",
        f"\n## Cards ({len(cards)})\n"
    ]

    for c in cards:
        t = c.get("title") or c.get("name") or c.get("slug")
        sub = f": {c['subtitle']}" if c.get("subtitle") else ""
        num = c.get("card_number") or c.get("number") or ""
        set_code = (c.get("expansion") or {}).get("code") or c.get("set_code") or ""
        c_type = c.get("type", "")
        cost = f"Cost: {c['cost']}" if c.get("cost") is not None else ""
        aspects = ", ".join(c.get("aspects", [])) if c.get("aspects") else "Neutral"
        meta_parts = [p for p in [f"{set_code} #{num}", c_type, cost, aspects] if p]
        meta = f" ({' | '.join(meta_parts)})" if meta_parts else ""
        lines.append(f"- [{t}{sub}](https://swu.avascry.com/card/{c['slug']}){meta}")

    lines.append(f"\n*Source: AvaScry Star Wars Unlimited (https://swu.avascry.com/trait/{clean_slug})*")

    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/trait/{slug}", response_class=HTMLResponse)
async def swu_trait_detail(request: Request, slug: str):
    db = get_swu_db()
    clean_slug = slug.removesuffix(".json").removesuffix(".md")
    
    traits_raw = [t for t in db.cards.distinct("traits") if t]
    matched_names = [t for t in traits_raw if re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-') == clean_slug]
    if not matched_names:
        raise HTTPException(status_code=404, detail="Trait not found")
    
    canonical_name = "Twi'lek" if "Twi'lek" in matched_names else matched_names[0]

    # Find canonical cards belonging to this trait
    cards = list(db.cards.find(
        {"traits": {"$in": matched_names}},
        {
            "_id": 0, "slug": 1, "title": 1, "name": 1, "subtitle": 1, "card_number": 1, "number": 1,
            "expansion": 1, "set_code": 1, "art_front": 1, "front_image": 1, "type": 1,
            "cost": 1, "power": 1, "hp": 1, "aspects": 1, "variant_type": 1
        }
    ).sort([("card_number", 1)]))

    # Resolve local images for thumbnails
    for c in cards:
        c_slug = c.get("slug") or ""
        base_c_slug = c_slug[:-1] if c_slug.endswith(("F", "f")) else c_slug
        if os.path.isfile(f"public/images/swu/{c_slug}_front.png"):
            c["art_front"] = f"/images/swu/{c_slug}_front.png"
        elif os.path.isfile(f"public/images/swu/{base_c_slug}_front.png"):
            c["art_front"] = f"/images/swu/{base_c_slug}_front.png"

    current_trait = {
        "name": canonical_name,
        "slug": clean_slug,
        "count": len(cards)
    }

    return templates.TemplateResponse(
        request=request,
        name="swu/traits.html",
        context={
            "base_path": get_base_prefix(request),
            "traits": [],
            "current_trait": current_trait,
            "cards": cards
        },
        headers={
            "Vary": "Accept",
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Link": f'</trait/{clean_slug}.md>; rel="alternate"; type="text/markdown", </trait/{clean_slug}.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
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
        },
        headers={
            "Vary": "Accept",
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Link": '</rules.md>; rel="alternate"; type="text/markdown", </rules.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
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
        },
        headers={
            "Vary": "Accept",
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
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
        },
        headers={
            "Vary": "Accept",
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
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
        },
        headers={
            "Vary": "Accept",
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/llms.txt", response_class=PlainTextResponse)
async def swu_llms_txt(request: Request):
    content = """# AvaScry Star Wars: Unlimited (SWU)
> Comprehensive canonical card database, aspect interactions, rules citation engine, and official card clarifications for Star Wars: Unlimited.

## LLM Retrieval Guidelines
- Base URL: https://swu.avascry.com
- Master HTML Sitemap: https://swu.avascry.com/sitemap.html
- Master Markdown Sitemap: https://swu.avascry.com/sitemap.md
- Machine readable format for any card: https://swu.avascry.com/card/{slug}.md
- Machine JSON format for any card: https://swu.avascry.com/card/{slug}.json
- Neural Vector Embedding (4096-dim): https://swu.avascry.com/vector/{slug}.json
- Neural Similarity Recommendations: https://swu.avascry.com/similar/{slug}.md
- Machine JSON format for any keyword: https://swu.avascry.com/keyword/{slug}.json
- Machine JSON format for any trait: https://swu.avascry.com/trait/{slug}.json
- Machine Markdown format for any trait: https://swu.avascry.com/trait/{slug}.md
- Traits & Tribal Directory: https://swu.avascry.com/traits
- Full XML Sitemap: https://swu.avascry.com/sitemap.xml

## Rules & Clarifications System
- Star Wars Comprehensive Rules: https://swu.avascry.com/rules
- Section permalinks: https://swu.avascry.com/rule/{slug} (e.g., /rule/1-general-concepts)
- Official Card Clarifications & Errata: https://swu.avascry.com/rulings
- Keyword Definitions & Reminders: https://swu.avascry.com/keywords
- Traits & Tribal Lexicon: https://swu.avascry.com/traits

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

## Unified Discord Identity & Network SSO
- Part of the unified AvaScry Card Network (MTG, SWU, Dominion, Necromunda).
- Single Discord OAuth sign-in shared network-wide across `swu.avascry.com` and all sister domains.
- Built for Star Wars tabletop pods with 1-click deck sharing, card embeds, and community errata lookup directly to Discord servers.
"""
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

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
        "## Unified Discord Identity & Network Single Sign-On (SSO)",
        "- Part of the unified AvaScry Card Network (MTG, SWU, Dominion, Necromunda).",
        "- Exclusive Discord OAuth authentication shared network-wide across all sister domains.",
        "- Shared Discord identity powers cross-game deck stash synchronization, Discord pod sharing, and community errata lookup.\n",
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

    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

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
    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

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
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
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

## Authentication & Discord Community Features
- **Network SSO**: Authentication operates across the entire AvaScry network (`avascry.com`, `swu.avascry.com`, `dominion.avascry.com`, `necromunda.avascry.com`) using a single Discord OAuth session.
- **Zero-Password Tabletop Identity**: No email or password management required; user profile, collections, and custom SWU decklists synchronize via Discord.
- **Pod-Ready**: Structured Markdown and JSON payloads are optimized for Discord community bots, visual deck previews, and tournament rules lookups.
"""
    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

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
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"}
    )

SWU_SITEMAP_CACHE = None
SWU_SITEMAP_CACHE_TS = 0.0

def get_swu_sitemap_data():
    global SWU_SITEMAP_CACHE, SWU_SITEMAP_CACHE_TS
    import time
    now = time.time()
    if SWU_SITEMAP_CACHE and (now - SWU_SITEMAP_CACHE_TS) < 3600:
        return SWU_SITEMAP_CACHE

    db = get_swu_db()

    # 1. Sets
    sets = []
    raw_sets = list(db.sets.find({}, {"_id": 0}))
    for s in raw_sets:
        code = s.get("setId") or s.get("code") or ""
        name = s.get("fullName") or s.get("name") or code
        count = s.get("numberCards") or s.get("card_count") or 0
        if code:
            sets.append({"code": code, "name": name, "card_count": count})
    if not sets:
        set_aggr = list(db.cards.aggregate([
            {"$group": {"_id": "$expansion.code", "name": {"$first": "$expansion.name"}, "card_count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]))
        sets = [{"code": s["_id"], "name": s.get("name") or s["_id"], "card_count": s["card_count"]} for s in set_aggr if s.get("_id")]

    # 2. Keywords
    keywords = list(db.keywords.find({}, {"_id": 0, "slug": 1, "name": 1}).sort("name", 1))

    # 2B. Traits
    traits_pipeline = [
        {"$match": {"traits": {"$exists": True, "$ne": []}}},
        {"$unwind": "$traits"},
        {"$group": {"_id": "$traits", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}}
    ]
    traits_aggr = list(db.cards.aggregate(traits_pipeline))
    traits_slug_map = {}
    for item in traits_aggr:
        raw_name = item["_id"]
        if not raw_name:
            continue
        slug = re.sub(r'[^a-z0-9]+', '-', raw_name.lower()).strip('-')
        count = item.get("count", 0)
        if slug not in traits_slug_map:
            traits_slug_map[slug] = {"name": raw_name, "slug": slug, "count": count}
        else:
            traits_slug_map[slug]["count"] += count
            if raw_name == "Twi'lek":
                traits_slug_map[slug]["name"] = raw_name
    traits = sorted(traits_slug_map.values(), key=lambda x: x["name"].lower())

    # 3. Canonical cards grouped alphabetically
    cards_cursor = db.cards.find({}, {
        "_id": 0, "slug": 1, "title": 1, "name": 1, "subtitle": 1, "variant_type": 1, "card_number": 1
    }).sort([("variant_type", -1), ("card_number", 1)])

    canonical_map = {}
    for c in cards_cursor:
        t = (c.get("title") or c.get("name") or "").strip()
        sub = (c.get("subtitle") or "").strip()
        if not t:
            continue
        c["title"] = t
        c["subtitle"] = sub
        key = f"{t.lower()}::{sub.lower()}"
        if key not in canonical_map:
            canonical_map[key] = c
        else:
            existing_var = str(canonical_map[key].get("variant_type", "")).lower()
            new_var = str(c.get("variant_type", "")).lower()
            if new_var in ("normal", "none", "") and existing_var not in ("normal", "none", ""):
                canonical_map[key] = c

    unique_cards = sorted(canonical_map.values(), key=lambda x: (x["title"].lower(), x.get("subtitle", "").lower()))

    import string
    alphabet = list(string.ascii_uppercase) + ["#"]
    cards_by_letter = {letter: [] for letter in alphabet}

    for c in unique_cards:
        first = c["title"][0].upper() if c["title"] else "#"
        if first in cards_by_letter:
            cards_by_letter[first].append(c)
        else:
            cards_by_letter["#"].append(c)

    cards_by_letter = {k: v for k, v in cards_by_letter.items() if v}

    cached_data = {
        "sets": sets,
        "keywords": keywords,
        "traits": traits,
        "total_cards": len(unique_cards),
        "unique_cards": unique_cards,
        "cards_by_letter": cards_by_letter,
        "alphabet": alphabet
    }
    SWU_SITEMAP_CACHE = cached_data
    SWU_SITEMAP_CACHE_TS = now
    return cached_data

@swu_router.get("/sitemap.html", response_class=HTMLResponse)
@swu_router.head("/sitemap.html")
async def swu_sitemap_html(request: Request):
    """High-density zero-JS HTML Master Sitemap with crawler multi-badges."""
    data = get_swu_sitemap_data()
    return templates.TemplateResponse(
        request=request,
        name="swu/sitemap.html",
        context={
            "base_path": get_base_prefix(request),
            "sets": data["sets"],
            "keywords": data["keywords"],
            "traits": data.get("traits", []),
            "total_cards": data["total_cards"],
            "cards_by_letter": data["cards_by_letter"],
            "alphabet": data["alphabet"]
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Link": '</sitemap.md>; rel="alternate"; type="text/markdown", </sitemap.xml>; rel="alternate"; type="application/xml"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/sitemap.md", response_class=PlainTextResponse)
@swu_router.head("/sitemap.md")
async def swu_sitemap_markdown():
    """Ultra-dense plain-text Markdown sitemap for AI crawlers (ClaudeBot, GPTBot, Perplexity)."""
    data = get_swu_sitemap_data()
    lines = [
        "# Star Wars: Unlimited Master Machine Sitemap",
        "> Complete directory of canonical cards, expansions, keywords, rules citations, neural vectors, and similarity graphs.",
        f"\n- **Base URL:** https://swu.avascry.com",
        f"- **Canonical Cards:** {data['total_cards']}",
        f"- **Expansions:** {len(data['sets'])}",
        f"- **Keywords:** {len(data['keywords'])}",
        f"- **Traits & Tribal Lexicons:** {len(data.get('traits', []))}",
        f"- **HTML Master Directory:** https://swu.avascry.com/sitemap.html",
        f"- **XML Sitemap:** https://swu.avascry.com/sitemap.xml",
        f"- **LLMs Manifest:** https://swu.avascry.com/llms.txt",
        "\n## Expansions & Sets"
    ]
    for s in data["sets"]:
        lines.append(f"- [{s['name']} ({s['code']})](https://swu.avascry.com/?set={s['code']}) — {s['card_count']} cards")

    lines.append("\n## Keywords & Game Mechanics")
    for kw in data["keywords"]:
        lines.append(f"- [{kw['name']}](https://swu.avascry.com/keyword/{kw['slug']}) • [MD](https://swu.avascry.com/keyword/{kw['slug']}.md) • [JSON](https://swu.avascry.com/keyword/{kw['slug']}.json)")

    lines.append(f"\n## Traits & Tribal Lexicons ({len(data.get('traits', []))})")
    for t in data.get("traits", []):
        lines.append(f"- [{t['name']}](https://swu.avascry.com/trait/{t['slug']}) ({t['count']} cards) • [MD](https://swu.avascry.com/trait/{t['slug']}.md) • [JSON](https://swu.avascry.com/trait/{t['slug']}.json)")

    lines.append("\n## Comprehensive Rules & Rulings")
    lines.append("- [Comprehensive Rules Index](https://swu.avascry.com/rules) • [MD](https://swu.avascry.com/rules.md) • [JSON](https://swu.avascry.com/rules.json)")
    lines.append("- [Official Card Rulings & Errata](https://swu.avascry.com/rulings)")

    lines.append(f"\n## Canonical Cards Directory ({data['total_cards']})")
    for c in data["unique_cards"]:
        title = c["title"]
        sub = f": {c['subtitle']}" if c.get("subtitle") else ""
        slug = c["slug"]
        lines.append(f"- [{title}{sub}](https://swu.avascry.com/card/{slug}) • [MD](https://swu.avascry.com/card/{slug}.md) • [JSON](https://swu.avascry.com/card/{slug}.json) • [Vector](https://swu.avascry.com/vector/{slug}.json) • [Similar](https://swu.avascry.com/similar/{slug})")

    content = "\n".join(lines)
    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "X-Markdown-Tokens": str(len(content.split())),
            "Link": '</sitemap.html>; rel="alternate"; type="text/html", </sitemap.xml>; rel="alternate"; type="application/xml"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@swu_router.get("/sitemap.xml", response_class=Response)
async def swu_sitemap_xml():
    """
    Lean, high-authority launch sitemap:
    - Top-level pillars & legal compliance pages (8 URLs)
    - 127 sampled cards for healthy crawl signal
    - Cache-Control 24h to prevent edge latency
    """
    db = get_swu_db()
    cards = list(db.cards.aggregate([
        {"$sample": {"size": 127}},
        {"$project": {"slug": 1, "_id": 0}}
    ]))

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '  <url><loc>https://swu.avascry.com/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
        '  <url><loc>https://swu.avascry.com/keywords</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        '  <url><loc>https://swu.avascry.com/traits</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        '  <url><loc>https://swu.avascry.com/rules</loc><changefreq>monthly</changefreq><priority>0.9</priority></url>',
        '  <url><loc>https://swu.avascry.com/rulings</loc><changefreq>daily</changefreq><priority>0.9</priority></url>',
        '  <url><loc>https://swu.avascry.com/about</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>',
        '  <url><loc>https://swu.avascry.com/privacy</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        '  <url><loc>https://swu.avascry.com/terms</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        '  <url><loc>https://swu.avascry.com/contact</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>'
    ]
    # Include core keywords in sitemap
    keywords = list(db.keywords.find({}, {"slug": 1, "_id": 0}))
    for kw in keywords:
        if kw.get("slug"):
            xml_lines.append(f'  <url><loc>https://swu.avascry.com/keyword/{kw["slug"]}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>')
    # Include traits in sitemap
    traits_raw = [t for t in db.cards.distinct("traits") if t]
    seen_trait_slugs = set()
    for t in traits_raw:
        tslug = re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')
        if tslug and tslug not in seen_trait_slugs:
            seen_trait_slugs.add(tslug)
            xml_lines.append(f'  <url><loc>https://swu.avascry.com/trait/{tslug}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    for c in cards:
        xml_lines.append(f'  <url><loc>https://swu.avascry.com/card/{c["slug"]}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    xml_lines.append('</urlset>')

    return Response(
        content="\n".join(xml_lines),
        media_type="application/xml; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=3600"}
    )

@swu_router.get("/robots.txt", response_class=PlainTextResponse)
async def swu_robots_txt():
    return PlainTextResponse(
        """User-agent: *
Allow: /
Sitemap: https://swu.avascry.com/sitemap.xml
Sitemap: https://swu.avascry.com/sitemap.html
""",
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"}
    )

@swu_router.get("/developers", response_class=HTMLResponse)
@swu_router.get("/api", response_class=HTMLResponse)
async def swu_developers(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="swu/developers.html",
        context={"base_path": get_base_prefix(request)}
    )

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
    from mtgabyss.shared.contact import process_contact_submission
    result = await process_contact_submission(
        request=request,
        subsite_name="Star Wars: Unlimited",
        subsite_color=0xfacc15,
        extra_field_name="category",
        extra_field_label="Category"
    )
    return templates.TemplateResponse(
        request=request,
        name="swu/contact.html",
        context={
            "base_path": get_base_prefix(request),
            "success": result["success"],
            "error": result["error"],
            "values": result.get("values", {})
        }
    )

def get_swu_deckbuilder_data():
    from mtgabyss.shared.cache import RAM_CACHE, set_ram_cache
    cached = RAM_CACHE.get("swu_deckbuilder_data")
    if cached:
        return cached

    db = get_swu_db()
    raw = list(db.cards.find(
        {"type": {"$in": ["Leader", "Base", "Unit", "Event", "Upgrade"]}},
        {
            "_id": 0,
            "slug": 1,
            "name": 1,
            "title": 1,
            "subtitle": 1,
            "type": 1,
            "cost": 1,
            "aspects": 1,
            "arenas": 1,
            "traits": 1,
            "power": 1,
            "hp": 1,
            "rarity": 1,
            "variant_type": 1,
            "set_code": 1,
            "front_image": 1,
            "local_image_front": 1
        }
    ).sort([("variant_type", -1)]))

    leaders_map, bases_map, playables_map = {}, {}, {}
    for c in raw:
        t = c.get("type")
        name = c.get("name") or c.get("title") or c.get("slug")
        if not name:
            continue
        sub = c.get("subtitle") or ""
        key = (name.strip(), sub.strip())
        is_normal = (c.get("variant_type") == "Normal")
        info = {
            "slug": c.get("slug"),
            "name": name.strip(),
            "subtitle": sub.strip(),
            "type": t,
            "cost": c.get("cost") if c.get("cost") is not None else 0,
            "aspects": [a for a in (c.get("aspects") or []) if a],
            "arenas": c.get("arenas") or [],
            "traits": c.get("traits") or [],
            "power": c.get("power"),
            "hp": c.get("hp"),
            "rarity": c.get("rarity") or "Common",
            "set_code": (c.get("set_code") or "").upper(),
            "image": c.get("local_image_front") or c.get("front_image") or ""
        }
        if t == "Leader":
            if key not in leaders_map or is_normal:
                leaders_map[key] = info
        elif t == "Base":
            if key not in bases_map or is_normal:
                bases_map[key] = info
        else:
            if key not in playables_map or is_normal:
                playables_map[key] = info

    res = {
        "leaders": sorted(list(leaders_map.values()), key=lambda x: x["name"]),
        "bases": sorted(list(bases_map.values()), key=lambda x: (x.get("hp") or 30, x["name"])),
        "playables": sorted(list(playables_map.values()), key=lambda x: (x.get("cost") or 0, x["name"]))
    }
    set_ram_cache("swu_deckbuilder_data", res)
    return res

@swu_router.get("/articles", response_class=HTMLResponse)
@swu_router.get("/guides", response_class=HTMLResponse)
async def swu_articles_index(request: Request, category: Optional[str] = None):
    """
    SWU Articles & Tactical Primers Hub.
    Offers listicles, expansion breakdowns, action tempo theory, and card mechanics.
    """
    from mtgabyss.data.swu_guides import SWU_GUIDES
    base_path = get_base_prefix(request)
    all_guides = list(SWU_GUIDES.values())

    cat_slug = (category or "").strip().lower()
    if cat_slug in ("synergies", "top-lists", "lists"):
        filtered = [g for g in all_guides if "synergies" in g.get("category", "").lower() or "list" in g.get("category", "").lower()]
    elif cat_slug in ("expansions", "meta", "sets"):
        filtered = [g for g in all_guides if "expansion" in g.get("category", "").lower()]
    elif cat_slug in ("strategy", "core"):
        filtered = [g for g in all_guides if "strategy" in g.get("category", "").lower()]
    elif cat_slug in ("mechanics", "rules"):
        filtered = [g for g in all_guides if "mechanic" in g.get("category", "").lower()]
    else:
        filtered = all_guides

    return templates.TemplateResponse(
        request=request,
        name="swu/guides/index.html",
        context={
            "base_path": base_path,
            "guides": filtered,
            "current_category": cat_slug,
            "total_guides": len(all_guides)
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400"
        }
    )

@swu_router.get("/articles/{slug}", response_class=HTMLResponse)
@swu_router.get("/guides/{slug}", response_class=HTMLResponse)
async def swu_article_detail(request: Request, slug: str):
    """
    Individual SWU Article & Strategy Primer detail view.
    """
    from mtgabyss.data.swu_guides import SWU_GUIDES
    clean_slug = slug.strip().lower()
    guide = SWU_GUIDES.get(clean_slug)
    if not guide:
        raise HTTPException(status_code=404, detail="SWU article not found")

    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="swu/guides/detail.html",
        context={
            "base_path": base_path,
            "guide": guide
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400"
        }
    )

@swu_router.get("/deckbuilder", response_class=HTMLResponse)
async def swu_deckbuilder(request: Request, leader: Optional[str] = None, base: Optional[str] = None, deck: Optional[str] = None):
    """
    Interactive Star Wars: Unlimited Deck Builder & Opening Hand Simulator.
    Allows players to configure Leader and Base, view real-time resource curve,
    track aspect penalties, test draw 6-card opening hands, and resource cards.
    """
    import json
    data = get_swu_deckbuilder_data()
    base_path = get_base_prefix(request)

    return templates.TemplateResponse(
        request=request,
        name="swu/deckbuilder.html",
        context={
            "base_path": base_path,
            "leaders": data["leaders"],
            "bases": data["bases"],
            "cards_json": json.dumps(data["playables"]),
            "leaders_json": json.dumps(data["leaders"]),
            "bases_json": json.dumps(data["bases"]),
            "initial_leader": leader or "",
            "initial_base": base or "",
            "initial_deck": deck or "",
            "total_cards": len(data["playables"]),
            "total_leaders": len(data["leaders"]),
            "total_bases": len(data["bases"])
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400"
        }
    )

