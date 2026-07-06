import os
import sys
import re
import json
from db_mongo import get_mongo_db

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
    if len(sys.argv) < 2:
        print("Usage: python generate_commander.py <commander_name>")
        sys.exit(1)
        
    search_term = sys.argv[1]
    db = get_mongo_db()
    
    print(f"Searching MongoDB for card: '{search_term}'...")
    card = db["cards"].find_one({
        "$or": [
            {"name": search_term},
            {"slug": slugify(search_term)}
        ]
    })
    
    if not card:
        print(f"Error: Card '{search_term}' not found in MongoDB.")
        sys.exit(1)
        
    name = card.get('name')
    slug = slugify(name)
    oracle_id = card.get('oracle_id')
    
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

    set_name = card.get('set_name', 'Unknown')
    set_code = (card.get('set') or 'Unknown').upper()
    collector_num = card.get('collector_number') or 'N/A'
    artist = card.get('artist') or 'Unknown'
    released_at = card.get('released_at') or 'Unknown'

    # Fetch printings from Scryfall API
    printings_list = []
    try:
        import urllib.request
        import urllib.parse
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

    clean_printings = [{
        'set_name': p['set_name'],
        'set_code': p['set_code'],
        'image': p['image'],
        'released_at': p['released_at'],
        'artist': p['artist'],
        'collector_number': p['collector_number']
    } for p in printings_list]
    printings_json_str = json.dumps(clean_printings)

    # Fetch all mechanics from MongoDB mechanics collection
    mechanics_map = {}
    try:
        for doc in db["mechanics"].find({}):
            mechanics_map[doc["slug"]] = doc
    except Exception as e:
        print(f"Warning: failed to query mechanics: {e}")

    found_slugs = set()
    display_names = {}

    # 1. Use card.keywords for keyword abilities
    card_keywords = card.get('keywords', [])
    for kw in card_keywords:
        if kw:
            kw_slug = slugify(kw)
            found_slugs.add(kw_slug)
            if kw_slug in mechanics_map:
                display_names[kw_slug] = mechanics_map[kw_slug]["name"]
            else:
                display_names[kw_slug] = kw

    # 2. Scan oracle_text for keyword actions and ability words
    oracle_text = card.get('oracle_text') or ''
    if oracle_text:
        # Strip reminder text in parentheses to avoid matching keywords inside rules explanations
        clean_oracle = re.sub(r'\(.*?\)', '', oracle_text, flags=re.DOTALL)
        
        for m_slug, mech in mechanics_map.items():
            m_name = mech["name"]
            term_type = mech.get("term_type")
            
            if term_type == "keyword_action":
                pattern = r'\b' + re.escape(m_name) + r'\b'
                if re.search(pattern, clean_oracle, re.IGNORECASE):
                    found_slugs.add(m_slug)
                    display_names[m_slug] = m_name
            elif term_type == "ability_word":
                # Detect ability words when they appear in normal ability-word style (before em dash/dash)
                pattern = r'\b' + re.escape(m_name) + r'\b\s*(?:—|--)'
                if re.search(pattern, clean_oracle, re.IGNORECASE):
                    found_slugs.add(m_slug)
                    display_names[m_slug] = m_name

    # Filter out internal/useless tags
    internal_tags = {"virtual-legendary", "meme"}
    found_slugs = found_slugs - internal_tags

    # Render chips
    chips_html_list = []
    for m_slug in sorted(list(found_slugs)):
        display_name = display_names.get(m_slug, m_slug.capitalize())
        mech_doc = mechanics_map.get(m_slug)
        definition = mech_doc.get("definition") if mech_doc else None
        
        if definition and mech_doc.get("status") == "defined":
            chips_html_list.append(
                f'<span class="mechanic-chip" tabindex="0" data-tooltip="{display_name}: {definition}">{display_name}</span>'
            )
        else:
            chips_html_list.append(
                f'<span class="mechanic-chip" tabindex="0">{display_name}</span>'
            )

    if chips_html_list:
        mechanics_chips_html = '<div class="hero-card-mechanics" id="hero-card-mechanics">\n          ' + "\n          ".join(chips_html_list) + '\n        </div>'
    else:
        mechanics_chips_html = ''

    # Fetch optional commander abyss content
    abyss_html = ""
    try:
        abyss_doc = db["commander_abysses"].find_one({
            "$or": [
                {"oracle_id": oracle_id},
                {"slug": slug},
                {"name": name}
            ]
        })
        if abyss_doc:
            abyss_text = (
                abyss_doc.get("body_markdown") or 
                abyss_doc.get("text") or 
                abyss_doc.get("abyss_text") or 
                abyss_doc.get("body") or 
                abyss_doc.get("content") or 
                ""
            ).strip()
            if abyss_text:
                formatted_text = markdown_to_html(abyss_text)
                abyss_html = f'<div class="profile-pull-quote">\n          {formatted_text}\n        </div>'
    except Exception as e:
        print(f"Warning: failed to query commander_abysses: {e}")

    # Fetch Lure content from abysses collection
    lure_html = ""
    try:
        abyss_lure_doc = db["abysses"].find_one({
            "entity_type": "commander",
            "oracle_id": oracle_id
        })
        if abyss_lure_doc:
            lure_data = abyss_lure_doc.get("content", {}).get("lure", {})
            if lure_data.get("status") == "generated" and lure_data.get("text"):
                lure_text = lure_data.get("text").strip()
                lure_html = f'<p class="commander-lure">{lure_text}</p>'
    except Exception as e:
        print(f"Warning: failed to query abysses: {e}")

    # Read template
    template_path = "templates/commander_detail.html"
    if not os.path.exists(template_path):
        print(f"Template not found at {template_path}!")
        sys.exit(1)
        
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    # Substitute values
    rendered = template_content.format(
        name=name,
        image_url=image_url,
        printings_json=printings_json_str,
        mechanics_chips=mechanics_chips_html,
        abyss_html=abyss_html,
        lure_html=lure_html
    )
    
    # Write to target
    output_dir = f"dist/commanders/{slug}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/index.html"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered)
        
    # Copy site.css to dist/assets/site.css so the relative link '../../assets/site.css' works
    import shutil
    dist_assets_dir = "dist/assets"
    os.makedirs(dist_assets_dir, exist_ok=True)
    shutil.copy2("public/assets/site.css", os.path.join(dist_assets_dir, "site.css"))
        
    print(f"\nStatic page generated successfully for commander: {name}")
    print(f"Output path: {output_path}")

if __name__ == '__main__':
    main()
