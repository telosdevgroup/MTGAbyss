"""
mtgabyss.middleware.access_logger
----------------------------------
Request logger middleware, IP extraction, caller badge classifier, and watchlist.
"""
import os
import sys
import re
import json
import time
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import Response

import i18n
from mtgabyss.network_router import get_request_host, get_site_badge
from mtgabyss.shared.bot_verifier import check_googlebot

# Enable Virtual Terminal Processing on Windows if supported
if os.name == 'nt':
    try:
        os.system('')
    except Exception:
        pass

# Detect if stdout supports ANSI colors
def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR") == "1":
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOR = _supports_color()

# ANSI SGR color primitives
CLR_RESET   = "\033[0m" if USE_COLOR else ""
CLR_BOLD    = "\033[1m" if USE_COLOR else ""
CLR_DIM     = "\033[2m" if USE_COLOR else ""

CLR_RED     = "\033[91m" if USE_COLOR else ""
CLR_GREEN   = "\033[92m" if USE_COLOR else ""
CLR_YELLOW  = "\033[93m" if USE_COLOR else ""
CLR_BLUE    = "\033[94m" if USE_COLOR else ""
CLR_MAGENTA = "\033[95m" if USE_COLOR else ""
CLR_CYAN    = "\033[96m" if USE_COLOR else ""
CLR_WHITE   = "\033[97m" if USE_COLOR else ""

# Color helpers
def c_dim(text: str) -> str:
    return f"{CLR_DIM}{text}{CLR_RESET}" if USE_COLOR else text

def c_bold(text: str) -> str:
    return f"{CLR_BOLD}{text}{CLR_RESET}" if USE_COLOR else text

def c_cyan(text: str) -> str:
    return f"{CLR_CYAN}{text}{CLR_RESET}" if USE_COLOR else text

def c_green(text: str) -> str:
    return f"{CLR_GREEN}{text}{CLR_RESET}" if USE_COLOR else text

def c_yellow(text: str) -> str:
    return f"{CLR_YELLOW}{text}{CLR_RESET}" if USE_COLOR else text

def c_magenta(text: str) -> str:
    return f"{CLR_MAGENTA}{text}{CLR_RESET}" if USE_COLOR else text

def c_blue(text: str) -> str:
    return f"{CLR_BLUE}{text}{CLR_RESET}" if USE_COLOR else text

def c_red(text: str) -> str:
    return f"{CLR_RED}{text}{CLR_RESET}" if USE_COLOR else text

def c_red_bold(text: str) -> str:
    return f"{CLR_BOLD}{CLR_RED}{text}{CLR_RESET}" if USE_COLOR else text

def c_yellow_bold(text: str) -> str:
    return f"{CLR_BOLD}{CLR_YELLOW}{text}{CLR_RESET}" if USE_COLOR else text

def c_green_bold(text: str) -> str:
    return f"{CLR_BOLD}{CLR_GREEN}{text}{CLR_RESET}" if USE_COLOR else text

# ---------------------------------------------------------------------------
# IP extraction
# ---------------------------------------------------------------------------
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
    return ""


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------
WATCHLIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "watchlist.json")
WATCHLIST = {}
try:
    if os.path.exists(WATCHLIST_PATH):
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f_w:
            WATCHLIST = json.load(f_w)
except Exception:
    pass


# ---------------------------------------------------------------------------
# Caller badge classifier
# ---------------------------------------------------------------------------
def get_caller_badge(request: Request) -> str:
    """Classify visitor into clear badges for high-signal log monitoring."""
    ua = request.headers.get("user-agent", "").lower()
    cf_country = request.headers.get("cf-ipcountry")
    ip = get_client_ip(request)

    # 0. Check IP Watchlist
    if ip in WATCHLIST:
        return WATCHLIST[ip].get("badge", "[Watchlist]")

    # Discord Bot Interaction Webhooks & Crawlers (Discord uses Discord-Interactions or Discordbot)
    if "discord" in ua or request.url.path.startswith("/api/discord"):
        return "[Social:Discord]"

    # Datacenter Scraper check (AWS & GCP compute)
    cloud_dc_prefixes = (
        "3.", "18.", "23.20.", "23.21.", "23.22.", "23.23.",
        "34.", "35.", "44.", "52.", "54.", "99.", "100.24.", "100.25.",
        "100.26.", "100.27.", "107.20.", "107.21.", "107.22.", "107.23.",
        "130.211.", "136.116.", "136.117.", "136.118.", "136.119.", "136.120."
    )
    if not ip.startswith("136.32.") and any(ip.startswith(p) for p in cloud_dc_prefixes) and not any(k in ua for k in ("googlebot", "bingbot", "discord")):
        if any(ip.startswith(p) for p in ("136.116.", "136.117.", "136.118.", "136.119.", "136.120.", "130.211.")):
            return "[GCP:Blocked]"
        return "[AWS:Blocked]"

    if "sleepbot" in ua:
        return "[SleepBot:Blocked]"

    # 1. Real-Time Live AI User Grounding Prompts (The Holy Grail)
    if "claude-user" in ua:
        return "[Claude-User]"
    if "chatgpt-user" in ua:
        return "[ChatGPT-User]"
    if "perplexity-user" in ua:
        return "[Perplexity-User]"
    if "shap-user" in ua:
        return "[Shap-User]"
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
    is_google_ua = any(g in ua for g in ("googlebot", "google-inspectiontool", "feedfetcher-google", "google-read-aloud", "googleother"))
    is_google_ip = any(ip.startswith(p) for p in google_prefixes)

    if is_google_ua or is_google_ip:
        v_status = check_googlebot(ip)
        suffix = ":Verified" if v_status == "VERIFIED" else (":SPOOFED" if v_status == "SPOOFED" else ":Claimed")
        if "googlebot-image" in ua or "image" in ua:
            return f"[Googlebot-Image{suffix}]"
        return f"[Googlebot{suffix}]"

    # 4. Bing / Microsoft IP subnets & User-Agents
    bing_prefixes = ("40.77.", "157.55.", "20.171.", "13.66.", "52.167.", "20.36.", "20.247.")
    if any(ip.startswith(p) for p in bing_prefixes) or any(b in ua for b in ("bingbot", "bingpreview", "msnbot")):
        return "[Bingbot]"

    # 5. AI Training, Retrieval & Search Agents
    if any(p in ua for p in ("perplexity", "perplexitybot", "ppx")):
        return "[Perplexity]"
    if any(o in ua for o in ("gptbot", "openai")):
        return "[GPTBot]"
    if "meta-externalagent" in ua:
        return "[Meta:AI]"
    if "meta-externalfetcher" in ua:
        return "[Meta:Fetcher]"
    if "meta-webindexer" in ua or "facebookcatalog" in ua:
        return "[Meta:Catalog]"
    if any(b in ua for b in ("bytespider", "bytedance")):
        return "[ByteSpider]"
    if any(a in ua for a in ("applebot", "applebot-extended", "apple-search")):
        return "[Apple:Blocked]"
    if any(amz in ua for amz in ("amazonbot", "amzn-search", "amzn-searchbot")):
        return "[Amazon:Blocked]"
    if "shapbot" in ua or "parallel" in ua:
        return "[AI:ShapBot]"
    if any(c in ua for c in ("cohere-ai", "cohere")):
        return "[Cohere]"
    if "ccbot" in ua or "commoncrawl" in ua:
        return "[AI:CommonCrawl]"
    if "diffbot" in ua:
        return "[AI:Diffbot]"
    if "youbot" in ua:
        return "[AI:YouBot]"
    if "imagesift" in ua:
        return "[AI:Imagesift]"
    if "deepseek" in ua:
        return "[AI:DeepSeek]"
    if "mistral" in ua:
        return "[AI:Mistral]"
    if any(d in ua for d in ("ai2bot", "anthropic")):
        return "[AI:Other]"

    # 4. Search Engines & Web Crawlers
    if "duckduckbot" in ua:
        return "[Crawler:DuckDuckGo]"
    if "yandex" in ua:
        return "[Crawler:Yandex]"
    if "baiduspider" in ua:
        return "[Crawler:Baidu]"
    if "sogou" in ua:
        return "[Crawler:Sogou]"
    if "seznam" in ua:
        return "[Crawler:Seznam]"
    if "petalbot" in ua:
        return "[Crawler:Petal]"
    if "yeti" in ua or "naver" in ua:
        return "[Crawler:Naver]"
    if "archive.org_bot" in ua or "ia_archiver" in ua:
        return "[Crawler:ArchiveOrg]"

    # 5. Social Media Embed & Link Preview Crawlers
    if "discordbot" in ua:
        return "[Social:Discord]"
    if "twitterbot" in ua:
        return "[Social:Twitter]"
    if "whatsapp" in ua:
        return "[Social:WhatsApp]"
    if "instagram" in ua:
        return "[Social:Instagram]"
    if any(t in ua for t in ("threads", "barcelona")):
        return "[Social:Threads]"
    if "facebookexternalhit" in ua or "facebot" in ua:
        return "[Social:Facebook]"
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

    if any(f in ua for f in ("feedbin", "inoreader", "newsblur", "feedly")):
        return "[FeedFetcher]"

    if "avascry-cachewarmer" in ua:
        return "[CacheWarmer]"

    if any(k in ua for k in ("ava9001", "ava9000", "siteblaster")):
        return "[SiteBlaster:9001]"

    path_req = request.url.path.lower()
    if any(p in path_req for p in ("/ads.txt", "/app-ads.txt", "/sellers.json", "/security.txt")):
        return "[Scanner:Ad/Sec]"
    if any(s in ua for s in ("censys", "shodan", "netcraft", "qualys", "zgrab")):
        return "[Scanner:Sec]"

    if any(s in ua for s in ("python", "requests", "aiohttp", "curl", "wget", "httpclient", "go-http-client", "node-fetch", "urllib", "axios", "postman")):
        return "[Dev:Script]"

    if "testclient" in ua or "pytest" in ua:
        return "[TestClient]"

    if any(bot in ua for bot in ("spider", "crawl", "slurp", "fetcher", "headless", "bot")):
        return "[Cloud:Spider]"

    if cf_country and cf_country != "XX":
        return f"[Browser:{cf_country}]"
    return "[Browser:Direct]"


# ---------------------------------------------------------------------------
# Access log
# ---------------------------------------------------------------------------
LOG_DIR = r"C:\avascry_data\logs"
ACCESS_LOG_PATH = os.path.join(LOG_DIR, "access.log")
os.makedirs(LOG_DIR, exist_ok=True)


async def request_logger_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    ip = get_client_ip(request)
    badge = get_caller_badge(request)
    if response.headers.get("x-shield") == "The-Abyss-Active" or response.status_code == 418:
        badge = "[Shield:Blocked]"
    elif response.headers.get("x-shield") in ("Scraper-Blocked", "Bot-Gone") or response.status_code == 410:
        badge = "[Scraper:Blocked]"
    method = request.method
    path = request.url.path
    if request.url.query:
        path = f"{path}?{request.url.query}"
    status = response.status_code

    res_ct = response.headers.get("content-type", "").lower()

    # 1. Surface tag (4 chars inside brackets)
    clean_p = path.lower().split("?")[0]
    if "image/" in res_ct or clean_p.startswith(("/images/", "/image/")) or clean_p.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico", ".svg")):
        raw_surf = "[IMG ]"
        surf_col = c_blue(raw_surf)
    elif clean_p.startswith(("/printing/", "/card/")):
        raw_surf = "[PRIN]"
        surf_col = c_green(raw_surf)
    elif clean_p.startswith("/similar"):
        raw_surf = "[SIM ]"
        surf_col = c_magenta(raw_surf)
    elif clean_p.startswith("/vector"):
        raw_surf = "[VECT]"
        surf_col = c_cyan(raw_surf)
    elif clean_p.startswith("/commander"):
        raw_surf = "[CMDR]"
        surf_col = c_yellow(raw_surf)
    elif clean_p.startswith("/artist"):
        raw_surf = "[ARTS]"
        surf_col = c_blue(raw_surf)
    elif clean_p.startswith("/set"):
        raw_surf = "[SETS]"
        surf_col = c_yellow(raw_surf)
    elif clean_p.startswith(("/sitemap", "/robots.txt", "/llms")) or clean_p.endswith((".xml", ".txt")):
        raw_surf = "[MAP ]"
        surf_col = c_dim(raw_surf)
    elif clean_p.startswith("/deck"):
        raw_surf = "[DECK]"
        surf_col = c_magenta(raw_surf)
    elif clean_p in ("/", ""):
        raw_surf = "[HOME]"
        surf_col = c_cyan(raw_surf)
    elif clean_p.endswith((".css", ".js", ".woff", ".woff2", ".ttf")):
        raw_surf = "[ASST]"
        surf_col = c_dim(raw_surf)
    else:
        raw_surf = "[PAGE]"
        surf_col = c_dim(raw_surf)

    # 2. Format tag (4 chars inside brackets)
    if "text/markdown" in res_ct or clean_p.endswith(".md"):
        raw_fmt = "[MD  ]"
        fmt_col = c_magenta(raw_fmt)
    elif "application/json" in res_ct or clean_p.endswith(".json"):
        raw_fmt = "[JSON]"
        fmt_col = c_yellow(raw_fmt)
    elif "image/" in res_ct or clean_p.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico", ".svg")):
        raw_fmt = "[IMG ]"
        fmt_col = c_blue(raw_fmt)
    elif "text/plain" in res_ct or clean_p.endswith(".txt"):
        raw_fmt = "[TXT ]"
        fmt_col = c_dim(raw_fmt)
    elif clean_p.endswith((".xml", ".rss")):
        raw_fmt = "[XML ]"
        fmt_col = c_dim(raw_fmt)
    elif clean_p.endswith((".css", ".js", ".woff", ".woff2", ".ttf")):
        raw_fmt = "[ASST]"
        fmt_col = c_dim(raw_fmt)
    else:
        raw_fmt = "[HTML]"
        fmt_col = c_cyan(raw_fmt)

    # 3. Game / Subdomain site badge
    site_badge_color, site_badge_raw = get_site_badge(get_request_host(request))
    # Standardize to 6 chars "[MTG ]", "[DOM ]", "[SWU ]"
    clean_site_raw = site_badge_raw if len(site_badge_raw) == 6 else f"{site_badge_raw:<6}"
    if USE_COLOR:
        # Match game color theme
        if "DOM" in clean_site_raw:
            site_col = c_cyan(clean_site_raw)
        elif "SWU" in clean_site_raw:
            site_col = c_magenta(clean_site_raw)
        elif "NEC" in clean_site_raw:
            site_col = c_red_bold(clean_site_raw)
        elif "MIN" in clean_site_raw:
            site_col = c_green(clean_site_raw)
        else:
            site_col = c_yellow(clean_site_raw)
    else:
        site_col = clean_site_raw

    # 4. Bot / Caller badge with visual hierarchy
    clean_badge = badge.strip()
    # Normalize badge width to exactly 18 chars
    if len(clean_badge) > 18:
        raw_badge_18 = clean_badge[:17] + "]"
    else:
        raw_badge_18 = f"{clean_badge:<18}"

    b_lower = clean_badge.lower()
    if any(k in b_lower for k in ("-user", "chatgpt-user", "claude-user", "perplexity-user")):
        # High-value live user prompt / citation
        badge_col = c_yellow_bold(raw_badge_18)
    elif "spoofed" in b_lower:
        badge_col = c_red_bold(raw_badge_18)
    elif "blocked" in b_lower:
        badge_col = c_red(raw_badge_18)
    elif any(v in b_lower for v in ("verified", "googlebot:verified", "bingbot")):
        # Quiet verified traffic — calm dim / normal
        badge_col = c_dim(raw_badge_18)
    elif "claimed" in b_lower:
        badge_col = c_yellow(raw_badge_18)
    elif any(s in b_lower for s in ("scraper", "scanner")):
        badge_col = c_red(raw_badge_18)
    elif "browser" in b_lower:
        badge_col = c_green(raw_badge_18)
    else:
        badge_col = c_dim(raw_badge_18)

    # 5. Status code styling (Prominent stand-out)
    if status >= 500:
        status_col = c_red_bold(str(status))
    elif status >= 400:
        status_col = c_yellow_bold(str(status))
    elif status >= 300:
        status_col = c_cyan(str(status))
    else:
        status_col = c_green(str(status))

    # 6. Latency styling (Fast = dim, Normal = default, Slow = highlighted)
    dur_int = int(round(duration_ms))
    dur_raw = f"{dur_int:>4}ms"
    if dur_int >= 1000:
        dur_col = c_red_bold(dur_raw)
    elif dur_int >= 400:
        dur_col = c_yellow_bold(dur_raw)
    else:
        dur_col = c_dim(dur_raw)

    # 7. Rigid column composition
    # [Site  ] [Caller/Bot        ] Status (Duration) [Surf] [Fmt ] -> Path
    # Example:
    # [MTG ] [Googlebot:Verified] 200 (  45ms) [PRIN] [HTML] -> /printing/sol-ring-cmm
    console_line = f"{site_col} {badge_col} {status_col} ({dur_col}) {surf_col} {fmt_col} -> {path}"

    # Exact format required by watch_traffic.py LOG_REGEX:
    # (?P<ts>\S+)\s+(?P<ip>\S+)\s+(?P<badge>\[[^\]]+\])\s+(?:\[(?P<site>[A-Z0-9_\s]+)\]\s+)?(?P<status>\d{3})\s+\(\s*(?P<lat>\d+)ms\)(?P<tags>(?:\s+\[[^\]]*\])*)\s+->\s+(?P<method>\S+)\s+(?P<path>\S+)
    raw_ua = request.headers.get("user-agent", "").replace("\r", " ").replace("\n", " ").strip()
    ua_suffix = f' "{raw_ua}"' if raw_ua else ""
    full_audit_line = f"{ip:<28} {clean_badge:<18} {clean_site_raw} {status} ({dur_int:>4d}ms) {raw_surf} {raw_fmt} -> {method} {path}"

    # Suppress console printing for blocked noise (still captured in audit log)
    is_blocked = status in (410, 418) or "Blocked" in badge or response.headers.get("x-shield") in ("Scraper-Blocked", "Bot-Gone", "Datacenter-Gone", "The-Abyss-Active")
    if not is_blocked:
        print(console_line, flush=True)

    try:
        with open(ACCESS_LOG_PATH, "a", encoding="utf-8") as f_log:
            f_log.write(f"{datetime.now(timezone.utc).isoformat()} {full_audit_line}{ua_suffix}\n")
    except Exception:
        pass
    return response


# ---------------------------------------------------------------------------
# Localization middleware (small, kept here alongside logger for app.py wiring)
# ---------------------------------------------------------------------------
async def add_localization_context(request: Request, call_next):
    lang = i18n.get_locale(request)
    request.state.lang = lang
    response = await call_next(request)
    if "lang" in request.query_params:
        response.set_cookie(key="mtgabyss_lang", value=lang, max_age=31536000, path="/")
    return response


def register_access_logger(app):
    """Register the access logger and localization middlewares on the FastAPI app."""
    app.middleware("http")(request_logger_middleware)
    app.middleware("http")(add_localization_context)
