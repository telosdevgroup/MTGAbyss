"""
mtgabyss.shared.cache
---------------------
High-speed in-memory RAM cache with auto-flush on Sunday night or at 48 GB RAM usage.
All routers import RAM_CACHE, set_ram_cache, and check_periodic_cache_flush from here
so they share a single dict instance across the process.
"""
import os
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from collections import OrderedDict

# =========================================================================
# HIGH-SPEED IN-MEMORY RAM CACHE (LRU, Auto-flushed Sunday night or at 48GB RAM)
# =========================================================================
RAM_CACHE: OrderedDict[str, Any] = OrderedDict()
PAGE_CACHE: OrderedDict[str, str] = OrderedDict()
LAST_SUNDAY_FLUSH: Optional[str] = None
MAX_CACHE_ITEMS: int = 200_000  # Max ~8-10 GB RAM footprint (safe guardrail on 128GB box)
MAX_PAGE_CACHE_ITEMS: int = 100_000  # Max ~2-4 GB rendered HTML footprint


def get_ram_cache(key: str) -> Optional[Any]:
    """Retrieve item from RAM cache and mark recently used (LRU)."""
    if key in RAM_CACHE:
        RAM_CACHE.move_to_end(key)
        return RAM_CACHE[key]
    return None


def set_ram_cache(key: str, value: Any):
    """Store item in cache with LRU safety ceiling."""
    if key in RAM_CACHE:
        RAM_CACHE.move_to_end(key)
        RAM_CACHE[key] = value
        return

    if len(RAM_CACHE) >= MAX_CACHE_ITEMS:
        # Trim least recently used half to preserve hot buffer while reclaiming memory
        try:
            half_size = len(RAM_CACHE) // 2
            for _ in range(half_size):
                RAM_CACHE.popitem(last=False)
        except Exception:
            RAM_CACHE.clear()
    RAM_CACHE[key] = value


def get_page_cache(key: str) -> Optional[str]:
    """Retrieve fully rendered HTML string from RAM cache and mark recently used (LRU)."""
    if key in PAGE_CACHE:
        PAGE_CACHE.move_to_end(key)
        return PAGE_CACHE[key]
    return None


def set_page_cache(key: str, html: str):
    """Store fully rendered HTML string in RAM cache with LRU eviction."""
    if key in PAGE_CACHE:
        PAGE_CACHE.move_to_end(key)
        PAGE_CACHE[key] = html
        return

    if len(PAGE_CACHE) >= MAX_PAGE_CACHE_ITEMS:
        try:
            half_size = len(PAGE_CACHE) // 2
            for _ in range(half_size):
                PAGE_CACHE.popitem(last=False)
        except Exception:
            PAGE_CACHE.clear()
    PAGE_CACHE[key] = html


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
                for _ in range(half_count):
                    RAM_CACHE.popitem(last=False)
                LAST_SUNDAY_FLUSH = date_key
                reason = "Sunday weekly trim" if is_sunday_night else f"48GB soft-cap reached ({ram_gb:.1f}GB)"
                print(f"[RAM CACHE] Trimmed least-recently-used {half_count:,} items. Kept {len(RAM_CACHE):,} hot entries warm (Reason: {reason})")
    except Exception as e:
        print(f"[RAM CACHE] Monitor error: {e}")
