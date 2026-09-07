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

# =========================================================================
# HIGH-SPEED IN-MEMORY RAM CACHE (Auto-flushed Sunday night or at 64GB RAM)
# =========================================================================
RAM_CACHE: Dict[str, Any] = {}
LAST_SUNDAY_FLUSH: Optional[str] = None
MAX_CACHE_ITEMS: int = 200_000  # Max ~8-10 GB RAM footprint (safe guardrail on 128GB box)


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
