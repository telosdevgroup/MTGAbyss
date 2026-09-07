#!/usr/bin/env python3
"""
blast_all.py — Unified AvaScry Multi-Game Network SiteBlaster 9001.

Orchestrates SiteBlaster invariant and route validation across all active games:
- MTG (Magic: The Gathering / avascry.com)
- Dominion (Rio Grande Games / dominion.avascry.com)
- SWU (Star Wars: Unlimited / swu.avascry.com)

Usage:
    python scripts/blast_all.py --quick
    python scripts/blast_all.py --deep
    python scripts/blast_all.py --games dominion,swu
    python scripts/blast_all.py --quick --seed 42
"""

import sys
import os
import time
import argparse
from typing import List, Dict, Any, Optional

# Ensure stdout/stderr handle UTF-8 cleanly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.site_blaster import SiteBlaster
from scripts.dominion_site_blaster import DominionSiteBlaster
from scripts.swu_site_blaster import SWUSiteBlaster


def run_blasters(
    games: List[str],
    deep: bool = False,
    seed: int = 1337,
    base_url: Optional[str] = None
) -> int:
    banner = """
========================================================================
     AVASCRY MULTI-GAME NETWORK INTEGRATION TESTER (SITEBLASTER 9001)   
========================================================================
"""
    print(banner)
    print(f"Target Games: {', '.join(g.upper() for g in games)}")
    print(f"Suite Mode:   {'DEEP' if deep else 'QUICK'}")
    print(f"Random Seed:  {seed}")
    print(f"Base URL:     {base_url or 'In-Process ASGI (TestClient)'}")
    print("========================================================\n")

    registry = {
        "mtg": ("Magic: The Gathering", SiteBlaster),
        "dominion": ("Dominion", DominionSiteBlaster),
        "swu": ("Star Wars: Unlimited", SWUSiteBlaster),
    }

    results = []
    overall_start = time.time()

    for game_key in games:
        if game_key not in registry:
            print(f"\033[93m[WARN] Unknown game key: {game_key}. Skipping.\033[0m")
            continue

        label, blaster_cls = registry[game_key]
        print(f"\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        print(f" BLASTING GAME: {label.upper()} ({game_key})")
        print(f"<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

        t0 = time.time()
        blaster = blaster_cls(base_url=base_url, deep=deep, seed=seed)
        exit_code = blaster.run_all()
        t1 = time.time()
        elapsed = t1 - t0

        results.append({
            "key": game_key,
            "label": label,
            "passed": blaster.passed,
            "failed": blaster.failed,
            "warnings": blaster.warnings,
            "elapsed": elapsed,
            "exit_code": exit_code,
            "failures_recap": getattr(blaster, "failures_recap", []),
            "warnings_recap": getattr(blaster, "warnings_recap", [])
        })

    total_elapsed = time.time() - overall_start
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_warnings = sum(r["warnings"] for r in results)

    # Consolidated Results Table
    print("\n" + "=" * 76)
    print("                 NETWORK SUITE EXECUTION SUMMARY                    ")
    print("=" * 76)
    mode_str = "Deep" if deep else "Quick"
    print(f"| {'Game':<22} | {'Mode':<6} | {'Passed':>7} | {'Failed':>7} | {'Warn':>5} | {'Time':>7} | {'Status':<6} |")
    print("|" + "-" * 24 + "|" + "-" * 8 + "|" + "-" * 9 + "|" + "-" * 9 + "|" + "-" * 7 + "|" + "-" * 9 + "|" + "-" * 8 + "|")

    for r in results:
        status = "\033[92mPASS\033[0m  " if r["failed"] == 0 else "\033[91mFAIL\033[0m  "
        print(f"| {r['label']:<22} | {mode_str:<6} | {r['passed']:>7} | {r['failed']:>7} | {r['warnings']:>5} | {r['elapsed']:>6.2f}s | {status} |")

    print("|" + "=" * 24 + "|" + "=" * 8 + "|" + "=" * 9 + "|" + "=" * 9 + "|" + "=" * 7 + "|" + "=" * 9 + "|" + "=" * 8 + "|")
    overall_status = "\033[92mPASS\033[0m  " if total_failed == 0 else "\033[91mFAIL\033[0m  "
    print(f"| {'TOTAL':<22} | {mode_str:<6} | {total_passed:>7} | {total_failed:>7} | {total_warnings:>5} | {total_elapsed:>6.2f}s | {overall_status} |")
    print("=" * 76)

    # Recaps if any failures or warnings
    if total_failed > 0:
        print("\n" + "=" * 76)
        print(f" FAILURES RECAP ({total_failed} TOTAL)")
        print("=" * 76)
        for r in results:
            if r["failures_recap"]:
                print(f"\n--- {r['label']} Failures ({len(r['failures_recap'])}) ---")
                for f in r["failures_recap"]:
                    extra = f" -> {f['reason']}" if f.get('reason') else ""
                    print(f"\033[91m[FAIL]\033[0m {f.get('category', ''):<20} {f.get('message', '')}{extra}")
                    for k, v in f.get("details", {}).items():
                        print(f"       \033[90m{k} = {v}\033[0m")

    if total_failed == 0:
        print("\n\033[92mALL NETWORKS GO. ALL GAMES SECURED. MULTIVERSE IN EQUILIBRIUM.\033[0m\n")
        return 0
    else:
        print(f"\n\033[91mNETWORK ATTENTION NEEDED: {total_failed} total failures across games.\033[0m\n")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Unified AvaScry Network SiteBlaster 9001")
    parser.add_argument("--deep", action="store_true", help="Run comprehensive deep suite across all games")
    parser.add_argument("--quick", action="store_true", help="Run fast quick suite across all games (default)")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic random seed (default: 1337)")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL of live server. Defaults to in-process ASGI.")
    parser.add_argument(
        "--games",
        type=str,
        default="all",
        help="Comma-separated list of games to blast: all, mtg, dominion, swu (default: all)"
    )
    args = parser.parse_args()

    games_arg = args.games.strip().lower()
    if games_arg == "all":
        selected_games = ["mtg", "dominion", "swu"]
    else:
        selected_games = [g.strip() for g in games_arg.split(",") if g.strip()]

    is_deep = bool(args.deep)
    exit_code = run_blasters(
        games=selected_games,
        deep=is_deep,
        seed=args.seed,
        base_url=args.base_url
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
