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
          value="<!-- SEARCH_VALUE_PLACEHOLDER -->"
          required
          autocomplete="off"
        >
        <button type="submit" class="homepage-search-btn">Search</button>
      </form>
      
      <div class="homepage-examples">
        <div class="homepage-examples-label" style="text-align: center; margin-top: 1.5rem;">Try searching for:</div>
        <div class="homepage-examples-list" style="display: flex; flex-direction: row; flex-wrap: wrap; justify-content: center; gap: 0.5rem; margin-top: 0.75rem;">
<!-- CARD_PILLS_PLACEHOLDER -->
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
  <header class="site-header">
    <a class="site-logo" href="index.html">MTGAbyss</a>
  </header>

  <div class="page-wrapper">
    <div class="container">
      <main class="search-results-panel">
        <h1 style="margin-top: 0; font-family: 'Outfit', sans-serif;">Search Results</h1>
        <div id="loading-indicator" style="color: var(--abyss-muted); margin-bottom: 1.5rem;">Searching card database...</div>
        
        <div style="margin-top: 1.5rem;">
          <div>Search query:</div>
          <div class="search-query-display" id="search-query-display">...</div>
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
              .replace(/[^a-z0-9\s-]/g, '')
              .replace(/[\s-]+/g, '-')
              .replace(/^-+|-+$/g, '');
    }

    document.addEventListener('DOMContentLoaded', () => {
      const params = new URLSearchParams(window.location.search);
      const query = params.get('q') || '';
      const displayEl = document.getElementById('search-query-display');
      displayEl.textContent = query;

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
            
            let html = `<p style="color: var(--abyss-muted); margin-bottom: 1.5rem;">No exact match found. Showing top ${displayMatches.length} matching cards:</p>`;
            html += '<ul style="list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem;">';
            for (const m of displayMatches) {
              html += `<li><a href="card/${m.slug}/" class="homepage-example-pill" style="display: block; text-decoration: none; text-align: center; margin: 0; width: auto; font-family: 'Outfit', sans-serif;">${m.name}</a></li>`;
            }
            html += '</ul>';
            resultsContainer.innerHTML = html;
          } else {
            resultsContainer.innerHTML = '<div style="color: var(--abyss-muted);">No cards found matching your query.</div>';
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
    # Fetch 6 random cards from MongoDB
    card_names = []
    db = None
    try:
        from db_mongo import get_mongo_db
        db = get_mongo_db()
        random_cards = list(db["cards"].aggregate([{"$sample": {"size": 6}}]))
        card_names = [c.get("name") for c in random_cards if c.get("name")]
    except Exception as e:
        print(f"Warning: failed to query cards from MongoDB ({e}). Using fallbacks.")
    
    # Pad with fallbacks if needed
    fallbacks = ["Black Lotus", "Sol Ring", "Lightning Bolt", "Counterspell", "Colossal Dreadmaw", "Ancestral Recall"]
    for f in fallbacks:
        if len(card_names) >= 6:
            break
        if f not in card_names:
            card_names.append(f)
    card_names = card_names[:6]

    prepopulated_name = card_names[0] if card_names else ""
    pill_names = card_names[1:]

    # Generate HTML for the pills
    pills_html = ""
    for name in pill_names:
        pills_html += f'          <button type="button" class="homepage-example-pill" data-query="{name}" style="text-align: center;">{name}</button>\n'

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
