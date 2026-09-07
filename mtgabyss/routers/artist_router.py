import re
import asyncio
from typing import List
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from db_mongo import get_mongo_db
import i18n
from mtgabyss.shared.helpers import slugify, safe_header_segment, resolve_card_images, templates
from mtgabyss.routers.auth_router import send_discord_notification

artist_router = APIRouter()

# In-memory artist name lookup table
_ARTISTS_MAP = None

# Live Gallery In-Memory Daily Cache (301 distinct Oracle cards)
_GALLERY_CACHE = {
    "timestamp": 0.0,
    "items": []
}

def get_or_build_gallery_cache(db) -> List[dict]:
    import time
    now = time.time()
    # Cache for 24 hours (86400 seconds)
    if _GALLERY_CACHE["items"] and (now - _GALLERY_CACHE["timestamp"]) < 86400:
        return _GALLERY_CACHE["items"]

    try:
        # Pull distinct Oracle cards (lang == en, non-token/non-promo standard oracle artworks)
        pipeline = [
            {"$match": {
                "image_uris.art_crop": {"$exists": True, "$ne": None},
                "lang": "en",
                "layout": {"$in": ["normal", "saga", "class", "leveler", "adventure"]}
            }},
            {"$sample": {"size": 301}},
            {"$project": {
                "name": 1,
                "slug": 1,
                "set": 1,
                "set_name": 1,
                "artist": 1,
                "rarity": 1,
                "released_at": 1,
                "image_uris": 1
            }}
        ]
        docs = list(db["cards"].aggregate(pipeline))
        items = []
        for doc in docs:
            c_name = doc.get("name") or "Card"
            c_set = (doc.get("set") or "").lower()
            c_slug = slugify(c_name)
            p_slug = f"{c_slug}-{c_set}" if c_set else c_slug
            art_url = doc.get("image_uris", {}).get("art_crop")
            large_url = doc.get("image_uris", {}).get("large") or doc.get("image_uris", {}).get("normal")
            
            if art_url:
                items.append({
                    "name": c_name,
                    "printing_slug": p_slug,
                    "set_name": doc.get("set_name", "Unknown"),
                    "set_code": c_set.upper(),
                    "artist": doc.get("artist", "Unknown Artist"),
                    "artist_slug": slugify(doc.get("artist") or "unknown"),
                    "rarity": (doc.get("rarity") or "").capitalize(),
                    "released_at": doc.get("released_at", ""),
                    "art_url": art_url,
                    "card_url": large_url
                })
        
        if items:
            _GALLERY_CACHE["items"] = items
            _GALLERY_CACHE["timestamp"] = now
            return items
    except Exception as e:
        print(f"Error building gallery cache: {e}")
        
    return _GALLERY_CACHE["items"]

@artist_router.get("/artists", response_class=HTMLResponse)
async def artists_list(request: Request):
    db = get_mongo_db()
    artists_data = []
    try:
        pipeline = [
            {"$match": {"artist": {"$exists": True, "$ne": None, "$ne": ""}}},
            {"$group": {"_id": "$artist", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 100}
        ]
        for item in db["cards"].aggregate(pipeline):
            name = item["_id"]
            if name and not re.search(r'unknown', name, re.IGNORECASE):
                artists_data.append({
                    "name": name,
                    "slug": slugify(name),
                    "card_count": item.get("count", 0)
                })
    except Exception as e:
        print(f"Error loading artists: {e}")
        
    return templates.TemplateResponse(
        request=request,
        name="artists.html",
        context={
            "active_nav": "artists",
            "artists": artists_data
        }
    )

@artist_router.get("/live-gallery", response_class=HTMLResponse)
async def live_gallery(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="live_gallery.html",
        context={
            "active_nav": "live-gallery",
            "body_class": "live-gallery-page",
            "current_lang": lang
        }
    )

@artist_router.get("/api/live-gallery/feed")
async def live_gallery_feed(request: Request):
    import random
    db = get_mongo_db()
    all_cached = get_or_build_gallery_cache(db)
    
    # Return a shuffled slice of 40 cards from the 301 cached Oracle cards
    if all_cached:
        shuffled = random.sample(all_cached, min(40, len(all_cached)))
        
        # Notify Discord once per user/guest session when they open the live gallery
        if not request.session.get("notified_gallery_session"):
            request.session["notified_gallery_session"] = True
            first_card = shuffled[0]
            first_img = first_card.get("art_url") or first_card.get("card_url")
            card_name = first_card.get("name", "Unknown Card")
            artist = first_card.get("artist", "Unknown Artist")
            set_name = first_card.get("set_name", "")
            
            user = request.session.get("user")
            user_display = (user.get("name") or user.get("discord_username")) if user else "A visitor (Guest)"
            
            asyncio.create_task(send_discord_notification(
                title="🖼️ Live Gallery Started",
                description=f"**{user_display}** just loaded the Live Gallery!",
                color=0x9B59B6,
                fields=[
                    {"name": "First Card", "value": card_name, "inline": True},
                    {"name": "Artist", "value": artist, "inline": True},
                    {"name": "Set", "value": set_name or "Standard", "inline": True}
                ],
                image_url=first_img
            ))
            
        return JSONResponse(content={"items": shuffled, "cards": shuffled})
        
    return JSONResponse(content={"items": [], "cards": []})

@artist_router.get("/artist/{slug}")
@artist_router.head("/artist/{slug}")
async def artist_detail(request: Request, slug: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    
    is_md = False
    is_json = False
    if slug.lower().endswith(".md"):
        slug = slug[:-3]
        is_md = True
    elif slug.lower().endswith(".json"):
        slug = slug[:-5]
        is_json = True

    # Fast in-memory resolution of exact artist casing (e.g. 'larry-macdougall' -> 'Larry MacDougall')
    global _ARTISTS_MAP
    if _ARTISTS_MAP is None:
        try:
            _ARTISTS_MAP = {slugify(a): a for a in db["cards"].distinct("artist") if a}
        except Exception:
            _ARTISTS_MAP = {}
    
    resolved_artist = _ARTISTS_MAP.get(slug)
    if resolved_artist:
        artist_name = resolved_artist
    else:
        unslugged = slug.replace('-', ' ')
        artist_name = unslugged.title()
    
    # 1. Fast exact match using index
    query_exact = {"artist": artist_name, "lang": "en"}
    cards_cursor = list(db["cards"].find(
        query_exact,
        {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "released_at": 1, "rarity": 1, "type_line": 1, "mana_cost": 1, "image_uris": 1, "image_slug": 1, "artist": 1}
    ).sort("released_at", -1).limit(60))
    
    if not cards_cursor:
        query_exact_any = {"artist": artist_name}
        cards_cursor = list(db["cards"].find(
            query_exact_any,
            {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "released_at": 1, "rarity": 1, "type_line": 1, "mana_cost": 1, "image_uris": 1, "image_slug": 1, "artist": 1}
        ).sort("released_at", -1).limit(60))
    
    # 2. Fallback to regex if exact title didn't hit
    if not cards_cursor:
        pattern = r'^' + r'[\s\W]*'.join(re.escape(w) for w in slug.split('-') if w) + r'$'
        query_regex = {"artist": {"$regex": pattern, "$options": "i"}, "lang": "en"}
        cards_cursor = list(db["cards"].find(
            query_regex,
            {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "released_at": 1, "rarity": 1, "type_line": 1, "mana_cost": 1, "image_uris": 1, "image_slug": 1, "artist": 1}
        ).sort("released_at", -1).limit(60))

    if not cards_cursor:
        pattern = r'^' + r'[\s\W]*'.join(re.escape(w) for w in slug.split('-') if w) + r'$'
        query_all = {"artist": {"$regex": pattern, "$options": "i"}}
        cards_cursor = list(db["cards"].find(
            query_all,
            {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "released_at": 1, "rarity": 1, "type_line": 1, "mana_cost": 1, "image_uris": 1, "image_slug": 1, "artist": 1}
        ).sort("released_at", -1).limit(60))

    if not cards_cursor:
        raise HTTPException(status_code=404, detail=f"Artist '{artist_name}' not found")

    cards = []
    for doc in cards_cursor:
        artist_name = doc.get("artist") or artist_name
        c_name = doc.get("name") or "Card"
        c_set = (doc.get("set") or "").lower()
        c_slug = slugify(c_name)
        small_url, norm_url, large_url = resolve_card_images(doc, background_tasks)
        cards.append({
            "name": c_name,
            "set": c_set,
            "set_name": doc.get("set_name") or c_set.upper(),
            "collector_number": doc.get("collector_number") or "",
            "rarity": doc.get("rarity") or "",
            "type_line": doc.get("type_line") or "",
            "mana_cost": doc.get("mana_cost") or "",
            "released_at": doc.get("released_at") or "",
            "printing_slug": f"{c_slug}-{c_set}" if c_set else c_slug,
            "image_url": norm_url,
            "large_image_url": large_url,
            "image_uris": {
                "small": small_url,
                "normal": norm_url,
                "large": large_url
            }
        })

    # Content Negotiation for AI Agents (Accept: text/markdown, application/json, or ?format=)
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()

    if is_json or "application/json" in accept_header or requested_format == "json":
        formatted_artist_cards = []
        for c in cards:
            c_p_slug = c.get("printing_slug") or ""
            c_norm = c.get("image_url") or f"/images/normal/{c_p_slug}.jpg"
            if c_norm.startswith("/"):
                c_norm = f"https://avascry.com{c_norm}"
            c_large = c.get("large_image_url") or c_norm
            if c_large.startswith("/"):
                c_large = f"https://avascry.com{c_large}"
                
            formatted_artist_cards.append({
                "name": c.get("name"),
                "printing_slug": c_p_slug,
                "set": c.get("set"),
                "set_name": c.get("set_name"),
                "collector_number": c.get("collector_number"),
                "rarity": c.get("rarity"),
                "type_line": c.get("type_line"),
                "mana_cost": c.get("mana_cost"),
                "released_at": c.get("released_at"),
                "image_uris": {
                    "normal": c_norm,
                    "large": c_large
                },
                "links": {
                    "html": f"https://avascry.com/printing/{c_p_slug}",
                    "markdown": f"https://avascry.com/printing/{c_p_slug}.md",
                    "json": f"https://avascry.com/printing/{c_p_slug}.json"
                }
            })

        artist_info = {
            "name": artist_name,
            "slug": slug,
            "links": {
                "html": f"https://avascry.com/artist/{slug}",
                "markdown": f"https://avascry.com/artist/{slug}.md",
                "json": f"https://avascry.com/artist/{slug}.json"
            }
        }
        artist_meta = db["artists"].find_one({"slug": slug}, {"blurb": 1, "commander_staples": 1})
        if artist_meta:
            if artist_meta.get("blurb"):
                artist_info["blurb"] = artist_meta["blurb"]
            if artist_meta.get("commander_staples"):
                artist_info["commander_staples"] = artist_meta["commander_staples"]

        return JSONResponse(
            content={
                "artist": artist_info,
                "total_artworks": len(formatted_artist_cards),
                "cards": formatted_artist_cards
            },
            headers={
                "Vary": "Accept",
                "Link": f'</artist/{safe_header_segment(slug)}.md>; rel="alternate"; type="text/markdown", </artist/{safe_header_segment(slug)}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_md or "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
        artist_meta = db["artists"].find_one({"slug": slug}, {"blurb": 1})
        artist_blurb = artist_meta.get("blurb") if artist_meta else None

        md_lines = [
            "---",
            f"artist: \"{artist_name}\"",
            f"artist_slug: \"{slug}\"",
            f"total_artworks: {len(cards)}",
            f"canonical_url: https://avascry.com/artist/{slug}",
            f"json_api: https://avascry.com/artist/{slug}.json",
            "---",
            f"\n# Magic: The Gathering Cards Illustrated by {artist_name}\n",
            f"- **Illustrator:** {artist_name}",
            f"- **Total Artworks Cataloged:** {len(cards)}",
            f"- **JSON API:** https://avascry.com/artist/{slug}.json\n"
        ]
        if artist_blurb:
            md_lines.append(f"{artist_blurb}\n")

        md_lines.extend([
            "| # | Card Name | Set | Type | Rarity | Mana Cost | Released |",
            "|---|-----------|-----|------|--------|-----------|----------|"
        ])
        for c in cards:
            c_num = c.get("collector_number") or "-"
            c_name = c.get("name", "")
            c_set = (c.get("set") or "").upper()
            c_type = c.get("type_line", "")
            c_rarity = (c.get("rarity") or "").capitalize()
            c_mana = c.get("mana_cost") or "-"
            c_rel = c.get("released_at") or "-"
            md_lines.append(f"| {c_num} | [{c_name}](https://avascry.com/printing/{c.get('printing_slug')}) | {c_set} | {c_type} | {c_rarity} | `{c_mana}` | {c_rel} |")

        md_text = "\n".join(md_lines)
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Vary": "Accept",
                "X-Markdown-Tokens": str(len(md_text.split())),
                "Link": f'</artist/{safe_header_segment(slug)}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )
        
    from spotlight_data import build_artist_spotlight
    spotlight = build_artist_spotlight(artist_name, slug, cards, db=db)

    return templates.TemplateResponse(
        request=request,
        name="artist_detail.html",
        context={
            "active_nav": "artists",
            "artist_name": artist_name,
            "artist_slug": slug,
            "total_cards": len(cards),
            "cards": cards,
            "spotlight": spotlight
        },
        headers={
            "Link": f'</artist/{safe_header_segment(slug)}.md>; rel="alternate"; type="text/markdown", </artist/{safe_header_segment(slug)}.json>; rel="alternate"; type="application/json"'
        }
    )

@artist_router.get("/artist/{slug}.md")
@artist_router.head("/artist/{slug}.md")
async def artist_detail_markdown(slug: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=md"
    return await artist_detail(request, slug, background_tasks)

@artist_router.get("/artist/{slug}.json")
@artist_router.head("/artist/{slug}.json")
async def artist_detail_json(slug: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=json"
    return await artist_detail(request, slug, background_tasks)
