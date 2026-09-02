#!/usr/bin/env python3
"""
AvaScry Dual-Surface HTML Sitemap Generator
Generates clean, zero-JS, high-density HTML sitemaps with dual [HTML] and [MD] links
for rapid crawler discovery by ClaudeBot, GPTBot, Perplexity, Googlebot, and Bingbot.
Includes Sets, Artists (2,550+ MTG illustrators), and all 38k Oracle cards.
"""

import os
import sys
import html
from datetime import datetime, timezone
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db
from scripts.generate_embedding import slugify

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "sitemaps")
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
INVALID_LAYOUTS = {'art_series', 'token', 'double_faced_token', 'emblem', 'planar', 'scheme', 'vanguard', 'memorabilia'}

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def html_escape(text: str) -> str:
    return html.escape(text or "")

def generate_header(title: str, description: str, breadcrumb: str = "") -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_escape(title)} | AvaScry Sitemap</title>
  <meta name="description" content="{html_escape(description)}">
  <meta name="robots" content="index, follow">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 960px; margin: 0 auto; padding: 24px 16px; color: #1e293b; background: #f8fafc; }}
    h1 {{ font-size: 1.75rem; color: #0f172a; margin-bottom: 8px; }}
    p.meta {{ color: #64748b; font-size: 0.875rem; margin-top: 0; margin-bottom: 24px; }}
    .nav-bar {{ margin-bottom: 20px; padding: 12px; background: #e2e8f0; border-radius: 6px; font-size: 0.9rem; }}
    .nav-bar a {{ color: #2563eb; text-decoration: none; font-weight: 500; }}
    .nav-bar a:hover {{ text-decoration: underline; }}
    ul {{ list-style-type: none; padding-left: 0; }}
    li {{ padding: 6px 0; border-bottom: 1px solid #e2e8f0; font-size: 0.95rem; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .badge-md {{ display: inline-block; background: #0f172a; color: #38bdf8; font-size: 0.75rem; font-weight: 600; padding: 1px 6px; border-radius: 4px; text-decoration: none; margin-left: 4px; }}
    .badge-md:hover {{ background: #1e293b; color: #7dd3fc; text-decoration: none; }}
    .badge-json {{ display: inline-block; background: #1e1b4b; color: #fbbf24; font-size: 0.75rem; font-weight: 600; padding: 1px 6px; border-radius: 4px; text-decoration: none; margin-left: 4px; }}
    .badge-json:hover {{ background: #312e81; color: #fde68a; text-decoration: none; }}
    .badge-vec {{ display: inline-block; background: #064e3b; color: #34d399; font-size: 0.75rem; font-weight: 600; padding: 1px 6px; border-radius: 4px; text-decoration: none; margin-left: 4px; }}
    .badge-vec:hover {{ background: #065f46; color: #6ee7b7; text-decoration: none; }}
    .type {{ color: #64748b; font-size: 0.85rem; margin-left: 6px; }}
    .mana {{ color: #d97706; font-family: monospace; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <nav class="nav-bar" aria-label="Breadcrumb">
    <a href="/">← AvaScry Home</a> | <a href="/sitemap.html">Sitemap Hub</a> {breadcrumb}
  </nav>
  <h1>{html_escape(title)}</h1>
  <p class="meta">Last Updated: {now_str} • Tri-Surface HTML, Markdown &amp; JSON AI Knowledge Index</p>
"""

def generate_footer() -> str:
    return """
  <hr style="margin-top: 32px; border: 0; border-top: 1px solid #cbd5e1;">
  <p style="font-size: 0.8rem; color: #64748b; text-align: center;">AvaScry AI Knowledge Graph • <a href="/llms.txt">llms.txt</a> • <a href="/sitemap.md">sitemap.md</a> • <a href="/sitemap.xml">sitemap.xml</a> • <a href="/robots.txt">robots.txt</a></p>
</body>
</html>
"""

def main():
    ensure_dirs()
    print("Connecting to MongoDB (mtgabyss_next)...")
    db = get_mongo_db()

    # 1. Fetch all distinct sets
    print("Fetching sets...")
    sets_pipeline = [
        {"$group": {"_id": "$set", "name": {"$first": "$set_name"}, "count": {"$sum": 1}}},
        {"$sort": {"name": 1}}
    ]
    all_sets = list(db["cards"].aggregate(sets_pipeline))
    print(f"Found {len(all_sets):,} sets.")

    # Write sets sitemap
    sets_html_path = os.path.join(OUTPUT_DIR, "sets.html")
    with open(sets_html_path, "w", encoding="utf-8") as f:
        f.write(generate_header("Magic: The Gathering Sets Index", "Complete list of Magic: The Gathering sets with card checklists and printings.", '| <a href="/sets.md">[Sets MD]</a> | <span>Sets</span>'))
        f.write("<ul>\n")
        for s in all_sets:
            set_code = s["_id"] or ""
            set_name = s["name"] or set_code.upper()
            count = s["count"]
            f.write(f'  <li><a href="/set/{set_code.lower()}"><strong>{html_escape(set_name)}</strong> ({set_code.upper()})</a> <a href="/set/{set_code.lower()}.md" class="badge-md">[Set MD]</a> <a href="/set/{set_code.lower()}.json" class="badge-json">[API JSON]</a> — {count:,} cards</li>\n')
        f.write("</ul>\n")
        f.write(generate_footer())
    print("Generated public/sitemaps/sets.html")

    # 2. Fetch all distinct artists
    print("Fetching MTG artists...")
    artists_pipeline = [
        {"$match": {"artist": {"$exists": True, "$ne": None, "$ne": ""}}},
        {"$group": {"_id": "$artist", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    all_artists = list(db["cards"].aggregate(artists_pipeline))
    print(f"Found {len(all_artists):,} artists.")

    # Write artists sitemap
    artists_html_path = os.path.join(OUTPUT_DIR, "artists.html")
    with open(artists_html_path, "w", encoding="utf-8") as f:
        f.write(generate_header(f"Magic: The Gathering Artists Index ({len(all_artists):,} Illustrators)", "Complete gallery index of all historical Magic: The Gathering illustrators and artists.", "| <span>Artists</span>"))
        f.write("<ul>\n")
        for a in all_artists:
            art_name = a["_id"] or ""
            art_slug = slugify(art_name)
            count = a["count"]
            f.write(f'  <li><a href="/artist/{art_slug}"><strong>{html_escape(art_name)}</strong></a> <a href="/artist/{art_slug}.md" class="badge-md" title="Artist Portfolio Markdown">[Portfolio MD]</a> <a href="/artist/{art_slug}.json" class="badge-json" title="Artist Portfolio JSON">[API JSON]</a> — {count:,} cards illustrated</li>\n')
        f.write("</ul>\n")
        f.write(generate_footer())
    print("Generated public/sitemaps/artists.html")

    # 3. Fetch all unique Oracle cards
    print("Fetching unique Oracle cards...")
    cards_cursor = db["cards"].find(
        {"layout": {"$nin": list(INVALID_LAYOUTS)}, "lang": "en"},
        {"oracle_id": 1, "name": 1, "slug": 1, "set": 1, "type_line": 1, "mana_cost": 1}
    )

    oracle_map = {}
    for c in cards_cursor:
        oid = c.get("oracle_id")
        if oid and oid not in oracle_map:
            oracle_map[oid] = c

    print(f"Found {len(oracle_map):,} unique Oracle cards.")

    # Group by first letter
    letter_groups = defaultdict(list)
    for oid, c in oracle_map.items():
        name = c.get("name") or "Unknown"
        first_char = name[0].upper()
        if 'A' <= first_char <= 'Z':
            letter_groups[first_char].append(c)
        else:
            letter_groups['0-9'].append(c)

    letters = sorted(letter_groups.keys())

    # Write sub-sitemaps for each letter (Both HTML and Markdown)
    for letter in letters:
        cards_in_letter = sorted(letter_groups[letter], key=lambda x: (x.get("name") or "").lower())
        
        # HTML Sitemap
        html_filename = f"cards-{letter.lower()}.html"
        html_filepath = os.path.join(OUTPUT_DIR, html_filename)
        with open(html_filepath, "w", encoding="utf-8") as f:
            breadcrumb = f'| <a href="/sitemap.html#letters">Letters</a> | <span>Letter {letter}</span>'
            f.write(generate_header(f"Cards Starting with '{letter}' ({len(cards_in_letter):,} Cards)", f"Browse MTG cards, synergies, and AI Markdown endpoints for cards starting with {letter}.", breadcrumb))
            f.write("<ul>\n")
            for c in cards_in_letter:
                c_name = c.get("name") or "Card"
                c_slug = c.get("slug") or slugify(c_name)
                if not c_slug or not c_slug.strip():
                    c_oid = c.get("oracle_id") or str(c.get("_id", "card"))
                    c_slug = f"blank-card-{str(c_oid)[:8]}"
                c_set = (c.get("set") or "").lower()
                c_printing_slug = f"{c_slug}-{c_set}" if c_set else c_slug
                c_mana = c.get("mana_cost") or ""
                c_type = c.get("type_line") or ""

                f.write(f'  <li>')
                f.write(f'<a href="/similar/{c_slug}"><strong>{html_escape(c_name)}</strong></a> <a href="/similar/{c_slug}.md" class="badge-md" title="AI Synergies Markdown">[Synergies MD]</a> <a href="/similar/{c_slug}.json" class="badge-json" title="AI Synergies JSON">[Synergies JSON]</a> <a href="/vector/{c_slug}.json" class="badge-vec" title="4096-Dim Neural Vector">[Vector]</a>')
                if c_mana:
                    f.write(f' <span class="mana">{html_escape(c_mana)}</span>')
                if c_type:
                    f.write(f' <span class="type">— {html_escape(c_type)}</span>')
                f.write(f' — <a href="/printing/{c_printing_slug}">[Card]</a> <a href="/printing/{c_printing_slug}.md" class="badge-md" title="Card Rules Markdown">[Card MD]</a> <a href="/printing/{c_printing_slug}.json" class="badge-json" title="Card Rules JSON">[Card JSON]</a>')
                f.write(f'</li>\n')
            f.write("</ul>\n")
            f.write(generate_footer())

        # Markdown Sitemap
        md_filename = f"cards-{letter.lower()}.md"
        md_filepath = os.path.join(OUTPUT_DIR, md_filename)
        with open(md_filepath, "w", encoding="utf-8") as f:
            f.write(f"# Magic: The Gathering Cards — Letter {letter} ({len(cards_in_letter):,} Cards)\n\n")
            f.write(f"> Canonical machine-readable Markdown sitemap for MTG cards, printings, 4096-d neural vectors, and synergy manifolds starting with '{letter}'.\n\n---\n\n")
            for c in cards_in_letter:
                c_name = c.get("name") or "Card"
                c_slug = c.get("slug") or slugify(c_name)
                if not c_slug or not c_slug.strip():
                    c_oid = c.get("oracle_id") or str(c.get("_id", "card"))
                    c_slug = f"blank-card-{str(c_oid)[:8]}"
                c_set = (c.get("set") or "").lower()
                c_printing_slug = f"{c_slug}-{c_set}" if c_set else c_slug
                c_mana = f" ({c.get('mana_cost')})" if c.get('mana_cost') else ""
                c_type = f" — {c.get('type_line')}" if c.get('type_line') else ""

                f.write(f"- [{c_name}](https://avascry.com/printing/{c_printing_slug}){c_mana}{c_type} • [MD](https://avascry.com/printing/{c_printing_slug}.md) • [JSON](https://avascry.com/printing/{c_printing_slug}.json) • [Vector](https://avascry.com/vector/{c_slug}.json) • [Synergies](https://avascry.com/similar/{c_slug}.md)\n")

        print(f"Generated public/sitemaps/{html_filename} and {md_filename} ({len(cards_in_letter):,} cards)")

    # 4. Write Master Sitemap Hub (public/sitemap.html)
    hub_path = os.path.join(PUBLIC_DIR, "sitemap.html")
    with open(hub_path, "w", encoding="utf-8") as f:
        f.write(generate_header("AvaScry HTML & AI Markdown Sitemap Directory", "Master sitemap hub linking all MTG cards, sets, artists, synergies, and Markdown endpoints for search engines and AI crawlers."))
        f.write(f"""
  <h2>Browse by Set & Artist</h2>
  <ul>
    <li><a href="/sitemaps/sets.html"><strong>All Magic: The Gathering Sets Index</strong></a> ({len(all_sets):,} expansion and promo sets)</li>
    <li><a href="/sitemaps/artists.html"><strong>All Magic: The Gathering Artists Index</strong></a> ({len(all_artists):,} historical illustrators)</li>
  </ul>

  <h2 id="letters">Browse Cards & 4096-Dim Synergies by Letter</h2>
  <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px;">
""")
        for letter in letters:
            count = len(letter_groups[letter])
            f.write(f'    <a href="/sitemaps/cards-{letter.lower()}.html" style="padding: 8px 14px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; font-weight: bold; color: #2563eb; text-decoration: none;">{letter} <span style="font-size: 0.75rem; color: #64748b; font-weight: normal;">({count:,})</span></a>\n')

        f.write("""
  </div>

  <h2>AI Agent & Machine Ingestion Resources</h2>
  <ul>
    <li><a href="/llms.txt"><strong>/llms.txt</strong></a> — Official standard descriptor for LLMs and AI search bots</li>
    <li><a href="/heartbeat.txt"><strong>/heartbeat.txt</strong></a> — Corpus freshness & sync heartbeat</li>
    <li><a href="/.well-known/ai-content"><strong>/.well-known/ai-content</strong></a> — AI Content Discovery Manifest</li>
    <li><a href="/sitemap.md"><strong>/sitemap.md</strong></a> — Raw Markdown Sitemap Index</li>
    <li><a href="/sitemap.xml"><strong>/sitemap.xml</strong></a> — Master XML Sitemap Index with <code>xhtml:link</code> alternates</li>
    <li><a href="/rules.md"><strong>/rules.md</strong></a> — Complete MTG Comprehensive Rules & Mechanics Engine (Markdown)</li>
    <li><a href="/rules.json"><strong>/rules.json</strong></a> — Complete MTG Comprehensive Rules Corpus (Structured JSON)</li>
    <li><a href="/legalities.md"><strong>/legalities.md</strong></a> — Complete MTG Format Legalities & Banlists (Markdown)</li>
    <li><a href="/legalities.json"><strong>/legalities.json</strong></a> — Complete MTG Format Legalities Corpus (Structured JSON)</li>
    <li><a href="/robots.txt"><strong>/robots.txt</strong></a> — Crawler access rules</li>
  </ul>
""")
        f.write(generate_footer())
    print("Generated master public/sitemap.html")

    # 5. Write Master Markdown Sitemap (public/sitemap.md) with 100% direct Markdown links
    md_hub_path = os.path.join(PUBLIC_DIR, "sitemap.md")
    with open(md_hub_path, "w", encoding="utf-8") as f:
        f.write("# AvaScry AI Corpus Index (Markdown Sitemap)\n\n")
        f.write("> AvaScry is a semantic, visual, and neural knowledge corpus for Magic: The Gathering. Powered by 4096-dimensional embeddings across 38,000+ Oracle cards.\n\n")
        f.write("## Core Knowledge & Rules Hubs\n")
        f.write("- [Comprehensive Rules & Gameplay Mechanics (`/rules.md`)](https://avascry.com/rules.md) • [JSON API](https://avascry.com/rules.json)\n")
        f.write("- [Format Legalities & Banlists (`/legalities.md`)](https://avascry.com/legalities.md) • [JSON API](https://avascry.com/legalities.json)\n")
        f.write("- [Sets Directory (`/sets.md`)](https://avascry.com/sets.md) • [HTML View](https://avascry.com/sitemaps/sets.html)\n")
        f.write("- [Artists Index (`/sitemaps/artists.html`)](https://avascry.com/sitemaps/artists.html)\n")
        f.write("- [Corpus Freshness Heartbeat (`/heartbeat.txt`)](https://avascry.com/heartbeat.txt)\n")
        f.write("- [LLMs Corpus Specification (`/llms.txt`)](https://avascry.com/llms.txt)\n")
        f.write("- [AI Content Manifest (`/.well-known/ai-content`)](https://avascry.com/.well-known/ai-content)\n")
        f.write("- [Master XML Sitemap Index](https://avascry.com/sitemap.xml)\n\n")
        
        f.write("## Card & Synergy Markdown Sitemaps by Letter\n")
        for letter in letters:
            count = len(letter_groups[letter])
            f.write(f"- [Cards & Synergies starting with '{letter}' ({count:,} cards)](https://avascry.com/sitemaps/cards-{letter.lower()}.md) • [HTML View](https://avascry.com/sitemaps/cards-{letter.lower()}.html)\n")

    print("Generated master public/sitemap.md with 100% direct Markdown links!")
    print("All Dual-Surface HTML & Markdown sitemaps generated successfully!")

if __name__ == "__main__":
    main()
