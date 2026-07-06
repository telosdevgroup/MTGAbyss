import os
import shutil

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

def main():
    # Fetch 5 random cards from MongoDB
    card_names = []
    try:
        from db_mongo import get_mongo_db
        db = get_mongo_db()
        random_cards = list(db["cards"].aggregate([{"$sample": {"size": 5}}]))
        card_names = [c.get("name") for c in random_cards if c.get("name")]
    except Exception as e:
        print(f"Warning: failed to query cards from MongoDB ({e}). Using fallbacks.")
    
    # Pad with fallbacks if needed
    fallbacks = ["Black Lotus", "Sol Ring", "Lightning Bolt", "Counterspell", "Colossal Dreadmaw"]
    for f in fallbacks:
        if len(card_names) >= 5:
            break
        if f not in card_names:
            card_names.append(f)
    card_names = card_names[:5]

    # Generate HTML for the pills
    pills_html = ""
    for name in card_names:
        pills_html += f'          <button type="button" class="homepage-example-pill" data-query="{name}" style="text-align: center;">{name}</button>\n'

    rendered_homepage = HOMEPAGE_TEMPLATE.replace("<!-- CARD_PILLS_PLACEHOLDER -->", pills_html.rstrip())

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
