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
            
        rulings = list(db.rulings.find({"$or": [{"card_id": f"card:{c.get('slug')}"}, {"card_id": c.get("_id")}]}))
        if rulings:
            lines.append("Official FAQ:")
            for r in rulings:
                lines.append(f"  * Q: {r.get('question')}")
                lines.append(f"    A: {r.get('answer')}")
        lines.append("")
        
    return PlainTextResponse(content="\n".join(lines), media_type="text/plain; charset=utf-8", headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"})

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
    return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8", headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"})

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
        headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"}
    )

@dominion_router.get("/sets.md", response_class=PlainTextResponse)
async def dominion_sets_md():
    """Manifest of all Dominion expansions, editions, and promo sets."""
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
    return PlainTextResponse(content="\n".join(lines), media_type="text/markdown; charset=utf-8", headers={"Content-Signal": "ai-train=yes, search=yes, ai-input=yes"})

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
    return PlainTextResponse(content=content, media_type="text/plain; charset=utf-8")
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
    
    return {
        "card": card,
        "image_url": base_img,
        "image_1e_url": f"https://dominion.avascry.com/images/{clean_slug}-1e.jpg",
        "versions": versions,
        "rulings": rulings
    }

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
            
    return "\n".join(md)

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
            "base_path": get_base_prefix(request)
        },
        headers={
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
    form = await request.form()
    honeypot = form.get("website_url", "").strip()
    # If honeypot filled, silently pretend success
    if honeypot:
        return templates.TemplateResponse(
            request=request,
            name="dominion/contact.html",
            context={"base_path": get_base_prefix(request), "success": True, "error": None}
        )

    name = str(form.get("name", "")).strip()
    contact_info = str(form.get("contact", "")).strip()
    category = str(form.get("category", "General Feedback")).strip()
    message = str(form.get("message", "")).strip()

    if not name or not contact_info or not message:
        return templates.TemplateResponse(
            request=request,
            name="dominion/contact.html",
            context={
                "base_path": get_base_prefix(request),
                "success": False,
                "error": "Please fill out all required fields before submitting."
            }
        )

    # Dispatch Discord notification via app.py helper
    try:
        from app import send_discord_notification
        fields = [
            {"name": "Sender", "value": name, "inline": True},
            {"name": "Contact", "value": contact_info, "inline": True},
            {"name": "Category", "value": category, "inline": False},
            {"name": "Message", "value": message[:1024], "inline": False}
        ]
        await send_discord_notification(
            title=f"📩 [Dominion Feedback] {category}",
            description=f"New inquiry received on **dominion.avascry.com** from **{name}**.",
            color=0xb45309,  # Dominion Amber / Copper
            fields=fields
        )
    except Exception as exc:
        print(f"[Dominion Contact Error] Failed to dispatch Discord notification: {exc}")

    return templates.TemplateResponse(
        request=request,
        name="dominion/contact.html",
        context={"base_path": get_base_prefix(request), "success": True, "error": None}
    )

