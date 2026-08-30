import os
import re
import asyncio
from typing import Optional, List, Dict, Any, Tuple
import httpx
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from db_mongo import get_mongo_db, get_old_db
import i18n

app = FastAPI(title="AvaScry", description="Magic: The Gathering Visual Explorer & Strategy Engine")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")

SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "fallback-insecure-secret-key-32-bytes-min")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="avascry_session",
    max_age=14 * 24 * 3600, # 14 days
    same_site="lax",
    https_only=False # Allow http for local development; cookies still work behind https proxy
)

# Ensure static & image directories exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("public/images/normal", exist_ok=True)
os.makedirs("public/images/large", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="public/images"), name="images")

templates = Jinja2Templates(directory="templates")
templates.env.globals["t"] = i18n.t
templates.env.globals["LANGUAGES"] = i18n.LANGUAGES
templates.env.globals["get_locale"] = i18n.get_locale

# =========================================================================
# HIGH-SPEED IN-MEMORY RAM CACHE (Auto-flushed Sunday night or at 64GB RAM)
# =========================================================================
RAM_CACHE: Dict[str, Any] = {}
LAST_SUNDAY_FLUSH: Optional[str] = None

def get_ram_usage_gb() -> float:
    """Return process RAM usage in GB."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 ** 3)
    except Exception:
        return 0.0

@app.on_event("startup")
async def start_cache_cleaner_task():
    async def periodic_cache_flush():
        global LAST_SUNDAY_FLUSH
        while True:
            try:
                now = datetime.now(timezone.utc)
                is_sunday_night = (now.weekday() == 6 and now.hour >= 23)
                date_key = now.strftime("%Y-%m-%d")
                ram_gb = get_ram_usage_gb()

                # Flush on Sunday night once, or if RAM exceeds 64GB guardrail
                if (is_sunday_night and LAST_SUNDAY_FLUSH != date_key) or (ram_gb >= 64.0):
                    count = len(RAM_CACHE)
                    RAM_CACHE.clear()
                    LAST_SUNDAY_FLUSH = date_key
                    print(f"[RAM CACHE] Flushed {count} cached items (Reason: {'Sunday weekly reset' if is_sunday_night else f'64GB guardrail reached: {ram_gb:.1f}GB'})")

            except Exception as e:
                print(f"[RAM CACHE] Monitor error: {e}")
            await asyncio.sleep(1800) # Check every 30 minutes

    asyncio.create_task(periodic_cache_flush())

_orig_template_response = templates.TemplateResponse

def localized_template_response(name: str, context: dict, *args, **kwargs):
    req = context.get("request") or kwargs.get("request")
    if req:
        if "current_lang" not in context:
            context["current_lang"] = getattr(req.state, "lang", i18n.get_locale(req))
        if "user" not in context:
            context["user"] = req.session.get("user")
    return _orig_template_response(name=name, context=context, *args, **kwargs)

templates.TemplateResponse = localized_template_response

# Context processor middleware to ensure current_lang is always available in templates
@app.middleware("http")
async def add_localization_context(request: Request, call_next):
    lang = i18n.get_locale(request)
    request.state.lang = lang
    response = await call_next(request)
    if "lang" in request.query_params:
        response.set_cookie(key="mtgabyss_lang", value=lang, max_age=31536000, path="/")
    return response


POWER_NINE = {
    'black lotus', 'ancestral recall', 'time walk', 
    'mox pearl', 'mox sapphire', 'mox jet', 
    'mox ruby', 'mox emerald', 'timetwister'
}

COLOR_MAP = {
    'W': 'White',
    'U': 'Blue',
    'B': 'Black',
    'R': 'Red',
    'G': 'Green'
}

WHITELISTED_TAGS = {
    'ramp', 'mana-rock', 'mana-dork', 'tutor', 'card-advantage', 'card-draw',
    'removal', 'board-wipe', 'counterspell', 'combo-piece', 'win-con',
    'token-generator', 'graveyard-recursion', 'aristocrats', 'blink',
    'stax', 'pillowfort', 'voltron', 'burn', 'mill', 'infect', 'anthem',
    'cantrip', 'mana-sink', 'extra-turns', 'extra-combats', 'lifegain',
    'sacrifice-outlet', 'hatebear', 'reanimation', 'cost-reducer', 'ritual',
    'evasion', 'protection', 'commander-staple'
}

# In-flight download task tracker to avoid duplicate downloads
_downloading_slugs = set()

def slugify(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^\w\s-]', '', s, flags=re.UNICODE)
    s = re.sub(r'[\s_-]+', '-', s)
    return s.strip('-')

def get_image_slug(card_doc: dict, has_faces: bool = False) -> str:
    base_slug = card_doc.get("image_slug")
    if not base_slug:
        card_name = card_doc.get('name') or 'unknown'
        set_name = card_doc.get('set_name') or card_doc.get('set') or 'unknown'
        artist = card_doc.get('artist') or 'unknown'
        collector_number = card_doc.get('collector_number') or card_doc.get('raw', {}).get('collector_number') or ''
        
        slug_parts = [
            slugify(card_name), 
            slugify(set_name), 
            slugify(artist),
            slugify(collector_number)
        ]
        slug_parts = [p for p in slug_parts if p]
        base_slug = "-".join(slug_parts)
        
    suffix = "_0" if has_faces else ""
    return f"{base_slug}{suffix}.jpg"

def get_scryfall_direct_uris(card_doc: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract direct CDN image URIs from the Scryfall card document (small, normal, large)."""
    # 1. Root level image_uris
    image_uris = card_doc.get("image_uris")
    if image_uris and isinstance(image_uris, dict):
        return image_uris.get("small"), image_uris.get("normal"), image_uris.get("large") or image_uris.get("normal")

    # 2. Multi-faced card faces
    card_faces = card_doc.get("card_faces")
    if card_faces and isinstance(card_faces, list) and len(card_faces) > 0:
        face_uris = card_faces[0].get("image_uris")
        if face_uris and isinstance(face_uris, dict):
            return face_uris.get("small"), face_uris.get("normal"), face_uris.get("large") or face_uris.get("normal")

    # 3. Check inside nested raw dict if imported from legacy schema
    raw = card_doc.get("raw", {})
    if raw and isinstance(raw, dict):
        raw_uris = raw.get("image_uris")
        if raw_uris and isinstance(raw_uris, dict):
            return raw_uris.get("small"), raw_uris.get("normal"), raw_uris.get("large") or raw_uris.get("normal")
        raw_faces = raw.get("card_faces")
        if raw_faces and isinstance(raw_faces, list) and len(raw_faces) > 0:
            face_uris = raw_faces[0].get("image_uris")
            if face_uris and isinstance(face_uris, dict):
                return face_uris.get("small"), face_uris.get("normal"), face_uris.get("large") or face_uris.get("normal")

    return None, None, None

async def _download_and_save_image(url: str, dest_path: str):
    """Download single image file asynchronously and save to disk."""
    if not url:
        return
    try:
        headers = {"User-Agent": "MTGAbyss/2.0 (mtgabyss.com)"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            if resp.status_code == 200 and resp.content:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
    except Exception as e:
        print(f"Warning: Failed to download image from {url}: {e}")

async def background_cache_card_images(slug_name: str, normal_url: Optional[str], large_url: Optional[str]):
    """Background task to fetch and persist both normal and large card images."""
    if slug_name in _downloading_slugs:
        return
    _downloading_slugs.add(slug_name)
    try:
        normal_path = f"public/images/normal/{slug_name}"
        large_path = f"public/images/large/{slug_name}"

        tasks = []
        if normal_url and not os.path.exists(normal_path):
            tasks.append(_download_and_save_image(normal_url, normal_path))
        if large_url and not os.path.exists(large_path):
            tasks.append(_download_and_save_image(large_url, large_path))

        if tasks:
            await asyncio.gather(*tasks)
    finally:
        _downloading_slugs.discard(slug_name)

def resolve_card_images(card_doc: dict, background_tasks: Optional[BackgroundTasks] = None) -> Tuple[str, str, str]:
    """
    Check if local images exist on disk.
    If yes -> return local paths (/images/normal/..., /images/large/...).
    If no  -> return Scryfall direct CDN URLs (small, normal, large).
    """
    card_faces = card_doc.get("card_faces") or card_doc.get("raw", {}).get("card_faces", [])
    has_faces = bool(card_faces)
    slug_name = get_image_slug(card_doc, has_faces)

    normal_local_file = f"public/images/normal/{slug_name}"
    large_local_file = f"public/images/large/{slug_name}"

    normal_exists = os.path.exists(normal_local_file)
    large_exists = os.path.exists(large_local_file)

    # Cache miss: get live Scryfall CDN URLs
    scryfall_small, scryfall_normal, scryfall_large = get_scryfall_direct_uris(card_doc)

    # Schedule background caching if Scryfall URLs exist
    if background_tasks and (scryfall_normal or scryfall_large):
        background_tasks.add_task(
            background_cache_card_images,
            slug_name,
            scryfall_normal,
            scryfall_large
        )

    # Return local if that specific file exists, else hotlink CDN URL, else placeholder
    img_url = f"/images/normal/{slug_name}" if normal_exists else (scryfall_normal or f"/images/normal/{slug_name}")
    large_img_url = f"/images/large/{slug_name}" if large_exists else (scryfall_large or img_url)
    small_img_url = scryfall_small or img_url

    return small_img_url, img_url, large_img_url

def build_card_view_model(card: dict, db=None, background_tasks: Optional[BackgroundTasks] = None) -> dict:
    small_image_url, image_url, large_image_url = resolve_card_images(card, background_tasks)

    # Check if localized image is missing/placeholder
    img_status = (card.get("image_status") or "").lower()
    is_placeholder = img_status in ("placeholder", "missing")
    lang_code = (card.get("lang") or "en").upper()
    has_image_note = is_placeholder and lang_code != "EN"

    # If it is a placeholder banner image, fall back to clean English printing if available
    if is_placeholder and db is not None:
        try:
            en_doc = db["cards"].find_one({
                "oracle_id": card.get("oracle_id"),
                "lang": "en",
                "image_status": {"$nin": ["placeholder", "missing"]}
            }, sort=[("released_at", 1)])
            if en_doc:
                _, en_normal, en_large = resolve_card_images(en_doc, background_tasks)
                image_url = en_normal
                large_image_url = en_large
        except Exception:
            pass

    # Resolve Back Face Image ONLY for real double-faced / transform cards
    back_image_url = None
    back_large_image_url = None
    is_dfc = False
    card_faces = card.get("card_faces") or card.get("raw", {}).get("card_faces", [])
    if card_faces and len(card_faces) > 1:
        face1 = card_faces[1]
        f1_uris = face1.get("image_uris") or {}
        back_image_url = f1_uris.get("normal")
        back_large_image_url = f1_uris.get("large") or back_image_url
        if back_image_url:
            is_dfc = True

    colors = card.get('color_identity', [])
    color_identity_str = ", ".join(COLOR_MAP.get(c, c) for c in colors) if colors else 'Colorless'
    
    # Build Badges
    type_line = card.get('type_line', '')
    main_types = ["Legendary", "Creature", "Artifact", "Enchantment", "Instant", "Sorcery", "Land", "Planeswalker"]
    badges = []
    for t in main_types:
        if t in type_line:
            badges.append({"label": t, "type": "type"})
    
    for c in colors:
        badges.append({"label": COLOR_MAP.get(c, c), "type": f"color-{c.lower()}"})
    if not colors:
        badges.append({"label": "Colorless", "type": "colorless"})
        
    rarity = (card.get('rarity') or '').capitalize()
    if rarity:
        badges.append({"label": rarity, "type": f"rarity-{rarity.lower()}"})
    
    if card.get('reserved'):
        badges.append({"label": "Reserved List", "type": "reserved"})
    if card.get('name', '').lower() in POWER_NINE:
        badges.append({"label": "Power Nine", "type": "p9"})

    # Filter whitelisted functional gameplay tags
    raw_tags = card.get('tags', [])
    filtered_tags = []
    for t in raw_tags:
        t_slug = t.get('tag', '') if isinstance(t, dict) else str(t)
        if t_slug.lower() in WHITELISTED_TAGS:
            clean_label = " ".join(w.capitalize() for w in t_slug.replace('-', ' ').replace('_', ' ').split())
            filtered_tags.append({"tag": clean_label, "raw_slug": t_slug})

    c_name = card.get("name") or "card"
    c_printed_name = card.get("printed_name") or c_name
    c_set = (card.get("set") or "").lower()
    base_slug = slugify(c_name)
    printing_slug = f"{base_slug}-{c_set}" if c_set else base_slug

    FLAGS = {
        'en': '🇺🇸', 'ja': '🇯🇵', 'fr': '🇫🇷', 'de': '🇩🇪',
        'es': '🇪🇸', 'it': '🇮🇹', 'zhs': '🇨🇳', 'zht': '🇹🇼',
        'pt': '🇧🇷', 'ru': '🇷🇺', 'ko': '🇰🇷'
    }
    c_lang = (card.get("lang") or "en").lower()

    return {
        "id": card.get("id"),
        "oracle_id": card.get("oracle_id"),
        "name": c_name,
        "printed_name": c_printed_name,
        "slug": base_slug,
        "printing_slug": printing_slug,
        "mana_cost": card.get("mana_cost"),
        "cmc": card.get("cmc", 0),
        "type_line": type_line,
        "oracle_text": card.get("oracle_text"),
        "power": card.get("power"),
        "toughness": card.get("toughness"),
        "loyalty": card.get("loyalty"),
        "colors": colors,
        "color_identity_str": color_identity_str,
        "keywords": card.get("keywords", []),
        "artist": card.get("artist"),
        "artist_slug": slugify(card.get("artist") or "unknown"),
        "set_name": card.get("set_name"),
        "set": c_set,
        "collector_number": card.get("collector_number"),
        "released_at": card.get("released_at"),
        "rarity": card.get("rarity", ""),
        "lang": card.get("lang", "en"),
        "legalities": card.get("legalities", {}),
        "tags": filtered_tags,
        "image_url": image_url,
        "large_image_url": large_image_url,
        "back_image_url": back_image_url,
        "back_large_image_url": back_large_image_url,
        "has_image_note": has_image_note,
        "badges": badges
    }


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    featured = []
    sample_slugs = ["black-lotus", "atraxa-praetors-voice", "the-ur-dragon", "sol-ring", "rhystic-study"]
    try:
        cards_cursor = db["cards"].find({"slug": {"$in": sample_slugs}}).limit(6)
        for c in cards_cursor:
            vm = build_card_view_model(c, db, background_tasks)
            featured.append(vm)
    except Exception:
        pass

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "active_nav": "home",
            "featured_cards": featured,
            "q": ""
        }
    )

@app.get("/random", response_class=HTMLResponse)
async def random_card(request: Request):
    import random
    db = get_mongo_db()
    try:
        gallery_items = get_or_build_gallery_cache(db)
        if gallery_items:
            chosen = random.choice(gallery_items)
            return RedirectResponse(url=f"/printing/{chosen['printing_slug']}", status_code=303)
            
        sample = list(db["cards"].aggregate([
            {"$match": {"lang": "en", "image_uris.normal": {"$exists": True}}},
            {"$sample": {"size": 1}}
        ]))
        if sample:
            c = sample[0]
            c_set = (c.get("set") or "").lower()
            c_slug = slugify(c.get("name") or "")
            target = f"{c_slug}-{c_set}" if c_set else (c.get("id") or c_slug)
            return RedirectResponse(url=f"/printing/{target}", status_code=303)
    except Exception as e:
        print(f"Error selecting random card: {e}")
    return RedirectResponse(url="/printing/black-lotus-lea", status_code=303)


# ==========================================
# AUTHENTICATION (Google OAuth)
# ==========================================

def get_base_url(request: Request) -> str:
    """Resolve correct base URL honoring Cloudflare / reverse proxy headers."""
    env_base = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")
    if env_base:
        return env_base
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{proto}://{host}"

@app.get("/auth/login")
async def auth_google_login(request: Request, next: str = "/commander"):
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id or "your-domain" in client_id:
        return HTMLResponse("<h3>Error: GOOGLE_CLIENT_ID is not configured in .env</h3>", status_code=500)
    
    redirect_uri = f"{get_base_url(request)}/auth/google/callback"
    request.session["oauth_next"] = next
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + httpx.QueryParams({
            "client_id": client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": redirect_uri,
            "access_type": "online",
            "prompt": "select_account"
        }).__str__()
    )
    return RedirectResponse(url=auth_url, status_code=303)

@app.get("/auth/google/callback")
async def auth_google_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    if error or not code:
        return RedirectResponse(url=f"/commander?auth_error={error or 'cancelled'}", status_code=303)
    
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = f"{get_base_url(request)}/auth/google/callback"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Exchange authorization code for token
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            
            # Fetch user profile info
            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_resp.raise_for_status()
            profile = user_resp.json()
            
        google_sub = profile.get("sub")
        if not google_sub:
            return RedirectResponse(url="/commander?auth_error=missing_sub", status_code=303)
            
        db = get_mongo_db()
        now = datetime.now(timezone.utc).isoformat()
        
        # Upsert user record strictly by google_sub
        user_doc = db["users"].find_one_and_update(
            {"google_sub": google_sub},
            {
                "$set": {
                    "email": profile.get("email", ""),
                    "name": profile.get("name", "Magic Player"),
                    "picture": profile.get("picture", ""),
                    "updated_at": now
                },
                "$setOnInsert": {
                    "google_sub": google_sub,
                    "created_at": now
                }
            },
            upsert=True,
            return_document=True
        )
        
        # Set session (store only safe user identity)
        request.session["user"] = {
            "id": str(user_doc["_id"]),
            "google_sub": google_sub,
            "name": user_doc.get("name", "Magic Player"),
            "email": user_doc.get("email", ""),
            "picture": user_doc.get("picture", "")
        }
        
        next_url = request.session.pop("oauth_next", "/commander")
        return RedirectResponse(url=next_url, status_code=303)
        
    except Exception as e:
        print(f"OAuth Callback Error: {e}")
        return RedirectResponse(url=f"/commander?auth_error=oauth_failed", status_code=303)

@app.get("/auth/logout")
async def auth_logout(request: Request, next: str = "/commander"):
    request.session.clear()
    return RedirectResponse(url=next, status_code=303)

@app.get("/api/me")
async def api_me(request: Request):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"authenticated": False, "user": None})
    return JSONResponse({"authenticated": True, "user": user})

# ==========================================
# DECK PERSISTENCE (Strict User Ownership)
# ==========================================

@app.get("/api/decks")
async def list_user_decks(request: Request):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"authenticated": False, "decks": []})
    
    db = get_mongo_db()
    decks = list(db["decks"].find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("updated_at", -1).limit(50))
    return JSONResponse({"authenticated": True, "decks": decks})

@app.get("/api/deck/{deck_id}")
async def get_user_deck(deck_id: str, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    db = get_mongo_db()
    deck = db["decks"].find_one(
        {"deck_id": deck_id, "user_id": user["id"]},
        {"_id": 0}
    )
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return JSONResponse({"deck": deck})

@app.post("/api/deck/save")
async def save_user_deck(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to save decks")
    
    body = await request.json()
    deck_id = body.get("deck_id") or str(uuid.uuid4())[:12]
    name = (body.get("name") or "Untitled Deck").strip()
    commander_data = body.get("commander") or {}
    cards = body.get("cards") or [] # [{oracle_id, name, count, image_normal, printing_slug}, ...]
    active_query = (body.get("active_query") or "").strip()

    db = get_mongo_db()
    now = datetime.now(timezone.utc).isoformat()
    
    deck_doc = {
        "deck_id": deck_id,
        "user_id": user["id"],
        "name": name,
        "commander": commander_data,
        "cards": cards,
        "active_query": active_query,
        "card_count": sum(c.get("count", 1) for c in cards),
        "updated_at": now
    }
    
    db["decks"].update_one(
        {"deck_id": deck_id, "user_id": user["id"]},
        {
            "$set": deck_doc,
            "$setOnInsert": {"created_at": now}
        },
        upsert=True
    )
    
    return JSONResponse({"status": "saved", "deck_id": deck_id, "updated_at": now})

@app.delete("/api/deck/{deck_id}")
async def delete_user_deck(deck_id: str, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    db = get_mongo_db()
    result = db["decks"].delete_one({"deck_id": deck_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Deck not found")
    return JSONResponse({"status": "deleted", "deck_id": deck_id})


@app.get("/commander", response_class=HTMLResponse)
async def commander_chooser(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="commander.html",
        context={
            "active_nav": "commander",
            "current_lang": lang
        }
    )

@app.get("/api/commander/search")
async def commander_search(
    q: Optional[str] = Query(None),
    colors: Optional[str] = Query(None),
    do_random: Optional[bool] = Query(False),
    limit: int = Query(24, le=60)
):
    db = get_mongo_db()
    mongo_filter = {
        "lang": "en",
        "$or": [
            {"type_line": re.compile(r"Legendary.*Creature", re.I)},
            {"oracle_text": re.compile(r"can be your commander", re.I)},
            {"card_faces.0.type_line": re.compile(r"Legendary.*Creature", re.I)},
        ]
    }

    # Color identity filter
    if colors:
        selected = [c.strip().upper() for c in colors.split(",") if c.strip()]
        if selected:
            mongo_filter["color_identity"] = {"$not": {"$elemMatch": {"$nin": selected}}}

    # Keyword search on name + oracle_text + type_line
    if q and q.strip():
        words = q.strip().split()
        word_filters = []
        for w in words:
            pattern = re.compile(re.escape(w), re.I)
            word_filters.append({"$or": [
                {"name": pattern},
                {"oracle_text": pattern},
                {"type_line": pattern},
                {"keywords": pattern},
            ]})
        if word_filters:
            mongo_filter["$and"] = word_filters

    try:
        projection = {"name": 1, "set": 1, "type_line": 1, "color_identity": 1,
                      "image_uris": 1, "card_faces": 1, "oracle_text": 1, "keywords": 1}
        if do_random or not (q and q.strip()):
            pipeline = [
                {"$match": mongo_filter},
                {"$sample": {"size": limit}},
                {"$project": projection}
            ]
            docs = list(db["cards"].aggregate(pipeline))
        else:
            docs = list(db["cards"].find(mongo_filter, projection).limit(limit))
    except Exception as e:
        print(f"Commander search error: {e}")
        docs = []

    results = []
    for doc in docs:
        name = doc.get("name") or "Unknown"
        c_set = (doc.get("set") or "").lower()
        printing_slug = f"{slugify(name)}-{c_set}" if c_set else slugify(name)
        img = (doc.get("image_uris") or {})
        if not img and doc.get("card_faces"):
            img = (doc["card_faces"][0].get("image_uris") or {})
        results.append({
            "name": name,
            "printing_slug": printing_slug,
            "type_line": doc.get("type_line", ""),
            "color_identity": doc.get("color_identity", []),
            "oracle_text": (doc.get("oracle_text") or "")[:220],
            "image_normal": img.get("normal") or img.get("large") or "",
            "image_art_crop": img.get("art_crop") or "",
        })

    return JSONResponse({"commanders": results})


@app.get("/api/commander/suggest")
async def commander_suggest(q: str = Query("")):
    """Fast autocomplete for commander names — prefix match, deduplicated by oracle_id (cached)."""
    q_clean = q.strip().lower()
    if not q_clean:
        return JSONResponse({"suggestions": []})
    
    cache_key = f"cmd_sug:{q_clean}"
    if cache_key in RAM_CACHE:
        return JSONResponse({"suggestions": RAM_CACHE[cache_key]})

    db = get_mongo_db()
    pattern = re.compile(f"^{re.escape(q.strip())}", re.I)
    commander_filter = {
        "lang": "en",
        "name": pattern,
        "$or": [
            {"type_line": re.compile(r"Legendary.*Creature", re.I)},
            {"oracle_text": re.compile(r"can be your commander", re.I)},
            {"card_faces.0.type_line": re.compile(r"Legendary.*Creature", re.I)},
        ]
    }
    pipeline = [
        {"$match": commander_filter},
        {"$sort": {"released_at": -1}},
        {
            "$group": {
                "_id": "$oracle_id",
                "name": {"$first": "$name"},
                "set": {"$first": "$set"},
                "type_line": {"$first": "$type_line"},
                "color_identity": {"$first": "$color_identity"},
                "oracle_text": {"$first": "$oracle_text"},
                "image_uris": {"$first": "$image_uris"},
                "card_faces": {"$first": "$card_faces"}
            }
        },
        {"$limit": 8}
    ]
    docs = list(db["cards"].aggregate(pipeline))

    suggestions = []
    for doc in docs:
        img = (doc.get("image_uris") or {})
        if not img and doc.get("card_faces"):
            img = (doc["card_faces"][0].get("image_uris") or {})
        name = doc.get("name", "")
        c_set = (doc.get("set") or "").lower()
        suggestions.append({
            "name": name,
            "oracle_id": doc.get("_id", ""),
            "printing_slug": f"{slugify(name)}-{c_set}" if c_set else slugify(name),
            "type_line": doc.get("type_line", ""),
            "color_identity": doc.get("color_identity", []),
            "oracle_text": doc.get("oracle_text", ""),
            "image_normal": img.get("normal") or img.get("large") or "",
            "image_art_crop": img.get("art_crop") or "",
        })
    RAM_CACHE[cache_key] = suggestions
    return JSONResponse({"suggestions": suggestions})


@app.get("/api/commander/profile")
async def commander_profile(oracle_id: str = Query(...)):
    """Return full commander card data by oracle_id."""
    db = get_mongo_db()
    doc = db["cards"].find_one(
        {"oracle_id": oracle_id, "lang": "en"},
        {"name": 1, "oracle_id": 1, "type_line": 1, "color_identity": 1,
         "oracle_text": 1, "keywords": 1, "image_uris": 1, "card_faces": 1,
         "mana_cost": 1, "cmc": 1, "set": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Commander not found")
    img = (doc.get("image_uris") or {})
    if not img and doc.get("card_faces"):
        img = (doc["card_faces"][0].get("image_uris") or {})
    name = doc.get("name", "")
    c_set = (doc.get("set") or "").lower()
    return JSONResponse({
        "name": name,
        "oracle_id": doc.get("oracle_id", ""),
        "printing_slug": f"{slugify(name)}-{c_set}" if c_set else slugify(name),
        "type_line": doc.get("type_line", ""),
        "color_identity": doc.get("color_identity", []),
        "oracle_text": doc.get("oracle_text", ""),
        "mana_cost": doc.get("mana_cost", ""),
        "image_normal": img.get("normal") or img.get("large") or "",
        "image_art_crop": img.get("art_crop") or "",
        "image_large": img.get("large") or img.get("normal") or "",
    })


@app.post("/api/commander/discover")
async def commander_discover(request: Request):
    """
    Interactive draft search:
    Accepts commander oracle_id, color_identity, and a natural language query/theme
    (e.g., 'red creature 4 mana', '10 lands', 'card draw').
    Returns deduplicated Oracle cards clamped to the commander's color identity.
    """
    body = await request.json()
    oracle_id: str = body.get("oracle_id", "")
    theme: str = body.get("theme", "").strip()
    color_identity: list = body.get("color_identity", [])
    limit: int = int(body.get("limit", 24))

    new_db = get_mongo_db()
    old_db = get_old_db()

    # Base query clamped to commander's color identity and English
    base_match = {"lang": "en"}
    if color_identity:
        base_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
    if oracle_id:
        base_match["oracle_id"] = {"$ne": oracle_id}

    # Parse query parameters (e.g. cmc/mana, card types, terms)
    theme_lower = theme.lower()
    and_conditions = []

    # CMC parsing (e.g. "4 mana", "cmc 3", "3-mana", "mana value 2")
    cmc_match = re.search(r'(\d+)\s*(?:mana|cmc)', theme_lower) or re.search(r'(?:mana|cmc)\s*(?:value\s*)?(\d+)', theme_lower)
    if cmc_match:
        try:
            target_cmc = float(cmc_match.group(1))
            and_conditions.append({"cmc": target_cmc})
        except ValueError:
            pass

    # Type line parsing
    type_tokens = []
    for t_kw in ["creature", "instant", "sorcery", "enchantment", "artifact", "planeswalker", "land", "battle"]:
        if t_kw in theme_lower:
            type_tokens.append(t_kw)
    if type_tokens:
        type_pattern = "|".join(type_tokens)
        and_conditions.append({"type_line": {"$regex": type_pattern, "$options": "i"}})

    # Color words in query
    color_map = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G", "colorless": "C"}
    explicit_colors = [c_code for c_name, c_code in color_map.items() if c_name in theme_lower]
    if explicit_colors and "C" not in explicit_colors:
        and_conditions.append({"colors": {"$in": explicit_colors}})

    # Remaining descriptive words / mechanics (e.g. "flying", "deathtouch", "draw", "counter")
    stopwords = {"mana", "cmc", "a", "an", "the", "for", "with", "and", "or", "in", "my", "deck", "want", "some", "good", "best", "different", "card", "cards", "what", "exists", "available", "show", "me", "that", "have", "has"}
    tokens = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', theme_lower) if w not in stopwords and w not in type_tokens and w not in color_map]
    
    # Require EVERY meaningful descriptive token (e.g. "flying") to match
    for token in tokens:
        token_regex = re.compile(re.escape(token), re.I)
        and_conditions.append({
            "$or": [
                {"name": token_regex},
                {"oracle_text": token_regex},
                {"type_line": token_regex},
                {"keywords": token_regex}
            ]
        })

    if and_conditions:
        base_match["$and"] = and_conditions

    # Aggregation pipeline: group by oracle_id to strictly guarantee 1 printing per oracle card
    pipeline = [
        {"$match": base_match},
        {"$sort": {"released_at": -1}},
        {
            "$group": {
                "_id": "$oracle_id",
                "name": {"$first": "$name"},
                "set": {"$first": "$set"},
                "type_line": {"$first": "$type_line"},
                "color_identity": {"$first": "$color_identity"},
                "oracle_text": {"$first": "$oracle_text"},
                "mana_cost": {"$first": "$mana_cost"},
                "cmc": {"$first": "$cmc"},
                "image_uris": {"$first": "$image_uris"},
                "card_faces": {"$first": "$card_faces"}
            }
        },
        {"$limit": max(limit, 60)}
    ]

    docs = list(new_db["cards"].aggregate(pipeline))

    # Only fall back to generic pre-computed similarity if user entered NO specific filters at all
    if len(docs) == 0 and not and_conditions and oracle_id:
        sim_doc = old_db["similar_cards"].find_one({"oracle_id": oracle_id})
        if sim_doc:
            sim_oids = [s["oracle_id"] for s in sim_doc.get("similar", []) if s.get("oracle_id") != oracle_id]
            fallback_match = {
                "oracle_id": {"$in": sim_oids},
                "lang": "en"
            }
            if color_identity:
                fallback_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
            
            fb_pipeline = [
                {"$match": fallback_match},
                {"$group": {
                    "_id": "$oracle_id",
                    "name": {"$first": "$name"},
                    "set": {"$first": "$set"},
                    "type_line": {"$first": "$type_line"},
                    "color_identity": {"$first": "$color_identity"},
                    "oracle_text": {"$first": "$oracle_text"},
                    "mana_cost": {"$first": "$mana_cost"},
                    "cmc": {"$first": "$cmc"},
                    "image_uris": {"$first": "$image_uris"},
                    "card_faces": {"$first": "$card_faces"}
                }},
                {"$limit": limit}
            ]
            docs = list(new_db["cards"].aggregate(fb_pipeline))

    # Check RAM Cache first
    cache_key = f"discover:{oracle_id}:{','.join(sorted(color_identity))}:{theme_lower}:{limit}"
    if cache_key in RAM_CACHE:
        return JSONResponse(RAM_CACHE[cache_key])

    results = []
    for doc in docs:
        img = (doc.get("image_uris") or {})
        if not img and doc.get("card_faces"):
            img = (doc["card_faces"][0].get("image_uris") or {})
        name = doc.get("name", "")
        c_set = (doc.get("set") or "").lower()
        oid = doc.get("_id", "")
        results.append({
            "name": name,
            "oracle_id": oid,
            "printing_slug": f"{slugify(name)}-{c_set}" if c_set else slugify(name),
            "type_line": doc.get("type_line", ""),
            "color_identity": doc.get("color_identity", []),
            "oracle_text": doc.get("oracle_text") or "",
            "mana_cost": doc.get("mana_cost", ""),
            "image_normal": img.get("normal") or img.get("large") or "",
            "image_large": img.get("large") or img.get("normal") or "",
        })

    response_data = {"cards": results, "query": theme, "total": len(results)}
    RAM_CACHE[cache_key] = response_data
    return JSONResponse(response_data)



@app.get("/card/{slug}", response_class=HTMLResponse)
async def card_name_shortcut(request: Request, slug: str):
    """Clean shortcut redirecting /card/<name> to the primary/earliest Oracle printing of that card."""
    db = get_mongo_db()
    unslugged = slug.replace('-', ' ')
    
    # 1. Match card by name or slug
    card = db["cards"].find_one({
        "$or": [
            {"slug": slug},
            {"name": slug},
            {"name": unslugged},
            {"name": {"$regex": f"^{re.escape(unslugged)}$", "$options": "i"}}
        ]
    })
    
    if card:
        oracle_id = card.get("oracle_id")
        if oracle_id:
            # Find earliest / original Oracle printing in English
            oracle_card = db["cards"].find_one(
                {"oracle_id": oracle_id, "lang": "en"},
                sort=[("released_at", 1)]
            ) or card
            c_slug = slugify(oracle_card.get("name") or "")
            c_set = (oracle_card.get("set") or "").lower()
            return RedirectResponse(url=f"/printing/{c_slug}-{c_set}", status_code=303)
            
    # Fallback to direct printing route
    return RedirectResponse(url=f"/printing/{slug}", status_code=303)

def slug_to_name_regex(slug: str) -> re.Pattern:
    """Build a regex that matches card names regardless of stripped apostrophes, commas, or dashes."""
    clean = slug.strip().lower()
    chars = [re.escape(c) if c != '-' else r'[\s\-\'\,\.\:]+' for c in clean]
    pattern_str = r'^' + r'[\'\,\.\:\s\-]*'.join(chars) + r'$'
    return re.compile(pattern_str, re.IGNORECASE)

@app.get("/printing/{identifier}", response_class=HTMLResponse)
async def printing_detail(request: Request, identifier: str, background_tasks: BackgroundTasks):
    current_lang = getattr(request.state, "lang", i18n.get_locale(request))
    user_state = request.session.get("user")
    
    # Fast In-Memory RAM Cache for Rendered Card Details
    cache_key = f"page:printing:{identifier.lower()}:{current_lang}:{bool(user_state)}"
    if cache_key in RAM_CACHE:
        return HTMLResponse(content=RAM_CACHE[cache_key], status_code=200)

    db = get_mongo_db()
    card = None

    # 1. Try match by UUID
    card = db["cards"].find_one({"id": identifier})

    # 2. Try match by <slug>-<set>-<lang> or <slug>-<set>
    if not card and '-' in identifier:
        parts = identifier.split('-')
        if len(parts) >= 3:
            # Check if last part is a language code (e.g. ja, de, it, fr, etc.)
            possible_lang = parts[-1].lower()
            possible_set = parts[-2].lower()
            card_slug = "-".join(parts[:-2])
            pattern = slug_to_name_regex(card_slug)
            
            card = db["cards"].find_one({
                "set": possible_set,
                "lang": possible_lang,
                "$or": [
                    {"slug": card_slug},
                    {"name": pattern}
                ]
            })

        if not card and len(parts) >= 2:
            card_slug, set_code = "-".join(parts[:-1]), parts[-1].lower()
            pattern = slug_to_name_regex(card_slug)
            card = db["cards"].find_one({
                "set": set_code,
                "$or": [
                    {"slug": card_slug},
                    {"name": pattern}
                ]
            })

    # 3. Fallback match by name or slug
    if not card:
        pattern = slug_to_name_regex(identifier)
        card = db["cards"].find_one({
            "$or": [
                {"slug": identifier},
                {"name": pattern}
            ]
        })

    if not card:
        raise HTTPException(status_code=404, detail="Printing not found in the Abyss")
        
    oracle_id = card.get("oracle_id")
    card_vm = build_card_view_model(card, db, background_tasks)
    
    # Load All Other Printings for this Oracle ID
    printings = []
    if oracle_id:
        p_cursor = db["cards"].find({"oracle_id": oracle_id}).sort("released_at", 1)
        for p in p_cursor:
            p_name = p.get("name") or card.get("name") or "card"
            p_printed_name = p.get("printed_name") or p_name
            p_set = (p.get("set") or "").lower()
            p_slug = slugify(p_name)
            p_lang = (p.get("lang") or "en").lower()
            p_printing_slug = f"{p_slug}-{p_set}-{p_lang}" if p_lang != "en" else (f"{p_slug}-{p_set}" if p_set else p.get("id"))
            p_small_url, p_img_url, p_large_url = resolve_card_images(p, background_tasks)
            FLAGS = {
                'en': '🇺🇸', 'ja': '🇯🇵', 'fr': '🇫🇷', 'de': '🇩🇪',
                'es': '🇪🇸', 'it': '🇮🇹', 'zhs': '🇨🇳', 'zht': '🇹🇼',
                'pt': '🇧🇷', 'ru': '🇷🇺', 'ko': '🇰🇷'
            }
            printings.append({
                "id": p.get("id"),
                "printing_slug": p_printing_slug,
                "name": p_name,
                "printed_name": p_printed_name,
                "set_name": p.get("set_name", "Unknown"),
                "set": p_set,
                "collector_number": p.get("collector_number", "N/A"),
                "rarity": p.get("rarity", ""),
                "lang": p_lang,
                "lang_flag": FLAGS.get(p_lang, '🌐'),
                "artist": p.get("artist", "Unknown"),
                "artist_slug": slugify(p.get("artist") or "unknown"),
                "released_at": p.get("released_at", ""),
                "image_url": p_small_url or p_img_url,
                "large_image_url": p_large_url or p_img_url,
                "is_current": (p.get("id") == card.get("id"))
            })

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

        # Group printings by language
        lang_groups = {}
        for p in printings:
            l_code = p.get("lang", "en").lower()
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

        # Sort printings inside each group by released_at descending
        for g in lang_groups.values():
            g["printings_list"].sort(key=lambda x: (not x["is_current"], x.get("released_at") or ""), reverse=False)

        # Sort language groups: English first, then active language, then alphabetical
        sorted_lang_groups = sorted(
            lang_groups.values(),
            key=lambda g: (
                0 if g["lang_code"] == "en" else (1 if g["has_current"] else 2),
                g["lang_name"]
            )
        )
            
    # Load Rulings
    rulings = []
    if oracle_id:
        rulings = list(db["rulings"].find({"oracle_id": oracle_id}).sort("published_at", 1))

    # Mechanics & Tooltips
    mechanics = []
    try:
        mech_cursor = db["mechanics"].find({})
        mechanics_map = {m["slug"]: m for m in mech_cursor}
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

    rendered_response = templates.TemplateResponse(
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
            "similar_cards": []
        }
    )
    # Cache rendered HTML in RAM
    if hasattr(rendered_response, "body") and rendered_response.body:
        RAM_CACHE[cache_key] = rendered_response.body.decode("utf-8")
    return rendered_response

@app.get("/search", response_class=HTMLResponse)
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
            "q": query_str
        }
    )

@app.get("/sets", response_class=HTMLResponse)
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

@app.get("/set/{code}", response_class=HTMLResponse)
async def set_detail(request: Request, code: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    set_code = code.lower()
    cards_cursor = db["cards"].find({"set": set_code}).sort("collector_number", 1).limit(200)
    cards = []
    set_name = set_code.upper()
    
    for doc in cards_cursor:
        set_name = doc.get("set_name") or set_name
        vm = build_card_view_model(doc, db, background_tasks)
        cards.append(vm)
        
    return templates.TemplateResponse(
        request=request,
        name="set_detail.html",
        context={
            "active_nav": "sets",
            "set_doc": {"code": set_code, "name": set_name},
            "total_cards": len(cards),
            "cards": cards
        }
    )

@app.get("/artists", response_class=HTMLResponse)
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

@app.get("/live-gallery", response_class=HTMLResponse)
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

# Live Gallery In-Memory Daily Cache (301 distinct Oracle cards)
_GALLERY_CACHE = {
    "timestamp": 0.0,
    "items": []
}

def get_or_build_gallery_cache(db) -> List[dict]:
    import time, random
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

@app.get("/api/live-gallery/feed")
async def live_gallery_feed():
    import random
    db = get_mongo_db()
    all_cached = get_or_build_gallery_cache(db)
    
    # Return a shuffled slice of 40 cards from the 301 cached Oracle cards
    if all_cached:
        shuffled = random.sample(all_cached, min(40, len(all_cached)))
        return JSONResponse(content={"items": shuffled})
        
    return JSONResponse(content={"items": []})




@app.get("/artist/{slug}", response_class=HTMLResponse)
async def artist_detail(request: Request, slug: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    unslugged = slug.replace('-', ' ')
    pattern = r'^' + r'[\s\W]*'.join(re.escape(w) for w in slug.split('-') if w) + r'$'
    
    query = {"artist": {"$regex": pattern, "$options": "i"}}
    total_count = db["cards"].count_documents(query)
    
    cards_cursor = db["cards"].find(query).sort("released_at", -1).limit(200)
    
    cards = []
    artist_name = unslugged.title()
    for doc in cards_cursor:
        artist_name = doc.get("artist") or artist_name
        vm = build_card_view_model(doc, db, background_tasks)
        cards.append(vm)
        
    return templates.TemplateResponse(
        request=request,
        name="artist_detail.html",
        context={
            "active_nav": "artists",
            "artist_name": artist_name,
            "total_cards": total_count if total_count > 0 else len(cards),
            "cards": cards
        }
    )

@app.get("/api/search-suggest", response_class=HTMLResponse)
async def search_suggest(request: Request, background_tasks: BackgroundTasks, q: Optional[str] = Query(None)):
    if not q or len(q.strip()) < 1:
        return HTMLResponse("")
        
    query_str = q.strip()
    db = get_mongo_db()
    
    pattern = re.compile(f"^{re.escape(query_str)}", re.IGNORECASE)
    results = []
    try:
        cursor = db["cards"].find(
            {"name": pattern, "lang": "en"},
            {"name": 1, "slug": 1, "set": 1, "lang": 1, "mana_cost": 1, "type_line": 1, "id": 1, "image_slug": 1, "raw": 1, "image_uris": 1, "card_faces": 1}
        ).limit(8)
        
        for doc in cursor:
            _, img_url, _ = resolve_card_images(doc, background_tasks)
            d_name = doc.get("name") or "card"
            d_set = (doc.get("set") or "").lower()
            d_slug = slugify(d_name)
            d_printing_slug = f"{d_slug}-{d_set}" if d_set else d_slug
            results.append({
                "name": d_name,
                "slug": d_printing_slug,
                "type_line": doc.get("type_line"),
                "mana_cost": doc.get("mana_cost"),
                "image_url": img_url
            })
    except Exception as e:
        print(f"Error in search suggest: {e}")
        
    return templates.TemplateResponse(
        request=request,
        name="partials/search_results.html",
        context={
            "results": results,
            "query": query_str
        }
    )

@app.get("/api/card/{slug}/lure", response_class=HTMLResponse)
async def card_lure_partial(request: Request, slug: str):
    db = get_mongo_db()
    card = db["cards"].find_one({"$or": [{"slug": slug}, {"slug": slugify(slug)}]})
    if not card:
        return HTMLResponse("")
        
    oracle_id = card.get("oracle_id")
    lure = None
    if oracle_id:
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
            
    return templates.TemplateResponse(
        request=request,
        name="partials/card_lure.html",
        context={
            "lure": lure
        }
    )

@app.get("/api/card/{slug}/similar", response_class=HTMLResponse)
async def card_similar_partial(request: Request, slug: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    card = db["cards"].find_one({"$or": [{"slug": slug}, {"slug": slugify(slug)}]})
    if not card:
        return HTMLResponse("")
        
    oracle_id = card.get("oracle_id")
    similar_cards = []
    if oracle_id:
        try:
            from mtgabyss.similar import calculate_similar_cards
            candidates = calculate_similar_cards(db, oracle_id)
            for c in candidates[:12]:
                _, img_url, _ = resolve_card_images(c, background_tasks)
                similar_cards.append({
                    "name": c.get("name"),
                    "slug": c.get("slug") or slugify(c.get("name")),
                    "image_url": img_url,
                    "score": c.get("similarity_score")
                })
        except Exception as e:
            print(f"Error loading similar cards: {e}")
            
    return templates.TemplateResponse(
        request=request,
        name="partials/similar_cards.html",
        context={
            "similar_cards": similar_cards
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8004,
        reload=True,
        reload_dirs=["templates", "static", "."]
    )
