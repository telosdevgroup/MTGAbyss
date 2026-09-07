"""
Star Wars: Unlimited (SWU) Sub-Application Router for swu.avascry.com and /swu.
Connects directly to MongoDB database 'avascry_swu'.
Serves HTML, Markdown (.md), JSON, sitemaps, and llms.txt endpoints for bots and humans.
"""

import re
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from db_mongo import get_mongo_db

swu_router = APIRouter(prefix="", tags=["Star Wars Unlimited"])
templates = Jinja2Templates(directory="templates")

def get_swu_db():
    client = get_mongo_db().client
    return client["avascry_swu"]

def get_base_prefix(request: Request) -> str:
    host = request.headers.get("host", "")
    from mtgabyss.network_router import extract_subdomain
    sub = extract_subdomain(host)
    if sub in ("swu", "starwars"):
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
                   view: Optional[str] = "scans"):
    db = get_swu_db()
    query = {}
    
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

    cards = list(db.cards.find(query, {
        "_id": 0,
        "slug": 1,
        "title": 1,
        "subtitle": 1,
        "card_number": 1,
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
        "art_front": 1,
        "art_back": 1,
        "text": 1
    }).sort([("expansion.code", 1), ("card_number", 1)]).limit(300))

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

    return templates.TemplateResponse(
        request=request,
        name="swu/home.html",
        context={
            "cards": cards,
            "total_count": db.cards.count_documents(query),
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
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Prev and Next card navigation
    current_num = card.get("card_number") or 0
    current_exp = card.get("expansion", {}).get("code")
    
    prev_card = db.cards.find_one({
        "expansion.code": current_exp,
        "card_number": {"$lt": current_num}
    }, {"_id": 0, "slug": 1, "title": 1, "card_number": 1}, sort=[("card_number", -1)])
    
    next_card = db.cards.find_one({
        "expansion.code": current_exp,
        "card_number": {"$gt": current_num}
    }, {"_id": 0, "slug": 1, "title": 1, "card_number": 1}, sort=[("card_number", 1)])

    # Similar/synergy cards: same traits or aspects in same set
    traits = card.get("traits", [])
    aspects = card.get("aspects", [])
    synergy_query = {
        "slug": {"$ne": card.get("slug")},
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
            "_id": 0, "slug": 1, "title": 1, "subtitle": 1, "art_front": 1, "type": 1, "cost": 1
        }).limit(6))

    return templates.TemplateResponse(
        request=request,
        name="swu/card.html",
        context={
            "card": card,
            "base_path": get_base_prefix(request),
            "prev_card": prev_card,
            "next_card": next_card,
            "synergy_cards": synergy_cards
        }
    )

@swu_router.get("/llms.txt", response_class=PlainTextResponse)
async def swu_llms_txt(request: Request):
    content = """# AvaScry Star Wars: Unlimited (SWU)
> Comprehensive canonical card database, aspect interactions, and rules engine for Star Wars: Unlimited.

## LLM Retrieval Guidelines
- Base URL: https://swu.avascry.com
- Machine readable format for any card: https://swu.avascry.com/card/{slug}.md
- Machine JSON format for any card: https://swu.avascry.com/card/{slug}.json
- Full XML Sitemap: https://swu.avascry.com/sitemap.xml

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
    return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")

@swu_router.get("/sitemap.xml", response_class=Response)
async def swu_sitemap_xml():
    db = get_swu_db()
    cards = list(db.cards.find({}, {"slug": 1, "_id": 0}))
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '  <url><loc>https://swu.avascry.com/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
        '  <url><loc>https://swu.avascry.com/about</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>',
        '  <url><loc>https://swu.avascry.com/privacy</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        '  <url><loc>https://swu.avascry.com/terms</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        '  <url><loc>https://swu.avascry.com/contact</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>'
    ]
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
