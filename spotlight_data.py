"""
spotlight_data.py — Curated and data-driven spotlight overlays for AvaScry Set and Artist pages.
"""

from typing import Dict, Any, Optional, List

# Curated sets with authentic editorial blurbs and card callouts
CURATED_SETS: Dict[str, Dict[str, Any]] = {
    "lea": {
        "title": "Where Magic Began",
        "blurb": "Limited Edition Alpha debuted in August 1993, launching Richard Garfield's revolutionary trading card game. Featuring the legendary Power Nine, iconic dual lands, and foundational spells that established Magic's identity for decades to come.",
        "hero_name": "Black Lotus",
        "hero_tag": "Signature Treasure",
        "supporting": [
            {"name": "Ancestral Recall", "tag": "Power Nine"},
            {"name": "Time Walk", "tag": "Power Nine"},
            {"name": "Underground Sea", "tag": "Original Dual Land"},
            {"name": "Lightning Bolt", "tag": "Core Classic"}
        ]
    },
    "arn": {
        "title": "Magic's First Expansion",
        "blurb": "Arabian Nights (December 1993) marked Magic's first standalone expansion, drawing inspiration from One Thousand and One Nights. It introduced the concept of expansion-specific mechanics, land destruction via strip mining, and exotic flavor.",
        "hero_name": "Juzám Djinn",
        "hero_tag": "Iconic Behemoth",
        "supporting": [
            {"name": "Bazaar of Baghdad", "tag": "Vintage Staple"},
            {"name": "Library of Alexandria", "tag": "Banned Powerhouse"},
            {"name": "Drop of Honey", "tag": "Reserved List"},
            {"name": "Shahrazad", "tag": "Subgame Legend"}
        ]
    },
    "rav": {
        "title": "The City of Guilds",
        "blurb": "Ravnica: City of Guilds (2005) introduced the definitive two-color guild structure that became a cornerstone of Magic design. Debuting Golgari, Dimir, Boros, and Selesnya alongside the beloved shocklands and hybrid mana.",
        "hero_name": "Dark Confidant",
        "hero_tag": "Modern Staple",
        "supporting": [
            {"name": "Overgrown Tomb", "tag": "Shockland"},
            {"name": "Watery Grave", "tag": "Shockland"},
            {"name": "Lightning Helix", "tag": "Boros Burn"},
            {"name": "Chord of Calling", "tag": "Tutor Staple"}
        ]
    },
    "isd": {
        "title": "Gothic Horror Unleashed",
        "blurb": "Innistrad (2011) redefined horror in Magic, introducing transform double-faced cards, the graveyard-fueled Morbid and Flashback mechanics, and classic horror tropes ranging from vampires and werewolves to geist hauntings.",
        "hero_name": "Liliana of the Veil",
        "hero_tag": "Modern Legend",
        "supporting": [
            {"name": "Snapcaster Mage", "tag": "Format Staple"},
            {"name": "Delver of Secrets", "tag": "Legacy All-Star"},
            {"name": "Past in Flames", "tag": "Storm Engine"},
            {"name": "Geist of Saint Traft", "tag": "Mythic Threat"}
        ]
    },
    "ths": {
        "title": "In the Shadow of Nyx",
        "blurb": "Theros (2013) brought Greek mythological flavor to life with indestructible Gods who require devotional faith to manifest as creatures, starry enchantment creatures from Nyx, and heroic monstrosities.",
        "hero_name": "Thoughtseize",
        "hero_tag": "Eternal Staple",
        "supporting": [
            {"name": "Nykthos, Shrine to Nyx", "tag": "Mana Engine"},
            {"name": "Master of Waves", "tag": "Devotion Star"},
            {"name": "Elspeth, Sun's Champion", "tag": "Mythic Hero"},
            {"name": "Thassa, God of the Sea", "tag": "Deity of the Deep"}
        ]
    },
    "mh2": {
        "title": "The Powerhouse of Modern",
        "blurb": "Modern Horizons 2 (2021) radically reshaped competitive non-rotating formats with pitch elementals, potent low-cost threats, and deep callbacks to Magic's historic design archive.",
        "hero_name": "Ragavan, Nimble Pilferer",
        "hero_tag": "Modern Menace",
        "supporting": [
            {"name": "Murktide Regent", "tag": "Dragon Staple"},
            {"name": "Solitude", "tag": "Pitch Elemental"},
            {"name": "Urza's Saga", "tag": "Enchantment Land"},
            {"name": "Fury", "tag": "Board Wipe Threat"}
        ]
    }
}

# Curated artists with authentic overviews and standout pieces
CURATED_ARTISTS: Dict[str, Dict[str, Any]] = {
    "christopher-rush": {
        "title": "Founding Visionary",
        "blurb": "One of Magic's original 25 illustrators, Christopher Rush helped define the game's earliest visual identity. He illustrated over 100 cards, including the most famous gaming artifact in existence, the Black Lotus, and designed the iconic five-color mana symbol wheel.",
        "hero_name": "Black Lotus",
        "hero_tag": "Most Famous MTG Art",
        "supporting": [
            {"name": "Lightning Bolt", "tag": "Iconic Alpha Burn"},
            {"name": "Brainstorm", "tag": "Ice Age Classic"},
            {"name": "Mana Vault", "tag": "Foundational Artifact"},
            {"name": "Sol Ring", "tag": "Vintage Classic"}
        ]
    },
    "john-avon": {
        "title": "Master of Lands & Atmosphere",
        "blurb": "Renowned across the community for his breathtaking panoramic landscapes and celestial horizons, John Avon has illustrated over 200 Magic cards. His work on Unhinged full-art basics, original Ravnica shocklands, and Mirrodin artifact lands remains legendary.",
        "hero_name": "Watery Grave",
        "hero_tag": "Original Shockland",
        "supporting": [
            {"name": "Overgrown Tomb", "tag": "Ravnica Shockland"},
            {"name": "Seat of the Synod", "tag": "Artifact Land"},
            {"name": "Lotus Field", "tag": "Pioneer Staple"},
            {"name": "Ancient Tomb", "tag": "Zendikar Expedition"}
        ]
    },
    "rebecca-guay": {
        "title": "Watercolor & Ethereal Fantasy",
        "blurb": "Celebrated for her delicate watercolor portraits, flowing line work, and renaissance-inspired fairy tale aesthetics, Rebecca Guay has contributed defining art to Magic since Alliances in 1996, creating many of the game's most cherished cards.",
        "hero_name": "Dark Ritual",
        "hero_tag": "Mercadian Masques",
        "supporting": [
            {"name": "Priest of Titania", "tag": "Urza's Saga"},
            {"name": "Bitterblossom", "tag": "Fae Staple"},
            {"name": "Path to Exile", "tag": "Modern Removal"},
            {"name": "Elvish Piper", "tag": "Classic Summoner"}
        ]
    },
    "greg-staples": {
        "title": "Dynamic Action & Iconic Beasts",
        "blurb": "Contributing powerful, dynamic character art and muscular fantasy illustrations to Magic for over two decades, Greg Staples has illustrated dozens of premier format staples, commanders, and tournament staples across major sets.",
        "hero_name": "Basking Rootwalla",
        "hero_tag": "Torment Classic",
        "supporting": [
            {"name": "Warren Instigator", "tag": "Zendikar Goblin"},
            {"name": "Tidehollow Sculler", "tag": "Shards of Alara"},
            {"name": "Scavenging Ghoul", "tag": "Dark Fantasy"},
            {"name": "Golgari Grave-Troll", "tag": "Dredge Engine"}
        ]
    }
}


def build_set_spotlight(set_code: str, set_name: str, cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a composed spotlight dictionary for a set.
    Uses curated data if present; otherwise derives an honest, factual summary from cards.
    """
    code_lower = set_code.lower()
    curated = CURATED_SETS.get(code_lower)

    # Calculate factual stats
    total_printings = len(cards)
    
    # Release years represented
    years = sorted(list({str(c.get("released_at", ""))[:4] for c in cards if c.get("released_at")}))
    release_year = years[0] if years else ""
    
    # Rarity breakdown
    rarities = {}
    for c in cards:
        r = (c.get("rarity") or "").capitalize()
        if r:
            rarities[r] = rarities.get(r, 0) + 1

    # Main card types represented
    types_count = {}
    for c in cards:
        t_line = c.get("type_line") or ""
        for t in ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Land", "Planeswalker"]:
            if t in t_line:
                types_count[t] = types_count.get(t, 0) + 1
    top_types = sorted(types_count.items(), key=lambda x: x[1], reverse=True)[:3]
    top_types_str = ", ".join(f"{t[0]}s" for t in top_types) if top_types else "Various Types"

    chips = []
    if release_year:
        chips.append({"label": f"Released {release_year}", "icon": "📅"})
    chips.append({"label": f"{total_printings} Cards", "icon": "🃏"})
    if top_types_str:
        chips.append({"label": top_types_str, "icon": "⚔️"})

    # Determine Hero and Supporting Cards
    card_by_name = {c.get("name"): c for c in cards}

    if curated:
        title = curated.get("title", f"Inside {set_name}")
        blurb = curated.get("blurb", "")
        hero_card = card_by_name.get(curated.get("hero_name"))
        hero_tag = curated.get("hero_tag", "Signature Card")

        supporting = []
        for s in curated.get("supporting", []):
            sc = card_by_name.get(s.get("name"))
            if sc:
                supporting.append({
                    "name": sc.get("name"),
                    "printing_slug": sc.get("printing_slug"),
                    "image_url": sc.get("image_url") or f"https://avascry.com/images/normal/{sc.get('image_slug')}.jpg",
                    "tag": s.get("tag", "Notable")
                })
    else:
        title = f"Inside {set_name}"
        blurb = f"{set_name} ({set_code.upper()}) features {total_printings} cards{' released in ' + release_year if release_year else ''}, highlighted by {top_types_str.lower()}."
        hero_tag = "Set Highlight"

        # Data-driven hero: pick first Mythic or Rare, or first card
        hero_card = None
        for c in cards:
            if c.get("rarity") in ("Mythic", "Rare"):
                hero_card = c
                break
        if not hero_card and cards:
            hero_card = cards[0]

        # Data-driven supporting: pick 4 other distinct cards
        supporting = []
        used_names = {hero_card.get("name")} if hero_card else set()
        for c in cards:
            c_name = c.get("name")
            if c_name not in used_names:
                used_names.add(c_name)
                supporting.append({
                    "name": c_name,
                    "printing_slug": c.get("printing_slug"),
                    "image_url": c.get("image_url") or f"https://avascry.com/images/normal/{c.get('image_slug')}.jpg",
                    "tag": c.get("rarity") or "Notable"
                })
                if len(supporting) >= 4:
                    break

    hero_data = None
    if hero_card:
        hero_data = {
            "name": hero_card.get("name"),
            "printing_slug": hero_card.get("printing_slug"),
            "image_url": hero_card.get("image_url") or f"https://avascry.com/images/normal/{hero_card.get('image_slug')}.jpg",
            "tag": hero_tag
        }

    return {
        "title": title,
        "blurb": blurb,
        "chips": chips,
        "hero": hero_data,
        "supporting": supporting
    }


def build_artist_spotlight(artist_name: str, artist_slug: str, cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a composed spotlight dictionary for an artist.
    Factual and data-driven overview of their cataloged Magic illustrations.
    """
    slug_clean = artist_slug.lower()
    curated = CURATED_ARTISTS.get(slug_clean)

    total_artworks = len(cards)
    
    # Calculate set count & active timeline
    sets_represented = list({c.get("set") for c in cards if c.get("set")})
    set_count = len(sets_represented)

    years = sorted(list({str(c.get("released_at", ""))[:4] for c in cards if c.get("released_at") and str(c.get("released_at", ""))[:4].isdigit()}))
    era_str = f"{years[0]}–{years[-1]}" if len(years) > 1 else (years[0] if years else "")

    chips = []
    chips.append({"label": f"{total_artworks} Artworks", "icon": "🎨"})
    if set_count:
        chips.append({"label": f"{set_count} Sets", "icon": "🏛️"})
    if era_str:
        chips.append({"label": f"Active {era_str}", "icon": "⏳"})

    card_by_name = {c.get("name"): c for c in cards}

    if curated:
        title = curated.get("title", f"Illustrations by {artist_name}")
        blurb = curated.get("blurb", "")
        hero_card = card_by_name.get(curated.get("hero_name"))
        hero_tag = curated.get("hero_tag", "Signature Work")

        supporting = []
        for s in curated.get("supporting", []):
            sc = card_by_name.get(s.get("name"))
            if sc:
                supporting.append({
                    "name": sc.get("name"),
                    "printing_slug": sc.get("printing_slug"),
                    "image_url": sc.get("image_url") or f"https://avascry.com/images/normal/{sc.get('image_slug')}.jpg",
                    "tag": s.get("tag", "Notable")
                })
    else:
        title = f"Illustrations by {artist_name}"
        timeline_part = f" spanning from {era_str}" if era_str else ""
        blurb = f"{artist_name} has illustrated {total_artworks} cataloged works across {set_count} Magic sets{timeline_part}."
        hero_tag = "Featured Work"

        # Data-driven hero: prioritize Rare/Mythic or earliest iconic card
        hero_card = None
        for c in cards:
            if c.get("rarity") in ("Mythic", "Rare"):
                hero_card = c
                break
        if not hero_card and cards:
            hero_card = cards[0]

        supporting = []
        used_names = {hero_card.get("name")} if hero_card else set()
        for c in cards:
            c_name = c.get("name")
            if c_name not in used_names:
                used_names.add(c_name)
                supporting.append({
                    "name": c_name,
                    "printing_slug": c.get("printing_slug"),
                    "image_url": c.get("image_url") or f"https://avascry.com/images/normal/{c.get('image_slug')}.jpg",
                    "tag": c.get("rarity") or c.get("set", "").upper()
                })
                if len(supporting) >= 4:
                    break

    hero_data = None
    if hero_card:
        hero_data = {
            "name": hero_card.get("name"),
            "printing_slug": hero_card.get("printing_slug"),
            "image_url": hero_card.get("image_url") or f"https://avascry.com/images/normal/{hero_card.get('image_slug')}.jpg",
            "tag": hero_tag
        }

    return {
        "title": title,
        "blurb": blurb,
        "chips": chips,
        "hero": hero_data,
        "supporting": supporting
    }
