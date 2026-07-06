import os
import sys
import re
from db_mongo import get_mongo_db

POWER_NINE = {
    'black lotus', 'ancestral recall', 'time walk', 
    'mox pearl', 'mox sapphire', 'mox jet', 
    'mox ruby', 'mox emerald', 'timetwister'
}

def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def markdown_to_html(md):
    if not md:
        return ""
    # Simple markdown parser to avoid dependencies
    html = md
    # Split paragraphs by double newline
    paragraphs = html.split('\n\n')
    formatted_paras = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # Headers: ### Header
        if p.startswith('### '):
            p = f"<h3>{p[4:]}</h3>"
        elif p.startswith('## '):
            p = f"<h2>{p[3:]}</h2>"
        elif p.startswith('# '):
            p = f"<h1>{p[2:]}</h1>"
        else:
            # Bold
            p = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', p)
            # Italics
            p = re.sub(r'\*(.*?)\*', r'<em>\1</em>', p)
            p = f"<p>{p.replace(chr(10), '<br>')}</p>"
        formatted_paras.append(p)
    return "\n".join(formatted_paras)

def main():
    db = get_mongo_db()
    
    # Check arguments
    search_term = None
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
        
    card = None
    
    # 1. Search by argument if provided
    if search_term:
        print(f"Searching MongoDB for card: '{search_term}'...")
        card = db["cards"].find_one({
            "$or": [
                {"name": search_term},
                {"slug": slugify(search_term)}
            ]
        })
        if card:
            print(f"Found '{card.get('name')}' by exact name/slug match.")
            
    # 2. Fallback to Black Lotus if no search term, or search term didn't match
    if not card:
        if search_term:
            print(f"Card '{search_term}' not found. Falling back to default...")
        card = db["cards"].find_one({"name": "Black Lotus"})
        if card:
            print("Found 'Black Lotus' in MongoDB.")
            
    # 3. Fallback to first restricted card
    if not card:
        print("Black Lotus not found. Searching for first card with Vintage legality = 'restricted'...")
        card = db["cards"].find_one({"legalities.vintage": "restricted"})
        if card:
            print(f"Found restricted card: '{card.get('name')}'")
            
    if not card:
        # Fallback to absolute first card in database
        card = db["cards"].find_one({})
        if card:
            print(f"No restricted cards or Black Lotus found. Using first card: '{card.get('name')}'")
        else:
            print("No cards found in the MongoDB database at all!")
            sys.exit(1)
            
    oracle_id = card.get('oracle_id')
    name = card.get('name')
    slug = slugify(name)
    
    # Load rulings
    rulings = list(db["rulings"].find({"oracle_id": oracle_id}).sort("published_at", 1))
    
    # Load tags from embedded array
    tags = card.get("tags", [])
    
    # Load AI page
    ai_page = db["ai_pages"].find_one({
        "oracle_id": oracle_id,
        "language": "en",
        "page_type": "profile"
    })
    
    # Format AI Profile section
    if ai_page:
        ai_profile_html = markdown_to_html(ai_page.get("body_markdown", ""))
        print(f"Found AI profile for '{name}'.")
    else:
        ai_profile_html = '<p style="font-style: italic; color: var(--text-secondary);">Abyss profile not generated yet.</p>'
        print(f"No AI profile found for '{name}'. Using placeholder.")
    
    # Extract card image URL
    image_url = ''
    raw_card = card.get('raw', {})
    image_uris = raw_card.get('image_uris', {})
    if image_uris:
        image_url = image_uris.get('large') or image_uris.get('normal', '')
    else:
        card_faces = raw_card.get('card_faces', [])
        if card_faces and card_faces[0].get('image_uris'):
            f_uris = card_faces[0].get('image_uris', {})
            image_url = f_uris.get('large') or f_uris.get('normal', '')

    # Generate HTML components
    mana_cost = card.get('mana_cost') or 'None'
    cmc = card.get('cmc', 0.0)
    type_line = card.get('type_line') or ''
    oracle_text = card.get('oracle_text') or ''
    
    # PT / Loyalty
    pt_loyalty_html = ''
    power = card.get('power')
    toughness = card.get('toughness')
    loyalty = card.get('loyalty')
    if power is not None and toughness is not None:
        pt_loyalty_html = f'<div class="pt-box">Power / Toughness: {power}/{toughness}</div>'
    elif loyalty is not None:
        pt_loyalty_html = f'<div class="pt-box">Loyalty: {loyalty}</div>'
        
    color_identity = ", ".join(card.get('color_identity', [])) or 'Colorless'
    keywords = ", ".join(card.get('keywords', [])) or 'None'
    artist = card.get('artist') or 'Unknown'
    released_at = card.get('released_at') or 'Unknown'
    
    # Badges formatting
    badges_list = []
    
    # Vintage legality
    vintage_leg = card.get('legalities', {}).get('vintage', 'not_legal')
    if vintage_leg == 'restricted':
        badges_list.append('<span class="badge restricted">Vintage: Restricted</span>')
    elif vintage_leg == 'banned':
        badges_list.append('<span class="badge banned">Vintage: Banned</span>')
    elif vintage_leg == 'legal':
        badges_list.append('<span class="badge legal">Vintage: Legal</span>')
    else:
        badges_list.append('<span class="badge">Vintage: Not Legal</span>')
        
    # Mana Value
    badges_list.append(f'<span class="badge">Mana Value: {cmc}</span>')
    
    # Reserved List
    if card.get('reserved'):
        badges_list.append('<span class="badge reserved">Reserved List</span>')
        
    # Power Nine
    if name.lower() in POWER_NINE:
        badges_list.append('<span class="badge p9">Power Nine</span>')
        
    # Color Identity
    ci_str = "".join(card.get('color_identity', []))
    if ci_str:
        badges_list.append(f'<span class="badge">Colors: {ci_str}</span>')
    else:
        badges_list.append('<span class="badge">Colorless</span>')
        
    badges_html = "\n".join(badges_list)
    
    # Legality Grid
    legalities = card.get('legalities', {})
    formats_to_show = ['vintage', 'legacy', 'commander', 'modern', 'pauper']
    legality_items = []
    for fmt in formats_to_show:
        status = legalities.get(fmt, 'not_legal')
        status_label = status.replace('_', ' ')
        legality_items.append(f"""
        <div class="legality-item">
          <span class="legality-name">{fmt}</span>
          <span class="legality-status {status}">{status_label}</span>
        </div>
        """)
    legality_grid_html = "\n".join(legality_items)
    
    # Printings Table
    set_name = card.get('set_name', 'Unknown')
    set_code = (card.get('set') or 'Unknown').upper()
    collector_num = card.get('collector_number') or 'N/A'
    rarity = (card.get('rarity') or 'Unknown').capitalize()
    printings_html = f"""
    <table class="printings-table">
      <thead>
        <tr>
          <th>Set Name</th>
          <th>Set Code</th>
          <th>Number</th>
          <th>Rarity</th>
          <th>Release Date</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>{set_name}</td>
          <td><span class="set-code">{set_code}</span></td>
          <td>#{collector_num}</td>
          <td>{rarity}</td>
          <td>{released_at}</td>
        </tr>
      </tbody>
    </table>
    <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.75rem; font-style: italic;">
      Note: This displays the primary representative printing of this card from Scryfall's Oracle dataset.
    </p>
    """
    
    # Rulings HTML
    rulings_html = ''
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
        
    # Tags HTML
    tags_html = ''
    if tags:
        for t in tags:
            tags_html += f'<span class="tag-badge" title="{t["namespace"]}">{t["tag"]}</span>'
    else:
        tags_html = '<div class="rulings-empty">No tags associated with this card.</div>'
        
    # Source fields
    # MongoDB docs contain standard BSON object ids and raw keys. We clean them up
    source_fields = sorted(list(card.keys()))
    if "_id" in source_fields:
        source_fields.remove("_id")
    source_fields_html = "".join([f"<div>{f}</div>" for f in source_fields])
    
    scryfall_uri = card.get('scryfall_uri') or 'https://scryfall.com'

    # Fetch printings from Scryfall API
    printings_list = []
    try:
        import urllib.request
        import urllib.parse
        import json
        url = 'https://api.scryfall.com/cards/search?q=' + urllib.parse.quote_plus(f'oracle_id:{oracle_id}') + '&unique=prints'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            for item in data.get('data', []):
                uris = item.get('image_uris', {})
                img = uris.get('large') or uris.get('normal')
                if not img:
                    faces = item.get('card_faces', [])
                    if faces and faces[0].get('image_uris'):
                        img = faces[0].get('image_uris', {}).get('large') or faces[0].get('image_uris', {}).get('normal')
                if img:
                    printings_list.append({
                        'set_name': item.get('set_name', 'Unknown Set'),
                        'set_code': item.get('set', '???').upper(),
                        'image': img,
                        'released_at': item.get('released_at', '9999-12-31'),
                        'artist': item.get('artist', 'Unknown Artist'),
                        'collector_number': item.get('collector_number', 'N/A')
                    })
        # Sort by released_at date ascending (oldest first)
        printings_list.sort(key=lambda x: x['released_at'])
    except Exception as e:
        print(f"Warning: failed to fetch prints from Scryfall: {e}")

    # Fallback to current card image if fetch fails or returns empty
    if not printings_list:
        printings_list = [{
            'set_name': set_name,
            'set_code': set_code,
            'image': image_url,
            'released_at': released_at,
            'artist': artist,
            'collector_number': collector_num
        }]
    else:
        # Override initial page image with the oldest printing image
        image_url = printings_list[0]['image']

    import json
    # Export all metadata keys to clean_printings JSON
    clean_printings = [{
        'set_name': p['set_name'],
        'set_code': p['set_code'],
        'image': p['image'],
        'released_at': p['released_at'],
        'artist': p['artist'],
        'collector_number': p['collector_number']
    } for p in printings_list]
    printings_json_str = json.dumps(clean_printings)

    # Read template
    template_path = "templates/card_detail.html"
    if not os.path.exists(template_path):
        print(f"Template not found at {template_path}!")
        sys.exit(1)
        
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    # Substitute values
    rendered = template_content.format(
        name=name,
        image_url=image_url,
        badges=badges_html,
        cmc=cmc,
        mana_cost=mana_cost,
        type_line=type_line,
        oracle_text=oracle_text,
        power_toughness_loyalty=pt_loyalty_html,
        color_identity=color_identity,
        keywords=keywords,
        artist=artist,
        released_at=released_at,
        legality_grid_html=legality_grid_html,
        printings_json=printings_json_str,
        printings_html=printings_html,
        rulings_html=rulings_html,
        tags_html=tags_html,
        source_fields_html=source_fields_html,
        scryfall_uri=scryfall_uri,
        ai_profile_html=ai_profile_html
    )
    
    # Write to target
    output_dir = f"public/card/{slug}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/index.html"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered)
        
    print(f"\nStatic page generated successfully for card: {name}")
    print(f"Output path: {output_path}")

if __name__ == '__main__':
    main()
