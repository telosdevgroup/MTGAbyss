#!/usr/bin/env python3
"""
necromunda_site_blaster.py — Necromunda SiteBlaster 9001: Real-entity integration & invariant tester.

Hardened non-destructive inspection runner for AvaScry Necromunda (Games Workshop / Warhammer 40,000 Underhive).
Exercises live/ASGI application routes, Mongo corpus data ('avascry_necromunda'), Markdown representations,
JSON APIs, Clan House Rosters, Weapon Trait interactions, Skill Disciplines, and machine discovery manifests.

Usage:
    python scripts/necromunda_site_blaster.py --quick
    python scripts/necromunda_site_blaster.py --deep
    python scripts/necromunda_site_blaster.py --quick --seed 42
    python scripts/necromunda_site_blaster.py --quick --base-url http://127.0.0.1:8004
"""

import sys
import os
import re
import html
import time
import random
import argparse
from typing import List, Dict, Any, Optional
from unittest.mock import patch, AsyncMock

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


class NecromundaSiteBlaster:
    USER_AGENT = "Ava9001/1.0 (Necromunda SiteBlaster 9001; AvaScry Necromunda; +https://necromunda.avascry.com)"

    def __init__(self, base_url: Optional[str] = None, deep: bool = False, seed: int = 1337):
        self.deep = deep
        self.seed = seed
        self.rng = random.Random(self.seed)
        self.base_url = (base_url or "https://necromunda.avascry.com").rstrip("/")
        self.user_agent = self.USER_AGENT

        default_headers = {
            "User-Agent": self.user_agent,
            "Host": "necromunda.avascry.com"
        }
        if base_url:
            self.client = httpx.Client(base_url=self.base_url, timeout=30.0, follow_redirects=False, headers=default_headers)
            self._is_testclient = False
        else:
            self.client = TestClient(app, base_url="https://necromunda.avascry.com", follow_redirects=False, headers=default_headers)
            self._is_testclient = True

        client = get_mongo_db().client
        self.db = client["avascry_necromunda"]
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
        req_headers = {"User-Agent": self.user_agent, "Host": "necromunda.avascry.com"}
        if headers:
            req_headers.update(headers)
        if not path.startswith("/"):
            path = "/" + path
        return self.client.get(path, headers=req_headers)

    def post(self, path: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        req_headers = {"User-Agent": self.user_agent, "Host": "necromunda.avascry.com"}
        if headers:
            req_headers.update(headers)
        if not path.startswith("/"):
            path = "/" + path
        return self.client.post(path, data=data, headers=req_headers)

    # =========================================================================
    # 1. CORE ROUTE SMOKE
    # =========================================================================
    def test_core_routes(self):
        print("\n--- [1/10] Running Core Route Smoke Suite ---")
        routes = [
            ("/", 200, "text/html"),
            ("/about", 200, "text/html"),
            ("/contact", 200, "text/html"),
            ("/privacy", 200, "text/html"),
            ("/terms", 200, "text/html"),
            ("/weapons", 200, "text/html"),
            ("/equipment", 200, "text/html"),
            ("/traits", 200, "text/html"),
            ("/houses", 200, "text/html"),
            ("/skills", 200, "text/html"),
            ("/llms.txt", 200, "text/plain"),
            ("/llms-full.txt", 200, "text/plain"),
            ("/sitemap.xml", 200, "application/xml"),
            ("/sitemap.html", 200, "text/html"),
            ("/sitemap.md", 200, "text/markdown"),
        ]

        for path, expected_status, expected_ct in routes:
            try:
                resp = self.get(path)
                if resp.status_code == expected_status:
                    if expected_ct and expected_ct not in resp.headers.get("content-type", ""):
                        self.log_warn("core route ct", path, f"Expected {expected_ct}, got {resp.headers.get('content-type')}")
                    else:
                        self.log_pass("core route smoke", f"{path} -> {resp.status_code}")
                else:
                    self.log_fail("core route smoke", path, f"Expected status {expected_status}, got {resp.status_code}")
            except Exception as e:
                self.log_fail("core route smoke", path, str(e))

    # =========================================================================
    # 2. UNDERHIVE ARMORY & WEAPON PROFILES
    # =========================================================================
    def test_weapons_suite(self):
        print("\n--- [2/10] Running Underhive Armory & Weapon Invariants ---")
        all_weapons = list(self.db.weapons.find({}, {"_id": 0}))
        if not all_weapons:
            self.log_fail("weapons corpus", "db.weapons", "No weapon records found in avascry_necromunda")
            return

        sample_size = len(all_weapons) if self.deep else min(10, len(all_weapons))
        sample = self.rng.sample(all_weapons, sample_size)
        self.log_pass("weapons sample", f"Sampling {len(sample)} of {len(all_weapons)} weapons (deep={self.deep})")

        for w in sample:
            slug = w.get("slug")
            name = w.get("name")
            if not slug or not name:
                self.log_fail("weapon record", f"Missing slug or name in record: {w}")
                continue

            # 1. HTML Profile
            html_path = f"/weapon/{slug}"
            try:
                r_html = self.get(html_path)
                if r_html.status_code == 200:
                    text = r_html.text
                    if name in text or html.escape(name) in text:
                        self.log_pass("weapon html", f"{html_path} contains '{name}'")
                    else:
                        self.log_fail("weapon html content", html_path, f"Name '{name}' missing from page")
                else:
                    self.log_fail("weapon html status", html_path, f"Status {r_html.status_code}")
            except Exception as e:
                self.log_fail("weapon html exception", html_path, str(e))

            # 2. Markdown Endpoint
            md_path = f"/weapon/{slug}.md"
            try:
                r_md = self.get(md_path)
                if r_md.status_code == 200:
                    text = r_md.text
                    if f"# {name}" in text and f'slug: "{slug}"' in text:
                        self.log_pass("weapon md", f"{md_path} valid frontmatter & header")
                    else:
                        self.log_fail("weapon md format", md_path, "Missing YAML slug or h1 name")
                else:
                    self.log_fail("weapon md status", md_path, f"Status {r_md.status_code}")
            except Exception as e:
                self.log_fail("weapon md exception", md_path, str(e))

            # 3. JSON Endpoint
            json_path = f"/weapon/{slug}.json"
            try:
                r_json = self.get(json_path)
                if r_json.status_code == 200:
                    data = r_json.json()
                    if data.get("slug") == slug and "cost_credits" in data:
                        self.log_pass("weapon json", f"{json_path} matched slug and cost_credits")
                    else:
                        self.log_fail("weapon json data", json_path, "Invalid JSON structure or missing fields")
                else:
                    self.log_fail("weapon json status", json_path, f"Status {r_json.status_code}")
            except Exception as e:
                self.log_fail("weapon json exception", json_path, str(e))

    # =========================================================================
    # 3. WEAPON TRAITS LEXICON INVARIANTS
    # =========================================================================
    def test_traits_suite(self):
        print("\n--- [3/10] Running Weapon Traits Lexicon Invariants ---")
        all_traits = list(self.db.traits.find({}, {"_id": 0}))
        if not all_traits:
            self.log_fail("traits corpus", "db.traits", "No trait records found")
            return

        sample_size = len(all_traits) if self.deep else min(10, len(all_traits))
        sample = self.rng.sample(all_traits, sample_size)
        self.log_pass("traits sample", f"Sampling {len(sample)} of {len(all_traits)} traits (deep={self.deep})")

        for t in sample:
            slug = t.get("slug")
            name = t.get("name")
            if not slug or not name:
                continue

            # Tri-surface verification
            r_html = self.get(f"/trait/{slug}")
            r_md = self.get(f"/trait/{slug}.md")
            r_json = self.get(f"/trait/{slug}.json")

            if r_html.status_code == 200 and r_md.status_code == 200 and r_json.status_code == 200:
                data = r_json.json()
                raw_html = html.unescape(r_html.text)
                has_html_name = (name in raw_html or html.escape(name) in r_html.text)
                has_md_header = (f"# Weapon Trait: {name}" in r_md.text or f"# {name}" in r_md.text)
                has_json_slug = (data.get("slug") == slug)
                if has_html_name and has_md_header and has_json_slug:
                    self.log_pass("trait tri-surface", f"Trait '{slug}' HTML/MD/JSON consistent")
                else:
                    self.log_fail("trait content", slug, f"Content mismatch across tri-surface (html={has_html_name}, md={has_md_header}, json={has_json_slug})")
            else:
                self.log_fail("trait status", slug, f"HTML:{r_html.status_code} MD:{r_md.status_code} JSON:{r_json.status_code}")

    # =========================================================================
    # 4. CLAN HOUSES OF HIVE PRIMUS
    # =========================================================================
    def test_houses_suite(self):
        print("\n--- [4/10] Running Clan Houses & Rosters Invariants ---")
        all_houses = list(self.db.houses.find({}, {"_id": 0}))
        if not all_houses:
            self.log_fail("houses corpus", "db.houses", "No clan house records found")
            return

        self.log_pass("houses corpus", f"Evaluating all {len(all_houses)} Clan Houses")
        for h in all_houses:
            slug = h.get("slug")
            name = h.get("name")
            if not slug or not name:
                continue

            r_html = self.get(f"/house/{slug}")
            r_md = self.get(f"/house/{slug}.md")
            r_json = self.get(f"/house/{slug}.json")

            if r_html.status_code == 200 and r_md.status_code == 200 and r_json.status_code == 200:
                data = r_json.json()
                has_roster = bool(data.get("roster"))
                has_skills = bool(data.get("primary_skills"))
                if has_roster and has_skills and name in r_html.text:
                    self.log_pass("house invariants", f"House '{name}' ({len(data.get('roster', []))} fighters, {len(data.get('primary_skills', []))} skill disciplines)")
                else:
                    self.log_fail("house data check", slug, "Missing roster or primary skills")
            else:
                self.log_fail("house status", slug, f"Statuses -> HTML:{r_html.status_code} MD:{r_md.status_code} JSON:{r_json.status_code}")

    # =========================================================================
    # 5. SKILL DISCIPLINES INVARIANTS
    # =========================================================================
    def test_skills_suite(self):
        print("\n--- [5/10] Running Skill Disciplines & Trees Invariants ---")
        all_skills = list(self.db.skills.find({}, {"_id": 0}))
        if not all_skills:
            self.log_fail("skills corpus", "db.skills", "No skill records found")
            return

        sample_size = len(all_skills) if self.deep else min(10, len(all_skills))
        sample = self.rng.sample(all_skills, sample_size)
        self.log_pass("skills sample", f"Sampling {len(sample)} of {len(all_skills)} skills (deep={self.deep})")

        for s in sample:
            slug = s.get("slug")
            name = s.get("name")
            tree = s.get("tree")
            if not slug or not name:
                continue

            r_html = self.get(f"/skill/{slug}")
            r_md = self.get(f"/skill/{slug}.md")
            r_json = self.get(f"/skill/{slug}.json")

            if r_html.status_code == 200 and r_md.status_code == 200 and r_json.status_code == 200:
                data = r_json.json()
                if data.get("tree") == tree and name in r_html.text and f"# Skill: {name}" in r_md.text:
                    self.log_pass("skill tri-surface", f"Skill '{name}' [{tree}] consistent across endpoints")
                else:
                    self.log_fail("skill content check", slug, "Tree badge or title mismatch")
            else:
                self.log_fail("skill status", slug, f"HTML:{r_html.status_code} MD:{r_md.status_code} JSON:{r_json.status_code}")

    # =========================================================================
    # 5B. TRADING POST & EQUIPMENT PROFILES
    # =========================================================================
    def test_equipment_suite(self):
        print("\n--- [5B/10] Running Trading Post & Equipment Invariants ---")
        all_equip = list(self.db.equipment.find({}, {"_id": 0}))
        if not all_equip:
            self.log_fail("equipment corpus", "db.equipment", "No equipment records found in avascry_necromunda")
            return

        sample_size = len(all_equip) if self.deep else min(15, len(all_equip))
        sample = self.rng.sample(all_equip, sample_size)
        self.log_pass("equipment sample", f"Sampling {len(sample)} of {len(all_equip)} equipment items (deep={self.deep})")

        for eq in sample:
            slug = eq.get("slug")
            name = eq.get("name")
            category = eq.get("category")
            if not slug or not name:
                continue

            # 1. HTML Detail
            html_path = f"/equipment/{slug}"
            try:
                r_html = self.get(html_path)
                if r_html.status_code == 200:
                    raw_html = html.unescape(r_html.text)
                    if (name in raw_html or html.escape(name) in r_html.text) and (category in raw_html if category else True):
                        self.log_pass("equipment html", f"{html_path} matched name and category")
                    else:
                        self.log_fail("equipment html content", html_path, "Item name or category missing from HTML body")
                else:
                    self.log_fail("equipment html status", html_path, f"Status {r_html.status_code}")
            except Exception as e:
                self.log_fail("equipment html exception", html_path, str(e))

            # 2. Markdown Endpoint
            md_path = f"/equipment/{slug}.md"
            try:
                r_md = self.get(md_path)
                if r_md.status_code == 200:
                    if f'slug: "{slug}"' in r_md.text and f"# Equipment: {name}" in r_md.text:
                        self.log_pass("equipment md", f"{md_path} valid frontmatter & header")
                    else:
                        self.log_fail("equipment md format", md_path, "Missing YAML slug or h1 header")
                else:
                    self.log_fail("equipment md status", md_path, f"Status {r_md.status_code}")
            except Exception as e:
                self.log_fail("equipment md exception", md_path, str(e))

            # 3. JSON Endpoint
            json_path = f"/equipment/{slug}.json"
            try:
                r_json = self.get(json_path)
                if r_json.status_code == 200:
                    data = r_json.json()
                    if data.get("slug") == slug and "cost_credits" in data:
                        self.log_pass("equipment json", f"{json_path} matched slug and cost_credits")
                    else:
                        self.log_fail("equipment json data", json_path, "Invalid JSON structure or missing fields")
                else:
                    self.log_fail("equipment json status", json_path, f"Status {r_json.status_code}")
            except Exception as e:
                self.log_fail("equipment json exception", json_path, str(e))

    # =========================================================================
    # 6. CONTACT WEBHOOK & HONEYPOT SUITE
    # =========================================================================
    def test_contact_suite(self):
        print("\n--- [6/10] Running Contact Webhook & Anti-Spam Suite ---")
        # 1. GET page
        r_get = self.get("/contact")
        if r_get.status_code == 200 and "Contact Us" in r_get.text and 'id="website_url"' in r_get.text:
            self.log_pass("contact get", "/contact rendered human-friendly form and honeypot field")
        else:
            self.log_fail("contact get", "/contact", f"Status {r_get.status_code} or form elements missing")

        # 2. Mocked successful POST dispatch
        with patch('mtgabyss.routers.auth_router.send_discord_notification', new_callable=AsyncMock) as mock_notify:
            r_post = self.post("/contact", data={
                "name": "Commander SiteBlaster",
                "contact": "blaster9001@underhive.net",
                "message": "Automated invariant check from Necromunda SiteBlaster 9001"
            })
            if r_post.status_code == 200 and "Message Sent!" in r_post.text:
                if mock_notify.called and mock_notify.call_args.kwargs['fields'][1]['value'] == "Commander SiteBlaster":
                    self.log_pass("contact dispatch", "Live webhook dispatch intercepted and payload validated")
                else:
                    self.log_fail("contact dispatch", "/contact", "send_discord_notification not called with expected payload")
            else:
                self.log_fail("contact post status", "/contact", f"Status {r_post.status_code}")

        # 3. Honeypot anti-spam absorption
        r_honey = self.post("/contact", data={
            "website_url": "http://scam-link.net",
            "name": "Spambot",
            "contact": "bot@spammer.org",
            "message": "Spam payload"
        })
        if r_honey.status_code == 200 and "Message Sent!" in r_honey.text:
            self.log_pass("contact honeypot", "Bot submission with honeypot filled absorbed silently")
        else:
            self.log_fail("contact honeypot", "/contact", f"Status {r_honey.status_code}")

        # 4. Required fields validation failure
        r_empty = self.post("/contact", data={"name": "", "contact": "", "message": ""})
        if r_empty.status_code == 200 and ("Please provide your contact info and a message" in r_empty.text or "Please fill out all required fields" in r_empty.text):
            self.log_pass("contact validation", "Empty submission blocked with user alert")
        else:
            self.log_fail("contact validation", "/contact", "Empty submission was not properly rejected")

    # =========================================================================
    # 7. SEARCH & CATEGORY UI INVARIANTS
    # =========================================================================
    def test_search_and_filters_suite(self):
        print("\n--- [7/10] Running Search & Category UI Invariants ---")
        pages = [
            ("/weapons", "weaponFilterInput", "categoryPillRow", "weapon-card"),
            ("/equipment", "equipmentFilterInput", "equipmentCatPillRow", "equipment-card"),
            ("/traits", "traitFilterInput", "traitCategoryPillRow", "trait-card"),
            ("/houses", "houseFilterInput", None, "house-card"),
            ("/skills", "skillFilterInput", "skillTreePillRow", "skill-card"),
        ]

        for path, input_id, pill_id, card_cls in pages:
            r = self.get(path)
            if r.status_code == 200:
                has_input = f'id="{input_id}"' in r.text
                has_card = card_cls in r.text
                has_pills = (f'id="{pill_id}"' in r.text) if pill_id else True

                if has_input and has_card and has_pills:
                    self.log_pass("search ui elements", f"{path} has input #{input_id}, cards .{card_cls}, and pills: {bool(pill_id)}")
                else:
                    self.log_fail("search ui missing", path, f"input={has_input}, cards={has_card}, pills={has_pills}")
            else:
                self.log_fail("search page status", path, f"Status {r.status_code}")

    # =========================================================================
    # 8. LLMS & DISCOVERY MANIFESTS
    # =========================================================================
    def test_discovery_manifests(self):
        print("\n--- [8/10] Running LLMs & Discovery Manifests Suite ---")
        # 1. llms.txt
        r_llms = self.get("/llms.txt")
        if r_llms.status_code == 200 and "# AvaScry Necromunda" in r_llms.text and "/weapons" in r_llms.text:
            self.log_pass("llms.txt", "Valid index with primary section links")
        else:
            self.log_fail("llms.txt check", "/llms.txt", "Invalid format or missing sections")

        # 2. llms-full.txt
        r_full = self.get("/llms-full.txt")
        if r_full.status_code == 200 and "ARMORY WEAPONS" in r_full.text and "Heavy Bolter" in r_full.text:
            self.log_pass("llms-full.txt", f"Comprehensive corpus manifest ({len(r_full.text)} chars)")
        else:
            self.log_fail("llms-full.txt check", "/llms-full.txt", "Manifest missing armory profiles")

        # 3. sitemap.xml
        r_xml = self.get("/sitemap.xml")
        if r_xml.status_code == 200 and "<urlset" in r_xml.text and "</urlset>" in r_xml.text:
            self.log_pass("sitemap.xml", f"Valid XML urlset ({r_xml.text.count('<loc>')} URLs)")
        else:
            self.log_fail("sitemap.xml check", "/sitemap.xml", "Malformed sitemap XML")

        # 4. sitemap.html & sitemap.md
        r_s_html = self.get("/sitemap.html")
        r_s_md = self.get("/sitemap.md")
        if r_s_html.status_code == 200 and r_s_md.status_code == 200:
            self.log_pass("sitemap formats", "sitemap.html and sitemap.md 200 OK")
        else:
            self.log_fail("sitemap formats", "sitemap", f"HTML:{r_s_html.status_code} MD:{r_s_md.status_code}")

    # =========================================================================
    # 9. BOUNDARY & 404 RESILIENCE
    # =========================================================================
    def test_boundary_and_404(self):
        print("\n--- [9/10] Running Boundary & 404 Resilience Suite ---")
        bad_endpoints = [
            ("/weapon/nonexistent-plasma-cannon", 404),
            ("/weapon/nonexistent-plasma-cannon.json", 404),
            ("/weapon/nonexistent-plasma-cannon.md", 404),
            ("/equipment/nonexistent-stimm-slug-dispenser", 404),
            ("/equipment/nonexistent-stimm-slug-dispenser.json", 404),
            ("/equipment/nonexistent-stimm-slug-dispenser.md", 404),
            ("/trait/nonexistent-rule-trait", 404),
            ("/trait/nonexistent-rule-trait.json", 404),
            ("/house/nonexistent-clan-house", 404),
            ("/house/nonexistent-clan-house.json", 404),
            ("/skill/nonexistent-skill-power", 404),
            ("/skill/nonexistent-skill-power.json", 404),
        ]

        for path, expected_status in bad_endpoints:
            try:
                resp = self.get(path)
                if resp.status_code == expected_status:
                    self.log_pass("404 boundary", f"{path} -> {resp.status_code}")
                else:
                    self.log_fail("404 boundary", path, f"Expected {expected_status}, got {resp.status_code}")
            except Exception as e:
                self.log_fail("404 boundary exception", path, str(e))

    # =========================================================================
    # 10. SUBDOMAIN & ROUTING SYMMETRY
    # =========================================================================
    def test_subdomain_routing_symmetry(self):
        print("\n--- [10/10] Running Subdomain Routing Symmetry Suite ---")
        # Subdomain host routing vs prefix routing
        test_paths = ["/", "/weapons", "/equipment", "/traits", "/houses", "/skills", "/about", "/privacy", "/terms", "/contact"]

        for p in test_paths:
            # 1. As host 'necromunda.avascry.com' at path 'p'
            r_sub = self.get(p, headers={"Host": "necromunda.avascry.com"})
            # 2. As fallback prefix on default host
            r_pfx = self.get(f"/necromunda{p}" if p != "/" else "/necromunda", headers={"Host": "avascry.com"})

            if r_sub.status_code == 200 and r_pfx.status_code == 200:
                self.log_pass("routing symmetry", f"Path '{p}' identical 200 OK on subdomain & /necromunda prefix")
            else:
                self.log_fail("routing symmetry", p, f"Subdomain={r_sub.status_code}, Prefix={r_pfx.status_code}")

    # =========================================================================
    # 11. COMBAT BALLISTICS & AMMO RELIABILITY INVARIANTS
    # =========================================================================
    def test_combat_ballistics_suite(self):
        print("\n--- [11/13] Running Combat Ballistics & Ammo Invariants ---")
        all_weapons = list(self.db.weapons.find({}, {"_id": 0}))
        if not all_weapons:
            self.log_fail("ballistics corpus", "db.weapons", "No weapon records found")
            return

        sample_size = len(all_weapons) if self.deep else min(15, len(all_weapons))
        sample = self.rng.sample(all_weapons, sample_size)
        self.log_pass("ballistics sample", f"Evaluating ballistics for {len(sample)} weapons (deep={self.deep})")

        ammo_pattern = re.compile(r"^([2-6]\+|\-|D6)$")
        for w in sample:
            name = w.get("name", "Unknown")
            slug = w.get("slug", "")
            cost = w.get("cost_credits")
            damage = w.get("damage")
            ap = w.get("armor_piercing")
            ammo = str(w.get("ammo", "")).strip()

            # Cost invariant
            if isinstance(cost, (int, float)) and cost >= 0:
                pass
            else:
                self.log_fail("weapon cost", slug, f"Invalid credit cost: {cost}")

            # Damage invariant (Necromunda weapons deal >= 1 damage unless Web/Entangle chemical weapons which deal 0 direct damage)
            traits = [t.lower() for t in w.get("traits", [])]
            is_web_or_entangle = any("web" in t or "entangle" in t for t in traits)
            if damage is None or (isinstance(damage, (int, float)) and damage < 0) or (isinstance(damage, (int, float)) and damage == 0 and not is_web_or_entangle):
                self.log_fail("weapon damage", slug, f"Damage must be >= 1 (or 0 for Web/Entangle): {damage}")


            # Armor piercing invariant (AP in Necromunda is 0 or negative integer, e.g. -1, -2, -3)
            if ap is not None and isinstance(ap, (int, float)) and ap > 0:
                self.log_warn("weapon ap", slug, f"AP is positive (+{ap}); typically 0 or negative in Necromunda")

            # Ammo check reliability invariant
            if ammo and (ammo_pattern.match(ammo) or ammo in ["-", "2+", "3+", "4+", "5+", "6+"]):
                pass
            else:
                self.log_warn("weapon ammo", slug, f"Non-standard ammo check notation: '{ammo}'")

        self.log_pass("ballistics invariants", f"Verified profile invariants across {len(sample)} weapons")

    # =========================================================================
    # 12. GANG ROSTER & FIGHTER CLASS INVARIANTS
    # =========================================================================
    def test_gang_roster_loadouts_suite(self):
        print("\n--- [12/13] Running Gang Roster & Fighter Class Invariants ---")
        all_houses = list(self.db.houses.find({}, {"_id": 0}))
        if not all_houses:
            self.log_fail("houses roster corpus", "db.houses", "No clan houses found")
            return

        fighter_roles_seen = set()
        total_fighters_checked = 0

        for h in all_houses:
            house_name = h.get("name", "Unknown House")
            roster = h.get("roster", [])
            if not roster:
                self.log_fail("house roster", house_name, "House has an empty fighter roster")
                continue

            for f in roster:
                total_fighters_checked += 1
                role = f.get("role", "")
                title = f.get("title", "")
                cost = f.get("cost_credits")
                fighter_roles_seen.add(role)

                # Fighter cost bound
                if not isinstance(cost, (int, float)) or cost <= 0:
                    self.log_fail("fighter cost", f"{house_name} -> {title}", f"Invalid fighter cost: {cost}")

                # Characteristics bound
                t = f.get("t")
                w = f.get("w")
                if isinstance(t, int) and (t < 1 or t > 10):
                    self.log_fail("fighter toughness", f"{house_name} -> {title}", f"Toughness out of bounds: {t}")
                if isinstance(w, int) and (w < 1 or w > 10):
                    self.log_fail("fighter wounds", f"{house_name} -> {title}", f"Wounds out of bounds: {w}")

        self.log_pass("roster loadout", f"Validated {total_fighters_checked} fighters across {len(all_houses)} Houses (Roles: {', '.join(sorted(fighter_roles_seen))})")

    # =========================================================================
    # 13. STANDARDIZED CONTACT 500-CHAR & HONEYPOT INVARIANTS
    # =========================================================================
    def test_contact_payload_limits_suite(self):
        print("\n--- [13/13] Running Contact 500-Char & Payload Limits Suite ---")
        # 1. Check frontend counter and maxlength
        r_get = self.get("/contact")
        if r_get.status_code == 200:
            if 'maxlength="500"' in r_get.text and 'id="char-counter"' in r_get.text:
                self.log_pass("contact bounds ui", "HTML includes maxlength='500' and #char-counter element")
            else:
                self.log_fail("contact bounds ui", "/contact", "Missing maxlength='500' or #char-counter")
        else:
            self.log_fail("contact bounds ui", "/contact", f"Status {r_get.status_code}")

        # 2. Over-length payload dispatch test (must be clipped to 500 characters by backend)
        oversized_message = "Necromunda tactical underhive transmission " + ("X" * 600)
        with patch('mtgabyss.routers.auth_router.send_discord_notification', new_callable=AsyncMock) as mock_notify:
            r_post = self.post("/contact", data={
                "name": "Underhive Arbitrator",
                "contact": "arbitrator@precinct.org",
                "message": oversized_message
            })
            if r_post.status_code == 200 and "Message Sent!" in r_post.text:
                if mock_notify.called:
                    dispatched_msg = mock_notify.call_args.kwargs['fields'][-1]['value']
                    if len(dispatched_msg) <= 500:
                        self.log_pass("contact payload limit", f"Oversized message (643 chars) clipped to {len(dispatched_msg)} chars in Discord webhook")
                    else:
                        self.log_fail("contact payload limit", "/contact", f"Payload exceeded 500 chars: {len(dispatched_msg)}")
                else:
                    self.log_fail("contact payload limit", "/contact", "Webhook notification not dispatched")
            else:
                self.log_fail("contact payload limit", "/contact", f"Status {r_post.status_code} or missing confirmation")

    # =========================================================================
    # MAIN RUNNER
    # =========================================================================
    def run_all(self) -> int:
        self.start_time = time.time()
        print("========================================================")
        print("  AVA9001 // NECROMUNDA SITEBLASTER 9001  ")
        print(f"  Target: {self.base_url} (Mode: {'Deep' if self.deep else 'Quick'}, Seed: {self.seed})")
        print("========================================================")

        self.test_core_routes()
        self.test_weapons_suite()
        self.test_traits_suite()
        self.test_houses_suite()
        self.test_skills_suite()
        self.test_equipment_suite()
        self.test_contact_suite()
        self.test_search_and_filters_suite()
        self.test_discovery_manifests()
        self.test_boundary_and_404()
        self.test_subdomain_routing_symmetry()
        self.test_combat_ballistics_suite()
        self.test_gang_roster_loadouts_suite()
        self.test_contact_payload_limits_suite()

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
        print(f"Necromunda SiteBlaster Summary: {self.passed} passed | {self.failed} failed | {self.warnings} warnings ({elapsed:.2f}s)")
        if self.failed == 0:
            print("\033[92m\nNECROMUNDA LIVES. UNDERHIVE SECURED. GANGS STANDING.\033[0m\n")
        else:
            print(f"\033[91m\nNECROMUNDA NEEDS ATTENTION ({self.failed} failures).\033[0m\n")
        print("========================================================\n")

        return 1 if self.failed > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="Necromunda SiteBlaster 9001 — Invariant & Route Tester")
    parser.add_argument("--deep", action="store_true", help="Run comprehensive deep suite across all corpus entities")
    parser.add_argument("--quick", action="store_true", help="Run fast quick suite with targeted sample sizes (default)")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic random seed (default: 1337)")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL of live server (e.g. http://127.0.0.1:8004). Defaults to in-process ASGI.")
    args = parser.parse_args()

    is_deep = bool(args.deep)
    blaster = NecromundaSiteBlaster(base_url=args.base_url, deep=is_deep, seed=args.seed)
    exit_code = blaster.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
