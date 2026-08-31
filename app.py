import os
import glob
import re
import asyncio
import secrets
import random
import gzip
import time
from typing import Optional, List, Dict, Any, Tuple
import httpx
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Query, BackgroundTasks, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from db_mongo import get_mongo_db, get_old_db
import i18n

app = FastAPI(title="AvaScry", description="Magic: The Gathering Visual Explorer & Strategy Engine")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")

@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    return FileResponse("public/sitemap.xml", media_type="application/xml")

@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return FileResponse("public/robots.txt", media_type="text/plain")

@app.get("/ads.txt", response_class=PlainTextResponse, include_in_schema=False)
async def ads_txt():
    return "google.com, pub-7283717447639840, DIRECT, f08c47fec0942fa0\n"

INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b3901b0f58d0445bb8d15a9e334df58a")

@app.get("/b3901b0f58d0445bb8d15a9e334df58a.txt", response_class=PlainTextResponse, include_in_schema=False)
async def indexnow_key_txt():
    return f"{INDEXNOW_KEY}\n"

async def ping_indexnow(urls: list[str]):
    """Background helper to notify Bing / IndexNow search engines when URLs are published or updated."""
    if not urls:
        return
    payload = {
        "host": "avascry.com",
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://avascry.com/{INDEXNOW_KEY}.txt",
        "urlList": urls[:10000]
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://api.indexnow.org/indexnow", json=payload)
            print(f"[IndexNow] Submitted {len(urls)} URLs. Response status: {resp.status_code}")
    except Exception as e:
        print(f"[IndexNow] Error notifying IndexNow: {e}")

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

# Serve card images with long-lived Cache-Control so Cloudflare caches them at the edge
@app.get("/images/{rest_of_path:path}", include_in_schema=False)
async def serve_image(rest_of_path: str):
    file_path = os.path.join("public", "images", rest_of_path)
    
    # 1. Direct file match on disk
    if os.path.isfile(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

    # 2. Check for missing extensions (.jpg, .webp, .png, .jpeg)
    for ext_try in [".jpg", ".webp", ".png", ".jpeg"]:
        if os.path.isfile(file_path + ext_try):
            file_path = file_path + ext_try
            ext = os.path.splitext(file_path)[1].lower()
            media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
            return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

    # 3. Fuzzy disk match (e.g. /images/normal/ohran-frostfang-ohran-frostfang -> matches on disk with _0.jpg or set suffix)
    parts = rest_of_path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] in ("normal", "large"):
        size_type = parts[0]
        slug_or_name = os.path.splitext(parts[1])[0]
        tokens = [t for t in slug_or_name.split("-") if t]
        
        for end_idx in range(len(tokens), 0, -1):
            prefix = "-".join(tokens[:end_idx])
            pattern = os.path.join("public", "images", size_type, f"{prefix}*")
            matches = glob.glob(pattern)
            valid_files = [m for m in matches if os.path.isfile(m)]
            if valid_files:
                matched_file = valid_files[0]
                ext = os.path.splitext(matched_file)[1].lower()
                media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
                return FileResponse(matched_file, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

        # 4. Fallback to Scryfall API / DB lookup if not on disk at all
        clean_slug = tokens[0] if tokens else slug_or_name
        clean_name = " ".join(tokens)
        try:
            db = get_mongo_db()
            card = db["cards"].find_one({
                "$or": [
                    {"slug": clean_slug},
                    {"image_slug": {"$regex": f"^{re.escape(clean_slug)}", "$options": "i"}},
                    {"name": {"$regex": f"^{re.escape(clean_name)}", "$options": "i"}}
                ]
            })
            if card:
                _, cdn_normal, cdn_large = get_scryfall_direct_uris(card)
                cdn_url = cdn_large if size_type == "large" else cdn_normal
                if cdn_url:
                    dest_save = file_path if file_path.endswith('.jpg') else file_path + '.jpg'
                    asyncio.create_task(_download_and_save_image(cdn_url, dest_save))
                    return RedirectResponse(url=cdn_url, status_code=307)
        except Exception as e:
            print(f"[Image Resolver Error] {e}")

    raise HTTPException(status_code=404)

templates = Jinja2Templates(
    directory="templates",
    context_processors=[
        lambda request: {
            "current_lang": getattr(request.state, "lang", i18n.get_locale(request)),
            "user": request.session.get("user") if hasattr(request, "session") else None
        }
    ]
)
templates.env.globals["t"] = i18n.t
templates.env.globals["LANGUAGES"] = i18n.LANGUAGES
templates.env.globals["get_locale"] = i18n.get_locale

# =========================================================================
# HIGH-SPEED IN-MEMORY RAM CACHE (Auto-flushed Sunday night or at 64GB RAM)
# =========================================================================
RAM_CACHE: Dict[str, Any] = {}
LAST_SUNDAY_FLUSH: Optional[str] = None
MAX_CACHE_ITEMS: int = 200_000 # Max ~8-10 GB RAM footprint (safe guardrail on 128GB box)

def set_ram_cache(key: str, value: Any):
    """Store item in cache with safety ceiling."""
    if len(RAM_CACHE) >= MAX_CACHE_ITEMS:
        # Clear oldest quarter to prevent unbounded growth
        try:
            keys_to_remove = list(RAM_CACHE.keys())[:50_000]
            for k in keys_to_remove:
                RAM_CACHE.pop(k, None)
        except Exception:
            RAM_CACHE.clear()
    RAM_CACHE[key] = value

_DOWNLOAD_SEMAPHORE = None

def get_download_semaphore() -> asyncio.Semaphore:
    """Lazily instantiate Semaphore inside active event loop."""
    global _DOWNLOAD_SEMAPHORE
    if _DOWNLOAD_SEMAPHORE is None:
        _DOWNLOAD_SEMAPHORE = asyncio.Semaphore(4)
    return _DOWNLOAD_SEMAPHORE

def get_ram_usage_gb() -> float:
    """Return process RAM usage in GB."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 ** 3)
    except Exception:
        return 0.0

def check_periodic_cache_flush():
    global LAST_SUNDAY_FLUSH
    try:
        now = datetime.now(timezone.utc)
        is_sunday_night = (now.weekday() == 6 and now.hour >= 23)
        date_key = now.strftime("%Y-%m-%d")
        ram_gb = get_ram_usage_gb()

        if (is_sunday_night and LAST_SUNDAY_FLUSH != date_key) or (ram_gb >= 64.0):
            count = len(RAM_CACHE)
            RAM_CACHE.clear()
            LAST_SUNDAY_FLUSH = date_key
            print(f"[RAM CACHE] Flushed {count} cached items (Reason: {'Sunday weekly reset' if is_sunday_night else f'64GB guardrail reached: {ram_gb:.1f}GB'})")
    except Exception as e:
        print(f"[RAM CACHE] Monitor error: {e}")

# =========================================================================
# HONEYPOT & BOT-TROLLING SHIELD (Gzip Bomb, Socratic Redirect, The Abyss)
# =========================================================================
# Pre-compress 10MB of zeros into ~10KB gzip (inflates heavily in scanner memory)
GZIP_BOMB_PAYLOAD: bytes = gzip.compress(b"0" * (10 * 1024 * 1024), compresslevel=9)

ETHICS_WIKI_URL = "https://en.wikipedia.org/wiki/Ethics"

THE_ABYSS_ASCII_HONEYPOT = """
================================================================================
                           THE ABYSS (Legends)
   "At the beginning of your upkeep, destroy target nonartifact creature bot.
    It cannot be regenerated."
================================================================================
   [HONEYPOT ENGAGED — BOGUS CREDENTIALS DISPATCHED]
   DB_PASSWORD="pwned_by_the_abyss_nice_try"
   AWS_ACCESS_KEY_ID="AKIA_YOU_HAVE_BEEN_BAMBOOZLED_BY_MTGABYSS"
   AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY_NICE_TRY"
   STRIPE_SECRET_KEY="sk_live_enjoy_wasting_your_time_and_compute"
   OPENAI_API_KEY="sk-proj-rickroll-infinite-troll-loop"
   MESSAGE="Your automated scanner has wandered into The Abyss. Have a lovely day."
================================================================================
"""

PROBE_REDIRECT_PATHS = (
    "/wp-admin", "/wp-login", "/admin.php", "/xmlrpc.php", "/phpmyadmin",
    "/pma", "/admin/login", "/administrator", "/wp-content", "/wp-includes"
)

PROBE_SENSITIVE_PATTERNS = (
    "/.env", "/.git", "/.aws", "/.ssh", "/.ds_store", "/config.json",
    "/api/env", "/api/config", "/docker-compose", "/web.config", "/phpinfo"
)

@app.middleware("http")
async def bot_probe_shield_middleware(request: Request, call_next):
    path = request.url.path.lower()

    # 1. CMS / Admin Scanners -> Redirect to Socratic Ethics
    if any(path.startswith(prefix) for prefix in PROBE_REDIRECT_PATHS):
        print(f"[SHIELD] Intercepted CMS exploit scan: {request.url.path} from {request.client.host if request.client else 'unknown'} -> Redirecting to Plato/Ethics")
        return RedirectResponse(url=ETHICS_WIKI_URL, status_code=301)

    # 2. Secret & Config File Scanners (e.g. /.env, /.git, /config.json)
    if any(p in path for p in PROBE_SENSITIVE_PATTERNS) or (path.startswith("/.") and not path.startswith("/.well-known")):
        accept_encoding = request.headers.get("accept-encoding", "").lower()
        print(f"[SHIELD] Intercepted secret hunter scan: {request.url.path} from {request.client.host if request.client else 'unknown'}")

        # If scanner accepts gzip, feed them the gzip memory bomb
        if "gzip" in accept_encoding:
            return Response(
                content=GZIP_BOMB_PAYLOAD,
                status_code=200,
                headers={
                    "Content-Encoding": "gzip",
                    "Content-Type": "text/plain; charset=utf-8",
                    "X-Shield": "The-Abyss-Active"
                }
            )
        
        # Otherwise, deliver HTTP 418 with The Abyss MTG ASCII Trap
        return Response(
            content=THE_ABYSS_ASCII_HONEYPOT.strip(),
            status_code=418,
            media_type="text/plain; charset=utf-8",
            headers={"X-Shield": "The-Abyss-Active"}
        )

    return await call_next(request)

@app.middleware("http")
async def add_localization_context(request: Request, call_next):
    lang = i18n.get_locale(request)
    request.state.lang = lang
    response = await call_next(request)
    if "lang" in request.query_params:
        response.set_cookie(key="mtgabyss_lang", value=lang, max_age=31536000, path="/")
    return response

def get_client_ip(request: Request) -> str:
    """Extract the most accurate client IP possible (Cloudflare -> XFF -> socket)."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

def get_caller_badge(request: Request) -> str:
    """Classify visitor into clear badges for high-signal log monitoring."""
    ua = request.headers.get("user-agent", "").lower()
    cf_country = request.headers.get("cf-ipcountry")
    
    if "googlebot" in ua or "google-inspectiontool" in ua or "feedfetcher-google" in ua:
        return "[Googlebot]"
    if "bingbot" in ua or "bingpreview" in ua:
        return "[Bingbot]"
    if "duckduckbot" in ua:
        return "[DuckDuckBot]"
    if "yandexbot" in ua:
        return "[YandexBot]"
    if "perplexitybot" in ua:
        return "[AI:Perplexity]"
    if "claudebot" in ua or "anthropic-ai" in ua:
        return "[AI:Claude]"
    if "gptbot" in ua or "chatgpt-user" in ua or "oai-searchbot" in ua:
        return "[AI:OpenAI]"
    if "bytespider" in ua:
        return "[AI:ByteDance]"
    if "twitterbot" in ua or "facebookexternalhit" in ua or "discordbot" in ua:
        return "[SocialBot]"
    if "avascry-cachewarmer" in ua:
        return "[CacheWarmer]"
    if any(bot in ua for bot in ("bot", "crawl", "spider", "slurp")):
        return "[Bot:Other]"
        
    if cf_country and cf_country != "XX":
        return f"[User:{cf_country}]"
    return "[User]"

LOG_DIR = "logs"
ACCESS_LOG_PATH = os.path.join(LOG_DIR, "access.log")
os.makedirs(LOG_DIR, exist_ok=True)

@app.middleware("http")
async def request_logger_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    
    ip = get_client_ip(request)
    badge = get_caller_badge(request)
    method = request.method
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    status = response.status_code
    
    log_line = f"{ip:<15} {badge:<15} {status} ({duration_ms:>4.0f}ms) -> {method} {path}"
    print(log_line, flush=True)
    try:
        with open(ACCESS_LOG_PATH, "a", encoding="utf-8") as f_log:
            f_log.write(f"{datetime.now(timezone.utc).isoformat()} {log_line}\n")
    except Exception:
        pass
    return response

def render_template(request: Request, name: str, context: dict):
    """Render template with user session and language context auto-injected."""
    if "request" not in context:
        context["request"] = request
    if "current_lang" not in context:
        context["current_lang"] = getattr(request.state, "lang", i18n.get_locale(request))
    if "user" not in context and hasattr(request, "session"):
        context["user"] = request.session.get("user")
    return templates.TemplateResponse(request=request, name=name, context=context)


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
    """Download single image file asynchronously and save to disk with polite rate limiting."""
    if not url:
        return
    try:
        async with get_download_semaphore():
            # Polite random 11-17ms delay to respect Scryfall CDN guidelines
            await asyncio.sleep(random.uniform(0.011, 0.017))
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

    # Localized Flavor Text for the specific printing
    raw_flavor = card.get("flavor_text") or card.get("raw", {}).get("flavor_text")
    if not raw_flavor and card.get("card_faces"):
        raw_flavor = card["card_faces"][0].get("flavor_text")
    if not raw_flavor and card.get("raw", {}).get("card_faces"):
        raw_flavor = card["raw"]["card_faces"][0].get("flavor_text")
    flavor_text = raw_flavor.strip() if raw_flavor else None

    # Extract Market Prices
    raw_prices = card.get("prices") or card.get("raw", {}).get("prices") or {}
    prices_data = {}
    if raw_prices.get("usd"):
        prices_data["usd"] = raw_prices["usd"]
    if raw_prices.get("usd_foil"):
        prices_data["usd_foil"] = raw_prices["usd_foil"]
    if raw_prices.get("usd_etched"):
        prices_data["usd_etched"] = raw_prices["usd_etched"]
    if raw_prices.get("eur"):
        prices_data["eur"] = raw_prices["eur"]

    return {
        "id": card.get("id"),
        "oracle_id": card.get("oracle_id"),
        "name": c_name,
        "printed_name": c_printed_name,
        "slug": base_slug,
        "printing_slug": printing_slug,
        "flavor_text": flavor_text,
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
        "badges": badges,
        "prices": prices_data,
        "prices_as_of": datetime.now(timezone.utc).strftime("%b %d, %Y")
    }


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    featured = []
    try:
        sample_slugs = ["black-lotus", "atraxa-praetors-voice", "the-ur-dragon", "sol-ring", "rhystic-study", "cyclonic-rift", "demonic-tutor", "mana-crypt", "force-of-will", "lightning-bolt", "smothering-tithe", "doubling-season"]
        cards_cursor = list(db["cards"].find({"slug": {"$in": sample_slugs}, "lang": "en"}).limit(18))
        for c in cards_cursor:
            img = c.get("image_uris")
            if not img and c.get("card_faces"):
                img = c["card_faces"][0].get("image_uris") or {}
            img = img or {}
            c_name = c.get("name") or "Card"
            c_set = (c.get("set") or "").lower()
            c_slug = slugify(c_name)
            p_slug = f"{c_slug}-{c_set}" if c_set else c_slug
            featured.append({
                "name": c_name,
                "slug": p_slug,
                "large_image_url": img.get("large") or img.get("normal") or f"/images/large/{c_slug}.jpg",
                "image_url": img.get("normal") or f"/images/normal/{c_slug}.jpg"
            })
    except Exception as e:
        print(f"Error loading homepage featured cards: {e}")

    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "active_nav": "home",
            "featured_cards": featured,
            "current_lang": lang,
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

def is_safe_redirect(url: Optional[str]) -> bool:
    """Validate that redirect target is strictly a safe local relative path."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.startswith("/") or url.startswith("//") or "\\" in url or "://" in url:
        return False
    if url.startswith("/auth"):
        return False
    return True

def get_base_url(request: Request) -> str:
    """Resolve correct base URL honoring Cloudflare / reverse proxy headers."""
    env_base = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")
    if env_base:
        return env_base
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{proto}://{host}"

@app.get("/auth/login", response_class=HTMLResponse)
async def auth_login_choice(request: Request, next: Optional[str] = None):
    redirect_target = next if is_safe_redirect(next) else "/dashboard"
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "active_nav": "login",
            "current_lang": lang,
            "next_url": redirect_target,
            "auth_error": request.query_params.get("auth_error"),
            "user": request.session.get("user")
        }
    )

@app.get("/auth/discord/login")
async def auth_discord_login(request: Request, next: Optional[str] = None):
    client_id = os.environ.get("DISCORD_CLIENT_ID", "").strip()
    if not client_id:
        return HTMLResponse("<h3>Error: DISCORD_CLIENT_ID is not configured in .env</h3>", status_code=500)
    
    redirect_target = next if is_safe_redirect(next) else "/dashboard"
    redirect_uri = f"{get_base_url(request)}/auth/discord/callback"
    request.session["oauth_next"] = redirect_target
    
    # If already logged in, store linking user ID
    curr_user = request.session.get("user")
    if curr_user and curr_user.get("id"):
        request.session["linking_user_id"] = curr_user["id"]
    
    oauth_state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = oauth_state
    
    auth_url = (
        "https://discord.com/oauth2/authorize?"
        + httpx.QueryParams({
            "client_id": client_id,
            "response_type": "code",
            "scope": "identify email",
            "redirect_uri": redirect_uri,
            "state": oauth_state,
            "prompt": "consent"
        }).__str__()
    )
    return RedirectResponse(url=auth_url, status_code=303)

@app.get("/auth/discord/callback")
async def auth_discord_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error or not code:
        print(f"[Discord Callback] Error received: {error}")
        return RedirectResponse(url=f"/auth/login?auth_error={error or 'cancelled'}", status_code=303)
    
    saved_state = request.session.pop("oauth_state", None)
    if not saved_state or not state or not secrets.compare_digest(saved_state, state):
        print("[Discord Callback] State mismatch detected")
        return RedirectResponse(url="/auth/login?auth_error=invalid_oauth_state", status_code=303)
    
    client_id = os.environ.get("DISCORD_CLIENT_ID", "").strip()
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET", "").strip()
    redirect_uri = f"{get_base_url(request)}/auth/discord/callback"
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://discord.com/api/v10/oauth2/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if token_resp.status_code != 200:
                print(f"[Discord Callback] Token exchange failed: {token_resp.text}")
                return RedirectResponse(url="/auth/login?auth_error=token_exchange_failed", status_code=303)
                
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            
            user_resp = await client.get(
                "https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_resp.status_code != 200:
                print(f"[Discord Callback] User info fetch failed: {user_resp.text}")
                return RedirectResponse(url="/auth/login?auth_error=userinfo_failed", status_code=303)
                
            discord_user = user_resp.json()
            
        discord_id = discord_user.get("id")
        discord_username = discord_user.get("username", "Planeswalker")
        email = discord_user.get("email", "")
        avatar_hash = discord_user.get("avatar")
        picture = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png" if avatar_hash else ""
        
        db = get_mongo_db()
        now = datetime.now(timezone.utc).isoformat()
        
        # Dual-identity merge / link
        linking_user_id = request.session.pop("linking_user_id", None)
        existing_user = None
        if linking_user_id:
            try:
                from bson import ObjectId
                existing_user = db["users"].find_one({"_id": ObjectId(linking_user_id)})
            except Exception:
                pass
                
        if not existing_user:
            query = {"discord_id": discord_id}
            if email:
                query = {"$or": [{"discord_id": discord_id}, {"email": email}]}
            existing_user = db["users"].find_one(query)
            
        if existing_user:
            update_data = {
                "discord_id": discord_id,
                "discord_username": discord_username,
                "updated_at": now
            }
            if picture and not existing_user.get("picture"):
                update_data["picture"] = picture
            if not existing_user.get("name") or existing_user.get("name") == "Magic Player":
                update_data["name"] = discord_username
            if email and not existing_user.get("email"):
                update_data["email"] = email
                
            db["users"].update_one({"_id": existing_user["_id"]}, {"$set": update_data})
            user_doc = db["users"].find_one({"_id": existing_user["_id"]})
        else:
            new_doc = {
                "discord_id": discord_id,
                "discord_username": discord_username,
                "name": discord_username,
                "email": email,
                "picture": picture,
                "created_at": now,
                "updated_at": now
            }
            res = db["users"].insert_one(new_doc)
            user_doc = db["users"].find_one({"_id": res.inserted_id})
            
        request.session["user"] = {
            "id": str(user_doc["_id"]),
            "discord_id": discord_id,
            "discord_username": discord_username,
            "google_sub": user_doc.get("google_sub"),
            "name": user_doc.get("name", discord_username),
            "email": user_doc.get("email", ""),
            "picture": user_doc.get("picture", "")
        }
        
        raw_next = request.session.pop("oauth_next", None)
        next_url = raw_next if is_safe_redirect(raw_next) else "/dashboard"
        return RedirectResponse(url=next_url, status_code=303)
    except Exception as e:
        print(f"[Discord Callback] Exception: {e}")
        return RedirectResponse(url="/auth/login?auth_error=oauth_failed", status_code=303)

@app.get("/auth/google/login")
async def auth_google_login(request: Request, next: Optional[str] = None):
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id or "your-domain" in client_id:
        return HTMLResponse("<h3>Error: GOOGLE_CLIENT_ID is not configured in .env</h3>", status_code=500)
    
    redirect_target = next if is_safe_redirect(next) else "/dashboard"
    redirect_uri = f"{get_base_url(request)}/auth/google/callback"
    request.session["oauth_next"] = redirect_target
    
    # If already logged in, store linking user ID
    curr_user = request.session.get("user")
    if curr_user and curr_user.get("id"):
        request.session["linking_user_id"] = curr_user["id"]
    
    # Generate cryptographic one-time state nonce
    oauth_state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = oauth_state
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + httpx.QueryParams({
            "client_id": client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": redirect_uri,
            "state": oauth_state,
            "access_type": "online",
            "prompt": "select_account"
        }).__str__()
    )
    return RedirectResponse(url=auth_url, status_code=303)

@app.get("/auth/google/callback")
async def auth_google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error or not code:
        print(f"[OAuth Callback] Error parameter received: {error}")
        return RedirectResponse(url=f"/auth/login?auth_error={error or 'cancelled'}", status_code=303)
    
    # Verify state parameter (strictly require both saved state and incoming state)
    saved_state = request.session.pop("oauth_state", None)
    if not saved_state or not state or not secrets.compare_digest(saved_state, state):
        print("[OAuth Callback] State mismatch or missing state detected")
        return RedirectResponse(url="/auth/login?auth_error=invalid_oauth_state", status_code=303)
    
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
            if token_resp.status_code != 200:
                print(f"[OAuth Callback] Token error: {token_resp.text}")
                return RedirectResponse(url="/auth/login?auth_error=token_exchange_failed", status_code=303)

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            
            # Fetch user profile info
            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if user_resp.status_code != 200:
                print(f"[OAuth Callback] Userinfo error: {user_resp.text}")
                return RedirectResponse(url="/auth/login?auth_error=userinfo_failed", status_code=303)

            profile = user_resp.json()
            
        google_sub = profile.get("sub")
        if not google_sub:
            print("[OAuth Callback] Missing Google sub in profile")
            return RedirectResponse(url="/auth/login?auth_error=missing_sub", status_code=303)
            
        email = profile.get("email", "")
        db = get_mongo_db()
        now = datetime.now(timezone.utc).isoformat()
        
        # Dual-identity merge / link
        linking_user_id = request.session.pop("linking_user_id", None)
        existing_user = None
        if linking_user_id:
            try:
                from bson import ObjectId
                existing_user = db["users"].find_one({"_id": ObjectId(linking_user_id)})
            except Exception:
                pass

        if not existing_user:
            query = {"google_sub": google_sub}
            if email:
                query = {"$or": [{"google_sub": google_sub}, {"email": email}]}
            existing_user = db["users"].find_one(query)
        if existing_user:
            update_data = {
                "google_sub": google_sub,
                "email": email or existing_user.get("email", ""),
                "picture": profile.get("picture", existing_user.get("picture", "")),
                "updated_at": now
            }
            if not existing_user.get("name"):
                update_data["name"] = profile.get("name", "Magic Player")
            db["users"].update_one({"_id": existing_user["_id"]}, {"$set": update_data})
            user_doc = db["users"].find_one({"_id": existing_user["_id"]})
        else:
            new_doc = {
                "google_sub": google_sub,
                "email": email,
                "name": profile.get("name", "Magic Player"),
                "picture": profile.get("picture", ""),
                "created_at": now,
                "updated_at": now
            }
            res = db["users"].insert_one(new_doc)
            user_doc = db["users"].find_one({"_id": res.inserted_id})
        
        # Set session
        request.session["user"] = {
            "id": str(user_doc["_id"]),
            "google_sub": google_sub,
            "discord_username": user_doc.get("discord_username"),
            "name": user_doc.get("name", "Magic Player"),
            "email": user_doc.get("email", ""),
            "picture": user_doc.get("picture", "")
        }
        
        raw_next = request.session.pop("oauth_next", None)
        next_url = raw_next if is_safe_redirect(raw_next) else "/dashboard"
        print(f"[OAuth Callback] Successfully authenticated user: {user_doc.get('name')} -> Redirecting to {next_url}")
        return RedirectResponse(url=next_url, status_code=303)
        
    except Exception as e:
        print(f"[OAuth Callback] Exception: {e}")
        return RedirectResponse(url="/auth/login?auth_error=oauth_failed", status_code=303)

@app.get("/auth/logout")
async def auth_logout(request: Request, next: Optional[str] = "/commander"):
    request.session.clear()
    target = next if is_safe_redirect(next) else "/commander"
    return RedirectResponse(url=target, status_code=303)

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

@app.post("/api/deck/{deck_id}/clone")
async def clone_user_deck(deck_id: str, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    db = get_mongo_db()
    original = db["decks"].find_one({"deck_id": deck_id})
    if not original:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    new_deck_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    
    is_owner = (original.get("user_id") == user["id"])
    clone_name = f"{original.get('name', 'Deck')} (Copy)" if is_owner else original.get("name", "Cloned Deck")
    
    cloned_doc = {
        "deck_id": new_deck_id,
        "user_id": user["id"],
        "name": clone_name,
        "commander": original.get("commander", {}),
        "cards": original.get("cards", []),
        "active_query": original.get("active_query", ""),
        "card_count": original.get("card_count", 0),
        "created_at": now,
        "updated_at": now
    }
    db["decks"].insert_one(cloned_doc)
    return JSONResponse({"status": "cloned", "new_deck_id": new_deck_id})

@app.get("/deck/{deck_id}", response_class=HTMLResponse)
async def public_deck_view(deck_id: str, request: Request):
    db = get_mongo_db()
    deck = db["decks"].find_one({"deck_id": deck_id})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found in the Abyss")
        
    user = request.session.get("user")
    is_owner = bool(user and user.get("id") == deck.get("user_id"))
    
    # Creator info: ONLY use Discord username or explicit handle, never Google real names
    discord_handle = None
    try:
        from bson import ObjectId
        creator = db["users"].find_one({"_id": ObjectId(deck.get("user_id"))})
        if creator:
            discord_handle = creator.get("discord_username")
    except Exception:
        pass
        
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="deck_detail.html",
        context={
            "active_nav": "commander",
            "current_lang": lang,
            "deck": deck,
            "is_owner": is_owner,
            "discord_handle": discord_handle,
            "user": user
        }
    )

@app.post("/api/user/settings")
async def update_user_settings(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    body = await request.json()
    new_name = (body.get("name") or "").strip()
    fav_format = (body.get("favorite_format") or "Commander / EDH").strip()
    
    db = get_mongo_db()
    update_fields = {
        "favorite_format": fav_format,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if new_name:
        update_fields["name"] = new_name
        # Update session display name as well
        request.session["user"]["name"] = new_name
        
    from bson import ObjectId
    user_filter = {"_id": ObjectId(user["id"])} if user.get("id") else {"google_sub": user.get("google_sub")}
    db["users"].update_one(
        user_filter,
        {"$set": update_fields}
    )
    return JSONResponse({"status": "updated", "name": new_name or user.get("name", "Player"), "favorite_format": fav_format})

@app.post("/api/saved-cards/toggle")
async def toggle_saved_card(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    body = await request.json()
    oracle_id = body.get("oracle_id")
    card_id = body.get("card_id")
    name = (body.get("name") or "").strip()
    slug = (body.get("slug") or "").strip()
    image_url = (body.get("image_url") or "").strip()
    set_name = (body.get("set_name") or "").strip()
    
    if not name:
        raise HTTPException(status_code=400, detail="Card name is required")
        
    db = get_mongo_db()
    query = {"user_id": user["id"]}
    if oracle_id:
        query["oracle_id"] = oracle_id
    elif card_id:
        query["card_id"] = card_id
    else:
        query["name"] = name
        
    existing = db["saved_cards"].find_one(query)
    if existing:
        db["saved_cards"].delete_one({"_id": existing["_id"]})
        return JSONResponse({"status": "removed", "saved": False})
    else:
        now = datetime.now(timezone.utc).isoformat()
        db["saved_cards"].insert_one({
            "user_id": user["id"],
            "oracle_id": oracle_id,
            "card_id": card_id,
            "name": name,
            "slug": slug,
            "image_url": image_url,
            "set_name": set_name,
            "saved_at": now
        })
        return JSONResponse({"status": "saved", "saved": True})

@app.post("/api/saved-cards/push-to-deck")
async def push_saved_card_to_deck(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    body = await request.json()
    deck_id = body.get("deck_id")
    card_item = body.get("card") # {oracle_id, name, slug, image_url, count}
    
    if not deck_id or not card_item:
        raise HTTPException(status_code=400, detail="deck_id and card are required")
        
    db = get_mongo_db()
    deck = db["decks"].find_one({"deck_id": deck_id, "user_id": user["id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
        
    cards = deck.get("cards", [])
    card_name = card_item.get("name")
    oracle_id = card_item.get("oracle_id")
    
    # Check if already in deck
    found = False
    for c in cards:
        if (oracle_id and c.get("oracle_id") == oracle_id) or (c.get("name", "").lower() == card_name.lower()):
            c["count"] = c.get("count", 1) + 1
            found = True
            break
            
    if not found:
        cards.append({
            "oracle_id": oracle_id,
            "name": card_name,
            "printing_slug": card_item.get("slug") or card_item.get("printing_slug"),
            "image_normal": card_item.get("image_url") or card_item.get("image_normal"),
            "count": card_item.get("count", 1)
        })
        
    now = datetime.now(timezone.utc).isoformat()
    db["decks"].update_one(
        {"deck_id": deck_id, "user_id": user["id"]},
        {
            "$set": {
                "cards": cards,
                "card_count": sum(c.get("count", 1) for c in cards),
                "updated_at": now
            }
        }
    )
    return JSONResponse({"status": "added", "deck_name": deck.get("name")})

@app.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/auth/login?next=/dashboard", status_code=303)
    
    from bson import ObjectId
    db = get_mongo_db()
    user_doc = {}
    if user.get("id"):
        try:
            user_doc = db["users"].find_one({"_id": ObjectId(user["id"])}) or {}
        except Exception:
            pass
    if not user_doc and user.get("google_sub"):
        user_doc = db["users"].find_one({"google_sub": user["google_sub"]}) or {}
    decks = list(db["decks"].find(
        {"user_id": user["id"]}
    ).sort("updated_at", -1))
    saved_cards = list(db["saved_cards"].find(
        {"user_id": user["id"]}
    ).sort("saved_at", -1))
    
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_nav": "dashboard",
            "current_lang": lang,
            "profile": user_doc,
            "decks": decks,
            "deck_count": len(decks),
            "saved_cards": saved_cards,
            "saved_card_count": len(saved_cards)
        }
    )


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

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={"current_lang": lang}
    )

@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="terms.html",
        context={"current_lang": lang}
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
    set_ram_cache(cache_key, suggestions)
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

    # Always fall back to commander similarity when strict token matching returns nothing
    is_fallback = False
    if len(docs) == 0 and oracle_id:
        is_fallback = True
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

        # Final safety net: if no similar_cards either, just return good staples in color
        if len(docs) == 0:
            safety_match = {"lang": "en", "edhrec_rank": {"$lte": 500}}
            if color_identity:
                safety_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
            if oracle_id:
                safety_match["oracle_id"] = {"$ne": oracle_id}
            docs = list(new_db["cards"].aggregate([
                {"$match": safety_match},
                {"$sort": {"edhrec_rank": 1}},
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
            ]))

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

    response_data = {"cards": results, "query": theme, "total": len(results), "fallback": is_fallback}
    set_ram_cache(cache_key, response_data)
    return JSONResponse(response_data)



@app.get("/card/{slug}")
async def card_name_shortcut(request: Request, slug: str):
    """Clean shortcut redirecting /card/<name> to the primary/earliest Oracle printing of that card."""
    db = get_mongo_db()
    unslugged = slug.replace('-', ' ')
    pattern = slug_to_name_regex(slug)
    
    # 1. Match card by slug, exact name, full regex (including //), or front face prefix
    card = db["cards"].find_one({
        "$or": [
            {"slug": slug},
            {"name": slug},
            {"name": unslugged},
            {"name": pattern},
            {"name": re.compile(r"^" + re.escape(unslugged) + r"\s*//", re.I)},
            {"card_faces.0.name": pattern}
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

def format_card_markdown(card_doc: dict, printings_count: int = 1, rulings: list = None) -> str:
    """Format structured, token-efficient Markdown for AI agents and LLMs."""
    name = card_doc.get("name", "Unknown Card")
    mana_cost = card_doc.get("mana_cost") or "N/A"
    cmc = card_doc.get("cmc", 0.0)
    type_line = card_doc.get("type_line", "")
    oracle_text = card_doc.get("oracle_text") or "(No Oracle text)"
    flavor_text = card_doc.get("flavor_text")
    power = card_doc.get("power")
    toughness = card_doc.get("toughness")
    loyalty = card_doc.get("loyalty")
    set_name = card_doc.get("set_name", "")
    set_code = (card_doc.get("set") or "").upper()
    collector_number = card_doc.get("collector_number", "")
    rarity = (card_doc.get("rarity") or "").capitalize()
    artist = card_doc.get("artist", "Unknown")
    legalities = card_doc.get("legalities", {})
    keywords = card_doc.get("keywords", [])

    lines = [
        f"# {name}",
        f"- **Mana Cost:** `{mana_cost}` (CMC: {cmc:g})",
        f"- **Type:** {type_line}",
    ]

    if power is not None and toughness is not None:
        lines.append(f"- **Power/Toughness:** {power}/{toughness}")
    if loyalty is not None:
        lines.append(f"- **Starting Loyalty:** {loyalty}")

    if keywords:
        lines.append(f"- **Keywords:** {', '.join(keywords)}")

    lines.append(f"\n## Oracle Text\n{oracle_text}\n")

    if flavor_text:
        lines.append(f"> *{flavor_text}*\n")

    lines.append("## Printing Details")
    lines.append(f"- **Set:** {set_name} ({set_code}) #{collector_number}")
    lines.append(f"- **Rarity:** {rarity}")
    lines.append(f"- **Artist:** {artist}")
    if printings_count > 1:
        lines.append(f"- **Total Printings:** {printings_count} across all editions")

    # Format Key Legalities
    key_formats = ["commander", "standard", "modern", "pioneer", "legacy", "vintage", "pauper"]
    leg_list = [f"{f.capitalize()}: `{legalities.get(f, 'not_legal')}`" for f in key_formats if f in legalities]
    if leg_list:
        lines.append(f"\n## Format Legalities\n" + " | ".join(leg_list))

    if rulings:
        lines.append(f"\n## Official Rulings")
        for r in rulings[:5]:
            pub = r.get("published_at", "")
            comment = r.get("comment", "")
            lines.append(f"- *({pub})* {comment}")

    return "\n".join(lines)

def slug_to_name_regex(slug: str) -> re.Pattern:
    """Build a regex that matches card names regardless of stripped apostrophes, commas, dashes, ampersands, or // slashes."""
    clean = slug.strip().lower()
    # Replace & or and representations
    clean = clean.replace('&', '-')
    chars = [re.escape(c) if c != '-' else r'[\s\-\'\,\.\:\/\&]+' for c in clean]
    pattern_str = r'^[\'\,\.\:\s\-\/\&]*' + r'[\'\,\.\:\s\-\/\&]*'.join(chars) + r'[\'\,\.\:\s\-\/\&]*$'
    return re.compile(pattern_str, re.IGNORECASE)

KNOWN_LANG_CODES = {'ja', 'de', 'fr', 'es', 'it', 'pt', 'ru', 'ko', 'zhs', 'zht'}

@app.get("/printing/{identifier}")
async def printing_detail(request: Request, identifier: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    card = None

    # 1. Try match by UUID
    card = db["cards"].find_one({"id": identifier})

    # 2. Try match by <slug>-<set>-<lang> (only if last token is an actual language code)
    if not card and '-' in identifier:
        parts = identifier.split('-')
        if len(parts) >= 3 and parts[-1].lower() in KNOWN_LANG_CODES:
            possible_lang = parts[-1].lower()
            possible_set = parts[-2].lower()
            card_slug = "-".join(parts[:-2])
            pattern = slug_to_name_regex(card_slug)
            
            card = db["cards"].find_one({
                "set": possible_set,
                "lang": possible_lang,
                "$or": [
                    {"slug": card_slug},
                    {"name": pattern},
                    {"card_faces.0.name": pattern}
                ]
            })

        # 3. Try match by <slug>-<set>
        if not card and len(parts) >= 2:
            card_slug, set_code = "-".join(parts[:-1]), parts[-1].lower()
            pattern = slug_to_name_regex(card_slug)
            card = db["cards"].find_one({
                "set": set_code,
                "$or": [
                    {"slug": card_slug},
                    {"name": pattern},
                    {"card_faces.0.name": pattern}
                ]
            })

    # 4. Fallback match by name or slug across entire collection
    if not card:
        pattern = slug_to_name_regex(identifier)
        card = db["cards"].find_one({
            "$or": [
                {"slug": identifier},
                {"name": pattern},
                {"card_faces.0.name": pattern}
            ]
        })

    if not card:
        raise HTTPException(status_code=404, detail="Printing not found in the Abyss")
        
    oracle_id = card.get("oracle_id")
    card_vm = build_card_view_model(card, db, background_tasks)
    
    # Load All Other Printings for this Oracle ID
    printings = []
    sorted_lang_groups = []
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

    # Find 4 Highly Relevant Synergistic / Mechanically Similar Cards (Quick memory-only or indexed projection)
    similar_cards = []
    try:
        colors = card.get("color_identity", [])
        keywords = card.get("keywords", [])
        
        sim_query = {
            "lang": "en",
            "oracle_id": {"$ne": oracle_id}
        }
        if keywords:
            sim_query["keywords"] = keywords[0]
        elif colors:
            sim_query["color_identity"] = colors[0]

        sim_cursor = db["cards"].find(
            sim_query,
            {"name": 1, "slug": 1, "set": 1, "set_name": 1, "image_uris": 1, "type_line": 1, "oracle_id": 1}
        ).limit(8)

        seen_oracles = set()
        for sc in sim_cursor:
            sc_oid = sc.get("oracle_id")
            if sc_oid and sc_oid not in seen_oracles:
                seen_oracles.add(sc_oid)
                sc_name = sc.get("name") or "Card"
                sc_set = (sc.get("set") or "").lower()
                sc_slug = slugify(sc_name)
                sc_img = sc.get("image_uris")
                if not sc_img and sc.get("card_faces"):
                    sc_img = sc["card_faces"][0].get("image_uris") or {}
                sc_img = sc_img or {}
                similar_cards.append({
                    "name": sc_name,
                    "slug": f"{sc_slug}-{sc_set}" if sc_set else sc_slug,
                    "set_name": sc.get("set_name") or "",
                    "type_line": sc.get("type_line") or "",
                    "image_url": sc_img.get("normal") or f"/images/normal/{sc_slug}.jpg",
                    "large_image_url": sc_img.get("large") or sc_img.get("normal") or f"/images/large/{sc_slug}.jpg"
                })
                if len(similar_cards) >= 4:
                    break
    except Exception as e:
        pass

    # Content Negotiation: Check for AI Agent / LLM requesting Markdown
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()
    if "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
        md_text = format_card_markdown(card, printings_count=len(printings), rulings=rulings)
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Vary": "Accept",
                "X-Markdown-Tokens": str(len(md_text.split())),
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    # Check if card is saved in user stash
    user = request.session.get("user")
    is_saved = False
    if user and oracle_id:
        try:
            is_saved = bool(db["saved_cards"].find_one({"user_id": user["id"], "oracle_id": oracle_id}))
        except Exception:
            is_saved = False

    return templates.TemplateResponse(
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
            "similar_cards": similar_cards,
            "is_saved": is_saved
        }
    )

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
            "q": query_str,
            "noindex": True
        },
        headers={"X-Robots-Tag": "noindex, follow"}
    )

@app.get("/similar/{slug}", response_class=HTMLResponse)
async def similar_cards_page(slug: str, request: Request, background_tasks: BackgroundTasks):
    """Deep similarity search: finds top 31 mechanically similar cards to the given card slug."""
    db = get_mongo_db()
    pattern = slug_to_name_regex(slug)
    card = db["cards"].find_one({"$or": [{"slug": slug}, {"name": pattern}]})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
        
    oracle_id = card.get("oracle_id")
    colors = card.get("color_identity", [])
    keywords = card.get("keywords", [])
    type_line = card.get("type_line", "")
    card_name = card.get("name") or "Card"
    
    sim_query = {
        "lang": "en",
        "oracle_id": {"$ne": oracle_id},
        "layout": {"$in": ["normal", "saga", "class", "leveler", "adventure"]}
    }
    
    or_clauses = []
    if keywords:
        or_clauses.append({"keywords": {"$in": keywords[:4]}})
    
    main_type = "Creature" if "Creature" in type_line else ("Artifact" if "Artifact" in type_line else ("Enchantment" if "Enchantment" in type_line else ("Instant" if "Instant" in type_line else "Sorcery")))
    if colors:
        or_clauses.append({"color_identity": {"$in": colors}})
    else:
        or_clauses.append({"keywords": {"$exists": True, "$ne": []}})

    if or_clauses:
        sim_query["$or"] = or_clauses

    sim_cursor = list(db["cards"].find(
        sim_query,
        {"name": 1, "slug": 1, "set": 1, "set_name": 1, "image_uris": 1, "type_line": 1, "mana_cost": 1, "oracle_id": 1}
    ).limit(50))

    results = []
    seen_oracles = set()
    for sc in sim_cursor:
        sc_oid = sc.get("oracle_id")
        if sc_oid and sc_oid not in seen_oracles:
            seen_oracles.add(sc_oid)
            sc_name = sc.get("name") or "Card"
            sc_set = (sc.get("set") or "").lower()
            sc_slug = slugify(sc_name)
            sc_img = sc.get("image_uris")
            if not sc_img and sc.get("card_faces"):
                sc_img = sc["card_faces"][0].get("image_uris") or {}
            sc_img = sc_img or {}
            results.append({
                "name": sc_name,
                "slug": f"{sc_slug}-{sc_set}" if sc_set else sc_slug,
                "image_url": sc_img.get("normal") or f"/images/normal/{sc_slug}.jpg",
                "large_image_url": sc_img.get("large") or sc_img.get("normal") or f"/images/large/{sc_slug}.jpg",
                "type_line": sc.get("type_line"),
                "mana_cost": sc.get("mana_cost")
            })
            if len(results) >= 31:
                break

    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "active_nav": "explore",
            "featured_cards": results,
            "current_lang": lang,
            "q": f"Similar to {card_name}"
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

@app.get("/set/{code}")
async def set_detail(request: Request, code: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    set_code = code.lower()
    cards_cursor = db["cards"].find({"set": set_code, "lang": "en"}).sort("collector_number", 1)
    cards = []
    set_name = set_code.upper()
    
    for doc in cards_cursor:
        set_name = doc.get("set_name") or set_name
        vm = build_card_view_model(doc, db, background_tasks)
        cards.append(vm)

    # Fallback if no English cards found (e.g. foreign-only set)
    if not cards:
        cards_cursor = db["cards"].find({"set": set_code}).sort("collector_number", 1).limit(200)
        for doc in cards_cursor:
            set_name = doc.get("set_name") or set_name
            vm = build_card_view_model(doc, db, background_tasks)
            cards.append(vm)

    # Content Negotiation for AI Agents (Accept: text/markdown or ?format=md)
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()
    if "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
        md_lines = [
            f"# {set_name} ({set_code.upper()})",
            f"**Total Printings:** {len(cards)}\n",
            "| # | Card Name | Type | Rarity | Mana Cost |",
            "|---|-----------|------|--------|-----------|"
        ]
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
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )
        
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




@app.get("/artist/{slug}")
async def artist_detail(request: Request, slug: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    unslugged = slug.replace('-', ' ')
    artist_name = unslugged.title()
    
    # 1. Fast exact match using index
    query_exact = {"artist": artist_name, "lang": "en"}
    cards_cursor = list(db["cards"].find(
        query_exact,
        {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "released_at": 1, "rarity": 1, "type_line": 1, "image_uris": 1, "image_slug": 1, "artist": 1}
    ).sort("released_at", -1).limit(60))
    
    # 2. Fallback to regex if exact title didn't hit
    if not cards_cursor:
        pattern = r'^' + r'[\s\W]*'.join(re.escape(w) for w in slug.split('-') if w) + r'$'
        query_regex = {"artist": {"$regex": pattern, "$options": "i"}, "lang": "en"}
        cards_cursor = list(db["cards"].find(
            query_regex,
            {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "released_at": 1, "rarity": 1, "type_line": 1, "image_uris": 1, "image_slug": 1, "artist": 1}
        ).sort("released_at", -1).limit(60))

    if not cards_cursor:
        pattern = r'^' + r'[\s\W]*'.join(re.escape(w) for w in slug.split('-') if w) + r'$'
        query_all = {"artist": {"$regex": pattern, "$options": "i"}}
        cards_cursor = list(db["cards"].find(
            query_all,
            {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "released_at": 1, "rarity": 1, "type_line": 1, "image_uris": 1, "image_slug": 1, "artist": 1}
        ).sort("released_at", -1).limit(60))
    
    cards = []
    for doc in cards_cursor:
        artist_name = doc.get("artist") or artist_name
        c_name = doc.get("name") or "Card"
        c_set = (doc.get("set") or "").lower()
        c_slug = slugify(c_name)
        c_imgs = doc.get("image_uris")
        if not c_imgs and doc.get("card_faces"):
            c_imgs = doc["card_faces"][0].get("image_uris") or {}
        c_imgs = c_imgs or {}
        img_url = c_imgs.get("normal") or (f"/images/normal/{doc.get('image_slug')}.jpg" if doc.get("image_slug") else f"/images/normal/{c_slug}.jpg")
        large_img_url = c_imgs.get("large") or img_url
        cards.append({
            "name": c_name,
            "set": c_set,
            "set_name": doc.get("set_name") or c_set.upper(),
            "collector_number": doc.get("collector_number") or "",
            "rarity": doc.get("rarity") or "",
            "type_line": doc.get("type_line") or "",
            "released_at": doc.get("released_at") or "",
            "printing_slug": f"{c_slug}-{c_set}" if c_set else c_slug,
            "image_url": img_url,
            "large_image_url": large_img_url
        })

    # Content Negotiation for AI Agents (Accept: text/markdown or ?format=md)
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()
    if "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
        md_lines = [
            f"# Magic: The Gathering Cards Illustrated by {artist_name}",
            f"**Total Artworks:** {len(cards)}\n",
            "| Card Name | Set | Type | Rarity | Released |",
            "|-----------|-----|------|--------|----------|"
        ]
        for c in cards:
            c_name = c.get("name", "")
            c_set = (c.get("set") or "").upper()
            c_type = c.get("type_line", "")
            c_rarity = (c.get("rarity") or "").capitalize()
            c_rel = c.get("released_at") or "-"
            md_lines.append(f"| [{c_name}](https://avascry.com/printing/{c.get('printing_slug')}) | {c_set} | {c_type} | {c_rarity} | {c_rel} |")

        md_text = "\n".join(md_lines)
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Vary": "Accept",
                "X-Markdown-Tokens": str(len(md_text.split())),
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )
        
    return templates.TemplateResponse(
        request=request,
        name="artist_detail.html",
        context={
            "active_nav": "artists",
            "artist_name": artist_name,
            "artist_slug": slug,
            "total_cards": len(cards),
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
        access_log=False,
        reload_dirs=["templates", "static"],
        reload_includes=["*.py", "*.html", "*.css", "*.js"]
    )
