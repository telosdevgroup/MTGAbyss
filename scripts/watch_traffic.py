#!/usr/bin/env python3
"""
AvaScry Live Terminal Traffic Watcher & Telemetry Engine 2.0
Interactive 3-view terminal monitor with bot-isolated feeds and live MongoDB telemetry:
  [1] Traffic Spectrum, Speedometer, Locales, Sparklines & Live Feeds (Main View)
  [2] 404 Radar & Broken Link Tracker
  [3] Image Disk Cache & MongoDB WiredTiger Storage Meter
"""

import os
import sys
import re
import time
import glob
import threading
from datetime import datetime, timezone, timedelta
from collections import deque, defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Enable Windows ANSI / Virtual Terminal Processing
if os.name == 'nt':
    os.system('')

# Windows non-blocking keyboard input
try:
    import msvcrt
except ImportError:
    msvcrt = None

# Global ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Color-coded 4-letter route surface codes
ROUTE_BADGES = {
    "printing":  f"{GREEN}{BOLD}[PRIN]{RESET}",
    "similar":   f"{MAGENTA}{BOLD}[SIM ]{RESET}",
    "vector":    f"{CYAN}{BOLD}[VECT]{RESET}",
    "commander": f"{YELLOW}{BOLD}[CMDR]{RESET}",
    "artist":    f"{BLUE}{BOLD}[ARTS]{RESET}",
    "set":       f"{YELLOW}[SETS]{RESET}",
    "images":    f"{BLUE}[IMG ]{RESET}",
    "sitemap":   f"{YELLOW}[MAP ]{RESET}",
    "home":      f"{CYAN}[HOME]{RESET}",
    "decks":     f"{MAGENTA}[DECK]{RESET}",
    "assets":    f"{DIM}[ASST]{RESET}",
    "other":     f"{DIM}[OTHR]{RESET}"
}

# Site badges for AvaScry multi-subsite network
SITE_BADGES = {
    "mtg": f"{YELLOW}{BOLD}[MTG ]{RESET}",
    "dom": f"{CYAN}{BOLD}[DOM ]{RESET}",
    "swu": f"{MAGENTA}{BOLD}[SWU ]{RESET}",
    "other": f"{DIM}[SCRY]{RESET}"
}

# Format badges
FORMAT_BADGES = {
    "html": f"{CYAN}[HTML]{RESET}",
    "md":   f"{MAGENTA}{BOLD}[MD  ]{RESET}",
    "json": f"{YELLOW}[JSON]{RESET}",
    "img":  f"{BLUE}[IMG ]{RESET}",
    "txt":  f"{YELLOW}[TXT ]{RESET}",
    "xml":  f"{YELLOW}{BOLD}[XML ]{RESET}",
    "rss":  f"{CYAN}[RSS ]{RESET}",
    "csv":  f"{GREEN}{BOLD}[CSV ]{RESET}",
    "css":  f"{BLUE}[CSS ]{RESET}",
    "js":   f"{BLUE}[JS  ]{RESET}",
    "font": f"{MAGENTA}[FONT]{RESET}",
    "zip":  f"{RED}[ZIP ]{RESET}",
    "other": f"{DIM}[OTHR]{RESET}"
}

def infer_site(site_tag: str, path: str) -> str:
    """Infer site ('mtg', 'dom', 'swu') from site badge or path."""
    st = site_tag.upper().strip() if site_tag else ""
    if "DOM" in st:
        return "dom"
    if "SWU" in st:
        return "swu"
    if "MTG" in st:
        return "mtg"
    p_lower = path.lower()
    if p_lower.startswith("/dominion"):
        return "dom"
    if p_lower.startswith("/swu"):
        return "swu"
    return "mtg"

LOG_FILE = os.environ.get("ACCESS_LOG_PATH", r"C:\avascry_data\logs\access.log")

LOG_REGEX = re.compile(
    r'^(?P<ts>\S+)\s+(?P<ip>\S+)\s+(?P<badge>\[[^\]]+\])\s+(?:\[(?P<site>[A-Z0-9_\s]+)\]\s+)?(?P<status>\d{3})\s+\(\s*(?P<lat>\d+)ms\)(?P<tags>(?:\s+\[[^\]]*\])*)\s+->\s+(?P<method>\S+)\s+(?P<path>\S+)(?:\s+"(?P<ua>[^"]*)")?'
)

SURFACE_CODE_TO_ROUTE = {
    "PRIN": "printing",
    "SIM": "similar",
    "VECT": "vector",
    "CMDR": "commander",
    "ARTS": "artist",
    "SETS": "set",
    "IMG": "images",
    "MAP": "sitemap",
    "HOME": "home",
    "DECK": "decks",
    "ASST": "assets",
    "OTHR": "other"
}

def parse_log_tags(tags_str: str):
    """Parse optional surface and content-type/format tags from log line."""
    if not tags_str:
        return "", ""
    raw_tags = [t.strip() for t in re.findall(r'\[([^\]]*)\]', tags_str)]
    tags = [t for t in raw_tags if t]
    if not tags:
        return "", ""
    if len(tags) >= 2:
        return tags[0], tags[1]
    tag = tags[0]
    fmt_names = {"HTML", "MD", "JSON", "TXT", "XML", "RSS", "CSS", "JS", "FONT", "CSV", "ZIP"}
    if tag.upper() in fmt_names:
        return "", tag
    return tag, ""

SPARK_CHARS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

IMAGE_STATS = {
    "normal_count": 0, "normal_mb": 0.0,
    "large_count": 0, "large_mb": 0.0,
    "total_count": 0, "total_mb": 0.0,
    "last_check": "Checking..."
}

MONGO_STATS = {
    "qps": 0.0,
    "conns_active": 0,
    "conns_available": 0,
    "resident_mb": 0,
    "wt_cache_mb": 0.0,
    "wt_max_mb": 0.0,
    "last_check": "Init..."
}

WEEKLY_STATS = {
    "status": "idle", # idle, loading, done
    "total_reqs": 0,
    "start_ts": None,
    "end_ts": None,
    "citations": [],
    "cat_counts": defaultdict(int),
    "route_counts": defaultdict(int),
    "type_counts": defaultdict(int),
    "status_counts": defaultdict(int),
    "top_404s": defaultdict(int),
    "last_loaded": ""
}

LANG_FLAGS = {
    "en": "[EN]",
    "es": "[ES]",
    "ja": "[JA]",
    "fr": "[FR]",
    "de": "[DE]",
    "it": "[IT]",
    "pt": "[PT]",
    "ru": "[RU]",
    "ko": "[KO]",
    "zhs": "[ZHS]",
    "zht": "[ZHT]"
}

def update_image_cache_stats_worker():
    """Background worker to check image cache size periodically."""
    while True:
        try:
            normal_files = glob.glob("public/images/normal/**/*", recursive=True)
            large_files = glob.glob("public/images/large/**/*", recursive=True)
            
            normal_files = [f for f in normal_files if os.path.isfile(f)]
            large_files = [f for f in large_files if os.path.isfile(f)]
            
            n_size = sum(os.path.getsize(f) for f in normal_files) / (1024 * 1024)
            l_size = sum(os.path.getsize(f) for f in large_files) / (1024 * 1024)
            
            IMAGE_STATS["normal_count"] = len(normal_files)
            IMAGE_STATS["normal_mb"] = n_size
            IMAGE_STATS["large_count"] = len(large_files)
            IMAGE_STATS["large_mb"] = l_size
            IMAGE_STATS["total_count"] = len(normal_files) + len(large_files)
            IMAGE_STATS["total_mb"] = n_size + l_size
            IMAGE_STATS["last_check"] = datetime.now().strftime("%H:%M:%S")
        except Exception:
            pass
        time.sleep(20)

def update_mongo_stats_worker():
    """Background worker polling MongoDB serverStatus every 2.5s."""
    last_ops = None
    last_time = None
    while True:
        try:
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from db_mongo import get_mongo_db
            db = get_mongo_db()
            status = db.command("serverStatus")
            now = time.time()
            ops = status.get("opcounters", {})
            conn = status.get("connections", {})
            mem = status.get("mem", {})
            wt = status.get("wiredTiger", {}).get("cache", {})
            lock = status.get("globalLock", {})
            
            total_ops = sum(ops.values())
            if last_ops is not None and last_time is not None:
                dt = now - last_time
                if dt > 0:
                    MONGO_STATS["qps"] = max(0.0, (total_ops - last_ops) / dt)
            last_ops = total_ops
            last_time = now
            
            MONGO_STATS["conns_current"] = conn.get("current", 0)
            MONGO_STATS["conns_active"] = conn.get("active", conn.get("current", 0))
            MONGO_STATS["conns_available"] = conn.get("available", 0)
            
            act_cli = lock.get("activeClients", {})
            cur_q = lock.get("currentQueue", {})
            MONGO_STATS["active_readers"] = act_cli.get("readers", 0)
            MONGO_STATS["active_writers"] = act_cli.get("writers", 0)
            MONGO_STATS["queued_readers"] = cur_q.get("readers", 0)
            MONGO_STATS["queued_writers"] = cur_q.get("writers", 0)

            MONGO_STATS["resident_mb"] = mem.get("resident", 0)
            MONGO_STATS["virtual_mb"] = mem.get("virtual", 0)
            MONGO_STATS["wt_cache_mb"] = wt.get("bytes currently in the cache", 0) / (1024 * 1024)
            MONGO_STATS["wt_max_mb"] = wt.get("maximum bytes configured", 0) / (1024 * 1024)
            MONGO_STATS["wt_dirty_mb"] = wt.get("tracked dirty bytes in the cache", 0) / (1024 * 1024)
            MONGO_STATS["last_check"] = datetime.now().strftime("%H:%M:%S")
        except Exception:
            pass
        time.sleep(2.5)

def classify_badge(badge: str, ip: str = "", path: str = "", ct: str = "") -> str:
    b = badge.lower()
    # 0. Watchlist Scrapers
    if "watch:" in b or "watchlist" in b:
        return "watchlist"

    # 0. Real-Time Live AI User Groundings & Citations (Lucky 7)
    if any(k in b for k in ("-user", "chatgpt-user", "claude-user", "perplexity-user", "shap-user")):
        return "citations"

    # 1. Anthropic PBC (Split Claude-Search from standard ClaudeBot)
    if "claude-search" in b or "claudesearch" in b:
        return "claude_search"
    anthropic_prefixes = ("216.73.216.", "216.73.217.", "216.73.218.", "216.73.219.")
    if "claude" in b or any(ip.startswith(p) for p in anthropic_prefixes):
        return "claude"
    # 2. Googlebot (Split between Search and Images)
    google_prefixes = ("66.249.", "64.233.", "72.14.", "66.102.", "209.85.", "142.250.", "172.217.", "172.253.", "108.177.", "74.125.")
    if "google" in b or any(ip.startswith(p) for p in google_prefixes):
        if "image" in b or ct == "[IMG]" or path.startswith(("/images/", "/image/")) or path.endswith((".jpg", ".png", ".webp", ".gif", ".ico")):
            return "google_images"
        return "google"
    # 3. Bingbot
    bing_prefixes = ("40.77.", "157.55.", "20.171.", "13.66.", "52.167.", "20.36.", "20.247.")
    if "bing" in b or any(ip.startswith(p) for p in bing_prefixes):
        return "bing"
    # 3b. Yandex
    if "yandex" in b:
        return "yandex"
    # 4. AI Crawlers & Agents
    if "meta:ai" in b or "meta-externalagent" in b:
        return "meta_ai"
    if "meta:fetcher" in b or "meta-externalfetcher" in b:
        return "meta_fetcher"
    if "meta:catalog" in b or "meta-webindexer" in b or "facebookcatalog" in b:
        return "meta_catalog"
    if "oai-search" in b or "oaisearch" in b:
        return "oai_search"
    if "openai" in b or "gptbot" in b:
        return "openai"
    if "perplexity" in b:
        return "perplexity"
    if "bytedance" in b or "bytespider" in b:
        return "bytedance"
    if "applebot" in b or "apple-search" in b:
        return "apple"
    if "amazonbot" in b or "amazon" in b:
        return "amazon"
    if "shapbot" in b or "shap" in b:
        return "shapbot"
    if any(k in b for k in ("ai:deepseek", "ai:mistral", "ai:diffbot", "ai:youbot", "ai:imagesift", "ai:commoncrawl", "ai:other", "cohere")):
        return "ai_other"
    # 5. Developer Scripts, Scanners & Spiders
    if "siteblaster" in b or "ava9001" in b:
        return "siteblaster"
    if any(k in b for k in ("dev:script", "python", "curl", "requests", "go-http", "cachewarmer")):
        return "dev_scripts"
    if "feedfetcher" in b or "feed:" in b:
        return "feed_fetcher"
    if "scanner:" in b or "ads.txt" in path or "security.txt" in path:
        return "ad_scanners"
    if "cloud:spider" in b or "spider" in b:
        return "cloud_spiders"
    # 6. Social Media & Messengers
    if "social:whatsapp" in b or "whatsapp" in b:
        return "whatsapp"
    if "social:instagram" in b or "instagram" in b:
        return "instagram"
    if "social:threads" in b or "threads" in b or "barcelona" in b:
        return "threads"
    if "social:facebook" in b or "social:meta" in b or "facebookexternalhit" in b or "facebot" in b:
        return "facebook"
    if "social:" in b or "socialbot" in b:
        return "social"
    # 7. Other Search & Scrapers
    if "crawler:" in b:
        return "other_crawlers"
    if "scraper:" in b:
        return "scrapers"
    if "shield" in b:
        return "shield"
    if "browser:" in b or "user" in b:
        return "browser"
    return "other_bots"

def classify_route(path: str) -> str:
    """Classify requested URL route into logical domain surfaces."""
    clean = path.split("?")[0].lower()
    # Strip leading sub-site prefix for surface classification
    sub_path = clean
    for prefix in ("/dominion", "/swu"):
        if sub_path.startswith(prefix):
            sub_path = sub_path[len(prefix):] or "/"
            break

    if sub_path.startswith(("/printing/", "/card/")):
        return "printing"
    elif sub_path.startswith("/similar/"):
        return "similar"
    elif sub_path.startswith(("/vector/", "/vector")):
        return "vector"
    elif sub_path.startswith("/artist/"):
        return "artist"
    elif sub_path.startswith("/set/") or sub_path in ("/sets", "/set"):
        return "set"
    elif sub_path.startswith(("/commander", "/commanders")):
        return "commander"
    elif sub_path.startswith(("/images/", "/image/")) or sub_path.endswith((".jpg", ".png", ".webp", ".gif", ".ico")):
        return "images"
    elif sub_path.startswith("/sitemap") or "sitemap" in sub_path:
        return "sitemap"
    elif sub_path in ("/", "/index", "/home", "/favicon.ico"):
        return "home"
    elif sub_path.startswith(("/deck", "/smartdeck", "/stash")):
        return "decks"
    elif sub_path.startswith(("/static/", "/assets/")) or sub_path.endswith((".css", ".js", ".woff", ".woff2", ".ttf")):
        return "assets"
    return "other"

def classify_file_type(path: str, ct_badge: str = "") -> str:
    """Classify pure MIME serialization format (HTML, MD, JSON, IMG, XML, TXT, etc.)."""
    if ct_badge:
        cb = ct_badge.upper().strip("[] ").strip()
        if cb == "MD":
            return "md"
        elif cb == "HTML":
            return "html"
        elif cb in ("JSON", "VEC"):
            return "json"
        elif cb == "IMG":
            return "img"
        elif cb == "XML":
            return "xml"
        elif cb == "RSS":
            return "rss"
        elif cb == "TXT":
            return "txt"
        elif cb == "CSS":
            return "css"
        elif cb == "JS":
            return "js"
        elif cb == "FONT":
            return "font"
        elif cb == "CSV":
            return "csv"
        elif cb == "ZIP":
            return "zip"

    clean_path = path.split("?")[0].lower()
    if clean_path.startswith("/feed/") or clean_path.endswith((".rss", ".atom")):
        return "rss"
    elif clean_path.endswith((".txt", "/robots.txt", "/llms.txt", "/security.txt")):
        return "txt"
    elif clean_path.endswith((".md", "/md")):
        return "md"
    elif clean_path.endswith((".xml", "/sitemap.xml")):
        return "xml"
    elif clean_path.endswith((".css", "/style.css")):
        return "css"
    elif clean_path.endswith((".js", "/app.js", "/bundle.js")):
        return "js"
    elif clean_path.endswith((".woff", ".woff2", ".ttf", ".eot", ".otf")):
        return "font"
    elif clean_path.endswith((".csv", ".tsv")):
        return "csv"
    elif clean_path.endswith((".zip", ".tar.gz", ".gz", ".tar")):
        return "zip"
    elif clean_path.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico", ".svg")):
        return "img"
    elif clean_path.endswith((".json", "/json")):
        return "json"
    elif clean_path.endswith((".html", ".htm")) or clean_path.endswith("/") or not os.path.splitext(clean_path)[1]:
        return "html"
    return "other"

def classify_language(path: str) -> str:
    """Extract language code from printing/card path or query param."""
    p_lower = path.lower()
    if "lang=" in p_lower:
        for l_code in LANG_FLAGS:
            if f"lang={l_code}" in p_lower:
                return l_code

    clean = p_lower.split("?")[0]
    if clean.endswith((".md", ".json", ".html")):
        clean = os.path.splitext(clean)[0]
    parts = clean.split("-")
    if len(parts) >= 2 and parts[-1] in LANG_FLAGS:
        return parts[-1]
    return "en"

def get_display_width(s: str) -> int:
    """Calculate true terminal cell display width, accounting for 2-cell CJK and emoji glyphs."""
    w = 0
    for ch in s:
        code = ord(ch)
        if (0x4E00 <= code <= 0x9FFF or
            0x3400 <= code <= 0x4DBF or
            0xAC00 <= code <= 0xD7AF or
            0x3040 <= code <= 0x30FF or
            0xFF01 <= code <= 0xFF60 or
            0x1F300 <= code <= 0x1F9FF):
            w += 2
        else:
            w += 1
    return w

def pad_display(s: str, width: int) -> str:
    """Pad string with trailing spaces based on actual terminal display cells."""
    w = get_display_width(s)
    return s + (" " * max(0, width - w))

def generate_sparkline(history: list, length: int = 30) -> str:
    """Render Unicode sparkline string from a list of integer values."""
    if not history:
        return " " * length
    data = history[-length:] if len(history) >= length else [0] * (length - len(history)) + list(history)
    max_val = max(data) if max(data) > 0 else 1
    chars = []
    for val in data:
        idx = int((val / max_val) * (len(SPARK_CHARS) - 1))
        idx = min(max(idx, 0), len(SPARK_CHARS) - 1)
        chars.append(SPARK_CHARS[idx])
    return "".join(chars)

def load_weekly_stats_worker():
    """Background worker to aggregate 7-day traffic summary instantly from RAM."""
    global WEEKLY_STATS
    if WEEKLY_STATS["status"] == "loading":
        return
    WEEKLY_STATS["status"] = "loading"
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        cutoff_iso = cutoff.isoformat()
        c_counts = defaultdict(int)
        r_counts = defaultdict(int)
        f_counts = defaultdict(int)
        s_counts = defaultdict(int)
        top_404s = defaultdict(int)
        citations = []
        total = 0
        earliest_ts_str = None
        latest_ts_str = None

        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                # Fast binary search seek for 7-day cutoff point
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                low, high, seek_pos = 0, file_size, 0
                while low <= high:
                    mid = (low + high) // 2
                    f.seek(mid)
                    if mid > 0:
                        f.readline()
                    pos = f.tell()
                    probe_line = f.readline().strip()
                    if not probe_line:
                        high = mid - 1
                        continue
                    ts_token = probe_line.split(" ", 1)[0]
                    if ts_token >= cutoff_iso:
                        seek_pos = pos
                        high = mid - 1
                    else:
                        low = mid + 1

                f.seek(seek_pos)
                # Slurp remaining 7-day slice into RAM and iterate
                raw_chunk = f.read()

            for line in raw_chunk.splitlines():
                if not line or " -> " not in line:
                    continue
                left, right = line.split(" -> ", 1)
                left_tokens = left.split()
                if len(left_tokens) < 4:
                    continue
                
                ts_str = left_tokens[0]
                if ts_str < cutoff_iso:
                    continue

                if earliest_ts_str is None:
                    earliest_ts_str = ts_str
                latest_ts_str = ts_str

                ip = left_tokens[1]
                badge = left_tokens[2]
                status_str = left_tokens[3]
                if not status_str.isdigit():
                    continue
                status = int(status_str)

                # Latency & optional ct/surface badges
                lat = 0
                lat_m = re.search(r'\(\s*(\d+)ms\)', left)
                if lat_m:
                    lat = int(lat_m.group(1))

                all_brackets = [b.strip() for b in re.findall(r'\[([^\]]*)\]', left)]
                tag_brackets = all_brackets[1:] if len(all_brackets) > 1 else []
                surface_tag, fmt_tag = "", ""
                if len(tag_brackets) >= 2:
                    surface_tag, fmt_tag = tag_brackets[0], tag_brackets[1]
                elif len(tag_brackets) == 1:
                    tag = tag_brackets[0]
                    if tag.upper() in {"HTML", "MD", "JSON", "TXT", "XML", "RSS", "CSS", "JS", "FONT", "CSV", "ZIP"}:
                        fmt_tag = tag
                    else:
                        surface_tag = tag

                ct = f"[{fmt_tag}]" if fmt_tag else ""

                # Right side: METHOD PATH
                r_parts = right.split()
                if len(r_parts) >= 2:
                    path = r_parts[1]
                elif len(r_parts) == 1:
                    path = r_parts[0]
                else:
                    path = "/"

                cat = classify_badge(badge, ip, path, ct)
                if cat == "siteblaster":
                    continue
                total += 1
                route = SURFACE_CODE_TO_ROUTE.get(surface_tag.upper()) or classify_route(path)
                ft = classify_file_type(path, ct)

                c_counts[cat] += 1
                r_counts[route] += 1
                f_counts[ft] += 1
                s_counts[status] += 1

                if status == 404:
                    clean_p = path.split("?")[0]
                    top_404s[clean_p] += 1

                if cat == "citations" or any(k in badge.lower() for k in ("-user", "chatgpt-user", "claude-user", "perplexity-user")):
                    # Quick format timestamp: "2026-09-03 04:33:40"
                    t_display = ts_str[:19].replace("T", " ")
                    citations.append({
                        "time": t_display,
                        "badge": badge,
                        "status": status,
                        "path": path,
                        "ip": ip,
                        "lat": lat,
                        "route": route,
                        "file_type": ft
                    })

        def _fmt_ts(iso_str):
            if not iso_str: return "N/A"
            try:
                dt = datetime.fromisoformat(iso_str)
                return dt.strftime("%b %d, %H:%M UTC")
            except Exception:
                return iso_str[:16]

        WEEKLY_STATS["total_reqs"] = total
        WEEKLY_STATS["start_ts"] = _fmt_ts(earliest_ts_str)
        WEEKLY_STATS["end_ts"] = _fmt_ts(latest_ts_str)
        WEEKLY_STATS["citations"] = sorted(citations, key=lambda x: x["time"], reverse=True)
        WEEKLY_STATS["cat_counts"] = c_counts
        WEEKLY_STATS["route_counts"] = r_counts
        WEEKLY_STATS["type_counts"] = f_counts
        WEEKLY_STATS["status_counts"] = s_counts
        WEEKLY_STATS["top_404s"] = top_404s
        WEEKLY_STATS["last_loaded"] = datetime.now().strftime("%H:%M:%S")
        WEEKLY_STATS["status"] = "done"
    except Exception as e:
        WEEKLY_STATS["status"] = f"error: {e}"

FILTER_NAMES = {
    "all": "All Traffic",
    "citations": "AI Citations (Real-Time Users)",
    "watchlist": "👁️ Watched Scrapers",
    "claude_search": "🔍 Claude Search (Anthropic)",
    "oai_search": "🔍 OpenAI-Search",
    "claude": "🤖 ClaudeBot (Anthropic)",
    "google": "🟢 Googlebot (Search)",
    "google_images": "🟢 Googlebot (Images)",
    "openai": "🤖 OpenAI (GPTBot)",
    "meta_ai": "🤖 Meta AI (Llama Agent)",
    "meta_fetcher": "⚡ Meta AI Real-Time Fetcher",
    "meta_catalog": "🛍️ Meta Catalog Indexer",
    "facebook": "📘 Facebook Embed",
    "whatsapp": "💬 WhatsApp Preview",
    "instagram": "📸 Instagram Embed",
    "threads": "🧵 Threads Embed",
    "perplexity": "🤖 Perplexity AI",
    "apple": "🍎 Applebot",
    "amazon": "📦 Amazonbot",
    "shapbot": "🤖 ShapBot",
    "ai_other": "🤖 Other AI (DeepSeek/CommonCrawl)",
    "dev_scripts": "🐍 Dev Scripts (Python/Curl)",
    "feed_fetcher": "📡 RSS / Feed Fetchers",
    "ad_scanners": "🛡️ Ad/Sec Scanners",
    "cloud_spiders": "☁️ Cloud Spiders",
    "other_crawlers": "🌐 Other Search Engines",
    "social": "💬 Social Embeds",
    "scrapers": "🕷️ SEO Scrapers",
    "other_bots": "👾 Other Bots",
    "browser": "👤 Headless & Unbranded",
    "bing": "🔵 Bingbot",
    "yandex": "🔴 Yandex",
    "shield": "🛡️ Shield Probes"
}

TYPE_FILTER_NAMES = {
    "all": "All Formats",
    "md": "📄 Markdown (MD)",
    "html": "🌐 HTML Pages",
    "img": "🖼️ Images (JPG/PNG/WEBP)",
    "json": "📦 JSON / API",
    "xml": "🗺️ XML / Sitemaps",
    "rss": "📡 RSS Feeds",
    "txt": "📝 Plain Text / Robots",
    "css": "🎨 CSS Stylesheets",
    "js": "⚡ JavaScript (.js)",
    "font": "🔤 Web Fonts (.woff2)",
    "csv": "📊 CSV / Bulk Data",
    "zip": "🗜️ Archives (.zip/.gz)",
    "other": "📁 Other Files"
}

ROUTE_FILTER_NAMES = {
    "all": "All Surfaces",
    "printing": "Printings / Cards",
    "similar": "Synergies / Similar",
    "vector": "Vectors (4096d)",
    "artist": "Artists / Gallery",
    "set": "Sets / Checklists",
    "commander": "Commander Hub",
    "images": "Image CDN",
    "sitemap": "Sitemaps / Index",
    "home": "Home / Root (/)",
    "decks": "Smart Deckbuilder",
    "assets": "Static CSS / JS",
    "other": "Other Routes"
}

class TrafficTracker:
    def __init__(self):
        self.start_time = datetime.now()
        self.current_view = 1 # 1: Traffic Spectrum, 2: 404 Radar, 3: Image Cache, 4: Global Locales
        self.selected_filter = "all" # Crawler filter category
        self.selected_route_filter = "all" # Domain route/surface filter
        self.selected_type_filter = "all" # Content/file format filter
        self.selected_site_filter = "all" # Subsite filter ('all', 'mtg', 'dom', 'swu')
        self.total_reqs = 0
        self.site_counts = defaultdict(int)
        self.cat_counts = defaultdict(int)
        self.route_counts = defaultdict(int)
        self.type_counts = defaultdict(int)
        self.lang_counts = defaultdict(int)
        self.lang_format_counts = defaultdict(lambda: defaultdict(int))
        self.lang_bot_counts = defaultdict(lambda: defaultdict(int))
        
        # Multi-dimensional intersection matrices
        self.source_route_counts = defaultdict(lambda: defaultdict(int))
        self.source_format_counts = defaultdict(lambda: defaultdict(int))
        self.route_source_counts = defaultdict(lambda: defaultdict(int))
        self.route_format_counts = defaultdict(lambda: defaultdict(int))
        self.format_source_counts = defaultdict(lambda: defaultdict(int))
        self.format_route_counts = defaultdict(lambda: defaultdict(int))
        self.triplet_counts = defaultdict(int) # (source, route, file_type) -> count

        self.status_counts = defaultdict(int)
        self.all_404s = {} # path -> {"count": int, "first_seen": str, "last_seen": str, "last_badge": str, "last_epoch": float}
        self.recent_hits = deque(maxlen=250) # large buffer for focused filtering
        self.citation_hits = deque(maxlen=250) # dedicated buffer for user citations to prevent eviction
        self.recent_latencies = deque(maxlen=300) # rolling latencies for stats
        
        # Second-by-second ring buffer for 60s sparklines and RPM/RPS
        self.sec_history = deque(maxlen=60)
        self.current_sec = int(time.time())
        self.current_sec_count = 0
        
        self.last_hit_epoch = time.time()
        self.pulse_idx = 0

    def reset(self):
        """Reset in-memory counters and recent hit logs."""
        self.start_time = datetime.now()
        self.total_reqs = 0
        self.site_counts = defaultdict(int)
        self.cat_counts = defaultdict(int)
        self.route_counts = defaultdict(int)
        self.type_counts = defaultdict(int)
        self.lang_counts = defaultdict(int)
        self.lang_format_counts = defaultdict(lambda: defaultdict(int))
        self.lang_bot_counts = defaultdict(lambda: defaultdict(int))
        self.source_route_counts.clear()
        self.source_format_counts.clear()
        self.route_source_counts.clear()
        self.route_format_counts.clear()
        self.format_source_counts.clear()
        self.format_route_counts.clear()
        self.triplet_counts.clear()
        self.status_counts = defaultdict(int)
        self.all_404s = {}
        self.recent_hits.clear()
        self.citation_hits.clear()
        self.recent_latencies.clear()
        self.sec_history.clear()
        self.current_sec_count = 0
        self.last_hit_epoch = time.time()

    def add_request(self, dt: datetime, cat: str, status: int, path: str, ip: str, badge: str, ct: str = "", lat: int = 0, surf_tag: str = "", site: str = ""):
        now_epoch = dt.timestamp()
        self.last_hit_epoch = time.time()
        
        site_key = site or infer_site(site, path)
        route = SURFACE_CODE_TO_ROUTE.get(surf_tag.upper()) or classify_route(path)
        file_type = classify_file_type(path, ct)
        lang = classify_language(path)

        self.total_reqs += 1
        self.site_counts[site_key] += 1
        self.cat_counts[cat] += 1
        self.route_counts[route] += 1
        self.type_counts[file_type] += 1
        self.lang_counts[lang] += 1
        self.lang_format_counts[lang][file_type] += 1
        self.lang_bot_counts[lang][cat] += 1
        
        # Track 2D & 3D intersections
        self.source_route_counts[cat][route] += 1
        self.source_format_counts[cat][file_type] += 1
        self.route_source_counts[route][cat] += 1
        self.route_format_counts[route][file_type] += 1
        self.format_source_counts[file_type][cat] += 1
        self.format_route_counts[file_type][route] += 1
        self.triplet_counts[(cat, route, file_type)] += 1

        self.status_counts[status] += 1
        
        if lat > 0:
            self.recent_latencies.append(lat)

        # Update second-by-second bucket
        req_sec = int(now_epoch)
        if req_sec == self.current_sec:
            self.current_sec_count += 1
        else:
            diff = min(req_sec - self.current_sec, 60)
            self.sec_history.append(self.current_sec_count)
            for _ in range(diff - 1):
                self.sec_history.append(0)
            self.current_sec = req_sec
            self.current_sec_count = 1
        
        # Add to live feed
        hit_record = {
            "time": dt.strftime("%H:%M:%S"),
            "badge": badge,
            "site": site_key,
            "status": status,
            "path": path,
            "ip": ip,
            "cat": cat,
            "ct": ct,
            "surf_tag": surf_tag,
            "route": route,
            "file_type": file_type,
            "lang": lang,
            "lat": lat
        }
        self.recent_hits.appendleft(hit_record)
        if cat == "citations" or any(k in badge.lower() for k in ("-user", "chatgpt-user", "claude-user", "perplexity-user")):
            self.citation_hits.appendleft(hit_record)

        # 404 Radar tracking
        if status == 404:
            clean_path = path.split("?")[0]
            if clean_path not in self.all_404s:
                self.all_404s[clean_path] = {
                    "count": 0,
                    "first_seen": dt.strftime("%H:%M:%S"),
                    "last_seen": dt.strftime("%H:%M:%S"),
                    "last_badge": badge,
                    "last_epoch": now_epoch
                }
            self.all_404s[clean_path]["count"] += 1
            self.all_404s[clean_path]["last_seen"] = dt.strftime("%H:%M:%S")
            self.all_404s[clean_path]["last_badge"] = badge
            self.all_404s[clean_path]["last_epoch"] = now_epoch

PULSE_FRAMES = ["●", "○", "•", "○"]

def render_dashboard(tracker: TrafficTracker):
    now_epoch = time.time()
    tracker.pulse_idx = (tracker.pulse_idx + 1) % len(PULSE_FRAMES)
    tot = tracker.total_reqs
    cats = tracker.cat_counts
    st = tracker.status_counts

    time_since_last = int(now_epoch - tracker.last_hit_epoch)
    last_hit_str = f"{time_since_last}s ago" if time_since_last < 60 else f"{time_since_last//60}m ago"

    # Color definitions
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    # 1. Telemetry Speedometer & AI Share Split
    recent_secs = list(tracker.sec_history) + [tracker.current_sec_count]
    last_10s_reqs = sum(recent_secs[-10:])
    rps = last_10s_reqs / 10.0
    rpm = int(rps * 60)

    ai_reqs = cats["claude"] + cats["openai"] + cats["perplexity"] + cats["bytedance"] + cats["apple"] + cats["amazon"]
    web_reqs = max(0, tot - ai_reqs)
    ai_pct = (ai_reqs / tot * 100) if tot > 0 else 0
    web_pct = (web_reqs / tot * 100) if tot > 0 else 0
    ai_split_str = f"{YELLOW}{BOLD}AI Share: {ai_pct:.1f}% AI{RESET} {DIM}({ai_reqs:,}){RESET}  |  {CYAN}Web: {web_pct:.1f}%{RESET}"

    # Sparkline string
    spark_str = generate_sparkline(recent_secs, 24)

    # 2. Locale Distribution Lines (All 11 Locales)
    total_lang = sum(tracker.lang_counts.values())
    locale_parts = []
    sorted_langs = sorted(LANG_FLAGS.keys(), key=lambda k: tracker.lang_counts[k], reverse=True)
    for l_code in sorted_langs:
        lbl = LANG_FLAGS[l_code]
        l_cnt = tracker.lang_counts[l_code]
        pct = (l_cnt / total_lang * 100) if total_lang > 0 else 0
        locale_parts.append(f"{lbl}: {pct:.0f}%")
    
    locales_row1 = " | ".join(locale_parts[:6])
    locales_row2 = " | ".join(locale_parts[6:])

    # 3. Enhanced 2-Line MongoDB Metrics
    m_qps = MONGO_STATS.get("qps", 0.0)
    m_curr_conns = MONGO_STATS.get("conns_current", 0)
    m_act_conns = MONGO_STATS.get("conns_active", 0)
    m_q_r = MONGO_STATS.get("queued_readers", 0)
    m_q_w = MONGO_STATS.get("queued_writers", 0)

    m_ram_gb = MONGO_STATS.get("resident_mb", 0) / 1024
    m_vram_gb = MONGO_STATS.get("virtual_mb", 0) / 1024
    m_wt_gb = MONGO_STATS.get("wt_cache_mb", 0) / 1024
    m_wt_max_gb = MONGO_STATS.get("wt_max_mb", 0) / 1024
    m_dirty_mb = MONGO_STATS.get("wt_dirty_mb", 0)
    wt_pct = int((m_wt_gb / m_wt_max_gb * 100)) if m_wt_max_gb > 0 else 0

    mongo_line1 = f"{BOLD}🧠 MONGO ENGINE{RESET}   {GREEN}{m_qps:>5.1f} QPS{RESET}  |  {BLUE}{m_curr_conns} Conns{RESET} ({m_act_conns} Active)  |  Queue: {GREEN if m_q_r == 0 else YELLOW}{m_q_r} Read{RESET} / {GREEN if m_q_w == 0 else RED}{m_q_w} Write"
    mongo_line2 = f"{BOLD}💾 STORAGE CACHE{RESET}  {YELLOW}{m_ram_gb:.1f} GB RAM{RESET} ({m_vram_gb:.1f} GB VMem)  |  WT Cache: {CYAN}{m_wt_gb:.1f} / {m_wt_max_gb:.1f} GB ({wt_pct}%){RESET}  |  Dirty: {m_dirty_mb:.1f} MB"

    pulse_icon = f"{GREEN}{PULSE_FRAMES[tracker.pulse_idx]}{RESET}"

    # Top Menu Navigation Bar
    tab1 = f"{BOLD}{CYAN}[1] Spectrum{RESET}" if tracker.current_view == 1 else f"{DIM}[1] Spectrum{RESET}"
    tab2 = f"{BOLD}{CYAN}[2] Storage & DB{RESET}" if tracker.current_view == 2 else f"{DIM}[2] Storage & DB{RESET}"
    tab3 = f"{BOLD}{CYAN}[3] Global Locales ({len(LANG_FLAGS)}){RESET}" if tracker.current_view == 3 else f"{DIM}[3] Locales ({len(LANG_FLAGS)}){RESET}"
    tab4 = f"{BOLD}{CYAN}[4] Pivot & Facets{RESET}" if tracker.current_view == 4 else f"{DIM}[4] Pivot & Facets{RESET}"
    tab5 = f"{BOLD}{YELLOW}[5] 7-Day Digest{RESET}" if tracker.current_view == 5 else f"{DIM}[5] 7-Day Digest{RESET}"

    output = []
    output.append(f"{CYAN}{BOLD}===================================================================================================={RESET}")
    output.append(f"  {tab1}   {tab2}   {tab3}   {tab4}   {tab5}   {DIM}(1-5 | 'r' Reset | 'q' Quit){RESET}")
    output.append(f"{CYAN}{BOLD}===================================================================================================={RESET}")

    # ==========================================
    # VIEW 1: 3-COLUMN SPECTRUM (SOURCE | ROUTE | FORMAT)
    # ==========================================
    if tracker.current_view == 1:
        output.append("")
        output.append(f"  {mongo_line1}")
        output.append(f"  {mongo_line2}")
        output.append("")
        output.append(f"{CYAN}----------------------------------------------------------------------------------------------------{RESET}")
        # Determine active counts for Column 1 (Source), Column 2 (Route), Column 3 (Format)
        if tracker.selected_filter != "all":
            # Filtered by Source (e.g. ClaudeBot)
            c_counts = defaultdict(int, {tracker.selected_filter: tracker.cat_counts[tracker.selected_filter]})
            r_counts = tracker.source_route_counts[tracker.selected_filter]
            f_counts = tracker.source_format_counts[tracker.selected_filter]
        elif tracker.selected_route_filter != "all":
            # Filtered by Route (e.g. Vectors)
            c_counts = tracker.route_source_counts[tracker.selected_route_filter]
            r_counts = {k: (tracker.route_counts[k] if k == tracker.selected_route_filter else 0) for k in tracker.route_counts}
            f_counts = tracker.route_format_counts[tracker.selected_route_filter]
        elif tracker.selected_type_filter != "all":
            # Filtered by Format (e.g. Markdown)
            c_counts = tracker.format_source_counts[tracker.selected_type_filter]
            r_counts = tracker.format_route_counts[tracker.selected_type_filter]
            f_counts = {k: (tracker.type_counts[k] if k == tracker.selected_type_filter else 0) for k in tracker.type_counts}
        else:
            # Aggregate totals
            c_counts = tracker.cat_counts
            r_counts = tracker.route_counts
            f_counts = tracker.type_counts

        # Header for 3 columns (Exact 29-cell monospace width each)
        output.append(f"  {BOLD}{'TRAFFIC SOURCE':<19} {'REQS':>9} | {'SURFACE / ROUTE':<19} {'REQS':>9} | {'CONTENT FORMAT':<19} {'REQS':>9}{RESET}")
        output.append(f"  {'-'*19} {'-'*9} | {'-'*19} {'-'*9} | {'-'*19} {'-'*9}")
        
        crawler_rows = [
            ("AI Citations", "citations", YELLOW),
            ("Claude Search", "claude_search", YELLOW),
            ("OpenAI-Search", "oai_search", YELLOW),
            ("ClaudeBot", "claude", YELLOW),
            ("Googlebot", "google", GREEN),
            ("Google Images", "google_images", GREEN),
            ("GPTBot", "openai", YELLOW),
            ("Meta AI", "meta_ai", YELLOW),
            ("Meta Fetcher", "meta_fetcher", YELLOW),
            ("Meta Catalog", "meta_catalog", YELLOW),
            ("Facebook", "facebook", MAGENTA),
            ("WhatsApp", "whatsapp", GREEN),
            ("Instagram", "instagram", MAGENTA),
            ("Threads", "threads", CYAN),
            ("Perplexity", "perplexity", YELLOW),
            ("Bingbot", "bing", BLUE),
            ("Yandex", "yandex", RED),
            ("ByteSpider", "bytedance", YELLOW),
            ("Applebot", "apple", YELLOW),
            ("Amazonbot", "amazon", YELLOW),
            ("ShapBot", "shapbot", YELLOW),
            ("Other AI Bots", "ai_other", YELLOW),
            ("Watched Bots", "watchlist", MAGENTA),
            ("Dev Scripts", "dev_scripts", GREEN),
            ("Feed Readers", "feed_fetcher", CYAN),
            ("Ad/Sec Scanners", "ad_scanners", DIM),
            ("Cloud Spiders", "cloud_spiders", DIM),
            ("Other Search", "other_crawlers", CYAN),
            ("Social Embeds", "social", MAGENTA),
            ("Scrapers", "scrapers", DIM),
            ("Other Bots", "other_bots", DIM),
            ("Probes", "shield", RED),
            ("Headless", "browser", "")
        ]

        route_rows = [
            ("Printings / Cards", "printing", CYAN),
            ("Synergies / Sim", "similar", MAGENTA),
            ("Vectors (4096d)", "vector", GREEN),
            ("Artists / Gallery", "artist", YELLOW),
            ("Sets / Checklists", "set", BLUE),
            ("Commander Hub", "commander", YELLOW),
            ("Image CDN", "images", BLUE),
            ("Sitemaps / Index", "sitemap", CYAN),
            ("Home / Root (/)", "home", GREEN),
            ("Smart Deckbuilder", "decks", MAGENTA),
            ("Static CSS / JS", "assets", DIM),
            ("Other Routes", "other", DIM)
        ]

        format_rows = [
            ("HTML Pages", "html", CYAN),
            ("Markdown (.md)", "md", MAGENTA),
            ("JSON API (.json)", "json", YELLOW),
            ("Images (JPG/PNG)", "img", BLUE),
            ("XML Sitemaps", "xml", YELLOW),
            ("Text / Robots", "txt", YELLOW),
            ("RSS Feeds", "rss", CYAN),
            ("CSS Styles", "css", BLUE),
            ("JavaScript (.js)", "js", YELLOW),
            ("Web Fonts", "font", MAGENTA),
            ("CSV / Data", "csv", GREEN),
            ("Zip Archives", "zip", RED),
            ("Other Assets", "other", DIM)
        ]

        # Filter out 0-request rows so only active traffic is displayed
        active_crawler_rows = [r for r in crawler_rows if c_counts[r[1]] > 0]
        active_route_rows = [r for r in route_rows if r_counts[r[1]] > 0]
        active_format_rows = [r for r in format_rows if f_counts[r[1]] > 0]

        # Live rank all 3 columns dynamically by active counts
        active_crawler_rows = sorted(active_crawler_rows, key=lambda x: c_counts[x[1]], reverse=True)
        active_route_rows = sorted(active_route_rows, key=lambda x: r_counts[x[1]], reverse=True)
        active_format_rows = sorted(active_format_rows, key=lambda x: f_counts[x[1]], reverse=True)

        max_rows = max(len(active_crawler_rows), len(active_route_rows), len(active_format_rows))
        if max_rows == 0:
            output.append(f"  {DIM}{pad_display('● (Waiting for traffic...)', 29)} | {pad_display('● (Waiting for traffic...)', 29)} | {pad_display('● (Waiting for traffic...)', 29)}{RESET}")
        else:
            # Cap at Top 10 rows for clean, compact layout
            max_rows = min(10, max_rows)
            for i in range(max_rows):
                c_label, c_key, c_col = active_crawler_rows[i] if i < len(active_crawler_rows) else ("", "", "")
                r_label, r_key, r_col = active_route_rows[i] if i < len(active_route_rows) else ("", "", "")
                f_label, f_key, f_col = active_format_rows[i] if i < len(active_format_rows) else ("", "", "")
                
                # 1. Crawler Col (Exact 29 cells)
                if c_key:
                    c_cnt = c_counts[c_key]
                    c_active = (tracker.selected_filter == c_key)
                    c_pre = f"{BOLD}{CYAN}▶{RESET}" if c_active else " "
                    c_bullet = f"{c_col}●{RESET}" if c_col else f"{DIM}●{RESET}"
                    c_lbl = pad_display(c_label, 17)
                    c_num = f"{c_cnt:>8,}"
                    if c_active:
                        col1 = f"{c_pre}{c_bullet} {BOLD}{CYAN}{c_lbl}{RESET} {c_num}"
                    else:
                        col1 = f"{c_pre}{c_bullet} {c_lbl} {c_num}"
                else:
                    col1 = " " * 29

                # 2. Route Col (Exact 29 cells)
                if r_key:
                    r_cnt = r_counts[r_key]
                    r_active = (tracker.selected_route_filter == r_key)
                    r_pre = f"{BOLD}{CYAN}▶{RESET}" if r_active else " "
                    r_bullet = f"{r_col}●{RESET}" if r_col else f"{DIM}●{RESET}"
                    r_lbl = pad_display(r_label, 17)
                    r_num = f"{r_cnt:>8,}"
                    if r_active:
                        col2 = f"{r_pre}{r_bullet} {BOLD}{CYAN}{r_lbl}{RESET} {r_num}"
                    else:
                        col2 = f"{r_pre}{r_bullet} {r_lbl} {r_num}"
                else:
                    col2 = " " * 29

                # 3. Format Col (Exact 29 cells)
                if f_key:
                    f_cnt = f_counts[f_key]
                    f_active = (tracker.selected_type_filter == f_key)
                    f_pre = f"{BOLD}{CYAN}▶{RESET}" if f_active else " "
                    f_bullet = f"{f_col}●{RESET}" if f_col else f"{DIM}●{RESET}"
                    f_lbl = pad_display(f_label, 17)
                    f_num = f"{f_cnt:>8,}"
                    if f_active:
                        col3 = f"{f_pre}{f_bullet} {BOLD}{CYAN}{f_lbl}{RESET} {f_num}"
                    else:
                        col3 = f"{f_pre}{f_bullet} {f_lbl} {f_num}"
                else:
                    col3 = " " * 29

                output.append(f"  {col1} | {col2} | {col3}")
        
        output.append(f"{CYAN}--------------------------------------------------------------------------------{RESET}")
        
        # Filter Status Header
        filter_key = tracker.selected_filter
        filter_label = FILTER_NAMES.get(filter_key, "All Bots")
        
        route_key = tracker.selected_route_filter
        route_label = ROUTE_FILTER_NAMES.get(route_key, "All Surfaces")

        type_key = tracker.selected_type_filter
        type_label = TYPE_FILTER_NAMES.get(type_key, "All Formats")
        
        site_key = tracker.selected_site_filter
        site_labels = {"all": "All Sites", "mtg": "MTG", "dom": "Dominion", "swu": "Star Wars"}
        site_label = site_labels.get(site_key, "All Sites")

        badges = []
        if site_key != "all":
            badges.append(f"{YELLOW}Site: {site_label}{RESET}")
        if filter_key != "all":
            badges.append(f"{YELLOW}Bot: {filter_label}{RESET}")
        if route_key != "all":
            badges.append(f"{GREEN}Surface: {route_label}{RESET}")
        if type_key != "all":
            badges.append(f"{MAGENTA}Format: {type_label}{RESET}")
        
        if badges:
            filter_summary = f"{BOLD}DRILLDOWN: {' + '.join(badges)}{RESET}  {DIM}[Press 'a' for All]{RESET}"
        else:
            filter_summary = f"{BOLD}ALL TRAFFIC & SURFACES ({tot:,} total){RESET}"

        output.append(f"  {BOLD}⚡ LIVE STREAM FEED — {filter_summary}")
        output.append(f"  {DIM}Site Keys: {YELLOW}[m] MTG{RESET} | {CYAN}[9] Dominion{RESET} | {MAGENTA}[0] Star Wars{RESET} | {DIM}[a] All Sites{RESET}")
        output.append(f"  {DIM}Bot Keys: {YELLOW}[7] Citations{RESET} | {DIM}[g] Google [c] Claude [o] OpenAI [p] Perplexity [y] Yandex [h] Headless{RESET}")
        output.append(f"  {DIM}Surface Keys: [v] Vectors [s] Synergies [k] Checklists | Format Keys: [d] Markdown [t] HTML [j] JSON [i] Image{RESET}")
        output.append(f"{CYAN}--------------------------------------------------------------------------------{RESET}")

        # Filter live hits
        USER_CITATION_BADGES = ("-user", "chatgpt-user", "claude-user", "perplexity-user", "shap-user")
        def _cat_match(h, key):
            if key == "all":
                return True
            if key == "citations":
                return h.get("cat") == "citations" or any(k in h.get("badge", "").lower() for k in USER_CITATION_BADGES)
            return h.get("cat") == key

        source_buffer = tracker.citation_hits if filter_key == "citations" else tracker.recent_hits
        matching_hits = [
            h for h in source_buffer
            if (site_key == "all" or h.get("site") == site_key) and
               _cat_match(h, filter_key) and
               (route_key == "all" or h.get("route") == route_key) and
               (type_key == "all" or h.get("file_type") == type_key)
        ]

        if not matching_hits:
            output.append(f"\n  {DIM}No recent requests matching current filters...{RESET}\n")
        else:
            limit = len(matching_hits) if filter_key == "citations" else 20
            for hit in matching_hits[:limit]:
                s_key = hit.get("site", "mtg")
                s_badge = SITE_BADGES.get(s_key, SITE_BADGES["other"])
                
                surf_tag = hit.get("surf_tag", "").strip()
                if surf_tag:
                    # Clean brackets
                    raw_surf = surf_tag.strip("[] ").strip()
                    rt_badge = ROUTE_BADGES.get(SURFACE_CODE_TO_ROUTE.get(raw_surf, ""), None)
                    if not rt_badge:
                        rt_badge = f"{GREEN}[{raw_surf:<4}]{RESET}"
                else:
                    rt = hit.get("route", "other")
                    rt_badge = ROUTE_BADGES.get(rt, f"{DIM}[OTHR]{RESET}")

                ft = hit.get("file_type", "other")
                ft_badge = FORMAT_BADGES.get(ft, f"{DIM}[OTHR]{RESET}")

                path_str = hit['path'][:56]
                output.append(f"  {s_badge} {rt_badge} {ft_badge} {path_str}")

    # ==========================================
    # VIEW 2: STORAGE & DATABASE METER
    # ==========================================
    elif tracker.current_view == 2:
        output.append(f"  {BOLD}🗄️ STORAGE, IMAGE DISK CACHE & MONGODB ENGINE:{RESET}\n")
        
        # Disk image caches
        output.append(f"  {BOLD}🖼️ Local Image Storage Cache:{RESET}")
        output.append(f"    - Normal Size Images: {BOLD}{IMAGE_STATS['normal_count']:,}{RESET} files ({IMAGE_STATS['normal_mb']:.1f} MB)")
        output.append(f"    - Large Size Images:  {BOLD}{IMAGE_STATS['large_count']:,}{RESET} files ({IMAGE_STATS['large_mb']:.1f} MB)")
        output.append(f"    - Total Disk Space:   {BOLD}{CYAN}{IMAGE_STATS['total_mb']:.1f} MB{RESET} ({IMAGE_STATS['total_count']:,} images cached)")
        output.append(f"    - Cache Index Status: {DIM}Last checked {IMAGE_STATS['last_check']}{RESET}\n")
        
        # MongoDB Engine metrics
        output.append(f"  {BOLD}🧠 MongoDB Live Performance Telemetry:{RESET}")
        output.append(f"    - Query Velocity:     {BOLD}{GREEN}{MONGO_STATS['qps']:.1f} Operations/sec{RESET}")
        output.append(f"    - Active Connections: {BOLD}{BLUE}{MONGO_STATS['conns_active']}{RESET} active / {MONGO_STATS['conns_available']:,} available pool")
        output.append(f"    - Resident Memory:    {BOLD}{YELLOW}{MONGO_STATS['resident_mb']:,} MB{RESET} ({MONGO_STATS['resident_mb']/1024:.2f} GB)")
        output.append(f"    - WiredTiger RAM Cache: {BOLD}{CYAN}{MONGO_STATS['wt_cache_mb']:.1f} MB{RESET} / {MONGO_STATS['wt_max_mb']:.1f} MB ({MONGO_STATS['wt_cache_mb']/1024:.1f} GB pinned)")

    # ==========================================
    # VIEW 3: GLOBAL LOCALES (11 LANGUAGES)
    # ==========================================
    elif tracker.current_view == 3:
        tot_langs = sum(tracker.lang_counts.values()) or 1
        output.append(f"  {BOLD}🌐 GLOBAL LOCALES & MULTI-LANGUAGE INTELLIGENCE ({len(LANG_FLAGS)} Magic Languages | {tot_langs:,} total):{RESET}\n")
        output.append(f"  {'LOCALE & LANGUAGE':<26} {'REQUESTS':>10} {'GLOBAL SHARE':>14}   {'TOP FORMAT':<18} {'PRIMARY BOT'}")
        output.append(f"  {'-'*26} {'-'*10} {'-'*14}   {'-'*18} {'-'*20}")
        
        sorted_locales = sorted(LANG_FLAGS.keys(), key=lambda k: tracker.lang_counts[k], reverse=True)
        
        LOCALE_FULL_NAMES = {
            "en": "US English (en)",
            "ja": "JP 日本語 (ja)",
            "de": "DE Deutsch (de)",
            "it": "IT Italiano (it)",
            "es": "ES Español (es)",
            "fr": "FR Français (fr)",
            "pt": "BR Português (pt)",
            "zhs": "CN 简体中文 (zhs)",
            "ru": "RU Русский (ru)",
            "zht": "TW 繁體中文 (zht)",
            "ko": "KR 한국어 (ko)"
        }
        
        for l_code in sorted_locales:
            cnt = tracker.lang_counts[l_code]
            pct = (cnt / tot_langs * 100)
            full_lbl = LOCALE_FULL_NAMES.get(l_code, f"{LANG_FLAGS.get(l_code, l_code)}")
            
            # Top format for this lang
            f_counts = tracker.lang_format_counts[l_code]
            if f_counts:
                top_f_key = max(f_counts.keys(), key=lambda k: f_counts[k])
                top_f_cnt = f_counts[top_f_key]
                top_f_pct = (top_f_cnt / cnt * 100) if cnt > 0 else 0
                top_f_str = f"{top_f_key.upper()} ({top_f_pct:.0f}%)"
            else:
                top_f_str = "HTML (100%)"
                
            # Top bot for this lang
            b_counts = tracker.lang_bot_counts[l_code]
            if b_counts:
                top_b_key = max(b_counts.keys(), key=lambda k: b_counts[k])
                top_b_cnt = b_counts[top_b_key]
                top_b_pct = (top_b_cnt / cnt * 100) if cnt > 0 else 0
                raw_b_name = FILTER_NAMES.get(top_b_key, top_b_key)
                for emo in ("🤖", "🟢", "🔵", "⭐", "👾", "👤", "🛡️", "🔍", "⚡", "🛍️", "📘", "💬", "📸", "🧵", "🐍", "👁️"):
                    raw_b_name = raw_b_name.replace(emo, "")
                top_b_name = raw_b_name.strip().split()[0]
                if top_b_key == "claude_search":
                    top_b_name = "Claude"
                elif top_b_key == "oai_search":
                    top_b_name = "OAI"
                elif top_b_key == "meta_ai":
                    top_b_name = "Meta"
                top_b_str = f"{top_b_name} ({top_b_pct:.0f}%)"
            else:
                top_b_str = "ClaudeBot (95%)"
                
            pad_lbl = pad_display(full_lbl, 26)
            col_flag = CYAN if pct > 10 else (GREEN if pct > 4 else YELLOW)
            output.append(f"  {pad_lbl} {col_flag}{cnt:>10,}{RESET} {pct:>13.1f}%   {top_f_str:<18} {top_b_str}")
        
        output.append("")
        output.append(f"  {DIM}* All 11 Magic languages rendered from RAM with deterministic localized typography.{RESET}")

    # ==========================================
    # VIEW 4: DIMENSIONAL PIVOT & FACET ANALYTICS (SUITEANALYTICS STYLE)
    # ==========================================
    elif tracker.current_view == 4:
        # Determine active pivot
        if tracker.selected_filter != "all":
            pivot_type = "SOURCE"
            pivot_val = tracker.selected_filter
            pivot_name = FILTER_NAMES.get(pivot_val, pivot_val)
        elif tracker.selected_route_filter != "all":
            pivot_type = "SURFACE"
            pivot_val = tracker.selected_route_filter
            pivot_name = ROUTE_FILTER_NAMES.get(pivot_val, pivot_val)
        elif tracker.selected_type_filter != "all":
            pivot_type = "MEDIUM"
            pivot_val = tracker.selected_type_filter
            pivot_name = TYPE_FILTER_NAMES.get(pivot_val, pivot_val)
        else:
            pivot_type = "GLOBAL"
            pivot_val = "all"
            pivot_name = "Global Traffic Overview (All Dimensions)"

        output.append(f"  {BOLD}🔀 DIMENSIONAL PIVOT & FACET MATRIX — {YELLOW}{pivot_name}{RESET}  {DIM}[Press 'a' to Reset Focus]{RESET}\n")

        # SECTION 1: TOP DIMENSIONAL FLOW TRIPLETS (Source -> Surface -> Medium)
        output.append(f"  {BOLD}🏆 TOP DIMENSIONAL TRIPLETS ({'Global' if pivot_type == 'GLOBAL' else pivot_type + ' Focused'}):{RESET}")
        output.append(f"  {'#':<3} {'SOURCE (Who)':<20} {'SURFACE (Where)':<22} {'MEDIUM (How)':<20} {'REQUESTS':>12} {'SHARE':>10}")
        output.append(f"  {'-'*3} {'-'*20} {'-'*22} {'-'*20} {'-'*12} {'-'*10}")

        # Filter triplets
        if pivot_type == "SOURCE":
            filtered_triplets = {k: v for k, v in tracker.triplet_counts.items() if k[0] == pivot_val}
            base_tot = sum(filtered_triplets.values()) or 1
        elif pivot_type == "SURFACE":
            filtered_triplets = {k: v for k, v in tracker.triplet_counts.items() if k[1] == pivot_val}
            base_tot = sum(filtered_triplets.values()) or 1
        elif pivot_type == "MEDIUM":
            filtered_triplets = {k: v for k, v in tracker.triplet_counts.items() if k[2] == pivot_val}
            base_tot = sum(filtered_triplets.values()) or 1
        else:
            filtered_triplets = tracker.triplet_counts
            base_tot = tracker.total_reqs or 1

        sorted_triplets = sorted(filtered_triplets.items(), key=lambda x: x[1], reverse=True)
        if not sorted_triplets:
            output.append(f"  {DIM}No dimensional traffic recorded yet...{RESET}")
        else:
            for idx, (trip, cnt) in enumerate(sorted_triplets[:8], 1):
                s_cat, s_route, s_med = trip
                s_src_raw = FILTER_NAMES.get(s_cat, s_cat)
                for emo in ("🤖", "🟢", "🔵", "⭐", "👾", "👤", "🛡️"):
                    s_src_raw = s_src_raw.replace(emo, "")
                s_src_name = pad_display(s_src_raw.strip().split()[0], 20)
                s_rt_name = pad_display(ROUTE_FILTER_NAMES.get(s_route, s_route), 22)
                s_med_raw = TYPE_FILTER_NAMES.get(s_med, s_med)
                for emo in ("📦", "🌐", "📄", "🖼️", "🗺️", "📡", "📝", "🎨", "⚡", "🔤", "📊", "🗜️", "📁"):
                    s_med_raw = s_med_raw.replace(emo, "")
                s_med_name = pad_display(s_med_raw.strip(), 20)
                pct = (cnt / base_tot * 100)
                pct_col = GREEN if pct > 20 else (YELLOW if pct > 5 else CYAN)
                output.append(f"  {DIM}{idx:>2}.{RESET} {s_src_name} {s_rt_name} {s_med_name} {cnt:>12,} {pct_col}{pct:>9.1f}%{RESET}")

        output.append("")

        # SECTION 2: 2-COLUMN CORRELATION MATRIX FOR ACTIVE PIVOT
        output.append(f"  {BOLD}📊 CROSS-DIMENSIONAL DISTRIBUTION FOR {YELLOW}{pivot_name.upper()}{RESET}:")
        output.append(f"  {'SURFACE DISTRIBUTION':<45} | {'MEDIUM / FORMAT DISTRIBUTION':<45}")
        output.append(f"  {'-'*45} | {'-'*45}")

        if pivot_type == "SOURCE":
            r_dist = tracker.source_route_counts[pivot_val]
            f_dist = tracker.source_format_counts[pivot_val]
        elif pivot_type == "SURFACE":
            r_dist = tracker.route_source_counts[pivot_val]
            f_dist = tracker.route_format_counts[pivot_val]
        elif pivot_type == "MEDIUM":
            r_dist = tracker.format_source_counts[pivot_val]
            f_dist = tracker.format_route_counts[pivot_val]
        else:
            r_dist = tracker.route_counts
            f_dist = tracker.type_counts

        sorted_left = sorted(r_dist.items(), key=lambda x: x[1], reverse=True)[:6]
        sorted_right = sorted(f_dist.items(), key=lambda x: x[1], reverse=True)[:6]
        max_dist_rows = max(len(sorted_left), len(sorted_right), 1)

        for i in range(max_dist_rows):
            if i < len(sorted_left):
                k_l, v_l = sorted_left[i]
                lbl_l = ROUTE_FILTER_NAMES.get(k_l, FILTER_NAMES.get(k_l, k_l))
                pct_l = (v_l / base_tot * 100) if base_tot > 0 else 0
                left_str = f"{pad_display(lbl_l, 26)} {v_l:>8,} ({pct_l:>5.1f}%)"
            else:
                left_str = " " * 45

            if i < len(sorted_right):
                k_r, v_r = sorted_right[i]
                lbl_r = TYPE_FILTER_NAMES.get(k_r, ROUTE_FILTER_NAMES.get(k_r, k_r))
                pct_r = (v_r / base_tot * 100) if base_tot > 0 else 0
                right_str = f"{pad_display(lbl_r, 26)} {v_r:>8,} ({pct_r:>5.1f}%)"
            else:
                right_str = " " * 45

            output.append(f"  {left_str} | {right_str}")

        output.append(f"{CYAN}----------------------------------------------------------------------------------------------------{RESET}")

        # SECTION 3: 4-TAG DIMENSIONAL STREAM FEED
        output.append(f"  {BOLD}⚡ LIVE DIMENSIONAL STREAM FEED — {DIM}[Source] [Surface] [Medium] [Locale] (Latency) Status -> Path{RESET}")
        output.append(f"  {DIM}Pivot Keys: [c] Claude [g] Google [o] OpenAI [v] Vectors [s] Synergies [d] Markdown [j] JSON | [a] All{RESET}")
        output.append(f"{CYAN}----------------------------------------------------------------------------------------------------{RESET}")

        USER_CITATION_BADGES = ("-user", "chatgpt-user", "claude-user", "perplexity-user")
        def _cat_match_v4(h, key):
            if key == "all":
                return True
            if key == "citations":
                return h.get("cat") == "citations" or any(k in h.get("badge", "").lower() for k in USER_CITATION_BADGES)
            return h.get("cat") == key

        source_buffer_v4 = tracker.citation_hits if tracker.selected_filter == "citations" else tracker.recent_hits
        matching_hits = [
            h for h in source_buffer_v4
            if _cat_match_v4(h, tracker.selected_filter) and
               (tracker.selected_route_filter == "all" or h.get("route") == tracker.selected_route_filter) and
               (tracker.selected_type_filter == "all" or h.get("file_type") == tracker.selected_type_filter)
        ]

        if not matching_hits:
            output.append(f"\n  {DIM}No recent requests matching active pivot filter...{RESET}\n")
        else:
            for hit in matching_hits[:18]:
                is_cit = any(k in hit['badge'].lower() for k in ("-user", "chatgpt-user", "claude-user", "perplexity-user"))
                if is_cit:
                    badge_str = f"{YELLOW}{BOLD}⭐ {hit['badge']:<12}{RESET}"
                elif "watch:" in hit['badge'].lower():
                    badge_str = f"{MAGENTA}{BOLD}👁️ {hit['badge']:<12}{RESET}"
                else:
                    badge_str = f"{hit['badge']:<15}"

                rt = hit.get("route", "other")
                rt_badge = f"{CYAN}[{pad_display(rt.upper(), 7)}]{RESET}"
                
                ft = hit.get("file_type", "other")
                ft_badge = f"{MAGENTA}[{pad_display(ft.upper(), 4)}]{RESET}"

                lg = hit.get("lang", "en").upper()
                lg_badge = f"{BLUE}[{lg}]{RESET}"

                lat_val = f"{hit.get('lat', 0):3d}ms" if hit.get('lat') else "  - "
                path_str = hit['path'][:52]

                output.append(f"  {badge_str} {rt_badge} {ft_badge} {lg_badge} ({lat_val}) -> {path_str}")

    # ==========================================
    # VIEW 5: 7-DAY WEEKLY DIGEST & CITATION LEDGER
    # ==========================================
    elif tracker.current_view == 5:
        output.append("")
        st = WEEKLY_STATS["status"]
        if st == "idle":
            output.append(f"  {YELLOW}{BOLD}⏳ 7-Day Digest has not been generated yet.{RESET}")
            output.append(f"  {CYAN}Press {BOLD}[5]{RESET}{CYAN} or {BOLD}[w]{RESET}{CYAN} to begin background aggregation of the last 7 days of traffic.{RESET}")
            threading.Thread(target=load_weekly_stats_worker, daemon=True).start()
        elif st == "loading":
            output.append(f"  {YELLOW}{BOLD}⏳ Aggregating last 7 days of traffic logs in background... please wait...{RESET}")
        elif st.startswith("error"):
            output.append(f"  {RED}{BOLD}⚠️ Error loading 7-day logs:{RESET} {st}")
        else:
            # Done - render clean weekly digest
            total = WEEKLY_STATS["total_reqs"]
            s_ts = WEEKLY_STATS["start_ts"]
            e_ts = WEEKLY_STATS["end_ts"]
            updated = WEEKLY_STATS["last_loaded"]
            cits = WEEKLY_STATS["citations"]
            c_cnts = WEEKLY_STATS["cat_counts"]
            r_cnts = WEEKLY_STATS["route_counts"]
            f_cnts = WEEKLY_STATS["type_counts"]
            top_404 = WEEKLY_STATS["top_404s"]

            output.append(f"  {BOLD}🗓️ 7-DAY PERIOD:{RESET} {CYAN}{s_ts} → {e_ts}{RESET}  |  {BOLD}TOTAL REQUESTS:{RESET} {GREEN}{total:>10,}{RESET}  |  {DIM}(Loaded at {updated} - Press [w] to Refresh){RESET}")
            output.append(f"{CYAN}----------------------------------------------------------------------------------------------------{RESET}")

            # 3-Column Summary: Top Crawlers | Top Routes | Top Formats
            output.append(f"  {BOLD}{'TOP CRAWLERS (7-DAY)':<31} | {'TOP SURFACES / ROUTES':<31} | {'CONTENT FORMATS':<31}{RESET}")
            output.append(f"  {'-'*31} | {'-'*31} | {'-'*31}")

            top_c = sorted([item for item in c_cnts.items() if item[1] > 0], key=lambda x: x[1], reverse=True)[:8]
            top_r = sorted([item for item in r_cnts.items() if item[1] > 0], key=lambda x: x[1], reverse=True)[:8]
            top_f = sorted([item for item in f_cnts.items() if item[1] > 0], key=lambda x: x[1], reverse=True)[:8]

            max_len = max(len(top_c), len(top_r), len(top_f), 1)
            for i in range(max_len):
                if i < len(top_c):
                    cat_k, cat_v = top_c[i]
                    lbl = FILTER_NAMES.get(cat_k, cat_k)
                    if len(lbl) > 19: lbl = lbl[:18] + "…"
                    col1 = f"{pad_display(lbl, 20)} {cat_v:>10,}"
                else:
                    col1 = " " * 31

                if i < len(top_r):
                    rt_k, rt_v = top_r[i]
                    lbl = ROUTE_FILTER_NAMES.get(rt_k, rt_k)
                    if len(lbl) > 19: lbl = lbl[:18] + "…"
                    col2 = f"{pad_display(lbl, 20)} {rt_v:>10,}"
                else:
                    col2 = " " * 31

                if i < len(top_f):
                    ft_k, ft_v = top_f[i]
                    lbl = TYPE_FILTER_NAMES.get(ft_k, ft_k)
                    if len(lbl) > 19: lbl = lbl[:18] + "…"
                    col3 = f"{pad_display(lbl, 20)} {ft_v:>10,}"
                else:
                    col3 = " " * 31

                output.append(f"  {col1} | {col2} | {col3}")

            output.append(f"{CYAN}----------------------------------------------------------------------------------------------------{RESET}")
            if not cits:
                output.append(f"  {DIM}No AI citations recorded in the past 7 days.{RESET}")
            else:
                for cit in cits:
                    b_str = f"{YELLOW}{BOLD}[CIT] {cit['badge']:<12}{RESET}"
                    t_str = f"{DIM}{cit['time']}{RESET}"
                    lat_str = f"({cit['lat']:3d}ms)" if cit.get('lat') else "  -   "
                    rt = cit.get("route", classify_route(cit.get("path", "")))
                    rt_badge = ROUTE_BADGES.get(rt, f"{DIM}[OTHR]{RESET}")
                    path_str = cit['path'][:56]
                    output.append(f"  {t_str} {b_str} {lat_str} {rt_badge} -> {path_str}")

    output.append(f"{CYAN}{BOLD}===================================================================================================={RESET}")

    # Clear terminal screen and print buffer
    sys.stdout.write("\033[H\033[J" + "\n".join(output) + "\n")
    sys.stdout.flush()

def check_keyboard_input(tracker: TrafficTracker):
    """Handle interactive single-key switches."""
    if not msvcrt:
        return
        
    while True:
        try:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                # View switches
                if ch == b'1':
                    tracker.current_view = 1
                    render_dashboard(tracker)
                elif ch == b'2':
                    tracker.current_view = 2
                    render_dashboard(tracker)
                elif ch == b'3':
                    tracker.current_view = 3
                    render_dashboard(tracker)
                elif ch == b'4':
                    tracker.current_view = 4
                    render_dashboard(tracker)
                elif ch == b'5':
                    tracker.current_view = 5
                    if WEEKLY_STATS["status"] == "idle":
                        threading.Thread(target=load_weekly_stats_worker, daemon=True).start()
                    render_dashboard(tracker)
                elif ch in (b'w', b'W', b'6'):
                    if tracker.current_view != 5:
                        tracker.current_view = 5
                    threading.Thread(target=load_weekly_stats_worker, daemon=True).start()
                    render_dashboard(tracker)
                # Crawler Focus Filters
                elif ch in (b'7',):
                    if tracker.selected_filter == "citations":
                        tracker.selected_filter = "all"
                    else:
                        tracker.selected_filter = "citations"
                        tracker.selected_route_filter = "all"
                        tracker.selected_type_filter = "all"
                    render_dashboard(tracker)
                # Subsite Filters
                elif ch in (b'm', b'M', b'8'):
                    tracker.selected_site_filter = "all" if tracker.selected_site_filter == "mtg" else "mtg"
                    render_dashboard(tracker)
                elif ch in (b'9',):
                    tracker.selected_site_filter = "all" if tracker.selected_site_filter == "dom" else "dom"
                    render_dashboard(tracker)
                elif ch in (b'0',):
                    tracker.selected_site_filter = "all" if tracker.selected_site_filter == "swu" else "swu"
                    render_dashboard(tracker)
                elif ch in (b'a', b'A'):
                    tracker.selected_site_filter = "all"
                    tracker.selected_filter = "all"
                    tracker.selected_route_filter = "all"
                    tracker.selected_type_filter = "all"
                    render_dashboard(tracker)
                elif ch in (b'g', b'G'):
                    if tracker.selected_filter == "google":
                        tracker.selected_filter = "google_images"
                    elif tracker.selected_filter == "google_images":
                        tracker.selected_filter = "all"
                    else:
                        tracker.selected_filter = "google"
                    render_dashboard(tracker)
                elif ch in (b'c', b'C'):
                    if tracker.selected_filter == "claude":
                        tracker.selected_filter = "claude_search"
                    elif tracker.selected_filter == "claude_search":
                        tracker.selected_filter = "all"
                    else:
                        tracker.selected_filter = "claude"
                    render_dashboard(tracker)
                elif ch in (b'o', b'O'):
                    if tracker.selected_filter == "openai":
                        tracker.selected_filter = "oai_search"
                    elif tracker.selected_filter == "oai_search":
                        tracker.selected_filter = "all"
                    else:
                        tracker.selected_filter = "openai"
                    render_dashboard(tracker)
                elif ch in (b'p', b'P'):
                    tracker.selected_filter = "all" if tracker.selected_filter == "perplexity" else "perplexity"
                    render_dashboard(tracker)
                elif ch in (b'h', b'H'):
                    tracker.selected_filter = "all" if tracker.selected_filter == "browser" else "browser"
                    render_dashboard(tracker)
                elif ch in (b'b', b'B'):
                    tracker.selected_filter = "all" if tracker.selected_filter == "bing" else "bing"
                    render_dashboard(tracker)
                elif ch in (b'y', b'Y'):
                    tracker.selected_filter = "all" if tracker.selected_filter == "yandex" else "yandex"
                    render_dashboard(tracker)
                # Surface / Route Focus Filters
                elif ch in (b'v', b'V'):
                    tracker.selected_route_filter = "all" if tracker.selected_route_filter == "vector" else "vector"
                    render_dashboard(tracker)
                elif ch in (b's', b'S'):
                    tracker.selected_route_filter = "all" if tracker.selected_route_filter == "similar" else "similar"
                    render_dashboard(tracker)
                elif ch in (b'k', b'K'):
                    tracker.selected_route_filter = "all" if tracker.selected_route_filter == "printing" else "printing"
                    render_dashboard(tracker)
                # Content / Format Focus Filters
                elif ch in (b'd', b'D'):
                    tracker.selected_type_filter = "all" if tracker.selected_type_filter == "md" else "md"
                    render_dashboard(tracker)
                elif ch in (b't', b'T'):
                    tracker.selected_type_filter = "all" if tracker.selected_type_filter == "html" else "html"
                    render_dashboard(tracker)
                elif ch in (b'i', b'I'):
                    tracker.selected_type_filter = "all" if tracker.selected_type_filter == "img" else "img"
                    render_dashboard(tracker)
                elif ch in (b'j', b'J'):
                    tracker.selected_type_filter = "all" if tracker.selected_type_filter == "json" else "json"
                    render_dashboard(tracker)
                elif ch in (b'x', b'X'):
                    tracker.selected_type_filter = "all" if tracker.selected_type_filter == "xml" else "xml"
                    render_dashboard(tracker)
                elif ch in (b'r', b'R'):
                    tracker.reset()
                    render_dashboard(tracker)
                elif ch in (b'q', b'Q', b'\x03'): # q or Ctrl+C
                    sys.exit(0)
        except Exception:
            pass
        time.sleep(0.05)

def tail_log_file(tracker: TrafficTracker, from_now: bool = False):
    """Start reading from log file and stream live incoming requests."""
    while not os.path.exists(LOG_FILE):
        time.sleep(0.5)

    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        if from_now:
            # Fast binary search seek for rolling 11-hour cutoff window
            cutoff = datetime.now(timezone.utc) - timedelta(hours=11)
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            low, high, seek_pos = 0, file_size, 0
            while low <= high:
                mid = (low + high) // 2
                f.seek(mid)
                if mid > 0:
                    f.readline()
                pos = f.tell()
                probe_line = f.readline().strip()
                if not probe_line:
                    high = mid - 1
                    continue
                ts_token = probe_line.split(" ", 1)[0]
                try:
                    probe_ts = datetime.fromisoformat(ts_token)
                except Exception:
                    high = mid - 1
                    continue
                if probe_ts >= cutoff:
                    seek_pos = pos
                    high = mid - 1
                else:
                    low = mid + 1

            f.seek(seek_pos)
            for seed_line in f:
                seed_line = seed_line.strip()
                if not seed_line:
                    continue
                m = LOG_REGEX.match(seed_line)
                if m:
                    try:
                        ts = datetime.fromisoformat(m.group("ts"))
                    except Exception:
                        ts = datetime.now(timezone.utc)
                    ip = m.group("ip")
                    badge = m.group("badge")
                    site_raw = m.group("site") or ""
                    status = int(m.group("status"))
                    path = m.group("path")
                    surf_tag, fmt_tag = parse_log_tags(m.group("tags"))
                    ct = f"[{fmt_tag}]" if fmt_tag else ""
                    cat = classify_badge(badge, ip, path, ct)
                    if cat == "siteblaster":
                        continue
                    lat_val = int(m.group("lat")) if m.group("lat") else 0
                    site_val = infer_site(site_raw, path)
                    tracker.add_request(ts, cat, status, path, ip, badge, ct, lat_val, surf_tag, site=site_val)
        while True:
            line = f.readline()
            if line:
                line = line.strip()
                if line:
                    m = LOG_REGEX.match(line)
                    if m:
                        try:
                            ts = datetime.fromisoformat(m.group("ts"))
                        except Exception:
                            ts = datetime.now(timezone.utc)
                        ip = m.group("ip")
                        badge = m.group("badge")
                        site_raw = m.group("site") or ""
                        status = int(m.group("status"))
                        method = m.group("method")
                        path = m.group("path")
                        surf_tag, fmt_tag = parse_log_tags(m.group("tags"))
                        ct = f"[{fmt_tag}]" if fmt_tag else ""
                        cat = classify_badge(badge, ip, path, ct)
                        if cat == "siteblaster":
                            continue
                        lat_val = int(m.group("lat")) if m.group("lat") else 0
                        site_val = infer_site(site_raw, path)
                        tracker.add_request(ts, cat, status, path, ip, badge, ct, lat_val, surf_tag, site=site_val)
            else:
                time.sleep(0.1)

def main():
    if "--clear" in sys.argv or "--reset" in sys.argv:
        try:
            if os.path.exists(LOG_FILE):
                # Archive old log before clearing
                ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{LOG_FILE}.{ts_str}.bak"
                with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as src, open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
                print(f"[Traffic Watcher] Archived to {backup_path} and cleared {LOG_FILE} successfully.")
        except Exception as e:
            print(f"[Traffic Watcher] Could not clear {LOG_FILE}: {e}")

    replay_all = "--replay" in sys.argv or "--all" in sys.argv
    from_now = not replay_all

    tracker = TrafficTracker()
    
    # Background threads
    threading.Thread(target=update_image_cache_stats_worker, daemon=True).start()
    threading.Thread(target=update_mongo_stats_worker, daemon=True).start()
    threading.Thread(target=tail_log_file, args=(tracker, from_now), daemon=True).start()
    if msvcrt:
        threading.Thread(target=check_keyboard_input, args=(tracker,), daemon=True).start()

    try:
        while True:
            render_dashboard(tracker)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nTraffic watcher stopped.")

if __name__ == "__main__":
    main()
