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

@dominion_router.get("", response_class=HTMLResponse)
@dominion_router.get("/", response_class=HTMLResponse)
async def dominion_home(request: Request):
    db = get_dominion_db()
    cards = list(db.cards.find({}, {"_id": 0, "name": 1, "slug": 1, "card_kinds": 1, "is_kingdom_card": 1}).sort("normalized_name", 1))
    total_cards = len(cards)
    total_expansions = db.expansions.count_documents({})
    
    return templates.TemplateResponse(
        request=request,
        name="dominion/home.html",
        context={
            "cards": cards,
            "total_cards": total_cards,
            "total_expansions": total_expansions
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

@dominion_router.get("/sitemap.xml", response_class=Response)
async def dominion_sitemap_xml():
    """Automated XML sitemap for Dominion cards."""
    db = get_dominion_db()
    cards = list(db.cards.find({}, {"slug": 1}))
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '  <url><loc>https://dominion.avascry.com/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>',
        '  <url><loc>https://dominion.avascry.com/llms.txt</loc><changefreq>monthly</changefreq><priority>0.9</priority></url>',
        '  <url><loc>https://dominion.avascry.com/llms-full.txt</loc><changefreq>monthly</changefreq><priority>0.9</priority></url>'
    ]
    for c in cards:
        xml.append(f'  <url><loc>https://dominion.avascry.com/card/{c["slug"]}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>')
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

    return templates.TemplateResponse(
        request=request,
        name="dominion/card.html",
        context={
            "card": card,
            "versions": versions,
            "rulings": rulings
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

