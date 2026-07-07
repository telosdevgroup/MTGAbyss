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
    if card_faces:
        image_url = f"/images/normal/{card.get('id')}_0.jpg"
    else:
        image_url = f"/images/normal/{card.get('id')}.jpg"

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
    meta_tags = f'<meta name="description" content="{html.escape(default_desc)}">'
    
    try:
        abyss_lure_doc = db["abysses"].find_one({"oracle_id": oracle_id})
        if abyss_lure_doc:
            lure_data = abyss_lure_doc.get("content", {}).get("lure", {})
            if lure_data.get("status") == "generated" and lure_data.get("text"):
                lure_text = lure_data.get("text").strip()
                collapsed_lure = " ".join(lure_text.split())
                escaped_lure = html.escape(collapsed_lure)
                lure_html = f'<blockquote class="abyss-lure">{html.escape(lure_text)}</blockquote>'
                meta_tags = f'<meta name="description" content="{escaped_lure}">\n  <meta property="og:description" content="{escaped_lure}">\n  <meta name="twitter:description" content="{escaped_lure}">'
    except Exception as e:
        pass

    # Similar cards calculation
    similar_cards = []
    try:
        target_emb_doc = db["card_embeddings"].find_one({"oracle_id": oracle_id})
        if target_emb_doc and target_emb_doc.get("embedding"):
            target_embedding = target_emb_doc["embedding"]
            target_dim = len(target_embedding)
            
            embeddings = load_embeddings(db)
            scored_candidates = []
            for emb_doc in embeddings:
                if emb_doc.get("oracle_id") == oracle_id:
                    continue
                vector = emb_doc.get("embedding")
                if not vector or len(vector) != target_dim:
                    continue
                sim = get_cosine_similarity(target_embedding, vector)
                scored_candidates.append((sim, emb_doc["oracle_id"]))
            
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
                    
                    cand_image_url = ''
                    cand_image_uris = cand_raw.get('image_uris', {})
                    if cand_image_uris:
                        cand_image_url = cand_image_uris.get('large') or cand_image_uris.get('normal', '')
                    else:
                        cand_faces = cand_raw.get('card_faces', [])
                        if cand_faces and cand_faces[0].get('image_uris'):
                            f_uris = cand_faces[0].get('image_uris', {})
                            cand_image_url = f_uris.get('large') or f_uris.get('normal', '')
                            
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

    # Read template
    template_path = os.path.join(os.path.dirname(__file__), "templates", "card_detail.html")
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
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
    return rendered

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
    return send_from_directory(data_path, filename)

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
    
    # Only load embeddings in the main worker process to prevent double loading
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        import threading
        threading.Thread(target=load_embeddings, args=(db,), daemon=True).start()
        
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
