"""Bot Verifier - Asynchronous Reverse & Forward DNS Verification

Verifies web crawlers claiming to be search engines (e.g. Googlebot) using
official reverse DNS (PTR) + forward DNS (A/AAAA) lookup standards.

All DNS lookups run asynchronously in background worker threads using public
upstream DNS resolvers (8.8.8.8, 1.1.1.1) to bypass local DNS sinkholes/filters.
Results are cached in-memory with a 24-hour TTL, ensuring ZERO latency penalty
on the active HTTP request path.
"""

import time
import threading
from typing import Dict, Tuple, Optional
import dns.resolver
import dns.reversename

# Cache format: {ip: (status, expire_timestamp)}
# Statuses: "VERIFIED", "SPOOFED", "PENDING"
_CACHE: Dict[str, Tuple[str, float]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 86400  # 24 hours

# Upstream public DNS resolver configured with fast timeouts
_resolver = dns.resolver.Resolver(configure=True)
_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
_resolver.timeout = 2.0
_resolver.lifetime = 2.5


def _is_google_hostname(hostname: str) -> bool:
    """Check if the resolved PTR hostname belongs to Google crawler domains."""
    h = hostname.rstrip(".").lower()
    return h.endswith(".googlebot.com") or h.endswith(".google.com")


def _perform_dns_verification(ip: str) -> str:
    """Synchronous verification worker executed inside a background thread.
    
    1. Reverse DNS (PTR): query the IP -> get hostname.
    2. Validate hostname ends with .googlebot.com or .google.com.
    3. Forward DNS (A): query hostname -> ensure IP matches original IP.
    """
    try:
        rev_name = dns.reversename.from_address(ip)
        ptr_answers = _resolver.resolve(rev_name, "PTR")
        
        verified = False
        for rdata in ptr_answers:
            hostname = str(rdata.target).rstrip(".")
            if _is_google_hostname(hostname):
                # Forward lookup to ensure authenticity
                try:
                    fwd_answers = _resolver.resolve(hostname, "A")
                    for fwd in fwd_answers:
                        if str(fwd).strip() == ip:
                            verified = True
                            break
                except Exception:
                    pass
                if verified:
                    break

        return "VERIFIED" if verified else "SPOOFED"
    except Exception:
        # If rDNS fails, timeouts, or NXDOMAIN, it is spoofed
        return "SPOOFED"


def _worker_task(ip: str) -> None:
    """Worker function executed in daemon thread to resolve and update cache."""
    status = _perform_dns_verification(ip)
    now = time.time()
    with _CACHE_LOCK:
        _CACHE[ip] = (status, now + _CACHE_TTL_SECONDS)


def check_googlebot(ip: str) -> str:
    """Non-blocking check for Googlebot authenticity.
    
    Returns:
        "VERIFIED": Successfully validated via rDNS and forward DNS.
        "SPOOFED": Claims Googlebot but failed DNS verification.
        "PENDING": Verification currently in flight; queued in background thread.
    """
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return "SPOOFED"

    now = time.time()
    with _CACHE_LOCK:
        cached = _CACHE.get(ip)
        if cached:
            status, expires_at = cached
            if now < expires_at:
                return status

        # Not in cache or expired -> queue background verification
        _CACHE[ip] = ("PENDING", now + 60.0)  # Pending marker for 60s
        t = threading.Thread(target=_worker_task, args=(ip,), daemon=True)
        t.start()
        return "PENDING"
