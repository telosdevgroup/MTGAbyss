"""
Host and Subdomain Router for the AvaScry Multi-Game Network.
Dispatches incoming HTTP requests by Host header:
- dominion.avascry.com -> Dominion sub-application
- starwars.avascry.com -> Star Wars sub-application
- avascry.com / fallback -> Existing MTG application (app.py)
"""

from typing import Dict, Any, Optional
from fastapi import Request

SUBDOMAIN_ROUTING_MAP: Dict[str, str] = {
    "dominion": "avascry_dominion",
    "swu": "avascry_swu",
    "necromunda": "avascry_necromunda",
    "minecraft": "avascry_minecraft",
    "lorcana": "avascry_lorcana",
    "netrunner": "avascry_netrunner",
    "onepiece": "avascry_onepiece"
}

def extract_subdomain(host: str) -> Optional[str]:
    """
    Extracts the leading game subdomain from a host string.
    e.g.:
      'dominion.avascry.com' -> 'dominion'
      'dominion.localhost:8004' -> 'dominion'
      'necromunda.avascry.com' -> 'necromunda'
      'minecraft.avascry.com' -> 'minecraft'
      'avascry.com' -> None
      'www.avascry.com' -> None
    """
    if not host:
        return None
    hostname = host.split(":")[0].lower()
    parts = hostname.split(".")
    if len(parts) >= 2:
        sub = parts[0]
        if sub in SUBDOMAIN_ROUTING_MAP:
            return sub
    return None

SITE_BADGES: Dict[str, Tuple[str, str]] = {
    "mtg": ("\033[93m[MTG ]\033[0m", "[MTG ]"),
    "dominion": ("\033[96m[DOM ]\033[0m", "[DOM ]"),
    "swu": ("\033[95m[SWU ]\033[0m", "[SWU ]"),
    "necromunda": ("\033[91m\033[1m[NECR]\033[0m", "[NECR]"),
    "minecraft": ("\033[92m[MINE]\033[0m", "[MINE]"),
    "lorcana": ("\033[94m[LORC]\033[0m", "[LORC]"),
    "netrunner": ("\033[92m[NETR]\033[0m", "[NETR]"),
    "onepiece": ("\033[91m[ONEP]\033[0m", "[ONEP]"),
}

def get_request_host(request: Request) -> str:
    """
    Extracts the host from the incoming request.
    Prioritizes 'x-forwarded-host' (used by Cloudflare / cloudflared tunnels)
    and falls back to 'host'.
    """
    forwarded = request.headers.get("x-forwarded-host")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("host", "")

def get_site_badge(host: Optional[str]) -> Tuple[str, str]:
    """
    Returns (color_badge, raw_badge) for the site, e.g. [MTG ], [DOM ], [SWU ].
    """
    sub = extract_subdomain(host) if host else None
    if sub in SITE_BADGES:
        return SITE_BADGES[sub]
    return SITE_BADGES["mtg"]


