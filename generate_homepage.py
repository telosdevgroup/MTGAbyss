import os
import shutil
import re

def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def get_scryfall_image_url(card_doc):
    raw = card_doc.get("raw", {})
    if not raw:
        return None
    image_uris = raw.get("image_uris")
    if image_uris and isinstance(image_uris, dict):
        return image_uris.get("normal") or image_uris.get("small")
    
    card_faces = raw.get("card_faces")
    if card_faces and isinstance(card_faces, list) and len(card_faces) > 0:
        face_uris = card_faces[0].get("image_uris")
        if face_uris and isinstance(face_uris, dict):
            return face_uris.get("normal") or face_uris.get("small")
            
    return None

HOMEPAGE_TEMPLATE = """<!DOCTYPE html>
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
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-837M1ZGHPE"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());

    gtag('config', 'G-837M1ZGHPE');
  </script>
  <!-- Microsoft Clarity -->
  <script type="text/javascript">
      (function(c,l,a,r,i,t,y){
          c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
          t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
          y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
      })(window, document, "clarity", "script", "xj4uzg0vsb");
  </script>
</head>
<body>
  <header class="site-header">
    <a class="site-logo" href="index.html">MTGAbyss</a>
    <nav>
      <a href="cards/">Cards</a>
    </nav>
  </header>

  <div class="homepage-wrapper">
    <div class="homepage-panel" style="max-width: 850px !important; margin: 0 auto;">
      <div class="homepage-brand">MTGAbyss</div>
      <div class="homepage-subtitle">What do you seek?</div>
      <div class="homepage-tagline">A bottomless archive of Magic: The Gathering. Where the cards gaze back.</div>
      
      <form class="homepage-search-form" id="search-form" action="search.html" method="get">
        <input 
          type="text" 
          name="q" 
          id="search-input" 
          class="homepage-search-input" 
          placeholder="Black Lotus" 
          value="<!-- SEARCH_VALUE_PLACEHOLDER -->"
          required
          autocomplete="off"
        >
        <button type="submit" class="homepage-search-btn">Search</button>
      </form>
      
      <div class="homepage-examples">
        <div class="homepage-examples-label">Try searching for:</div>
        <div class="homepage-examples-list" style="display: flex !important; flex-direction: row !important; justify-content: center !important; align-items: center !important; gap: 1rem !important; flex-wrap: nowrap !important; margin-top: 1rem !important; width: 100% !important;">
<!-- CARD_PILLS_PLACEHOLDER -->
        </div>
      </div>
    </div>
  </div>

  <script>
    document.addEventListener('DOMContentLoaded', () => {
      const searchForm = document.getElementById('search-form');
      const searchInput = document.getElementById('search-input');
      const pills = document.querySelectorAll('.homepage-example-pill-img');

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

SEARCH_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Search Results | MTGAbyss</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/site.css">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-837M1ZGHPE"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());

    gtag('config', 'G-837M1ZGHPE');
  </script>
  <!-- Microsoft Clarity -->
  <script type="text/javascript">
      (function(c,l,a,r,i,t,y){
          c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
          t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
          y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
      })(window, document, "clarity", "script", "xj4uzg0vsb");
  </script>
</head>
<body>
  <header class="site-header search-page-header">
    <a class="site-logo" href="index.html">MTGAbyss</a>
    <form class="header-search-form" id="header-search-form" action="search.html" method="get">
      <input 
        type="text" 
        name="q" 
        id="header-search-input" 
        class="header-search-input" 
        placeholder="Search cards..." 
        required
        autocomplete="off"
      >
      <button type="submit" class="header-search-btn">Search</button>
    </form>
  </header>

  <div class="page-wrapper">
    <div class="container">
      <main class="search-results-panel">
        <h1 style="margin-top: 0; font-family: 'Outfit', sans-serif;">Search Results</h1>
        <div id="loading-indicator" style="color: var(--abyss-muted); margin-bottom: 1.5rem;">Searching card database...</div>
        
        <div style="margin-top: 1.5rem; display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;">
          <span style="font-weight: 500;">Search query:</span>
          <span class="search-query-display" id="search-query-display">...</span>
        </div>

        <div id="results-container" style="margin-top: 2rem;"></div>

        <div style="margin-top: 2.5rem;">
          <a href="index.html" class="homepage-search-btn" style="text-decoration: none; display: inline-block;">&larr; Back to Search</a>
        </div>
      </main>
    </div>
  </div>

  <script>
    function slugify(s) {
      if (!s) return "";
      return s.toLowerCase()
              .replace(/[^a-z0-9\\s-]/g, '')
              .replace(/[\\s-]+/g, '-')
              .replace(/^-+|-+$/g, '');
    }

    document.addEventListener('DOMContentLoaded', () => {
      const params = new URLSearchParams(window.location.search);
      const query = params.get('q') || '';
      const displayEl = document.getElementById('search-query-display');
      displayEl.textContent = query;

      const headerInput = document.getElementById('header-search-input');
      if (headerInput) {
        headerInput.value = query;
      }

      const cleanQuery = query.trim();
      if (!cleanQuery) {
        document.getElementById('loading-indicator').textContent = 'No search query provided.';
        return;
      }

      const querySlug = slugify(cleanQuery);

      fetch('search-index.json')
        .then(response => response.json())
        .then(index => {
          // index is {"Utopia Sprawl": "utopia-sprawl", ...}
          let exactMatchSlug = null;
          const queryLower = cleanQuery.toLowerCase();
          
          for (const [name, slug] of Object.entries(index)) {
            if (name.toLowerCase() === queryLower || slug === querySlug) {
              exactMatchSlug = slug;
              break;
            }
          }

          if (exactMatchSlug) {
            document.getElementById('loading-indicator').textContent = 'Found exact match! Redirecting...';
            window.location.href = `card/${exactMatchSlug}/`;
            return;
          }

          // Prefix / substring search
          const matches = [];
          for (const [name, slug] of Object.entries(index)) {
            const nameLower = name.toLowerCase();
            if (nameLower.startsWith(queryLower)) {
              matches.push({ name, slug, score: 2 });
            } else if (nameLower.includes(queryLower)) {
              matches.push({ name, slug, score: 1 });
            }
          }

          matches.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));

          const resultsContainer = document.getElementById('results-container');
          document.getElementById('loading-indicator').style.display = 'none';

          if (matches.length > 0) {
            const limit = 50;
            const displayMatches = matches.slice(0, limit);
            
            let html = `
              <div class="search-info-bar">
                <span class="search-count">Found <strong>${matches.length}</strong> matches</span>
                <span class="search-limit">(showing top ${displayMatches.length})</span>
              </div>
              <div class="search-results-grid">
            `;
            for (const m of displayMatches) {
              html += `
                <a href="card/${m.slug}/" class="search-result-card">
                  <div class="search-result-content">
                    <span class="search-result-icon">✦</span>
                    <span class="search-result-name">${m.name}</span>
                  </div>
                  <span class="search-result-action">View details &rarr;</span>
                </a>
              `;
            }
            html += '</div>';
            resultsContainer.innerHTML = html;
          } else {
            resultsContainer.innerHTML = '<div style="color: var(--abyss-muted); padding: 2rem 0; text-align: center;">No cards found matching your query.</div>';
          }
        })
        .catch(err => {
          console.error(err);
          document.getElementById('loading-indicator').textContent = 'Error loading search index.';
        });
    });
  </script>
</body>
</html>
"""

def main():
    import json
    pill_cards = []
    db = None
    try:
        from db_mongo import get_mongo_db
        db = get_mongo_db()
        
        # Fetch 6 random cards with images for the pills/examples
        pill_docs = list(db["cards"].aggregate([
            {"$match": {
                "$and": [
                    {"name": {"$exists": True, "$ne": ""}},
                    {"$or": [
                        {"raw.image_uris": {"$exists": True}},
                        {"raw.card_faces": {"$exists": True}}
                    ]}
                ]
            }},
            {"$sample": {"size": 6}}
        ]))
        for c in pill_docs:
            scryfall_url = get_scryfall_image_url(c)
            if scryfall_url:
                pill_cards.append({
                    "name": c.get("name"),
                    "image_url": scryfall_url
                })
    except Exception as e:
        print(f"Warning: failed to query cards from MongoDB ({e}). Using fallbacks.")
    
    # Pad pill_cards with fallbacks if needed
    fallbacks = [
        {"name": "Black Lotus", "image_url": "https://cards.scryfall.io/normal/front/b/d/bd8fa256-3535-4c46-bc3c-dcee457519ab.jpg"},
        {"name": "Sol Ring", "image_url": "https://cards.scryfall.io/normal/front/c/c/cc999776-251d-4a35-ae80-5b82eb15fcff.jpg"},
        {"name": "Lightning Bolt", "image_url": "https://cards.scryfall.io/normal/front/f/2/f2bb4783-bdce-2647-4531-838d-4a5748266376.jpg"},
        {"name": "Counterspell", "image_url": "https://cards.scryfall.io/normal/front/a/c/ac1c5cff-e579-432a-bcee-864b12eb0558.jpg"},
        {"name": "Colossal Dreadmaw", "image_url": "https://cards.scryfall.io/normal/front/8/0/8059d092-2c7d-4c61-af55-8942107a7c1f.jpg"},
        {"name": "Ancestral Recall", "image_url": "https://cards.scryfall.io/normal/front/7/b/7b9edea9-96eb-4146-8922-fbefdb8d57af.jpg"}
    ]
    for f in fallbacks:
        if len(pill_cards) >= 6:
            break
        if not any(c["name"] == f["name"] for c in pill_cards):
            pill_cards.append(f)
    pill_cards = pill_cards[:6]

    prepopulated_name = pill_cards[0]["name"] if pill_cards else ""
    pill_examples = pill_cards[1:]

    # Generate HTML for the pills (small CDN thumbnail images with inline styling)
    pills_html = ""
    for card in pill_examples:
        pills_html += f'          <img class="homepage-example-pill-img" data-query="{card["name"]}" src="{card["image_url"]}" alt="{card["name"]}" title="Click to search {card["name"]}" style="width: 150px !important; height: 210px !important; object-fit: contain; border-radius: 6px; cursor: pointer; border: 1.5px solid var(--abyss-border); transition: transform 0.2s;">\n'

    rendered_homepage = HOMEPAGE_TEMPLATE.replace("<!-- CARD_PILLS_PLACEHOLDER -->", pills_html.rstrip())
    rendered_homepage = rendered_homepage.replace("<!-- SEARCH_VALUE_PLACEHOLDER -->", prepopulated_name)

    # Generate search-index.json mapping name to slug
    search_index = {}
    if db is not None:
        try:
            print("Generating search-index.json from MongoDB...")
            all_cards = list(db["cards"].find({}, {"name": 1, "slug": 1}))
            for c in all_cards:
                name = c.get("name")
                slug = c.get("slug") or slugify(name)
                if name:
                    search_index[name] = slug
            print(f"Index built with {len(search_index):,} cards.")
        except Exception as e:
            print(f"Warning: failed to generate search index: {e}")

    # Targets
    targets = ["dist", "public"]
    
    for target in targets:
        os.makedirs(target, exist_ok=True)
        
        # Write index.html
        index_path = os.path.join(target, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(rendered_homepage)
        print(f"Generated: {index_path}")
        
        # Write search.html
        search_path = os.path.join(target, "search.html")
        with open(search_path, "w", encoding="utf-8") as f:
            f.write(SEARCH_TEMPLATE)
        print(f"Generated: {search_path}")

        # Write search-index.json
        index_file_path = os.path.join(target, "search-index.json")
        with open(index_file_path, "w", encoding="utf-8") as f:
            json.dump(search_index, f, indent=2)
        print(f"Generated: {index_file_path}")
        
        # Copy assets
        assets_dir = os.path.join(target, "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        src_css = "public/assets/site.css"
        dst_css = os.path.join(assets_dir, "site.css")
        
        if os.path.abspath(src_css) != os.path.abspath(dst_css) and os.path.exists(src_css):
            shutil.copy2(src_css, dst_css)
            print(f"Copied CSS to: {dst_css}")

    print("Homepage generation completed successfully.")

if __name__ == "__main__":
    main()
