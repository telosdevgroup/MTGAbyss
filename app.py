import os
import glob
import re
import json
import asyncio
import secrets
import random
import gzip
import time
import socket
import threading
import httpx
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import uuid
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
load_dotenv()

# Silence Windows asyncio proactor WinError 10054 on sudden client disconnects
if os.name == 'nt':
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _orig_call_conn_lost = _ProactorBasePipeTransport._call_connection_lost
        def _silent_conn_lost(self, exc=None):
            try:
                if getattr(self, '_sock', None) is not None:
                    self._sock.shutdown(socket.SHUT_RDWR)
            except (ConnectionResetError, OSError):
                pass
            try:
                _orig_call_conn_lost(self, exc)
            except (ConnectionResetError, OSError):
                pass
        _ProactorBasePipeTransport._call_connection_lost = _silent_conn_lost
    except Exception:
        pass

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

@app.get("/sitemap-{name}.xml", include_in_schema=False)
async def sub_sitemap_xml(name: str):
    file_path = os.path.join("public", f"sitemap-{name}.xml")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/xml")
    return PlainTextResponse("Sitemap not found", status_code=404)

@app.get("/sitemap.html", include_in_schema=False)
async def sitemap_html():
    return FileResponse("public/sitemap.html", media_type="text/html; charset=utf-8")

@app.get("/sitemaps/{filename}", include_in_schema=False)
async def sitemaps_file(filename: str):
    file_path = os.path.join("public", "sitemaps", filename)
    if os.path.exists(file_path):
        if filename.endswith(".md"):
            return FileResponse(file_path, media_type="text/markdown; charset=utf-8")
        return FileResponse(file_path, media_type="text/html; charset=utf-8")
    return PlainTextResponse("Sitemap not found", status_code=404)

@app.get("/sitemap.md", include_in_schema=False)
async def sitemap_md():
    return FileResponse("public/sitemap.md", media_type="text/markdown; charset=utf-8")

@app.get("/rules.md", include_in_schema=False)
async def rules_md():
    return FileResponse("public/rules.md", media_type="text/markdown; charset=utf-8", headers={"Link": '</rules.json>; rel="alternate"; type="application/json"'})

@app.get("/rules.json", include_in_schema=False)
async def rules_json():
    return FileResponse("public/rules.json", media_type="application/json", headers={"Link": '</rules.md>; rel="alternate"; type="text/markdown"'})

@app.get("/legalities.md", include_in_schema=False)
async def legalities_md():
    return FileResponse("public/legalities.md", media_type="text/markdown; charset=utf-8", headers={"Link": '</legalities.json>; rel="alternate"; type="application/json"'})

@app.get("/legalities.json", include_in_schema=False)
async def legalities_json():
    return FileResponse("public/legalities.json", media_type="application/json", headers={"Link": '</legalities.md>; rel="alternate"; type="text/markdown"'})

@app.get("/sets.md", include_in_schema=False)
async def sets_md():
    return FileResponse("public/sets.md", media_type="text/markdown; charset=utf-8")

@app.get("/.well-known/ai-content", include_in_schema=False)
async def well_known_ai_content():
    return FileResponse("public/.well-known/ai-content", media_type="text/plain; charset=utf-8")

@app.get("/manifest.json", include_in_schema=False)
async def manifest_json():
    return FileResponse("public/manifest.json", media_type="application/manifest+json")

@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return FileResponse("public/robots.txt", media_type="text/plain")

@app.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    return FileResponse("public/llms.txt", media_type="text/plain; charset=utf-8")

@app.get("/heartbeat.txt", include_in_schema=False)
async def heartbeat_txt():
    return FileResponse("public/heartbeat.txt", media_type="text/plain; charset=utf-8")

@app.get("/vector/{identifier}", include_in_schema=False)
@app.get("/vector/{identifier}.json", include_in_schema=False)
async def vector_embedding(identifier: str):
    """Expose raw 4096-dimensional Qwen 8B vector embedding for a card."""
    clean_id = identifier.lower().replace(".json", "").strip()
    if not clean_id or clean_id in ("", ".", "..", ".md", ".json"):
        raise HTTPException(status_code=404, detail="Vector embedding not found")

    db = get_mongo_db()

    # 1. Match by oracle_id or slug in card_embeddings_8b
    doc = db["card_embeddings_8b"].find_one({
        "$or": [
            {"oracle_id": clean_id},
            {"slug": clean_id},
            {"card_name": {"$regex": f"^{re.escape(clean_id.replace('-', ' '))}$", "$options": "i"}}
        ]
    })

    # 2. Fallback via cards collection
    if not doc:
        pattern = slug_to_name_regex(clean_id)
        card_doc = db["cards"].find_one({"$or": [{"slug": clean_id}, {"name": pattern}]})
        if card_doc and card_doc.get("oracle_id"):
            doc = db["card_embeddings_8b"].find_one({"oracle_id": card_doc["oracle_id"]})

    if not doc:
        raise HTTPException(status_code=404, detail="Vector embedding not found")

    oracle_id = doc.get("oracle_id")
    card_name = doc.get("card_name") or clean_id.replace('-', ' ').title()
    card_slug = doc.get("slug") or slugify(card_name)
    embedding = doc.get("embedding", [])

    return JSONResponse(
        content={
            "name": card_name,
            "oracle_id": oracle_id,
            "slug": card_slug,
            "model": doc.get("embedding_model") or "Qwen/Qwen2.5-8B-Instruct",
            "dimensions": len(embedding) or 4096,
            "version": doc.get("embedding_version") or "1.0",
            "links": {
                "vector": f"https://avascry.com/vector/{card_slug}.json",
                "similar": f"https://avascry.com/similar/{card_slug}.json",
                "html": f"https://avascry.com/card/{card_slug}",
                "markdown": f"https://avascry.com/similar/{card_slug}.md"
            },
            "embedding": embedding
        },
        headers={
            "Vary": "Accept",
            "Link": f'</similar/{card_slug}.json>; rel="related"; type="application/json"',
            "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
        }
    )

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

# In-memory prefix index for O(1) resolution of multi-face, art-series, and extensionless card slugs
IMAGE_PREFIX_MAP = {"normal": {}, "large": {}}

def build_image_prefix_index():
    """Build in-memory prefix hash table in background thread on startup (takes ~1s for 340k files)."""
    for size_type in ("normal", "large"):
        folder = os.path.join("public", "images", size_type)
        if not os.path.isdir(folder):
            continue
        try:
            m = {}
            for f in os.listdir(folder):
                if f.endswith((".jpg", ".png", ".webp")):
                    base = os.path.splitext(f)[0]
                    m[base] = f
                    parts = f.split("-")
                    for i in range(1, len(parts)):
                        prefix = "-".join(parts[:i])
                        if prefix not in m:
                            m[prefix] = f
            IMAGE_PREFIX_MAP[size_type] = m
            print(f"[Image Index] Cached {len(m):,} prefix entries for {size_type} in RAM.")
        except Exception as e:
            print(f"[Image Index Error] {e}")

threading.Thread(target=build_image_prefix_index, daemon=True).start()

# Serve card images with long-lived Cache-Control so Cloudflare caches them at the edge
@app.get("/images/{rest_of_path:path}", include_in_schema=False)
async def serve_image(rest_of_path: str):
    file_path = os.path.join("public", "images", rest_of_path)
    
    # 1. Direct O(1) file match on disk
    if os.path.isfile(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

    # 2. Fast O(1) checks for missing extensions and multi-face suffixes
    for ext_try in [".jpg", ".webp", ".png", ".jpeg", "_0.jpg", "_1.jpg"]:
        candidate = file_path + ext_try
        if os.path.isfile(candidate):
            ext = os.path.splitext(candidate)[1].lower()
            media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
            return FileResponse(candidate, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

    # 3. Instant in-memory prefix lookup (resolves murder-murder, cecil-dark-knight...)
    parts = rest_of_path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] in ("normal", "large"):
        size_type = parts[0]
        slug_or_name = os.path.splitext(parts[1])[0]
        
        matched_filename = IMAGE_PREFIX_MAP.get(size_type, {}).get(slug_or_name)
        if matched_filename:
            target_path = os.path.join("public", "images", size_type, matched_filename)
            if os.path.isfile(target_path):
                ext = os.path.splitext(target_path)[1].lower()
                media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
                return FileResponse(target_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

        # 4. Fallback indexed lookup if card is completely un-cached
        clean_name = slug_or_name.replace("-", " ").title()

        def _lookup_card():
            db = get_mongo_db()
            return db["cards"].find_one(
                {"$or": [{"slug": slug_or_name}, {"name": clean_name}]},
                {"image_uris": 1, "card_faces": 1, "raw": 1}
            )

        try:
            card = await asyncio.to_thread(_lookup_card)
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
        # Trim oldest half to preserve warm buffer while reclaiming memory
        try:
            half_size = len(RAM_CACHE) // 2
            keys_to_remove = list(RAM_CACHE.keys())[:half_size]
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
    """Gently trim oldest 50% of cache on Sunday nights or when RAM hits 48GB soft-cap."""
    global LAST_SUNDAY_FLUSH
    try:
        now = datetime.now(timezone.utc)
        is_sunday_night = (now.weekday() == 6 and now.hour >= 23)
        date_key = now.strftime("%Y-%m-%d")
        ram_gb = get_ram_usage_gb()

        if (is_sunday_night and LAST_SUNDAY_FLUSH != date_key) or (ram_gb >= 48.0):
            total_items = len(RAM_CACHE)
            if total_items > 500:
                half_count = total_items // 2
                keys_to_drop = list(RAM_CACHE.keys())[:half_count]
                for k in keys_to_drop:
                    RAM_CACHE.pop(k, None)
                LAST_SUNDAY_FLUSH = date_key
                reason = "Sunday weekly trim" if is_sunday_night else f"48GB soft-cap reached ({ram_gb:.1f}GB)"
                print(f"[RAM CACHE] Trimmed oldest {len(keys_to_drop):,} items. Kept {len(RAM_CACHE):,} hot entries warm (Reason: {reason})")
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

PROBE_KEYWORDS = (
    "wp-", "xmlrpc", "wlwmanifest", "wordpress", "phpmyadmin", "pma",
    "administrator", "setup.php", "install.php", "eval-stdin", "phpunit",
    "thinkphp", "autodiscover", "webdav", "telescope", "alfa-rex",
    "wso.php", "shell.php", "c99.php", "b374k", "cgi-bin", "wp1", "wp2"
)

PROBE_SENSITIVE_PATTERNS = (
    ".env", ".git", ".aws", ".ssh", ".ds_store", "config.json",
    "api/env", "api/config", "docker-compose", "web.config", "phpinfo"
)

@app.middleware("http")
async def bot_probe_shield_middleware(request: Request, call_next):
    raw_path = request.url.path.lower()
    norm_path = re.sub(r'/+', '/', raw_path)

    # 1. CMS & WordPress Exploit Scanners -> Trap & Honeypot
    is_cms_probe = any(k in norm_path for k in PROBE_KEYWORDS)
    is_sensitive_probe = any(p in norm_path for p in PROBE_SENSITIVE_PATTERNS) or (norm_path.startswith("/.") and not norm_path.startswith("/.well-known"))

    if is_cms_probe or is_sensitive_probe:
        client_ip = get_client_ip(request)
        accept_encoding = request.headers.get("accept-encoding", "").lower()
        print(f"[SHIELD] Intercepted malicious probe: {raw_path} from {client_ip} -> Honeypot engaged")

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
WATCHLIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "watchlist.json")
WATCHLIST = {}
try:
    if os.path.exists(WATCHLIST_PATH):
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f_w:
            WATCHLIST = json.load(f_w)
except Exception:
    pass

def get_caller_badge(request: Request) -> str:
    """Classify visitor into clear badges for high-signal log monitoring."""
    ua = request.headers.get("user-agent", "").lower()
    cf_country = request.headers.get("cf-ipcountry")
    ip = get_client_ip(request)
    
    # 0. Check IP Watchlist
    if ip in WATCHLIST:
        return WATCHLIST[ip].get("badge", "[Watchlist]")
    
    # 1. Real-Time Live AI User Grounding Prompts (The Holy Grail)
    if "claude-user" in ua:
        return "[Claude-User]"
    if "chatgpt-user" in ua:
        return "[ChatGPT-User]"
    if "perplexity-user" in ua:
        return "[Perplexity-User]"
    if "claude-searchbot" in ua or "claude-search" in ua:
        return "[Claude-Search]"
    if "oai-searchbot" in ua or "oai-search" in ua:
        return "[OAI-Search]"

    # 2. Anthropic PBC / ClaudeBot Bulk Training
    anthropic_prefixes = ("216.73.216.", "216.73.217.", "216.73.218.", "216.73.219.")
    if any(ip.startswith(p) for p in anthropic_prefixes) or any(c in ua for c in ("claudebot", "anthropic-ai", "claude-web", "claude")):
        return "[ClaudeBot]"

    # 3. Google IP subnets & User-Agents
    google_prefixes = ("66.249.", "64.233.", "72.14.", "66.102.", "209.85.", "142.250.", "172.217.", "172.253.", "108.177.", "74.125.")
    if any(ip.startswith(p) for p in google_prefixes) or any(g in ua for g in ("googlebot", "google-inspectiontool", "feedfetcher-google", "google-read-aloud", "googleother")):
        if "googlebot-image" in ua or "image" in ua:
            return "[Googlebot-Image]"
        return "[Googlebot]"

    # 4. Bing / Microsoft IP subnets & User-Agents
    bing_prefixes = ("40.77.", "157.55.", "20.171.", "13.66.", "52.167.", "20.36.", "20.247.")
    if any(ip.startswith(p) for p in bing_prefixes) or any(b in ua for b in ("bingbot", "bingpreview", "msnbot")):
        return "[Bingbot]"

    # 5. AI Training, Retrieval & Search Agents
    if any(p in ua for p in ("perplexity", "perplexitybot", "ppx")):
        return "[Perplexity]"
    if any(o in ua for o in ("gptbot", "openai")):
        return "[GPTBot]"
    if any(b in ua for b in ("bytespider", "bytedance")):
        return "[ByteSpider]"
    if any(a in ua for a in ("applebot", "applebot-extended", "apple-search")):
        return "[Applebot]"
    if "amazonbot" in ua:
        return "[Amazonbot]"
    if any(c in ua for c in ("cohere-ai", "cohere")):
        return "[Cohere]"
    if any(d in ua for d in ("deepseek", "mistral")):
        return "[AI:Other]"

    # 4. Search Engines & Web Crawlers
    if "duckduckbot" in ua:
        return "[Crawler:DuckDuckGo]"
    if "yandexbot" in ua:
        return "[Crawler:Yandex]"
    if "baiduspider" in ua:
        return "[Crawler:Baidu]"
    if "sogou" in ua:
        return "[Crawler:Sogou]"
    if "seznam" in ua:
        return "[Crawler:Seznam]"

    # 5. Social Media Embed & Link Preview Crawlers
    if "discordbot" in ua:
        return "[Social:Discord]"
    if "twitterbot" in ua:
        return "[Social:Twitter]"
    if "facebookexternalhit" in ua or "meta-externalagent" in ua:
        return "[Social:Meta]"
    if "telegrambot" in ua:
        return "[Social:Telegram]"

    # 6. SEO & Commercial Data Scrapers
    if "ahrefsbot" in ua:
        return "[Scraper:Ahrefs]"
    if "semrushbot" in ua:
        return "[Scraper:Semrush]"
    if "dotbot" in ua:
        return "[Scraper:DotBot]"
    if "mj12bot" in ua:
        return "[Scraper:MJ12]"

    if "avascry-cachewarmer" in ua:
        return "[CacheWarmer]"
        
    path_req = request.url.path.lower()
    if any(p in path_req for p in ("/ads.txt", "/app-ads.txt", "/sellers.json", "/security.txt")):
        return "[Scanner:Ad/Sec]"

    if any(s in ua for s in ("python", "requests", "aiohttp", "curl", "wget", "httpclient", "go-http-client", "node-fetch", "urllib", "axios", "postman")):
        return "[Dev:Script]"

    if any(bot in ua for bot in ("spider", "crawl", "slurp", "fetcher", "headless", "bot")):
        return "[Cloud:Spider]"
        
    if cf_country and cf_country != "XX":
        return f"[Browser:{cf_country}]"
    return "[Browser:Direct]"

LOG_DIR = r"C:\avascry_data\logs"
ACCESS_LOG_PATH = os.path.join(LOG_DIR, "access.log")
os.makedirs(LOG_DIR, exist_ok=True)

@app.middleware("http")
async def request_logger_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    
    ip = get_client_ip(request)
    badge = get_caller_badge(request)
    if response.headers.get("x-shield") == "The-Abyss-Active" or response.status_code == 418:
        badge = "[Shield:Blocked]"
    method = request.method
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    status = response.status_code
    
    res_ct = response.headers.get("content-type", "").lower()
    if path.startswith("/vector") or "/vector/" in path:
        type_tag = "[VEC]"
    elif "text/markdown" in res_ct or path.endswith(".md"):
        type_tag = "[MD]"
    elif "text/html" in res_ct:
        type_tag = "[HTML]"
    elif "/feed/" in path or "rss" in res_ct or path.endswith(".rss"):
        type_tag = "[RSS]"
    elif "xml" in res_ct or path.endswith(".xml"):
        type_tag = "[XML]"
    elif "application/json" in res_ct or path.endswith(".json"):
        type_tag = "[JSON]"
    elif "text/css" in res_ct or path.endswith(".css"):
        type_tag = "[CSS]"
    elif "javascript" in res_ct or path.endswith(".js"):
        type_tag = "[JS]"
    elif "font" in res_ct or path.endswith((".woff", ".woff2", ".ttf", ".eot", ".otf")):
        type_tag = "[FONT]"
    elif "text/csv" in res_ct or path.endswith((".csv", ".tsv")):
        type_tag = "[CSV]"
    elif path.endswith((".zip", ".tar.gz", ".gz", ".tar")):
        type_tag = "[ZIP]"
    elif "image/" in res_ct or path.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico", ".svg")):
        type_tag = "[IMG]"
    elif "text/plain" in res_ct or path.endswith(".txt") or "/robots.txt" in path or "/llms.txt" in path:
        type_tag = "[TXT]"
    else:
        type_tag = ""
    
    log_line = f"{ip:<15} {badge:<16} {status} ({duration_ms:>4.0f}ms) {type_tag:<6} -> {method} {path}"
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

# In-flight download task tracker and dead URL cache to avoid duplicate/stalled downloads
_downloading_slugs = set()
_failed_image_urls = set()

def slugify(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^\w\s-]', '', s, flags=re.UNICODE)
    s = re.sub(r'[\s_-]+', '-', s)
    return s.strip('-')

def get_image_slug(card_doc: dict, has_faces: bool = False) -> str:
    """Derive local file name from printing_slug, slug, or sanitized card name."""
    if card_doc.get("image_slug"):
        slug = card_doc["image_slug"]
    elif card_doc.get("printing_slug"):
        slug = card_doc["printing_slug"]
    elif card_doc.get("slug"):
        slug = card_doc["slug"]
    else:
        name = card_doc.get("name") or "card"
        slug = slugify(name)
    return f"{slug}.jpg"

def get_scryfall_direct_uris(card_doc: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract direct Scryfall CDN image URIs from raw dict or root fields."""
    image_uris = card_doc.get("image_uris")
    if image_uris and isinstance(image_uris, dict):
        return image_uris.get("small"), image_uris.get("normal"), image_uris.get("large") or image_uris.get("normal")

    card_faces = card_doc.get("card_faces")
    if card_faces and isinstance(card_faces, list) and len(card_faces) > 0:
        face_uris = card_faces[0].get("image_uris")
        if face_uris and isinstance(face_uris, dict):
            return face_uris.get("small"), face_uris.get("normal"), face_uris.get("large") or face_uris.get("normal")

    raw = card_doc.get("raw")
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
    """Download single image file asynchronously and save to disk with polite rate limiting and dead-URL caching."""
    if not url or url in _failed_image_urls:
        return
    try:
        async with get_download_semaphore():
            # Polite random 10-15ms delay
            await asyncio.sleep(random.uniform(0.010, 0.015))
            headers = {"User-Agent": "AvaScry/2.0 (avascry.com)"}
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=2.0)) as client:
                resp = await client.get(url, headers=headers, follow_redirects=True)
                if resp.status_code == 200 and resp.content:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "wb") as f:
                        f.write(resp.content)
                else:
                    _failed_image_urls.add(url)
    except asyncio.CancelledError:
        pass
    except Exception:
        _failed_image_urls.add(url)

async def background_cache_card_images(slug_name: str, normal_url: Optional[str], large_url: Optional[str]):
    """Background task to fetch and persist both normal and large card images."""
    if slug_name in _downloading_slugs:
        return
    _downloading_slugs.add(slug_name)
    try:
        normal_path = f"public/images/normal/{slug_name}"
        large_path = f"public/images/large/{slug_name}"

        tasks = []
        if normal_url and not os.path.exists(normal_path) and normal_url not in _failed_image_urls:
            tasks.append(_download_and_save_image(normal_url, normal_path))
        if large_url and not os.path.exists(large_path) and large_url not in _failed_image_urls:
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

def is_commander_eligible(card: dict) -> bool:
    """Single source of truth for Commander eligibility matching SmartDeck."""
    t_line = (card.get("type_line") or "").lower()
    o_text = (card.get("oracle_text") or "").lower()
    faces = card.get("card_faces") or card.get("raw", {}).get("card_faces", [])
    front_type = (faces[0].get("type_line") or "").lower() if faces else ""
    front_oracle = (faces[0].get("oracle_text") or "").lower() if faces else ""

    if ("legendary" in t_line and "creature" in t_line) or ("legendary" in front_type and "creature" in front_type):
        return True
    if "can be your commander" in o_text or "can be your commander" in front_oracle:
        return True
    return False

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
        "is_commander": is_commander_eligible(card),
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

@app.get("/developers", response_class=HTMLResponse)
@app.head("/developers")
async def developers_hub(request: Request):
    format_param = request.query_params.get("format", "").lower()
    accept_header = request.headers.get("accept", "").lower()
    if format_param == "md" or "text/markdown" in accept_header:
        return await developers_hub_markdown(request)
    if format_param == "json" or "application/json" in accept_header:
        return await developers_hub_json(request)

    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="developers.html",
        context={
            "current_lang": lang,
            "languages": i18n.LANGUAGES,
            "active_nav": "developers"
        },
        headers={
            "Link": '</developers.md>; rel="alternate"; type="text/markdown", </developers.json>; rel="alternate"; type="application/json"'
        }
    )

@app.get("/developers.md")
@app.head("/developers.md")
async def developers_hub_markdown(request: Request):
    lang = i18n.get_locale(request)
    title = i18n.t('dev_page_title', lang)
    subtitle = i18n.t('dev_hero_subtitle', lang)
    ai_desc = i18n.t('dev_ai_desc', lang)
    api_desc = i18n.t('dev_api_desc', lang)
    vec_desc = i18n.t('dev_vector_desc', lang)
    cockatrice_desc = i18n.t('dev_cockatrice_desc', lang)
    rss_desc = i18n.t('dev_rss_desc', lang)

    md = f"""# {title}

> {subtitle}

- **Language:** {lang}
- **Corpus-Version:** 1.0
- **Canonical-Host:** https://avascry.com

## 1. AI Agent & LLM Ingestion (Markdown Surface)
{ai_desc}

### Endpoints
- Card Rules: `https://avascry.com/printing/<slug>-<set>.md`
- 4096-Dim Synergies: `https://avascry.com/similar/<slug>.md`
- Set Checklists: `https://avascry.com/set/<set-code>.md`
- Artist Portfolios: `https://avascry.com/artist/<artist-slug>.md`
- Comprehensive Rules: `https://avascry.com/rules.md`
- Format Legalities: `https://avascry.com/legalities.md`

## 2. Ultra-Fast REST JSON API
{api_desc}

### Endpoints
- Card Printing: `https://avascry.com/printing/<slug>-<set>.json`
- Card Synergies: `https://avascry.com/similar/<slug>.json`
- Set Details: `https://avascry.com/set/<set-code>.json`
- Artist Portfolio: `https://avascry.com/artist/<artist-slug>.json`
- Rules Corpus: `https://avascry.com/rules.json`
- Legalities Corpus: `https://avascry.com/legalities.json`

## 3. 4096-Dimensional Neural Vectors (Qwen 8B)
{vec_desc}

- Endpoint: `https://avascry.com/vector/<card-slug>.json`

## 4. Cockatrice Desktop Simulator XML
{cockatrice_desc}

- Endpoint: `https://avascry.com/set/<set-code>/cockatrice.xml`

## 5. Discord Webhooks & Live RSS 2.0 Feeds
{rss_desc}

- Sets Feed: `https://avascry.com/feed/sets.xml`
- Rulings Feed: `https://avascry.com/feed/rulings.xml`
"""
    return Response(
        content=md.strip(),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Vary": "Accept, Accept-Language",
            "Link": '</developers>; rel="alternate"; type="text/html", </developers.json>; rel="alternate"; type="application/json"'
        }
    )

@app.get("/developers.json")
@app.head("/developers.json")
async def developers_hub_json(request: Request):
    lang = i18n.get_locale(request)
    return JSONResponse(
        content={
            "name": "AvaScry AI & Developer Ecosystem",
            "version": "1.0",
            "language": lang,
            "canonical_host": "https://avascry.com",
            "endpoints": {
                "markdown": {
                    "card": "https://avascry.com/printing/{slug}-{set}.md",
                    "similar": "https://avascry.com/similar/{slug}.md",
                    "set": "https://avascry.com/set/{code}.md",
                    "artist": "https://avascry.com/artist/{slug}.md",
                    "rules": "https://avascry.com/rules.md",
                    "legalities": "https://avascry.com/legalities.md"
                },
                "json": {
                    "card": "https://avascry.com/printing/{slug}-{set}.json",
                    "similar": "https://avascry.com/similar/{slug}.json",
                    "set": "https://avascry.com/set/{code}.json",
                    "artist": "https://avascry.com/artist/{slug}.json",
                    "vector": "https://avascry.com/vector/{slug}.json",
                    "rules": "https://avascry.com/rules.json",
                    "legalities": "https://avascry.com/legalities.json"
                },
                "xml": {
                    "cockatrice_set": "https://avascry.com/set/{code}/cockatrice.xml",
                    "feed_sets": "https://avascry.com/feed/sets.xml",
                    "feed_rulings": "https://avascry.com/feed/rulings.xml"
                }
            }
        },
        headers={
            "Link": '</developers>; rel="alternate"; type="text/html", </developers.md>; rel="alternate"; type="text/markdown"'
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

    # If no search theme query entered, serve top 4096-dim Qwen 8B neural synergies directly!
    if not theme and oracle_id:
        sim_doc = new_db["similar_cards"].find_one({"oracle_id": oracle_id})
        if sim_doc:
            similar_raw = sim_doc.get("similar", [])
            sim_oids = [s if isinstance(s, str) else s.get("oracle_id") for s in similar_raw]
            sim_oids = [oid for oid in sim_oids if oid and oid != oracle_id]
            
            fb_match = {
                "oracle_id": {"$in": sim_oids},
                "lang": "en"
            }
            if color_identity:
                fb_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
            
            raw_docs = list(new_db["cards"].find(fb_match, {
                "oracle_id": 1, "name": 1, "set": 1, "type_line": 1, "color_identity": 1,
                "oracle_text": 1, "mana_cost": 1, "cmc": 1, "image_uris": 1, "card_faces": 1, "image_slug": 1
            }))
            doc_map = {}
            for d in raw_docs:
                oid = d.get("oracle_id")
                if oid and oid not in doc_map:
                    doc_map[oid] = d
            
            docs = [doc_map[oid] for oid in sim_oids if oid in doc_map][:limit]

    if not docs:
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
                    "card_faces": {"$first": "$card_faces"},
                    "image_slug": {"$first": "$image_slug"}
                }
            },
            {"$limit": max(limit, 60)}
        ]
        docs = list(new_db["cards"].aggregate(pipeline))

    # Always fall back to 4096-dim neural vector similarity when strict token matching returns nothing
    is_fallback = False
    if len(docs) == 0 and oracle_id:
        is_fallback = True
        sim_doc = new_db["similar_cards"].find_one({"oracle_id": oracle_id})
        if sim_doc:
            similar_raw = sim_doc.get("similar", [])
            sim_oids = [s if isinstance(s, str) else s.get("oracle_id") for s in similar_raw]
            sim_oids = [oid for oid in sim_oids if oid and oid != oracle_id]
            fallback_match = {
                "oracle_id": {"$in": sim_oids},
                "lang": "en"
            }
            if color_identity:
                fallback_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
            
            raw_docs = list(new_db["cards"].find(fallback_match, {
                "oracle_id": 1, "name": 1, "set": 1, "type_line": 1, "color_identity": 1,
                "oracle_text": 1, "mana_cost": 1, "cmc": 1, "image_uris": 1, "card_faces": 1, "image_slug": 1
            }))
            doc_map = {}
            for d in raw_docs:
                oid = d.get("oracle_id")
                if oid and oid not in doc_map:
                    doc_map[oid] = d
            docs = [doc_map[oid] for oid in sim_oids if oid in doc_map][:limit]

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
        oid = str(doc.get("oracle_id") or doc.get("_id") or "")
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
    
    # 1. Fast indexed match by printing_slug or slug
    card = db["cards"].find_one({"printing_slug": slug})
    if not card:
        card = db["cards"].find_one({"slug": slug})
    if not card and '-' in slug:
        parts = slug.split('-')
        if len(parts) >= 2:
            card_slug, set_code = "-".join(parts[:-1]), parts[-1].lower()
            card = db["cards"].find_one({"set": set_code, "slug": card_slug})
            if not card:
                card = db["cards"].find_one({"slug": card_slug})
    if not card:
        card = db["cards"].find_one({"name": unslugged})
    
    if card:
        oracle_id = card.get("oracle_id")
        if oracle_id:
            # Find earliest / original Oracle printing in English
            oracle_cards = list(db["cards"].find({"oracle_id": oracle_id, "lang": "en"}).limit(20))
            if oracle_cards:
                oracle_card = min(oracle_cards, key=lambda x: str(x.get("released_at") or "9999"))
            else:
                oracle_card = card
            c_slug = slugify(oracle_card.get("name") or "")
            c_set = (oracle_card.get("set") or "").lower()
            return RedirectResponse(url=f"/printing/{c_slug}-{c_set}", status_code=303)
            
    # Fallback to direct printing route
    return RedirectResponse(url=f"/printing/{slug}", status_code=303)

def format_card_markdown(card_doc: dict, printings_count: int = 1, rulings: list = None, similar_cards: list = None) -> str:
    """Format structured, machine-native Markdown with YAML frontmatter for AI agents and LLMs."""
    name = card_doc.get("name", "Unknown Card")
    mana_cost = card_doc.get("mana_cost") or "N/A"
    cmc = card_doc.get("cmc", 0.0)
    type_line = card_doc.get("type_line", "")
    oracle_text = card_doc.get("oracle_text") or "(No Oracle text)"
    flavor_text = card_doc.get("flavor_text")
    power = card_doc.get("power")
    toughness = card_doc.get("toughness")
    loyalty = card_doc.get("loyalty")
    defense = card_doc.get("defense")
    set_name = card_doc.get("set_name", "")
    set_code = (card_doc.get("set") or "").upper()
    collector_number = card_doc.get("collector_number", "")
    rarity = (card_doc.get("rarity") or "common").lower()
    artist = card_doc.get("artist", "Unknown")
    legalities = card_doc.get("legalities", {})
    keywords = card_doc.get("keywords", [])
    colors = card_doc.get("colors") or []
    color_identity = card_doc.get("color_identity") or []
    oracle_id = card_doc.get("oracle_id", "")
    slug = card_doc.get("slug") or slugify(name)
    set_lower = (card_doc.get("set") or "").lower()
    printing_slug = f"{slug}-{set_lower}" if set_lower else slug

    # Construct YAML Frontmatter
    frontmatter_lines = [
        "---",
        f'name: "{name}"',
        f'mana_cost: "{mana_cost}"',
        f'cmc: {cmc:g}',
        f'type_line: "{type_line}"',
        f'colors: {json.dumps(colors)}',
        f'color_identity: {json.dumps(color_identity)}',
        f'keywords: {json.dumps(keywords)}',
        f'set: "{set_code}"',
        f'set_name: "{set_name}"',
        f'collector_number: "{collector_number}"',
        f'rarity: "{rarity}"',
        f'artist: "{artist}"',
        f'oracle_id: "{oracle_id}"',
        f'canonical_url: "https://avascry.com/printing/{printing_slug}"',
        "legalities:"
    ]
    key_formats = ["commander", "standard", "modern", "pioneer", "legacy", "vintage", "pauper", "penny"]
    for f in key_formats:
        status = legalities.get(f, "not_legal")
        frontmatter_lines.append(f'  {f}: "{status}"')
    frontmatter_lines.append("---")
    frontmatter_text = "\n".join(frontmatter_lines)

    lines = [
        frontmatter_text,
        f"\n# {name}",
        f"- **Mana Cost:** `{mana_cost}` (CMC: {cmc:g})",
        f"- **Type:** {type_line}",
    ]

    if power is not None and toughness is not None:
        lines.append(f"- **Power/Toughness:** {power}/{toughness}")
    if loyalty is not None:
        lines.append(f"- **Starting Loyalty:** {loyalty}")
    if defense is not None:
        lines.append(f"- **Defense:** {defense}")

    if keywords:
        lines.append(f"- **Keywords:** {', '.join(keywords)}")

    lines.append(f"\n## Oracle Text\n{oracle_text}\n")

    if flavor_text:
        lines.append(f"> *{flavor_text}*\n")

    if similar_cards:
        lines.append("## Top 4096-Dim Neural Synergies")
        for idx, sc in enumerate(similar_cards[:6], 1):
            sc_n = sc.get("name")
            sc_slug = sc.get("slug")
            sc_type = sc.get("type_line", "")
            lines.append(f"{idx}. [{sc_n}](/printing/{sc_slug}.md) — {sc_type}")
        lines.append("")

    lines.append("## Printing Details")
    lines.append(f"- **Set:** {set_name} ({set_code}) #{collector_number}")
    lines.append(f"- **Rarity:** {rarity.capitalize()}")
    lines.append(f"- **Artist:** {artist}")
    if printings_count > 1:
        lines.append(f"- **Total Printings:** {printings_count} across all historical editions")

    # Format Key Legalities Table
    leg_list = [f"{f.capitalize()}: `{legalities.get(f, 'not_legal')}`" for f in key_formats if f in legalities]
    if leg_list:
        lines.append(f"\n## Format Legalities\n" + " | ".join(leg_list))

    if rulings:
        lines.append(f"\n## Official Rulings")
        for r in rulings[:6]:
            pub = r.get("published_at", "")
            comment = r.get("comment", "")
            lines.append(f"- *({pub})* {comment}")

    return "\n".join(lines)

def slug_to_name_regex(slug: str) -> re.Pattern:
    """Build a regex that matches card names regardless of stripped apostrophes, exclamation points, question marks, commas, dashes, ampersands, or // slashes."""
    clean = slug.strip().lower()
    clean = clean.replace('&', '-')
    chars = [re.escape(c) if c != '-' else r'[\s\W_]+' for c in clean]
    pattern_str = r'^[\s\W_]*' + r'[\s\W_]*'.join(chars) + r'[\s\W_]*$'
    return re.compile(pattern_str, re.IGNORECASE)

KNOWN_LANG_CODES = {'ja', 'de', 'fr', 'es', 'it', 'pt', 'ru', 'ko', 'zhs', 'zht'}

@app.get("/printing/{identifier}")
@app.head("/printing/{identifier}")
async def printing_detail(request: Request, identifier: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    card = None

    is_md = False
    is_json = False
    if identifier.lower().endswith(".md"):
        identifier = identifier[:-3]
        is_md = True
    elif identifier.lower().endswith(".json"):
        identifier = identifier[:-5]
        is_json = True

    identifier = identifier.strip()
    if not identifier or identifier in ("", ".", "..", "-"):
        raise HTTPException(status_code=404, detail="Card printing not found")

    # 1. Direct indexed match by printing_slug or id or slug
    card = db["cards"].find_one({"printing_slug": identifier})
    if not card:
        card = db["cards"].find_one({"id": identifier})
    if not card:
        card = db["cards"].find_one({"slug": identifier})

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
            p_small_url, p_img_url, p_large_url = resolve_card_images(p, None)
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

    # Mechanics & Tooltips (In-Memory Cache)
    mechanics = []
    try:
        global _MECHANICS_MAP
        if '_MECHANICS_MAP' not in globals() or _MECHANICS_MAP is None:
            mech_cursor = list(db["mechanics"].find({}))
            _MECHANICS_MAP = {m["slug"]: m for m in mech_cursor}
        mechanics_map = _MECHANICS_MAP
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

    # Find Top 6 Highly Relevant Synergistic Cards from the 4096-Dim Neural Vector Brain
    similar_cards = []
    try:
        sim_doc = db["similar_cards"].find_one({"oracle_id": oracle_id})
        if sim_doc:
            similar_raw = sim_doc.get("similar", [])
            sim_oids = [s if isinstance(s, str) else s.get("oracle_id") for s in similar_raw]
            sim_oids = [oid for oid in sim_oids if oid and oid != oracle_id][:15]
            
            sim_cursor = list(db["cards"].find(
                {"oracle_id": {"$in": sim_oids}, "lang": "en"},
                {"name": 1, "slug": 1, "set": 1, "set_name": 1, "image_uris": 1, "card_faces": 1, "type_line": 1, "mana_cost": 1, "oracle_id": 1, "image_slug": 1}
            ))
            doc_map = {}
            for sc in sim_cursor:
                sc_oid = sc.get("oracle_id")
                if sc_oid and sc_oid not in doc_map:
                    doc_map[sc_oid] = sc
            
            for sc_oid in sim_oids:
                if sc_oid in doc_map:
                    sc = doc_map[sc_oid]
                    sc_name = sc.get("name") or "Card"
                    sc_set = (sc.get("set") or "").lower()
                    sc_slug = slugify(sc_name)
                    sc_p_slug = f"{sc_slug}-{sc_set}" if sc_set else sc_slug
                    sc_img = sc.get("image_uris") or {}
                    if not sc_img and sc.get("card_faces"):
                        sc_img = sc["card_faces"][0].get("image_uris") or {}
                    
                    sc_norm = sc_img.get("normal") or (f"https://avascry.com/images/normal/{sc.get('image_slug')}.jpg" if sc.get("image_slug") else f"https://avascry.com/images/normal/{sc_slug}.jpg")
                    if sc_norm.startswith("/"):
                        sc_norm = f"https://avascry.com{sc_norm}"
                    sc_large = sc_img.get("large") or sc_norm
                    if sc_large.startswith("/"):
                        sc_large = f"https://avascry.com{sc_large}"

                    similar_cards.append({
                        "name": sc_name,
                        "slug": sc_p_slug,
                        "set_name": sc.get("set_name") or "",
                        "type_line": sc.get("type_line") or "",
                        "mana_cost": sc.get("mana_cost") or "",
                        "image_url": sc_norm,
                        "large_image_url": sc_large,
                        "image_uris": {
                            "normal": sc_norm,
                            "large": sc_large
                        },
                        "links": {
                            "html": f"https://avascry.com/printing/{sc_p_slug}",
                            "markdown": f"https://avascry.com/printing/{sc_p_slug}.md",
                            "json": f"https://avascry.com/printing/{sc_p_slug}.json"
                        }
                    })
                    if len(similar_cards) >= 8:
                        break
    except Exception as e:
        pass

    # Content Negotiation: Check for AI Agent / LLM requesting Markdown or JSON
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()
    canonical_printing_slug = card_vm.get("printing_slug") or identifier

    if is_json or "application/json" in accept_header or requested_format == "json":
        card_set = (card.get("set") or "").lower()
        card_set_name = card.get("set_name") or card_set.upper()
        card_norm = card_vm.get("image_url") or f"/images/normal/{canonical_printing_slug}.jpg"
        if card_norm.startswith("/"):
            card_norm = f"https://avascry.com{card_norm}"
        card_large = card_vm.get("large_image_url") or card_norm
        if card_large.startswith("/"):
            card_large = f"https://avascry.com{card_large}"

        card_json = {
            "name": card.get("name"),
            "mana_cost": card.get("mana_cost"),
            "cmc": float(card.get("cmc") or 0.0),
            "type_line": card.get("type_line"),
            "oracle_text": card.get("oracle_text"),
            "layout": card.get("layout", "normal"),
            "card_faces": card.get("card_faces"),
            "power": card.get("power"),
            "toughness": card.get("toughness"),
            "loyalty": card.get("loyalty"),
            "colors": card.get("colors") or [],
            "color_identity": card.get("color_identity") or [],
            "keywords": card.get("keywords") or [],
            "set": card_set,
            "set_name": card_set_name,
            "collector_number": card.get("collector_number") or "",
            "rarity": card.get("rarity") or "",
            "artist": card.get("artist") or "",
            "oracle_id": oracle_id,
            "image_uris": {
                "normal": card_norm,
                "large": card_large
            },
            "links": {
                "html": f"https://avascry.com/printing/{canonical_printing_slug}",
                "markdown": f"https://avascry.com/printing/{canonical_printing_slug}.md",
                "json": f"https://avascry.com/printing/{canonical_printing_slug}.json"
            },
            "legalities": card.get("legalities") or {},
            "rulings": rulings,
            "printings_count": len(printings),
            "similar_cards": similar_cards[:6]
        }
        return JSONResponse(
            content=card_json,
            headers={
                "Vary": "Accept",
                "Link": f'</printing/{canonical_printing_slug}.md>; rel="alternate"; type="text/markdown", </printing/{canonical_printing_slug}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_md or "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
        md_text = format_card_markdown(card, printings_count=len(printings), rulings=rulings, similar_cards=similar_cards)
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Vary": "Accept",
                "X-Markdown-Tokens": str(len(md_text.split())),
                "Link": f'</printing/{canonical_printing_slug}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    # Check if card is saved in user stash
    user = request.session.get("user") if "session" in request.scope else None
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
        },
        headers={
            "Link": f'</printing/{canonical_printing_slug}.md>; rel="alternate"; type="text/markdown", </printing/{canonical_printing_slug}.json>; rel="alternate"; type="application/json"'
        }
    )

@app.get("/printing/{slug}.md")
@app.head("/printing/{slug}.md")
async def printing_detail_markdown(request: Request, slug: str, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=md"
    return await printing_detail(request, slug, background_tasks)

@app.get("/printing/{slug}.json")
@app.head("/printing/{slug}.json")
async def printing_detail_json(request: Request, slug: str, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=json"
    return await printing_detail(request, slug, background_tasks)

@app.head("/printing/{identifier}")
async def printing_detail_head(request: Request, identifier: str, background_tasks: BackgroundTasks):
    return await printing_detail(request, identifier, background_tasks)

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
@app.head("/similar/{slug}")
async def similar_cards_page(slug: str, request: Request, background_tasks: BackgroundTasks):
    """Deep similarity search: finds top 31 mechanically similar cards from the 38k embedding graph."""
    db = get_mongo_db()

    is_md = False
    is_json = False
    if slug.lower().endswith(".md"):
        slug = slug[:-3]
        is_md = True
    elif slug.lower().endswith(".json"):
        slug = slug[:-5]
        is_json = True

    slug = slug.strip()
    if not slug or slug in ("", ".", "..", "-"):
        raise HTTPException(status_code=404, detail="Card not found")

    pattern = slug_to_name_regex(slug)
    card = db["cards"].find_one({"$or": [{"slug": slug}, {"name": pattern}]})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
        
    oracle_id = card.get("oracle_id")
    card_name = card.get("name") or "Card"
    card_set = (card.get("set") or "").lower()
    card_slug = slugify(card_name)
    card_printing_slug = f"{card_slug}-{card_set}" if card_set else card_slug
    
    # Resolve target card image
    _, target_img, _ = resolve_card_images(card, background_tasks)

    # Fetch precomputed cosine similarity from 38k embedding collection
    sim_doc = db["similar_cards"].find_one({"oracle_id": oracle_id})
    similar_items = sim_doc.get("similar", []) if sim_doc else []
    
    results = []
    seen_oracles = {oracle_id}
    
    if similar_items:
        sim_oids = [s if isinstance(s, str) else s.get("oracle_id") for s in similar_items if (s if isinstance(s, str) else s.get("oracle_id"))]
        
        c_docs = list(db["cards"].find(
            {"oracle_id": {"$in": sim_oids[:60]}, "lang": "en"},
            {"name": 1, "slug": 1, "set": 1, "image_uris": 1, "card_faces": 1, "type_line": 1, "mana_cost": 1, "oracle_id": 1, "image_slug": 1, "raw": 1}
        ))
        
        doc_by_oid = {}
        for d in c_docs:
            oid = d.get("oracle_id")
            if oid and oid not in doc_by_oid:
                doc_by_oid[oid] = d
                
        for oid in sim_oids:
            if oid in doc_by_oid and oid not in seen_oracles:
                seen_oracles.add(oid)
                sc = doc_by_oid[oid]
                sc_name = sc.get("name") or "Card"
                sc_set = (sc.get("set") or "").lower()
                sc_slug = slugify(sc_name)
                sc_printing_slug = f"{sc_slug}-{sc_set}" if sc_set else sc_slug
                _, sc_img_url, _ = resolve_card_images(sc, None)
                
                results.append({
                    "name": sc_name,
                    "slug": sc_printing_slug,
                    "image_url": sc_img_url,
                    "type_line": sc.get("type_line"),
                    "mana_cost": sc.get("mana_cost")
                })
                if len(results) >= 31:
                    break

    if not results:
        # Dynamic fallback for custom/playtest/unvectorized cards (e.g. Star Trek, Universes Beyond)
        keywords = card.get("keywords", [])
        colors = card.get("color_identity", [])
        type_line = card.get("type_line", "")
        
        fallback_query = {
            "oracle_id": {"$ne": oracle_id},
            "lang": "en"
        }
        clauses = []
        if keywords:
            clauses.append({"keywords": {"$in": keywords[:3]}})
        if colors:
            clauses.append({"color_identity": {"$in": colors}})
            
        main_type = "Creature" if "Creature" in type_line else ("Artifact" if "Artifact" in type_line else ("Enchantment" if "Enchantment" in type_line else ("Instant" if "Instant" in type_line else "Sorcery")))
        clauses.append({"type_line": {"$regex": main_type}})
        fallback_query["$or"] = clauses
        
        fallback_cursor = list(db["cards"].find(
            fallback_query,
            {"name": 1, "slug": 1, "set": 1, "image_uris": 1, "card_faces": 1, "type_line": 1, "mana_cost": 1, "oracle_id": 1, "image_slug": 1, "raw": 1}
        ).limit(60))
        
        for sc in fallback_cursor:
            sc_oid = sc.get("oracle_id")
            if sc_oid and sc_oid not in seen_oracles:
                seen_oracles.add(sc_oid)
                sc_name = sc.get("name") or "Card"
                sc_set = (sc.get("set") or "").lower()
                sc_slug = slugify(sc_name)
                sc_printing_slug = f"{sc_slug}-{sc_set}" if sc_set else sc_slug
                _, sc_img_url, _ = resolve_card_images(sc, None)
                
                results.append({
                    "name": sc_name,
                    "slug": sc_printing_slug,
                    "image_url": sc_img_url,
                    "type_line": sc.get("type_line"),
                    "mana_cost": sc.get("mana_cost"),
                    "score": 0.70
                })
                if len(results) >= 31:
                    break

    # Content Negotiation for AI Agents (Accept: text/markdown, application/json, or ?format=)
    accept_header = request.headers.get("accept", "").lower()
    requested_format = request.query_params.get("format", "").lower()

    if is_json or "application/json" in accept_header or requested_format == "json":
        target_norm = target_img
        if target_norm.startswith("/"):
            target_norm = f"https://avascry.com{target_norm}"
            
        formatted_results = []
        for sc in results:
            sc_img = sc.get("image_url") or ""
            if sc_img.startswith("/"):
                sc_img = f"https://avascry.com{sc_img}"
            sc_slug = sc.get("slug") or ""
            formatted_results.append({
                "name": sc.get("name"),
                "slug": sc_slug,
                "type_line": sc.get("type_line"),
                "mana_cost": sc.get("mana_cost"),
                "score": sc.get("score"),
                "image_uris": {
                    "normal": sc_img
                },
                "links": {
                    "html": f"https://avascry.com/printing/{sc_slug}",
                    "markdown": f"https://avascry.com/printing/{sc_slug}.md",
                    "json": f"https://avascry.com/printing/{sc_slug}.json"
                }
            })

        sim_json = {
            "target_card": {
                "name": card_name,
                "slug": card_slug,
                "printing_slug": card_printing_slug,
                "type_line": card.get("type_line", ""),
                "mana_cost": card.get("mana_cost", ""),
                "image_uris": {
                    "normal": target_norm
                },
                "links": {
                    "html": f"https://avascry.com/printing/{card_printing_slug}",
                    "markdown": f"https://avascry.com/printing/{card_printing_slug}.md",
                    "json": f"https://avascry.com/printing/{card_printing_slug}.json"
                }
            },
            "algorithm": "4096-dimensional Qwen 8B Cosine Similarity",
            "links": {
                "html": f"https://avascry.com/similar/{card_slug}",
                "markdown": f"https://avascry.com/similar/{card_slug}.md",
                "json": f"https://avascry.com/similar/{card_slug}.json"
            },
            "total_similar": len(formatted_results),
            "similar_cards": formatted_results
        }
        return JSONResponse(
            content=sim_json,
            headers={
                "Vary": "Accept",
                "Link": f'</similar/{card_slug}.md>; rel="alternate"; type="text/markdown", </similar/{card_slug}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_md or "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
        md_lines = [
            "---",
            f"target_card: {card_name}",
            f"mana_cost: \"{card.get('mana_cost', '')}\"",
            f"type_line: \"{card.get('type_line', '')}\"",
            f"algorithm: \"4096-dimensional Qwen 8B Cosine Similarity over 38,000 Oracle embeddings\"",
            f"canonical_url: https://avascry.com/similar/{card_slug}",
            f"json_api: https://avascry.com/similar/{card_slug}.json",
            "---",
            f"\n# Cards Similar & Synergistic to {card_name}\n",
            f"- **Target Card:** [{card_name}](https://avascry.com/printing/{card_printing_slug}) ({card.get('type_line', '')}) `{card.get('mana_cost', '')}`",
            f"- **Algorithm:** 4096-dimensional Qwen 8B Cosine Similarity over 38,000 Oracle embeddings",
            f"- **JSON API:** https://avascry.com/similar/{card_slug}.json",
            f"\n## Top 31 Synergistic Matches\n"
        ]
        for idx, sc in enumerate(results, 1):
            sc_p_slug = sc.get("slug") or slugify(sc.get("name") or "card")
            md_lines.append(f"{idx}. [**{sc['name']}**](https://avascry.com/printing/{sc_p_slug}) `{sc.get('mana_cost') or 'N/A'}` — *{sc.get('type_line') or ''}*")
        
        md_text = "\n".join(md_lines)
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Vary": "Accept",
                "X-Markdown-Tokens": str(len(md_text.split())),
                "Link": f'</similar/{card_slug}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="similar.html",
        context={
            "active_nav": "explore",
            "card": {
                "name": card_name,
                "slug": card_slug,
                "printing_slug": card_printing_slug,
                "type_line": card.get("type_line", ""),
                "mana_cost": card.get("mana_cost", "")
            },
            "target_image": target_img,
            "similar_cards": results
        },
        headers={
            "Link": f'</similar/{card_slug}.md>; rel="alternate"; type="text/markdown", </similar/{card_slug}.json>; rel="alternate"; type="application/json"'
        }
    )

@app.get("/similar/{slug}.md")
@app.head("/similar/{slug}.md")
async def similar_cards_markdown(slug: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=md"
    return await similar_cards_page(slug, request, background_tasks)

@app.get("/similar/{slug}.json")
@app.head("/similar/{slug}.json")
async def similar_cards_json(slug: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=json"
    return await similar_cards_page(slug, request, background_tasks)

@app.head("/similar/{slug}")
async def similar_cards_head(slug: str, request: Request, background_tasks: BackgroundTasks):
    return await similar_cards_page(slug, request, background_tasks)

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
@app.head("/set/{code}")
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
    cards_cursor = list(db["cards"].find(
        {"set": set_code, "lang": "en"},
        {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "rarity": 1, "type_line": 1, "mana_cost": 1, "cmc": 1, "image_slug": 1, "image_uris": 1}
    ))
    if not cards_cursor:
        cards_cursor = list(db["cards"].find(
            {"set": set_code},
            {"name": 1, "set": 1, "set_name": 1, "collector_number": 1, "rarity": 1, "type_line": 1, "mana_cost": 1, "cmc": 1, "image_slug": 1, "image_uris": 1}
        ).limit(300))

    cards = []
    set_name = set_code.upper()
    for doc in cards_cursor:
        set_name = doc.get("set_name") or set_name
        c_name = doc.get("name") or "Card"
        c_slug = slugify(c_name)
        c_num = str(doc.get("collector_number") or "")
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
            "image_slug": doc.get("image_slug") or c_slug
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
            img_slug = c.get("image_slug") or c_slug
            c_norm = f"https://avascry.com/images/normal/{img_slug}.jpg"
            c_large = f"https://avascry.com/images/large/{img_slug}.jpg"
                
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

        return JSONResponse(
            content={
                "set": {
                    "code": set_code,
                    "name": set_name,
                    "links": {
                        "html": f"https://avascry.com/set/{set_code}",
                        "markdown": f"https://avascry.com/set/{set_code}.md",
                        "json": f"https://avascry.com/set/{set_code}.json"
                    }
                },
                "total_cards": len(formatted_set_cards),
                "cards": formatted_set_cards
            },
            headers={
                "Vary": "Accept",
                "Link": f'</set/{set_code}.md>; rel="alternate"; type="text/markdown", </set/{set_code}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_md or "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
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
            f"- **JSON API:** https://avascry.com/set/{set_code}.json\n",
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
                "Link": f'</set/{set_code}.json>; rel="alternate"; type="application/json"',
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
        },
        headers={
            "Link": f'</set/{set_code}.md>; rel="alternate"; type="text/markdown", </set/{set_code}.json>; rel="alternate"; type="application/json"'
        }
    )

@app.get("/set/{code}.md")
@app.head("/set/{code}.md")
async def set_detail_markdown(code: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=md"
    return await set_detail(request, code, background_tasks)

@app.get("/set/{code}.json")
@app.head("/set/{code}.json")
async def set_detail_json(code: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=json"
    return await set_detail(request, code, background_tasks)

@app.get("/set/{code}/cockatrice.xml")
@app.get("/set/{code}.xml")
@app.head("/set/{code}/cockatrice.xml")
@app.head("/set/{code}.xml")
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

@app.get("/feed/sets.xml")
@app.head("/feed/sets.xml")
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

@app.get("/feed/rulings.xml")
@app.head("/feed/rulings.xml")
async def feed_rulings_xml():
    """RSS 2.0 Syndication Feed of official Magic: The Gathering card rulings."""
    db = get_mongo_db()
    db_old = get_old_db()
    rulings_col = db["rulings"] if db["rulings"].estimated_document_count() > 0 else db_old["rulings"]
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
@app.head("/artist/{slug}")
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

    unslugged = slug.replace('-', ' ')
    artist_name = unslugged.title()
    
    # 1. Fast exact match using index
    query_exact = {"artist": artist_name, "lang": "en"}
    cards_cursor = list(db["cards"].find(
        query_exact,
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
            "mana_cost": doc.get("mana_cost") or "",
            "released_at": doc.get("released_at") or "",
            "printing_slug": f"{c_slug}-{c_set}" if c_set else c_slug,
            "image_url": img_url,
            "large_image_url": large_img_url
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

        return JSONResponse(
            content={
                "artist": {
                    "name": artist_name,
                    "slug": slug,
                    "links": {
                        "html": f"https://avascry.com/artist/{slug}",
                        "markdown": f"https://avascry.com/artist/{slug}.md",
                        "json": f"https://avascry.com/artist/{slug}.json"
                    }
                },
                "total_artworks": len(formatted_artist_cards),
                "cards": formatted_artist_cards
            },
            headers={
                "Vary": "Accept",
                "Link": f'</artist/{slug}.md>; rel="alternate"; type="text/markdown", </artist/{slug}.json>; rel="alternate"; type="application/json"',
                "Content-Signal": "ai-train=yes, search=yes, ai-input=yes"
            }
        )

    if is_md or "text/markdown" in accept_header or "text/x-markdown" in accept_header or requested_format in ("md", "markdown"):
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
            f"- **JSON API:** https://avascry.com/artist/{slug}.json\n",
            "| # | Card Name | Set | Type | Rarity | Mana Cost | Released |",
            "|---|-----------|-----|------|--------|-----------|----------|"
        ]
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
                "Link": f'</artist/{slug}.json>; rel="alternate"; type="application/json"',
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
        },
        headers={
            "Link": f'</artist/{slug}.md>; rel="alternate"; type="text/markdown", </artist/{slug}.json>; rel="alternate"; type="application/json"'
        }
    )

@app.get("/artist/{slug}.md")
@app.head("/artist/{slug}.md")
async def artist_detail_markdown(slug: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=md"
    return await artist_detail(request, slug, background_tasks)

@app.get("/artist/{slug}.json")
@app.head("/artist/{slug}.json")
async def artist_detail_json(slug: str, request: Request, background_tasks: BackgroundTasks):
    request.scope["query_string"] = b"format=json"
    return await artist_detail(request, slug, background_tasks)

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
        reload=False,
        access_log=False
    )
