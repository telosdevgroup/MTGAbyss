#!/usr/bin/env python3
"""
swu_site_blaster.py — Star Wars: Unlimited SiteBlaster 9001: Real-entity integration & invariant tester.

Hardened non-destructive inspection runner for AvaScry Star Wars: Unlimited (Fantasy Flight Games / Lucasfilm).
Exercises live/ASGI application routes, Mongo corpus data ('avascry_swu'), Markdown representations,
JSON APIs, XML formats, Comprehensive Rules citations, Keywords, Clarifications, and machine discovery manifests.

Usage:
    python scripts/swu_site_blaster.py --quick
    python scripts/swu_site_blaster.py --deep
    python scripts/swu_site_blaster.py --quick --seed 42
    python scripts/swu_site_blaster.py --quick --base-url http://127.0.0.1:8004
"""

import sys
import os
import re
import json
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


class SWUSiteBlaster:
    USER_AGENT = "Ava9001/1.0 (SWU SiteBlaster 9001; AvaScry Star Wars Unlimited; +https://swu.avascry.com)"

    def __init__(self, base_url: Optional[str] = None, deep: bool = False, seed: int = 1337):
        self.deep = deep
        self.seed = seed
        self.rng = random.Random(self.seed)
        self.base_url = (base_url or "https://swu.avascry.com").rstrip("/")
        self.user_agent = self.USER_AGENT

        default_headers = {
            "User-Agent": self.user_agent,
            "Host": "swu.avascry.com"
        }
        if base_url:
            self.client = httpx.Client(base_url=self.base_url, timeout=30.0, follow_redirects=False, headers=default_headers)
            self._is_testclient = False
        else:
            self.client = TestClient(app, base_url="https://swu.avascry.com", follow_redirects=False, headers=default_headers)
            self._is_testclient = True

        client = get_mongo_db().client
        self.db = client["avascry_swu"]
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
        req_headers = {"User-Agent": self.user_agent, "Host": "swu.avascry.com"}
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
            ("/privacy", 200, "text/html"),
            ("/terms", 200, "text/html"),
            ("/contact", 200, "text/html"),
            ("/random", 307, None),
            ("/random.json", 200, "application/json"),
            ("/random.md", 307, None),
            ("/rules", 200, "text/html"),
            ("/rules.md", 200, "text/markdown"),
            ("/rules.json", 200, "application/json"),
            ("/rulings", 200, "text/html"),
            ("/errata", 200, "text/html"),
            ("/keywords", 200, "text/html"),
            ("/traits", 200, "text/html"),
            ("/.well-known/ai-content", 200, "text/plain"),
            ("/sitemap.xml", 200, "application/xml"),
            ("/llms.txt", 200, "text/plain"),
            ("/llms-full.txt", 200, "text/plain"),
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
                        if target and "/card/" in target:
                            rand_resp = self.get(target)
                            if rand_resp.status_code == 200:
                                self.log_pass("random redirect target", f"/random -> {target} -> 200 OK")
                            else:
                                self.log_fail("random redirect target", f"/random -> {target}", f"Status {rand_resp.status_code}")
                        else:
                            self.log_fail("random redirect target", "/random", f"Invalid target: {target}")

                    # Verify redirect target for /random.md
                    if path == "/random.md":
                        target_md = resp.headers.get("location")
                        if target_md and target_md.endswith(".md"):
                            self.log_pass("random.md redirect", f"/random.md -> {target_md}")
                        else:
                            self.log_fail("random.md redirect", "/random.md", f"Invalid target: {target_md}")
                else:
                    self.log_fail("core route smoke", path, f"Expected status {expected_status}, got {resp.status_code}")
            except Exception as e:
                self.log_fail("core route smoke", path, str(e))

    # =========================================================================
    # 2. REAL ENTITY CARDS (QUAD-SURFACE: HTML, MARKDOWN, JSON, XML)
    # =========================================================================
    def test_entity_cards(self):
        print("\n--- [2/10] Running Real Entity Quad-Surface Suite (HTML, MD, JSON, XML) ---")
        sample_size = 30 if self.deep else 10
        cards = list(self.db.cards.find({}, {"_id": 0, "name": 1, "title": 1, "slug": 1, "type": 1, "aspects": 1, "rarity": 1}))

        if not cards:
            self.log_fail("entity card sample", "Mongo collection 'cards'", "No cards found in avascry_swu.cards")
            return

        sampled_cards = []
        sampled_slugs = set()

        # Guarantee diversity across card types (Leader, Base, Unit, Event, Upgrade)
        key_types = ["Leader", "Base", "Unit", "Event", "Upgrade"]
        for kt in key_types:
            matching = [c for c in cards if c.get("type", "").lower() == kt.lower() and c.get("slug") not in sampled_slugs]
            if matching:
                chosen = self.rng.choice(matching)
                sampled_cards.append(chosen)
                sampled_slugs.add(chosen.get("slug"))

        # Guarantee diversity across aspects (Vigilance, Command, Aggression, Cunning, Villainy, Heroism)
        key_aspects = ["Vigilance", "Command", "Aggression", "Cunning", "Villainy", "Heroism"]
        for ka in key_aspects:
            matching = [c for c in cards if ka in c.get("aspects", []) and c.get("slug") not in sampled_slugs]
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
            name = card.get("name") or card.get("title") or slug

            # 1. HTML Representation & SEO Alternates
            try:
                resp_html = self.get(f"/card/{slug}")
                if resp_html.status_code == 200:
                    text = resp_html.text
                    text_norm = text.lower().replace("&#39;", "'").replace("&#x27;", "'").replace("&apos;", "'").replace("&quot;", '"')
                    name_clean = name.replace('"', '').replace('“', '').replace('”', '').replace("'", "").replace("’", "").lower()
                    name_found = (
                        name.lower() in text_norm or 
                        html.unescape(name.lower()) in text_norm or
                        name_clean in text_norm.replace("'", "").replace("’", "") or
                        (name_clean.split() and name_clean.split()[0] in text_norm.replace("'", "").replace("’", ""))
                    )
                    if name_found:
                        self.log_pass("card HTML", f"{name} (/card/{slug})")
                    else:
                        self.log_warn("card HTML", f"{name} (/card/{slug})", "Card name missing from rendered HTML")

                    # Check rel="alternate" tags and Link headers
                    has_md_link = f"{slug}.md" in text
                    has_json_link = f"{slug}.json" in text
                    has_xml_link = f"{slug}.xml" in text
                    if has_md_link and has_json_link and has_xml_link:
                        self.log_pass("card HTML alternates", f"{slug} has MD/JSON/XML alternate link tags")
                    else:
                        self.log_warn("card HTML alternates", f"{slug}", "Missing alternate link tags in HTML head")

                    # Check Cache-Control header
                    cc = resp_html.headers.get("cache-control", "")
                    if "max-age=3600" in cc:
                        self.log_pass("card HTML cache", f"{slug} Cache-Control verified")
                    else:
                        self.log_warn("card HTML cache", f"/card/{slug}", f"Unexpected Cache-Control: {cc}")

                    # Check Schema.org @graph structured data
                    ld_match = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', text, re.DOTALL)
                    if ld_match:
                        try:
                            ld_json = json.loads(ld_match.group(1))
                            graph = ld_json.get("@graph", [])
                            types = {item.get("@type") for item in graph if isinstance(item, dict)}
                            if {"WebPage", "BreadcrumbList", "Thing"}.issubset(types):
                                self.log_pass("card Schema.org graph", f"{slug} valid @graph (types: {', '.join(sorted(types))})")
                            else:
                                self.log_warn("card Schema.org graph", f"{slug}", f"Missing standard types in @graph: {types}")
                        except Exception as e:
                            self.log_fail("card Schema.org graph", f"/card/{slug}", f"Failed to parse JSON-LD: {e}")
                    else:
                        self.log_warn("card Schema.org graph", f"/card/{slug}", "No application/ld+json script tag found")
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
                    if "max-age=3600" in resp_md.headers.get("cache-control", ""):
                        self.log_pass("card Markdown cache", f"{slug}.md Cache-Control verified")
                else:
                    self.log_fail("card Markdown", f"/card/{slug}.md", f"Status {resp_md.status_code}")
            except Exception as e:
                self.log_fail("card Markdown", f"/card/{slug}.md", str(e))

            # 3. JSON Representation & REST Symmetry
            try:
                resp_json = self.get(f"/card/{slug}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    c_slug = data.get("slug")
                    if c_slug == slug:
                        self.log_pass("card JSON REST", f"{name} (/card/{slug}.json)")
                    else:
                        self.log_fail("card JSON REST", f"/card/{slug}.json", "REST symmetry mismatch with Mongo entity",
                                      {"expected_slug": slug, "json_slug": c_slug})

                    if "max-age=3600" in resp_json.headers.get("cache-control", ""):
                        self.log_pass("card JSON cache", f"{slug}.json Cache-Control verified")

                    # Mechanics & Invariant validation
                    card_type = data.get("type") or ""
                    if card_type.lower() == "leader":
                        if data.get("local_image_back") or data.get("epic_action") or data.get("unit_power") is not None:
                            self.log_pass("leader mechanics", f"{name} leader unit/back face attributes validated")
                        else:
                            self.log_warn("leader mechanics", f"{name}", "Leader missing deploy or unit face attributes")
                    elif card_type.lower() == "unit":
                        arenas = data.get("arenas") or []
                        if isinstance(arenas, list) and any(a in ["Ground", "Space"] for a in arenas):
                            self.log_pass("unit arena", f"{name} ({', '.join(arenas)} Arena)")
                        elif data.get("arena") in ["Ground", "Space"]:
                            self.log_pass("unit arena", f"{name} ({data.get('arena')} Arena)")
                        else:
                            self.log_warn("unit arena", f"{name}", f"Unexpected arenas value: {arenas}")
                else:
                    self.log_fail("card JSON REST", f"/card/{slug}.json", f"Status {resp_json.status_code}")
            except Exception as e:
                self.log_fail("card JSON REST", f"/card/{slug}.json", str(e))

            # 4. XML Representation
            try:
                resp_xml = self.get(f"/card/{slug}.xml")
                if resp_xml.status_code == 200:
                    if "<card>" in resp_xml.text and f"<slug>{slug}</slug>" in resp_xml.text:
                        self.log_pass("card XML format", f"{name} (/card/{slug}.xml)")
                    else:
                        self.log_fail("card XML format", f"/card/{slug}.xml", "Missing root <card> or <slug>")
                else:
                    self.log_fail("card XML format", f"/card/{slug}.xml", f"Status {resp_xml.status_code}")
            except Exception as e:
                self.log_fail("card XML format", f"/card/{slug}.xml", str(e))

    # =========================================================================
    # 2b. NEURAL EMBEDDINGS & SIMILARITY GRAPH
    # =========================================================================
    def test_similarity_graph(self):
        print("\n--- [2b/10] Running Neural Embeddings & Similarity Graph Suite ---")
        docs = list(self.db.similar_cards.find({}, {"_id": 0, "slug": 1, "title": 1, "similar": 1}).limit(50))
        if not docs:
            self.log_fail("similarity suite", "Mongo similar_cards", "No records found in avascry_swu.similar_cards")
            return

        sample_cards = self.rng.sample(docs, min(8, len(docs)))
        for item in sample_cards:
            slug = item.get("slug")
            name = item.get("title")

            # 1. HTML Similarity Page
            try:
                resp_html = self.get(f"/similar/{slug}")
                if resp_html.status_code == 200:
                    text = resp_html.text
                    if "Similar to" in text or name in text:
                        self.log_pass("similar HTML", f"{name} (/similar/{slug})")
                    else:
                        self.log_fail("similar HTML", f"/similar/{slug}", "HTML missing card title or header")

                    # Check Schema.org CollectionPage and ItemList
                    if "CollectionPage" in text and "ItemList" in text:
                        self.log_pass("similar Schema.org", f"{slug} Schema.org ItemList validated")
                    else:
                        self.log_warn("similar Schema.org", f"/similar/{slug}", "Missing CollectionPage or ItemList structured data")

                    if f"/similar/{slug}.md" in text and f"/similar/{slug}.json" in text:
                        self.log_pass("similar alternates", f"{slug} alternate links present in HTML")
                    else:
                        self.log_warn("similar alternates", f"/similar/{slug}", "Missing alternate links for MD/JSON")
                else:
                    self.log_fail("similar HTML", f"/similar/{slug}", f"Status {resp_html.status_code}")
            except Exception as e:
                self.log_fail("similar HTML", f"/similar/{slug}", str(e))

            # 2. Markdown Similarity Endpoint
            try:
                resp_md = self.get(f"/similar/{slug}.md")
                if resp_md.status_code == 200:
                    if "# Mechanically Similar Cards to" in resp_md.text and "Top Similar Cards" in resp_md.text:
                        self.log_pass("similar Markdown", f"{name} (/similar/{slug}.md)")
                    else:
                        self.log_fail("similar Markdown", f"/similar/{slug}.md", "Missing expected markdown headers")
                    if "max-age=3600" in resp_md.headers.get("cache-control", ""):
                        self.log_pass("similar Markdown cache", f"{slug}.md Cache-Control verified")
                else:
                    self.log_fail("similar Markdown", f"/similar/{slug}.md", f"Status {resp_md.status_code}")
            except Exception as e:
                self.log_fail("similar Markdown", f"/similar/{slug}.md", str(e))

            # 3. JSON Similarity API Endpoint
            try:
                resp_json = self.get(f"/similar/{slug}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    if data.get("model") == "qwen3-embedding:8b" and data.get("dimension") == 4096:
                        self.log_pass("similar JSON model", f"{slug}.json (4096-dim qwen3-embedding:8b)")
                    else:
                        self.log_fail("similar JSON model", f"/similar/{slug}.json", f"Unexpected model metadata: {data.get('model')}")

                    similar_list = data.get("similar", [])
                    if len(similar_list) > 0 and "score" in similar_list[0]:
                        self.log_pass("similar JSON list", f"{name} returned {len(similar_list)} ranked similar cards (top score: {similar_list[0]['score']})")
                    else:
                        self.log_fail("similar JSON list", f"/similar/{slug}.json", "Empty or invalid similar cards array")
                else:
                    self.log_fail("similar JSON API", f"/similar/{slug}.json", f"Status {resp_json.status_code}")
            except Exception as e:
                self.log_fail("similar JSON API", f"/similar/{slug}.json", str(e))

            # 4. Raw Neural Vector Endpoint (/vector/{slug}.json)
            try:
                resp_vec = self.get(f"/vector/{slug}.json")
                if resp_vec.status_code == 200:
                    vec_data = resp_vec.json()
                    emb = vec_data.get("embedding", [])
                    dims = vec_data.get("dimensions", 0)
                    if len(emb) == 4096 and dims == 4096:
                        self.log_pass("raw neural vector", f"{name} (/vector/{slug}.json) -> exactly 4,096 float dimensions")
                    else:
                        self.log_fail("raw neural vector", f"/vector/{slug}.json", f"Expected 4096 dimensions, got {len(emb)}")

                    if emb and isinstance(emb[0], float):
                        self.log_pass("raw vector precision", f"{slug} float precision validated ({emb[0]:.6f})")
                    else:
                        self.log_fail("raw vector precision", f"/vector/{slug}.json", "Vector values are not floats")
                else:
                    self.log_fail("raw neural vector", f"/vector/{slug}.json", f"Status {resp_vec.status_code}")
            except Exception as e:
                self.log_fail("raw neural vector", f"/vector/{slug}.json", str(e))

    # =========================================================================
    # 3. KEYWORDS & RULES CITATION ENGINE
    # =========================================================================
    def test_keywords_and_rules(self):
        print("\n--- [3/10] Running Keywords & Rules Citation Engine Suite ---")
        keywords = list(self.db.keywords.find({}, {"_id": 0, "slug": 1, "name": 1}))
        if not keywords:
            self.log_fail("keywords suite", "Mongo keywords", "No keywords found in avascry_swu.keywords")
            return

        sampled_kw = self.rng.sample(keywords, min(6, len(keywords)))
        for kw in sampled_kw:
            kslug = kw.get("slug")
            kname = kw.get("name")

            # HTML keyword page
            try:
                resp_html = self.get(f"/keyword/{kslug}")
                if resp_html.status_code == 200:
                    if kname.lower() in resp_html.text.lower():
                        self.log_pass("keyword HTML", f"Keyword '{kname}' (/keyword/{kslug})")
                    else:
                        self.log_warn("keyword HTML", f"Keyword '{kname}'", "Keyword name missing from HTML")
                else:
                    self.log_fail("keyword HTML", f"/keyword/{kslug}", f"Status {resp_html.status_code}")
            except Exception as e:
                self.log_fail("keyword HTML", f"/keyword/{kslug}", str(e))

            # JSON keyword API
            try:
                resp_json = self.get(f"/keyword/{kslug}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    if data.get("slug") == kslug and data.get("name") == kname:
                        self.log_pass("keyword JSON", f"Keyword '{kname}' API verified")
                    else:
                        self.log_fail("keyword JSON", f"/keyword/{kslug}.json", "JSON attributes mismatch")
                else:
                    self.log_fail("keyword JSON", f"/keyword/{kslug}.json", f"Status {resp_json.status_code}")
            except Exception as e:
                self.log_fail("keyword JSON", f"/keyword/{kslug}.json", str(e))

            # Markdown keyword export
            try:
                resp_md = self.get(f"/keyword/{kslug}.md")
                if resp_md.status_code == 200 and f"# {kname}" in resp_md.text:
                    self.log_pass("keyword Markdown", f"Keyword '{kname}' Markdown header verified")
                else:
                    self.log_warn("keyword Markdown", f"/keyword/{kslug}.md", f"Status {resp_md.status_code}")
            except Exception as e:
                self.log_fail("keyword Markdown", f"/keyword/{kslug}.md", str(e))

        # Sample CR Rules sections
        rules = list(self.db.rules_entries.find({}, {"_id": 0, "slug": 1, "title": 1}).limit(10))
        if rules:
            rule_sample = self.rng.sample(rules, min(3, len(rules)))
            for r in rule_sample:
                rslug = r.get("slug")
                rtitle = r.get("title")
                try:
                    resp = self.get(f"/rule/{rslug}")
                    if resp.status_code == 200:
                        self.log_pass("CR rule section", f"Rule '{rtitle}' (/rule/{rslug})")
                    else:
                        self.log_fail("CR rule section", f"/rule/{rslug}", f"Status {resp.status_code}")
                except Exception as e:
                    self.log_fail("CR rule section", f"/rule/{rslug}", str(e))

        # Sample SWU Traits & Tribal Lexicons
        traits_sample = ["force", "trooper", "bounty-hunter", "imperial", "rebel"]
        for tslug in traits_sample:
            # HTML trait detail
            try:
                resp_thtml = self.get(f"/trait/{tslug}")
                if resp_thtml.status_code == 200:
                    self.log_pass("trait HTML", f"Trait /trait/{tslug} -> 200 OK")
                else:
                    self.log_fail("trait HTML", f"/trait/{tslug}", f"Status {resp_thtml.status_code}")
            except Exception as e:
                self.log_fail("trait HTML", f"/trait/{tslug}", str(e))

            # JSON trait detail
            try:
                resp_tjson = self.get(f"/trait/{tslug}.json")
                if resp_tjson.status_code == 200:
                    tdata = resp_tjson.json()
                    if tdata.get("slug") == tslug and tdata.get("card_count", 0) > 0:
                        self.log_pass("trait JSON", f"Trait /trait/{tslug}.json ({tdata['card_count']} cards) verified")
                    else:
                        self.log_fail("trait JSON", f"/trait/{tslug}.json", "Invalid trait JSON payload")
                else:
                    self.log_fail("trait JSON", f"/trait/{tslug}.json", f"Status {resp_tjson.status_code}")
            except Exception as e:
                self.log_fail("trait JSON", f"/trait/{tslug}.json", str(e))

            # Markdown trait detail
            try:
                resp_tmd = self.get(f"/trait/{tslug}.md")
                if resp_tmd.status_code == 200 and f"Slug:** {tslug}" in resp_tmd.text:
                    self.log_pass("trait Markdown", f"Trait /trait/{tslug}.md verified")
                else:
                    self.log_fail("trait Markdown", f"/trait/{tslug}.md", f"Status {resp_tmd.status_code}")
            except Exception as e:
                self.log_fail("trait Markdown", f"/trait/{tslug}.md", str(e))

    # =========================================================================
    # 4. OFFICIAL CARD CLARIFICATIONS & RULINGS FEED
    # =========================================================================
    def test_clarifications_and_rulings(self):
        print("\n--- [4/10] Running Official Clarifications & Rulings Feed Suite ---")
        try:
            resp_rulings = self.get("/rulings")
            if resp_rulings.status_code == 200 and "Official Rulings" in resp_rulings.text:
                self.log_pass("rulings feed", "/rulings live feed rendered 200 OK")
            else:
                self.log_fail("rulings feed", "/rulings", f"Status {resp_rulings.status_code}")
        except Exception as e:
            self.log_fail("rulings feed", "/rulings", str(e))

        # Verify errata feed
        try:
            resp_errata = self.get("/errata")
            if resp_errata.status_code == 200 and "Errata" in resp_errata.text:
                self.log_pass("errata feed", "/errata page rendered 200 OK")
            else:
                self.log_fail("errata feed", "/errata", f"Status {resp_errata.status_code}")
        except Exception as e:
            self.log_fail("errata feed", "/errata", str(e))

        # Verify individual ruling pages
        rulings_with_slug = list(self.db.clarifications.find({"slug": {"$exists": True, "$ne": ""}}, {"_id": 0, "slug": 1}).limit(20))
        if rulings_with_slug:
            sampled_r = self.rng.sample(rulings_with_slug, min(4, len(rulings_with_slug)))
            for r in sampled_r:
                r_slug = r.get("slug")
                try:
                    resp_r = self.get(f"/ruling/{r_slug}")
                    if resp_r.status_code == 200:
                        self.log_pass("ruling detail", f"/ruling/{r_slug} -> 200 OK")
                    else:
                        self.log_fail("ruling detail", f"/ruling/{r_slug}", f"Status {resp_r.status_code}")
                except Exception as e:
                    self.log_fail("ruling detail", f"/ruling/{r_slug}", str(e))

        # Verify cards with official clarifications render them
        clarifications = list(self.db.clarifications.find({}).limit(20))
        if clarifications:
            sampled_clar = self.rng.sample(clarifications, min(5, len(clarifications)))
            for clar in sampled_clar:
                c_slug = clar.get("card_slug") or (clar.get("card_id", "").replace("card:", "") if clar.get("card_id") else "")
                if not c_slug:
                    continue
                try:
                    resp_card = self.get(f"/card/{c_slug}")
                    if resp_card.status_code == 200:
                        self.log_pass("card clarification", f"Card '{c_slug}' clarification page verified")
                    else:
                        self.log_warn("card clarification", f"/card/{c_slug}", f"Status {resp_card.status_code}")
                except Exception as e:
                    self.log_fail("card clarification", f"/card/{c_slug}", str(e))

    # =========================================================================
    # 5. SEARCH & FILTER MECHANICS
    # =========================================================================
    def test_search_and_filters(self):
        print("\n--- [5/10] Running Search & Filter Mechanics Suite ---")
        filter_tests = [
            ("?aspect=Vigilance", "Vigilance"),
            ("?aspect=Command", "Command"),
            ("?type=Leader", "Leader"),
            ("?q=Luke", "Luke"),
        ]

        for query_param, expected_text in filter_tests:
            try:
                resp = self.get(f"/{query_param}")
                if resp.status_code == 200 and expected_text.lower() in resp.text.lower():
                    self.log_pass("catalog filter", f"Filter '{query_param}' matched expected content '{expected_text}'")
                else:
                    self.log_fail("catalog filter", f"/{query_param}", f"Status {resp.status_code}")
            except Exception as e:
                self.log_fail("catalog filter", f"/{query_param}", str(e))

    # =========================================================================
    # 6. COMPREHENSIVE RULES SURFACES
    # =========================================================================
    def test_comprehensive_rules_exports(self):
        print("\n--- [6/10] Running Comprehensive Rules Surfaces Suite ---")
        rules_endpoints = [
            ("/rules.md", "text/markdown", ["Star Wars: Unlimited", "Rules", "Arenas"]),
            ("/rules.json", "application/json", ["Star Wars: Unlimited", "phases", "arenas"]),
        ]

        for path, expected_ct, expected_frags in rules_endpoints:
            try:
                resp = self.get(path)
                if resp.status_code == 200:
                    missing = [f for f in expected_frags if f.lower() not in resp.text.lower()]
                    if not missing:
                        self.log_pass("rules export", f"{path} format and fragments validated")
                    else:
                        self.log_warn("rules export", path, f"Missing fragments: {missing}")

                    if "max-age=86400" in resp.headers.get("cache-control", ""):
                        self.log_pass("rules cache", f"{path} Cache-Control verified")
                    else:
                        self.log_warn("rules cache", path, f"Unexpected Cache-Control: {resp.headers.get('cache-control')}")
                else:
                    self.log_fail("rules export", path, f"Status {resp.status_code}")
            except Exception as e:
                self.log_fail("rules export", path, str(e))

    # =========================================================================
    # 7. MACHINE DISCOVERY & LLM MANIFESTS
    # =========================================================================
    def test_machine_discovery(self):
        print("\n--- [7/10] Running Machine Discovery & LLM Manifests Suite ---")
        manifests = [
            ("/llms.txt", ["Star Wars: Unlimited", "https://swu.avascry.com/"]),
            ("/llms-full.txt", ["Star Wars: Unlimited", "Game: Star Wars: Unlimited"]),
            ("/.well-known/ai-content", ["domain: swu.avascry.com", "ai-train: allowed"]),
            ("/robots.txt", ["User-agent: *", "https://swu.avascry.com/sitemap.xml", "https://swu.avascry.com/sitemap.html"]),
            ("/sitemap.xml", ["<urlset", "/card/", "/keywords", "/rules"]),
            ("/sitemap.html", ["Machine Index", "Canonical Cards Directory", "[MD]", "[JSON]", "[Vector]", "[Similar]"]),
            ("/sitemap.md", ["# Star Wars: Unlimited Master Machine Sitemap", "## Expansions & Sets", "## Keywords & Game Mechanics", "## Canonical Cards Directory", "[Vector]"]),
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
    # 8. IMAGE DELIVERY & LOCAL SCAN RESOLUTION
    # =========================================================================
    def test_image_delivery(self):
        print("\n--- [8/10] Running Image Delivery & Local Scan Resolution Suite ---")
        sample_cards = list(self.db.cards.find({"local_image_front": {"$exists": True, "$ne": None}}, 
                                               {"slug": 1, "local_image_front": 1, "local_image_back": 1, "type": 1}).limit(15))
        if not sample_cards:
            self.log_warn("image delivery", "Mongo cards", "No cards with local_image_front found")
            return

        sampled = self.rng.sample(sample_cards, min(6, len(sample_cards)))
        for c in sampled:
            front_img = c.get("local_image_front")
            if front_img:
                try:
                    resp = self.client.get(front_img)
                    if resp.status_code == 200:
                        ct = resp.headers.get("content-type", "")
                        if "image/" in ct:
                            self.log_pass("card front image", f"{front_img} -> 200 OK ({ct})")
                        else:
                            self.log_warn("card front image", front_img, f"Unexpected content-type: {ct}")
                    else:
                        self.log_warn("card front image", front_img, f"Status {resp.status_code}")
                except Exception as e:
                    self.log_fail("card front image", front_img, str(e))

            # For double-sided cards (Leaders/Bases), verify back image
            back_img = c.get("local_image_back")
            if back_img:
                try:
                    resp_b = self.client.get(back_img)
                    if resp_b.status_code == 200:
                        self.log_pass("card back image", f"{back_img} -> 200 OK")
                    else:
                        self.log_warn("card back image", back_img, f"Status {resp_b.status_code}")
                except Exception as e:
                    self.log_fail("card back image", back_img, str(e))

    # =========================================================================
    # 9. 404 & MALFORMED BOUNDARIES
    # =========================================================================
    def test_boundary_and_404(self):
        print("\n--- [9/10] Running 404 & Malformed Boundaries Suite ---")
        bogus_routes = [
            ("/card/definitely-not-a-real-swu-card-12345", 404),
            ("/card/definitely-not-a-real-swu-card-12345.json", 404),
            ("/card/definitely-not-a-real-swu-card-12345.md", 404),
            ("/card/definitely-not-a-real-swu-card-12345.xml", 404),
            ("/keyword/definitely-not-a-real-keyword-12345", 404),
            ("/keyword/definitely-not-a-real-keyword-12345.json", 404),
            ("/keyword/definitely-not-a-real-keyword-12345.md", 404),
            ("/trait/definitely-not-a-real-trait-12345", 404),
            ("/trait/definitely-not-a-real-trait-12345.json", 404),
            ("/trait/definitely-not-a-real-trait-12345.md", 404),
            ("/rule/99-99-definitely-not-a-real-rule", 404),
            ("/vector/definitely-not-a-real-swu-card-12345.json", 404),
            ("/card/", 404),
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
            resp_prefix = self.client.get("/swu", headers={"User-Agent": self.user_agent, "Host": "avascry.com"})
            # Subdomain rewrite via Host header
            resp_subdomain = self.client.get("/", headers={"User-Agent": self.user_agent, "Host": "swu.avascry.com"})

            if resp_prefix.status_code == 200 and resp_subdomain.status_code == 200:
                self.log_pass("subdomain routing", "Both /swu and Host: swu.avascry.com / return 200 OK")
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
        print("    SWU SITEBLASTER 9001 — INVARIANT & ROUTE TESTER     ")
        print(f"  Mode: {'DEEP' if self.deep else 'QUICK'} | Seed: {self.seed}")
        print(f"  Target: {self.base_url} (ASGI In-Process: {self._is_testclient})")
        print("========================================================")

        self.test_core_routes()
        self.test_entity_cards()
        self.test_similarity_graph()
        self.test_keywords_and_rules()
        self.test_clarifications_and_rulings()
        self.test_search_and_filters()
        self.test_comprehensive_rules_exports()
        self.test_machine_discovery()
        self.test_image_delivery()
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
        print(f"SWU SiteBlaster Summary: {self.passed} passed | {self.failed} failed | {self.warnings} warnings ({elapsed:.2f}s)")
        if self.failed == 0:
            print("\033[92m\nTHE FORCE IS WITH AVASCRY. ALL SECTORS SECURED. GALAXY AT PEACE.\033[0m\n")
        else:
            print(f"\033[91m\nSWU NEEDS ATTENTION ({self.failed} failures).\033[0m\n")
        print("========================================================\n")

        return 1 if self.failed > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="Star Wars Unlimited SiteBlaster 9001 — Invariant & Route Tester")
    parser.add_argument("--deep", action="store_true", help="Run comprehensive deep suite with larger sample sizes")
    parser.add_argument("--quick", action="store_true", help="Run fast quick suite with targeted sample sizes (default)")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic random seed (default: 1337)")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL of live server (e.g. http://127.0.0.1:8004). Defaults to in-process ASGI.")
    args = parser.parse_args()

    is_deep = bool(args.deep)
    blaster = SWUSiteBlaster(base_url=args.base_url, deep=is_deep, seed=args.seed)
    exit_code = blaster.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
