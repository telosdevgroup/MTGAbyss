#!/usr/bin/env python3
"""
sync_citations_sitemap.py

Tiny standalone helper to:
1. Pull live content citations from http://127.0.0.1:8000/api/citations
2. Merge new unique AvaScry routes into public/sitemap-citations.xml with today's date
3. Optionally ping IndexNow for newly added URLs (--indexnow)

Usage:
    python sync_citations_sitemap.py [--dry-run] [--indexnow]
"""

import os
import sys
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

INDEXNOW_KEY = "b3901b0f58d0445bb8d15a9e334df58a"
HOST = "avascry.com"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SITEMAP_PATH = os.path.join(PROJECT_DIR, "public", "sitemap-citations.xml")
API_URL = "http://127.0.0.1:8000/api/citations"

def load_existing_sitemap():
    if not os.path.exists(SITEMAP_PATH):
        return {}
    try:
        tree = ET.parse(SITEMAP_PATH)
        root = tree.getroot()
        items = {}
        for url in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
            loc = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            lastmod = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
            if loc is not None and loc.text:
                items[loc.text.strip()] = lastmod.text.strip() if lastmod is not None else ""
        return items
    except Exception as e:
        print(f"Error parsing existing sitemap: {e}")
        return {}

def fetch_cited_routes():
    try:
        with urllib.request.urlopen(API_URL, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = data.get("items", [])
        avascry_routes = set()
        for item in items:
            if item.get("site") == "AvaScry":
                r = item.get("route", "").strip()
                if r and r.startswith("/") and not r.startswith("/?"):
                    avascry_routes.add(r)
        return avascry_routes
    except Exception as e:
        print(f"Could not reach {API_URL}: {e}")
        print("Ensure the log stream server is running on port 8000.")
        return set()

def submit_indexnow(urls):
    if not urls:
        return
    print(f"Submitting {len(urls)} URLs to IndexNow via Bing...")
    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{HOST}/{INDEXNOW_KEY}.txt",
        "urlList": urls
    }
    data = json.dumps(payload).encode("utf-8")
    
    # Try Bing primary endpoint first, with fallback to api.indexnow.org
    endpoints = [
        "https://www.bing.com/indexnow",
        "https://api.indexnow.org/indexnow"
    ]
    
    for endpoint in endpoints:
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"IndexNow [{endpoint}] Response: HTTP {resp.status} (Success)")
                return
        except urllib.error.HTTPError as e:
            print(f"IndexNow [{endpoint}] HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")
            return
        except Exception as e:
            print(f"IndexNow [{endpoint}] failed ({e}), trying fallback...")

def main():
    dry_run = "--dry-run" in sys.argv
    do_indexnow = "--indexnow" in sys.argv

    print(f"Reading existing citations sitemap from: {SITEMAP_PATH}")
    existing = load_existing_sitemap()
    print(f"Existing URLs in sitemap: {len(existing)}")

    cited_routes = fetch_cited_routes()
    print(f"Unique AvaScry cited routes in active log stream: {len(cited_routes)}")

    today = datetime.now().strftime("%Y-%m-%d")
    new_urls = []
    merged = dict(existing)

    for route in sorted(cited_routes):
        full_url = f"https://{HOST}{route}"
        if full_url not in merged:
            merged[full_url] = today
            new_urls.append(full_url)

    print(f"Newly discovered citation URLs to add: {len(new_urls)}")
    if new_urls:
        for u in new_urls[:10]:
            print(f"  + {u}")
        if len(new_urls) > 10:
            print(f"  ... and {len(new_urls) - 10} more.")

    if not new_urls:
        print("Sitemap is already completely up to date with current citations.")
        if do_indexnow:
            # If user explicitly ran with --indexnow and wants to submit top cited URLs anyway:
            all_urls = [f"https://{HOST}{r}" for r in sorted(cited_routes)]
            if all_urls:
                print(f"Submitting all {len(all_urls)} active cited URLs to IndexNow...")
                submit_indexnow(all_urls)
        return

    if dry_run:
        print("\n[DRY RUN] No changes written.")
        return

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for url, lastmod in merged.items():
        mod = lastmod or today
        lines.append('  <url>')
        lines.append(f'    <loc>{url}</loc>')
        lines.append(f'    <lastmod>{mod}</lastmod>')
        lines.append('    <changefreq>daily</changefreq>')
        lines.append('    <priority>1.0</priority>')
        lines.append('  </url>')
    lines.append('</urlset>')
    lines.append('')

    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nSuccessfully wrote {len(merged)} URLs to {SITEMAP_PATH}")

    if do_indexnow:
        submit_indexnow(new_urls)
    else:
        print("Tip: Run with --indexnow to also push these new URLs directly to Bing/IndexNow.")

if __name__ == "__main__":
    main()
