"""
seed_necromunda.py — Seeds MongoDB with curated, structured Necromunda Underhive data:
- necro_weapons: Comprehensive armory (Las, Bolt, Plasma, Flame, Solid Shot, Heavy, Melee)
- necro_traits: Full trait definitions & special rules
- necro_houses: The Core Clan Houses & Outlaw gangs
- necro_skills: Primary & secondary skill trees
"""

import sys
import os
from db_mongo import get_mongo_db

def seed_necromunda():
    client = get_mongo_db().client
    db = client["avascry_necromunda"]

    print("[Necromunda Seeder] Initializing database 'avascry_necromunda'...")

    # 1. TRAITS
    traits = [
        {
            "name": "Plentiful",
            "slug": "plentiful",
            "category": "Ammo",
            "summary": "Free reload without rolling an Ammo check.",
            "rules_text": "A weapon with the Plentiful trait can be reloaded without rolling an Ammo check. A fighter simply takes a Reload (Simple) action and the weapon is instantly reloaded.",
            "faq": "Hot-shot las packs remove the Plentiful trait from standard lasguns."
        },
        {
            "name": "Hot-shot",
            "slug": "hot-shot",
            "category": "Power",
            "summary": "Supercharged las capacitor adding +1 Strength and -1 AP, but reduces ammo reliability.",
            "rules_text": "The weapon has had its power conduits boosted. It loses the Plentiful trait and has a more volatile 4+ ammo check.",
            "faq": "Counts as a weapon accessory and permanently modifies the profile."
        },
        {
            "name": "Rapid Fire (1)",
            "slug": "rapid-fire-1",
            "category": "Shooting",
            "summary": "Roll a Firepower dice; each bullet symbol yields an additional hit.",
            "rules_text": "When firing with a weapon with the Rapid Fire (X) trait, roll a Firepower dice. The number of bullet symbols rolled determines the number of additional hits scored, up to a maximum of X. Hits may be allocated to the original target or other targets within 3\".",
            "faq": "If an Ammo symbol is rolled alongside bullets, the hits still count before an Ammo check is made."
        },
        {
            "name": "Rapid Fire (2)",
            "slug": "rapid-fire-2",
            "category": "Shooting",
            "summary": "Roll two Firepower dice; each bullet symbol yields additional hits.",
            "rules_text": "When firing with a weapon with the Rapid Fire (2) trait, roll up to two Firepower dice. Each bullet symbol rolled scores additional hits, allocated to targets within 3\".",
            "faq": "Heavy weapons like Heavy Bolters combine Rapid Fire (2) with high Strength and AP."
        },
        {
            "name": "Seismic",
            "slug": "seismic",
            "category": "Impact",
            "summary": "Causes Pinning even through armor and doubles wound rolls on 6.",
            "rules_text": "If a target is wounded by a Seismic weapon, it is automatically Pinned, even if its armor save negates the damage. Furthermore, if a 6 is rolled to wound, the attack counts as having Damage 2 (or +1 Damage).",
            "faq": "Exceptionally lethal in tight zone mortalis corridors against heavily armored Van Saar or Subjugators."
        },
        {
            "name": "Knockback",
            "slug": "knockback",
            "category": "Movement",
            "summary": "Knocks target directly away from shooter by 1 inch.",
            "rules_text": "If the roll to wound equals or beats the target's Strength, the target is pushed 1\" directly away. If the target hits a wall or obstacle, they take 1 additional Damage. If pushed off a ledge, they must take an Initiative test to avoid falling.",
            "faq": "Great for pitching enemy gangers into pit falls and vat hazards."
        },
        {
            "name": "Concussion",
            "slug": "concussion",
            "category": "Debuff",
            "summary": "Reduces target's Initiative by 2 until the end of the round.",
            "rules_text": "Any fighter hit by a Concussion weapon has their Initiative reduced by 2 (to a minimum of 6+) until the end of the round.",
            "faq": "Synergizes with Knockback because targets must roll worse Initiative to avoid falling off ledges."
        },
        {
            "name": "Unwieldy",
            "slug": "unwieldy",
            "category": "Restriction",
            "summary": "Shooting requires a Double Action; in melee, subtract 1 from hit rolls.",
            "rules_text": "A weapon with the Unwieldy trait takes a Shoot (Double) action rather than a Shoot (Basic) action to fire. In close combat, attacks made with an Unwieldy weapon suffer a -1 penalty to hit rolls unless the fighter is equipped with a suspensor or harnessing gear.",
            "faq": "Suspensors reduce the Shoot action from Double to Basic."
        },
        {
            "name": "Blast (3\")",
            "slug": "blast-3",
            "category": "Area",
            "summary": "Uses the 3-inch blast marker; attacks scatter on a miss.",
            "rules_text": "Target a point on the battlefield. Place a 3\" blast marker. Roll a Scatter dice and D6 if line of sight is obstructed or the shot misses. All models under the marker are hit.",
            "faq": "Cannot Pin models unless the blast marker directly clips their base or causes damage."
        },
        {
            "name": "Blast (5\")",
            "slug": "blast-5",
            "category": "Area",
            "summary": "Uses the 5-inch blast marker; devastates clustered targets.",
            "rules_text": "Target a point on the battlefield. Place a 5\" blast marker. All models under the template suffer a hit.",
            "faq": "Common on frag missiles and heavy artillery."
        },
        {
            "name": "Blaze",
            "slug": "blaze",
            "category": "Hazard",
            "summary": "Sets target on fire; target must spend action to put out flames.",
            "rules_text": "When hit, roll a D6. On a 4+, the target is caught in Blaze. While on fire, a fighter cannot take active actions and suffers an automatic S3, AP -1, D1 hit during the priority phase until extinguished.",
            "faq": "Cawdor and Redemptionists specialize heavily in Blaze weapons."
        },
        {
            "name": "Melta",
            "slug": "melta",
            "category": "Armor Piercing",
            "summary": "At short range, weapon damage is increased by +2.",
            "rules_text": "If a Melta weapon scores a hit at Short range, count its Damage as being increased by +2 (typically yielding Damage 4).",
            "faq": "The ultimate vehicle and heavy armor executioner."
        },
        {
            "name": "Versatile",
            "slug": "versatile",
            "category": "Melee",
            "summary": "Allows engaging in close combat from weapon's Long range.",
            "rules_text": "The weapon has a Long range attribute. The bearer may make close combat attacks against an enemy model within this Long range even if not in base-to-base contact.",
            "faq": "Whips, polearms, and shock staves commonly carry Versatile."
        },
        {
            "name": "Rend",
            "slug": "rend",
            "category": "Critical",
            "summary": "Rolling a natural 6 to wound increases Damage by 1.",
            "rules_text": "If a natural 6 is rolled on the wound die, increase the Damage characteristic of the attack by +1.",
            "faq": "Common on chain weapons and heavy cleavers."
        },
        {
            "name": "Silent",
            "slug": "silent",
            "category": "Stealth",
            "summary": "Firing does not reveal fighter in darkness and avoids sentry alerts.",
            "rules_text": "Firing this weapon does not trigger Sentry alarms in stealth missions and does not reveal the shooter's position in Pitch Black scenarios.",
            "faq": "House Delaque signature trait on flechette pistols and needle rifles."
        }
    ]

    db.traits.delete_many({})
    db.traits.insert_many(traits)
    print(f"[Necromunda Seeder] Seeded {len(traits)} weapon traits.")

    # 2. WEAPONS
    weapons = [
        # Lasguns & Laser Weapons
        {
            "name": "Lasgun",
            "slug": "lasgun",
            "category": "Basic Weapon",
            "weapon_type": "Las Weapon",
            "cost_credits": 15,
            "rarity": "Common",
            "range_short": "0-18\"",
            "range_long": "18-24\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 3,
            "damage": 1,
            "armor_piercing": 0,
            "ammo": "2+",
            "traits": ["Plentiful"],
            "availability": ["Van Saar (10cr)", "Escher (15cr)", "Cawdor (15cr)", "Trading Post (15cr)"],
            "description": "The workhorse laser carbine of the Imperium. Cheap, exceptionally reliable, and readily recharged with nearly any battery or thermal tap."
        },
        {
            "name": "Hot-shot Lasgun",
            "slug": "hot-shot-lasgun",
            "category": "Basic Weapon",
            "weapon_type": "Las Weapon",
            "cost_credits": 35,
            "rarity": "Rare (8)",
            "range_short": "0-18\"",
            "range_long": "18-24\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 4,
            "damage": 1,
            "armor_piercing": -1,
            "ammo": "4+",
            "traits": ["Hot-shot"],
            "availability": ["Van Saar (25cr)", "Trading Post (35cr)"],
            "description": "Standard lasgun augmented with high-density capacitor packs. Pierces heavy flak armor at the expense of ammo reliability."
        },
        {
            "name": "Lascarbine",
            "slug": "lascarbine",
            "category": "Basic Weapon",
            "weapon_type": "Las Weapon",
            "cost_credits": 20,
            "rarity": "Common",
            "range_short": "0-12\"",
            "range_long": "12-24\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 3,
            "damage": 1,
            "armor_piercing": 0,
            "ammo": "4+",
            "traits": ["Plentiful", "Rapid Fire (1)"],
            "availability": ["Van Saar (20cr)", "Trading Post (20cr)"],
            "description": "Compact, rapid-pulsing laser carbine engineered for close-quarters room clearing in hive tunnels."
        },
        {
            "name": "Lascannon",
            "slug": "lascannon",
            "category": "Heavy Weapon",
            "weapon_type": "Las Weapon",
            "cost_credits": 175,
            "rarity": "Rare (10)",
            "range_short": "0-24\"",
            "range_long": "24-48\"",
            "accuracy_short": "-",
            "accuracy_long": "+1",
            "strength": 10,
            "damage": 3,
            "armor_piercing": -3,
            "ammo": "4+",
            "traits": ["Unwieldy"],
            "availability": ["Van Saar (155cr)", "Trading Post (175cr)"],
            "description": "Military-grade tank-hunting beam weapon capable of punching through bulkheads and Goliath armored ridge-haulers."
        },
        # Bolters & Heavy Ballistics
        {
            "name": "Boltgun",
            "slug": "boltgun",
            "category": "Basic Weapon",
            "weapon_type": "Bolt Weapon",
            "cost_credits": 55,
            "rarity": "Rare (8)",
            "range_short": "0-12\"",
            "range_long": "12-24\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 4,
            "damage": 2,
            "armor_piercing": -1,
            "ammo": "6+",
            "traits": ["Rapid Fire (1)"],
            "availability": ["Goliath (55cr)", "Orlock (55cr)", "Trading Post (55cr)"],
            "description": "Fires self-propelled explosive mass-reactive bolts. Feared across the Underhive for its devastating stopping power."
        },
        {
            "name": "Heavy Bolter",
            "slug": "heavy-bolter",
            "category": "Heavy Weapon",
            "weapon_type": "Bolt Weapon",
            "cost_credits": 160,
            "rarity": "Rare (10)",
            "range_short": "0-18\"",
            "range_long": "18-36\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 5,
            "damage": 2,
            "armor_piercing": -2,
            "ammo": "6+",
            "traits": ["Rapid Fire (2)", "Unwieldy"],
            "availability": ["Goliath (140cr)", "Orlock (160cr)", "Trading Post (160cr)"],
            "description": "Massive crew-served or suspensor-mounted heavy firearm spitting high-explosive 1.00 caliber shells in sustained bursts."
        },
        {
            "name": "Heavy Concussion Ram",
            "slug": "heavy-concussion-ram",
            "category": "Heavy Weapon",
            "weapon_type": "Concussion Weapon",
            "cost_credits": 70,
            "rarity": "Rare (9)",
            "range_short": "0-15\"",
            "range_long": "15-30\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 4,
            "damage": 1,
            "armor_piercing": -1,
            "ammo": "4+",
            "traits": ["Concussion", "Knockback", "Seismic"],
            "availability": ["Palanite Enforcers (Subjugators) (70cr)"],
            "description": "Riot-control sonic artillery. Blows enemies off elevated gantries and pins armored targets without breaching pressurized domes."
        },
        # Solid Shot & Autoguns
        {
            "name": "Autogun",
            "slug": "autogun",
            "category": "Basic Weapon",
            "weapon_type": "Solid Shot",
            "cost_credits": 15,
            "rarity": "Common",
            "range_short": "0-12\"",
            "range_long": "12-24\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 3,
            "damage": 1,
            "armor_piercing": 0,
            "ammo": "4+",
            "traits": ["Rapid Fire (1)"],
            "availability": ["Orlock (15cr)", "Cawdor (10cr)", "Trading Post (15cr)"],
            "description": "Gas-operated projectile rifle firing caseless rounds. Highly lethal burst fire in the hands of an experienced ganger."
        },
        {
            "name": "Combat Shotgun",
            "slug": "combat-shotgun",
            "category": "Basic Weapon",
            "weapon_type": "Shotgun",
            "cost_credits": 60,
            "rarity": "Rare (7)",
            "range_short": "0-4\"",
            "range_long": "4-12\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 4,
            "damage": 2,
            "armor_piercing": 0,
            "ammo": "4+",
            "traits": ["Knockback", "Rapid Fire (1)"],
            "availability": ["Orlock (55cr)", "Goliath (60cr)", "Trading Post (60cr)"],
            "description": "Heavy-bore pump weapon equipped with slug and salvo magazines for brutal hallway clearing."
        },
        # Special & Exotic Weapons
        {
            "name": "Plasma Gun",
            "slug": "plasma-gun",
            "category": "Special Weapon",
            "weapon_type": "Plasma Weapon",
            "cost_credits": 100,
            "rarity": "Rare (9)",
            "range_short": "0-12\"",
            "range_long": "12-24\"",
            "accuracy_short": "+2",
            "accuracy_long": "-",
            "strength": 5,
            "damage": 2,
            "armor_piercing": -1,
            "ammo": "5+",
            "traits": ["Rapid Fire (1)"],
            "availability": ["Van Saar (90cr)", "Delaque (100cr)", "Trading Post (100cr)"],
            "description": "High-heat reactor weapon firing magnetic spheres of solar plasma. Standard fire mode vaporizes gangers instantly."
        },
        {
            "name": "Meltagun",
            "slug": "meltagun",
            "category": "Special Weapon",
            "weapon_type": "Melta Weapon",
            "cost_credits": 135,
            "rarity": "Rare (11)",
            "range_short": "0-6\"",
            "range_long": "6-12\"",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 8,
            "damage": 3,
            "armor_piercing": -4,
            "ammo": "4+",
            "traits": ["Melta"],
            "availability": ["Goliath (125cr)", "Trading Post (135cr)"],
            "description": "Short-range thermal agitation projector. Liquefies battleplate and chassis within arm's reach."
        },
        {
            "name": "Flamer",
            "slug": "flamer",
            "category": "Special Weapon",
            "weapon_type": "Flame Weapon",
            "cost_credits": 140,
            "rarity": "Rare (8)",
            "range_short": "T",
            "range_long": "T",
            "accuracy_short": "-",
            "accuracy_long": "-",
            "strength": 4,
            "damage": 1,
            "armor_piercing": -1,
            "ammo": "5+",
            "traits": ["Blaze"],
            "availability": ["Cawdor (120cr)", "Escher (140cr)", "Trading Post (140cr)"],
            "description": "Uses teardrop flame template. Ignites multiple opponents simultaneously, sowing panic and disrupting firing lines."
        },
        # Melee Weapons
        {
            "name": "Chainsword",
            "slug": "chainsword",
            "category": "Close Combat",
            "weapon_type": "Melee",
            "cost_credits": 25,
            "rarity": "Common",
            "range_short": "E",
            "range_long": "E",
            "accuracy_short": "+1",
            "accuracy_long": "-",
            "strength": 3,
            "damage": 1,
            "armor_piercing": -1,
            "ammo": "-",
            "traits": ["Rend"],
            "availability": ["Escher (25cr)", "Goliath (25cr)", "Trading Post (25cr)"],
            "description": "Motorized monomolecular sawblade capable of tearing flesh and light carapace with ease."
        },
        {
            "name": "Power Claw",
            "slug": "power-claw",
            "category": "Close Combat",
            "weapon_type": "Power Weapon",
            "cost_credits": 60,
            "rarity": "Rare (9)",
            "range_short": "E",
            "range_long": "E",
            "accuracy_short": "-",
            "accuracy_long": "-",
            "strength": 5,
            "damage": 2,
            "armor_piercing": -2,
            "ammo": "-",
            "traits": ["Rend"],
            "availability": ["Goliath (50cr)", "Trading Post (60cr)"],
            "description": "Disruption-field energized claw engineered for industrial mining or dismantling rival champions."
        },
        {
            "name": "Shock Whip",
            "slug": "shock-whip",
            "category": "Close Combat",
            "weapon_type": "Exotic Melee",
            "cost_credits": 25,
            "rarity": "Rare (8)",
            "range_short": "E",
            "range_long": "3\"",
            "accuracy_short": "-",
            "accuracy_long": "+1",
            "strength": 3,
            "damage": 1,
            "armor_piercing": -1,
            "ammo": "-",
            "traits": ["Versatile"],
            "availability": ["Escher (25cr)", "Trading Post (25cr)"],
            "description": "Electrified mono-cable whip allowing Escher Queens and Matriarchs to lash out at enemies from 3 inches away."
        }
    ]

    db.weapons.delete_many({})
    db.weapons.insert_many(weapons)
    print(f"[Necromunda Seeder] Seeded {len(weapons)} weapons into 'necro_weapons'.")

    # 3. HOUSES / GANGS
    houses = [
        {
            "name": "House Van Saar",
            "slug": "van-saar",
            "title": "The House of Artifice",
            "specialty": "High-tech weaponry, plasma, energy shields, and cyberteknika.",
            "lore": "Possessing a malfunctioning, radioactive Standard Template Construct (STC), Van Saar crafts the finest weapons and armored survival suits on Necromunda at the cost of slow cellular degradation.",
            "primary_skills": ["Shooting", "Savant", "Tech"],
            "signature_weapons": ["Lasgun", "Hot-shot Lasgun", "Plasma Gun", "Lascannon"]
        },
        {
            "name": "House Goliath",
            "slug": "goliath",
            "title": "The House of Chains",
            "specialty": "Genetically vat-grown giants, heavy melee, brute strength, and stub cannonry.",
            "lore": "Engineered to labor in the sweltering foundries and deep slag pits, Goliaths prize physical supremacy and devastating close combat.",
            "primary_skills": ["Brawn", "Ferocity", "Muscle"],
            "signature_weapons": ["Boltgun", "Heavy Bolter", "Power Claw", "Combat Shotgun"]
        },
        {
            "name": "House Escher",
            "slug": "escher",
            "title": "The House of Blades",
            "specialty": "Chems, toxins, agility, venom blades, and whip weaponry.",
            "lore": "An all-female matriarchy dominating Necromunda's pharmaceutical and stimulant trade, fielding lightning-fast fighters with poisoned weaponry.",
            "primary_skills": ["Agility", "Combat", "Finesse"],
            "signature_weapons": ["Lasgun", "Shock Whip", "Chainsword", "Flamer"]
        },
        {
            "name": "House Orlock",
            "slug": "orlock",
            "title": "The House of Iron",
            "specialty": "Mining networks, shotguns, autoguns, heavy stubbers, and sheer grit.",
            "lore": "Controlling the inter-hive rail networks and deep ore mines, Orlocks rely on disciplined kinetic firepower, sturdy leather-plate armor, and family loyalty.",
            "primary_skills": ["Ferocity", "Combat", "Bravado"],
            "signature_weapons": ["Autogun", "Combat Shotgun", "Heavy Bolter"]
        },
        {
            "name": "House Cawdor",
            "slug": "cawdor",
            "title": "The House of Faith",
            "specialty": "Horde swarms, scrap-polearms, blunderbusses, fire, and fanatic zeal.",
            "lore": "The destitute scavengers of the hive heaps, Cawdor gangers worship the God-Emperor through extreme penance, overwhelming numbers, and improvised incendiary weapons.",
            "primary_skills": ["Brawn", "Combat", "Piety"],
            "signature_weapons": ["Autogun", "Flamer", "Lasgun"]
        },
        {
            "name": "House Delaque",
            "slug": "delaque",
            "title": "The House of Shadow",
            "specialty": "Espionage, stealth, silent needle weapons, web guns, and psychomancy.",
            "lore": "Whispering spies and bald shadow-runners cloaked in long trench coats, Delaque deals in secrets, assassination, and unnatural darkness.",
            "primary_skills": ["Agility", "Cunning", "Obfuscation"],
            "signature_weapons": ["Plasma Gun", "Lasgun"]
        },
        {
            "name": "Palanite Enforcers",
            "slug": "palanite-enforcers",
            "title": "The Law of the Hive",
            "specialty": "Authoritarian suppression, concussion rams, riot shields, and sniper fire.",
            "lore": "Lord Helmawr's brutal planetary police force, dispatched into the Underhive to quash worker uprisings and preserve quota shipments by any means necessary.",
            "primary_skills": ["Shooting", "Brawn", "Enforcement"],
            "signature_weapons": ["Heavy Concussion Ram", "Boltgun", "Combat Shotgun"]
        }
    ]

    db.houses.delete_many({})
    db.houses.insert_many(houses)
    print(f"[Necromunda Seeder] Seeded {len(houses)} clan houses.")

    # 4. SKILLS
    skills = [
        {
            "name": "Fast Shot",
            "slug": "fast-shot",
            "tree": "Shooting",
            "rules_text": "The fighter can make a Shoot (Simple) action instead of a Shoot (Basic) action. They may shoot twice in a single activation if they perform two Shoot actions.",
            "tactics": "Deadly on Van Saar champions armed with plasma guns or hot-shot lasguns."
        },
        {
            "name": "Marksman",
            "slug": "marksman",
            "tree": "Shooting",
            "rules_text": "The fighter ignores the target priority rule and ignores penalties for targets in Partial Cover (-1).",
            "tactics": "Essential for snipers operating long-range laser or needle rifles."
        },
        {
            "name": "Iron Jaw",
            "slug": "iron-jaw",
            "tree": "Brawn",
            "rules_text": "When rolling on the Lasting Injury table, this fighter may roll two D66 and pick the lower roll.",
            "tactics": "Greatly increases survival rate of frontline Goliath champions."
        },
        {
            "name": "Inspirational",
            "slug": "inspirational",
            "tree": "Leadership",
            "rules_text": "Friendly fighters within 8\" may use this fighter's Cool or Willpower characteristic instead of their own when taking Bottle tests or Nerve tests.",
            "tactics": "Crucial for keeping cheap horde gangers (Cawdor, Juves) from breaking and running."
        },
        {
            "name": "Infiltrate",
            "slug": "infiltrate",
            "tree": "Cunning",
            "rules_text": "During deployment, this fighter may be placed anywhere on the battlefield that is at least 6\" away from any enemy model and not in their line of sight.",
            "tactics": "Signature Delaque and Escher ambusher skill for claiming early high-ground or control consoles."
        }
    ]

    db.skills.delete_many({})
    db.skills.insert_many(skills)
    print(f"[Necromunda Seeder] Seeded {len(skills)} skill trees.")

    # Create indexes for O(1) slug lookups
    db.weapons.create_index("slug", unique=True)
    db.traits.create_index("slug", unique=True)
    db.houses.create_index("slug", unique=True)
    db.skills.create_index("slug", unique=True)
    print("[Necromunda Seeder] Created unique slug indexes.")
    print("[OK] Necromunda Corpus Seed Complete!")

if __name__ == "__main__":
    seed_necromunda()
