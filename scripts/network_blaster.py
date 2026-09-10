#!/usr/bin/env python3
"""
network_blaster.py — Unified AvaScry Network Release Gate.

Sequentially invokes site blasters across all AvaScry network properties:
- MTG (AvaScry apex)
- Dominion
- Star Wars Unlimited (SWU)
- Necromunda

Usage:
    python scripts/network_blaster.py --quick
    python scripts/network_blaster.py --deep
    python scripts/network_blaster.py --site dominion --quick
    python scripts/network_blaster.py --json
"""

import sys
import os
import re
import json
import time
import argparse
import subprocess
from typing import Dict, Any, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SITES = [
    {
        "id": "mtg",
        "name": "MTG",
        "script": os.path.join(SCRIPT_DIR, "site_blaster.py"),
    },
    {
        "id": "dominion",
        "name": "Dominion",
        "script": os.path.join(SCRIPT_DIR, "dominion_site_blaster.py"),
    },
    {
        "id": "swu",
        "name": "SWU",
        "script": os.path.join(SCRIPT_DIR, "swu_site_blaster.py"),
    },
    {
        "id": "necromunda",
        "name": "Necromunda",
        "script": os.path.join(SCRIPT_DIR, "necromunda_site_blaster.py"),
    },
    {
        "id": "minecraft",
        "name": "Minecraft",
        "script": os.path.join(SCRIPT_DIR, "minecraft_site_blaster.py"),
    },
]

SUMMARY_PATTERN = re.compile(
    r"(\d+)\s+passed\s*\|\s*(\d+)\s+failed(?:\s*\|\s*(\d+)\s+warnings)?",
    re.IGNORECASE,
)


def run_site(
    site: Dict[str, str],
    deep: bool,
    seed: Optional[int],
    base_url: Optional[str],
    quiet_individual: bool = False,
) -> Dict[str, Any]:
    cmd = [sys.executable, site["script"]]
    if deep:
        cmd.append("--deep")
    else:
        cmd.append("--quick")
    if seed is not None:
        cmd.extend(["--seed", str(seed)])
    if base_url:
        cmd.extend(["--base-url", base_url])

    start_time = time.perf_counter()
    output_lines = []
    returncode = 0
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=REPO_ROOT,
            bufsize=1,
        )
        if proc.stdout:
            for line in proc.stdout:
                output_lines.append(line)
                if not quiet_individual:
                    sys.stdout.write(line)
                    sys.stdout.flush()
        proc.wait()
        returncode = proc.returncode
    except Exception as exc:
        output_lines.append(str(exc))
        returncode = 1
    duration = time.perf_counter() - start_time
    output = "".join(output_lines)

    passed = 0
    failed = 0
    warnings = 0
    found_summary = False

    # Search lines backwards for the final summary line
    for line in reversed(output.splitlines()):
        match = SUMMARY_PATTERN.search(line)
        if match:
            passed = int(match.group(1))
            failed = int(match.group(2))
            warnings = int(match.group(3)) if match.group(3) else 0
            found_summary = True
            break

    # If return code was failure but no summary was found, mark as failed
    if not found_summary and returncode != 0:
        failed = 1

    return {
        "id": site["id"],
        "name": site["name"],
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "duration": round(duration, 2),
        "returncode": returncode,
        "output": output,
    }


def main():
    parser = argparse.ArgumentParser(description="AvaScry Unified NetworkBlaster Release Gate")
    parser.add_argument("--deep", action="store_true", help="Run comprehensive deep suite across sites")
    parser.add_argument("--quick", action="store_true", help="Run fast sanity check suite (default)")
    parser.add_argument("--site", choices=["mtg", "dominion", "swu", "necromunda", "all"], default="all",
                        help="Filter execution to a specific site")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--base-url", type=str, default=None, help="Optional base URL override (for local/testing)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON summary")
    parser.add_argument("--fail-fast", action="store_true", help="Stop execution immediately upon first site failure")
    parser.add_argument("--quiet-logs", action="store_true", help="Suppress individual test logs, only show summary table")
    args = parser.parse_args()

    deep = args.deep
    if not deep and not args.quick:
        # Default mode is quick unless specified
        deep = False

    target_sites = SITES
    if args.site and args.site != "all":
        target_sites = [s for s in SITES if s["id"] == args.site]

    results: List[Dict[str, Any]] = []

    if not args.json:
        mode_str = "DEEP RELEASE GATE" if deep else "QUICK SANITY GATE"
        print("=" * 60)
        print(f"Starting AvaScry NetworkBlaster [{mode_str}]")
        print(f"Target Sites: {', '.join(s['name'] for s in target_sites)}")
        print("=" * 60 + "\n", flush=True)

    for site in target_sites:
        if not args.json:
            print(f">>> Invoking {site['name']} SiteBlaster...", flush=True)
        res = run_site(
            site=site,
            deep=deep,
            seed=args.seed,
            base_url=args.base_url,
            quiet_individual=args.quiet_logs or args.json,
        )
        results.append(res)
        if args.fail_fast and (res["failed"] > 0 or res["returncode"] != 0):
            if not args.json:
                print(f"\n[FAIL-FAST] Halting immediately due to failure in {site['name']}.")
            break

    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_warnings = sum(r["warnings"] for r in results)
    total_duration = sum(r["duration"] for r in results)
    any_failures = any(r["failed"] > 0 or r["returncode"] != 0 for r in results)

    if args.json:
        json_output = {
            "mode": "deep" if deep else "quick",
            "all_passed": not any_failures,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_warnings": total_warnings,
            "total_duration_seconds": round(total_duration, 2),
            "sites": [
                {
                    "site": r["name"],
                    "id": r["id"],
                    "passed": r["passed"],
                    "failed": r["failed"],
                    "warnings": r["warnings"],
                    "duration_seconds": r["duration"],
                    "returncode": r["returncode"],
                }
                for r in results
            ],
        }
        print(json.dumps(json_output, indent=2))
    else:
        print("\n" + "=" * 60)
        print("AvaScry NetworkBlaster Summary")
        print("=" * 60)
        for r in results:
            name_padded = f"{r['name']:<13}"
            summary_str = f"{r['passed']} passed | {r['failed']} failed | {r['warnings']} warnings | {r['duration']}s"
            if r["failed"] > 0 or r["returncode"] != 0:
                summary_str += " [FAIL]"
            print(f"{name_padded} {summary_str}")

        print("-" * 60)
        print(f"NETWORK TOTAL: {total_passed:,} passed | {total_failed} failed | {total_warnings} warnings | {total_duration:.1f}s")
        if not any_failures:
            print("STATUS: ALL SITES SECURE")
        else:
            print("STATUS: NETWORK RELEASE GATE FAILED")
        print("=" * 60)

    sys.exit(1 if any_failures else 0)


if __name__ == "__main__":
    main()
