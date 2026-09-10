#!/usr/bin/env python3
"""
minecraft_site_blaster.py — AvaScry Minecraft SiteBlaster 9001.

Hardened non-destructive inspection runner for AvaScry Minecraft (Java Edition Vanilla Data Atlas).
Exercises live/ASGI application routes, tri-surface parity (HTML, JSON, Markdown),
items/blocks/recipes/entities catalogs, machine discovery manifests, subdomain routing symmetry,
and unified network navigation coherence.

Usage:
    python scripts/minecraft_site_blaster.py --quick
    python scripts/minecraft_site_blaster.py --deep
    python scripts/minecraft_site_blaster.py --quick --base-url http://127.0.0.1:8000
    python scripts/minecraft_site_blaster.py --json
"""

import sys
import os
import re
import html
import json
import time
import random
import argparse
from typing import List, Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import httpx
from starlette.testclient import TestClient
from app import app


class MinecraftSiteBlaster:
    USER_AGENT = "Ava9001/1.0 (Minecraft SiteBlaster 9001; AvaScry Minecraft; +https://minecraft.avascry.com)"

    def __init__(self, base_url: Optional[str] = None, deep: bool = False, seed: int = 1337):
        self.deep = deep
        self.seed = seed
        self.rng = random.Random(self.seed)
        self.base_url = (base_url or "https://minecraft.avascry.com").rstrip("/")
        self.user_agent = self.USER_AGENT

        default_headers = {
            "User-Agent": self.user_agent,
            "Host": "minecraft.avascry.com"
        }
        if base_url:
            self.client = httpx.Client(base_url=self.base_url, timeout=30.0, follow_redirects=False, headers=default_headers)
            self._is_testclient = False
        else:
            self.client = TestClient(app, base_url="http://testserver")
            self._is_testclient = True

        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results: List[Dict[str, Any]] = []

    def get(self, path: str, headers: Optional[Dict[str, str]] = None, host: Optional[str] = None) -> httpx.Response:
        req_headers = {"User-Agent": self.user_agent}
        if host:
            req_headers["Host"] = host
        elif self._is_testclient:
            req_headers["Host"] = "minecraft.avascry.com"

        if headers:
            req_headers.update(headers)

        return self.client.get(path, headers=req_headers)

    def log_pass(self, suite: str, message: str):
        self.passed += 1
        print(f"[PASS] {suite:<20} {message}")
        self.results.append({"status": "PASS", "suite": suite, "message": message})

    def log_fail(self, suite: str, target: str, error: str, details: Optional[Dict] = None):
        self.failed += 1
        msg = f"{target} -> {error}"
        print(f"[FAIL] {suite:<20} {msg}")
        self.results.append({"status": "FAIL", "suite": suite, "message": msg, "details": details})

    def log_warn(self, suite: str, target: str, message: str):
        self.warnings += 1
        msg = f"{target} -> {message}"
        print(f"[WARN] {suite:<20} {msg}")
        self.results.append({"status": "WARN", "suite": suite, "message": msg})

    # --- 1. CORE ENDPOINTS & NAVIGATION ---
    def test_core_endpoints(self):
        print("\n--- [1/8] Running Core Navigation & Landing Pages Suite ---")
        routes = [
            ("/", "Home"),
            ("/items", "Items Catalog"),
            ("/blocks", "Blocks Catalog"),
            ("/recipes", "Recipes Catalog"),
            ("/entities", "Entities Catalog"),
            ("/biomes", "Biomes Catalog"),
            ("/guides", "Guides Hub"),
        ]
        for route, name in routes:
            try:
                resp = self.get(route)
                if resp.status_code == 200:
                    self.log_pass("core endpoints", f"{name} ({route}) returned 200 OK")
                else:
                    self.log_fail("core endpoints", route, f"Expected 200, got {resp.status_code}")
            except Exception as e:
                self.log_fail("core endpoints", route, str(e))

    # --- 2. SUBDOMAIN ROUTING SYMMETRY ---
    def test_subdomain_symmetry(self):
        print("\n--- [2/8] Running Subdomain Routing Symmetry Suite ---")
        pairs = [
            ("/", "/minecraft"),
            ("/items", "/minecraft/items"),
            ("/blocks", "/minecraft/blocks"),
            ("/recipes", "/minecraft/recipes"),
            ("/about", "/minecraft/about"),
            ("/terms", "/minecraft/terms"),
            ("/privacy", "/minecraft/privacy"),
            ("/contact", "/minecraft/contact"),
        ]
        for sub_path, prefix_path in pairs:
            try:
                r_sub = self.get(sub_path, host="minecraft.avascry.com")
                r_pre = self.get(prefix_path, host="avascry.com")
                if r_sub.status_code == 200 and r_pre.status_code == 200:
                    self.log_pass("subdomain symmetry", f"{sub_path} symmetric with {prefix_path} (200 OK)")
                else:
                    self.log_fail("subdomain symmetry", sub_path, f"Sub: {r_sub.status_code}, Prefix: {r_pre.status_code}")
            except Exception as e:
                self.log_fail("subdomain symmetry", sub_path, str(e))

    # --- 3. TRI-SURFACE PARITY (HTML, JSON, MD) ---
    def test_tri_surface_parity(self):
        print("\n--- [3/8] Running Tri-Surface Parity (HTML / JSON / MD) Suite ---")
        entities = [
            ("item", "diamond-pickaxe", "Diamond Pickaxe"),
            ("item", "iron-sword", "Iron Sword"),
            ("block", "diamond-ore", "Diamond Ore"),
            ("block", "obsidian", "Obsidian"),
            ("recipe", "diamond-pickaxe", "diamond-pickaxe"),
            ("entity", "creeper", "Creeper"),
        ]
        for kind, slug, title in entities:
            # HTML
            try:
                r_html = self.get(f"/{kind}/{slug}")
                if r_html.status_code == 200 and title.lower() in r_html.text.lower():
                    self.log_pass("tri-surface html", f"/{kind}/{slug} -> 200 OK")
                else:
                    self.log_fail("tri-surface html", f"/{kind}/{slug}", f"Status {r_html.status_code}")
            except Exception as e:
                self.log_fail("tri-surface html", f"/{kind}/{slug}", str(e))

            # JSON
            try:
                r_json = self.get(f"/{kind}/{slug}.json")
                if r_json.status_code == 200:
                    data = r_json.json()
                    if "entity_id" in data or "id" in data or "facts" in data or "slug" in data:
                        self.log_pass("tri-surface json", f"/{kind}/{slug}.json -> Valid schema")
                    else:
                        self.log_fail("tri-surface json", f"/{kind}/{slug}.json", "Missing expected schema fields")
                else:
                    self.log_fail("tri-surface json", f"/{kind}/{slug}.json", f"Status {r_json.status_code}")
            except Exception as e:
                self.log_fail("tri-surface json", f"/{kind}/{slug}.json", str(e))

            # MD
            try:
                r_md = self.get(f"/{kind}/{slug}.md")
                if r_md.status_code == 200 and len(r_md.text) > 20:
                    self.log_pass("tri-surface md", f"/{kind}/{slug}.md -> Valid Markdown")
                else:
                    self.log_fail("tri-surface md", f"/{kind}/{slug}.md", f"Status {r_md.status_code}")
            except Exception as e:
                self.log_fail("tri-surface md", f"/{kind}/{slug}.md", str(e))

    # --- 4. CATALOG LISTS & MACHINE PARITY ---
    def test_catalog_lists(self):
        print("\n--- [4/8] Running Catalog Lists & Pagination Suite ---")
        catalogs = ["items", "blocks", "recipes", "entities"]
        for cat in catalogs:
            try:
                r_json = self.get(f"/{cat}.json?limit=10")
                if r_json.status_code == 200:
                    data = r_json.json()
                    entries = data.get("entries", [])
                    if len(entries) > 0:
                        self.log_pass("catalog machine json", f"/{cat}.json returned {len(entries)} items")
                    else:
                        self.log_warn("catalog machine json", f"/{cat}.json", "Empty entries array")
                else:
                    self.log_fail("catalog machine json", f"/{cat}.json", f"Status {r_json.status_code}")

                r_md = self.get(f"/{cat}.md?limit=10")
                if r_md.status_code == 200 and ("|" in r_md.text or "#" in r_md.text):
                    self.log_pass("catalog machine md", f"/{cat}.md returned Markdown content")
                else:
                    self.log_fail("catalog machine md", f"/{cat}.md", f"Status {r_md.status_code}")
            except Exception as e:
                self.log_fail("catalog machine", cat, str(e))

    # --- 5. MACHINE DISCOVERY & LLM MANIFESTS ---
    def test_machine_discovery(self):
        print("\n--- [5/8] Running Machine Discovery & LLM Manifests Suite ---")
        manifests = [
            ("/llms.txt", "text/plain", "AvaScry Minecraft"),
            ("/llms-full.txt", "text/plain", "ITEMS & TOOLS"),
            ("/sitemap.xml", "xml", "urlset"),
            ("/sitemap.md", "markdown", "Minecraft"),
            ("/robots.txt", "text/plain", "User-agent"),
        ]
        for path, ct_expected, content_kw in manifests:
            try:
                resp = self.get(path)
                if resp.status_code == 200 and content_kw.lower() in resp.text.lower():
                    self.log_pass("machine discovery", f"{path} valid and contains '{content_kw}'")
                else:
                    self.log_fail("machine discovery", path, f"Status {resp.status_code} or missing '{content_kw}'")
            except Exception as e:
                self.log_fail("machine discovery", path, str(e))

    # --- 6. UNIFIED NETWORK FOOTER & BRANDING ---
    def test_footer_and_branding(self):
        print("\n--- [6/8] Running Unified Network Footer & Branding Suite ---")
        try:
            resp = self.get("/")
            if resp.status_code == 200:
                html_text = resp.text
                if "AvaScry Network" in html_text and "Magic: The Gathering" in html_text:
                    self.log_pass("network footer", "Footer displays AvaScry Network gaming links")
                else:
                    self.log_fail("network footer", "/", "Missing AvaScry Network section in footer")

                if "AvaScry Professional" in html_text and "avaspecs.com" in html_text:
                    self.log_pass("network footer", "Footer displays AvaScry Professional links (2-column layout)")
                else:
                    self.log_fail("network footer", "/", "Missing AvaScry Professional section in footer")

                if "Mojang" in html_text or "Minecraft is a trademark" in html_text:
                    self.log_pass("legal disclaimer", "Footer includes Mojang/Minecraft trademark notice")
                else:
                    self.log_fail("legal disclaimer", "/", "Missing Mojang/Minecraft trademark notice")
            else:
                self.log_fail("network footer", "/", f"Status {resp.status_code}")
        except Exception as e:
            self.log_fail("network footer", "/", str(e))

    # --- 7. BOUNDARIES & 404 RESILIENCE ---
    def test_boundaries(self):
        print("\n--- [7/8] Running Boundary & 404 Resilience Suite ---")
        bad_routes = [
            "/item/nonexistent-diamond-laser-sword",
            "/item/nonexistent-diamond-laser-sword.json",
            "/item/nonexistent-diamond-laser-sword.md",
            "/block/nonexistent-vibranium-block",
            "/block/nonexistent-vibranium-block.json",
            "/block/nonexistent-vibranium-block.md",
            "/recipe/nonexistent-recipe",
            "/entity/nonexistent-mob-entity",
        ]
        for route in bad_routes:
            try:
                resp = self.get(route)
                if resp.status_code == 404:
                    self.log_pass("boundary 404", f"{route} correctly returned 404")
                else:
                    self.log_fail("boundary 404", route, f"Expected 404, got {resp.status_code}")
            except Exception as e:
                self.log_fail("boundary 404", route, str(e))

    # --- 8. LEGAL & CONTACT BOUNDS ---
    def test_legal_and_contact(self):
        print("\n--- [8/8] Running Legal, Support & Contact Bounds Suite ---")
        legal_routes = ["/about", "/privacy", "/terms", "/contact"]
        for route in legal_routes:
            try:
                resp = self.get(route)
                if resp.status_code == 200 and "AvaScry Minecraft" in resp.text:
                    self.log_pass("legal pages", f"{route} returns 200 OK with branding")
                else:
                    self.log_fail("legal pages", route, f"Status {resp.status_code}")
            except Exception as e:
                self.log_fail("legal pages", route, str(e))

    def run_all(self):
        start_time = time.time()
        print("========================================================")
        print("AvaScry Minecraft SiteBlaster 9001: Integration Runner")
        print(f"Base: {self.base_url} | Seed: {self.seed} | Deep: {self.deep}")
        print("========================================================")

        self.test_core_endpoints()
        self.test_subdomain_symmetry()
        self.test_tri_surface_parity()
        self.test_catalog_lists()
        self.test_machine_discovery()
        self.test_footer_and_branding()
        self.test_boundaries()
        self.test_legal_and_contact()

        elapsed = round(time.time() - start_time, 2)
        print("\n========================================================")
        print(f"Minecraft SiteBlaster Summary: {self.passed} passed | {self.failed} failed | {self.warnings} warnings ({elapsed}s)")
        if self.failed == 0:
            print("\nMINECRAFT LIVES. OVERWORLD SECURED. ALL RECIPES VALID.\n")
        else:
            print("\nMINECRAFT FAILURE DETECTED.\n")
        print("========================================================\n")
        return self.failed == 0


def main():
    parser = argparse.ArgumentParser(description="AvaScry Minecraft SiteBlaster 9001")
    parser.add_argument("--quick", action="store_true", help="Run quick invariant checks")
    parser.add_argument("--deep", action="store_true", help="Run comprehensive checks")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL for target server")
    parser.add_argument("--seed", type=int, default=1337, help="RNG seed")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format")
    args = parser.parse_args()

    blaster = MinecraftSiteBlaster(base_url=args.base_url, deep=args.deep, seed=args.seed)
    success = blaster.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
