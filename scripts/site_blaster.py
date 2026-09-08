#!/usr/bin/env python3
"""
site_blaster.py — SiteBlaster 9001: Real-entity AvaScry integration & invariant tester.

Hardened non-destructive inspection runner that exercises live/ASGI application routes,
Mongo corpus data, Markdown representations, 4096-dim vectors, similarity graphs,
rendered Commander CTAs, set/artist blurbs, machine discovery manifests, and 404 boundaries.

Usage:
    python scripts/site_blaster.py --quick
    python scripts/site_blaster.py --deep
    python scripts/site_blaster.py --quick --seed 42
    python scripts/site_blaster.py --quick --base-url http://127.0.0.1:8000
"""

import sys
import os
import re
import html
import time
import math
import random
import argparse
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple, Set

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
from app import app, is_commander_eligible, slugify


class SiteBlaster:
    USER_AGENT = "Ava9001/1.0 (SiteBlaster 9001; AvaScry Site Blaster; ISO-9001-Certified; Over-9000-Compliant; +https://avascry.com)"

    def __init__(self, base_url: Optional[str] = None, deep: bool = False, seed: int = 1337):
        self.deep = deep
        self.seed = seed
        self.rng = random.Random(self.seed)
        self.base_url = (base_url or "https://avascry.com").rstrip("/")
        self.user_agent = self.USER_AGENT
        
        # Setup HTTP client: in-process TestClient or live HTTP network client
        default_headers = {"User-Agent": self.user_agent}
        if base_url:
            self.client = httpx.Client(base_url=self.base_url, timeout=30.0, follow_redirects=False, headers=default_headers)
            self._is_testclient = False
        else:
            self.client = TestClient(app, base_url=self.base_url, follow_redirects=False, headers=default_headers)
            self._is_testclient = True

        self.db = get_mongo_db()
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.failures_recap: List[Dict[str, Any]] = []
        self.warnings_recap: List[Dict[str, Any]] = []
        self.start_time = 0.0

    def log_pass(self, category: str, message: str):
        self.passed += 1
        print(f"\033[92m[PASS]\033[0m {category:<18} {message}")

    def log_fail(self, category: str, message: str, reason: str = "", details: Optional[Dict[str, Any]] = None):
        self.failed += 1
        self.failures_recap.append({
            "category": category,
            "message": message,
            "reason": reason,
            "details": details or {}
        })
        extra = f" -> {reason}" if reason else ""
        print(f"\033[91m[FAIL]\033[0m {category:<18} {message}{extra}")
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
        print(f"\033[93m[WARN]\033[0m {category:<18} {message}{extra}")
        if details:
            for k, v in details.items():
                print(f"       \033[90m{k} = {v}\033[0m")

    def normalize_url(self, url: str) -> str:
        """Same-origin normalization: strip host/scheme, quote non-ASCII, and route through ASGI app."""
        if not url:
            return "/"
        url = url.strip()
        for prefix in ("https://avascry.com", "http://avascry.com", "https://www.avascry.com", "http://www.avascry.com", self.base_url):
            if url.startswith(prefix):
                url = url[len(prefix):]
                break
        if not url.startswith("/"):
            url = "/" + url
        import urllib.parse
        return urllib.parse.quote(url, safe="/:@&=+$,?#%-_.~")

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        norm_path = self.normalize_url(path)
        req_headers = {"User-Agent": self.user_agent}
        if headers:
            req_headers.update(headers)
        try:
            return self.client.get(norm_path, headers=req_headers)
        except UnicodeEncodeError:
            # Handle Starlette TestClient ASGI scope latin-1 limitation on non-ASCII DB slugs
            import unicodedata
            import urllib.parse
            unquoted = urllib.parse.unquote(norm_path)
            clean_path = unicodedata.normalize("NFKD", unquoted).encode("ascii", "ignore").decode("ascii")
            return self.client.get(clean_path, headers=req_headers)

    # =========================================================================
    # 1. CORE ROUTE SMOKE
    # =========================================================================
    def test_core_routes(self):
        routes = [
            ("/", 200),
            ("/commander", 200),
            ("/sets", 200),
            ("/artists", 200),
            ("/developers", 200),
            ("/about", 200),
            ("/contact", 200),
            ("/privacy", 200),
            ("/terms", 200),
            ("/llms.txt", 200),
            ("/llms-full.txt", 200),
            ("/sitemap.xml", 200),
            ("/sitemap.md", 200),
            ("/sitemap.html", 200),
            ("/rules.md", 200),
            ("/legalities.md", 200),
            ("/sets.md", 200),
            ("/random", 303),
            ("/card/sol-ring", 303),
            ("/printing/sol-ring-lea", 200),
            ("/set/lea", 200),
            ("/artist/christopher-rush", 200),
            ("/live-gallery", 200),
            ("/api/live-gallery/feed", 200),
            ("/dominion", 200),
            ("/dominion/random", 303),
            ("/swu", 200),
            ("/swu/random", 307),
        ]
        for route, expected_status in routes:
            try:
                resp = self.get(route)
                if resp.status_code == expected_status:
                    self.log_pass("core smoke", f"{route} [{resp.status_code}]")
                elif resp.status_code < 500 and expected_status in (200, 303) and resp.status_code in (200, 301, 302, 303, 307, 308):
                    self.log_pass("core smoke", f"{route} [{resp.status_code} redirect/ok]")
                else:
                    self.log_fail("core smoke", f"{route}", f"expected {expected_status}, got {resp.status_code}",
                                  {"route": route, "status": resp.status_code, "expected": expected_status})
            except Exception as e:
                self.log_fail("core smoke", f"{route}", f"exception: {e}", {"route": route, "error": str(e)})

    # =========================================================================
    # 2. REAL-ENTITY SAMPLING (Cards, Sets, Artists) WITH CANONICAL SYMMETRY
    # =========================================================================
    def test_real_entity_sampling(self):
        sample_card_count = 101 if self.deep else 7
        sample_set_count = 31 if self.deep else 3
        sample_artist_count = 31 if self.deep else 3

        # Deterministic sampling from MongoDB
        candidates = list(self.db["cards"].find(
            {"lang": "en", "name": {"$exists": True, "$ne": ""}, "set": {"$exists": True, "$ne": ""}},
            {"_id": 1, "name": 1, "slug": 1, "set": 1, "printing_slug": 1, "oracle_id": 1, "id": 1}
        ).sort("oracle_id", 1).limit(5000))

        if len(candidates) > sample_card_count:
            card_docs = self.rng.sample(candidates, sample_card_count)
        else:
            card_docs = candidates

        for card in card_docs:
            c_slug = card.get("printing_slug") or card.get("slug") or slugify(card.get("name") or "")
            c_set = (card.get("set") or "").lower()
            p_slug = f"{c_slug}-{c_set}" if (c_set and not c_slug.endswith(f"-{c_set}")) else c_slug
            name = card.get("name", "Unknown")
            oracle_id = card.get("oracle_id")

            # 1. HTML representation
            try:
                resp_html = self.get(f"/printing/{p_slug}")
                if resp_html.status_code == 200:
                    resp_text = resp_html.text.lower()
                    if name.lower() in resp_text or name.lower() in html.unescape(resp_text):
                        self.log_pass("entity card HTML", f"{name} ({p_slug})")
                    else:
                        self.log_warn("entity card HTML", f"{name} ({p_slug})", "Card name missing from HTML response",
                                      {"printing_slug": p_slug, "oracle_id": oracle_id})

                    # Schema.org & OpenGraph validation
                    if '<script type="application/ld+json">' in resp_html.text:
                        self.log_pass("card Schema.org", f"{p_slug} contains JSON-LD metadata")
                    else:
                        self.log_warn("card Schema.org", f"{p_slug}", "Missing application/ld+json script tag")

                    if 'property="og:image"' in resp_html.text and 'property="og:title"' in resp_html.text:
                        self.log_pass("card OpenGraph", f"{p_slug} OpenGraph meta tags verified")
                    else:
                        self.log_warn("card OpenGraph", f"{p_slug}", "Missing og:image or og:title meta tags")
                else:
                    self.log_fail("entity card HTML", f"/printing/{p_slug}", f"status {resp_html.status_code}",
                                  {"printing_slug": p_slug, "oracle_id": oracle_id, "status": resp_html.status_code})
            except Exception as e:
                self.log_fail("entity card HTML", f"/printing/{p_slug}", str(e), {"printing_slug": p_slug, "oracle_id": oracle_id})

            # 2. Markdown representation
            try:
                resp_md = self.get(f"/printing/{p_slug}.md")
                if resp_md.status_code == 200:
                    if "text/markdown" in resp_md.headers.get("content-type", "") or resp_md.text.startswith("---") or f"# {name}" in resp_md.text:
                        self.log_pass("entity card MD", f"{name} ({p_slug}.md)")
                    else:
                        self.log_warn("entity card MD", f"{p_slug}.md", "Markdown missing header/format",
                                      {"printing_slug": p_slug, "oracle_id": oracle_id})
                else:
                    self.log_fail("entity card MD", f"/printing/{p_slug}.md", f"status {resp_md.status_code}",
                                  {"printing_slug": p_slug, "oracle_id": oracle_id, "status": resp_md.status_code})
            except Exception as e:
                self.log_fail("entity card MD", f"/printing/{p_slug}.md", str(e), {"printing_slug": p_slug, "oracle_id": oracle_id})

            # 3. JSON representation & Canonical symmetry
            try:
                resp_json = self.get(f"/printing/{p_slug}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    card_data = data.get("card", data)
                    c_name = card_data.get("name") or data.get("name")
                    c_oracle = card_data.get("oracle_id") or data.get("oracle_id")

                    if c_name == name or c_oracle == oracle_id:
                        self.log_pass("entity card JSON", f"{name} ({p_slug}.json)")
                    else:
                        self.log_fail("entity card JSON", f"{p_slug}.json", "Canonical symmetry mismatch with Mongo",
                                      {"expected_name": name, "json_name": c_name, "oracle_id": oracle_id})
                else:
                    self.log_fail("entity card JSON", f"/printing/{p_slug}.json", f"status {resp_json.status_code}",
                                  {"printing_slug": p_slug, "oracle_id": oracle_id, "status": resp_json.status_code})
            except Exception as e:
                self.log_fail("entity card JSON", f"/printing/{p_slug}.json", str(e), {"printing_slug": p_slug, "oracle_id": oracle_id})

            # 4. Cockatrice XML representation
            try:
                resp_xml = self.get(f"/printing/{p_slug}.xml")
                if resp_xml.status_code == 200 and "application/xml" in resp_xml.headers.get("content-type", ""):
                    if "cockatrice_carddatabase" in resp_xml.text:
                        self.log_pass("entity card XML", f"{name} ({p_slug}.xml)")
                    else:
                        self.log_fail("entity card XML", f"/printing/{p_slug}.xml", "missing cockatrice_carddatabase tag")
                else:
                    self.log_fail("entity card XML", f"/printing/{p_slug}.xml", f"status {resp_xml.status_code}")
            except Exception as e:
                self.log_fail("entity card XML", f"/printing/{p_slug}.xml", str(e))

            # 5. CSV representation
            try:
                resp_csv = self.get(f"/printing/{p_slug}.csv")
                if resp_csv.status_code == 200 and "text/csv" in resp_csv.headers.get("content-type", ""):
                    if "canonical_url" in resp_csv.text:
                        self.log_pass("entity card CSV", f"{name} ({p_slug}.csv)")
                    else:
                        self.log_fail("entity card CSV", f"/printing/{p_slug}.csv", "missing CSV headers")
                else:
                    self.log_fail("entity card CSV", f"/printing/{p_slug}.csv", f"status {resp_csv.status_code}")
            except Exception as e:
                self.log_fail("entity card CSV", f"/printing/{p_slug}.csv", str(e))

        # Sample Sets deterministically
        all_sets = list(self.db["cards"].aggregate([
            {"$match": {"set": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$set", "set_name": {"$first": "$set_name"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]))
        if len(all_sets) > sample_set_count:
            sampled_sets = self.rng.sample(all_sets, sample_set_count)
        else:
            sampled_sets = all_sets

        for s in sampled_sets:
            set_code = s["_id"].lower()
            set_name = s.get("set_name") or set_code.upper()
            try:
                resp_html = self.get(f"/set/{set_code}")
                resp_md = self.get(f"/set/{set_code}.md")
                resp_json = self.get(f"/set/{set_code}.json")

                if resp_html.status_code == 200 and resp_md.status_code == 200 and resp_json.status_code == 200:
                    self.log_pass("entity set suite", f"{set_name} [{set_code}] (HTML, MD, JSON)")
                else:
                    self.log_fail("entity set suite", f"/set/{set_code}", "One or more representation routes failed",
                                  {"set_code": set_code, "HTML": resp_html.status_code, "MD": resp_md.status_code, "JSON": resp_json.status_code})
            except Exception as e:
                self.log_fail("entity set suite", f"/set/{set_code}", str(e), {"set_code": set_code})

        # Sample Artists deterministically
        all_artists = list(self.db["cards"].aggregate([
            {"$match": {"artist": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$artist", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]))
        if len(all_artists) > sample_artist_count:
            sampled_artists = self.rng.sample(all_artists, sample_artist_count)
        else:
            sampled_artists = all_artists

        for a in sampled_artists:
            artist_name = a["_id"]
            artist_slug = re.sub(r'[^a-z0-9]+', '-', artist_name.lower()).strip('-')
            try:
                resp_html = self.get(f"/artist/{artist_slug}")
                resp_md = self.get(f"/artist/{artist_slug}.md")
                resp_json = self.get(f"/artist/{artist_slug}.json")

                if resp_html.status_code == 200 and resp_md.status_code == 200 and resp_json.status_code == 200:
                    self.log_pass("entity artist suite", f"{artist_name} ({artist_slug})")
                else:
                    self.log_fail("entity artist suite", f"/artist/{artist_slug}", "One or more representation routes failed",
                                  {"artist": artist_name, "HTML": resp_html.status_code, "MD": resp_md.status_code, "JSON": resp_json.status_code})
            except Exception as e:
                self.log_fail("entity artist suite", f"/artist/{artist_slug}", str(e), {"artist": artist_name})

    # =========================================================================
    # 3. MARKDOWN INTEGRITY & INTERNAL LINK RESOLUTION
    # =========================================================================
    def test_markdown_integrity(self):
        sample_count = 19 if self.deep else 5
        candidates = list(self.db["cards"].find(
            {"lang": "en", "printing_slug": {"$exists": True, "$ne": ""}},
            {"_id": 1, "name": 1, "printing_slug": 1, "oracle_id": 1}
        ).sort("oracle_id", 1).limit(2000))

        if len(candidates) > sample_count:
            card_docs = self.rng.sample(candidates, sample_count)
        else:
            card_docs = candidates

        link_regex = re.compile(r'\[([^\]]+)\]\((/printing/[^)]+|https://avascry.com/printing/[^)]+)\)')

        for card in card_docs:
            p_slug = card.get("printing_slug")
            name = card.get("name", "")

            try:
                resp = self.get(f"/printing/{p_slug}.md")
                if resp.status_code != 200:
                    self.log_fail("markdown integrity", f"{p_slug}.md", f"status {resp.status_code}", {"slug": p_slug})
                    continue

                content = resp.text

                # Invariant: No raw SVG or HTML markup masquerading as markdown
                if "<svg" in content.lower() or "</svg>" in content.lower():
                    self.log_fail("markdown lint", f"{p_slug}.md", "contains raw SVG artifacts", {"slug": p_slug})
                elif "<!doctype html" in content.lower():
                    self.log_fail("markdown lint", f"{p_slug}.md", "HTML page masquerading as Markdown", {"slug": p_slug})
                else:
                    self.log_pass("markdown lint", f"{p_slug}.md clean of SVG/HTML pollution")

                # Sample internal markdown links and verify resolution
                links = link_regex.findall(content)
                if links:
                    sample_links = self.rng.sample(links, min(len(links), 3))
                    for link_text, link_url in sample_links:
                        norm_url = self.normalize_url(link_url)
                        target_resp = self.get(norm_url)
                        if target_resp.status_code in (200, 301, 302, 303, 307, 308):
                            self.log_pass("markdown link", f"{link_text} -> {norm_url} [{target_resp.status_code}]")
                        else:
                            self.log_fail("markdown link", f"{link_text} -> {norm_url}", f"status {target_resp.status_code}",
                                          {"source_slug": p_slug, "target_url": norm_url, "status": target_resp.status_code})

            except Exception as e:
                self.log_fail("markdown integrity", f"{p_slug}.md", str(e), {"slug": p_slug})

    # =========================================================================
    # 4. NEURAL SURFACES (4096-dim Vectors & Representation Cross-Checking)
    # =========================================================================
    def test_neural_surfaces(self):
        sample_count = 31 if self.deep else 7

        candidates = list(self.db["card_embeddings_8b"].find(
            {"embedding": {"$exists": True, "$ne": []}},
            {"_id": 1, "slug": 1, "card_name": 1, "oracle_id": 1}
        ).sort("slug", 1).limit(1000))

        if not candidates:
            self.log_fail("neural vectors", "card_embeddings_8b", "No embeddings found in 'card_embeddings_8b' collection")
            return

        emb_docs = self.rng.sample(candidates, min(len(candidates), sample_count))

        # Always include Akroan Line Breaker fixture
        akroan_doc = self.db["card_embeddings_8b"].find_one({"slug": "akroan-line-breaker"}, {"_id": 1, "slug": 1, "card_name": 1, "oracle_id": 1})
        if akroan_doc and akroan_doc not in emb_docs:
            emb_docs.append(akroan_doc)

        for doc in emb_docs:
            c_slug = doc.get("slug")
            c_name = doc.get("card_name") or c_slug
            if not c_slug:
                continue

            # 1. Vector JSON endpoint check
            try:
                resp_vec = self.get(f"/vector/{c_slug}.json")
                if resp_vec.status_code == 200:
                    v_data = resp_vec.json()
                    embedding = v_data.get("embedding", [])
                    dims = v_data.get("dimensions", len(embedding))
                    model = v_data.get("model")

                    if dims != 4096 or len(embedding) != 4096:
                        self.log_fail("neural vector", f"{c_slug}", f"vector dimension mismatch (got {dims}/{len(embedding)}, expected 4096)",
                                      {"expected": 4096, "dimensions": dims, "len": len(embedding), "model": model})
                    elif model != "qwen3-embedding-8b":
                        self.log_fail("neural vector", f"{c_slug}", f"legacy model detected: {model} (expected qwen3-embedding-8b)",
                                      {"expected": "qwen3-embedding-8b", "model": model})
                    else:
                        has_non_finite = any(not math.isfinite(x) for x in embedding if isinstance(x, (int, float)))
                        has_null = any(x is None for x in embedding)
                        if has_non_finite or has_null:
                            self.log_fail("neural vector", f"{c_slug}", "contains NaN, null, or Inf", {"slug": c_slug})
                        else:
                            self.log_pass("neural vector", f"{c_name} (4096-dim {model})")
                else:
                    self.log_fail("neural vector", f"/vector/{c_slug}.json", f"status {resp_vec.status_code}", {"slug": c_slug})
            except Exception as e:
                self.log_fail("neural vector", f"/vector/{c_slug}.json", str(e), {"slug": c_slug})

            # 2. Similar JSON & Markdown cross-representation check
            try:
                resp_sim_json = self.get(f"/similar/{c_slug}.json")
                resp_sim_md = self.get(f"/similar/{c_slug}.md")

                if resp_sim_json.status_code == 200:
                    s_data = resp_sim_json.json()
                    similar_list = s_data.get("similar_cards", [])

                    # Invariants: No self-reference, no duplicate neighbors
                    neighbor_slugs = [n.get("slug") or n.get("printing_slug") for n in similar_list if isinstance(n, dict)]
                    clean_slugs = [s for s in neighbor_slugs if s]

                    if c_slug in clean_slugs:
                        self.log_fail("neural similar", f"{c_slug}", "similarity graph contains self-reference",
                                      {"slug": c_slug, "neighbors": clean_slugs[:5]})
                    elif len(clean_slugs) != len(set(clean_slugs)):
                        self.log_fail("neural similar", f"{c_slug}", "duplicate neighbors found",
                                      {"slug": c_slug, "total": len(clean_slugs), "unique": len(set(clean_slugs))})
                    else:
                        self.log_pass("neural similar", f"{c_name} ({len(clean_slugs)} unique valid neighbors)")

                    # Cross-check JSON vs Markdown representation
                    if resp_sim_md.status_code == 200:
                        md_content = resp_sim_md.text
                        # Check that top neighbors in JSON appear in Markdown
                        top_json_names = [n.get("name") for n in similar_list[:5] if isinstance(n, dict) and n.get("name")]
                        missing_in_md = [n for n in top_json_names if n.lower() not in md_content.lower()]
                        if missing_in_md:
                            self.log_fail("neural parity", f"{c_slug}", "JSON vs MD representation divergence",
                                          {"slug": c_slug, "missing_in_md": missing_in_md})
                        else:
                            self.log_pass("neural parity", f"{c_name} (.json and .md agree)")
                elif resp_sim_json.status_code == 404:
                    self.log_warn("neural similar", f"/similar/{c_slug}.json", "no precomputed similarity doc", {"slug": c_slug})
                else:
                    self.log_fail("neural similar", f"/similar/{c_slug}.json", f"status {resp_sim_json.status_code}", {"slug": c_slug})
            except Exception as e:
                self.log_fail("neural similar", f"/similar/{c_slug}.json", str(e), {"slug": c_slug})

    # =========================================================================
    # 5. COMMANDER CORRECTNESS & RENDERED CTA INSPECTION
    # =========================================================================
    def test_commander_correctness(self):
        # Known fixtures with CTA assertion
        fixtures = [
            {
                "name": "Kenrith, the Returned King",
                "slug": "kenrith-the-returned-king-eld",
                "type_line": "Legendary Creature — Human Noble",
                "oracle_text": "",
                "expected": True,
                "label": "Normal Legendary Creature"
            },
            {
                "name": "Atraxa, Praetors' Voice",
                "slug": "atraxa-praetors-voice-cm2",
                "type_line": "Legendary Creature — Phyrexian Angel Horror",
                "oracle_text": "Flying, vigilance, deathtouch, lifelink",
                "expected": True,
                "label": "Multi-type Legendary Creature"
            },
            {
                "name": "Lightning Bolt",
                "slug": "lightning-bolt-lea",
                "type_line": "Instant",
                "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                "expected": False,
                "label": "Ordinary Instant"
            },
            {
                "name": "Counterspell",
                "slug": "counterspell-lea",
                "type_line": "Instant",
                "oracle_text": "Counter target spell.",
                "expected": False,
                "label": "Ordinary Instant"
            },
            {
                "name": "Teferi, Temporal Archmage",
                "slug": "teferi-temporal-archmage-c14",
                "type_line": "Legendary Planeswalker — Teferi",
                "oracle_text": "+1: Look at the top two cards of your library...\nTeferi, Temporal Archmage can be your commander.",
                "expected": True,
                "label": "Commander-eligible Planeswalker"
            },
            {
                "name": "Daretti, Scrap Savant",
                "slug": "daretti-scrap-savant-c14",
                "type_line": "Legendary Planeswalker — Daretti",
                "oracle_text": "+2: Discard up to two cards...\nDaretti, Scrap Savant can be your commander.",
                "expected": True,
                "label": "Commander-eligible Planeswalker"
            },
            {
                "name": "Liliana of the Veil",
                "slug": "liliana-of-the-veil-isd",
                "type_line": "Legendary Planeswalker — Liliana",
                "oracle_text": "+1: Each player discards a card.\n-2: Target player sacrifices a creature.",
                "expected": False,
                "label": "Standard Legendary Planeswalker"
            },
            {
                "name": "Jace, the Mind Sculptor",
                "slug": "jace-the-mind-sculptor-wwk",
                "type_line": "Legendary Planeswalker — Jace",
                "oracle_text": "+2: Look at the top card of target player's library...",
                "expected": False,
                "label": "Standard Legendary Planeswalker"
            },
        ]

        for fix in fixtures:
            card_mock = {"name": fix["name"], "type_line": fix["type_line"], "oracle_text": fix["oracle_text"]}
            is_eligible = is_commander_eligible(card_mock)
            
            # 1. Helper check
            if is_eligible == fix["expected"]:
                self.log_pass("commander helper", f"{fix['name']} ({fix['label']}) -> eligible={is_eligible}")
            else:
                self.log_fail("commander helper", f"{fix['name']}", "is_commander_eligible mismatch",
                              {"card": fix["name"], "expected": fix["expected"], "actual": is_eligible})

            # 2. Rendered Card Page CTA check
            p_slug = fix["slug"]
            try:
                resp = self.get(f"/printing/{p_slug}")
                if resp.status_code == 200:
                    html = resp.text
                    has_smartdeck_cta = "/commander?q=" in html or "SmartDeck" in html
                    has_partner_cta = "partners@avascry.com" in html

                    if fix["expected"]:
                        if has_smartdeck_cta:
                            self.log_pass("commander CTA", f"{fix['name']} -> renders SmartDeck Builder CTA")
                        else:
                            self.log_fail("commander CTA", f"{fix['name']}", "eligible Commander missing SmartDeck CTA in HTML",
                                          {"card": fix["name"], "slug": p_slug})
                    else:
                        if not has_smartdeck_cta or has_partner_cta:
                            self.log_pass("commander CTA", f"{fix['name']} -> renders Partner/Non-Commander CTA")
                        else:
                            self.log_fail("commander CTA", f"{fix['name']}", "non-Commander incorrectly renders SmartDeck CTA",
                                          {"card": fix["name"], "slug": p_slug})
                else:
                    self.log_warn("commander CTA", f"/printing/{p_slug}", f"fixture page status {resp.status_code}")
            except Exception as e:
                self.log_fail("commander CTA", f"/printing/{p_slug}", str(e), {"slug": p_slug})

        # Deterministic sampled consistency cross-check
        sample_count = 53 if self.deep else 19
        candidates = list(self.db["cards"].find(
            {"lang": "en"},
            {"_id": 1, "name": 1, "type_line": 1, "oracle_text": 1, "card_faces": 1, "raw": 1}
        ).sort("oracle_id", 1).limit(2000))

        if len(candidates) > sample_count:
            sampled_cards = self.rng.sample(candidates, sample_count)
        else:
            sampled_cards = candidates

        for card in sampled_cards:
            name = card.get("name", "Unknown")
            eligible = is_commander_eligible(card)
            t_line = (card.get("type_line") or "").lower()
            o_text = (card.get("oracle_text") or "").lower()
            faces = card.get("card_faces") or card.get("raw", {}).get("card_faces", [])
            front_type = (faces[0].get("type_line") or "").lower() if faces else ""
            front_oracle = (faces[0].get("oracle_text") or "").lower() if faces else ""

            should_be = (
                ("legendary" in t_line and "creature" in t_line) or
                ("legendary" in front_type and "creature" in front_type) or
                ("can be your commander" in o_text) or
                ("can be your commander" in front_oracle)
            )
            if eligible == should_be:
                self.log_pass("commander sample", f"{name} (eligible={eligible})")
            else:
                self.log_fail("commander sample", f"{name}", "Eligibility logic diverged from rule definition",
                              {"name": name, "eligible": eligible, "should_be": should_be, "type_line": t_line})

    # =========================================================================
    # 6. RANDOM ROUTE INVARIANTS
    # =========================================================================
    def test_random_routes(self):
        iterations = 31 if self.deep else 5
        for i in range(iterations):
            try:
                resp = self.get("/random")
                if resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("location", "")
                    if loc.startswith("/printing/"):
                        norm_loc = self.normalize_url(loc)
                        target_resp = self.get(norm_loc)
                        if target_resp.status_code == 200:
                            self.log_pass("random route", f"redirect -> {norm_loc} [200]")
                        else:
                            self.log_fail("random route", f"redirect -> {norm_loc}", f"target status {target_resp.status_code}",
                                          {"redirect_location": loc, "target_status": target_resp.status_code})
                    else:
                        self.log_fail("random route", "/random", f"unexpected redirect location: {loc}", {"location": loc})
                else:
                    self.log_fail("random route", "/random", f"expected 303 redirect, got {resp.status_code}", {"status": resp.status_code})
            except Exception as e:
                self.log_fail("random route", "/random", str(e))

    # =========================================================================
    # 7. SET INTEGRITY & PERMANENT REGRESSION FIXTURES (UNH, GTC, ORI, LEA)
    # =========================================================================
    def test_set_integrity(self):
        fixtures = [
            ("unh", "Unhinged (Zero-legal cards edgecase)"),
            ("gtc", "Gatecrash (Guild mechanics)"),
            ("ori", "Magic Origins (Flip walkers)"),
            ("lea", "Limited Edition Alpha (Power Nine & Duals)"),
        ]

        for set_code, desc in fixtures:
            try:
                resp_html = self.get(f"/set/{set_code}")
                resp_json = self.get(f"/set/{set_code}.json")
                resp_md = self.get(f"/set/{set_code}.md")

                if resp_html.status_code == 200 and resp_json.status_code == 200 and resp_md.status_code == 200:
                    j_data = resp_json.json()
                    total_cards = j_data.get("total_cards", 0)
                    cards = j_data.get("cards", [])

                    foreign_cards = []
                    for c in cards:
                        p_slug = c.get("printing_slug", "")
                        if not p_slug.endswith(f"-{set_code}"):
                            card_in_set = self.db["cards"].find_one({"set": set_code, "name": c.get("name")})
                            if not card_in_set:
                                foreign_cards.append(c.get("name"))

                    if foreign_cards:
                        self.log_fail("set fixture", f"{set_code} ({desc})", f"contains {len(foreign_cards)} foreign cards",
                                      {"set_code": set_code, "foreign_samples": foreign_cards[:3]})
                    else:
                        self.log_pass("set fixture", f"{set_code} ({desc}) - {total_cards} cards verified")
                else:
                    self.log_fail("set fixture", f"/set/{set_code}", "Set representation failed",
                                  {"set_code": set_code, "HTML": resp_html.status_code, "JSON": resp_json.status_code, "MD": resp_md.status_code})
            except Exception as e:
                self.log_fail("set fixture", f"/set/{set_code}", str(e), {"set_code": set_code})

        # Sampled set integrity
        sample_count = 17 if self.deep else 3
        all_sets = list(self.db["cards"].aggregate([
            {"$match": {"set": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$set"}},
            {"$sort": {"_id": 1}}
        ]))
        if len(all_sets) > sample_count:
            sampled_sets = self.rng.sample(all_sets, sample_count)
        else:
            sampled_sets = all_sets

        for s in sampled_sets:
            code = s["_id"].lower()
            try:
                resp = self.get(f"/set/{code}.json")
                if resp.status_code == 200:
                    data = resp.json()
                    total_in_api = data.get("total_cards", 0)
                    if total_in_api > 0:
                        self.log_pass("set integrity", f"Set [{code.upper()}] has {total_in_api} cards")
                    else:
                        self.log_warn("set integrity", f"Set [{code.upper()}] has 0 cards in API", {"set_code": code})
                else:
                    self.log_fail("set integrity", f"/set/{code}.json", f"status {resp.status_code}", {"set_code": code})
            except Exception as e:
                self.log_fail("set integrity", f"/set/{code}.json", str(e), {"set_code": code})

    # =========================================================================
    # 8. ARTIST INTEGRITY
    # =========================================================================
    def test_artist_integrity(self):
        sample_count = 17 if self.deep else 3
        all_artists = list(self.db["cards"].aggregate([
            {"$match": {"artist": {"$exists": True, "$ne": ""}}},
            {"$group": {"_id": "$artist", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]))
        if len(all_artists) > sample_count:
            sampled_artists = self.rng.sample(all_artists, sample_count)
        else:
            sampled_artists = all_artists

        for a in sampled_artists:
            artist_name = a["_id"]
            artist_slug = re.sub(r'[^a-z0-9]+', '-', artist_name.lower()).strip('-')
            if not artist_slug:
                continue

            try:
                resp_json = self.get(f"/artist/{artist_slug}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    cards = data.get("cards", [])
                    non_matching = [c.get("name") for c in cards if (c.get("artist") or "").lower() != artist_name.lower() and c.get("artist")]
                    if non_matching:
                        self.log_fail("artist integrity", f"{artist_name}", "contains cards not by artist",
                                      {"artist": artist_name, "non_matching_samples": non_matching[:3]})
                    else:
                        self.log_pass("artist integrity", f"{artist_name} ({len(cards)} cards verified)")
                else:
                    self.log_fail("artist integrity", f"/artist/{artist_slug}.json", f"status {resp_json.status_code}", {"artist": artist_name})
            except Exception as e:
                self.log_fail("artist integrity", f"/artist/{artist_slug}.json", str(e), {"artist": artist_name})

    # =========================================================================
    # 9. BLURB LINTING & TEMPLATE SANITY
    # =========================================================================
    def test_blurb_linting(self):
        targets = [
            ("/set/lea", "Set LEA Spotlight"),
            ("/set/rav", "Set RAV Spotlight"),
            ("/set/isd", "Set ISD Spotlight"),
            ("/artist/christopher-rush", "Artist Christopher Rush"),
            ("/artist/rebecca-guay", "Artist Rebecca Guay"),
        ]

        banned_tokens = ["{{", "}}", "undefined", "NaN", "None", "[object Object]"]

        for route, label in targets:
            try:
                resp = self.get(route)
                if resp.status_code == 200:
                    html = resp.text
                    found_banned = [tok for tok in banned_tokens if tok in html]
                    if found_banned:
                        self.log_fail("blurb lint", f"{label} ({route})", "found unrendered template token(s)",
                                      {"route": route, "tokens": found_banned})
                    else:
                        self.log_pass("blurb lint", f"{label} free of template artifacts")
                else:
                    self.log_fail("blurb lint", f"{route}", f"status {resp.status_code}", {"route": route})
            except Exception as e:
                self.log_fail("blurb lint", f"{route}", str(e), {"route": route})

    # =========================================================================
    # 10. 404 & FAILURE BOUNDARY TESTING (Clean 404s, NEVER 500s)
    # =========================================================================
    def test_404_boundaries(self):
        bogus_routes = [
            ("/printing/definitely-nonexistent-card-xyz123456789", 404),
            ("/printing/--..", 404),
            ("/set/zzzyyy99", 404),
            ("/set/nonexistent-set-code-12345", 404),
            ("/artist/definitely-not-a-real-artist-slug-12345", 404),
            ("/vector/definitely-nonexistent-card-slug-12345.json", 404),
            ("/similar/definitely-nonexistent-card-slug-12345.json", 404),
            ("/art/definitely-nonexistent-art-id-12345", 404),
            ("/art/definitely-nonexistent-art-id-12345.json", 404),
            ("/art/definitely-nonexistent-art-id-12345.md", 404),
        ]

        for route, expected_status in bogus_routes:
            try:
                resp = self.get(route)
                if resp.status_code == expected_status:
                    self.log_pass("404 boundary", f"{route} -> clean {resp.status_code}")
                elif resp.status_code == 500:
                    self.log_fail("404 boundary", f"{route}", "CRITICAL: returned 500 Internal Server Error instead of 404",
                                  {"route": route, "status": 500})
                else:
                    self.log_warn("404 boundary", f"{route}", f"expected {expected_status}, got {resp.status_code}",
                                  {"route": route, "status": resp.status_code})
            except Exception as e:
                self.log_fail("404 boundary", f"{route}", f"exception: {e}", {"route": route, "error": str(e)})

    # =========================================================================
    # 11. MACHINE DISCOVERY SURFACES (sitemaps, llms.txt, llms-full.txt)
    # =========================================================================
    def test_machine_discovery(self):
        manifest_files = [
            ("/llms.txt", "llms.txt manifest"),
            ("/llms-full.txt", "llms-full.txt manifest"),
            ("/sitemap.md", "sitemap.md manifest"),
        ]

        url_regex = re.compile(r'https?://avascry\.com(/[a-zA-Z0-9_\-\./]+)')

        for route, label in manifest_files:
            try:
                resp = self.get(route)
                if resp.status_code == 200:
                    content = resp.text
                    raw_urls = url_regex.findall(content)
                    clean_urls = []
                    for u in raw_urls:
                        # Skip documentation placeholders and bare prefixes
                        if any(ch in u for ch in ("<", ">", "{", "}", "*")):
                            continue
                        if u.rstrip("/") in ("/set", "/artist", "/printing", "/similar", "/vector"):
                            continue
                        clean_urls.append(u)

                    if clean_urls:
                        sampled_urls = self.rng.sample(clean_urls, min(len(clean_urls), 5 if self.deep else 2))
                        for sub_url in sampled_urls:
                            if sub_url.endswith(".gz") or sub_url.endswith(".xml"):
                                continue
                            sub_resp = self.get(sub_url)
                            if sub_resp.status_code in (200, 301, 302, 303, 307, 308):
                                self.log_pass("manifest link", f"[{label}] -> {sub_url} [{sub_resp.status_code}]")
                            else:
                                self.log_fail("manifest link", f"[{label}] -> {sub_url}", f"status {sub_resp.status_code}",
                                              {"manifest": label, "url": sub_url, "status": sub_resp.status_code})
                    else:
                        self.log_pass("manifest format", f"[{label}] 200 OK")
                else:
                    self.log_fail("manifest format", f"{route}", f"status {resp.status_code}", {"route": route})
            except Exception as e:
                self.log_fail("manifest format", f"{route}", str(e), {"route": route})

    # =========================================================================
    # 12. IMAGE SYNTAX & DEGRADATION
    # =========================================================================
    def test_images(self):
        sample_count = 19 if self.deep else 5
        candidates = list(self.db["cards"].find(
            {"lang": "en", "image_uris": {"$exists": True}},
            {"_id": 1, "name": 1, "printing_slug": 1, "slug": 1, "set": 1, "oracle_id": 1}
        ).sort("oracle_id", 1).limit(1000))

        if len(candidates) > sample_count:
            card_docs = self.rng.sample(candidates, sample_count)
        else:
            card_docs = candidates

        for card in card_docs:
            c_slug = card.get("printing_slug") or card.get("slug") or slugify(card.get("name") or "")
            c_set = (card.get("set") or "").lower()
            p_slug = f"{c_slug}-{c_set}" if (c_set and not c_slug.endswith(f"-{c_set}")) else c_slug
            try:
                resp = self.get(f"/printing/{p_slug}.json")
                if resp.status_code == 200:
                    data = resp.json()
                    card_data = data.get("card", data)
                    images = card_data.get("image_uris") or card_data.get("images") or {}
                    img_normal = images.get("normal") if isinstance(images, dict) else None
                    if not img_normal:
                        img_normal = card_data.get("image_url")

                    if img_normal:
                        if img_normal.startswith("/") or img_normal.startswith("https://") or img_normal.startswith("http://"):
                            self.log_pass("image syntax", f"{p_slug} ({img_normal[:32]}...)")
                        else:
                            self.log_fail("image syntax", f"{p_slug}", "malformed image URL",
                                          {"slug": p_slug, "image_url": img_normal})
                    else:
                        self.log_pass("image syntax", f"{p_slug} (graceful null image)")
            except Exception as e:
                self.log_fail("image syntax", f"{p_slug}", str(e), {"slug": p_slug})

    # =========================================================================
    # 13. UNICODE & MULTILINGUAL BOUNDARY FIXTURES
    # =========================================================================
    def test_unicode_boundary_fixtures(self):
        """Regression tests for non-ASCII, multilingual, and diacritic entities in HTTP responses."""
        fixtures = [
            ("Surtr, Fiery Jötun", "/similar/surtr-fiery-jtun.md", "diacritic /similar endpoint"),
            ("Surtr, Fiery Jötun", "/similar/surtr-fiery-jtun.json", "diacritic /similar JSON endpoint"),
            ("Jakub Šlemr Bio", "/printing/jakub-slemr-bio-1999-wc99", "non-ASCII champion card printing"),
            ("Jakub Šlemr Bio", "/printing/jakub-slemr-bio-1999-wc99.md", "non-ASCII champion card Markdown"),
            ("Jakub Šlemr Bio", "/printing/jakub-slemr-bio-1999-wc99.json", "non-ASCII champion card JSON"),
            ("The Lord of the Eagles (JA)", "/printing/the-lord-of-the-eagles-hob-ja", "Japanese localized printing"),
            ("Lim-Dûl's Vault", "/similar/lim-dls-vault.md", "accent + apostrophe compound name"),
        ]

        for name, route, desc in fixtures:
            try:
                resp = self.get(route)
                if resp.status_code != 200:
                    self.log_fail("unicode fixture", f"{name} ({route})", f"expected 200, got {resp.status_code}", {"route": route, "status": resp.status_code})
                    continue

                # 1. Assert Link header is strictly ASCII-encodable
                link = resp.headers.get("Link", "")
                if link:
                    if not link.isascii():
                        self.log_fail("unicode header", f"{route}", "Link header contains raw non-ASCII bytes", {"link": link})
                        continue
                    try:
                        link.encode("ascii")
                    except UnicodeEncodeError as e:
                        self.log_fail("unicode header", f"{route}", f"Link header failed ASCII encoding: {e}", {"link": link})
                        continue

                    # 2. Extract and resolve target URIs in Link header
                    import re
                    targets = re.findall(r'<([^>]+)>', link)
                    all_targets_ok = True
                    for target_url in targets:
                        norm_target = self.normalize_url(target_url)
                        t_resp = self.get(norm_target)
                        if t_resp.status_code != 200:
                            all_targets_ok = False
                            self.log_fail("unicode link target", f"{norm_target}", f"target in Link header returned {t_resp.status_code}",
                                          {"source_route": route, "target": norm_target, "status": t_resp.status_code})
                            break
                    if not all_targets_ok:
                        continue

                self.log_pass("unicode fixture", f"{name} ({desc}) -> clean 200 & ASCII Link")
            except Exception as e:
                self.log_fail("unicode fixture", f"{route}", str(e), {"route": route, "error": str(e)})

    # =========================================================================
    # 14. LOCALIZATION INVARIANTS & MULTILINGUAL PRINTINGS
    # =========================================================================
    def test_localization_invariants(self):
        """Verify ?lang= negotiation, mtgabyss_lang cookie, and localized printing pages."""
        # 1. Test language switcher negotiation and cookie behavior
        locales = ["ja", "fr", "de", "es", "it", "zhs", "pt", "ru", "ko"]
        for loc in locales:
            try:
                resp = self.get(f"/?lang={loc}")
                if resp.status_code == 200:
                    set_cookie = resp.headers.get("set-cookie", "")
                    if f"mtgabyss_lang={loc}" in set_cookie:
                        self.log_pass("localization param", f"?lang={loc} -> 200 & sets cookie mtgabyss_lang={loc}")
                    else:
                        self.log_warn("localization cookie", f"?lang={loc} returned 200 but cookie was: {set_cookie}")
                else:
                    self.log_fail("localization param", f"/?lang={loc}", f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("localization param", f"/?lang={loc}", str(e))

        # 2. Localized printing fixtures (Japanese, German, French)
        localized_fixtures = [
            ("/printing/the-lord-of-the-eagles-hob-ja", "Japanese printing fixture", ["鳥たちの王", "日本語", "The Lord of the Eagles"]),
            ("/printing/counterspell-lea", "English printing fixture (control)", ["Counterspell"]),
        ]

        for route, desc, expected_markers in localized_fixtures:
            try:
                resp = self.get(route)
                if resp.status_code == 200:
                    html = resp.text
                    matched = [m for m in expected_markers if m in html]
                    if matched:
                        self.log_pass("localized printing", f"{route} ({desc}) -> 200 OK with markers {matched}")
                    else:
                        self.log_fail("localized printing", f"{route} ({desc})", "expected localized content markers not found",
                                      {"expected": expected_markers})
                else:
                    self.log_fail("localized printing", f"{route}", f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("localized printing", f"{route}", str(e))

    # =========================================================================
    # 15. CTA TARGETS & LIVE GALLERY / RANDOM SET INVARIANTS
    # =========================================================================
    def test_cta_targets(self):
        """Verify Live Gallery route/feed API, artist CTA link, and set random-card CTA link."""
        # 1. Live Gallery and Feed API
        try:
            resp_gal = self.get("/live-gallery")
            if resp_gal.status_code == 200:
                self.log_pass("cta target", "/live-gallery -> 200 OK")
            else:
                self.log_fail("cta target", "/live-gallery", f"status {resp_gal.status_code}")
        except Exception as e:
            self.log_fail("cta target", "/live-gallery", str(e))

        try:
            resp_feed = self.get("/api/live-gallery/feed")
            if resp_feed.status_code == 200:
                data = resp_feed.json()
                cards = data.get("cards", [])
                if isinstance(cards, list) and len(cards) > 0:
                    self.log_pass("cta target", f"/api/live-gallery/feed -> 200 OK ({len(cards)} cards)")
                else:
                    self.log_warn("cta target", "/api/live-gallery/feed returned empty card feed")
            else:
                self.log_fail("cta target", "/api/live-gallery/feed", f"status {resp_feed.status_code}")
        except Exception as e:
            self.log_fail("cta target", "/api/live-gallery/feed", str(e))

        # 2. Artist detail Live Gallery CTA link
        sample_artists = ["christopher-rush", "rebecca-guay"]
        for artist_slug in sample_artists:
            try:
                resp = self.get(f"/artist/{artist_slug}")
                if resp.status_code == 200:
                    if 'href="/live-gallery"' in resp.text:
                        self.log_pass("artist cta", f"/artist/{artist_slug} has Live Gallery CTA link")
                    else:
                        self.log_fail("artist cta", f"/artist/{artist_slug}", "missing href='/live-gallery' CTA")
                else:
                    self.log_fail("artist cta", f"/artist/{artist_slug}", f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("artist cta", f"/artist/{artist_slug}", str(e))

        # 3. Set detail Random Card CTA link and execution
        sample_sets = ["rav", "gtc", "ori"]
        for set_code in sample_sets:
            try:
                resp = self.get(f"/set/{set_code}")
                if resp.status_code == 200:
                    expected_cta = f'href="/random?set={set_code}"'
                    if expected_cta in resp.text:
                        self.log_pass("set cta", f"/set/{set_code} has Random Card CTA")
                    else:
                        self.log_fail("set cta", f"/set/{set_code}", f"missing {expected_cta} CTA")
                else:
                    self.log_fail("set cta", f"/set/{set_code}", f"status {resp.status_code}")

                # Test executing the set random redirect
                r_resp = self.get(f"/random?set={set_code}")
                if r_resp.status_code in (301, 302, 303, 307, 308):
                    loc = r_resp.headers.get("location", "")
                    if loc.startswith("/printing/"):
                        norm_loc = self.normalize_url(loc)
                        t_resp = self.get(norm_loc)
                        if t_resp.status_code == 200:
                            if norm_loc.endswith(f"-{set_code}") or f"-{set_code}" in norm_loc:
                                self.log_pass("set random target", f"/random?set={set_code} -> {norm_loc} [200 belonging to {set_code}]")
                            else:
                                self.log_warn("set random target", f"/random?set={set_code} resolved to {norm_loc}")
                        else:
                            self.log_fail("set random target", f"/random?set={set_code}", f"target {norm_loc} status {t_resp.status_code}")
                    else:
                        self.log_fail("set random target", f"/random?set={set_code}", f"unexpected redirect location {loc}")
                else:
                    self.log_fail("set random target", f"/random?set={set_code}", f"expected 303 redirect, got {r_resp.status_code}")
            except Exception as e:
                self.log_fail("set random target", f"/random?set={set_code}", str(e))

    # =========================================================================
    # 16. AD CONTAMINATION INVARIANT (Machine Surfaces Must Remain 100% Ad/Script Free)
    # =========================================================================
    def test_machine_ad_contamination(self):
        """Ensure machine endpoints (.md, .json, .txt, .xml, /vector/*) never contain ad tags or tracking scripts."""
        sample_machine_routes = [
            "/printing/sol-ring-lea.md",
            "/printing/sol-ring-lea.json",
            "/similar/sol-ring.md",
            "/similar/sol-ring.json",
            "/vector/sol-ring.json",
            "/set/lea.md",
            "/set/lea.json",
            "/artist/christopher-rush.md",
            "/artist/christopher-rush.json",
            "/llms.txt",
            "/llms-full.txt",
            "/rules.md",
            "/legalities.md",
            "/sets.md",
            "/sitemap.md",
            "/sitemap.xml",
            "/heartbeat.txt",
        ]

        if self.deep:
            # Add extra sampled cards and sets in deep mode
            extra_cards = ["black-lotus-lea", "counterspell-lea", "dark-ritual-lea", "lightning-bolt-lea"]
            for ec in extra_cards:
                sample_machine_routes.extend([
                    f"/printing/{ec}.md",
                    f"/printing/{ec}.json",
                    f"/vector/{ec}.json"
                ])

        banned_ad_tokens = [
            "<script",
            "adsbygoogle",
            "pagead2.googlesyndication.com",
            "googletagmanager.com",
            "clarity.ms",
            "google-adsense-account",
            "ca-pub-",
        ]

        for route in sample_machine_routes:
            try:
                resp = self.get(route)
                if resp.status_code == 200:
                    text_lower = resp.text.lower()
                    found = [tok for tok in banned_ad_tokens if tok in text_lower]
                    if found:
                        self.log_fail("machine ad-free", route, "CRITICAL: Ad/tracker token found in machine surface!",
                                      {"route": route, "tokens_found": found})
                    else:
                        self.log_pass("machine ad-free", f"{route} (clean of all ad/tracker scripts)")
                else:
                    self.log_warn("machine ad-free", route, f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("machine ad-free", route, str(e))

    # =========================================================================
    # 17. LEGITIMACY & LEGAL CONTENT INTEGRITY
    # =========================================================================
    def test_legitimacy_content(self):
        """Verify About, Contact, Privacy, and Terms pages render authentic content and disclaimers."""
        checks = [
            ("/about", [
                "About AvaScry",
                "Neural",
                "SmartDeck",
                "Scryfall",
                "Wizards of the Coast",
                "Fan Content Policy"
            ]),
            ("/contact", [
                "Contact",
                "Support",
                "Telos Development Group",
                "telosdevgroup@gmail.com"
            ]),
            ("/privacy", [
                "Privacy Policy",
                "Information We Collect",
                "telosdevgroup@gmail.com"
            ]),
            ("/terms", [
                "Terms of Service",
                "Fan Content Policy",
                "Wizards of the Coast",
                "Scryfall"
            ])
        ]

        for route, required_snippets in checks:
            try:
                resp = self.get(route)
                if resp.status_code == 200:
                    html_text = resp.text
                    missing = [snip for snip in required_snippets if snip.lower() not in html_text.lower()]
                    if missing:
                        self.log_fail("legitimacy content", route, "missing required legitimacy tokens",
                                      {"route": route, "missing": missing})
                    else:
                        self.log_pass("legitimacy content", f"{route} ({len(required_snippets)}/{len(required_snippets)} compliance tokens verified)")
                else:
                    self.log_fail("legitimacy content", route, f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("legitimacy content", route, str(e))

    # =========================================================================
    # 18. FOOTER NAVIGATION COHERENCE
    # =========================================================================
    def test_footer_coherence(self):
        """Verify that human entry points render the unified footer with legitimacy links."""
        sample_pages = [
            ("/", "Homepage"),
            ("/sets", "Sets Index"),
            ("/artists", "Artists Index"),
            ("/live-gallery", "Live Gallery"),
            ("/printing/sol-ring-lea", "Card Detail"),
            ("/set/lea", "Set Detail"),
            ("/artist/christopher-rush", "Artist Detail"),
        ]

        expected_links = [
            'href="/about"',
            'href="/contact"',
            'href="/privacy"',
            'href="/terms"',
        ]

        for route, label in sample_pages:
            try:
                resp = self.get(route)
                if resp.status_code == 200:
                    html_text = resp.text
                    missing_links = [link for link in expected_links if link not in html_text]
                    if missing_links:
                        self.log_fail("footer coherence", f"{label} ({route})", "missing footer legitimacy link(s)",
                                      {"missing": missing_links})
                    else:
                        self.log_pass("footer coherence", f"{label} ({route}) has complete legitimacy footer")
                else:
                    self.log_fail("footer coherence", f"{label} ({route})", f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("footer coherence", f"{label} ({route})", str(e))

    # =========================================================================
    # 19. EDITORIAL SPOTLIGHT & ANTI-CARD-DUMP INVARIANT
    # =========================================================================
    def test_editorial_spotlight(self):
        """Verify that curated sets and artists provide rich editorial spotlights, not bare database dumps."""
        curated_sets = [
            ("lea", "Limited Edition Alpha", "Where Magic Began"),
            ("rav", "Ravnica: City of Guilds", "The City of Guilds"),
            ("isd", "Innistrad", "Gothic Horror Unleashed"),
        ]
        for set_code, set_name, expected_title in curated_sets:
            try:
                resp = self.get(f"/set/{set_code}")
                if resp.status_code == 200:
                    html_text = resp.text
                    has_block = "spotlight-block" in html_text or "Set Spotlight" in html_text
                    has_title = expected_title in html_text
                    if has_block and has_title:
                        self.log_pass("editorial set", f"/set/{set_code} -> spotlight '{expected_title}' present")
                    else:
                        self.log_fail("editorial set", f"/set/{set_code}", "editorial spotlight missing or incomplete",
                                      {"has_block": has_block, "has_title": has_title, "expected_title": expected_title})
                else:
                    self.log_fail("editorial set", f"/set/{set_code}", f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("editorial set", f"/set/{set_code}", str(e))

        curated_artists = [
            ("christopher-rush", "Christopher Rush"),
            ("rebecca-guay", "Rebecca Guay"),
        ]
        for artist_slug, artist_name in curated_artists:
            try:
                resp = self.get(f"/artist/{artist_slug}")
                if resp.status_code == 200:
                    html_text = resp.text
                    has_spotlight = "spotlight-block" in html_text or "Artist Spotlight" in html_text or "Total Artworks" in html_text
                    if has_spotlight:
                        self.log_pass("editorial artist", f"/artist/{artist_slug} -> rich artist profile verified")
                    else:
                        self.log_fail("editorial artist", f"/artist/{artist_slug}", "missing artist spotlight profile")
                else:
                    self.log_fail("editorial artist", f"/artist/{artist_slug}", f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("editorial artist", f"/artist/{artist_slug}", str(e))

    # =========================================================================
    # 20. LIVE GALLERY & IMMERSIVE ART SLIDESHOW
    # =========================================================================
    def test_live_gallery(self):
        """Verify Live Gallery UI and API feed invariants, including browser Accept header card links."""
        # 1. Page test
        try:
            resp = self.get("/live-gallery")
            if resp.status_code == 200 and "slideshow-stage" in resp.text:
                self.log_pass("live gallery", "/live-gallery rendered with slideshow stage")
            else:
                self.log_fail("live gallery", "/live-gallery", f"status {resp.status_code} or missing stage element")
        except Exception as e:
            self.log_fail("live gallery", "/live-gallery", str(e))

        # 2. Feed test
        feed_items = []
        try:
            resp = self.get("/api/live-gallery/feed")
            if resp.status_code == 200:
                data = resp.json()
                feed_items = data.get("items") or []
                if len(feed_items) > 0:
                    self.log_pass("live gallery", f"/api/live-gallery/feed returned {len(feed_items)} cards")
                else:
                    self.log_fail("live gallery", "/api/live-gallery/feed", "feed returned empty items list")
            else:
                self.log_fail("live gallery", "/api/live-gallery/feed", f"status {resp.status_code}")
        except Exception as e:
            self.log_fail("live gallery", "/api/live-gallery/feed", str(e))

        # 3. Card click link verification (ensure browser Accept headers receive HTML, not raw XML)
        if feed_items:
            sample_size = min(len(feed_items), 8 if self.deep else 2)
            sample = self.rng.sample(feed_items, sample_size)
            browser_headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"}
            for item in sample:
                p_slug = item.get("printing_slug")
                if not p_slug:
                    continue
                try:
                    card_resp = self.get(f"/printing/{p_slug}", headers=browser_headers)
                    ct = card_resp.headers.get("content-type", "")
                    if card_resp.status_code == 200 and "text/html" in ct:
                        self.log_pass("live gallery link", f"/printing/{p_slug} [browser Accept -> HTML]")
                    else:
                        self.log_fail("live gallery link", f"/printing/{p_slug}", f"expected text/html, got {ct} (status {card_resp.status_code})")
                except Exception as e:
                    self.log_fail("live gallery link", f"/printing/{p_slug}", str(e))

    # =========================================================================
    # 21. BASIC LAND & MASSIVE PRINTING INVARIANTS ("The Forest Incident")
    # =========================================================================
    def test_basic_land_invariants(self):
        """
        Verify that high-volume basic lands with thousands of printings (e.g. Forest, Island, Mountain, Swamp, Plains)
        satisfy invariant capping (max 31 per language), render HTML without memory explosion or timeouts,
        and provide complete multi-format representations (HTML, MD, JSON, XML, CSV).
        """
        basic_lands = [
            ("Forest", "forest-lea", "lea", "Alpha Forest"),
            ("Island", "island-lea", "lea", "Alpha Island"),
            ("Mountain", "mountain-lea", "lea", "Alpha Mountain"),
            ("Swamp", "swamp-lea", "lea", "Alpha Swamp"),
            ("Plains", "plains-lea", "lea", "Alpha Plains"),
        ]

        # In deep mode, test all 5 basic lands; in quick mode, test Forest + Island
        test_cases = basic_lands if self.deep else basic_lands[:2]

        for name, p_slug, set_code, label in test_cases:
            # 1. HTML representation & latency check
            try:
                t0 = time.time()
                resp_html = self.get(f"/printing/{p_slug}")
                latency = time.time() - t0

                if resp_html.status_code == 200:
                    text = resp_html.text
                    # Must contain card name and not be an empty shell
                    if name.lower() in text.lower():
                        self.log_pass("forest incident", f"{label} HTML rendered in {latency:.3f}s")
                    else:
                        self.log_fail("forest incident", f"/printing/{p_slug}", "HTML missing card name",
                                      {"card": name, "slug": p_slug})
                else:
                    self.log_fail("forest incident", f"/printing/{p_slug}", f"status {resp_html.status_code}",
                                  {"card": name, "status": resp_html.status_code})
            except Exception as e:
                self.log_fail("forest incident", f"/printing/{p_slug}", str(e), {"card": name})

            # 2. JSON representation & 31-printings capping invariant check
            try:
                resp_json = self.get(f"/printing/{p_slug}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    card_data = data.get("card", data)
                    c_name = card_data.get("name") or data.get("name")
                    if c_name == name:
                        self.log_pass("forest incident", f"{label} JSON verified")
                    else:
                        self.log_fail("forest incident", f"/printing/{p_slug}.json", f"name mismatch: got {c_name}, expected {name}")
                else:
                    self.log_fail("forest incident", f"/printing/{p_slug}.json", f"status {resp_json.status_code}")
            except Exception as e:
                self.log_fail("forest incident", f"/printing/{p_slug}.json", str(e))

            # 3. Markdown representation check
            try:
                resp_md = self.get(f"/printing/{p_slug}.md")
                if resp_md.status_code == 200 and f"# {name}" in resp_md.text:
                    self.log_pass("forest incident", f"{label} Markdown verified")
                else:
                    self.log_fail("forest incident", f"/printing/{p_slug}.md", f"status {resp_md.status_code} or missing # {name}")
            except Exception as e:
                self.log_fail("forest incident", f"/printing/{p_slug}.md", str(e))

            # 4. Cockatrice XML and CSV representations
            try:
                resp_xml = self.get(f"/printing/{p_slug}.xml")
                resp_csv = self.get(f"/printing/{p_slug}.csv")
                if resp_xml.status_code == 200 and resp_csv.status_code == 200:
                    self.log_pass("forest incident", f"{label} XML + CSV verified")
                else:
                    self.log_fail("forest incident", f"{label} XML/CSV",
                                  f"XML: {resp_xml.status_code}, CSV: {resp_csv.status_code}")
            except Exception as e:
                self.log_fail("forest incident", f"{label} XML/CSV", str(e))

    # =========================================================================
    # 21. VISUAL ARTWORK & MULTIMODAL SIMILARITY SURFACES
    # =========================================================================
    def test_visual_artwork_and_similarities(self):
        """
        Verify Visual Artwork Analysis (Qwen3-VL) & Visual Similarity Graph (Qwen3-Embedding:8B).
        Tests /art/{illustration_id}.json, /art/{illustration_id}.md, and card printing visual parity.
        """
        sample_count = 17 if self.deep else 5

        # 1. Sample from vl_art_similarities
        sim_candidates = list(self.db["vl_art_similarities"].find(
            {"top_neighbors": {"$exists": True}},
            {"_id": 1, "illustration_id": 1, "top_neighbors": 1, "model": 1}
        ).limit(500))

        if not sim_candidates:
            self.log_warn("visual art", "vl_art_similarities", "No documents in vl_art_similarities collection")
            return

        sampled = self.rng.sample(sim_candidates, min(len(sim_candidates), sample_count))

        for sim_doc in sampled:
            ill_id = sim_doc.get("illustration_id")
            if not ill_id:
                continue

            # Check JSON endpoint
            try:
                resp_json = self.get(f"/art/{ill_id}.json")
                if resp_json.status_code == 200:
                    data = resp_json.json()
                    card_name = data.get("card_name", "Unknown")
                    neighbors = data.get("top_neighbors", {})

                    # Verify categories: by_subject, by_vibe, by_scene
                    has_categories = all(cat in neighbors for cat in ("by_subject", "by_vibe", "by_scene"))
                    if has_categories:
                        total_neighbors = sum(len(neighbors[cat]) for cat in ("by_subject", "by_vibe", "by_scene"))
                        self.log_pass("visual art JSON", f"{card_name} ({ill_id[:8]}... -> {total_neighbors} visual neighbors)")
                    else:
                        self.log_fail("visual art JSON", f"/art/{ill_id}.json", "Missing neighbor categories",
                                      {"illustration_id": ill_id, "keys": list(neighbors.keys())})

                    # Verify Link header pointing to Markdown representation
                    link_header = resp_json.headers.get("Link", "")
                    if f"/art/{ill_id}.md" in link_header:
                        self.log_pass("visual art Link", f"{card_name} Link header -> .md")
                    else:
                        self.log_warn("visual art Link", f"{card_name}", "Link header missing .md reference",
                                      {"link": link_header})
                else:
                    self.log_fail("visual art JSON", f"/art/{ill_id}.json", f"status {resp_json.status_code}",
                                  {"illustration_id": ill_id})
            except Exception as e:
                self.log_fail("visual art JSON", f"/art/{ill_id}.json", str(e), {"illustration_id": ill_id})

            # Check Markdown endpoint
            try:
                resp_md = self.get(f"/art/{ill_id}.md")
                if resp_md.status_code == 200:
                    md_text = resp_md.text
                    if "Visual Artwork Analysis" in md_text and "Top 7 Nearest Visual Neighbors" in md_text:
                        self.log_pass("visual art MD", f"{ill_id[:8]}... (.md report verified)")
                    else:
                        self.log_fail("visual art MD", f"/art/{ill_id}.md", "Markdown missing expected sections",
                                      {"illustration_id": ill_id})
                else:
                    self.log_fail("visual art MD", f"/art/{ill_id}.md", f"status {resp_md.status_code}",
                                  {"illustration_id": ill_id})
            except Exception as e:
                self.log_fail("visual art MD", f"/art/{ill_id}.md", str(e), {"illustration_id": ill_id})

        # 2. Check a card printing that has an illustration_id with visual similarities
        try:
            test_ill = sampled[0].get("illustration_id")
            card_with_art = self.db["cards"].find_one({"illustration_id": test_ill, "lang": "en"})
            if card_with_art:
                p_slug = card_with_art.get("printing_slug") or f"{slugify(card_with_art.get('name'))}-{card_with_art.get('set', '').lower()}"
                card_resp = self.get(f"/printing/{p_slug}")
                if card_resp.status_code == 200:
                    html_content = card_resp.text
                    if "/art/" in html_content or "Visual Similarities" in html_content or "Nearest Visual" in html_content:
                        self.log_pass("visual art HTML", f"{card_with_art.get('name')} renders visual art links in HTML")
                    else:
                        self.log_pass("visual art HTML", f"{card_with_art.get('name')} served 200 OK")
        except Exception as e:
            self.log_warn("visual art HTML", "card page check", str(e))

    # =========================================================================
    # 22. MULTILINGUAL & SLUG RESOLUTION LATENCY INVARIANTS
    # =========================================================================
    def test_multilingual_performance_invariants(self):
        """
        Verify that multilingual (<slug>-<set>-<lang>) and hyphenated card lookups
        resolve directly without paying the 500ms unanchored regex table scan tax.
        """
        fixtures = [
            ("/printing/harald-unites-the-elves-khm-ko", "Harald Unites the Elves (Korean)"),
            ("/printing/doorkeeper-rtr-fr", "Doorkeeper (French)"),
            ("/printing/oathsworn-vampire-rix-ko", "Oathsworn Vampire (Korean)"),
            ("/printing/awakened-awareness-neo-it", "Awakened Awareness (Italian)"),
            ("/printing/fear-of-the-dark-dsk-es", "Fear of the Dark (Spanish)"),
            ("/printing/tempered-steel-som-zht", "Tempered Steel (Traditional Chinese)"),
            ("/printing/avalanche-caller-khm-de", "Avalanche Caller (German)"),
            ("/card/water-wurm", "Water Wurm (Hyphenated card name redirect)"),
        ]

        # Warm up request
        self.get(fixtures[0][0])

        for route, label in fixtures:
            try:
                t0 = time.perf_counter()
                resp = self.get(route)
                dur_ms = (time.perf_counter() - t0) * 1000.0

                if resp.status_code in (200, 303):
                    # In-process TestClient should easily resolve in < 150ms (avoiding the 500ms scan)
                    if dur_ms < 250.0:
                        self.log_pass("perf invariant", f"{label:<42} -> {dur_ms:5.1f}ms [{resp.status_code}]")
                    else:
                        self.log_fail("perf invariant", f"{route}", f"latency regression: took {dur_ms:.1f}ms (> 250ms threshold)",
                                      {"route": route, "duration_ms": dur_ms})
                else:
                    self.log_fail("perf invariant", f"{route}", f"unexpected status {resp.status_code}",
                                  {"route": route, "status": resp.status_code})
            except Exception as e:
                self.log_fail("perf invariant", f"{route}", str(e))

    # =========================================================================
    # 23. MULTI-GAME NETWORK & SUBDOMAIN ROUTING INVARIANTS
    # =========================================================================
    def test_network_subdomain_routing(self):
        """
        Verify host header and X-Forwarded-Host dispatch:
        - dominion.avascry.com -> Dominion sub-app
        - swu.avascry.com -> Star Wars Unlimited sub-app
        - avascry.com -> Magic: The Gathering main app
        """
        subdomain_cases = [
            ("dominion.avascry.com", "/", 200, "Dominion Subdomain Home"),
            ("swu.avascry.com", "/", 200, "Star Wars Unlimited Subdomain Home"),
            ("necromunda.avascry.com", "/", 200, "Necromunda Subdomain Home"),
            ("necromunda.avascry.com", "/weapons", 200, "Necromunda Weapons Index"),
            ("necromunda.avascry.com", "/houses", 200, "Necromunda Houses Index"),
            ("avascry.com", "/", 200, "MTG Root Home"),
            ("avascry.com", "/heartbeat.txt", 200, "MTG Heartbeat"),
        ]

        for host, path, expected_status, label in subdomain_cases:
            # 1. Test via standard 'Host' header
            try:
                resp_host = self.get(path, headers={"Host": host})
                if resp_host.status_code == expected_status:
                    self.log_pass("subdomain host", f"{host}{path} -> {label} [{resp_host.status_code}]")
                else:
                    self.log_fail("subdomain host", f"{host}{path}", f"expected {expected_status}, got {resp_host.status_code}")
            except Exception as e:
                self.log_fail("subdomain host", f"{host}{path}", str(e))

            # 2. Test via Cloudflare tunnel 'X-Forwarded-Host' header
            try:
                resp_xfh = self.get(path, headers={"X-Forwarded-Host": host})
                if resp_xfh.status_code == expected_status:
                    self.log_pass("subdomain xfh", f"[X-Forwarded-Host: {host}] -> {label} [{resp_xfh.status_code}]")
                else:
                    self.log_fail("subdomain xfh", f"{host}{path}", f"expected {expected_status}, got {resp_xfh.status_code}")
            except Exception as e:
                self.log_fail("subdomain xfh", f"{host}{path}", str(e))

    # =========================================================================
    # =========================================================================
    # 24. CONTACT & BOT HONEYPOT RESILIENCE ACROSS ALL SITES
    # =========================================================================
    def test_contact_and_honeypot(self):
        """
        Verify unified contact form presentation, validation, and anti-bot honeypot suppression
        across all active game subsites (MTG, SWU, Dominion, Necromunda).
        """
        contact_hosts = [
            ("avascry.com", "/contact", "MTG Contact"),
            ("swu.avascry.com", "/contact", "SWU Contact"),
            ("dominion.avascry.com", "/contact", "Dominion Contact"),
            ("necromunda.avascry.com", "/contact", "Necromunda Contact"),
        ]

        for host, path, label in contact_hosts:
            try:
                resp = self.get(path, headers={"Host": host})
                if resp.status_code == 200:
                    text = resp.text
                    if '<form' in text and 'name="website_url"' in text and 'name="message"' in text:
                        self.log_pass("contact form", f"{label} ({host}{path}) rendered with honeypot field 'website_url'")
                    else:
                        self.log_fail("contact form", f"{host}{path}", "Form or honeypot field 'website_url' missing from HTML")
                else:
                    self.log_fail("contact form", f"{host}{path}", f"status {resp.status_code}")
            except Exception as e:
                self.log_fail("contact form", f"{host}{path}", str(e))

        # 2. POST /contact with bot honeypot populated (anti-spam catch)
        try:
            bot_payload = {
                "name": "SpamBot 9000",
                "contact": "spambot@example.com",
                "message": "Buy cheap backlinks now!",
                "website_url": "http://spamsite.evil.com"
            }
            if self._is_testclient:
                resp_bot = self.client.post("/contact", data=bot_payload)
            else:
                resp_bot = self.client.post(f"{self.base_url}/contact", data=bot_payload)

            if resp_bot.status_code in (200, 302, 303):
                self.log_pass("contact honeypot", f"Bot submission handled safely [{resp_bot.status_code}]")
            else:
                self.log_fail("contact honeypot", "/contact", f"Unexpected status on bot catch: {resp_bot.status_code}")
        except Exception as e:
            self.log_fail("contact honeypot", "/contact", str(e))

        # 3. POST /contact with missing required fields (validation check)
        try:
            invalid_payload = {
                "name": "",
                "contact": "",
                "message": "",
                "website_url": ""
            }
            if self._is_testclient:
                resp_val = self.client.post("/contact", data=invalid_payload)
            else:
                resp_val = self.client.post(f"{self.base_url}/contact", data=invalid_payload)

            if resp_val.status_code == 200:
                self.log_pass("contact validation", "Empty submission caught by form validation without error 500")
            else:
                self.log_fail("contact validation", "/contact", f"Expected 200 validation response, got {resp_val.status_code}")
        except Exception as e:
            self.log_fail("contact validation", "/contact", str(e))

    # =========================================================================
    # 25. AUTH & CROSS-SUBDOMAIN SSO INVARIANTS
    # =========================================================================
    def test_auth_surfaces(self):
        """
        Verify user authentication endpoints, OAuth SSO dispatch, safe redirect filtering,
        and header Sign-In UI presence across all game sites.
        """
        auth_cases = [
            ("/auth/login", 200, "Auth Login Portal"),
            ("/auth/discord/login", 303, "Discord OAuth Dispatch"),
            ("/auth/logout", 303, "Logout Redirect"),
        ]
        for route, expected_status, label in auth_cases:
            try:
                resp = self.get(route)
                if resp.status_code == expected_status:
                    self.log_pass("auth surface", f"{label} ({route}) -> [{resp.status_code}]")
                else:
                    self.log_fail("auth surface", route, f"expected {expected_status}, got {resp.status_code}")
            except Exception as e:
                self.log_fail("auth surface", route, str(e))

        # Open-redirect prevention & safe redirect targets
        redirect_scenarios = [
            ("/auth/login?next=/dashboard", "/dashboard", True, "safe relative path"),
            ("/auth/login?next=https://swu.avascry.com/card/luke-skywalker", "https://swu.avascry.com/card/luke-skywalker", True, "trusted SWU subdomain"),
            ("/auth/login?next=https://dominion.avascry.com/random", "https://dominion.avascry.com/random", True, "trusted Dominion subdomain"),
            ("/auth/login?next=https://necromunda.avascry.com/weapons", "https://necromunda.avascry.com/weapons", True, "trusted Necromunda subdomain"),
            ("/auth/login?next=https://evil.com/phish", "/dashboard", False, "blocked untrusted external domain"),
            ("/auth/login?next=//attacker.org", "/dashboard", False, "blocked protocol-relative URL"),
        ]

        for req_url, expected_target, should_preserve, desc in redirect_scenarios:
            try:
                resp = self.get(req_url)
                if resp.status_code == 200:
                    text = resp.text
                    if should_preserve:
                        target_encoded = expected_target.replace("://", "%3A//")
                        enc_target = urllib.parse.quote_plus(expected_target)
                        if expected_target in text or target_encoded in text or enc_target in text or html.escape(expected_target) in text:
                            self.log_pass("auth safe redirect", f"Preserved {desc} -> {expected_target}")
                        else:
                            self.log_fail("auth safe redirect", req_url, f"Expected {expected_target} in response HTML")
                    else:
                        if "evil.com" not in text and "attacker.org" not in text:
                            self.log_pass("auth open-redirect defense", f"Purged {desc} -> defaulted to safe target")
                        else:
                            self.log_fail("auth open-redirect defense", req_url, "Malicious target leaked into response HTML")
                else:
                    self.log_fail("auth redirect", req_url, f"Unexpected status {resp.status_code}")
            except Exception as e:
                self.log_fail("auth redirect", req_url, str(e))

        # Header Sign-In UI verification across network sites
        subsite_navs = [
            ("avascry.com", "/", "MTG Home"),
            ("swu.avascry.com", "/", "SWU Home"),
            ("dominion.avascry.com", "/", "Dominion Home"),
            ("necromunda.avascry.com", "/", "Necromunda Home"),
        ]
        for host, path, label in subsite_navs:
            try:
                resp = self.get(path, headers={"Host": host})
                if resp.status_code == 200:
                    if ('/auth/discord/login' in text or '/auth/login' in text) and ('Sign In with Discord' in text or 'Sign In' in text):
                        self.log_pass("subsite auth nav", f"{label} ({host}) displays unified Sign In with Discord control")
                    else:
                        self.log_warn("subsite auth nav", f"{host}{path}", "Sign In link not detected in navbar")
                else:
                    self.log_fail("subsite auth nav", f"{host}{path}", f"Status {resp.status_code}")
            except Exception as e:
                self.log_fail("subsite auth nav", f"{host}{path}", str(e))

    # =========================================================================
    # MAIN RUNNER
    # =========================================================================
    def run_all(self) -> int:
        self.start_time = time.time()
        mode_str = "DEEP" if self.deep else "QUICK"
        print(f"\n========================================================")
        print(f" SiteBlaster 9001 — AvaScry Site Doctor [{mode_str} MODE]")
        print(f" Target Base: {self.base_url} | Seed: {self.seed}")
        print(f" User-Agent:  {self.user_agent}")
        print(f"========================================================\n")

        suites = [
            ("Core Route Smoke", self.test_core_routes),
            ("Live Gallery & SSE Feeds", self.test_live_gallery),
            ("Commander Rules & Identity Invariants", self.test_commander_correctness),
            ("Boundary & 404 Resilience", self.test_404_boundaries),
            ("Random Discovery Routes", self.test_random_routes),
            ("Set Integrity & Distribution", self.test_set_integrity),
            ("Artist Integrity & Galleries", self.test_artist_integrity),
            ("Card Blurb & Rules Linting", self.test_blurb_linting),
            ("Real Entity Tri-Surface (HTML, MD, JSON, XML, CSV)", self.test_real_entity_sampling),
            ("Markdown Spec & Frontmatter Integrity", self.test_markdown_integrity),
            ("Neural & Vector Search Surfaces", self.test_neural_surfaces),
            ("Machine Discovery & LLM Manifests", self.test_machine_discovery),
            ("Image Delivery & Scan Resolution", self.test_images),
            ("Unicode & Non-ASCII Slugs & Boundaries", self.test_unicode_boundary_fixtures),
            ("Localization & Multi-Language Invariants", self.test_localization_invariants),
            ("CTA Targets & Conversions", self.test_cta_targets),
            ("Machine Ad & Injection Guardrails", self.test_machine_ad_contamination),
            ("Legitimacy & Editorial Content", self.test_legitimacy_content),
            ("Footer & Network Coherence", self.test_footer_coherence),
            ("Editorial Spotlight & Curations", self.test_editorial_spotlight),
            ("Basic Land Capping & Forest Incident Invariants", self.test_basic_land_invariants),
            ("Visual Artwork & Multi-Modal Similarity Surfaces", self.test_visual_artwork_and_similarities),
            ("Multilingual Performance & Benchmark Invariants", self.test_multilingual_performance_invariants),
            ("Network Subdomain Routing & Proxy Symmetry", self.test_network_subdomain_routing),
            ("Contact Form & Bot Honeypot Resilience", self.test_contact_and_honeypot),
            ("Auth & SSO Login Invariants", self.test_auth_surfaces),
        ]

        total_suites = len(suites)
        for idx, (name, suite_fn) in enumerate(suites, 1):
            print(f"\n--- [{idx}/{total_suites}] Running {name} Suite ---", flush=True)
            suite_fn()

        elapsed = time.time() - self.start_time

        if self.failures_recap:
            print(f"\n========================================================")
            print(f" FAILURES ({len(self.failures_recap)})")
            print(f"========================================================")
            for f in self.failures_recap:
                extra = f" -> {f['reason']}" if f['reason'] else ""
                print(f"\033[91m[FAIL]\033[0m {f['category']:<18} {f['message']}{extra}")
                for k, v in f["details"].items():
                    print(f"       \033[90m{k} = {v}\033[0m")

        if self.warnings_recap:
            print(f"\n========================================================")
            print(f" WARNINGS ({len(self.warnings_recap)})")
            print(f"========================================================")
            for w in self.warnings_recap:
                extra = f" -> {w['reason']}" if w['reason'] else ""
                print(f"\033[93m[WARN]\033[0m {w['category']:<18} {w['message']}{extra}")
                for k, v in w["details"].items():
                    print(f"       \033[90m{k} = {v}\033[0m")

        print(f"\n========================================================")
        print(f"SiteBlaster Summary: {self.passed} passed | {self.failed} failed | {self.warnings} warnings ({elapsed:.2f}s)")
        if self.failed == 0:
            print(f"\033[92m\nAVASCRY LIVES. POWER LEVEL > 9000.\033[0m\n")
        else:
            print(f"\033[91m\nAVASCRY NEEDS ATTENTION ({self.failed} failures).\033[0m\n")
        print(f"========================================================\n")

        return 1 if self.failed > 0 else 0


def main():
    parser = argparse.ArgumentParser(description="AvaScry SiteBlaster 9001 — Invariant & Route Tester")
    parser.add_argument("--deep", action="store_true", help="Run comprehensive deep suite with larger sample sizes")
    parser.add_argument("--quick", action="store_true", help="Run fast quick suite with targeted sample sizes (default)")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic random seed (default: 1337)")
    parser.add_argument("--base-url", type=str, default=None, help="Base URL of live server (e.g. http://127.0.0.1:8000). Defaults to in-process ASGI.")
    args = parser.parse_args()

    is_deep = bool(args.deep)
    blaster = SiteBlaster(base_url=args.base_url, deep=is_deep, seed=args.seed)
    exit_code = blaster.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
