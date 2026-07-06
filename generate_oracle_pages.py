import os
import sys
import re
import json
import datetime
import collections
from db_mongo import get_mongo_db, ensure_indexes

def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def format_oracle_text(text):
    if not text:
        return ""
    # Split paragraphs by newline, wrap in <p>, style symbol references if needed
    paras = text.split('\n')
    formatted = []
    for p in paras:
        p = p.strip()
        if p:
            # Highlight mana symbols like {T}, {B}, {3}
            p = re.sub(r'\{(.*?)\}', r'<span class="mana-symbol">\1</span>', p)
            formatted.append(f"<p>{p}</p>")
    return "\n".join(formatted)

def build_card_face_html(face, index=None):
    name = face.get("name", "Unnamed Face")
    mana_cost = face.get("mana_cost") or "None"
    type_line = face.get("type_line") or "Unknown"
    oracle_text = format_oracle_text(face.get("oracle_text", ""))
    
    # PT / Loyalty
    pt_loyalty = ""
    power = face.get("power")
    toughness = face.get("toughness")
    loyalty = face.get("loyalty")
    if power is not None and toughness is not None:
        pt_loyalty = f'<div class="pt-box">Power / Toughness: {power}/{toughness}</div>'
    elif loyalty is not None:
        pt_loyalty = f'<div class="pt-box">Loyalty: {loyalty}</div>'
        
    face_label = f" - Face {index}" if index else ""
    
    return f"""
    <div class="card-face">
      <div class="card-face-title">
        <span>{name}{face_label}</span>
        <span class="mana-cost">{mana_cost}</span>
      </div>
      <div class="card-face-type">{type_line}</div>
      <div class="oracle-text-box">{oracle_text}</div>
      {pt_loyalty}
    </div>
    """

def generate_page(oracle_id, cards_group, rulings, tags, template_content, output_dir, slug_map):
    # Sort printings by released_at asc, set_name, collector_number
    def sort_key(c):
        rel = c.get("released_at") or "0000-00-00"
        set_n = c.get("set_name") or ""
        coll = c.get("collector_number") or ""
        # Pad collector number to sort numerically if possible
        try:
            coll_val = f"{int(coll):06d}"
        except ValueError:
            coll_val = str(coll).zfill(6)
        return (rel, set_n, coll_val)
        
    sorted_cards = sorted(cards_group, key=sort_key)
    canonical_card = sorted_cards[0] # The representative card (usually oldest/first printed)
    
    card_name = canonical_card.get("name")
    
    # Establish canonical slug
    base_slug = slugify(card_name)
    if not base_slug:
        base_slug = "unnamed"
    
    # Handle slug collisions across different oracle_ids
    if oracle_id in slug_map:
        slug = slug_map[oracle_id]
    else:
        # Check if slug is taken by another oracle_id
        if base_slug in slug_map.values():
            slug = f"{base_slug}-{oracle_id[:8]}"
        else:
            slug = base_slug
        slug_map[oracle_id] = slug
        
    # Badges
    badges_list = []
    vintage_leg = canonical_card.get("legalities", {}).get("vintage", "not_legal")
    if vintage_leg == "restricted":
        badges_list.append('<span class="badge restricted">Vintage: Restricted</span>')
    elif vintage_leg == "banned":
        badges_list.append('<span class="badge banned">Vintage: Banned</span>')
    elif vintage_leg == "legal":
        badges_list.append('<span class="badge legal">Vintage: Legal</span>')
    else:
        badges_list.append('<span class="badge">Vintage: Not Legal</span>')
        
    badges_list.append(f'<span class="badge">Mana Value: {canonical_card.get("cmc", 0.0)}</span>')
    if canonical_card.get("reserved"):
        badges_list.append('<span class="badge reserved">Reserved List</span>')
    if card_name.lower() in {
        'black lotus', 'ancestral recall', 'time walk', 
        'mox pearl', 'mox sapphire', 'mox jet', 
        'mox ruby', 'mox emerald', 'timetwister'
    }:
        badges_list.append('<span class="badge p9">Power Nine</span>')
    badges_html = "\n".join(badges_list)
    
    # Image gallery HTML
    image_gallery_parts = []
    # Check if the canonical card has card_faces
    card_faces = canonical_card.get("card_faces") or []
    image_uris = canonical_card.get("image_uris")
    
    if image_uris:
        image_gallery_parts.append(f"""
        <div class="card-image-wrapper">
          <img src="{image_uris.get('normal')}" loading="lazy" alt="{card_name}">
        </div>
        """)
    elif card_faces:
        # Multi-faced card
        for i, face in enumerate(card_faces, 1):
            f_img = face.get("image_uris")
            if f_img:
                image_gallery_parts.append(f"""
                <div class="card-image-wrapper">
                  <img src="{f_img.get('normal')}" loading="lazy" alt="{face.get('name', card_name)} (Face {i})">
                </div>
                """)
                
    image_gallery_html = "\n".join(image_gallery_parts)
    
    # Card info text
    card_info_parts = []
    if card_faces:
        for i, face in enumerate(card_faces, 1):
            card_info_parts.append(build_card_face_html(face, i))
    else:
        card_info_parts.append(build_card_face_html(canonical_card))
    card_info_html = "\n".join(card_info_parts)
    
    # Facts
    color_identity = ", ".join(canonical_card.get("color_identity", [])) or "Colorless"
    mana_value = canonical_card.get("cmc", 0.0)
    keywords = ", ".join(canonical_card.get("keywords", [])) or "None"
    
    # Tags
    tags_html = ""
    if tags:
        for t in tags:
            tags_html += f'<span class="tag-badge" title="{t.get("namespace", "")}">{t.get("tag", "")}</span> '
    else:
        tags_html = '<div class="rulings-empty">No tags associated with this card.</div>'
        
    # Legality Grid
    legalities = canonical_card.get("legalities", {})
    formats = ["standard", "future", "historic", "timeless", "gladiator", "pioneer", "modern", "legacy", "pauper", "vintage", "penny", "commander", "oathbreaker", "standardbrawl", "brawl", "competitivebrawl", "alchemy", "paupercommander", "duel", "oldschool", "premodern", "predh", "tlr"]
    legality_items = []
    for fmt in formats:
        status = legalities.get(fmt, "not_legal")
        status_label = status.replace("_", " ")
        legality_items.append(f"""
        <div class="legality-item">
          <span class="legality-name">{fmt}</span>
          <span class="legality-status {status}">{status_label}</span>
        </div>
        """)
    legality_grid_html = "\n".join(legality_items)
    
    # Rulings
    rulings_html = ""
    if rulings:
        for r in rulings:
            rulings_html += f"""
            <div class="ruling-item">
              <div class="ruling-date">{r.get('published_at', '')} ({r.get('source', '').upper()})</div>
              <div>{r.get('comment', '')}</div>
            </div>
            """
    else:
        rulings_html = '<div class="rulings-empty">No rulings available.</div>'
        
    # Printings Grid
    printings_grid_parts = []
    for card in sorted_cards:
        c_set = card.get("set", "Unknown").upper()
        c_set_name = card.get("set_name", "Unknown Set")
        c_num = card.get("collector_number", "N/A")
        c_rarity = (card.get("rarity") or "Unknown").capitalize()
        c_artist = card.get("artist") or "Unknown"
        c_released = card.get("released_at") or "Unknown"
        c_lang = card.get("lang") or "en"
        c_scryfall = card.get("scryfall_uri") or "https://scryfall.com"
        
        # Image
        c_img_uri = ""
        c_imgs = card.get("image_uris")
        if c_imgs:
            c_img_uri = c_imgs.get("normal")
        else:
            c_faces = card.get("card_faces") or []
            if c_faces and c_faces[0].get("image_uris"):
                c_img_uri = c_faces[0].get("image_uris").get("normal")
                
        img_html = ""
        if c_img_uri:
            img_html = f"""
            <div class="variant-image-wrapper">
              <img src="{c_img_uri}" loading="lazy" alt="{card_name} ({c_set})">
            </div>
            """
            
        # Finishes
        finishes = card.get("raw", {}).get("finishes", [])
        finishes_str = "/".join(finishes) or "nonfoil"
        
        # Badges for variant card
        variant_badges = []
        if card.get("raw", {}).get("promo"):
            variant_badges.append('<span class="variant-mini-badge">Promo</span>')
        if card.get("raw", {}).get("digital"):
            variant_badges.append('<span class="variant-mini-badge">Digital</span>')
        if card.get("raw", {}).get("variation"):
            variant_badges.append('<span class="variant-mini-badge">Variation</span>')
        if "foil" in finishes:
            variant_badges.append('<span class="variant-mini-badge foil">Foil</span>')
        if "etched" in finishes:
            variant_badges.append('<span class="variant-mini-badge foil">Etched</span>')
            
        variant_badges_html = "\n".join(variant_badges)
        
        # Frame effects
        border_color = card.get("raw", {}).get("border_color", "black")
        frame = card.get("raw", {}).get("frame", "modern")
        full_art = "Full Art" if card.get("raw", {}).get("full_art") else "Standard Art"
        textless = "Textless" if card.get("raw", {}).get("textless") else "Texted"
        
        printings_grid_parts.append(f"""
        <div class="variant-card">
          {img_html}
          <div class="variant-header">
            <span class="variant-set-name">{c_set_name}</span>
            <span class="variant-set-code">{c_set}</span>
          </div>
          <div class="variant-details">
            <div class="variant-detail-row">
              <span class="variant-detail-label">Collector Number</span>
              <span class="variant-detail-value">#{c_num}</span>
            </div>
            <div class="variant-detail-row">
              <span class="variant-detail-label">Rarity</span>
              <span class="variant-detail-value">{c_rarity}</span>
            </div>
            <div class="variant-detail-row">
              <span class="variant-detail-label">Artist</span>
              <span class="variant-detail-value">{c_artist}</span>
            </div>
            <div class="variant-detail-row">
              <span class="variant-detail-label">Release Date</span>
              <span class="variant-detail-value">{c_released}</span>
            </div>
            <div class="variant-detail-row">
              <span class="variant-detail-label">Language</span>
              <span class="variant-detail-value">{c_lang}</span>
            </div>
            <div class="variant-detail-row">
              <span class="variant-detail-label">Finishes</span>
              <span class="variant-detail-value">{finishes_str}</span>
            </div>
            <div class="variant-detail-row">
              <span class="variant-detail-label">Frame/Border</span>
              <span class="variant-detail-value">{border_color} ({frame})</span>
            </div>
            <div class="variant-detail-row">
              <span class="variant-detail-label">Style</span>
              <span class="variant-detail-value">{full_art} / {textless}</span>
            </div>
          </div>
          <div class="variant-badges">
            {variant_badges_html}
          </div>
          <a href="{c_scryfall}" target="_blank" rel="noopener noreferrer" class="scryfall-link-btn">
            View on Scryfall &rarr;
          </a>
        </div>
        """)
        
    printings_grid_html = "\n".join(printings_grid_parts)
    scryfall_canonical_link = canonical_card.get("scryfall_uri") or "https://scryfall.com"
    
    # Replace placeholders in template (doing simple replace to avoid bracket errors)
    rendered = template_content.replace("{card_name}", card_name) \
                               .replace("{badges}", badges_html) \
                               .replace("{image_gallery_html}", image_gallery_html) \
                               .replace("{card_info_html}", card_info_html) \
                               .replace("{color_identity}", color_identity) \
                               .replace("{mana_value}", str(mana_value)) \
                               .replace("{keywords}", keywords) \
                               .replace("{tags_html}", tags_html) \
                               .replace("{legality_grid_html}", legality_grid_html) \
                               .replace("{rulings_html}", rulings_html) \
                               .replace("{printings_count}", str(len(sorted_cards))) \
                               .replace("{printings_grid_html}", printings_grid_html) \
                               .replace("{scryfall_canonical_link}", scryfall_canonical_link)
                               
    card_dir = os.path.join(output_dir, "cards", slug)
    os.makedirs(card_dir, exist_ok=True)
    output_file = os.path.join(card_dir, "index.html")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(rendered)
        
    return slug, card_name, canonical_card

def build_index_page(output_dir, sorted_cards):
    os.makedirs(os.path.join(output_dir, "cards"), exist_ok=True)
    
    # Sort cards alphabetically by name
    sorted_cards = sorted(sorted_cards, key=lambda x: x[1].lower())
    
    import random
    card_names = []
    if sorted_cards:
        sampled = random.sample(sorted_cards, min(5, len(sorted_cards)))
        card_names = [c[1] for c in sampled]
    
    # Pad with fallbacks if needed
    fallbacks = ["Black Lotus", "Sol Ring", "Lightning Bolt", "Counterspell", "Colossal Dreadmaw"]
    for f in fallbacks:
        if len(card_names) >= 5:
            break
        if f not in card_names:
            card_names.append(f)
    card_names = card_names[:5]

    pills_html = ""
    for name in card_names:
        pills_html += f'          <button type="button" class="homepage-example-pill" data-query="{name}" style="text-align: center;">{name}</button>\n'
    
    # Main Index - Search Centered
    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MTGAbyss — What do you seek?</title>
  <meta name="description" content="MTGAbyss: Natural language card search. Find Magic: The Gathering cards.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="site-header">
    <a class="site-logo" href="index.html">MTGAbyss</a>
    <nav>
      <a href="cards/index.html">Cards</a>
    </nav>
  </header>

  <div class="homepage-wrapper">
    <div class="homepage-panel">
      <div class="homepage-brand">MTGAbyss</div>
      <div class="homepage-subtitle">What do you seek?</div>
      
      <form class="homepage-search-form" id="search-form" action="search.html" method="get">
        <input 
          type="text" 
          name="q" 
          id="search-input" 
          class="homepage-search-input" 
          placeholder="Black Lotus" 
          required
          autocomplete="off"
        >
        <button type="submit" class="homepage-search-btn">Search</button>
      </form>
      
      <div class="homepage-examples">
        <div class="homepage-examples-label" style="text-align: center; margin-top: 1.5rem;">Try searching for:</div>
        <div class="homepage-examples-list" style="display: flex; flex-direction: row; flex-wrap: wrap; justify-content: center; gap: 0.5rem; margin-top: 0.75rem;">
{pills_html.rstrip()}
        </div>
      </div>
    </div>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', () => {
      const searchForm = document.getElementById('search-form');
      const searchInput = document.getElementById('search-input');
      const pills = document.querySelectorAll('.homepage-example-pill');

      pills.forEach(pill => {
        pill.addEventListener('click', () => {
          const query = pill.getAttribute('data-query');
          searchInput.value = query;
          searchForm.submit();
        });
      });
    });
  </script>
</body>
</html>
"""
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # Search placeholder page
    search_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Search Results | MTGAbyss</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="site-header">
    <a class="site-logo" href="index.html">MTGAbyss</a>
  </header>

  <div class="page-wrapper">
    <div class="container">
      <main class="search-results-panel">
        <h1 style="margin-top: 0; font-family: 'Outfit', sans-serif;">Search Results</h1>
        <p style="color: var(--abyss-muted);">This is a minimal placeholder for the natural-language card parser.</p>
        
        <div style="margin-top: 2rem;">
          <div>Search query:</div>
          <div class="search-query-display" id="search-query-display">...</div>
        </div>

        <div style="margin-top: 2.5rem;">
          <a href="index.html" class="homepage-search-btn" style="text-decoration: none; display: inline-block;">&larr; Back to Search</a>
        </div>
      </main>
    </div>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', () => {
      const params = new URLSearchParams(window.location.search);
      const query = params.get('q') || '';
      document.getElementById('search-query-display').textContent = query;
    });
  </script>
</body>
</html>
"""
    with open(os.path.join(output_dir, "search.html"), "w", encoding="utf-8") as f:
        f.write(search_html)
        
    # Cards directory page (statically paginated/chunked index)
    # We will split card list into alphabetical letters
    alphabet = collections.defaultdict(list)
    for slug, name, card in sorted_cards:
        first_char = name[0].upper() if name else ""
        if not re.match(r'[A-Z]', first_char):
            first_char = "0-9"
        alphabet[first_char].append((slug, name))
        
    alphabet_keys = sorted(list(alphabet.keys()), key=lambda x: (x == "0-9", x))
    
    # Generate cards/index.html (with letters index and letter pagination)
    for current_letter in alphabet_keys:
        letter_cards = alphabet[current_letter]
        
        # Build layout with A-Z navigation bar
        nav_html_list = []
        for l in alphabet_keys:
            active_class = "active" if l == current_letter else ""
            l_slug = "index" if l == "A" else l.lower()
            nav_html_list.append(f'<a href="{l_slug}.html" class="badge {active_class}" style="margin: 0.2rem; display: inline-block;">{l}</a>')
        nav_html = "\n".join(nav_html_list)
        
        card_links = []
        for slug, name in letter_cards:
            card_links.append(f'<li><a href="{slug}/index.html" style="color: var(--accent-purple); text-decoration: none; font-weight: 500; font-size: 1.1rem; line-height: 2;">{name}</a></li>')
        card_links_html = "\n".join(card_links)
        
        letter_page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Oracle Cards Directory - {current_letter}</title>
  <link rel="stylesheet" href="../assets/site.css">
  <style>
    .alphabet-nav {{
      background-color: var(--bg-panel);
      padding: 1rem;
      border-radius: 8px;
      border: 1px solid var(--border-color);
      margin-bottom: 1.5rem;
      text-align: center;
    }}
    .alphabet-nav a {{
      text-decoration: none;
    }}
    .alphabet-nav a.active {{
      background-color: var(--accent-purple);
      color: #000;
      border-color: var(--accent-purple);
    }}
    .cards-list-container {{
      column-count: 1;
      column-gap: 2rem;
    }}
    @media (min-width: 576px) {{
      .cards-list-container {{ column-count: 2; }}
    }}
    @media (min-width: 768px) {{
      .cards-list-container {{ column-count: 3; }}
    }}
    .cards-list-container ul {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Oracle Cards Directory</h1>
      <p style="color: var(--text-secondary); margin-top: 0.5rem;">Grouped by name alphabetically</p>
    </header>
    
    <nav class="alphabet-nav">
      {nav_html}
    </nav>
    
    <main class="panel">
      <h2 class="panel-title">{current_letter} Cards ({len(letter_cards)})</h2>
      <div class="cards-list-container">
        <ul>
          {card_links_html}
        </ul>
      </div>
    </main>
  </div>
</body>
</html>
"""
        # Save 'A' page as index.html, others as letter.html
        filename = "index.html" if current_letter == "A" else f"{current_letter.lower()}.html"
        file_path = os.path.join(output_dir, "cards", filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(letter_page_html)

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    import argparse
    parser = argparse.ArgumentParser(description="Build Oracle cards static pages.")
    parser.add_argument("--card", type=str, default=None, help="Name or slug of specific card to build.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of oracle cards to build.")
    parser.add_argument("--all", action="store_true", help="Build all cards in database.")
    args = parser.parse_args()
    
    db = get_mongo_db()
    ensure_indexes(db)
    
    # Load template
    template_path = "templates/oracle_card_detail.html"
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}")
        sys.exit(1)
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
        
    output_dir = "public"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Fetch cards and group by oracle_id
    print("Loading cards from MongoDB...")
    
    query = {}
    if args.card:
        # Search exact match or slug match
        query = {"$or": [{"name": args.card}, {"slug": slugify(args.card)}]}
        
    all_cards = list(db["cards"].find(query))
    if not all_cards:
        print("No cards found matching the criteria.")
        sys.exit(0)
        
    print(f"Loaded {len(all_cards)} card documents. Grouping by oracle_id...")
    groups = collections.defaultdict(list)
    for c in all_cards:
        groups[c.get("oracle_id")].append(c)
        
    oracle_ids = list(groups.keys())
    if args.limit and not args.card:
        oracle_ids = oracle_ids[:args.limit]
        
    print(f"Total unique Oracle card identities to generate: {len(oracle_ids)}")
    
    # Load rulings for the active oracle_ids
    print("Loading rulings...")
    all_rulings = list(db["rulings"].find({"oracle_id": {"$in": oracle_ids}}))
    
    rulings_by_oracle = collections.defaultdict(list)
    for r in all_rulings:
        rulings_by_oracle[r.get("oracle_id")].append(r)
        
    slug_map = {}
    generated_cards = []
    search_index = []
    
    total = len(oracle_ids)
    processed = 0
    
    for oid in oracle_ids:
        group = groups[oid]
        rulings = rulings_by_oracle.get(oid, [])
        tags = group[0].get("tags", []) if group else []
        
        # Sort rulings by published_at
        rulings = sorted(rulings, key=lambda x: x.get("published_at") or "")
        
        processed += 1
        card_name = group[0].get("name", "Unknown Card")
        
        # Progress output: Building oracle cards 123/38000: Black Lotus
        print(f"Building oracle cards {processed}/{total}: {card_name}")
        
        slug, name, canonical = generate_page(oid, group, rulings, tags, template_content, output_dir, slug_map)
        generated_cards.append((slug, name, canonical))
        
        # Add to search index
        search_index.append({
            "name": name,
            "slug": slug,
            "type_line": canonical.get("type_line", ""),
            "oracle_text": canonical.get("oracle_text", ""),
            "color_identity": canonical.get("color_identity", []),
            "keywords": canonical.get("keywords", [])
        })
        
    # Generate search-index.json
    print("Generating search-index.json...")
    with open(os.path.join(output_dir, "search-index.json"), "w", encoding="utf-8") as f:
        json.dump(search_index, f, indent=2)
        
    # Generate sitemap.xml
    print("Generating sitemap.xml...")
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for slug, _, _ in generated_cards:
        sitemap_lines.append(f"  <url>")
        sitemap_lines.append(f"    <loc>https://mtgabyss.com/cards/{slug}/index.html</loc>")
        sitemap_lines.append(f"    <lastmod>{now_str}</lastmod>")
        sitemap_lines.append(f"  </url>")
    sitemap_lines.append('</urlset>')
    with open(os.path.join(output_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sitemap_lines))
        
    # Generate index page and directory
    print("Generating index and directory pages...")
    build_index_page(output_dir, generated_cards)
    
    print("\nStatic build completed successfully.")

if __name__ == "__main__":
    main()
