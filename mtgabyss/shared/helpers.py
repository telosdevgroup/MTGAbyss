"""
mtgabyss.shared.helpers
-----------------------
Shared utility functions and constants used by all routers.
Import from here rather than from app.py.
"""
import os
import re
import asyncio
import random
import urllib.parse
from typing import Optional, Tuple, Any
from datetime import datetime, timezone

import httpx
from fastapi import BackgroundTasks, Request
from fastapi.templating import Jinja2Templates

import i18n
from mtgabyss.shared.cache import RAM_CACHE, set_ram_cache

# ---------------------------------------------------------------------------
# Jinja2 templates instance (shared across all routers)
# ---------------------------------------------------------------------------
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

from mtgabyss.data.guides import autolink_cards
templates.env.filters["autolink_cards"] = autolink_cards


def render_template(request: Request, name: str, context: dict):
    """Render template with user session and language context auto-injected."""
    if "request" not in context:
        context["request"] = request
    if "current_lang" not in context:
        context["current_lang"] = getattr(request.state, "lang", i18n.get_locale(request))
    if "user" not in context and hasattr(request, "session"):
        context["user"] = request.session.get("user")
    return templates.TemplateResponse(request=request, name=name, context=context)


# ---------------------------------------------------------------------------
# MTG domain constants
# ---------------------------------------------------------------------------
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
_downloading_slugs: set = set()
_failed_image_urls: set = set()

# ---------------------------------------------------------------------------
# Semaphore (lazy-init inside event loop)
# ---------------------------------------------------------------------------
_DOWNLOAD_SEMAPHORE = None


def get_download_semaphore() -> asyncio.Semaphore:
    """Lazily instantiate Semaphore inside active event loop."""
    global _DOWNLOAD_SEMAPHORE
    if _DOWNLOAD_SEMAPHORE is None:
        _DOWNLOAD_SEMAPHORE = asyncio.Semaphore(4)
    return _DOWNLOAD_SEMAPHORE


# ---------------------------------------------------------------------------
# String utilities
# ---------------------------------------------------------------------------
def slugify(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^\w\s-]', '', s, flags=re.UNICODE)
    s = re.sub(r'[\s_-]+', '-', s)
    return s.strip('-')


def safe_header_segment(value: str) -> str:
    """Safely percent-encode a URI slug/segment for use in HTTP headers (strictly ASCII-compliant)."""
    return urllib.parse.quote(str(value or ""), safe="-._~")


def slug_to_name_regex(slug: str) -> re.Pattern:
    """Build a regex that matches card names regardless of stripped apostrophes, exclamation points, question marks, commas, dashes, ampersands, or // slashes."""
    clean = slug.strip().lower()
    clean = clean.replace('&', '-')
    chars = [re.escape(c) if c != '-' else r'[\s\W_]+' for c in clean]
    pattern_str = r'^[\s\W_]*' + r'[\s\W_]*'.join(chars) + r'[\s\W_]*$'
    return re.compile(pattern_str, re.IGNORECASE)


# ---------------------------------------------------------------------------
# Image URI resolution
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Image prefix map (populated by image_router on startup)
# ---------------------------------------------------------------------------
# Routers that need to resolve local image files should import IMAGE_PREFIX_MAP
# from mtgabyss.routers.image_router — it is built at startup time there.
# resolve_card_images imports it lazily to avoid circular import.
def resolve_card_images(card_doc: dict, background_tasks: Optional[BackgroundTasks] = None) -> Tuple[str, str, str]:
    """
    Check if local images exist on disk.
    Prioritizes exact set-specific printing images ({card_slug}-{set_name}* or {card_slug}-{set_code}*),
    falling back to generic card slug, and finally Scryfall direct CDN URLs.
    """
    # Lazy import to avoid circular dependency with image_router
    try:
        from mtgabyss.routers.image_router import IMAGE_PREFIX_MAP
    except ImportError:
        IMAGE_PREFIX_MAP = {"normal": {}, "large": {}}

    card_faces = card_doc.get("card_faces") or card_doc.get("raw", {}).get("card_faces", [])
    has_faces = bool(card_faces)
    slug_name = get_image_slug(card_doc, has_faces)

    # 1. Check for set-specific printing match via in-memory prefix map
    c_slug = slugify(card_doc.get("name") or "")
    set_slug = slugify(card_doc.get("set_name") or "")
    set_code = (card_doc.get("set") or "").lower()
    c_num = str(card_doc.get("collector_number") or "").strip()

    normal_filename = None
    large_filename = None

    for prefix_try in [
        f"{c_slug}-{set_slug}-{c_num}" if c_num else None,
        f"{c_slug}-{set_code}-{c_num}" if c_num else None,
        f"{c_slug}-{set_slug}",
        f"{c_slug}-{set_code}"
    ]:
        if not prefix_try:
            continue
        if not normal_filename and prefix_try in IMAGE_PREFIX_MAP.get("normal", {}):
            normal_filename = IMAGE_PREFIX_MAP["normal"][prefix_try]
        if not large_filename and prefix_try in IMAGE_PREFIX_MAP.get("large", {}):
            large_filename = IMAGE_PREFIX_MAP["large"][prefix_try]
        if normal_filename and large_filename:
            break

    normal_local_file = f"public/images/normal/{normal_filename or slug_name}"
    large_local_file = f"public/images/large/{large_filename or slug_name}"

    normal_exists = os.path.exists(normal_local_file)
    large_exists = os.path.exists(large_local_file)

    # Cache miss: get live Scryfall CDN URLs
    scryfall_small, scryfall_normal, scryfall_large = get_scryfall_direct_uris(card_doc)

    # Schedule background caching if Scryfall URLs exist
    if background_tasks and not normal_exists and (scryfall_normal or scryfall_large):
        background_tasks.add_task(
            background_cache_card_images,
            slug_name,
            scryfall_normal,
            scryfall_large
        )

    # Return local if that specific file exists, else hotlink CDN URL, else placeholder
    img_url = f"/images/normal/{normal_filename or slug_name}" if normal_exists else (scryfall_normal or f"/images/normal/{slug_name}")
    large_img_url = f"/images/large/{large_filename or slug_name}" if large_exists else (scryfall_large or img_url)
    small_img_url = scryfall_small or img_url

    return small_img_url, img_url, large_img_url


# ---------------------------------------------------------------------------
# Card lookup
# ---------------------------------------------------------------------------
def find_card_by_slug(db, slug: str) -> Optional[dict]:
    """
    High-performance multi-tier card lookup in MongoDB:
    1. Exact Title Case (1ms on indexed name)
    2. Exact unslugged as-is (1ms)
    3. Direct slug match (1ms)
    4. Comma/punctuation variants (e.g. 'Jace, the Mind Sculptor') (1-2ms)
    5. Fallback to unanchored regex (only for uncommon punctuation)
    """
    clean = slug.strip()
    unslugged = clean.replace('-', ' ')
    title_name = unslugged.title()

    # Check RAM Cache first
    cache_key = f"slug_card:{clean.lower()}"
    if cache_key in RAM_CACHE:
        return RAM_CACHE[cache_key]

    # 1. Exact Title Case & Unslugged
    card = db["cards"].find_one({"name": title_name})
    if not card and unslugged != title_name:
        card = db["cards"].find_one({"name": unslugged})

    # 1b. Standard MTG Title Casing (e.g. "Vanguard of the Rose", "Lord of the Undead")
    if not card and '-' in clean:
        words = clean.split('-')
        mtg_title = " ".join(
            w.lower() if (i > 0 and w.lower() in ("the", "of", "in", "to", "at", "for", "and", "a", "an", "on", "by", "with", "from")) else w.capitalize()
            for i, w in enumerate(words)
        )
        if mtg_title not in (title_name, unslugged):
            card = db["cards"].find_one({"name": mtg_title})

    # 2. Direct slug match
    if not card:
        card = db["cards"].find_one({"slug": clean})

    # 3. Direct hyphenated card names (e.g. "Investi-Gate")
    if not card:
        hyphen_title = "-".join(w.capitalize() for w in clean.split('-'))
        card = db["cards"].find_one({"name": hyphen_title})

    # 4. Comma & Apostrophe variants (e.g. "Jace, the Mind Sculptor", "Hero's Uncle")
    words = clean.split('-')
    if not card and len(words) >= 2:
        # 4a. Possessive apostrophes (Hero's Uncle, Gaea's Cradle)
        apos_cand = " ".join(
            (w[:-1].capitalize() + "'s") if (w.endswith('s') and not w.endswith('ss') and len(w) > 2) else w.capitalize()
            for w in words
        )
        card = db["cards"].find_one({"name": apos_cand})

        # 4b. Comma separated (Jace, the Mind Sculptor)
        if not card:
            rest = " ".join(w if w.lower() in ("the", "of", "in", "to", "at", "for", "and", "a", "an") else w.capitalize() for w in words[1:])
            card = db["cards"].find_one({"name": f"{words[0].capitalize()}, {rest}"})

    # 5. Fallback to full regex
    if not card:
        pattern = slug_to_name_regex(clean)
        card = db["cards"].find_one({"name": pattern})

    if card:
        set_ram_cache(cache_key, card)
    return card


# ---------------------------------------------------------------------------
# Commander eligibility
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Card view model builder
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# IndexNow ping
# ---------------------------------------------------------------------------
import httpx as _httpx

INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b3901b0f58d0445bb8d15a9e334df58a")


async def ping_indexnow(urls: list):
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
        async with _httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://api.indexnow.org/indexnow", json=payload)
            print(f"[IndexNow] Submitted {len(urls)} URLs. Response status: {resp.status_code}")
    except Exception as e:
        print(f"[IndexNow] Error notifying IndexNow: {e}")
