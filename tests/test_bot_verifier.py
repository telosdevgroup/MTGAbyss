import time
import pytest
from mtgabyss.shared.bot_verifier import check_googlebot, _CACHE, _CACHE_LOCK, _perform_dns_verification

def test_googlebot_real_ip_dns_verification():
    """Verify that a legitimate Google crawler IP resolves to VERIFIED."""
    # Official Googlebot crawler IP (part of 66.249.66.0/24)
    result = _perform_dns_verification("66.249.66.1")
    assert result == "VERIFIED"

def test_googlebot_fake_ip_dns_verification():
    """Verify that a fake IP claiming Googlebot resolves to SPOOFED."""
    # Cloudflare Anycast DNS IP or random VPS IP that is NOT googlebot
    result = _perform_dns_verification("1.1.1.1")
    assert result == "SPOOFED"

def test_check_googlebot_async_and_caching():
    """Verify that check_googlebot returns immediately without blocking, and caches results."""
    test_ip = "66.249.66.2"
    with _CACHE_LOCK:
        _CACHE.pop(test_ip, None)

    # First call should immediately return PENDING and start background thread
    t0 = time.time()
    status1 = check_googlebot(test_ip)
    elapsed = time.time() - t0
    assert elapsed < 0.05  # < 50ms, absolutely non-blocking
    assert status1 in ("PENDING", "VERIFIED")

    # Give background thread up to 3 seconds to finish
    max_wait = 3.0
    start = time.time()
    while time.time() - start < max_wait:
        with _CACHE_LOCK:
            if test_ip in _CACHE and _CACHE[test_ip][0] != "PENDING":
                break
        time.sleep(0.1)

    # Subsequent call should hit the cache in < 1ms
    t1 = time.time()
    status2 = check_googlebot(test_ip)
    elapsed2 = time.time() - t1
    assert elapsed2 < 0.005  # < 5ms
    assert status2 == "VERIFIED"
