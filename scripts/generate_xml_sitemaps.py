#!/usr/bin/env python3
"""
AvaScry XML Sitemap Index & Sub-Sitemaps Generator
Generates standard, Google/Bing-compliant XML Sitemap Index and sub-sitemaps for:
1. sitemap-similar.xml (All 34,882 4096-dim neural synergy pages)
2. sitemap-cards.xml (Canonical printing pages)
3. sitemap-artists.xml (All 2,550 artist portfolio galleries)
4. sitemap-sets.xml (All 1,048 set checklists)
5. sitemap.xml (Master Sitemap Index)
"""

import os
import sys
import html
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db
from scripts.generate_embedding import slugify

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
INVALID_LAYOUTS = {'art_series', 'token', 'double_faced_token', 'emblem', 'planar', 'scheme', 'vanguard', 'memorabilia'}

def escape_xml(s: str) -> str:
    return html.escape(s or "")

def main():
    print("Connecting to MongoDB (mtgabyss_next)...")
    db = get_mongo_db()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Generate sitemap-similar.xml
    print("Fetching unique Oracle cards for sitemap-similar.xml...")
    cards_cursor = db["cards"].find(
        {"layout": {"$nin": list(INVALID_LAYOUTS)}, "lang": "en"},
        {"oracle_id": 1, "name": 1, "slug": 1, "set": 1, "printing_slug": 1}
    )
    oracle_map = {}
    for c in cards_cursor:
        oid = c.get("oracle_id")
        if oid and oid not in oracle_map:
            oracle_map[oid] = c

    similar_xml_path = os.path.join(PUBLIC_DIR, "sitemap-similar.xml")
    with open(similar_xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n')
        for oid, c in oracle_map.items():
            name = c.get("name") or "Card"
            slug = c.get("slug") or slugify(name)
            if not slug or not slug.strip():
                slug = f"blank-card-{str(oid)[:8]}"
            escaped_slug = escape_xml(slug)
            f.write("  <url>\n")
            f.write(f"    <loc>https://avascry.com/similar/{escaped_slug}</loc>\n")
            f.write(f'    <xhtml:link rel="alternate" type="text/markdown" href="https://avascry.com/similar/{escaped_slug}.md" />\n')
            f.write(f'    <xhtml:link rel="alternate" type="application/json" href="https://avascry.com/similar/{escaped_slug}.json" />\n')
            f.write(f"    <lastmod>{today_str}</lastmod>\n")
            f.write("    <changefreq>weekly</changefreq>\n")
            f.write("    <priority>0.9</priority>\n")
            f.write("  </url>\n")
        f.write("</urlset>\n")
    print(f"Generated public/sitemap-similar.xml ({len(oracle_map):,} URLs)")

    # 2. Generate sitemap-cards.xml
    print("Generating sitemap-cards.xml...")
    cards_xml_path = os.path.join(PUBLIC_DIR, "sitemap-cards.xml")
    with open(cards_xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n')
        # Core pages
        for core_path, prio in [("/", "1.0"), ("/commander", "0.9"), ("/sets", "0.8")]:
            f.write("  <url>\n")
            f.write(f"    <loc>https://avascry.com{core_path}</loc>\n")
            f.write(f"    <lastmod>{today_str}</lastmod>\n")
            f.write("    <changefreq>daily</changefreq>\n")
            f.write(f"    <priority>{prio}</priority>\n")
            f.write("  </url>\n")
        for oid, c in oracle_map.items():
            name = c.get("name") or "Card"
            slug = c.get("slug") or slugify(name)
            if not slug or not slug.strip():
                slug = f"blank-card-{str(oid)[:8]}"
            set_code = (c.get("set") or "").lower()
            p_slug = f"{slug}-{set_code}" if set_code else slug
            escaped_p_slug = escape_xml(p_slug)
            f.write("  <url>\n")
            f.write(f"    <loc>https://avascry.com/printing/{escaped_p_slug}</loc>\n")
            f.write(f'    <xhtml:link rel="alternate" type="text/markdown" href="https://avascry.com/printing/{escaped_p_slug}.md" />\n')
            f.write(f'    <xhtml:link rel="alternate" type="application/json" href="https://avascry.com/printing/{escaped_p_slug}.json" />\n')
            f.write(f"    <lastmod>{today_str}</lastmod>\n")
            f.write("    <changefreq>weekly</changefreq>\n")
            f.write("    <priority>0.8</priority>\n")
            f.write("  </url>\n")
        f.write("</urlset>\n")
    print(f"Generated public/sitemap-cards.xml ({len(oracle_map) + 3:,} URLs)")

    # 3. Generate sitemap-artists.xml
    print("Generating sitemap-artists.xml...")
    artists = list(db["cards"].aggregate([
        {"$match": {"artist": {"$exists": True, "$ne": None, "$ne": ""}}},
        {"$group": {"_id": "$artist", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]))
    artists_xml_path = os.path.join(PUBLIC_DIR, "sitemap-artists.xml")
    with open(artists_xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n')
        for a in artists:
            art_name = a["_id"] or ""
            art_slug = slugify(art_name)
            escaped_art = escape_xml(art_slug)
            f.write("  <url>\n")
            f.write(f"    <loc>https://avascry.com/artist/{escaped_art}</loc>\n")
            f.write(f'    <xhtml:link rel="alternate" type="text/markdown" href="https://avascry.com/artist/{escaped_art}.md" />\n')
            f.write(f'    <xhtml:link rel="alternate" type="application/json" href="https://avascry.com/artist/{escaped_art}.json" />\n')
            f.write(f"    <lastmod>{today_str}</lastmod>\n")
            f.write("    <changefreq>monthly</changefreq>\n")
            f.write("    <priority>0.7</priority>\n")
            f.write("  </url>\n")
        f.write("</urlset>\n")
    print(f"Generated public/sitemap-artists.xml ({len(artists):,} URLs)")

    # 4. Generate sitemap-sets.xml
    print("Generating sitemap-sets.xml...")
    sets = list(db["cards"].aggregate([
        {"$group": {"_id": "$set", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]))
    sets_xml_path = os.path.join(PUBLIC_DIR, "sitemap-sets.xml")
    with open(sets_xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n')
        for s in sets:
            set_code = (s["_id"] or "").lower()
            if not set_code:
                continue
            escaped_set = escape_xml(set_code)
            f.write("  <url>\n")
            f.write(f"    <loc>https://avascry.com/set/{escaped_set}</loc>\n")
            f.write(f'    <xhtml:link rel="alternate" type="text/markdown" href="https://avascry.com/set/{escaped_set}.md" />\n')
            f.write(f'    <xhtml:link rel="alternate" type="application/json" href="https://avascry.com/set/{escaped_set}.json" />\n')
            f.write(f"    <lastmod>{today_str}</lastmod>\n")
            f.write("    <changefreq>monthly</changefreq>\n")
            f.write("    <priority>0.7</priority>\n")
            f.write("  </url>\n")
        f.write("</urlset>\n")
    print(f"Generated public/sitemap-sets.xml ({len(sets):,} URLs)")

    # 5. Generate sitemap-legalities.xml & sitemap-rules.xml
    legalities_xml_path = os.path.join(PUBLIC_DIR, "sitemap-legalities.xml")
    with open(legalities_xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n')
        f.write('  <url>\n')
        f.write('    <loc>https://avascry.com/legalities.md</loc>\n')
        f.write('    <xhtml:link rel="alternate" type="application/json" href="https://avascry.com/legalities.json" />\n')
        f.write(f'    <lastmod>{today_str}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority>\n')
        f.write('  </url>\n')
        f.write('  <url>\n')
        f.write('    <loc>https://avascry.com/commander</loc>\n')
        f.write(f'    <lastmod>{today_str}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority>\n')
        f.write('  </url>\n')
        f.write('</urlset>\n')

    rules_xml_path = os.path.join(PUBLIC_DIR, "sitemap-rules.xml")
    with open(rules_xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n')
        f.write('  <url>\n')
        f.write('    <loc>https://avascry.com/rules.md</loc>\n')
        f.write('    <xhtml:link rel="alternate" type="application/json" href="https://avascry.com/rules.json" />\n')
        f.write(f'    <lastmod>{today_str}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority>\n')
        f.write('  </url>\n')
        f.write('</urlset>\n')

    # 6. Generate Master sitemap.xml (Sitemap Index)
    print("Generating Master sitemap.xml (Sitemap Index)...")
    master_sitemap_path = os.path.join(PUBLIC_DIR, "sitemap.xml")
    with open(master_sitemap_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for sitemap_name in ["sitemap-similar.xml", "sitemap-cards.xml", "sitemap-artists.xml", "sitemap-sets.xml", "sitemap-legalities.xml", "sitemap-rules.xml"]:
            f.write("  <sitemap>\n")
            f.write(f"    <loc>https://avascry.com/{sitemap_name}</loc>\n")
            f.write(f"    <lastmod>{today_str}</lastmod>\n")
            f.write("  </sitemap>\n")
        f.write("</sitemapindex>\n")
    print("Generated Master public/sitemap.xml (Sitemap Index)")
    print("All XML Sitemaps generated successfully!")

if __name__ == "__main__":
    main()
