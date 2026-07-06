import os
import sys
import re
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db, ensure_indexes

def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

TERM_TYPE_MAPPING = {
    "keyword-abilities": "keyword_ability",
    "keyword-actions": "keyword_action",
    "ability-words": "ability_word"
}

SEEDS = {
    "Flying": (
        "This creature can’t be blocked except by creatures with flying or reach.",
        "Can’t be blocked except by flying or reach."
    ),
    "Vigilance": (
        "Attacking doesn’t cause this creature to tap.",
        "Attacking doesn’t cause this creature to tap."
    ),
    "Deathtouch": (
        "Any amount of damage this deals to a creature is enough to destroy it.",
        "Any amount of damage this deals to a creature is enough to destroy it."
    ),
    "Lifelink": (
        "Damage dealt by this creature also causes its controller to gain that much life.",
        "Damage dealt by this creature also causes its controller to gain that much life."
    ),
    "Proliferate": (
        "Choose any number of permanents and/or players with counters, then give each another counter of a kind already there.",
        "Choose any number of permanents and/or players with counters, then give each another counter of a kind already there."
    ),
    "Haste": (
        "This creature can attack and tap as soon as it comes under your control.",
        "This creature can attack and tap as soon as it comes under your control."
    ),
    "Trample": (
        "This creature can deal excess combat damage to the player, planeswalker, or battle it’s attacking.",
        "This creature can deal excess combat damage to the player, planeswalker, or battle it’s attacking."
    ),
    "Reach": (
        "This creature can block creatures with flying.",
        "This creature can block creatures with flying."
    ),
    "First strike": (
        "This creature deals combat damage before creatures without first strike.",
        "This creature deals combat damage before creatures without first strike."
    ),
    "Double strike": (
        "This creature deals both first-strike and regular combat damage.",
        "This creature deals both first-strike and regular combat damage."
    ),
    "Menace": (
        "This creature can’t be blocked except by two or more creatures.",
        "This creature can’t be blocked except by two or more creatures."
    ),
    "Hexproof": (
        "This permanent can’t be the target of spells or abilities your opponents control.",
        "This permanent can’t be the target of spells or abilities your opponents control."
    ),
    "Indestructible": (
        "Effects that say “destroy” don’t destroy this permanent, and lethal damage doesn’t destroy it.",
        "Effects that say “destroy” don’t destroy this permanent, and lethal damage doesn’t destroy it."
    ),
    "Defender": (
        "This creature can’t attack.",
        "This creature can’t attack."
    ),
    "Flash": (
        "You may cast this spell any time you could cast an instant.",
        "You may cast this spell any time you could cast an instant."
    ),
    "Ward": (
        "Whenever this permanent becomes the target of a spell or ability an opponent controls, counter it unless that player pays the ward cost.",
        "Whenever this permanent becomes the target of a spell or ability an opponent controls, counter it unless that player pays the ward cost."
    ),
    "Scry": (
        "Look at cards from the top of your library, then put any number on the bottom and the rest on top in any order.",
        "Look at cards from the top of your library, then put any number on the bottom and the rest on top in any order."
    ),
    "Surveil": (
        "Look at cards from the top of your library, then put any number into your graveyard and the rest on top in any order.",
        "Look at cards from the top of your library, then put any number into your graveyard and the rest on top in any order."
    ),
    "Investigate": (
        "Create a Clue token.",
        "Create a Clue token."
    ),
    "Connive": (
        "Draw a card, then discard a card. If you discarded a nonland card, put a +1/+1 counter on that creature.",
        "Draw a card, then discard a card. If you discarded a nonland card, put a +1/+1 counter on that creature."
    ),
    "Explore": (
        "Reveal the top card of your library. Put it into your hand if it’s a land. Otherwise, put a +1/+1 counter on the creature, then put the card back or into your graveyard.",
        "Reveal the top card of your library. Put it into your hand if it’s a land. Otherwise, put a +1/+1 counter on the creature, then put the card back or into your graveyard."
    )
}

def main():
    db = get_mongo_db()
    ensure_indexes(db)
    
    print("Building mechanics collection from scryfall_catalogs...")
    
    # Query the scryfall_catalogs for the three keys
    catalogs = db["scryfall_catalogs"].find({
        "catalog_key": {"$in": list(TERM_TYPE_MAPPING.keys())}
    })
    
    # Keep track of counts for report
    upserted_count = 0
    defined_count = 0
    needs_def_count = 0
    
    # Create normalized mechanics
    for cat_doc in catalogs:
        source_catalog = cat_doc.get("catalog_key")
        term_type = TERM_TYPE_MAPPING[source_catalog]
        data = cat_doc.get("data", [])
        
        for name in data:
            slug = slugify(name)
            if not slug:
                continue
            
            # Check if this mechanic already exists
            existing = db["mechanics"].find_one({"slug": slug})
            
            # Seed value matching (case-insensitive name check or matching slug)
            seed_match = None
            for seed_name, (defn, short_defn) in SEEDS.items():
                if slugify(seed_name) == slug:
                    seed_match = (seed_name, defn, short_defn)
                    break
            
            now = datetime.now(timezone.utc)
            
            if existing:
                # Update existing doc: preserve existing definition if it has one
                has_definition = existing.get("definition") is not None
                
                new_doc = {
                    "name": existing.get("name", name),
                    "slug": slug,
                    "term_type": term_type,
                    "source_catalog": source_catalog,
                    "updated_at": now
                }
                
                if has_definition:
                    # Keep existing definition/short_definition/status/source
                    new_doc["definition"] = existing.get("definition")
                    new_doc["short_definition"] = existing.get("short_definition")
                    new_doc["status"] = existing.get("status", "defined")
                    new_doc["source"] = existing.get("source", "existing")
                    new_doc["created_at"] = existing.get("created_at", now)
                    if new_doc["status"] == "defined":
                        defined_count += 1
                    else:
                        needs_def_count += 1
                else:
                    # If it was empty but has a seed definition now, apply it
                    if seed_match:
                        seed_name, defn, short_defn = seed_match
                        new_doc["name"] = seed_name
                        new_doc["definition"] = defn
                        new_doc["short_definition"] = short_defn
                        new_doc["status"] = "defined"
                        new_doc["source"] = "scryfall_catalog_plus_local_definition_seed"
                        defined_count += 1
                    else:
                        new_doc["definition"] = None
                        new_doc["short_definition"] = None
                        new_doc["status"] = "needs_definition"
                        new_doc["source"] = "scryfall_catalog"
                        needs_def_count += 1
                    new_doc["created_at"] = existing.get("created_at", now)
                
                db["mechanics"].replace_one({"slug": slug}, new_doc)
                upserted_count += 1
            else:
                # Create a new document
                new_doc = {
                    "slug": slug,
                    "term_type": term_type,
                    "source_catalog": source_catalog,
                    "created_at": now,
                    "updated_at": now
                }
                
                if seed_match:
                    seed_name, defn, short_defn = seed_match
                    new_doc["name"] = seed_name
                    new_doc["definition"] = defn
                    new_doc["short_definition"] = short_defn
                    new_doc["status"] = "defined"
                    new_doc["source"] = "scryfall_catalog_plus_local_definition_seed"
                    defined_count += 1
                else:
                    new_doc["name"] = name
                    new_doc["definition"] = None
                    new_doc["short_definition"] = None
                    new_doc["status"] = "needs_definition"
                    new_doc["source"] = "scryfall_catalog"
                    needs_def_count += 1
                
                db["mechanics"].replace_one({"slug": slug}, new_doc, upsert=True)
                upserted_count += 1
                
    print(f"Build complete.")
    print(f"Mechanics upserted count: {upserted_count}")
    print(f"Defined count: {defined_count}")
    print(f"Needs_definition count: {needs_def_count}")

if __name__ == "__main__":
    main()
