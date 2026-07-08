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

def get_image_slug(card_doc, has_faces=False):
    card_name = card_doc.get('name') or 'unknown'
    set_name = card_doc.get('set_name') or card_doc.get('set') or 'unknown'
    artist = card_doc.get('artist') or 'unknown'
    
    slug_parts = [slugify(card_name), slugify(set_name), slugify(artist)]
    slug_parts = [p for p in slug_parts if p]
    base_slug = "-".join(slug_parts)
    
    suffix = "_0" if has_faces else ""
    return f"{base_slug}{suffix}.jpg"

def generate_page(search_term=None, db=None):
    if db is None:
        db = get_mongo_db()
        
    referenced_images = {} # maps local_rel_path -> target_rel_path
    
    def add_card_images(card_doc, has_faces=False):
        card_id = card_doc.get('id')
        if not card_id:
            return
        suffix = "_0" if has_faces else ""
        slug_name = get_image_slug(card_doc, has_faces)
        referenced_images[f"public/images/normal/{card_id}{suffix}.jpg"] = f"images/normal/{slug_name}"
        referenced_images[f"public/images/large/{card_id}{suffix}.jpg"] = f"images/large/{slug_name}"
        
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
    else:
        ai_profile_html = ""
    
    # Extract card image URL (point directly to local path)
    raw_card = card.get('raw', {})
    card_faces = raw_card.get('card_faces', [])
    slug_name = get_image_slug(card, bool(card_faces))
    image_url = f"../../images/normal/{slug_name}"
    add_card_images(card, bool(card_faces))
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
        p_slug_name = get_image_slug(p_doc, bool(p_faces))
        p_image_url = f"../../images/normal/{p_slug_name}"
        p_large_image_url = f"../../images/large/{p_slug_name}"
        add_card_images(p_doc, bool(p_faces))

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

    initial_print = printings_list[0]
    initial_artist = initial_print.get('artist') or ''
    if initial_artist and re.search(r'unknown', initial_artist, re.IGNORECASE):
        initial_artist = ''
    initial_set = initial_print.get('set_name') or ''
    initial_released = initial_print.get('released_at', '')
    initial_year = initial_released.split('-')[0] if '-' in initial_released else ''
    
    alt_parts = [name]
    if initial_set:
        alt_parts.append(initial_set)
    if initial_year:
        alt_parts.append(initial_year)
    if initial_artist:
        alt_parts.append(initial_artist)
    image_alt = " | ".join(alt_parts)

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
    
    # Calculate image name for og:image
    image_filename = os.path.basename(large_image_url)
    image_abs_url = f"https://mtgabyss.com/images/large/{image_filename}"
    
    description_text = default_desc
    has_lure = False
    
    try:
        abyss_lure_doc = db["abysses"].find_one({
            "oracle_id": oracle_id
        })
        if abyss_lure_doc:
            lure_data = abyss_lure_doc.get("content", {}).get("lure", {})
            if lure_data.get("status") == "generated" and lure_data.get("text"):
                lure_text = lure_data.get("text").strip()
                collapsed_lure = " ".join(lure_text.split())
                description_text = collapsed_lure
                lure_html = f'<blockquote class="abyss-lure">{html.escape(lure_text)}</blockquote>'
                has_lure = True
    except Exception as e:
        print(f"Warning: failed to query abysses: {e}")

    escaped_desc = html.escape(description_text)
    meta_tags = f'<meta name="description" content="{escaped_desc}">'
    
    # Open Graph/Twitter descriptions only if Lure is present
    if has_lure:
        meta_tags += f'\n  <meta property="og:description" content="{escaped_desc}">\n  <meta name="twitter:description" content="{escaped_desc}">'
        
    meta_tags += f'\n  <meta property="og:image" content="{image_abs_url}">\n  <meta name="twitter:image" content="{image_abs_url}">'
    meta_tags += f'\n  <meta property="og:title" content="{html.escape(name)} | MTGAbyss">\n  <meta name="twitter:title" content="{html.escape(name)} | MTGAbyss">'

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
                if len(similar_cards) >= 35:
                    break
                cand_card = db["cards"].find_one({"oracle_id": cand_oracle_id})
                if cand_card:
                    cand_raw = cand_card.get('raw', {})
                    layout = cand_raw.get('layout', 'normal')
                    if layout in ['art_series', 'token', 'double_faced_token', 'emblem', 'planar', 'scheme', 'vanguard', 'memorabilia']:
                        continue
                        
                    cand_name = cand_card.get("name")
                    cand_slug = slugify(cand_name)
                    
                    # Extract local image URL
                    cand_faces = cand_raw.get('card_faces', [])
                    cand_slug_name = get_image_slug(cand_card, bool(cand_faces))
                    cand_image_url = f"../../images/normal/{cand_slug_name}"
                    add_card_images(cand_card, bool(cand_faces))
                            
                    cand_lure = ""
                    try:
                        cand_lure_doc = db["abysses"].find_one({"oracle_id": cand_oracle_id})
                        if cand_lure_doc:
                            l_data = cand_lure_doc.get("content", {}).get("lure", {})
                            if l_data.get("status") == "generated" and l_data.get("text"):
                                cand_lure = l_data.get("text").strip()
                    except Exception:
                        pass

                    earliest = get_earliest_printing(db, cand_oracle_id, cand_card)
                    similar_cards.append({
                        "name": cand_name,
                        "slug": cand_slug,
                        "image_url": cand_image_url,
                        "similarity": round(sim, 4),
                        "earliest_printing": earliest,
                        "lure": cand_lure
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

    # Construct rich Schema.org VisualArtwork Graph mapping all printings & similar cards
    printing_items = []
    for idx, p in enumerate(printings_list):
        p_large_filename = os.path.basename(p.get('large_image') or p['image'])
        p_image_abs = f"https://mtgabyss.com/images/large/{p_large_filename}"
        
        p_artist = p.get('artist') or ''
        if p_artist and re.search(r'unknown', p_artist, re.IGNORECASE):
            p_artist = ''
            
        p_year = p.get('released_at', '').split('-')[0] if '-' in p.get('released_at', '') else ''
        
        artwork_item = {
            "@type": "VisualArtwork",
            "name": f"{name} ({p['set_name']})",
            "image": p_image_abs,
            "artMedium": "Card Art",
            "artworkSurface": "Cardstock",
        }
        if p_artist:
            artwork_item["creator"] = {
                "@type": "Person",
                "name": p_artist
            }
        if p_year:
            artwork_item["dateCreated"] = p_year
        if p.get('set_name'):
            artwork_item["isPartOf"] = {
                "@type": "CreativeWorkSeries",
                "name": p['set_name']
            }
            
        printing_items.append({
            "@type": "ListItem",
            "position": idx + 1,
            "item": artwork_item
        })

    similar_items = []
    for idx, s in enumerate(similar_cards):
        s_large_filename = os.path.basename(s['image_url']).replace('/normal/', '/large/')
        s_image_abs = f"https://mtgabyss.com/images/large/{s_large_filename}"
        
        s_artist = s.get('earliest_printing', {}).get('artist') or ''
        if s_artist and re.search(r'unknown', s_artist, re.IGNORECASE):
            s_artist = ''
            
        s_year = s.get('earliest_printing', {}).get('released_at', '').split('-')[0] if '-' in s.get('earliest_printing', {}).get('released_at', '') else ''
        
        s_artwork = {
            "@type": "VisualArtwork",
            "name": s['name'],
            "image": s_image_abs,
            "artMedium": "Card Art",
            "artworkSurface": "Cardstock"
        }
        if s_artist:
            s_artwork["creator"] = {
                "@type": "Person",
                "name": s_artist
            }
        if s_year:
            s_artwork["dateCreated"] = s_year
        if s.get('earliest_printing', {}).get('set_name'):
            s_artwork["isPartOf"] = {
                "@type": "CreativeWorkSeries",
                "name": s['earliest_printing']['set_name']
            }
            
        similar_items.append({
            "@type": "ListItem",
            "position": idx + 1,
            "item": s_artwork
        })

    main_artist = printings_list[0].get('artist') or ''
    if main_artist and re.search(r'unknown', main_artist, re.IGNORECASE):
        main_artist = ''
        
    main_year = printings_list[0].get('released_at', '').split('-')[0] if '-' in printings_list[0].get('released_at', '') else ''
    
    main_artwork = {
        "@type": "VisualArtwork",
        "@id": f"https://mtgabyss.com/card/{slug}#artwork",
        "name": name,
        "image": image_abs_url,
        "description": description_text,
        "artMedium": "Card Art",
        "artworkSurface": "Cardstock"
    }
    if main_artist:
        main_artwork["creator"] = {
            "@type": "Person",
            "name": main_artist
        }
    if main_year:
        main_artwork["dateCreated"] = main_year

    json_ld = {
        "@context": "https://schema.org",
        "@graph": [
            main_artwork,
            {
                "@type": "ItemList",
                "@id": f"https://mtgabyss.com/card/{slug}#printings",
                "name": f"Historical printings of {name}",
                "itemListElement": printing_items
            }
        ]
    }
    if similar_items:
        json_ld["@graph"].append({
            "@type": "ItemList",
            "@id": f"https://mtgabyss.com/card/{slug}#similar",
            "name": f"Similar cards to {name}",
            "itemListElement": similar_items
        })

    json_ld_script = f'\n  <script type="application/ld+json">\n  {json.dumps(json_ld, indent=2)}\n  </script>'
    meta_tags += json_ld_script

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
        image_alt=image_alt,
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
    return slug, referenced_images

def main():
    import argparse
    import subprocess
    import os
    import tarfile
    import io
    import sys
    
    parser = argparse.ArgumentParser(description="Generate card page.")
    parser.add_argument("search_term", nargs="?", default=None, help="Name or slug of the card")
    parser.add_argument("--deploy", action="store_true", help="Upload the generated page to the VPS")
    args = parser.parse_args()
    
    result = generate_page(args.search_term)
    if not result:
        return
    slug, referenced_images = result
    
    if slug and args.deploy:
        print(f"\nDeploying card page for '{slug}' to remote server...")
        try:
            # 1. Build a tar archive in memory containing the HTML directory and images
            print("Bundling HTML and referenced images into an archive...")
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w:gz") as tar:
                # Add the card details HTML folder
                card_dir = f"public/card/{slug}"
                if os.path.exists(card_dir):
                    for root, dirs, files in os.walk(card_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, "public")
                            tar.add(file_path, arcname=arcname)
                
                # Add the referenced normal & large images
                image_count = 0
                for local_path, target_arcname in referenced_images.items():
                    if os.path.exists(local_path):
                        tar.add(local_path, arcname=target_arcname)
                        image_count += 1
            
            tar_bytes = tar_stream.getvalue()
            print(f"Archive created ({len(tar_bytes) / 1024 / 1024:.2f} MB, containing {image_count} images).")
            
            # 2. Pipe the tarball via a single SSH process (only one password prompt)
            print("Uploading archive and configuring permissions on the server...")
            remote_cmd = (
                "tar -xzf - -C /srv/www/mtgabyss.com && "
                "find /srv/www/mtgabyss.com/card /srv/www/mtgabyss.com/images -type d -exec chmod 755 {} + && "
                "find /srv/www/mtgabyss.com/card /srv/www/mtgabyss.com/images -type f -exec chmod 644 {} +"
            )
            
            ssh_proc = subprocess.Popen(
                ["ssh", "ubuntu@15.204.113.15", remote_cmd],
                stdin=subprocess.PIPE
            )
            
            # Write the tar bytes to ssh stdin and wait for completion
            ssh_proc.communicate(input=tar_bytes)
            
            if ssh_proc.returncode == 0:
                print("Deployment completed successfully!")
            else:
                print(f"Deployment failed with exit code: {ssh_proc.returncode}")
                sys.exit(ssh_proc.returncode)
                
        except Exception as e:
            print(f"Error during deployment: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()
