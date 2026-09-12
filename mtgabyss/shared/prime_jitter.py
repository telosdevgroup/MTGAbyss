"""
mtgabyss.shared.prime_jitter
-----------------------------
Mathematical harmonic-damping and stochastic dispersion utilities.
Anchors timeouts, retry intervals, and sample sizes to prime/pseudo-prime numbers
to eliminate constructive interference (thundering herd lockstep) and satisfy
the Central Limit Theorem (N >= 31).
"""
import random
from typing import List, Union

# Prime ladder for exponential-like backoff without power-of-two harmonic resonance
# 1.1, 2.3, 3.1, 5.3, 7.1, 11.3, 13.1, 17.3, 19.1, 23.3, 29.1, 31.3
PRIME_LADDER: List[float] = [1.123, 2.317, 3.141, 5.303, 7.129, 11.311, 13.147, 17.321, 19.183, 23.327, 29.173, 31.379]

# Statistically robust prime thresholds (N >= 31 satisfies Central Limit Theorem)
PRIME_SAMPLE_SIZES: List[int] = [7, 13, 19, 31, 67, 127, 257, 509, 1021]


def prime_jitter(base: Union[int, float], jitter_pct: float = 0.17) -> float:
    """
    Applies stochastic dispersion around a prime or prime-ish base value.
    Uses a prime percentage default (17%) to break harmonic alignment.
    
    Example:
        prime_jitter(3.1) -> 3.2415, 2.9832, etc.
    """
    # Uniform random dispersion in [-jitter_pct, +jitter_pct]
    factor = 1.0 + (random.random() * 2.0 - 1.0) * jitter_pct
    return max(0.001, round(base * factor, 4))


def get_prime_backoff(attempt: int, max_cap: float = 31.379) -> float:
    """
    Returns a prime-ish backoff delay in seconds for a given retry attempt (0-indexed).
    Combines prime ladder stepping with stochastic jitter to ensure concurrent
    retries never collide in lockstep.
    
    Sequence:
        Attempt 0 -> ~1.12s + jitter
        Attempt 1 -> ~2.31s + jitter
        Attempt 2 -> ~3.14s + jitter
        Attempt 3 -> ~5.30s + jitter
        Attempt 4 -> ~7.12s + jitter
        ...
    """
    idx = max(0, min(attempt, len(PRIME_LADDER) - 1))
    base_val = PRIME_LADDER[idx]
    jittered = prime_jitter(base_val, jitter_pct=0.13)
    return min(jittered, max_cap)


def prime_sample_size(min_required: int = 30) -> int:
    """
    Returns the nearest prime N >= 31 to satisfy the Central Limit Theorem (N >= 30)
    for statistical validity, while breaking modulo-2 and power-of-two alignment.
    """
    for p in PRIME_SAMPLE_SIZES:
        if p >= min_required and p >= 31:
            return p
    return 31
