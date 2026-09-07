"""
Dominion Sub-Application Router for dominion.avascry.com.
Connects directly to MongoDB database 'avascry_dominion'.
Serves HTML, Markdown (.md), JSON, sitemaps, and llms.txt endpoints for bots and humans.
"""

import re
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from db_mongo import get_mongo_db

dominion_router = APIRouter(prefix="", tags=["Dominion"])
templates = Jinja2Templates(directory="templates")

def get_dominion_db():
    client = get_mongo_db().client
    return client["avascry_dominion"]

def get_base_prefix(request: Request) -> str:
    host = request.headers.get("host", "")
    from mtgabyss.network_router import extract_subdomain
    if extract_subdomain(host) == "dominion":
        return ""
    return "/dominion"

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
        tag = e.get("set_tag", "").lower()
        if tag and tag not in seen_tags:
            seen_tags.add(tag)
            clean_expansions.append({"set_tag": tag, "name": e.get("name")})
            
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

@dominion_router.get("/llms.txt", response_class=PlainTextResponse)
async def dominion_llms_txt(request: Request):
    """Navigational manifest for LLM search agents."""
    return (
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
    )

@dominion_router.get("/llms-full.txt", response_class=PlainTextResponse)
async def dominion_llms_full_txt():
    """Full plain-text game corpus for direct model ingestion."""
    db = get_dominion_db()
    cards = list(db.cards.find({}).sort("normalized_name", 1))
    lines = [
        "# AvaScry Dominion — Full Rules & Card Corpus",
        "Game: Dominion",
        "Source: Rio Grande Games / Official Dominion Rules",
        f"Total Cards: {len(cards)}\n"
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
            
        rulings = list(db.rulings.find({"card_id": c["_id"]}))
        if rulings:
            lines.append("Official FAQ:")
            for r in rulings:
                lines.append(f"  * Q: {r.get('question')}")
                lines.append(f"    A: {r.get('answer')}")
        lines.append("")
        
    return "\n".join(lines)

@dominion_router.get("/robots.txt", response_class=PlainTextResponse)
async def dominion_robots_txt():
    """Standard crawl directives for Dominion subdomain."""
    return (
        "User-agent: *\n"
        "Allow: /\n\n"
        "Sitemap: https://dominion.avascry.com/sitemap.xml\n"
    )

@dominion_router.get("/sitemap.xml", response_class=Response)
async def dominion_sitemap_xml():
    """Automated XML sitemap with Google Image extensions for Dominion cards."""
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
    return Response(content="\n".join(xml), media_type="application/xml")

@dominion_router.get("/card/{slug}.json")
async def dominion_card_json(slug: str):
    db = get_dominion_db()
    card = db.cards.find_one({"slug": slug}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    versions = list(db.card_versions.find({"card_id": f"card:{slug}"}, {"_id": 0}))
    rulings = list(db.rulings.find({"card_id": f"card:{slug}"}, {"_id": 0}))
    
    return {
        "card": card,
        "versions": versions,
        "rulings": rulings
    }

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
            md.append(f"- **Text**: {v.get('printed_rules_text', '')}\n")
            
    if rulings:
        md.append("## Official Rulings & Rules FAQ")
        for r in rulings:
            md.append(f"**{r.get('question', '')}**\n")
            md.append(f"{r.get('answer', '')}\n")
            
    return "\n".join(md)

@dominion_router.get("/card/{slug}", response_class=HTMLResponse)
async def dominion_card_html(request: Request, slug: str):
    db = get_dominion_db()
    card = db.cards.find_one({"slug": slug})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
        
    versions = list(db.card_versions.find({"card_id": f"card:{slug}"}))
    rulings = list(db.rulings.find({"card_id": f"card:{slug}"}))

    def _format_rules(text: str) -> str:
        if not text:
            return ""
        # Format coin token tags
        t = re.sub(r'(\d+)\s*<\*COIN\*>', r'+\1 Coin', text)
        t = t.replace("<*COIN*>", "Coin")
        # Format paragraph / line break tokens
        t = re.sub(r'(?:<n>\s*)+', '\n\n', t)
        return t.strip()

    for v in versions:
        v["printed_rules_text"] = _format_rules(v.get("printed_rules_text", ""))

    for r in rulings:
        r["answer"] = _format_rules(r.get("answer", ""))

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
            "v1_tag": v_1e.get("expansion_tag", "").title(),
            "v1_text": t1,
            "v1_cost": v_1e.get("cost", {}),
            "v2_edition": v_2e.get("edition", "2nd Edition"),
            "v2_tag": v_2e.get("expansion_tag", "").title(),
            "v2_text": t2,
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
            "base_path": get_base_prefix(request)
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

