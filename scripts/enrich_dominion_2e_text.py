"""
Enrich Dominion 2nd Edition Card Versions with Modern Official Rules Text.
Queries Dominion Strategy Wiki Cargo / Module data for canonical 2E wording
(e.g., 'in hand' instead of 'in his hand', optional 'You may' clauses, coin formatting)
and updates MongoDB 'avascry_dominion' card_versions collection.
"""

import os
import re
import json
import urllib.request
import urllib.parse
from pymongo import MongoClient

def clean_wiki_text(raw: str) -> str:
    t = raw.replace("|", "")
    
    # Coin tokens: +[2] -> +2 Coins, [3] -> 3 Coins
    def replace_coin(match):
        prefix = match.group(1) or ""
        num = match.group(2)
        if prefix:
            return f"+{num} Coins"
        return f"{num} Coins"

    t = re.sub(r'(\+)?\[(\d+)\]', replace_coin, t)
    
    # Replace 3 or more slashes (paragraph break / divider) with <n>
    t = re.sub(r'/{3,}', '<n>', t)
    
    # Replace 1 or 2 slashes (line wrap) with space
    t = re.sub(r'/{1,2}', ' ', t)
    
    # Clean multiple spaces
    t = re.sub(r'[ \t]+', ' ', t)
    
    # Strip spaces around <n>
    t = re.sub(r'\s*<n>\s*', '<n>', t)
    
    return t.strip()

def fetch_wiki_modules(card_names: list[str]) -> dict[str, str]:
    """Fetch text.en for a batch of card names using MediaWiki multi-title query."""
    results = {}
    if not card_names:
        return results

    titles = "|".join([f"Module:{name}" for name in card_names])
    params = {
        "action": "query",
        "titles": titles,
        "prop": "revisions",
        "rvslots": "main",
        "rvprop": "content",
        "format": "json"
    }
    url = "https://dominionstrategy.miraheze.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "AvaScry-Enricher/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                title = pdata.get("title", "")
                if not title.startswith("Module:"):
                    continue
                c_name = title[len("Module:"):]
                revs = pdata.get("revisions", [])
                if not revs:
                    continue
                wt = revs[0].get("slots", {}).get("main", {}).get("*", "")
                m = re.search(r'text\s*=\s*\{[^}]*?en\s*=\s*"([^"]+)"', wt, re.DOTALL)
                if m:
                    results[c_name] = clean_wiki_text(m.group(1))
    except Exception as e:
        print(f"Error fetching batch: {e}")
    return results

def main():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri)
    db = client["avascry_dominion"]

    # Identify all cards that have a 2e version
    v_2e_cards = list(db.card_versions.find({"edition": "2e"}))
    card_ids = sorted(list(set(v["card_id"] for v in v_2e_cards)))
    print(f"Found {len(card_ids)} unique cards with 2E versions.")

    card_map = {}
    for cid in card_ids:
        c = db.cards.find_one({"_id": cid}, {"name": 1, "slug": 1})
        if c:
            # Normalize card name for wiki (e.g. Harem / Farm -> Harem, etc.)
            wname = c["name"].split(" / ")[0].strip()
            card_map[c["name"]] = {"cid": cid, "wiki_name": wname, "slug": c["slug"]}

    all_names = list(card_map.keys())
    batch_size = 25
    updated_count = 0
    diff_with_1e = 0

    print(f"Fetching official 2E texts from Dominion Strategy Wiki...")
    for i in range(0, len(all_names), batch_size):
        chunk = all_names[i:i + batch_size]
        wiki_names = [card_map[n]["wiki_name"] for n in chunk]
        fetched = fetch_wiki_modules(wiki_names)

        for name in chunk:
            wname = card_map[name]["wiki_name"]
            cid = card_map[name]["cid"]
            if wname in fetched:
                new_text = fetched[wname]
                # Check current 1e text
                v_1e = db.card_versions.find_one({"card_id": cid, "edition": "1e"})
                old_1e_text = v_1e.get("printed_rules_text", "") if v_1e else ""

                # Update 2e versions
                res = db.card_versions.update_many(
                    {"card_id": cid, "edition": "2e"},
                    {"$set": {"printed_rules_text": new_text}}
                )
                if res.modified_count > 0:
                    updated_count += res.modified_count
                    if old_1e_text and old_1e_text != new_text:
                        diff_with_1e += 1
                        print(f"  [DIFF] {name}:")
                        print(f"    1E: {old_1e_text[:70]}...")
                        print(f"    2E: {new_text[:70]}...")

    print("\n" + "=" * 50)
    print(f"Enrichment Complete!")
    print(f"2E Version Documents Updated: {updated_count}")
    print(f"Cards with Active 1E vs 2E Diff: {diff_with_1e}")

if __name__ == "__main__":
    main()
