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

def get_earliest_printing(db, oracle_id, fallback_card):
    return {
        'set_name': fallback_card.get('set_name', 'Unknown Set'),
        'set_code': (fallback_card.get('set') or '???').upper(),
        'released_at': fallback_card.get('released_at', 'Unknown'),
        'artist': fallback_card.get('artist', 'Unknown Artist'),
        'collector_number': fallback_card.get('collector_number', 'N/A')
    }

def generate_page(search_term=None, db=None):
    if db is None:
        db = get_mongo_db()
        
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
            return
            
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
        profile_content = markdown_to_html(ai_page.get("body_markdown", ""))
        ai_profile_html = f'<div class="profile-pull-quote">\n          {profile_content}\n        </div>'
        print(f"Found AI profile for '{name}'.")
    else:
        ai_profile_html = ""
        print(f"No AI profile found for '{name}'.")
    
    # Extract card image URL (point directly to local path)
    raw_card = card.get('raw', {})
    card_faces = raw_card.get('card_faces', [])
    if card_faces:
        image_url = f"/images/normal/{card.get('id')}_0.jpg"
    else:
        image_url = f"/images/normal/{card.get('id')}.jpg"
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
    set_name = card.get('set_name', 'Unknown')
    set_code = (card.get('set') or 'Unknown').upper()
    collector_num = card.get('collector_number') or 'N/A'
    rarity = (card.get('rarity') or 'Unknown').capitalize()
    
    # Badges formatting
    badges_list = []
    
    # 1. Card Types
    main_types = ["Legendary", "Creature", "Artifact", "Enchantment", "Instant", "Sorcery", "Land", "Planeswalker"]
    for t in main_types:
        if t in type_line:
            badges_list.append(f'<span class="badge">{t}</span>')
            
    # 2. Colors / Colorless
    color_map = {
        'W': 'White',
        'U': 'Blue',
        'B': 'Black',
        'R': 'Red',
        'G': 'Green'
    }
    colors = card.get('color_identity', [])
    if not colors:
        badges_list.append('<span class="badge">Colorless</span>')
    else:
        for c in colors:
            c_name = color_map.get(c, c)
            badges_list.append(f'<span class="badge">{c_name}</span>')

    # 3. Card Metadata (Set, Artist, Number, Rarity, Year)
    if rarity:
        badges_list.append(f'<span class="badge rarity-{rarity.lower()}">{rarity}</span>')
    if set_name:
        badges_list.append(f'<span class="badge">{set_name} ({set_code})</span>')
    if released_at and released_at != 'Unknown':
        year = released_at.split('-')[0]
        badges_list.append(f'<span class="badge">{year}</span>')
    if collector_num:
        badges_list.append(f'<span class="badge">#{collector_num}</span>')
    if artist:
        badges_list.append(f'<span class="badge">Artist: {artist}</span>')

    # 4. Reserved List & Power Nine
    if card.get('reserved'):
        badges_list.append('<span class="badge reserved">Reserved List</span>')
    if name.lower() in POWER_NINE:
        badges_list.append('<span class="badge p9">Power Nine</span>')
        
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
        tags_html = '<div class="rulings-empty">No rulings associated with this card.</div>'
        
    # Source fields
    # MongoDB docs contain standard BSON object ids and raw keys. We clean them up
    source_fields = sorted(list(card.keys()))
    if "_id" in source_fields:
        source_fields.remove("_id")
    source_fields_html = "".join([f"<div>{f}</div>" for f in source_fields])
    
    scryfall_uri = card.get('scryfall_uri') or 'https://scryfall.com'

    # Construct printings list locally (querying card_prints collection)
    printings_cursor = db["card_prints"].find({"oracle_id": oracle_id})
    printings_list = []
    
    # Sort printings by release date ascending, then base_priority descending
    p_docs = list(printings_cursor)
    p_docs.sort(key=lambda x: (x.get("released_at") or "9999-12-31", -x.get("base_priority", 0)))
    
    for p_doc in p_docs:
        p_faces = p_doc.get('card_faces') or []
        if p_faces:
            p_image_url = f"/images/normal/{p_doc['id']}_0.jpg"
            p_large_image_url = f"/images/large/{p_doc['id']}_0.jpg"
        else:
            p_image_url = f"/images/normal/{p_doc['id']}.jpg"
            p_large_image_url = f"/images/large/{p_doc['id']}.jpg"

        printings_list.append({
            'set_name': p_doc.get('set_name', 'Unknown Set'),
            'set_code': (p_doc.get('set') or '???').upper(),
            'image': p_image_url,
            'large_image': p_large_image_url,
            'released_at': p_doc.get('released_at', 'Unknown'),
            'artist': p_doc.get('artist', 'Unknown Artist'),
            'collector_number': p_doc.get('collector_number', 'N/A')
        })

    # Fallback to current card image if fetch fails or returns empty
    if not printings_list:
        printings_list = [{
            'set_name': set_name,
            'set_code': set_code,
            'image': image_url,
            'large_image': image_url.replace('/normal/', '/large/'),
            'released_at': released_at,
            'artist': artist,
            'collector_number': collector_num
        }]
    else:
        # Override initial page image with the oldest printing image
        image_url = printings_list[0]['image']

    large_image_url = printings_list[0].get('large_image', image_url.replace('/normal/', '/large/'))

    import json
    # Export all metadata keys to clean_printings JSON
    clean_printings = [{
        'set_name': p['set_name'],
        'set_code': p['set_code'],
        'image': p['image'],
        'large_image': p.get('large_image', p['image'].replace('/normal/', '/large/')),
        'released_at': p['released_at'],
        'artist': p['artist'],
        'collector_number': p['collector_number']
    } for p in printings_list]
    printings_json_str = json.dumps(clean_printings)

    import html
    # Fetch Lure content from abysses collection
    lure_html = ""
    default_desc = f"Oracle card details, rulings, legality, and all printings for {name} on MTGAbyss."
    meta_tags = f'<meta name="description" content="{html.escape(default_desc)}">'
    
    try:
        abyss_lure_doc = db["abysses"].find_one({
            "oracle_id": oracle_id
        })
        if abyss_lure_doc:
            lure_data = abyss_lure_doc.get("content", {}).get("lure", {})
            if lure_data.get("status") == "generated" and lure_data.get("text"):
                lure_text = lure_data.get("text").strip()
                collapsed_lure = " ".join(lure_text.split())
                escaped_lure = html.escape(collapsed_lure)
                
                lure_html = f'<blockquote class="abyss-lure">{html.escape(lure_text)}</blockquote>'
                meta_tags = f'<meta name="description" content="{escaped_lure}">\n  <meta property="og:description" content="{escaped_lure}">\n  <meta name="twitter:description" content="{escaped_lure}">'
    except Exception as e:
        print(f"Warning: failed to query abysses: {e}")

    # Fetch similar cards using embeddings
    similar_cards = []
    try:
        import math
        import json
        try:
            import numpy as np
            HAS_NUMPY = True
        except ImportError:
            HAS_NUMPY = False

        def get_cosine_similarity(v1, v2):
            if HAS_NUMPY:
                a = np.array(v1, dtype=np.float32)
                b = np.array(v2, dtype=np.float32)
                norm_a = np.linalg.norm(a)
                norm_b = np.linalg.norm(b)
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                return float(np.dot(a, b) / (norm_a * norm_b))
            else:
                dot_product = sum(x * y for x, y in zip(v1, v2))
                norm_a = math.sqrt(sum(x * x for x in v1))
                norm_b = math.sqrt(sum(y * y for y in v2))
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                return dot_product / (norm_a * norm_b)

        target_emb_doc = db["card_embeddings"].find_one({"oracle_id": oracle_id})
        if target_emb_doc and target_emb_doc.get("embedding"):
            target_embedding = target_emb_doc["embedding"]
            target_dim = len(target_embedding)
            
            # Fetch all candidate embeddings (excluding current card)
            all_embeddings = list(db["card_embeddings"].find(
                {"oracle_id": {"$ne": oracle_id}},
                {"oracle_id": 1, "embedding": 1}
            ))
            
            scored_candidates = []
            for emb_doc in all_embeddings:
                vector = emb_doc.get("embedding")
                if not vector or not isinstance(vector, list) or len(vector) != target_dim:
                    continue
                sim = get_cosine_similarity(target_embedding, vector)
                scored_candidates.append((sim, emb_doc["oracle_id"]))
            
            # Sort by similarity descending and pick top 3 valid standard cards
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            
            for sim, cand_oracle_id in scored_candidates:
                if len(similar_cards) >= 4:
                    break
                cand_card = db["cards"].find_one({"oracle_id": cand_oracle_id})
                if cand_card:
                    cand_raw = cand_card.get('raw', {})
                    layout = cand_raw.get('layout', 'normal')
                    if layout in ['art_series', 'token', 'double_faced_token', 'emblem', 'planar', 'scheme', 'vanguard', 'memorabilia']:
                        continue
                        
                    cand_name = cand_card.get("name")
                    cand_slug = slugify(cand_name)
                    
                    # Extract image URL
                    cand_image_url = ''
                    cand_image_uris = cand_raw.get('image_uris', {})
                    if cand_image_uris:
                        cand_image_url = cand_image_uris.get('large') or cand_image_uris.get('normal', '')
                    else:
                        cand_faces = cand_raw.get('card_faces', [])
                        if cand_faces and cand_faces[0].get('image_uris'):
                            f_uris = cand_faces[0].get('image_uris', {})
                            cand_image_url = f_uris.get('large') or f_uris.get('normal', '')
                            
                    earliest = get_earliest_printing(db, cand_oracle_id, cand_card)
                    similar_cards.append({
                        "name": cand_name,
                        "slug": cand_slug,
                        "image_url": cand_image_url,
                        "similarity": round(sim, 4),
                        "earliest_printing": earliest
                    })
    except Exception as e:
        print(f"Warning: failed to calculate similar cards: {e}")

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
        
        if definition:
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

    similar_cards_json_str = json.dumps(similar_cards)

    # Read template
    template_path = "templates/card_detail.html"
    if not os.path.exists(template_path):
        print(f"Template not found at {template_path}!")
        return
        
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    # Substitute values
    rendered = template_content.format(
        name=name,
        image_url=image_url,
        large_image_url=large_image_url,
        badges=badges_html,
        mechanics_chips=mechanics_chips_html,
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
        ai_profile_html=ai_profile_html,
        lure_html=lure_html,
        meta_tags=meta_tags,
        similar_cards_json=similar_cards_json_str
    )
    
    # Write to target
    output_dir = f"public/card/{slug}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/index.html"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered)
        
    print(f"\nStatic page generated successfully for card: {name}")
    print(f"Output path: {output_path}")

def main():
    # Check arguments
    search_term = None
    if len(sys.argv) > 1:
        search_term = sys.argv[1]
    
    generate_page(search_term)
