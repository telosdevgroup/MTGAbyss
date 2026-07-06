import os
import sys
import re
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

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

def determine_eligible_sections(card):
    sections = ["abyss_profile"]
    type_line = card.get("type_line", "") or ""
    name_lower = (card.get("name", "") or "").lower()
    
    if "Legendary" in type_line and "Creature" in type_line:
        sections.append("commander_voice")
        
    is_power_nine = name_lower in POWER_NINE
    is_artifact = "Artifact" in type_line
    is_restricted = card.get("legalities", {}).get("vintage") == "restricted"
    if is_artifact and (is_power_nine or is_restricted):
        sections.append("relic_profile")
        
    if is_restricted or is_power_nine or name_lower == "library of alexandria" or name_lower == "bazaar of baghdad":
        sections.append("vintage_table_read")
        
    return sections

def get_default_persona(section_type):
    if section_type == "commander_voice":
        return "commander"
    elif section_type == "relic_profile":
        return "archivist"
    elif section_type == "vintage_table_read":
        return "vintage_pro"
    return "abyss_scholar"

def markdown_to_html(md):
    if not md:
        return ""
    html = md
    paragraphs = html.split('\n\n')
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

def build_card_html(card, sections):
    # Format facts box
    name = card.get("name")
    mana_cost = card.get("mana_cost") or "None"
    type_line = card.get("type_line") or "Unknown"
    oracle_text = card.get("oracle_text") or ""
    color_identity = ", ".join(card.get("color_identity", [])) or "Colorless"
    keywords = ", ".join(card.get("keywords", [])) or "None"
    artist = card.get("artist") or "Unknown"
    released_at = card.get("released_at") or "Unknown"
    scryfall_uri = card.get("scryfall_uri") or "https://scryfall.com"
    cmc = card.get("cmc", 0.0)

    # Format badges
    badges = []
    vintage_leg = card.get("legalities", {}).get("vintage", "not_legal")
    if vintage_leg == "restricted":
        badges.append('<span class="badge restricted">Vintage: Restricted</span>')
    elif vintage_leg == "banned":
        badges.append('<span class="badge banned">Vintage: Banned</span>')
    elif vintage_leg == "legal":
        badges.append('<span class="badge legal">Vintage: Legal</span>')
    else:
        badges.append('<span class="badge">Vintage: Not Legal</span>')

    badges.append(f'<span class="badge">Mana Value: {cmc}</span>')
    if card.get("reserved"):
        badges.append('<span class="badge reserved">Reserved List</span>')
    if name.lower() in POWER_NINE:
        badges.append('<span class="badge p9">Power Nine</span>')
    
    badges_html = "\n".join(badges)

    # Look for vignette or hook section
    vignette_sec = next((s for s in sections if s.get("section_type") == "vignette_experiment"), None)
    hook_sec = next((s for s in sections if s.get("section_type") == "hook"), None)
    
    hook_html = ""
    if vignette_sec and vignette_sec.get("content"):
        text = vignette_sec["content"].get("text", "")
        hook_html = f"""
        <section class="panel section-panel profile-panel" style="margin-bottom: 1.5rem;">
          <h2 class="panel-title">Vignette</h2>
          <div class="profile-content">
            <p style="font-size: 1.25rem; font-style: italic; color: #fff; line-height: 1.6; white-space: pre-wrap;">{text}</p>
          </div>
        </section>
        """
    elif hook_sec and hook_sec.get("content"):
        text = hook_sec["content"].get("text", "")
        is_mock = hook_sec.get("model") == "mock-model" or "mock" in str(text).lower()
        is_failed = hook_sec.get("quality") == "needs_regeneration"

        badge_html = ""
        if is_mock:
            badge_html += ' <span class="badge" style="background-color: var(--border-color); color: var(--text-secondary); margin-left: 0.5rem; vertical-align: middle;">Mock</span>'
        if is_failed:
            badge_html += ' <span class="badge restricted" style="margin-left: 0.5rem; vertical-align: middle;">Needs Regeneration</span>'

        hook_html = f"""
        <section class="panel section-panel profile-panel" style="margin-bottom: 1.5rem;">
          <h2 class="panel-title">Hook{badge_html}</h2>
          <div class="profile-content">
            <p style="font-size: 1.25rem; font-style: italic; color: #fff; line-height: 1.6;">{text}</p>
          </div>
        </section>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} | MTGAbyss</title>
  <link rel="stylesheet" href="../../assets/site.css">
</head>
<body>
  <div class="container">
    <header>
      <div class="header-main">
        <h1>{name}</h1>
        <div class="badges-row">
          {badges_html}
        </div>
      </div>
    </header>

    <!-- Hook Block -->
    {hook_html}

    <!-- Source Facts Box -->
    <main class="database-layout">
      <section class="panel rules-panel">
        <h2 class="panel-title">Rules & Text</h2>
        <div class="field-row">
          <span class="field-label">Mana Cost</span>
          <span class="field-value mana-cost">{mana_cost}</span>
        </div>
        <div class="field-row">
          <span class="field-label">Type Line</span>
          <span class="field-value type-line">{type_line}</span>
        </div>
        <div class="oracle-text-box">{oracle_text}</div>
      </section>

      <section class="panel facts-panel">
        <h2 class="panel-title">Source Facts</h2>
        <div class="field-row">
          <span class="field-label">Color Identity</span>
          <span class="field-value">{color_identity}</span>
        </div>
        <div class="field-row">
          <span class="field-label">Keywords</span>
          <span class="field-value">{keywords}</span>
        </div>
        <div class="field-row">
          <span class="field-label">Artist</span>
          <span class="field-value">{artist}</span>
        </div>
        <div class="field-row">
          <span class="field-label">First Released</span>
          <span class="field-value">{released_at}</span>
        </div>
      </section>
    </main>

    <footer>
      <p>Card data compiled from local Scryfall bulk data files. All AI-generated prose is creative commentary and fan analysis.</p>
      <p><a href="{scryfall_uri}" target="_blank" rel="noopener noreferrer">View on Scryfall &rarr;</a></p>
    </footer>
  </div>
</body>
</html>
"""
    return html_content

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Fallback for older python versions if any

    import argparse
    parser = argparse.ArgumentParser(description="Build static text-only HTML pages.")
    parser.add_argument("--all", action="store_true", help="Build pages for all cards in the database.")
    parser.add_argument("--card", type=str, default=None, help="Name or slug of a specific card to build.")
    args = parser.parse_args()

    db = get_mongo_db()
    ensure_indexes(db)

    now = datetime.datetime.now(datetime.timezone.utc)
    
    # Save build run info
    run_id = db["build_runs"].insert_one({
        "started_at": now,
        "status": "running"
    }).inserted_id

    # Filter cards based on arguments
    if args.card:
        cards = list(db["cards"].find({
            "$or": [
                {"name": args.card},
                {"slug": slugify(args.card)}
            ]
        }))
        print(f"Filtering build to card: '{args.card}' (Found {len(cards)} matching cards)")
    elif not args.all:
        # Default: compile only cards that have at least one entry in generated_sections
        oracle_ids = db["generated_sections"].distinct("oracle_id")
        cards = list(db["cards"].find({"oracle_id": {"$in": oracle_ids}}))
        print(f"Compiling pages only for {len(cards)} cards with generated sections...")
    else:
        cards = list(db["cards"].find({}))
        print(f"Compiling pages for all {len(cards)} cards...")

    pages_generated = 0

    for card in cards:
        oracle_id = card.get("oracle_id")
        slug = card.get("slug") or slugify(card.get("name"))
        if not slug:
            continue

        # Get all sections for this card
        sections = list(db["generated_sections"].find({
            "oracle_id": oracle_id
        }))

        html = build_card_html(card, sections)

        output_dir = f"public/cards/{slug}"
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = f"{output_dir}/index.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        
        pages_generated += 1
        print(f"Generated page for card: {card.get('name')} -> {output_file}")

    db["build_runs"].update_one(
        {"_id": run_id},
        {"$set": {"status": "completed", "completed_at": datetime.datetime.now(datetime.timezone.utc), "pages_generated": pages_generated}}
    )
    print(f"Compilation finished. Total pages generated: {pages_generated}")

if __name__ == "__main__":
    main()
