import os
import sys
import re
import math
import html
import json
import urllib.request
import urllib.parse
from flask import Flask, request, redirect, send_from_directory, abort

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_mongo import get_mongo_db

app = Flask(__name__)

# Cache collections in memory for performance
ALL_EMBEDDINGS = None
PRINTINGS_CACHE = {}

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

def get_image_slug(card_doc, has_faces=False):
    base_slug = card_doc.get("image_slug")
    if not base_slug:
        card_name = card_doc.get('name') or 'unknown'
        set_name = card_doc.get('set_name') or card_doc.get('set') or 'unknown'
        artist = card_doc.get('artist') or 'unknown'
        collector_number = card_doc.get('collector_number') or card_doc.get('raw', {}).get('collector_number') or ''
        
        slug_parts = [
            slugify(card_name), 
            slugify(set_name), 
            slugify(artist),
            slugify(collector_number)
        ]
        slug_parts = [p for p in slug_parts if p]
        base_slug = "-".join(slug_parts)
        
    suffix = "_0" if has_faces else ""
    return f"{base_slug}{suffix}.jpg"

def lookup_uuid_by_image_slug(db, image_slug):
    base = image_slug
    if base.endswith('.jpg'):
        base = base[:-4]
    has_faces = False
    if base.endswith('_0'):
        base = base[:-2]
        has_faces = True
        
    parts = base.split('-')
    for i in range(len(parts), 0, -1):
        candidate_slug = "-".join(parts[:i])
        card_doc = db["cards"].find_one({"slug": candidate_slug})
        if card_doc:
            oracle_id = card_doc.get("oracle_id")
            if oracle_id:
                p_docs = list(db["card_prints"].find({"oracle_id": oracle_id}))
                for p_doc in p_docs:
                    if get_image_slug(p_doc, has_faces) == image_slug:
                        return p_doc.get("id"), has_faces
            if get_image_slug(card_doc, has_faces) == image_slug:
                return card_doc.get("id"), has_faces
    return None, has_faces

def markdown_to_html(md):
    if not md:
        return ""
    html_content = md
    paragraphs = html_content.split('\n\n')
    formatted_paras = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('### '):
            p = f"<h3>{p[4:]}</h3>"
        elif p.startswith('## '):
            p = f"<h2>{p[3:]}</h2>"
        elif p.startswith('# '):
            p = f"<h1>{p[2:]}</h1>"
        else:
            p = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', p)
            p = re.sub(r'\*(.*?)\*', r'<em>\1</em>', p)
            p = f"<p>{p.replace(chr(10), '<br>')}</p>"
        formatted_paras.append(p)
    return "\n".join(formatted_paras)

def format_mana_symbols(text):
    if not text:
        return ""
    def replace_symbol(match):
        sym = match.group(1)
        clean_sym = sym.replace('/', '')
        return f'<img src="https://svgs.scryfall.io/card-symbols/{clean_sym.upper()}.svg" alt="{sym}" class="mana-symbol" style="height: 0.9em; width: 0.9em; vertical-align: middle; margin: 0 0.1em; display: inline-block;">'
    return re.sub(r'\{(.*?)\}', replace_symbol, text)

def get_earliest_printing(db, oracle_id, fallback_card):
    return {
        'set_name': fallback_card.get('set_name', 'Unknown Set'),
        'set_code': (fallback_card.get('set') or '???').upper(),
        'released_at': fallback_card.get('released_at', 'Unknown'),
        'artist': fallback_card.get('artist', 'Unknown Artist'),
        'collector_number': fallback_card.get('collector_number', 'N/A')
    }

def load_embeddings(db):
    global ALL_EMBEDDINGS
    if ALL_EMBEDDINGS is None:
        print("Loading all card embeddings into memory...")
        try:
            ALL_EMBEDDINGS = list(db["card_embeddings"].find({}, {"oracle_id": 1, "embedding": 1}))
            print(f"Loaded {len(ALL_EMBEDDINGS)} embeddings.")
        except Exception as e:
            print(f"Error loading embeddings: {e}")
            ALL_EMBEDDINGS = []
    return ALL_EMBEDDINGS

def get_cosine_similarity(v1, v2):
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_a = math.sqrt(sum(x * x for x in v1))
    norm_b = math.sqrt(sum(y * y for y in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def render_card_detail(card_slug):
    db = get_mongo_db()
    card = db["cards"].find_one({"slug": card_slug})
    if not card:
        # Try search by exact name as fallback
        card = db["cards"].find_one({"name": card_slug.replace('-', ' ')})
    
    if not card:
        abort(404, description="Card not found")

    oracle_id = card.get('oracle_id')
    
    # Prioritize this card's lure and image generation jobs
    if oracle_id:
        print(f"Prioritizing card '{card.get('name')}' (oracle_id: {oracle_id}) to priority 1000000 on visit.")
        db["cards"].update_one(
            {"oracle_id": oracle_id},
            {"$set": {"base_priority": 1000000}}
        )
        db["card_prints"].update_many(
            {"oracle_id": oracle_id},
            {"$set": {"base_priority": 1000000}}
        )
        card["base_priority"] = 1000000
    name = card.get('name')
    slug = card.get('slug') or slugify(name)
    
    # Load rulings
    rulings = list(db["rulings"].find({"oracle_id": oracle_id}).sort("published_at", 1))
    
    # Load tags
    tags = card.get("tags", [])
    
    # Extract oracle text and flavor text (including multi-faced cards support)
    raw_card = card.get('raw', {})
    oracle_text = card.get('oracle_text') or raw_card.get('oracle_text') or ''
    if not oracle_text:
        card_faces = raw_card.get('card_faces', [])
        if card_faces:
            oracle_text = "\n\n".join([face.get('oracle_text') for face in card_faces if face.get('oracle_text')])
            
    flavor_text = card.get('flavor_text') or raw_card.get('flavor_text') or ''
    if not flavor_text:
        card_faces = raw_card.get('card_faces', [])
        if card_faces:
            flavor_text = " // ".join([face.get('flavor_text') for face in card_faces if face.get('flavor_text')])
            
    # Load AI page profile
    ai_page = db["ai_pages"].find_one({
        "oracle_id": oracle_id,
        "language": "en",
        "page_type": "profile"
    })
    
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
    if rulings:
        rulings_html = "".join([f"""
        <div class="ruling-item">
          <div class="ruling-date">{r.get('published_at', '')} ({r.get('source', '').upper()})</div>
          <div>{r.get('comment', '')}</div>
        </div>
        """ for r in rulings])
    else:
        rulings_html = '<div class="rulings-empty">No rulings available.</div>'
        
    # Tags HTML
    if tags:
        tags_html = "".join([f'<span class="tag-badge" title="{t["namespace"]}">{t["tag"]}</span>' for t in tags])
    else:
        tags_html = '<div class="rulings-empty">No tags associated with this card.</div>'
        
    source_fields = sorted(list(card.keys()))
    if "_id" in source_fields:
        source_fields.remove("_id")
    source_fields_html = "".join([f"<div>{f}</div>" for f in source_fields])
    
    scryfall_uri = card.get('scryfall_uri') or 'https://scryfall.com'

    # Construct printings list locally (querying card_prints collection)
    global PRINTINGS_CACHE
    if oracle_id in PRINTINGS_CACHE:
        printings_list = PRINTINGS_CACHE[oracle_id]
    else:
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

            printings_list.append({
                'set_name': p_doc.get('set_name', 'Unknown Set'),
                'set_code': (p_doc.get('set') or '???').upper(),
                'image': p_image_url,
                'large_image': p_large_image_url,
                'released_at': p_doc.get('released_at', 'Unknown'),
                'artist': p_doc.get('artist', 'Unknown Artist'),
                'collector_number': p_doc.get('collector_number', 'N/A')
            })
        PRINTINGS_CACHE[oracle_id] = printings_list

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

    lure_html = ""
    default_desc = f"Oracle card details, rulings, legality, and all printings for {name} on MTGAbyss."
    
    # Calculate image name for og:image
    image_filename = os.path.basename(large_image_url)
    image_abs_url = f"https://mtgabyss.com/images/large/{image_filename}"
    
    description_text = default_desc
    has_lure = False
    
    try:
        abyss_lure_doc = db["abysses"].find_one({"oracle_id": oracle_id})
        if abyss_lure_doc:
            lure_data = abyss_lure_doc.get("content", {}).get("lure", {})
            if lure_data.get("status") == "generated" and lure_data.get("text"):
                lure_text = lure_data.get("text").strip()
                collapsed_lure = " ".join(lure_text.split())
                description_text = collapsed_lure
                lure_html = f'<blockquote class="abyss-lure">{html.escape(lure_text)}</blockquote>'
                has_lure = True
    except Exception as e:
        pass

    escaped_desc = html.escape(description_text)
    meta_tags = f'<meta name="description" content="{escaped_desc}">'
    
    # Open Graph/Twitter descriptions only if Lure is present
    if has_lure:
        meta_tags += f'\n  <meta property="og:description" content="{escaped_desc}">\n  <meta name="twitter:description" content="{escaped_desc}">'
        
    meta_tags += f'\n  <meta property="og:image" content="{image_abs_url}">\n  <meta name="twitter:image" content="{image_abs_url}">'
    meta_tags += f'\n  <meta property="og:title" content="{html.escape(name)} | MTGAbyss">\n  <meta name="twitter:title" content="{html.escape(name)} | MTGAbyss">'

    # Similar cards calculation
    similar_cards = []
    try:
        # Load from precalculated research_insights first
        insights = db["research_insights"].find_one({"_id": "global_insights"})
        similar_candidates = []
        if insights and "links" in insights:
            for link in insights["links"]:
                src = link.get("source")
                tgt = link.get("target")
                sim = link.get("similarity", 0.0)
                if src == oracle_id:
                    similar_candidates.append((sim, tgt))
                elif tgt == oracle_id:
                    similar_candidates.append((sim, src))
                    
        # If no precalculated insights, fall back to calculating similarities with a limit
        if not similar_candidates:
            target_emb_doc = db["card_embeddings"].find_one({"oracle_id": oracle_id})
            if target_emb_doc and target_emb_doc.get("embedding"):
                target_embedding = target_emb_doc["embedding"]
                target_dim = len(target_embedding)
                
                # Fetch a sample of 200 embeddings instead of ALL to avoid OOM / slow load
                sample_embeddings = list(db["card_embeddings"].find({}, {"oracle_id": 1, "embedding": 1}).limit(200))
                for emb_doc in sample_embeddings:
                    if emb_doc.get("oracle_id") == oracle_id:
                        continue
                    vector = emb_doc.get("embedding")
                    if not vector or len(vector) != target_dim:
                        continue
                    sim = get_cosine_similarity(target_embedding, vector)
                    similar_candidates.append((sim, emb_doc["oracle_id"]))
                    
        similar_candidates.sort(key=lambda x: x[0], reverse=True)
        similar_candidates = similar_candidates[:35]
        
        if similar_candidates:
            # Bulk query cards & abysses to avoid N+1 query problem
            cand_oracle_ids = [c[1] for c in similar_candidates]
            
            cards_cursor = db["cards"].find({"oracle_id": {"$in": cand_oracle_ids}})
            cards_by_oracle = {c["oracle_id"]: c for c in cards_cursor}
            
            abysses_cursor = db["abysses"].find({"oracle_id": {"$in": cand_oracle_ids}})
            abysses_by_oracle = {}
            for doc in abysses_cursor:
                l_text = doc.get("content", {}).get("lure", {}).get("text", "")
                if l_text:
                    abysses_by_oracle[doc["oracle_id"]] = l_text.strip()
                    
            for sim, cand_oracle_id in similar_candidates:
                cand_card = cards_by_oracle.get(cand_oracle_id)
                if not cand_card:
                    continue
                    
                cand_raw = cand_card.get('raw', {})
                layout = cand_raw.get('layout', 'normal')
                if layout in ['art_series', 'token', 'double_faced_token', 'emblem', 'planar', 'scheme', 'vanguard', 'memorabilia']:
                    continue
                    
                cand_name = cand_card.get("name")
                cand_slug = slugify(cand_name)
                
                cand_image_url = ''
                cand_image_uris = cand_raw.get('image_uris', {})
                if cand_image_uris:
                    cand_image_url = cand_image_uris.get('large') or cand_image_uris.get('normal', '')
                else:
                    cand_faces = cand_raw.get('card_faces', [])
                    if cand_faces and cand_faces[0].get('image_uris'):
                        f_uris = cand_faces[0].get('image_uris', {})
                        cand_image_url = f_uris.get('large') or f_uris.get('normal', '')
                        
                cand_lure = abysses_by_oracle.get(cand_oracle_id, "")
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
        print(f"Error calculating similar cards: {e}")

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
    template_path = os.path.join(os.path.dirname(__file__), "templates", "card_detail.html")
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
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
    return rendered

@app.route('/research')
def research_dashboard():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "research.html")
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Research dashboard template not found!", 404

@app.route('/api/research')
def api_research():
    db = get_mongo_db()
    insights = db["research_insights"].find_one({"_id": "global_insights"})
    if not insights:
        return {"error": "Insights data not generated yet. Please run abyss_walker/walker.py first."}, 404
    
    # Format datetime for JSON serialization
    if "stats" in insights and "updated_at" in insights["stats"]:
        insights["stats"]["updated_at"] = insights["stats"]["updated_at"].isoformat()
    
    # Remove _id
    if "_id" in insights:
        del insights["_id"]
        
    return insights

@app.route('/')
@app.route('/index.html')
def home():
    public_index = os.path.join(os.path.dirname(__file__), "public", "index.html")
    if os.path.exists(public_index):
        with open(public_index, 'r', encoding='utf-8') as f:
            return f.read()
    return "MTGAbyss Homepage placeholder. Run generate_homepage.py first!"

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), "public", "assets"), filename)

@app.route('/images/<size>/<filename>')
def serve_card_images(size, filename):
    public_path = os.path.join(os.path.dirname(__file__), "public", "images", size)
    if os.path.exists(os.path.join(public_path, filename)):
        return send_from_directory(public_path, filename)
    data_path = os.path.join(os.path.dirname(__file__), "data", "images", size)
    if os.path.exists(os.path.join(data_path, filename)):
        return send_from_directory(data_path, filename)
        
    # If not found directly, try lookup by slugified image name
    db = get_mongo_db()
    card_id, has_faces = lookup_uuid_by_image_slug(db, filename)
    if card_id:
        suffix = "_0" if has_faces else ""
        uuid_filename = f"{card_id}{suffix}.jpg"
        if os.path.exists(os.path.join(public_path, uuid_filename)):
            return send_from_directory(public_path, uuid_filename)
        if os.path.exists(os.path.join(data_path, uuid_filename)):
            return send_from_directory(data_path, uuid_filename)
            
    return abort(404)

@app.route('/data/images/<size>/<filename>')
def serve_data_card_images(size, filename):
    data_path = os.path.join(os.path.dirname(__file__), "data", "images", size)
    return send_from_directory(data_path, filename)

@app.route('/card/<slug>/index.html')
@app.route('/card/<slug>/')
@app.route('/card/<slug>')
def card_detail(slug):
    try:
        return render_card_detail(slug)
    except Exception as e:
        import traceback
        traceback.print_exc()
        abort(500, description=str(e))

@app.route('/search.html')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect('/')
    
    db = get_mongo_db()
    slug = slugify(query)
    
    # 1. Exact or Slug Match
    card = db["cards"].find_one({
        "$or": [
            {"name": {"$regex": f"^{re.escape(query)}$", "$options": "i"}},
            {"slug": slug}
        ]
    })
    if card:
        return redirect(f'/card/{card.get("slug")}/index.html')
        
    # 2. Search matches
    matches = list(db["cards"].find(
        {"name": {"$regex": re.escape(query), "$options": "i"}},
        {"name": 1, "slug": 1}
    ).limit(50))
    
    match_list_html = ""
    if matches:
        match_list_html = '<ul style="list-style: none; padding: 0; margin-top: 2rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem;">'
        for m in matches:
            match_list_html += f'<li><a href="/card/{m["slug"]}/index.html" class="homepage-example-pill" style="display: block; text-decoration: none; text-align: center; margin: 0; width: auto;">{m["name"]}</a></li>'
        match_list_html += '</ul>'
    else:
        match_list_html = '<div style="margin-top: 2rem; color: var(--abyss-muted);">No cards found matching your query.</div>'
        
    template_path = os.path.join(os.path.dirname(__file__), "public", "search.html")
    if not os.path.exists(template_path):
        template_content = "<h1>Search Results</h1><div id='search-query-display'></div><div id='results'></div>"
    else:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
            
    rendered = template_content.replace(
        '<div class="search-query-display" id="search-query-display">...</div>',
        f'<div class="search-query-display" id="search-query-display">{html.escape(query)}</div>\n{match_list_html}'
    )
    return rendered

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting MTGAbyss preview server on http://localhost:{port}")
    db = get_mongo_db()
    
    # Preloading embeddings disabled to save RAM and speed up startup on Pi
    pass
        
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
