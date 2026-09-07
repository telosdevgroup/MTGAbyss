#!/usr/bin/env python3
"""
dominion_site_blaster.py — Dominion SiteBlaster 9001: Real-entity integration & invariant tester.

Hardened non-destructive inspection runner for AvaScry Dominion (Rio Grande Games / Donald X. Vaccarino).
Exercises live/ASGI application routes, Mongo corpus data ('avascry_dominion'), Markdown representations,
JSON APIs, 1e vs 2e edition diffing, rules architectures, and machine discovery manifests.

Usage:
    python scripts/dominion_site_blaster.py --quick
    python scripts/dominion_site_blaster.py --deep
    python scripts/dominion_site_blaster.py --quick --seed 42
    python scripts/dominion_site_blaster.py --quick --base-url http://127.0.0.1:8004
"""

import sys
import os
import re
import html
import time
import random
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

import httpx
from starlette.testclient import TestClient
from db_mongo import get_mongo_db
from app import app


class DominionSiteBlaster:
    USER_AGENT = "Ava9001/1.0 (Dominion SiteBlaster 9001; AvaScry Dominion; +https://dominion.avascry.com)"

    def __init__(self, base_url: Optional[str] = None, deep: bool = False, seed: int = 1337):
        self.deep = deep
        self.seed = seed
        self.rng = random.Random(self.seed)
        self.base_url = (base_url or "https://dominion.avascry.com").rstrip("/")
        self.user_agent = self.USER_AGENT

        default_headers = {
            "User-Agent": self.user_agent,
            "Host": "dominion.avascry.com"
        }
        if base_url:
            self.client = httpx.Client(base_url=self.base_url, timeout=30.0, follow_redirects=False, headers=default_headers)
            self._is_testclient = False
        else:
            self.client = TestClient(app, base_url="https://dominion.avascry.com", follow_redirects=False, headers=default_headers)
            self._is_testclient = True

        client = get_mongo_db().client
        self.db = client["avascry_dominion"]
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.failures_recap: List[Dict[str, Any]] = []
        self.warnings_recap: List[Dict[str, Any]] = []
        self.start_time = 0.0

    def log_pass(self, category: str, message: str):
        self.passed += 1
        print(f"\033[92m[PASS]\033[0m {category:<20} {message}")

    def log_fail(self, category: str, message: str, reason: str = "", details: Optional[Dict[str, Any]] = None):
        self.failed += 1
        self.failures_recap.append({
            "category": category,
            "message": message,
            "reason": reason,
            "details": details or {}
        })
        extra = f" -> {reason}" if reason else ""
        print(f"\033[91m[FAIL]\033[0m {category:<20} {message}{extra}")
        if details:
            for k, v in details.items():
                print(f"       \033[90m{k} = {v}\033[0m")

    def log_warn(self, category: str, message: str, reason: str = "", details: Optional[Dict[str, Any]] = None):
        self.warnings += 1
        self.warnings_recap.append({
            "category": category,
            "message": message,
            "reason": reason,
            "details": details or {}
        })
        extra = f" -> {reason}" if reason else ""
        print(f"\033[93m[WARN]\033[0m {category:<20} {message}{extra}")
        if details:
            for k, v in details.items():
                print(f"       \033[90m{k} = {v}\033[0m")

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        req_headers = {"User-Agent": self.user_agent, "Host": "dominion.avascry.com"}
        if headers:
            req_headers.update(headers)
        if not path.startswith("/"):
            path = "/" + path
        return self.client.get(path, headers=req_headers)

    # =========================================================================
    # 1. CORE ROUTE SMOKE
    # =========================================================================
    def test_core_routes(self):
        print("\n--- [1/10] Running Core Route Smoke Suite ---")
        routes = [
            ("/", 200, "text/html"),
            ("/about", 200, "text/html"),
            ("/random", 307, None),
            ("/rules.md", 200, "text/markdown"),
            ("/rules.json", 200, "application/json"),
            ("/sets.md", 200, "text/markdown"),
            ("/.well-known/ai-content", 200, "text/plain"),
            ("/sitemap.xml", 200, "application/xml"),
            ("/llms.txt", 200, "text/plain"),
            ("/llms-full.txt", 200, "text/plain"),
            ("/privacy", 200, "text/html"),
            ("/terms", 200, "text/html"),
            ("/contact", 200, "text/html"),
        ]

        for path, expected_status, expected_ct in routes:
            try:
                resp = self.get(path)
                if resp.status_code == expected_status:
                    if expected_ct and expected_ct not in resp.headers.get("content-type", ""):
                        self.log_warn("core route ct", path, f"Expected {expected_ct}, got {resp.headers.get('content-type')}")
                    else:
                        self.log_pass("core route smoke", f"{path} -> {resp.status_code}")
                    
                    # Verify redirect target for /random
                    if path == "/random":
                        target = resp.headers.get("location")
                        if target:
                            # Test following the random target
                            rand_resp = self.get(target)
                            if rand_resp.status_code == 200:
                                self.log_pass("random redirect target", f"/random -> {target} -> 200 OK")
                            else:
                                self.log_fail("random redirect target", f"/random -> {target}", f"Status {rand_resp.status_code}")
                        else:
                            self.log_fail("random redirect target", "/random", "Missing Location header")
                else:
                    self.log_fail("core route smoke", path, f"Expected status {expected_status}, got {resp.status_code}")
            except Exception as e:
                self.log_fail("core route smoke", path, str(e))

    # =========================================================================
    # 2. REAL ENTITY CARDS (TRI-SURFACE: HTML, MARKDOWN, JSON)
    # =========================================================================
    def test_entity_cards(self):
        print("\n--- [2/10] Running Real Entity Tri-Surface Suite (HTML, MD, JSON) ---")
        sample_size = 35 if self.deep else 12
        cards = list(self.db.cards.find({}, {"_id": 0, "name": 1, "slug": 1, "card_kinds": 1, "is_kingdom_card": 1}))

        if not cards:
            self.log_fail("entity card sample", "Mongo collection 'cards'", "No cards found in avascry_dominion.cards")
            return

        sampled_cards = []
        sampled_slugs = set()
        # Ensure diverse card kind representation across major Dominion types
        key_kinds = ["Action", "Treasure", "Victory", "Attack", "Reaction", "Duration", "Event", "Landmark", "Project", "Way", "Ally", "Trait"]
        for kind in key_kinds:
            matching = [c for c in cards if kind.lower() in [k.lower() for k in c.get("card_kinds", [])] and c.get("slug") not in sampled_slugs]
            if matching:
                chosen = self.rng.choice(matching)
                sampled_cards.append(chosen)
                sampled_slugs.add(chosen.get("slug"))

        # Fill remaining up to sample_size
        remaining = [c for c in cards if c.get("slug") not in sampled_slugs]
        if remaining and len(sampled_cards) < sample_size:
            sampled_cards.extend(self.rng.sample(remaining, min(sample_size - len(sampled_cards), len(remaining))))

        for card in sampled_cards:
            slug = card.get("slug")
            name = card.get("name", slug)

            # 1. HTML Representation
            try:
                resp_html = self.get(f"/card/{slug}")
                if resp_html.status_code == 200:
                    text_lower = resp_html.text.lower()
                    if name.lower() in text_lower or html.unescape(name.lower()) in text_lower:
                        self.log_pass("card HTML", f"{name} (/card/{slug})")
                    else:
                        self.log_warn("card HTML", f"{name} (/card/{slug})", "Card name missing from rendered HTML")
                else:
                    self.log_fail("card HTML", f"/card/{slug}", f"Status {resp_html.status_code}")
            except Exception as e:
                self.log_fail("card HTML", f"/card/{slug}", str(e))

            # 2. Markdown Representation
            try:
                resp_md = self.get(f"/card/{slug}.md")
                if resp_md.status_code == 200:
                    if f"# {name}" in resp_md.text or name in resp_md.text:
                        self.log_pass("card Markdown", f"{name} (/card/{slug}.md)")
                    else:
                        self.log_warn("card Markdown", f"/card/{slug}.md", "Markdown missing card name header")
                else:
                    self.log_fail("card Markdown", f"/card/{slug}.md", f"Status {resp_md.status_code}")
            except Exception as e:
                self.log_fail("card Markdown", f"/card/{slug}.md", str(e))

            # 3. JSON Representation & REST Symmetry
            try:
                resp_json = self.get(f"/card/{slug}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    c_data = data.get("card", {})
                    c_name = c_data.get("name")
                    c_slug = c_data.get("slug")
                    if c_name == name and c_slug == slug:
                        self.log_pass("card JSON REST", f"{name} (/card/{slug}.json)")
                    else:
                        self.log_fail("card JSON REST", f"/card/{slug}.json", "REST symmetry mismatch with Mongo entity",
                                      {"expected_name": name, "json_name": c_name, "expected_slug": slug, "json_slug": c_slug})
                else:
                    self.log_fail("card JSON REST", f"/card/{slug}.json", f"Status {resp_json.status_code}")
            except Exception as e:
                self.log_fail("card JSON REST", f"/card/{slug}.json", str(e))

    # =========================================================================
    # 3. 1ST VS 2ND EDITION DIFF INVARIANTS
    # =========================================================================
    def test_edition_diffs(self):
        print("\n--- [3/10] Running 1st vs 2nd Edition Diff Invariants Suite ---")
        known_multi_edition = ["militia", "mine", "moat", "remodel", "village", "witch", "cellar", "market", "smithy"]
        
        for slug in known_multi_edition:
            card = self.db.cards.find_one({"slug": slug})
            if not card:
                continue

            try:
                resp_json = self.get(f"/card/{slug}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    versions = data.get("versions", [])
                    has_1e = any("1" in str(v.get("edition", "")).lower() or "1e" in str(v.get("expansion_tag", "")).lower() for v in versions)
                    has_2e = any("2" in str(v.get("edition", "")).lower() or "2e" in str(v.get("expansion_tag", "")).lower() for v in versions)
                    
                    if has_1e and has_2e:
                        self.log_pass("edition versions", f"{card['name']} has both 1e and 2e versions ({len(versions)} total)")
                    else:
                        self.log_warn("edition versions", f"{card['name']}", f"Expected 1e and 2e versions, found: {[v.get('edition') for v in versions]}")

                    # Test HTML diff rendering
                    resp_html = self.get(f"/card/{slug}")
                    if resp_html.status_code == 200 and ("1st Edition" in resp_html.text or "2nd Edition" in resp_html.text):
                        self.log_pass("edition HTML diff", f"{card['name']} diff block verified in HTML")
                    else:
                        self.log_warn("edition HTML diff", f"{card['name']}", "1st/2nd edition text comparison block not found in HTML")
                else:
                    self.log_fail("edition diff", f"/card/{slug}.json", f"Status {resp_json.status_code}")
            except Exception as e:
                self.log_fail("edition diff", f"/card/{slug}", str(e))

    # =========================================================================
    # 4. OFFICIAL RULINGS & FAQ VERIFICATION
    # =========================================================================
    def test_rulings_integrity(self):
        print("\n--- [4/10] Running Official Rulings & Rules FAQ Suite ---")
        rulings = list(self.db.rulings.find({}).limit(20))
        if not rulings:
            self.log_warn("rulings suite", "Mongo rulings", "No rulings found in avascry_dominion.rulings")
            return

        sampled_rulings = self.rng.sample(rulings, min(8, len(rulings)))
        for r in sampled_rulings:
            cid = r.get("card_id", "")
            slug = cid.replace("card:", "")
            if not slug:
                continue

            try:
                resp = self.get(f"/card/{slug}.json")
                if resp.status_code == 200:
                    data = resp.json()
                    card_rulings = data.get("rulings", [])
                    if len(card_rulings) > 0:
                        self.log_pass("card rulings JSON", f"Card '{slug}' returns {len(card_rulings)} official rulings")
                    else:
                        self.log_warn("card rulings JSON", f"Card '{slug}'", "Expected rulings in JSON output but list is empty")
                else:
                    self.log_fail("card rulings JSON", f"/card/{slug}.json", f"Status {resp.status_code}")
            except Exception as e:
                self.log_fail("card rulings JSON", f"/card/{slug}.json", str(e))

    # =========================================================================
    # 5. EXPANSIONS & SETS MANIFEST INTEGRITY
    # =========================================================================
    def test_expansions_integrity(self):
        print("\n--- [5/10] Running Expansions & Sets Manifest Suite ---")
        try:
            resp = self.get("/sets.md")
            if resp.status_code == 200:
                text = resp.text
                if "| Expansion | Code | Year | Status |" in text:
                    self.log_pass("sets manifest table", "/sets.md markdown table header present")
                else:
                    self.log_fail("sets manifest table", "/sets.md", "Missing markdown table header")

                # Verify core expansions are listed
                core_sets = ["Base", "Intrigue", "Seaside", "Prosperity", "Hinterlands", "Dark Ages"]
                for cs in core_sets:
                    if cs in text:
                        self.log_pass("sets manifest expansion", f"Expansion '{cs}' verified in manifest")
                    else:
                        self.log_warn("sets manifest expansion", f"Expansion '{cs}' not found in /sets.md")
            else:
                self.log_fail("sets manifest", "/sets.md", f"Status {resp.status_code}")
        except Exception as e:
            self.log_fail("sets manifest", "/sets.md", str(e))

    # =========================================================================
    # 6. MACHINE DISCOVERY & LLM MANIFESTS
    # =========================================================================
    def test_machine_discovery(self):
        print("\n--- [6/10] Running Machine Discovery & LLM Manifests Suite ---")
        manifests = [
            ("/llms.txt", ["# AvaScry Dominion", "https://dominion.avascry.com/"]),
            ("/llms-full.txt", ["# AvaScry Dominion", "Game: Dominion"]),
            ("/rules.md", ["# Dominion Complete Rules", "Action Phase", "Buy Phase"]),
            ("/rules.json", ["Dominion", "Donald X. Vaccarino", "Action"]),
            ("/sitemap.xml", ["<urlset", "<loc>https://dominion.avascry.com/card/"]),
        ]

        for path, expected_fragments in manifests:
            try:
                resp = self.get(path)
                if resp.status_code == 200:
                    missing = [frag for frag in expected_fragments if frag not in resp.text]
                    if not missing:
                        self.log_pass("machine discovery", f"{path} content validated")
                    else:
                        self.log_fail("machine discovery", path, f"Missing required fragments: {missing}")
                else:
                    self.log_fail("machine discovery", path, f"Status {resp.status_code}")
            except Exception as e:
                self.log_fail("machine discovery", path, str(e))

    # =========================================================================
    # 7. IMAGE DELIVERY & CDN FALLBACK
    # =========================================================================
    def test_image_delivery(self):
        print("\n--- [7/10] Running Image Delivery & CDN Fallback Suite ---")
        sample_slugs = ["chapel", "village", "witch", "militia", "market"]
        for slug in sample_slugs:
            # 1. On-demand dynamic delivery via dominion_router
            try:
                resp = self.client.get(f"/dominion/images/{slug}.jpg")
                if resp.status_code == 200:
                    ct = resp.headers.get("content-type", "")
                    if "image/jpeg" in ct:
                        self.log_pass("image dynamic serve", f"/dominion/images/{slug}.jpg (cached JPEG on disk)")
                    else:
                        self.log_warn("image dynamic serve", f"/dominion/images/{slug}.jpg", f"Unexpected content-type: {ct}")
                elif resp.status_code == 307:
                    loc = resp.headers.get("location", "")
                    if loc.startswith("http"):
                        self.log_pass("image CDN fallback", f"/dominion/images/{slug}.jpg -> 307 CDN redirect")
                    else:
                        self.log_fail("image CDN fallback", f"/dominion/images/{slug}.jpg", f"Malformed location: {loc}")
                else:
                    self.log_fail("image dynamic serve", f"/dominion/images/{slug}.jpg", f"Status {resp.status_code}")
            except Exception as e:
                self.log_fail("image dynamic serve", f"/dominion/images/{slug}.jpg", str(e))

            # 2. Subdomain delivery via Host: dominion.avascry.com /images/{slug}.jpg
            try:
                resp_sub = self.get(f"/images/{slug}.jpg")
                if resp_sub.status_code == 200:
                    self.log_pass("subdomain image serve", f"/images/{slug}.jpg")
                elif resp_sub.status_code == 307:
                    self.log_pass("subdomain image CDN", f"/images/{slug}.jpg -> 307 redirect")
                else:
                    self.log_fail("subdomain image serve", f"/images/{slug}.jpg", f"Status {resp_sub.status_code}")
            except Exception as e:
                self.log_fail("subdomain image serve", f"/images/{slug}.jpg", str(e))

            # 3. Direct static mount delivery
            try:
                resp_static = self.client.get(f"/images/dominion/{slug}.jpg")
                if resp_static.status_code == 200:
                    self.log_pass("image static serve", f"/images/dominion/{slug}.jpg")
                else:
                    self.log_warn("image static serve", f"/images/dominion/{slug}.jpg", f"Status {resp_static.status_code}")
            except Exception as e:
                self.log_fail("image static serve", f"/images/dominion/{slug}.jpg", str(e))

    # =========================================================================
    # 8. CARD SYNERGIES & MECHANICS ENGINE
    # =========================================================================
    def test_synergies_and_mechanics(self):
        print("\n--- [8/10] Running Card Synergies & Mechanics Engine Suite ---")
        known_synergies = [
            ("chapel", "Trashing"),
            ("village", "Action Engine"),
            ("witch", "Attack"),
        ]
        for slug, expected_label in known_synergies:
            try:
                resp = self.get(f"/card/{slug}")
                if resp.status_code == 200:
                    if expected_label.lower() in resp.text.lower():
                        self.log_pass("synergy engine", f"Card '{slug}' rendered synergy '{expected_label}'")
                    else:
                        self.log_warn("synergy engine", f"Card '{slug}'", f"Expected synergy '{expected_label}' in HTML")
                else:
                    self.log_fail("synergy engine", f"/card/{slug}", f"Status {resp.status_code}")
            except Exception as e:
                self.log_fail("synergy engine", f"/card/{slug}", str(e))

    # =========================================================================
    # 9. 404 & MALFORMED BOUNDARIES
    # =========================================================================
    def test_boundary_and_404(self):
        print("\n--- [9/10] Running 404 & Malformed Boundaries Suite ---")
        bogus_routes = [
            ("/card/definitely-not-a-real-dominion-card-12345", 404),
            ("/card/definitely-not-a-real-dominion-card-12345.json", 404),
            ("/card/definitely-not-a-real-dominion-card-12345.md", 404),
            ("/card/", 404),
            ("/dominion/images/definitely-not-a-real-dominion-card-12345.jpg", 404),
        ]

        for path, expected_status in bogus_routes:
            try:
                resp = self.get(path)
                if resp.status_code == expected_status:
                    self.log_pass("boundary 404", f"{path} correctly returned {resp.status_code}")
                else:
                    self.log_fail("boundary 404", path, f"Expected {expected_status}, got {resp.status_code}")
            except Exception as e:
                self.log_fail("boundary 404", path, str(e))

    # =========================================================================
    # 10. SUBDOMAIN HOST ROUTING SYMMETRY
    # =========================================================================
    def test_subdomain_routing_symmetry(self):
        print("\n--- [10/10] Running Subdomain Host Routing Symmetry Suite ---")
        try:
            # Direct path prefix on MTG app
            resp_prefix = self.client.get("/dominion", headers={"User-Agent": self.user_agent, "Host": "avascry.com"})
            # Subdomain rewrite via Host header
            resp_subdomain = self.client.get("/", headers={"User-Agent": self.user_agent, "Host": "dominion.avascry.com"})

            if resp_prefix.status_code == 200 and resp_subdomain.status_code == 200:
                self.log_pass("subdomain routing", "Both /dominion and Host: dominion.avascry.com / return 200 OK")
            else:
                self.log_fail("subdomain routing", "Host routing symmetry", 
                              f"Prefix status: {resp_prefix.status_code}, Subdomain status: {resp_subdomain.status_code}")
        except Exception as e:
            self.log_fail("subdomain routing", "Host routing check", str(e))

    # =========================================================================
    # RUNNER
    # =========================================================================
    def run_all(self) -> int:
        self.start_time = time.time()
        print("\n========================================================")
        print("  DOMINION SITEBLASTER 9001 — INVARIANT & ROUTE TESTER  ")
        print(f"  Mode: {'DEEP' if self.deep else 'QUICK'} | Seed: {self.seed}")
        print(f"  Target: {self.base_url} (ASGI In-Process: {self._is_testclient})")
        print("========================================================")

        self.test_core_routes()
        self.test_entity_cards()
        self.test_edition_diffs()
        self.test_rulings_integrity()
        self.test_expansions_integrity()
        self.test_machine_discovery()
        self.test_image_delivery()
        self.test_synergies_and_mechanics()
        self.test_boundary_and_404()
        self.test_subdomain_routing_symmetry()

        elapsed = time.time() - self.start_time

        if self.failures_recap:
            print("\n========================================================")
            print(f" FAILURES ({len(self.failures_recap)})")
            print("========================================================")
            for f in self.failures_recap:
                extra = f" -> {f['reason']}" if f['reason'] else ""
                print(f"\033[91m[FAIL]\033[0m {f['category']:<20} {f['message']}{extra}")
                for k, v in f["details"].items():
                    print(f"       \033[90m{k} = {v}\033[0m")

        if self.warnings_recap:
            print("\n========================================================")
            print(f" WARNINGS ({len(self.warnings_recap)})")
            print("========================================================")
            for w in self.warnings_recap:
                extra = f" -> {w['reason']}" if w['reason'] else ""
                print(f"\033[93m[WARN]\033[0m {w['category']:<20} {w['message']}{extra}")
                for k, v in w["details"].items():
                    print(f"       \033[90m{k} = {v}\033[0m")

        print("\n========================================================")
        print(f"Dominion SiteBlaster Summary: {self.passed} passed | {self.failed} failed | {self.warnings} warnings ({elapsed:.2f}s)")
        if self.failed == 0:
            print("\033[92m\nDOMINION LIVES. KINGDOM SECURE. ALL PROVINCES CLAIMED.\033[0m\n")
        else:
            print(f"\033[91m\nDOMINION NEEDS ATTENTION ({self.failed} failures).\033[0m\n")
        print("========================================================\n")

        return 1 if self.failed > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="Dominion SiteBlaster 9001 — Invariant & Route Tester")
    parser.add_argument("--deep", action="store_true", help="Run comprehensive deep suite with larger sample sizes")
    parser.add_argument("--quick", action="store_true", help="Run fast quick suite with targeted sample sizes (default)")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic random seed (default: 1337)")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL of live server (e.g. http://127.0.0.1:8004). Defaults to in-process ASGI.")
    args = parser.parse_args()

    is_deep = bool(args.deep)
    blaster = DominionSiteBlaster(base_url=args.base_url, deep=is_deep, seed=args.seed)
    exit_code = blaster.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
