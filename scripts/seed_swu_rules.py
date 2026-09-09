"""
Seeds official Star Wars: Unlimited keywords, mechanics, Comprehensive Rules entries,
and indexes card rulings into dedicated collections in MongoDB 'avascry_swu'.
"""

import os
import re
from pymongo import MongoClient, ASCENDING

SWU_KEYWORDS = [
    {
        "slug": "sentinel",
        "name": "Sentinel",
        "category": "Keyword Ability",
        "rules_section": "7.5.11",
        "introduced_in": "SOR",
        "reminder_text": "Units in this arena can't attack your non-Sentinel units or your base.",
        "summary": "Protective ability that forces enemy units in the same arena to attack the Sentinel unit before attacking other friendly units or your base.",
        "comprehensive_text": "7.5.11 Sentinel: While a player controls a unit with Sentinel in an arena, enemy units in that arena cannot choose to attack the player's base or non-Sentinel friendly units in that arena. If a player controls multiple units with Sentinel in an arena, the opponent may choose which Sentinel unit to attack."
    },
    {
        "slug": "smuggle",
        "name": "Smuggle",
        "category": "Keyword Ability",
        "rules_section": "7.5.15",
        "introduced_in": "SHD",
        "reminder_text": "You may play this card from your resources for its Smuggle cost. If you do, replace it with the top card of your deck as a resource.",
        "summary": "Allows playing a card directly from your resource row, immediately replenishing the resource with the top card of your deck.",
        "comprehensive_text": "7.5.15 Smuggle [Cost]: While a card with Smuggle is face-down in a player's resource row, that player may play the card by paying its specified Smuggle cost rather than its printed resource cost. When a card is played via Smuggle, the player immediately takes the top card of their deck and places it into their resource row face-down and exhausted."
    },
    {
        "slug": "bounty",
        "name": "Bounty",
        "category": "Keyword Ability",
        "rules_section": "7.5.13",
        "introduced_in": "SHD",
        "reminder_text": "When this unit is defeated or captured, its opponent collects its Bounty.",
        "summary": "Triggered ability placed on enemy or friendly units that awards rewards (cards, resources, damage) to the opponent when the unit is defeated or captured.",
        "comprehensive_text": "7.5.13 Bounty: A keyword that represents a triggered ability on a unit. When a unit with Bounty is defeated or captured, its opponent resolves the effect following the Bounty keyword. The opponent is considered the controller of the Bounty ability."
    },
    {
        "slug": "piloting",
        "name": "Piloting",
        "category": "Keyword Ability",
        "rules_section": "7.5.18",
        "introduced_in": "JTL",
        "reminder_text": "You may play this unit as an upgrade on a friendly Vehicle unit in the same or any arena.",
        "summary": "Allows unit cards with Piloting to be deployed either as standalone combatants or attached to friendly Vehicles as stat-boosting pilot upgrades.",
        "comprehensive_text": "7.5.18 Piloting: A card with Piloting may be played as an Upgrade attached to a friendly Vehicle unit. While attached as a pilot, the card is treated as an Upgrade and not a Unit. If the host Vehicle is defeated, the attached pilot upgrade is also defeated unless specified otherwise."
    },
    {
        "slug": "indirect-damage",
        "name": "Indirect Damage",
        "category": "Game Mechanic",
        "rules_section": "8.3.4",
        "introduced_in": "JTL",
        "reminder_text": "The affected player divides this damage among units they control and their base as they choose.",
        "summary": "Special non-targeted damage distributed among a player's units and/or base by the defending player.",
        "comprehensive_text": "8.3.4 Indirect Damage: When an effect deals Indirect Damage to a player, that player chooses how to assign and distribute the full amount of damage among their own units and their base. Indirect Damage is not dealt simultaneously with combat attack damage."
    },
    {
        "slug": "ambush",
        "name": "Ambush",
        "category": "Keyword Ability",
        "rules_section": "7.5.1",
        "introduced_in": "SOR",
        "reminder_text": "After this unit is played, you may ready it and attack an enemy unit.",
        "summary": "Enables an entering unit to ready immediately and initiate an attack against an opposing enemy unit in its arena.",
        "comprehensive_text": "7.5.1 Ambush: After a unit with Ambush enters play from being played, its controller may ready the unit. If they do, that unit immediately initiates an attack against an eligible enemy unit in its arena. This attack follows all standard combat timing rules."
    },
    {
        "slug": "overwhelm",
        "name": "Overwhelm",
        "category": "Keyword Ability",
        "rules_section": "7.5.7",
        "introduced_in": "SOR",
        "reminder_text": "When attacking an enemy unit, deal excess combat damage to the opponent's base.",
        "summary": "Trample-style combat effect where combat damage exceeding the defender's remaining HP is dealt directly to the enemy base.",
        "comprehensive_text": "7.5.7 Overwhelm: While attacking an enemy unit, any combat damage dealt by the attacker in excess of the defending unit's remaining hit points is dealt to the defending player's base."
    },
    {
        "slug": "raid",
        "name": "Raid",
        "category": "Keyword Ability",
        "rules_section": "7.5.9",
        "introduced_in": "SOR",
        "reminder_text": "While attacking, this unit gets +X power.",
        "summary": "Offensive stat bonus granting extra power exclusively while the unit is declared as an attacker.",
        "comprehensive_text": "7.5.9 Raid X: While a unit with Raid X is attacking, it gets +X Power. This bonus applies only during attack resolution and does not modify the unit's power when defending."
    },
    {
        "slug": "restore",
        "name": "Restore",
        "category": "Keyword Ability",
        "rules_section": "7.5.10",
        "introduced_in": "SOR",
        "reminder_text": "When this unit attacks, heal X damage from your base.",
        "summary": "Triggers upon attack initiation to remove damage counters from the controlling player's base.",
        "comprehensive_text": "7.5.10 Restore X: When a unit with Restore X attacks, its controller immediately heals X damage from their base."
    },
    {
        "slug": "grit",
        "name": "Grit",
        "category": "Keyword Ability",
        "rules_section": "7.5.4",
        "introduced_in": "SOR",
        "reminder_text": "This unit gets +1/+0 for each damage on it.",
        "summary": "Passive aggressive mechanic increasing a unit's attack power proportional to the amount of damage counters on it.",
        "comprehensive_text": "7.5.4 Grit: A static ability. This unit gets +1 Power for each damage counter currently placed on it."
    },
    {
        "slug": "shielded",
        "name": "Shielded",
        "category": "Keyword Ability",
        "rules_section": "7.5.12",
        "introduced_in": "SOR",
        "reminder_text": "When this unit enters play, give a Shield token to it.",
        "summary": "Enters the battlefield protected by a damage-absorbing Shield token.",
        "comprehensive_text": "7.5.12 Shielded: When a card with Shielded enters play, its controller immediately gives a Shield token to it. If the unit would take damage, defeat the Shield token instead."
    },
    {
        "slug": "coordinate",
        "name": "Coordinate",
        "category": "Keyword Ability",
        "rules_section": "7.5.16",
        "introduced_in": "TWI",
        "reminder_text": "While you control 3 or more units, this ability is active.",
        "summary": "Swarm synergy mechanic that unlocks additional passive, triggered, or stat benefits while controlling a board of 3+ units.",
        "comprehensive_text": "7.5.16 Coordinate: A conditional ability that is active only while its controller controls 3 or more units across all arenas."
    },
    {
        "slug": "exploit",
        "name": "Exploit",
        "category": "Keyword Ability",
        "rules_section": "7.5.17",
        "introduced_in": "TWI",
        "reminder_text": "For each unit you defeat when playing this card, its cost is reduced by 2.",
        "summary": "Sacrifice mechanic enabling players to defeat friendly units to discount the resource cost of powerful boss units.",
        "comprehensive_text": "7.5.17 Exploit X: When playing a card with Exploit X, the player may defeat up to X units they control. For each unit defeated this way, reduce the card's cost by 2 resources."
    },
    {
        "slug": "saboteur",
        "name": "Saboteur",
        "category": "Keyword Ability",
        "rules_section": "7.5.8",
        "introduced_in": "SOR",
        "reminder_text": "When this unit attacks, ignore Sentinel and defeat all Shield tokens on the defender.",
        "summary": "Infiltration ability that bypasses enemy Sentinel units and defeats all Shield tokens on the defending unit before damage is dealt.",
        "comprehensive_text": "7.5.8 Saboteur: When an attacker with Saboteur attacks, it ignores the Sentinel ability of any enemy units in that arena. Additionally, when a unit with Saboteur attacks an enemy unit that has one or more Shield tokens attached, all Shield tokens on the defender are defeated before combat damage is dealt."
    },
    {
        "slug": "capture",
        "name": "Capture",
        "category": "Keyword Action",
        "rules_section": "7.6.2",
        "introduced_in": "SHD",
        "reminder_text": "Place an enemy non-leader unit face-down under this unit as a captured card.",
        "summary": "Imprisonment action where a guarding unit holds an enemy unit face-down beneath it until the guarding unit leaves play.",
        "comprehensive_text": "7.6.2 Capture: An instruction to take an enemy non-leader unit from play, exhaust it, and place it face-down under the guarding unit. The captured unit loses all upgrades and tokens. When the guarding unit leaves play, all captured cards under it are rescued: flipped face-up and returned to their owner's arena exhausted."
    },
    {
        "slug": "experience",
        "name": "Experience",
        "category": "Token Upgrade",
        "rules_section": "7.5.3",
        "introduced_in": "SOR",
        "reminder_text": "Give an Experience token to a unit (+1/+0 and +0/+1).",
        "summary": "Stat-boosting token upgrade granting +1 Power and +1 HP to the attached friendly or enemy unit.",
        "comprehensive_text": "7.5.3 Experience: An Experience token is a token upgrade that gives the attached unit +1/+1 (+1 Power and +1 HP). Any number of Experience tokens may be attached to a single unit."
    },
    {
        "slug": "shield",
        "name": "Shield",
        "category": "Token Upgrade",
        "rules_section": "7.5.12",
        "introduced_in": "SOR",
        "reminder_text": "If attached unit would take damage, defeat this Shield instead.",
        "summary": "Protective token upgrade that completely absorbs the next instance of damage the host unit would receive.",
        "comprehensive_text": "7.5.12 Shield: A Shield token is a token upgrade attached to a unit. While attached, if the host unit would be dealt damage from an attack or ability, defeat one Shield token on the unit instead of dealing that damage."
    }
]

SWU_RULES_SECTIONS = [
    {
        "section": "1.1",
        "section_slug": "1-1",
        "chapter": "1. Game Overview & Objects",
        "title": "Arenas: Ground and Space",
        "text": "1.1.1 The play area is divided into two distinct combat arenas: Ground Arena and Space Arena. Ground units may only be played into and interact with the Ground Arena. Space units may only be played into and interact with the Space Arena unless explicitly specified."
    },
    {
        "section": "3.2",
        "section_slug": "3-2",
        "chapter": "3. Action Phase & Turn Structure",
        "title": "Taking Actions & The Initiative",
        "text": "3.2.1 Players alternate taking single actions during the Action Phase. Available actions include: Playing a Card, Attacking with a Unit, Using an Action Ability, Taking the Initiative, or Passing. When a player takes the Initiative, they claim the Initiative token and must pass for the remainder of the Action Phase."
    },
    {
        "section": "4.1",
        "section_slug": "4-1",
        "chapter": "4. Leader Deployment & Epic Actions",
        "title": "Leader Deployment Timing",
        "text": "4.1.1 Each player begins the game with one Leader card face-up in their leader zone. Each leader has an Epic Action that allows it to deploy as a Unit once per game once a threshold of resources is reached. When deployed, flip the leader to its Unit side, ready it, and move it to the indicated arena."
    },
    {
        "section": "5.3",
        "section_slug": "5-3",
        "chapter": "5. Combat & Attack Timing",
        "title": "Attack Steps & Damage Resolution",
        "text": "5.3.1 An attack consists of four sequential steps: Declare Attack (exhaust attacking unit, choose target), On Attack Triggers (resolve attacker abilities), Deal Combat Damage (simultaneous damage between attacker and defender), and Complete Attack ('After completing an attack' triggers)."
    },
    {
        "section": "7.5.1",
        "section_slug": "7-5-1",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Ambush",
        "text": "7.5.1 After a unit with Ambush enters play from being played, its controller may ready the unit. If they do, that unit immediately initiates an attack against an eligible enemy unit in its arena."
    },
    {
        "section": "7.5.7",
        "section_slug": "7-5-7",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Overwhelm",
        "text": "7.5.7 While attacking an enemy unit, any combat damage dealt by the attacker in excess of the defending unit's remaining hit points is dealt to the defending player's base."
    },
    {
        "section": "7.5.11",
        "section_slug": "7-5-11",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Sentinel",
        "text": "7.5.11 While a player controls a unit with Sentinel in an arena, enemy units in that arena cannot choose to attack the player's base or non-Sentinel friendly units in that arena."
    },
    {
        "section": "7.5.13",
        "section_slug": "7-5-13",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Bounty",
        "text": "7.5.13 When a unit with Bounty is defeated or captured, its opponent resolves the effect following the Bounty keyword. The opponent is considered the controller of the Bounty ability."
    },
    {
        "section": "7.5.15",
        "section_slug": "7-5-15",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Smuggle",
        "text": "7.5.15 While a card with Smuggle is face-down in a player's resource row, that player may play the card by paying its specified Smuggle cost. The player immediately replaces it with the top card of their deck as an exhausted resource."
    },
    {
        "section": "7.5.18",
        "section_slug": "7-5-18",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Piloting",
        "text": "7.5.18 A card with Piloting may be played as an Upgrade attached to a friendly Vehicle unit. While attached as a pilot, the card is treated as an Upgrade and not a Unit."
    },
    {
        "section": "8.3.4",
        "section_slug": "8-3-4",
        "chapter": "8. Damage & Defeat",
        "title": "Indirect Damage",
        "text": "8.3.4 When an effect deals Indirect Damage to a player, that player chooses how to assign and distribute the full amount of damage among their own units and their base."
    },
    {
        "section": "7.5.8",
        "section_slug": "7-5-8",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Saboteur",
        "text": "7.5.8 When an attacker with Saboteur attacks, it ignores Sentinel and defeats all Shield tokens on the defender before combat damage is dealt."
    },
    {
        "section": "7.6.2",
        "section_slug": "7-6-2",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Capture",
        "text": "7.6.2 An instruction to exhaust an enemy non-leader unit and place it face-down under the guarding unit. Rescued when the guarding unit leaves play."
    },
    {
        "section": "7.5.3",
        "section_slug": "7-5-3",
        "chapter": "7. Keywords and Named Abilities",
        "title": "Experience",
        "text": "7.5.3 An Experience token is a token upgrade that gives the attached unit +1/+1 (+1 Power and +1 HP)."
    }
]

def slugify(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def seed_rules_and_keywords(mongo_uri: str = "mongodb://localhost:27017"):
    client = MongoClient(mongo_uri)
    db = client["avascry_swu"]

    print("Seeding SWU Keywords & Mechanics...")
    db.keywords.create_index([("slug", ASCENDING)], unique=True)
    for kw in SWU_KEYWORDS:
        db.keywords.update_one({"slug": kw["slug"]}, {"$set": kw}, upsert=True)
    print(f"Upserted {len(SWU_KEYWORDS)} keywords into avascry_swu.keywords.")

    print("Seeding Comprehensive Rules entries...")
    db.rules_entries.create_index([("section_slug", ASCENDING)], unique=True)
    db.rules_entries.create_index([("slug", ASCENDING)])
    for rule in SWU_RULES_SECTIONS:
        rule_copy = dict(rule)
        rule_copy["slug"] = f"{rule['section'].replace('.', '-')}-{slugify(rule['title'])}"
        rule_copy["section_id"] = rule["section"]
        rule_copy["content"] = rule["text"]
        db.rules_entries.update_one({"section_slug": rule["section_slug"]}, {"$set": rule_copy}, upsert=True)
    print(f"Upserted {len(SWU_RULES_SECTIONS)} rules entries into avascry_swu.rules_entries.")

    print("Indexing official card clarifications into avascry_swu.clarifications...")
    db.clarifications.create_index([("slug", ASCENDING)], unique=True)
    db.clarifications.create_index([("card_slug", ASCENDING)])

    cards_with_rules = list(db.cards.find({"rules": {"$ne": None}}))
    indexed_rulings = 0

    for card in cards_with_rules:
        raw_rules = card.get("rules", "").strip()
        if not raw_rules:
            continue

        # Split multiple bullet points / paragraphs if present
        paragraphs = [p.strip() for p in raw_rules.split("\n") if p.strip()]
        for idx, para in enumerate(paragraphs):
            # Clean up curly quotes or weird encoding
            clean_para = para.strip().replace("’", "'").replace("“", '"').replace("”", '"')
            # Create deterministic slug
            card_slug = card.get("slug")
            ruling_slug = f"{card_slug}-ruling-{idx + 1}" if len(paragraphs) > 1 else f"{card_slug}-ruling"
            
            # Associate keyword if mentioned in ruling or card text
            matched_keywords = [
                kw["slug"] for kw in SWU_KEYWORDS 
                if kw["name"].lower() in clean_para.lower() or kw["name"].lower() in (card.get("text") or "").lower()
            ]

            card_set = card.get("expansion", {}).get("code") if isinstance(card.get("expansion"), dict) else card.get("set_code")
            card_num = card.get("card_number") or card.get("number")

            clarification_doc = {
                "slug": ruling_slug,
                "card_slug": card_slug,
                "card_title": card.get("title") or card.get("name"),
                "card_set": card_set or "SOR",
                "card_number": card_num or "",
                "question": f"How does {card.get('title') or card.get('name')} work according to official rulings?",
                "answer": clean_para,
                "ruling_text": clean_para,
                "keywords": matched_keywords,
                "source": "Official Fantasy Flight Games Rulings & Errata Document",
                "authority": "official",
                "status": "current"
            }

            db.clarifications.update_one({"slug": ruling_slug}, {"$set": clarification_doc}, upsert=True)
            indexed_rulings += 1

    print(f"Successfully indexed {indexed_rulings} official clarifications into avascry_swu.clarifications!")

if __name__ == "__main__":
    seed_rules_and_keywords()
