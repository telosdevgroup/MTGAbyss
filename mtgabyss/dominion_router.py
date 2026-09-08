"""
Dominion Sub-Application Router for dominion.avascry.com.
Connects directly to MongoDB database 'avascry_dominion'.
Serves HTML, Markdown (.md), JSON, sitemaps, and llms.txt endpoints for bots and humans.
"""

import os
import re
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from db_mongo import get_mongo_db

dominion_router = APIRouter(prefix="", tags=["Dominion"])
templates = Jinja2Templates(directory="templates")

# In-memory TTL cache for expensive crawler manifests (1h TTL)
DOMINION_CACHE = {}

def get_cached(key: str, ttl_seconds: int = 3600):
    entry = DOMINION_CACHE.get(key)
    if entry and (time.time() - entry["time"] < ttl_seconds):
        return entry["data"]
    return None

def set_cached(key: str, data):
    DOMINION_CACHE[key] = {"data": data, "time": time.time()}

@dominion_router.get("/images/{rest_of_path:path}", include_in_schema=False)
async def dominion_serve_image(rest_of_path: str):
    """
    Serve Dominion card scans from local storage (public/images/dominion/...)
    with dynamic CDN fallback if the card is known in the database.
    """
    # Check public/images/dominion/
    file_path = os.path.join("public", "images", "dominion", rest_of_path)
    if os.path.isfile(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        media_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

    # Check fallback: public/images/ directly
    fallback_path = os.path.join("public", "images", rest_of_path)
    if os.path.isfile(fallback_path):
        ext = os.path.splitext(fallback_path)[1].lower()
        media_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return FileResponse(fallback_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

    # Check database for remote image_url to provide 307 CDN redirect fallback
    slug = os.path.splitext(rest_of_path)[0]
    db = get_dominion_db()
    card = db.cards.find_one({"slug": slug}, {"image_url": 1, "image_1e_url": 1})
    if card:
        target_url = card.get("image_url")
        if slug.endswith("-1e") and card.get("image_1e_url"):
            target_url = card.get("image_1e_url")
        if target_url:
            return RedirectResponse(target_url, status_code=307)

    raise HTTPException(status_code=404, detail="Dominion image not found")

def get_dominion_db():
    client = get_mongo_db().client
    return client["avascry_dominion"]

def get_base_prefix(request: Request) -> str:
    host = request.headers.get("host", "")
    from mtgabyss.network_router import extract_subdomain
    if extract_subdomain(host) == "dominion":
        return ""
    return "/dominion"

def format_expansion_name(tag: str, raw_name: str = None, exp_map: dict = None) -> str:
    if not tag:
        return ""
    name = raw_name or (exp_map.get(tag.lower()) if exp_map else "")
    if name and not name.startswith('*') and (' ' in name or name.istitle()) and not any(p in name.lower() for p in ['removed', 'bigbox']):
        return name
    s = re.sub(r'([a-z])([A-Z0-9])', r'\1 \2', tag)
    s = re.sub(r'([0-9])([A-Z])', r'\1 \2', s)
    s = re.sub(r'\b1St\b', '1st', s.title())
    s = re.sub(r'\b2Nd\b', '2nd', s)
    s = s.replace('And', '&').replace('Bigbox', 'Big Box').replace('De', 'DE')
    return s

@dominion_router.get("", response_class=HTMLResponse)
@dominion_router.get("/", response_class=HTMLResponse)
async def dominion_home(request: Request):
    db = get_dominion_db()
    cards = list(db.cards.find({}, {"_id": 0, "name": 1, "slug": 1, "card_kinds": 1, "is_kingdom_card": 1}).sort("normalized_name", 1))
    
    # Enrich cards with version data (cost, expansion tags, rules snippet)
    versions = list(db.card_versions.find({}, {"_id": 0, "card_id": 1, "cost": 1, "expansion_tag": 1, "printed_rules_text": 1}))
    versions_by_card = {}
    for v in versions:
        cid = v.get("card_id")
        if cid:
            versions_by_card.setdefault(cid, []).append(v)
            
    for c in cards:
        cvs = versions_by_card.get(f"card:{c['slug']}", [])
        c["expansions"] = list(dict.fromkeys([v.get("expansion_tag", "").lower() for v in cvs if v.get("expansion_tag")]))
        cost = cvs[0].get("cost", {}) if cvs else {}
        c["cost"] = cost
        c["rules_text"] = " ".join([v.get("printed_rules_text", "") for v in cvs if v.get("printed_rules_text")])
        
    expansions = list(db.expansions.find({}, {"_id": 0, "set_tag": 1, "name": 1}).sort("name", 1))
    seen_tags = set()
    clean_expansions = []
    for e in expansions:
        orig_tag = e.get("set_tag", "")
        tag = orig_tag.lower()
        if tag and tag not in seen_tags:
            seen_tags.add(tag)
            clean_name = format_expansion_name(orig_tag, e.get("name"))
            clean_expansions.append({"set_tag": tag, "name": clean_name})
            
    clean_expansions.sort(key=lambda x: x["name"])
    total_cards = len(cards)
    total_expansions = len(clean_expansions)
    
    return templates.TemplateResponse(
        request=request,
        name="dominion/home.html",
        context={
            "cards": cards,
            "total_cards": total_cards,
            "total_expansions": total_expansions,
            "expansions": clean_expansions,
            "base_path": get_base_prefix(request)
        }
    )

@dominion_router.get("/kingdom-generator", response_class=HTMLResponse)
async def dominion_kingdom_generator(request: Request,
                                     cards: Optional[str] = None,
                                     sets: Optional[str] = None):
    """
    Dedicated 10-Kingdom Generator for Dominion.
    Supports pre-seeding via `?cards=slug1,slug2,...` and set filtering via `?sets=base,prosperity,...`.
    """
    db = get_dominion_db()
    all_cards = list(db.cards.find({}, {"_id": 0, "name": 1, "slug": 1, "card_kinds": 1, "is_kingdom_card": 1}).sort("normalized_name", 1))

    # Enrich cards with version cost & expansion data
    versions = list(db.card_versions.find({}, {"_id": 0, "card_id": 1, "cost": 1, "expansion_tag": 1, "printed_rules_text": 1}))
    versions_by_card = {}
    for v in versions:
        cid = v.get("card_id")
        if cid:
            versions_by_card.setdefault(cid, []).append(v)

    for c in all_cards:
        cvs = versions_by_card.get(f"card:{c['slug']}", [])
        c["expansions"] = list(dict.fromkeys([v.get("expansion_tag", "").lower() for v in cvs if v.get("expansion_tag")]))
        cost = cvs[0].get("cost", {}) if cvs else {}
        c["cost"] = cost
        c["rules_text"] = " ".join([v.get("printed_rules_text", "") for v in cvs if v.get("printed_rules_text")])

    expansions = list(db.expansions.find({}, {"_id": 0, "set_tag": 1, "name": 1}).sort("name", 1))
    seen_tags = set()
    clean_expansions = []
    for e in expansions:
        orig_tag = e.get("set_tag", "")
        tag = orig_tag.lower()
        if tag and tag not in seen_tags:
            seen_tags.add(tag)
            clean_name = format_expansion_name(orig_tag, e.get("name"))
            clean_expansions.append({"set_tag": tag, "name": clean_name})
    clean_expansions.sort(key=lambda x: x["name"])

    # Parse initial cards from query parameter if provided
    initial_slugs = [s.strip().lower() for s in cards.split(",")] if cards else []
    initial_sets = [s.strip().lower() for s in sets.split(",")] if sets else []

    return templates.TemplateResponse(
        request=request,
        name="dominion/kingdom_generator.html",
        context={
            "cards": all_cards,
            "expansions": clean_expansions,
            "initial_slugs": initial_slugs,
            "initial_sets": initial_sets,
            "base_path": get_base_prefix(request)
        }
    )

@dominion_router.get("/llms.txt", response_class=PlainTextResponse)
async def dominion_llms_txt(request: Request):
    """Navigational manifest for LLM search agents."""
    return PlainTextResponse(
        content=(
            "# AvaScry Dominion\n\n"
            "> Structured Dominion card, expansion, edition, and official rules data.\n\n"
            "## Start here\n"
            "- [All Cards](https://dominion.avascry.com/)\n"
            "- [Card Sitemap](https://dominion.avascry.com/sitemap.xml)\n"
            "- [Full Corpus](https://dominion.avascry.com/llms-full.txt)\n\n"
            "## Endpoints\n"
            "- HTML: https://dominion.avascry.com/card/{slug}\n"
            "- Markdown: https://dominion.avascry.com/card/{slug}.md\n"
            "- JSON: https://dominion.avascry.com/card/{slug}.json\n"
            "- Vector Embedding (4096-dim): https://dominion.avascry.com/vector/{slug}.json\n"
            "- Master HTML Sitemap: https://dominion.avascry.com/sitemap.html\n"
            "- Master Markdown Sitemap: https://dominion.avascry.com/sitemap.md\n\n"
            "## Unified Discord Identity & Network SSO\n"
            "- Part of the unified AvaScry Card Network (MTG, SWU, Dominion, Necromunda).\n"
            "- Single Discord OAuth sign-in shared network-wide across dominion.avascry.com and all sister domains.\n"
            "- Built for tabletop Discord groups with saved Kingdom presets and 1-click sharing.\n"
        ),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@dominion_router.get("/llms-full.txt", response_class=PlainTextResponse)
async def dominion_llms_full_txt():
    """Full plain-text game corpus for direct model ingestion with 1h in-memory caching."""
    cached = get_cached("dominion_llms_full_txt", ttl_seconds=3600)
    if cached:
        return PlainTextResponse(
            content=cached,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes",
                "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"
            }
        )

    db = get_dominion_db()
    cards = list(db.cards.find({}).sort("normalized_name", 1))
    lines = [
        "# AvaScry Dominion — Full Rules & Card Corpus",
        "Game: Dominion",
        "Source: Rio Grande Games / Official Dominion Rules",
        f"Total Cards: {len(cards)}\n",
        "## Authentication & Discord Integration Architecture",
        "- Network SSO: Single Discord authentication session operates network-wide across avascry.com, swu.avascry.com, dominion.avascry.com, and necromunda.avascry.com.",
        "- Zero-Password Tabletop Identity: User profile and kingdom generator bookmarks synchronize via Discord without email or password management.",
        "- Discord Bot Ready: Structured card markdown and JSON payloads are optimized for Discord bot integrations and community card lookups.\n",
    ]
    
    for c in cards:
        lines.append(f"## {c['name']}")
        lines.append(f"URL: https://dominion.avascry.com/card/{c['slug']}")
        lines.append(f"Types: {', '.join(c.get('card_kinds', []))}")
        lines.append(f"Kingdom Card: {'Yes' if c.get('is_kingdom_card') else 'No'}")
        
        versions = list(db.card_versions.find({"card_id": c["_id"]}))
        for v in versions:
            cost = v.get("cost", {})
            lines.append(f"- Edition: {v.get('expansion_tag')} ({v.get('edition')}) | Cost: {cost.get('coins', 0)} Coins | Rules: {v.get('printed_rules_text', '')}")
            
        rulings = list(db.rulings.find({"$or": [{"card_id": f"card:{c.get('slug')}"}, {"card_id": c.get("_id")}]}))
        if rulings:
            lines.append("Official FAQ:")
            for r in rulings:
                lines.append(f"  * Q: {r.get('question')}")
                lines.append(f"    A: {r.get('answer')}")
        lines.append("")
        
    full_text = "\n".join(lines)
    set_cached("dominion_llms_full_txt", full_text)
    return PlainTextResponse(
        content=full_text,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes",
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"
        }
    )

@dominion_router.get("/rules.md", response_class=PlainTextResponse)
async def dominion_rules_md():
    """Canonical Markdown rules overview of Dominion turn structure and card interaction rules."""
    content = """# Dominion Complete Rules & Mechanics Architecture
> Authoritative rules reference for Dominion (Rio Grande Games / Donald X. Vaccarino).

## 1. Game Flow & Turn Phases
Dominion is played in three sequential turn phases (the **ABC** phases):
1. **A — Action Phase**:
   - The active player may play one Action card from their hand.
   - Playing an Action may grant additional Actions (+Actions), additional Buys (+Buys), additional Coins (+Coins), or additional cards (+Cards).
   - If a player has multiple Actions remaining, they may play additional Action cards until all Action points are exhausted or they choose to stop.
2. **B — Buy Phase**:
   - The player may play any number of Treasure cards from their hand in any order.
   - The player then uses their accumulated Coins to purchase cards from the Supply. By default, a player has 1 Buy. Additional Buys allow purchasing multiple cards from the Supply provided sufficient Coins.
   - Purchased cards are placed directly into the player's Discard pile unless otherwise specified (e.g. Nomad Camp, Tracker).
3. **C — Clean-up Phase**:
   - All cards in play (Actions and Treasures played this turn) and all remaining cards in hand are placed face up into the player's Discard pile.
   - The player draws 5 new cards from their Deck to form their next hand.
   - If the player's Deck runs out of cards during a draw, they shuffle their Discard pile to form a fresh Deck.

## 2. Card Classes & Types
- **Action**: Cards played during the Action phase that provide instructions and resources.
- **Treasure**: Currency cards played during the Buy phase to generate purchasing power (Copper, Silver, Gold, Platinum).
- **Victory**: Score cards that provide Victory Points (VP) at the end of the game (Estate, Duchy, Province, Colony, Curse).
- **Reaction**: Cards that can be revealed or played in response to specific game events (e.g., Moat, Sheepdog, Falconer).
- **Duration**: Orange cards that remain in play across multiple turns to provide delayed or recurring effects (introduced in *Seaside*).
- **Attack**: Hostile Action cards that impair opponents (discarding, trashing, cursing).

## 3. Game End Conditions
The game ends immediately after any player's turn when either:
1. The **Province** supply pile is empty (or Colony pile in games using Platinum/Colony).
2. Any **three Supply piles** are empty (four piles in games with 5-6 players).

The player with the highest total Victory Points across their entire deck wins.
"""
    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes",
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"
        }
    )

@dominion_router.get("/rules.json", response_class=JSONResponse)
async def dominion_rules_json():
    """Structured JSON rules architecture for programmatic engines."""
    return JSONResponse(
        content={
            "game": "Dominion",
            "publisher": "Rio Grande Games",
            "designer": "Donald X. Vaccarino",
            "turn_structure": [
                {"phase": "Action", "description": "Play 1 Action card by default. Chain +Actions."},
                {"phase": "Buy", "description": "Play Treasures, spend accumulated Coins with available Buys."},
                {"phase": "Clean-up", "description": "Discard cards in play and hand, draw 5 cards."}
            ],
            "card_types": ["Action", "Treasure", "Victory", "Reaction", "Duration", "Attack", "Curse"],
            "end_conditions": [
                "Province (or Colony) pile empty",
                "Any 3 supply piles empty (4 piles in 5-6 player games)"
            ]
        },
        headers={
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes",
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"
        }
    )

@dominion_router.get("/sets.md", response_class=PlainTextResponse)
async def dominion_sets_md():
    """Manifest of all Dominion expansions, editions, and promo sets with 1h in-memory caching."""
    cached = get_cached("dominion_sets_md", ttl_seconds=3600)
    if cached:
        return PlainTextResponse(
            content=cached,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes",
                "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"
            }
        )

    db = get_dominion_db()
    expansions = list(db.expansions.find({}).sort("year", 1))
    lines = [
        "# Dominion Expansions & Manifest",
        "Author: Donald X. Vaccarino | Publisher: Rio Grande Games\n",
        "| Expansion | Code | Year | Status |",
        "| :--- | :--- | :--- | :--- |"
    ]
    for e in expansions:
        name = e.get("name") or e.get("set_tag")
        code = e.get("set_tag", "").upper()
        year = e.get("year", "—")
        status = "2nd Edition Available" if "2e" in code.lower() or "second" in name.lower() else "Active"
        lines.append(f"| {name} | {code} | {year} | {status} |")
    content = "\n".join(lines)
    set_cached("dominion_sets_md", content)
    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes",
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"
        }
    )

@dominion_router.get("/.well-known/ai-content", response_class=PlainTextResponse)
async def dominion_well_known_ai():
    content = """# AI Content Declaration & Scraping Permission
domain: dominion.avascry.com
operator: AvaScry Card Network
ai-train: allowed
ai-search: allowed
machine-endpoints:
  - https://dominion.avascry.com/llms.txt
  - https://dominion.avascry.com/llms-full.txt
  - https://dominion.avascry.com/rules.md
  - https://dominion.avascry.com/rules.json
  - https://dominion.avascry.com/sets.md
  - https://dominion.avascry.com/sitemap.xml
format-negotiation:
  - Header: "Accept: text/markdown" -> /card/{slug}.md
  - Header: "Accept: application/json" -> /card/{slug}.json
"""
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"}
    )

@dominion_router.get("/robots.txt", response_class=PlainTextResponse)
@dominion_router.head("/robots.txt")
async def dominion_robots_txt():
    """Standard crawl directives for Dominion subdomain."""
    return PlainTextResponse(
        "User-agent: *\n"
        "Allow: /\n\n"
        "Sitemap: https://dominion.avascry.com/sitemap.xml\n"
        "Sitemap: https://dominion.avascry.com/sitemap.html\n",
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"}
    )

@dominion_router.get("/sitemap.xml", response_class=Response)
async def dominion_sitemap_xml():
    """Automated XML sitemap with Google Image extensions for Dominion cards (cached 24h)."""
    cached = get_cached("dominion_sitemap_xml", ttl_seconds=86400)
    if cached:
        return Response(content=cached, media_type="application/xml", headers={"Cache-Control": "public, max-age=86400"})

    import datetime
    today = datetime.date.today().isoformat()
    db = get_dominion_db()
    cards = list(db.cards.find({}, {"slug": 1, "name": 1}))
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        f'  <url><loc>https://dominion.avascry.com/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>',
        f'  <url><loc>https://dominion.avascry.com/llms.txt</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://dominion.avascry.com/llms-full.txt</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>'
    ]
    for c in cards:
        slug = c.get("slug", "")
        name = c.get("name", slug).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        xml.append(
            f'  <url>\n'
            f'    <loc>https://dominion.avascry.com/card/{slug}</loc>\n'
            f'    <lastmod>{today}</lastmod>\n'
            f'    <changefreq>monthly</changefreq>\n'
            f'    <priority>0.8</priority>\n'
            f'    <image:image>\n'
            f'      <image:loc>https://dominion.avascry.com/images/{slug}.jpg</image:loc>\n'
            f'      <image:title>{name} Dominion Card</image:title>\n'
            f'    </image:image>\n'
            f'  </url>'
        )
    xml.append('</urlset>')
    sitemap_content = "\n".join(xml)
    set_cached("dominion_sitemap_xml", sitemap_content)
    return Response(content=sitemap_content, media_type="application/xml", headers={"Cache-Control": "public, max-age=86400"})

@dominion_router.get("/sitemap.html", response_class=HTMLResponse)
async def dominion_sitemap_html(request: Request):
    """
    Complete HTML Directory & Visual Sitemap for Dominion.
    Organizes all 819 cards alphabetically, by expansion, and by landscape types,
    with tri-surface links (.html, .md, .json) and fast jump navigation.
    """
    db = get_dominion_db()
    all_cards = list(db.cards.find({}, {"_id": 0}).sort("name", 1))

    # Version cost map
    versions = list(db.card_versions.find({}, {"_id": 0, "card_id": 1, "cost": 1, "expansion_tag": 1}))
    versions_by_card = {}
    for v in versions:
        cid = v.get("card_id")
        if cid:
            versions_by_card.setdefault(cid, []).append(v)

    expansions = list(db.expansions.find({}, {"_id": 0, "set_tag": 1, "name": 1}))
    exp_name_map = {e.get("set_tag", "").lower(): e.get("name") for e in expansions if e.get("set_tag")}

    # Enrich cards
    for c in all_cards:
        slug = c.get("slug")
        cvs = versions_by_card.get(f"card:{slug}", [])
        c["cost"] = cvs[0].get("cost", {}) if cvs else {}
        c["expansions"] = list(dict.fromkeys([v.get("expansion_tag", "").lower() for v in cvs if v.get("expansion_tag")]))

    # Group alphabetically
    letters_dict = {}
    for c in all_cards:
        first = (c.get("name", "")[:1].upper()) or "#"
        if not first.isalpha():
            first = "#"
        letters_dict.setdefault(first, []).append(c)

    sorted_letters = sorted(letters_dict.keys(), key=lambda x: (x == "#", x))
    cards_by_letter = [{"letter": let, "cards": letters_dict[let]} for let in sorted_letters]

    # Group by expansion
    sets_dict = {}
    for c in all_cards:
        for exp in c.get("expansions", []):
            exp_clean = exp_name_map.get(exp) or format_expansion_name(exp)
            sets_dict.setdefault(exp_clean, []).append(c)
    cards_by_set = sorted([{"set_name": k, "cards": v} for k, v in sets_dict.items()], key=lambda x: x["set_name"])

    # Landscapes & Non-Supply
    landscapes = [c for c in all_cards if any(k in ["event", "landmark", "project", "way", "ally", "trait"] for k in [x.lower() for x in c.get("card_kinds", [])])]

    return templates.TemplateResponse(
        request=request,
        name="dominion/sitemap.html",
        context={
            "cards_by_letter": cards_by_letter,
            "cards_by_set": cards_by_set,
            "landscapes": landscapes,
            "letters": sorted_letters,
            "total_cards": len(all_cards),
            "total_sets": len(cards_by_set),
            "base_path": get_base_prefix(request)
        },
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@dominion_router.get("/sitemap.md", response_class=PlainTextResponse)
async def dominion_sitemap_markdown():
    """Structured Markdown Sitemap & Index for bots, LLMs, and crawlers."""
    cached = get_cached("dominion_sitemap_md", ttl_seconds=86400)
    if cached:
        return PlainTextResponse(
            content=cached,
            media_type="text/markdown; charset=utf-8",
            headers={"Cache-Control": "public, max-age=86400"}
        )

    db = get_dominion_db()
    all_cards = list(db.cards.find({}, {"_id": 0, "name": 1, "slug": 1, "card_kinds": 1, "is_kingdom_card": 1}).sort("name", 1))

    md = [
        "# AvaScry Dominion — Markdown Directory & Sitemap Index",
        "Canonical index of all Dominion cards, official Donald X. Vaccarino rulings, and API endpoints.\n",
        "## Machine Endpoints",
        "- Human HTML Directory: https://dominion.avascry.com/sitemap.html",
        "- Markdown Sitemap: https://dominion.avascry.com/sitemap.md",
        "- XML Image Sitemap: https://dominion.avascry.com/sitemap.xml",
        "- LLM Context Manifest: https://dominion.avascry.com/llms.txt",
        "- Full Corpus Export: https://dominion.avascry.com/llms-full.txt",
        "- Rules Architecture: https://dominion.avascry.com/rules.md",
        "- Expansions Manifest: https://dominion.avascry.com/sets.md",
        "- Kingdom Generator: https://dominion.avascry.com/kingdom-generator\n",
        f"## Complete Card Catalog ({len(all_cards)} Cards)",
        "| Card | Types | Kingdom | HTML | Markdown | JSON | Vector |",
        "|---|---|:---:|:---:|:---:|:---:|:---:|"
    ]

    for c in all_cards:
        slug = c.get("slug")
        name = c.get("name")
        kinds = ", ".join(c.get("card_kinds", []))
        is_kg = "Yes" if c.get("is_kingdom_card") else "No"
        md.append(f"| [{name}](https://dominion.avascry.com/card/{slug}) | {kinds} | {is_kg} | [HTML](https://dominion.avascry.com/card/{slug}) | [MD](https://dominion.avascry.com/card/{slug}.md) | [JSON](https://dominion.avascry.com/card/{slug}.json) | [Vector](https://dominion.avascry.com/vector/{slug}.json) |")

    content = "\n".join(md)
    set_cached("dominion_sitemap_md", content)
    return PlainTextResponse(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400"}
    )

@dominion_router.get("/random")
async def dominion_random_card(request: Request):
    db = get_dominion_db()
    pipeline = [
        {"$sample": {"size": 1}},
        {"$project": {"slug": 1, "_id": 0}}
    ]
    sample = list(db.cards.aggregate(pipeline))
    if not sample:
        raise HTTPException(status_code=404, detail="No Dominion cards found")
    slug = sample[0]["slug"]
    base_path = get_base_prefix(request)
    return RedirectResponse(url=f"{base_path}/card/{slug}", status_code=307, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@dominion_router.get("/vector/{identifier}", include_in_schema=False)
@dominion_router.get("/vector/{identifier}.json", include_in_schema=False)
@dominion_router.head("/vector/{identifier}", include_in_schema=False)
@dominion_router.head("/vector/{identifier}.json", include_in_schema=False)
async def dominion_vector_embedding(identifier: str):
    """Expose raw 4096-dimensional Qwen 8B vector embedding for a Dominion card."""
    clean_id = identifier.lower().replace(".json", "").strip()
    if not clean_id or clean_id in ("", ".", "..", ".md", ".json"):
        raise HTTPException(status_code=404, detail="Vector embedding not found")

    db = get_dominion_db()
    doc = db.embeddings_dominion.find_one({"slug": clean_id})
    if not doc:
        doc = db.embeddings_dominion.find_one({"name": {"$regex": f"^{re.escape(clean_id.replace('-', ' '))}$", "$options": "i"}})
    if not doc:
        card_doc = db.cards.find_one({"slug": clean_id})
        if card_doc:
            doc = db.embeddings_dominion.find_one({"slug": card_doc.get("slug")})

    if not doc:
        raise HTTPException(status_code=404, detail="Vector embedding not found")

    slug = doc.get("slug") or clean_id
    name = doc.get("name") or clean_id.replace('-', ' ').title()
    embedding = doc.get("embedding", [])

    return JSONResponse(
        content={
            "name": name,
            "slug": slug,
            "model": doc.get("model") or "qwen3-embedding:8b",
            "dimensions": len(embedding) or 4096,
            "version": "1.0",
            "card_kinds": doc.get("card_kinds", []),
            "context_text": doc.get("context_text", ""),
            "links": {
                "vector": f"https://dominion.avascry.com/vector/{slug}.json",
                "html": f"https://dominion.avascry.com/card/{slug}",
                "markdown": f"https://dominion.avascry.com/card/{slug}.md",
                "json": f"https://dominion.avascry.com/card/{slug}.json"
            },
            "embedding": embedding
        },
        headers={
            "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
            "Access-Control-Allow-Origin": "*",
            "Link": f'</card/{slug}.json>; rel="alternate"; type="application/json", </card/{slug}>; rel="up"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@dominion_router.get("/card/{slug}.json")
async def dominion_card_json(slug: str):
    clean_slug = slug.lower().strip()
    db = get_dominion_db()
    card = db.cards.find_one({"slug": clean_slug}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Canonical absolute image URLs
    base_img = f"https://dominion.avascry.com/images/{clean_slug}.jpg"
    card["image_url"] = base_img

    versions = list(db.card_versions.find({"card_id": f"card:{clean_slug}"}, {"_id": 0}))
    for v in versions:
        ed = str(v.get("edition", "")).lower()
        stag = str(v.get("expansion_tag", "")).lower()
        if "1e" in ed or "1st" in stag:
            v["image_url"] = f"https://dominion.avascry.com/images/{clean_slug}-1e.jpg"
        else:
            v["image_url"] = base_img

    rulings = list(db.rulings.find({"card_id": f"card:{clean_slug}"}, {"_id": 0}))
    related_cards = card.get("related_cards", [])
    
    return JSONResponse(
        content={
            "card": card,
            "image_url": base_img,
            "image_1e_url": f"https://dominion.avascry.com/images/{clean_slug}-1e.jpg",
            "versions": versions,
            "rulings": rulings,
            "related_cards": related_cards,
            "links": {
                "vector": f"https://dominion.avascry.com/vector/{clean_slug}.json",
                "markdown": f"https://dominion.avascry.com/card/{clean_slug}.md",
                "html": f"https://dominion.avascry.com/card/{clean_slug}"
            }
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Link": f'</vector/{clean_slug}.json>; rel="alternate"; type="application/json", </card/{clean_slug}.md>; rel="alternate"; type="text/markdown"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

def format_dominion_rules_html(text: str) -> str:
    if not text:
        return ""
    # Coin tokens: '1 <*COIN*>' or '<*COIN*>'
    t = re.sub(r'(\d+)\s*<\*COIN\*>', r'+\1 Coin', text)
    t = t.replace("<*COIN*>", "Coin")
    t = t.replace("<*POTION*>", "Potion")
    t = re.sub(r'<\*?VP\*?>', 'VP', t)
    # Dominion line divider (<line> is the below-the-line divider on cards)
    t = re.sub(r'<line\s*/?>', '<hr class="dominion-divider">', t)
    # Line and paragraph breaks: normalize <n> to <br><br>
    t = re.sub(r'(?:<n>\s*)+', '<br><br>', t)
    # Alignment tags
    t = t.replace("<center>", '<div style="text-align: center;">').replace("</center>", "</div>")
    t = t.replace("<left>", '<div style="text-align: left;">').replace("</left>", "</div>")
    return t.strip()

def format_dominion_rules_plain(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'(\d+)\s*<\*COIN\*>', r'+\1 Coin', text)
    t = t.replace("<*COIN*>", "Coin")
    t = t.replace("<*POTION*>", "Potion")
    t = re.sub(r'<\*?VP\*?>', 'VP', t)
    t = re.sub(r'<line\s*/?>', '\n---\n', t)
    t = re.sub(r'(?:<br\s*/?>|<n>\s*)+', '\n', t)
    t = re.sub(r'</?(?:center|left|b|i|u)>', '', t)
    return t.strip()

@dominion_router.get("/card/{slug}.md", response_class=PlainTextResponse)
async def dominion_card_markdown(slug: str):
    db = get_dominion_db()
    card = db.cards.find_one({"slug": slug})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    versions = list(db.card_versions.find({"card_id": f"card:{slug}"}))
    rulings = list(db.rulings.find({"card_id": f"card:{slug}"}))
    
    md = [
        f"# {card['name']}",
        f"**Types**: {', '.join(card.get('card_kinds', []))}",
        f"**Kingdom Card**: {'Yes' if card.get('is_kingdom_card') else 'No'}\n"
    ]
    
    if versions:
        md.append("## Versions & Costs")
        for v in versions:
            cost = v.get("cost", {})
            cost_str = f"{cost.get('coins', 0)} Coins"
            if cost.get("debt"):
                cost_str += f", {cost['debt']} Debt"
            if cost.get("potion"):
                cost_str += ", 1 Potion"
            md.append(f"### {v.get('expansion_tag', 'Base')} ({v.get('edition', 'standard')})")
            md.append(f"- **Cost**: {cost_str}")
            clean_text = format_dominion_rules_plain(v.get('printed_rules_text', ''))
            md.append(f"- **Text**: {clean_text}\n")
            
    if rulings:
        md.append("## Official Rulings & Rules FAQ")
        for r in rulings:
            md.append(f"**{r.get('question', '')}**\n")
            clean_ans = format_dominion_rules_plain(r.get('answer', ''))
            md.append(f"{clean_ans}\n")
            
    related_cards = card.get("related_cards", [])
    if related_cards:
        md.append("## Synergistic & Related Cards (Top 11)")
        md.append("Calculated via 4096-dimensional neural vector embeddings (`qwen3-embedding:8b`). Pairings & comparisons:")
        for idx, r in enumerate(related_cards, 1):
            cost_coins = r.get('cost', {}).get('coins', 0) if isinstance(r.get('cost'), dict) else 0
            cost_info = f"${cost_coins}" if cost_coins else "$0"
            types_str = ", ".join(r.get("card_kinds", []))
            sim_score = r.get('score', r.get('similarity', 0))
            md.append(f"{idx}. [{r['name']}](https://dominion.avascry.com/card/{r['slug']}) ({cost_info} {types_str}) — Score: {sim_score:.4f} • [Vector](https://dominion.avascry.com/vector/{r['slug']}.json)")
        md.append("")
            
    return PlainTextResponse(
        "\n".join(md),
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

@dominion_router.get("/card/{slug}", response_class=HTMLResponse)
async def dominion_card_html(request: Request, slug: str):
    db = get_dominion_db()
    card = db.cards.find_one({"slug": slug})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
        
    versions = list(db.card_versions.find({"card_id": f"card:{slug}"}))
    rulings = list(db.rulings.find({"card_id": f"card:{slug}"}))

    exp_map = {e.get('set_tag', '').lower(): e.get('name') for e in db.expansions.find({}, {"set_tag": 1, "name": 1})}

    def _format_expansion(tag: str) -> str:
        return format_expansion_name(tag, exp_map=exp_map)

    for v in versions:
        raw_text = v.get("printed_rules_text", "")
        v["printed_rules_html"] = format_dominion_rules_html(raw_text)
        v["printed_rules_text"] = format_dominion_rules_plain(raw_text)
        v["expansion_name"] = _format_expansion(v.get("expansion_tag", ""))

    for r in rulings:
        raw_ans = r.get("answer", "")
        r["answer_html"] = format_dominion_rules_html(raw_ans)
        r["answer"] = format_dominion_rules_plain(raw_ans)

    # Alphabetical prev/next cards
    norm = card.get("normalized_name") or card.get("name", "").lower()
    prev_card = db.cards.find_one({"normalized_name": {"$lt": norm}}, {"_id": 0, "name": 1, "slug": 1}, sort=[("normalized_name", -1)])
    next_card = db.cards.find_one({"normalized_name": {"$gt": norm}}, {"_id": 0, "name": 1, "slug": 1}, sort=[("normalized_name", 1)])

    # Detect 1st vs 2nd edition diff
    v_1e = next((v for v in versions if "1" in str(v.get("edition", "")).lower() or "1e" in str(v.get("expansion_tag", "")).lower()), None)
    v_2e = next((v for v in versions if "2" in str(v.get("edition", "")).lower() or "2e" in str(v.get("expansion_tag", "")).lower()), None)
    edition_diff = None
    if v_1e and v_2e:
        t1 = v_1e.get("printed_rules_text", "").strip()
        t2 = v_2e.get("printed_rules_text", "").strip()
        edition_diff = {
            "v1_edition": v_1e.get("edition", "1st Edition"),
            "v1_tag": _format_expansion(v_1e.get("expansion_tag", "")),
            "v1_text": t1,
            "v1_html": v_1e.get("printed_rules_html", "").strip(),
            "v1_cost": v_1e.get("cost", {}),
            "v2_edition": v_2e.get("edition", "2nd Edition"),
            "v2_tag": _format_expansion(v_2e.get("expansion_tag", "")),
            "v2_text": t2,
            "v2_html": v_2e.get("printed_rules_html", "").strip(),
            "v2_cost": v_2e.get("cost", {}),
            "has_text_change": t1 != t2
        }

    # Extract mechanics and synergies
    all_text = " ".join([v.get("printed_rules_text", "") for v in versions]).lower()
    kinds = [k.lower() for k in card.get("card_kinds", [])]
    synergies = []
    if "trash" in all_text:
        synergies.append({"label": "Trashing", "query": "trash"})
    if "+2 action" in all_text or "+1 action" in all_text or "+3 action" in all_text or "+action" in all_text:
        synergies.append({"label": "Action Engine", "query": "action"})
    if "+1 buy" in all_text or "+2 buy" in all_text or "+buy" in all_text:
        synergies.append({"label": "+Buy", "query": "buy"})
    if "+1 card" in all_text or "+2 card" in all_text or "+3 card" in all_text or "+card" in all_text:
        synergies.append({"label": "Card Draw", "query": "card"})
    if "gain" in all_text:
        synergies.append({"label": "Gainer", "query": "gain"})
    if "attack" in kinds:
        synergies.append({"label": "Attack", "query": "attack"})
    if "reaction" in kinds:
        synergies.append({"label": "Reaction", "query": "reaction"})
    if "duration" in kinds:
        synergies.append({"label": "Duration", "query": "duration"})
    if "victory" in kinds:
        synergies.append({"label": "Victory", "query": "victory"})
    if "treasure" in kinds:
        synergies.append({"label": "Treasure", "query": "treasure"})

    return templates.TemplateResponse(
        request=request,
        name="dominion/card.html",
        context={
            "card": card,
            "versions": versions,
            "rulings": rulings,
            "prev_card": prev_card,
            "next_card": next_card,
            "edition_diff": edition_diff,
            "synergies": synergies,
            "related_cards": card.get("related_cards", []),
            "base_path": get_base_prefix(request)
        },
        headers={
            "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
            "Vary": "Accept",
            "Link": f'</card/{slug}.md>; rel="alternate"; type="text/markdown", </card/{slug}.json>; rel="alternate"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

import os
import asyncio
import httpx
from fastapi.responses import FileResponse, RedirectResponse

DOMINION_IMAGE_DIR = os.path.join("public", "images", "dominion")
os.makedirs(DOMINION_IMAGE_DIR, exist_ok=True)

async def _download_dominion_image(cdn_url: str, local_path: str):
    try:
        headers = {"User-Agent": "AvaScry/2.0"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(cdn_url, headers=headers, follow_redirects=True)
            if resp.status_code == 200 and resp.content:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
    except Exception as e:
        print(f"[Dominion Image Download Error] {e}")

@dominion_router.get("/images/{slug}.jpg", include_in_schema=False)
async def dominion_card_image(slug: str):
    """
    On-demand card image delivery:
    1. If exists locally on disk, serve immediately with 30-day immutable cache.
    2. If not on disk, lookup CDN url in avascry_dominion, start background download,
       and return 307 temporary redirect to hotlink immediately.
    """
    clean_slug = slug.lower().strip()
    local_file = os.path.join(DOMINION_IMAGE_DIR, f"{clean_slug}.jpg")
    
    if os.path.isfile(local_file):
        return FileResponse(
            local_file,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=2592000, immutable"}
        )
        
    db = get_dominion_db()
    card = db.cards.find_one({"slug": clean_slug}, {"image_url": 1})
    if card and card.get("image_url"):
        cdn_url = card["image_url"]
        # Trigger background download to local disk
        asyncio.create_task(_download_dominion_image(cdn_url, local_file))
        # Hotlink on first request
        return RedirectResponse(url=cdn_url, status_code=307)
        
    raise HTTPException(status_code=404, detail="Image not found")

@dominion_router.get("/about", response_class=HTMLResponse)
async def dominion_about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dominion/about.html",
        context={"base_path": get_base_prefix(request)}
    )

@dominion_router.get("/privacy", response_class=HTMLResponse)
async def dominion_privacy(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dominion/privacy.html",
        context={"base_path": get_base_prefix(request)}
    )

@dominion_router.get("/terms", response_class=HTMLResponse)
async def dominion_terms(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dominion/terms.html",
        context={"base_path": get_base_prefix(request)}
    )

@dominion_router.get("/contact", response_class=HTMLResponse)
async def dominion_contact(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dominion/contact.html",
        context={"base_path": get_base_prefix(request), "success": False, "error": None}
    )

@dominion_router.post("/contact", response_class=HTMLResponse)
async def dominion_contact_post(request: Request):
    from mtgabyss.shared.contact import process_contact_submission
    result = await process_contact_submission(
        request=request,
        subsite_name="AvaScry Dominion",
        subsite_color=0xb45309,
        extra_field_name="category",
        extra_field_label="Category"
    )
    return templates.TemplateResponse(
        request=request,
        name="dominion/contact.html",
        context={
            "base_path": get_base_prefix(request),
            "success": result["success"],
            "error": result["error"],
            "values": result.get("values", {})
        }
    )


