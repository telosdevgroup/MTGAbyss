import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from db_mongo import get_mongo_db
from mtgabyss.shared.helpers import slugify, safe_header_segment, resolve_card_images, templates

sets_router = APIRouter()

@sets_router.get("/sets", response_class=HTMLResponse)
async def sets_list(request: Request):
    db = get_mongo_db()
    sets_data = []
    try:
        pipeline = [
            {"$group": {"_id": "$set", "name": {"$first": "$set_name"}, "count": {"$sum": 1}}},
            {"$sort": {"name": 1}}
        ]
        for item in db["cards"].aggregate(pipeline):
            code = (item["_id"] or "").lower()
            if code:
                sets_data.append({
                    "code": code,
                    "name": item.get("name") or code.upper(),
                    "card_count": item.get("count", 0)
                })
    except Exception as e:
        print(f"Error loading sets: {e}")
        
    return templates.TemplateResponse(
        request=request,
        name="sets.html",
        context={
            "active_nav": "sets",
            "sets": sets_data
        }
    )

@sets_router.get("/set/{code}")
@sets_router.head("/set/{code}")
async def set_detail(request: Request, code: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    
    is_md = False
    is_json = False
    if code.lower().endswith(".md"):
        code = code[:-3]
        is_md = True
    elif code.lower().endswith(".json"):
        code = code[:-5]
        is_json = True

    set_code = code.lower()
    projection = {
        "name": 1, "set": 1, "set_name": 1, "collector_number": 1, "rarity": 1,
        "type_line": 1, "mana_cost": 1, "cmc": 1, "image_slug": 1, "image_uris": 1,
        "card_faces": 1, "raw": 1
    }
    cards_cursor = list(db["cards"].find({"set": set_code, "lang": "en"}, projection))
    if not cards_cursor:
        cards_cursor = list(db["cards"].find({"set": set_code}, projection).limit(300))

    if not cards_cursor:
        raise HTTPException(status_code=404, detail=f"Set '{set_code}' not found")

    cards = []
    set_name = set_code.upper()
    for doc in cards_cursor:
        set_name = doc.get("set_name") or set_name
        c_name = doc.get("name") or "Card"
        c_slug = slugify(c_name)
        c_num = str(doc.get("collector_number") or "")
        small_url, norm_url, large_url = resolve_card_images(doc, background_tasks)
        cards.append({
            "name": c_name,
            "set": set_code,
            "set_name": set_name,
            "printing_slug": f"{c_slug}-{set_code}" if set_code else c_slug,
            "collector_number": c_num,
            "rarity": (doc.get("rarity") or "").capitalize(),
            "type_line": doc.get("type_line") or "",
            "mana_cost": doc.get("mana_cost") or "",
            "cmc": float(doc.get("cmc") or 0.0),
            "image_slug": doc.get("image_slug") or c_slug,
            "image_url": norm_url,
            "large_image_url": large_url,
            "image_uris": {
                "small": small_url,
                "normal": norm_url,
                "large": large_url
            }
        })

    # Prefix-aware natural sort for collector numbers (e.g. 1, 2, 3... 281, then A-1, A-2)
    def natural_collector_sort(c):
        num_str = str(c.get("collector_number") or "999999")
        m = re.search(r'\d+', num_str)
        num_val = int(m.group()) if m else 999999
        is_promo_or_rebalance = 1 if num_str.startswith(("A-", "p", "s", "★")) else 0
        return (is_promo_or_rebalance, num_val, num_str)
        
    cards.sort(key=natural_collector_sort)

    # Content Negotiation for AI Agents (Accept: text/markdown, application/json, or ?format=)
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()

    if is_json or "application/json" in accept_header or requested_format == "json":
        formatted_set_cards = []
        for c in cards:
            c_slug = c.get("printing_slug") or slugify(c.get("name") or "card")
            c_norm = c.get("image_url") or (c.get("image_uris") and c["image_uris"].get("normal"))
            if c_norm and c_norm.startswith("/"):
                c_norm = f"https://avascry.com{c_norm}"
            c_large = c.get("large_image_url") or (c.get("image_uris") and c["image_uris"].get("large"))
            if c_large and c_large.startswith("/"):
                c_large = f"https://avascry.com{c_large}"
                
            formatted_set_cards.append({
                "name": c.get("name"),
                "printing_slug": c_slug,
                "collector_number": c.get("collector_number"),
                "rarity": c.get("rarity"),
                "type_line": c.get("type_line"),
                "mana_cost": c.get("mana_cost"),
                "cmc": float(c.get("cmc") or 0.0),
                "image_uris": {
                    "normal": c_norm,
                    "large": c_large
                },
                "links": {
                    "html": f"https://avascry.com/printing/{c_slug}",
                    "markdown": f"https://avascry.com/printing/{c_slug}.md",
                    "json": f"https://avascry.com/printing/{c_slug}.json"
                }
            })

        set_info = {
            "code": set_code,
            "name": set_name,
            "links": {
                "html": f"https://avascry.com/set/{set_code}",
                "markdown": f"https://avascry.com/set/{set_code}.md",
                "json": f"https://avascry.com/set/{set_code}.json"
            }
        }
        set_meta = db["sets"].find_one({"code": set_code}, {"blurb": 1, "commander_staples": 1})
        if set_meta:
            if set_meta.get("blurb"):
                set_info["blurb"] = set_meta["blurb"]
            if set_meta.get("commander_staples"):
                set_info["commander_staples"] = set_meta["commander_staples"]

        return JSONResponse(
            content={
                "set": set_info,
                "total_cards": len(formatted_set_cards),
                "cards": formatted_set_cards
            },
            headers={
                "Vary": "Accept",
                "Link": f'</set/{safe_header_segment(set_code)}.md>; rel="alternate"; type="text/markdown", </set/{safe_header_segment(set_code)}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_md or "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
        set_meta = db["sets"].find_one({"code": set_code}, {"blurb": 1})
        set_blurb = set_meta.get("blurb") if set_meta else None

        md_lines = [
            "---",
            f"set_name: \"{set_name}\"",
            f"set_code: \"{set_code.upper()}\"",
            f"total_cards: {len(cards)}",
            f"canonical_url: https://avascry.com/set/{set_code}",
            f"json_api: https://avascry.com/set/{set_code}.json",
            "---",
            f"\n# {set_name} ({set_code.upper()})\n",
            f"- **Set Code:** `{set_code.upper()}`",
            f"- **Total Printings:** {len(cards)}",
            f"- **JSON API:** https://avascry.com/set/{set_code}.json\n"
        ]
        if set_blurb:
            md_lines.append(f"{set_blurb}\n")

        md_lines.extend([
            "| # | Card Name | Type | Rarity | Mana Cost |",
            "|---|-----------|------|--------|-----------|"
        ])
        for c in cards:
            c_num = c.get("collector_number", "")
            c_name = c.get("name", "")
            c_type = c.get("type_line", "")
            c_rarity = (c.get("rarity") or "").capitalize()
            c_mana = c.get("mana_cost") or "-"
            md_lines.append(f"| {c_num} | [{c_name}](https://avascry.com/printing/{c.get('printing_slug')}) | {c_type} | {c_rarity} | `{c_mana}` |")

        md_text = "\n".join(md_lines)
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Vary": "Accept",
                "X-Markdown-Tokens": str(len(md_text.split())),
                "Link": f'</set/{safe_header_segment(set_code)}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )
        
    from spotlight_data import build_set_spotlight
    spotlight = build_set_spotlight(set_code, set_name, cards, db=db)

    return templates.TemplateResponse(
        request=request,
        name="set_detail.html",
        context={
            "active_nav": "sets",
            "set_doc": {"code": set_code, "name": set_name},
            "total_cards": len(cards),
            "cards": cards,
            "spotlight": spotlight
        },
        headers={
            "Link": f'</set/{safe_header_segment(set_code)}.md>; rel="alternate"; type="text/markdown", </set/{safe_header_segment(set_code)}.json>; rel="alternate"; type="application/json"'
        }
    )

@sets_router.get("/set/{code}.md")
@sets_router.head("/set/{code}.md")
async def set_detail_markdown(code: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=md"
    return await set_detail(request, code, background_tasks)

@sets_router.get("/set/{code}.json")
@sets_router.head("/set/{code}.json")
async def set_detail_json(code: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=json"
    return await set_detail(request, code, background_tasks)

@sets_router.get("/set/{code}/cockatrice.xml")
@sets_router.get("/set/{code}.xml")
@sets_router.head("/set/{code}/cockatrice.xml")
@sets_router.head("/set/{code}.xml")
async def set_cockatrice_xml(code: str):
    """Export complete set checklist as Cockatrice v4 XML database for desktop MTG simulators."""
    db = get_mongo_db()
    set_code = code.strip().lower()
    
    # Query distinct cards in this set
    cards_cursor = db["cards"].find(
        {"set": set_code, "lang": "en"},
        {"name": 1, "oracle_text": 1, "type_line": 1, "mana_cost": 1, "cmc": 1, 
         "colors": 1, "power": 1, "toughness": 1, "loyalty": 1, "legalities": 1, 
         "slug": 1, "set": 1, "set_name": 1, "released_at": 1}
    )
    cards = list(cards_cursor)
    if not cards:
        # Check non-en or general set
        cards = list(db["cards"].find({"set": set_code}).limit(500))
    if not cards:
        raise HTTPException(status_code=404, detail="Set not found in the Abyss")

    set_name = cards[0].get("set_name") or set_code.upper()
    released_at = cards[0].get("released_at") or "2026-01-01"

    root = ET.Element("cockatrice_carddatabase", version="4")
    sets_elem = ET.SubElement(root, "sets")
    set_elem = ET.SubElement(sets_elem, "set")
    ET.SubElement(set_elem, "name").text = set_code.upper()
    ET.SubElement(set_elem, "longname").text = set_name
    ET.SubElement(set_elem, "settype").text = "Expansion"
    ET.SubElement(set_elem, "releasedate").text = str(released_at)

    cards_elem = ET.SubElement(root, "cards")
    seen_names = set()
    for c in cards:
        c_name = c.get("name") or "Card"
        if c_name in seen_names:
            continue
        seen_names.add(c_name)

        card_elem = ET.SubElement(cards_elem, "card")
        ET.SubElement(card_elem, "name").text = c_name
        ET.SubElement(card_elem, "text").text = c.get("oracle_text") or ""
        
        prop = ET.SubElement(card_elem, "prop")
        type_line = c.get("type_line") or ""
        ET.SubElement(prop, "type").text = type_line
        
        main_type = type_line.split("—")[0].strip().split()[-1] if type_line else "Card"
        ET.SubElement(prop, "maintype").text = main_type
        ET.SubElement(prop, "manacost").text = c.get("mana_cost") or ""
        ET.SubElement(prop, "cmc").text = str(int(c.get("cmc", 0.0)))
        ET.SubElement(prop, "colors").text = "".join(c.get("colors") or [])
        
        pt = f"{c.get('power')}/{c.get('toughness')}" if c.get('power') is not None else ""
        ET.SubElement(prop, "pt").text = pt
        ET.SubElement(prop, "loyalty").text = str(c.get("loyalty") or "")
        
        legalities = c.get("legalities") or {}
        for fmt in ["standard", "commander", "modern", "pioneer", "legacy", "vintage", "pauper"]:
            status = legalities.get(fmt, "not_legal")
            ET.SubElement(prop, f"format-{fmt}").text = "legal" if status == "legal" else ("banned" if status == "banned" else "not_legal")

        c_slug = c.get("slug") or slugify(c_name)
        img_url = f"https://avascry.com/images/normal/{c_slug}-{set_code}.jpg"
        set_tag = ET.SubElement(card_elem, "set", picURL=img_url)
        set_tag.text = set_code.upper()
        
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

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'inline; filename="{set_code}_cockatrice.xml"'}
    )

@sets_router.get("/feed/sets.xml")
@sets_router.head("/feed/sets.xml")
async def feed_sets_xml():
    """RSS 2.0 Syndication Feed of the latest Magic: The Gathering sets and printings."""
    db = get_mongo_db()
    pipeline = [
        {"$group": {"_id": "$set", "name": {"$first": "$set_name"}, "released_at": {"$first": "$released_at"}, "count": {"$sum": 1}}},
        {"$sort": {"released_at": -1}},
        {"$limit": 30}
    ]
    sets = list(db["cards"].aggregate(pipeline))
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "AvaScry — Magic: The Gathering Sets & Expansions Feed"
    ET.SubElement(channel, "link").text = "https://avascry.com"
    ET.SubElement(channel, "description").text = "Real-time syndicated RSS feed of MTG sets, checklists, and 4096-dim vector embeddings on AvaScry."
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = now_rfc

    for s in sets:
        code = (s["_id"] or "").lower()
        name = s["name"] or code.upper()
        count = s["count"]
        rel = s.get("released_at") or "2026-01-01"
        
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"{name} ({code.upper()}) — {count:,} Cards"
        ET.SubElement(item, "link").text = f"https://avascry.com/set/{code}"
        ET.SubElement(item, "guid", isPermaLink="true").text = f"https://avascry.com/set/{code}"
        ET.SubElement(item, "description").text = f"Full card checklist and embeddings for {name} ({code.upper()}) with {count:,} cards. Available in HTML (/set/{code}), Markdown (/set/{code}.md), JSON (/set/{code}.json), and Cockatrice XML (/set/{code}/cockatrice.xml)."
        ET.SubElement(item, "pubDate").text = f"{rel} 00:00:00 GMT"

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return Response(content=xml_bytes, media_type="application/rss+xml")

@sets_router.get("/feed/rulings.xml")
@sets_router.head("/feed/rulings.xml")
async def feed_rulings_xml():
    """RSS 2.0 Syndication Feed of official Magic: The Gathering card rulings."""
    db = get_mongo_db()
    rulings_col = db["rulings"]
    rulings_cursor = rulings_col.find().sort("published_at", -1).limit(40)
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "AvaScry — Official MTG Card Rulings Feed"
    ET.SubElement(channel, "link").text = "https://avascry.com/rules.json"
    ET.SubElement(channel, "description").text = "Syndicated RSS feed of official Wizards of the Coast and Scryfall card rulings."
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = now_rfc

    for r in rulings_cursor:
        oid = r.get("oracle_id")
        card = db["cards"].find_one({"oracle_id": oid, "lang": "en"}) if oid else None
        c_name = card.get("name") if card else "Card Ruling"
        c_slug = card.get("slug") if card else "ruling"
        comment = r.get("comment") or ""
        pub = r.get("published_at") or "2026-01-01"
        
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"Ruling: {c_name}"
        ET.SubElement(item, "link").text = f"https://avascry.com/card/{c_slug}"
        ET.SubElement(item, "guid", isPermaLink="false").text = f"ruling-{oid}-{pub}"
        ET.SubElement(item, "description").text = f"Official Ruling for {c_name}: {comment}"
        ET.SubElement(item, "pubDate").text = f"{pub} 00:00:00 GMT"

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return Response(content=xml_bytes, media_type="application/rss+xml")
