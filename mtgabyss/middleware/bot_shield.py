"""
mtgabyss.middleware.bot_shield
------------------------------
Honeypot & bot-trolling shield middleware.
Intercepts WordPress/CMS exploit scanners, gzip-bombs them, and rate-limits known scraper UAs.
"""
import asyncio
import gzip
import re

from fastapi import Request
from fastapi.responses import Response

from mtgabyss.middleware.access_logger import get_client_ip

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

BLOCKED_BOT_AGENTS = (
    "applebot", "amazonbot", "amzn-searchbot", "amzn-search",
    "bytespider", "bytedance",
    "meta-externalagent", "meta-externalfetcher", "facebookbot"
)

SCRAPER_USER_AGENTS = (
    "shapbot", "gptbot", "oai-search", "cohere-ai", "diffbot", "ccbot", "commoncrawl"
)

_SCRAPER_SEMAPHORE = None


def get_scraper_semaphore() -> asyncio.Semaphore:
    global _SCRAPER_SEMAPHORE
    if _SCRAPER_SEMAPHORE is None:
        _SCRAPER_SEMAPHORE = asyncio.Semaphore(2)
    return _SCRAPER_SEMAPHORE


async def bot_probe_shield_middleware(request: Request, call_next):
    raw_path = request.url.path.lower()
    norm_path = re.sub(r'/+', '/', raw_path)

    ua = request.headers.get("user-agent", "").lower()

    # Immediate rejection for blocked bots (Applebot, Amazonbot, Meta, ByteSpider)
    if any(b in ua for b in BLOCKED_BOT_AGENTS):
        return Response(
            content="410 Gone: This resource is permanently removed and no longer exists.",
            status_code=410,
            media_type="text/plain; charset=utf-8",
            headers={"X-Shield": "Bot-Gone", "Cache-Control": "public, max-age=604800"}
        )

    is_scraper = any(s in ua for s in SCRAPER_USER_AGENTS)
    if is_scraper:
        sem = get_scraper_semaphore()
        if sem.locked():
            return Response(
                content="Rate limit exceeded. Please back off.",
                status_code=429,
                headers={"Retry-After": "1", "X-Shield": "The-Abyss-RateLimit"}
            )
        try:
            await sem.acquire()
            return await call_next(request)
        finally:
            sem.release()

    # 1. CMS & WordPress Exploit Scanners -> Trap & Honeypot
    is_static_asset = norm_path.startswith(("/images/", "/static/", "/favicon"))
    is_cms_probe = not is_static_asset and any(k in norm_path for k in PROBE_KEYWORDS)
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


def register_bot_shield(app):
    """Register the bot shield middleware on the FastAPI app."""
    app.middleware("http")(bot_probe_shield_middleware)
