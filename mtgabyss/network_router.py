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
    "starwars": "avascry_starwars",
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
