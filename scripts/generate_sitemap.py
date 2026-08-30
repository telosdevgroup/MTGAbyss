import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
import html
import random

# Add root directory to path to allow importing db_mongo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db
from scripts.lure_shared import slugify

def format_xml(element):
    xml_str = ET.tostring(element, encoding="utf-8")
    reparsed = minidom.parseString(xml_str)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8")

def get_html_header():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Card Directory | MTGAbyss</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/site.css">
  <style>
    .sitemap-header {
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--abyss-border);
      padding-bottom: 1.5rem;
    }
    .sitemap-letters {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      margin-bottom: 2.5rem;
    }
    .sitemap-letter-pill {
      display: inline-block;
      background: var(--abyss-surface);
      border: 1px solid var(--abyss-border);
      color: var(--abyss-text);
      padding: 0.6rem 1.2rem;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 600;
      transition: all 0.2s ease;
    }
    .sitemap-letter-pill:hover, .sitemap-letter-pill.active {
      background: var(--sakura-deep);
      border-color: var(--sakura-deep);
      color: white;
    }
    .sitemap-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 1rem;
      margin-bottom: 3rem;
    }
    .sitemap-card-link {
      display: block;
      color: var(--abyss-link);
      text-decoration: none;
      padding: 0.5rem;
      border-radius: 4px;
      transition: all 0.2s ease;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .sitemap-card-link:hover {
      background: var(--abyss-surface-raised);
      color: var(--sakura-deep);
      padding-left: 0.75rem;
    }
    .back-link {
      display: inline-block;
      margin-bottom: 1.5rem;
      color: var(--abyss-muted);
      text-decoration: none;
      font-weight: 500;
    }
    .back-link:hover {
      color: var(--sakura-deep);
    }
  </style>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-837M1ZGHPE"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-837M1ZGHPE');
  </script>
</head>
<body>
  <header class="site-header">
    <a class="site-logo" href="index.html">MTGAbyss</a>
  </header>
  <div class="page-wrapper" style="padding-top: 80px; width: 100%;">
    <div class="container" style="max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem;">
"""

def get_html_footer():
    return """
    </div>
  </div>
</body>
</html>
"""

def main():
    print("Connecting to MongoDB...")
    db = get_mongo_db()
    
    print("Fetching card data from database...")
    cards = list(db["cards"].find({}, {"name": 1, "slug": 1}))
    print(f"Found {len(cards):,} cards.")

    base_url = "https://mtgabyss.com"
    os.makedirs("public", exist_ok=True)
    
    # -------------------------------------------------------------
    # 1. XML Sitemap (All cards)
    # -------------------------------------------------------------
    print("Building XML Sitemap (all cards)...")
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    # Homepage
    url_el = ET.SubElement(urlset, "url")
    ET.SubElement(url_el, "loc").text = f"{base_url}/"
    ET.SubElement(url_el, "changefreq").text = "daily"
    ET.SubElement(url_el, "priority").text = "1.0"
    
    # Search Page
    url_el = ET.SubElement(urlset, "url")
    ET.SubElement(url_el, "loc").text = f"{base_url}/search.html"
    ET.SubElement(url_el, "changefreq").text = "daily"
    ET.SubElement(url_el, "priority").text = "0.8"
    
    # Sitemap Index Page (HTML sitemap index)
    url_el = ET.SubElement(urlset, "url")
    ET.SubElement(url_el, "loc").text = f"{base_url}/sitemap.html"
    ET.SubElement(url_el, "changefreq").text = "weekly"
    ET.SubElement(url_el, "priority").text = "0.7"

    # Select exactly 98 random cards (+ 3 base URLs = 101 entries total)
    sample_size = min(98, len(cards))
    random_cards = random.sample(cards, sample_size)
    print(f"Sampled {sample_size} random cards for XML sitemap.")

    for card in random_cards:
        name = card.get("name")
        slug = card.get("slug") or slugify(name)
        if slug:
            url_el = ET.SubElement(urlset, "url")
            ET.SubElement(url_el, "loc").text = f"{base_url}/card/{slug}"
            ET.SubElement(url_el, "changefreq").text = "weekly"
            ET.SubElement(url_el, "priority").text = "0.5"
            
    sitemap_xml_path = os.path.join("public", "sitemap.xml")
    with open(sitemap_xml_path, "wb") as f:
        f.write(format_xml(urlset))
    print(f"Generated {sitemap_xml_path} with {sample_size + 3:,} entries.")

    # -------------------------------------------------------------
    # 2. Robots.txt
    # -------------------------------------------------------------
    print("Building Robots.txt...")
    robots_path = os.path.join("public", "robots.txt")
    robots_content = f"""# Allow standard search engines
User-agent: Googlebot
User-agent: Bingbot
User-agent: YandexBot
User-agent: Slurp
User-agent: DuckDuckBot
Allow: /

# Block AI scrapers and search crawlers
User-agent: GPTBot
User-agent: ChatGPT-User
User-agent: Anthropic-AI
User-agent: Claude-Web
User-agent: ClaudeBot
User-agent: cohere-ai
User-agent: OMgilibot
User-agent: YouBot
User-agent: PerplexityBot
User-agent: Diffbot
User-agent: ByteSpider
User-agent: FacebookBot
User-agent: ImagesiftBot
User-agent: PetalBot
User-agent: Amazonbot
Disallow: /

# Block SEO and aggressive scrapers
User-agent: AhrefsBot
User-agent: SemrushBot
User-agent: DotBot
User-agent: Rogerbot
User-agent: MJ12bot
Disallow: /

# Allow everyone else
User-agent: *
Allow: /

Sitemap: {base_url}/sitemap.xml
"""
    with open(robots_path, "w", encoding="utf-8") as f:
        f.write(robots_content)
    print(f"Generated {robots_path}")

    # -------------------------------------------------------------
    # 3. HTML Sitemaps (Alphabetical)
    # -------------------------------------------------------------
    print("Grouping cards by starting character...")
    groups = {}
    for card in cards:
        name = card.get("name", "")
        if not name:
            continue
        first_char = name[0].upper()
        if not first_char.isalnum():
            group_key = "num"
        elif first_char.isdigit():
            group_key = "num"
        else:
            group_key = first_char
            
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(card)

    # Sort groups alphabetically, with num last
    sorted_group_keys = sorted([k for k in groups.keys() if k != "num"])
    if "num" in groups:
        sorted_group_keys.append("num")
        
    # Helper to generate letter pill navigation HTML
    def get_navigation_html(active_key=None):
        nav_html = '<div class="sitemap-letters">\n'
        for key in sorted_group_keys:
            display_label = "#" if key == "num" else key
            active_class = ' active' if key == active_key else ''
            nav_html += f'    <a href="sitemap-{key.lower()}.html" class="sitemap-letter-pill{active_class}">{display_label}</a>\n'
        nav_html += "  </div>\n"
        return nav_html

    # Generate main public/sitemap.html (Index page)
    print("Generating main sitemap.html directory index...")
    index_html = get_html_header()
    index_html += """
      <div class="sitemap-header">
        <h1 style="font-family: 'Outfit', sans-serif; font-size: 2.5rem; margin: 0 0 0.5rem 0;">Alphabetical Directory</h1>
        <p style="color: var(--abyss-muted); margin: 0;">Browse our complete index of Magic: The Gathering cards alphabetically.</p>
      </div>
    """
    index_html += get_navigation_html()
    index_html += get_html_footer()
    
    main_sitemap_path = os.path.join("public", "sitemap.html")
    with open(main_sitemap_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"Generated {main_sitemap_path}")

    # Generate individual sitemap-*.html pages
    for key in sorted_group_keys:
        key_lower = key.lower()
        display_label = "#" if key == "num" else key
        group_cards = sorted(groups[key], key=lambda c: c.get("name", "").lower())
        
        print(f"Generating sitemap-{key_lower}.html ({len(group_cards):,} cards)...")
        
        page_html = get_html_header()
        page_html += f"""
      <a href="sitemap.html" class="back-link">&larr; Back to Directory</a>
      <div class="sitemap-header">
        <h1 style="font-family: 'Outfit', sans-serif; font-size: 2.5rem; margin: 0 0 0.5rem 0;">Cards starting with "{display_label}"</h1>
        <p style="color: var(--abyss-muted); margin: 0;">Total cards in this section: {len(group_cards):,}</p>
      </div>
        """
        page_html += get_navigation_html(key)
        
        # Grid list
        page_html += '      <div class="sitemap-grid">\n'
        for card in group_cards:
            c_name = card.get("name")
            c_slug = card.get("slug") or slugify(c_name)
            escaped_name = html.escape(c_name)
            page_html += f'        <a href="card/{c_slug}/index.html" class="sitemap-card-link" title="{escaped_name}">{escaped_name}</a>\n'
        page_html += '      </div>\n'
        
        page_html += get_html_footer()
        
        letter_sitemap_path = os.path.join("public", f"sitemap-{key_lower}.html")
        with open(letter_sitemap_path, "w", encoding="utf-8") as f:
            f.write(page_html)
            
    print("Alphabetical HTML sitemaps generation complete!")

if __name__ == "__main__":
    main()
