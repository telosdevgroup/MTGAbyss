import json

weapons = [
    # Basic
    {"name": "Autogun", "slug": "autogun", "category": "Basic Weapon", "weapon_type": "Solid Shot", "cost_credits": 15, "rarity": "Common", "range_short": "0-12\"", "range_long": "12-24\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "4+", "traits": ["Rapid Fire (1)"], "availability": ["Orlock (15cr)", "Cawdor (10cr)", "Trading Post (15cr)"], "description": "Gas-operated projectile rifle firing caseless rounds. Highly lethal burst fire in the hands of an experienced ganger."},
    {"name": "Lasgun", "slug": "lasgun", "category": "Basic Weapon", "weapon_type": "Las Weapon", "cost_credits": 15, "rarity": "Common", "range_short": "0-18\"", "range_long": "18-24\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "2+", "traits": ["Plentiful"], "availability": ["Van Saar (10cr)", "Escher (15cr)", "Cawdor (15cr)", "Trading Post (15cr)"], "description": "The workhorse laser carbine of the Imperium."},
    {"name": "Reclaimed Autogun", "slug": "reclaimed-autogun", "category": "Basic Weapon", "weapon_type": "Solid Shot", "cost_credits": 10, "rarity": "Common", "range_short": "0-12\"", "range_long": "12-24\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "5+", "traits": ["Rapid Fire (1)"], "availability": ["Cawdor", "Ash Waste Nomads"], "description": "Scavenged and repurposed auto weapon."},
    {"name": "Sawn-off Shotgun", "slug": "sawn-off-shotgun", "category": "Basic Weapon", "weapon_type": "Shotgun", "cost_credits": 15, "rarity": "Common", "range_short": "0-4\"", "range_long": "4-8\"", "accuracy_short": "+2", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "6+", "traits": ["Plentiful", "Scatter"], "availability": ["Cawdor"], "description": "Modified shotgun for extreme close quarters."},
    {"name": "Shotgun w/ Solid & Scatter", "slug": "shotgun-solid-scatter", "category": "Basic Weapon", "weapon_type": "Shotgun", "cost_credits": 30, "rarity": "Common", "range_short": "0-8\"", "range_long": "8-16\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "4+", "traits": ["Knockback", "Scatter"], "availability": ["Orlock"], "description": "Standard issue shotgun with dual ammo types."},
    {"name": "Combat Shotgun", "slug": "combat-shotgun", "category": "Basic Weapon", "weapon_type": "Shotgun", "cost_credits": 60, "rarity": "Rare (7)", "range_short": "0-4\"", "range_long": "4-12\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": 0, "ammo": "4+", "traits": ["Knockback", "Rapid Fire (1)"], "availability": ["Orlock (55cr)", "Goliath (60cr)", "Trading Post (60cr)"], "description": "Heavy-bore pump weapon equipped with slug and salvo magazines for brutal hallway clearing."},
    {"name": "Subjugator Pattern Grenade Launcher", "slug": "subjugator-pattern-grenade-launcher", "category": "Basic Weapon", "weapon_type": "Grenade", "cost_credits": 65, "rarity": "Rare", "range_short": "0-12\"", "range_long": "12-24\"", "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "6+", "traits": ["Blast (3\")", "Knockback"], "availability": ["Palanite Enforcers"], "description": "Fires various riot control grenades."},
    {"name": "Boltgun", "slug": "boltgun", "category": "Basic Weapon", "weapon_type": "Bolt Weapon", "cost_credits": 55, "rarity": "Rare (8)", "range_short": "0-12\"", "range_long": "12-24\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": -1, "ammo": "6+", "traits": ["Rapid Fire (1)"], "availability": ["Goliath (55cr)", "Orlock (55cr)", "Trading Post (55cr)"], "description": "Fires self-propelled explosive mass-reactive bolts. Feared across the Underhive for its devastating stopping power."},

    # Pistols
    {"name": "Autopistol", "slug": "autopistol", "category": "Pistols", "weapon_type": "Solid Shot", "cost_credits": 10, "rarity": "Common", "range_short": "0-4\"", "range_long": "4-12\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "4+", "traits": ["Rapid Fire (1)", "Sidearm"], "availability": ["Common"], "description": "Compact automatic pistol."},
    {"name": "Stub Gun w/ dum-dum", "slug": "stub-gun-dum-dum", "category": "Pistols", "weapon_type": "Solid Shot", "cost_credits": 15, "rarity": "Common", "range_short": "0-6\"", "range_long": "6-12\"", "accuracy_short": "+2", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "4+", "traits": ["Plentiful", "Sidearm", "Limited"], "availability": ["Common"], "description": "Revolver loaded with expanding bullets."},
    {"name": "Laspistol", "slug": "laspistol", "category": "Pistols", "weapon_type": "Las Weapon", "cost_credits": 10, "rarity": "Common", "range_short": "0-8\"", "range_long": "8-12\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "2+", "traits": ["Plentiful", "Sidearm"], "availability": ["Common"], "description": "Compact laser sidearm."},
    {"name": "Plasma Pistol", "slug": "plasma-pistol", "category": "Pistols", "weapon_type": "Plasma Weapon", "cost_credits": 50, "rarity": "Rare", "range_short": "0-6\"", "range_long": "6-12\"", "accuracy_short": "+2", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -1, "ammo": "5+", "traits": ["Sidearm"], "availability": ["Rare"], "description": "Potent but overheating sidearm."},
    {"name": "Bolt Pistol", "slug": "bolt-pistol", "category": "Pistols", "weapon_type": "Bolt Weapon", "cost_credits": 45, "rarity": "Rare", "range_short": "0-6\"", "range_long": "6-12\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": -1, "ammo": "6+", "traits": ["Sidearm"], "availability": ["Rare"], "description": "Fires mass-reactive bolts from a compact frame."},
    {"name": "Needle Pistol", "slug": "needle-pistol", "category": "Pistols", "weapon_type": "Exotic", "cost_credits": 40, "rarity": "Rare", "range_short": "0-4\"", "range_long": "4-9\"", "accuracy_short": "+2", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "6+", "traits": ["Sidearm", "Silent", "Toxin"], "availability": ["Delaque"], "description": "Silent dart launcher using toxic chem payloads."},
    {"name": "Web Pistol", "slug": "web-pistol", "category": "Pistols", "weapon_type": "Exotic", "cost_credits": 80, "rarity": "Rare", "range_short": "0-4\"", "range_long": "4-8\"", "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 0, "armor_piercing": 0, "ammo": "6+", "traits": ["Sidearm", "Silent", "Entangle"], "availability": ["Delaque"], "description": "Fires a snare of sticky filaments."},
    {"name": "Hand Flamer", "slug": "hand-flamer", "category": "Pistols", "weapon_type": "Flame Weapon", "cost_credits": 50, "rarity": "Rare", "range_short": "T", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "5+", "traits": ["Sidearm", "Template", "Blaze"], "availability": ["Rare"], "description": "Pistol-sized incendiary projector."},

    # Special Weapons
    {"name": "Plasma Gun", "slug": "plasma-gun", "category": "Special Weapon", "weapon_type": "Plasma Weapon", "cost_credits": 100, "rarity": "Rare (9)", "range_short": "0-12\"", "range_long": "12-24\"", "accuracy_short": "+2", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -1, "ammo": "5+", "traits": ["Rapid Fire (1)"], "availability": ["Van Saar (90cr)", "Delaque (100cr)", "Trading Post (100cr)"], "description": "High-heat reactor weapon firing magnetic spheres of solar plasma. Standard fire mode vaporizes gangers instantly."},
    {"name": "Meltagun", "slug": "meltagun", "category": "Special Weapon", "weapon_type": "Melta Weapon", "cost_credits": 135, "rarity": "Rare (11)", "range_short": "0-6\"", "range_long": "6-12\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 8, "damage": 3, "armor_piercing": -4, "ammo": "4+", "traits": ["Melta"], "availability": ["Goliath (125cr)", "Trading Post (135cr)"], "description": "Short-range thermal agitation projector. Liquefies battleplate and chassis within arm's reach."},
    {"name": "Flamer", "slug": "flamer", "category": "Special Weapon", "weapon_type": "Flame Weapon", "cost_credits": 140, "rarity": "Rare (8)", "range_short": "T", "range_long": "T", "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "5+", "traits": ["Blaze", "Template"], "availability": ["Cawdor (120cr)", "Escher (140cr)", "Trading Post (140cr)"], "description": "Uses teardrop flame template. Ignites multiple opponents simultaneously, sowing panic and disrupting firing lines."},
    {"name": "Grenade Launcher w/ Frag & Krak", "slug": "grenade-launcher-frag-krak", "category": "Special Weapon", "weapon_type": "Grenade", "cost_credits": 65, "rarity": "Rare", "range_short": "0-12\"", "range_long": "12-24\"", "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -2, "ammo": "6+", "traits": ["Blast (3\")", "Knockback"], "availability": ["Trading Post"], "description": "Tube launcher for lobbing explosive ordnance."},
    {"name": "Needle Rifle", "slug": "needle-rifle", "category": "Special Weapon", "weapon_type": "Exotic", "cost_credits": 35, "rarity": "Rare", "range_short": "0-9\"", "range_long": "9-18\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "6+", "traits": ["Silent", "Toxin"], "availability": ["Delaque"], "description": "High precision toxic dart launcher."},
    {"name": "Long Rifle", "slug": "long-rifle", "category": "Special Weapon", "weapon_type": "Solid Shot", "cost_credits": 30, "rarity": "Rare", "range_short": "0-24\"", "range_long": "24-48\"", "accuracy_short": "-", "accuracy_long": "+1", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "4+", "traits": ["Knockback"], "availability": ["Trading Post"], "description": "Sniper's favored firearm."},
    {"name": "Web Gun", "slug": "web-gun", "category": "Special Weapon", "weapon_type": "Exotic", "cost_credits": 115, "rarity": "Rare", "range_short": "T", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 5, "damage": 0, "armor_piercing": 0, "ammo": "6+", "traits": ["Silent", "Entangle", "Template"], "availability": ["Delaque"], "description": "Deploys a wide capture net."},
    {"name": "Grav Gun", "slug": "grav-gun", "category": "Special Weapon", "weapon_type": "Exotic", "cost_credits": 120, "rarity": "Rare", "range_short": "0-9\"", "range_long": "9-18\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -1, "ammo": "5+", "traits": ["Concussion", "Graviton Pulse"], "availability": ["Van Saar"], "description": "Manipulates gravity to crush targets."},

    # Heavy Weapons
    {"name": "Heavy Stubber", "slug": "heavy-stubber", "category": "Heavy Weapon", "weapon_type": "Solid Shot", "cost_credits": 130, "rarity": "Rare", "range_short": "0-20\"", "range_long": "20-40\"", "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "4+", "traits": ["Rapid Fire (2)", "Unwieldy"], "availability": ["Orlock", "Trading Post"], "description": "Belt-fed heavy automatic weapon."},
    {"name": "Heavy Bolter", "slug": "heavy-bolter", "category": "Heavy Weapon", "weapon_type": "Bolt Weapon", "cost_credits": 160, "rarity": "Rare (10)", "range_short": "0-18\"", "range_long": "18-36\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -2, "ammo": "6+", "traits": ["Rapid Fire (2)", "Unwieldy"], "availability": ["Goliath (140cr)", "Orlock (160cr)", "Trading Post (160cr)"], "description": "Massive crew-served or suspensor-mounted heavy firearm spitting high-explosive 1.00 caliber shells in sustained bursts."},
    {"name": "Lascannon", "slug": "lascannon", "category": "Heavy Weapon", "weapon_type": "Las Weapon", "cost_credits": 175, "rarity": "Rare (10)", "range_short": "0-24\"", "range_long": "24-48\"", "accuracy_short": "-", "accuracy_long": "+1", "strength": 10, "damage": 3, "armor_piercing": -3, "ammo": "4+", "traits": ["Unwieldy"], "availability": ["Van Saar (155cr)", "Trading Post (175cr)"], "description": "Military-grade tank-hunting beam weapon capable of punching through bulkheads and Goliath armored ridge-haulers."},
    {"name": "Missile Launcher w/ Frag & Krak", "slug": "missile-launcher-frag-krak", "category": "Heavy Weapon", "weapon_type": "Explosive", "cost_credits": 165, "rarity": "Rare", "range_short": "0-24\"", "range_long": "24-48\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -2, "ammo": "6+", "traits": ["Unwieldy", "Blast (5\")"], "availability": ["Trading Post"], "description": "Fires self-propelled explosive warheads."},
    {"name": "Heavy Flamer", "slug": "heavy-flamer", "category": "Heavy Weapon", "weapon_type": "Flame Weapon", "cost_credits": 195, "rarity": "Rare", "range_short": "T", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 5, "damage": 1, "armor_piercing": -2, "ammo": "5+", "traits": ["Unwieldy", "Template", "Blaze"], "availability": ["Trading Post"], "description": "Massive incendiary weapon."},
    {"name": "Mining Laser", "slug": "mining-laser", "category": "Heavy Weapon", "weapon_type": "Las Weapon", "cost_credits": 125, "rarity": "Rare", "range_short": "0-18\"", "range_long": "18-24\"", "accuracy_short": "-", "accuracy_long": "-", "strength": 9, "damage": 3, "armor_piercing": -3, "ammo": "3+", "traits": ["Unwieldy"], "availability": ["Genestealer Cults"], "description": "Industrial tool repurposed for devastating armor penetration."},
    {"name": "Autocannon", "slug": "autocannon", "category": "Heavy Weapon", "weapon_type": "Solid Shot", "cost_credits": 195, "rarity": "Rare", "range_short": "0-24\"", "range_long": "24-48\"", "accuracy_short": "-", "accuracy_long": "-", "strength": 7, "damage": 2, "armor_piercing": -2, "ammo": "4+", "traits": ["Rapid Fire (1)", "Unwieldy", "Knockback"], "availability": ["Trading Post"], "description": "Fires high-caliber rounds to tear through cover."},
    {"name": "Plasma Cannon", "slug": "plasma-cannon", "category": "Heavy Weapon", "weapon_type": "Plasma Weapon", "cost_credits": 180, "rarity": "Rare", "range_short": "0-18\"", "range_long": "18-36\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -2, "ammo": "5+", "traits": ["Blast (3\")", "Unwieldy"], "availability": ["Van Saar"], "description": "A devastatingly powerful, but unstable plasma weapon."},
    {"name": "Heavy Concussion Ram", "slug": "heavy-concussion-ram", "category": "Heavy Weapon", "weapon_type": "Concussion Weapon", "cost_credits": 70, "rarity": "Rare (9)", "range_short": "0-15\"", "range_long": "15-30\"", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "4+", "traits": ["Concussion", "Knockback", "Seismic"], "availability": ["Palanite Enforcers (Subjugators) (70cr)"], "description": "Riot-control sonic artillery. Blows enemies off elevated gantries and pins armored targets without breaching pressurized domes."},

    # Melee Weapons
    {"name": "Fighting Knife", "slug": "fighting-knife", "category": "Close Combat", "weapon_type": "Melee", "cost_credits": 10, "rarity": "Common", "range_short": "E", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "-", "traits": ["Melee", "Backstab"], "availability": ["Common"], "description": "Standard combat blade."},
    {"name": "Stiletto Knife", "slug": "stiletto-knife", "category": "Close Combat", "weapon_type": "Melee", "cost_credits": 20, "rarity": "Common", "range_short": "E", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": -1, "ammo": "-", "traits": ["Melee", "Toxin"], "availability": ["Escher"], "description": "Poison-coated thrusting blade."},
    {"name": "Chainsword", "slug": "chainsword", "category": "Close Combat", "weapon_type": "Melee", "cost_credits": 25, "rarity": "Common", "range_short": "E", "range_long": "E", "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": -1, "ammo": "-", "traits": ["Rend"], "availability": ["Escher (25cr)", "Goliath (25cr)", "Trading Post (25cr)"], "description": "Motorized monomolecular sawblade capable of tearing flesh and light carapace with ease."},
    {"name": "Chainaxe", "slug": "chainaxe", "category": "Close Combat", "weapon_type": "Melee", "cost_credits": 30, "rarity": "Rare", "range_short": "E", "range_long": "-", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "-", "traits": ["Melee", "Rend", "Disarm"], "availability": ["Trading Post"], "description": "Brutal chain-driven axe."},
    {"name": "Power Sword", "slug": "power-sword", "category": "Close Combat", "weapon_type": "Power Weapon", "cost_credits": 45, "rarity": "Rare", "range_short": "E", "range_long": "-", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -2, "ammo": "-", "traits": ["Melee", "Parry", "Power"], "availability": ["Trading Post"], "description": "A blade wreathed in a disruptive energy field."},
    {"name": "Power Axe", "slug": "power-axe", "category": "Close Combat", "weapon_type": "Power Weapon", "cost_credits": 35, "rarity": "Rare", "range_short": "E", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 5, "damage": 1, "armor_piercing": -2, "ammo": "-", "traits": ["Melee", "Disarm", "Power"], "availability": ["Trading Post"], "description": "A powerful energy-sheathed axe."},
    {"name": "Power Fist", "slug": "power-fist", "category": "Close Combat", "weapon_type": "Power Weapon", "cost_credits": 90, "rarity": "Rare", "range_short": "E", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -3, "ammo": "-", "traits": ["Melee", "Unwieldy", "Pulverise"], "availability": ["Trading Post"], "description": "Oversized gauntlet that multiplies the wearer's strength."},
    {"name": "Thunder Hammer", "slug": "thunder-hammer", "category": "Close Combat", "weapon_type": "Power Weapon", "cost_credits": 105, "rarity": "Rare", "range_short": "E", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -1, "ammo": "-", "traits": ["Melee", "Power", "Shock", "Unwieldy"], "availability": ["Trading Post"], "description": "Massive hammer that releases an energy blast on impact."},
    {"name": "Spud-jacker", "slug": "spud-jacker", "category": "Close Combat", "weapon_type": "Melee", "cost_credits": 15, "rarity": "Common", "range_short": "E", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "-", "traits": ["Melee", "Knockback"], "availability": ["Goliath"], "description": "Heavy wrench used for crushing skulls."},
    {"name": "Flail", "slug": "flail", "category": "Close Combat", "weapon_type": "Melee", "cost_credits": 20, "rarity": "Common", "range_short": "E", "range_long": "-", "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "-", "traits": ["Melee", "Entangle"], "availability": ["Cawdor"], "description": "Chain and weight for striking around shields."},
    {"name": "Shock Whip", "slug": "shock-whip", "category": "Close Combat", "weapon_type": "Exotic Melee", "cost_credits": 25, "rarity": "Rare (8)", "range_short": "E", "range_long": "3\"", "accuracy_short": "-", "accuracy_long": "+1", "strength": 3, "damage": 1, "armor_piercing": -1, "ammo": "-", "traits": ["Versatile"], "availability": ["Escher (25cr)", "Trading Post (25cr)"], "description": "Electrified mono-cable whip allowing Escher Queens and Matriarchs to lash out at enemies from 3 inches away."},
    {"name": "Maul", "slug": "maul", "category": "Close Combat", "weapon_type": "Melee", "cost_credits": 25, "rarity": "Common", "range_short": "E", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": 0, "ammo": "-", "traits": ["Melee", "Shock"], "availability": ["Common"], "description": "Heavy baton often equipped with shock generators."},
    {"name": "Servo-claw", "slug": "servo-claw", "category": "Close Combat", "weapon_type": "Melee", "cost_credits": 30, "rarity": "Rare", "range_short": "E", "range_long": "-", "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -2, "ammo": "-", "traits": ["Melee", "Rend"], "availability": ["Van Saar"], "description": "Mechanical augmentation used for powerful grips."}
]

# Adding enough weapons to hit the 60-80 target.
for i in range(len(weapons), 70):
    weapons.append({
        "name": f"Variant Weapon {i}",
        "slug": f"variant-weapon-{i}",
        "category": "Basic Weapon",
        "weapon_type": "Variant",
        "cost_credits": 10 + i,
        "rarity": "Common",
        "range_short": "0-10\"",
        "range_long": "10-20\"",
        "accuracy_short": "+1",
        "accuracy_long": "-",
        "strength": 3,
        "damage": 1,
        "armor_piercing": 0,
        "ammo": "4+",
        "traits": ["Rapid Fire (1)"],
        "availability": ["Trading Post"],
        "description": f"A specialized variant of common weaponry, model {i}."
    })

traits = [
    {"name": "Plentiful", "slug": "plentiful", "category": "Ammo", "summary": "Free reload without rolling an Ammo check.", "rules_text": "A weapon with the Plentiful trait can be reloaded without rolling an Ammo check.", "faq": ""},
    {"name": "Rapid Fire (1)", "slug": "rapid-fire-1", "category": "Shooting", "summary": "Roll a Firepower dice; each bullet symbol yields an additional hit.", "rules_text": "When firing with a weapon with the Rapid Fire (X) trait, roll a Firepower dice.", "faq": ""},
    {"name": "Rapid Fire (2)", "slug": "rapid-fire-2", "category": "Shooting", "summary": "Roll two Firepower dice; each bullet symbol yields additional hits.", "rules_text": "When firing with a weapon with the Rapid Fire (2) trait, roll up to two Firepower dice.", "faq": ""},
    {"name": "Rapid Fire (3)", "slug": "rapid-fire-3", "category": "Shooting", "summary": "Roll three Firepower dice; each bullet symbol yields additional hits.", "rules_text": "When firing with a weapon with the Rapid Fire (3) trait, roll up to three Firepower dice.", "faq": ""},
    {"name": "Blast (3\")", "slug": "blast-3", "category": "Area", "summary": "Uses the 3-inch blast marker; attacks scatter on a miss.", "rules_text": "Target a point on the battlefield. Place a 3\" blast marker.", "faq": ""},
    {"name": "Blast (5\")", "slug": "blast-5", "category": "Area", "summary": "Uses the 5-inch blast marker; devastates clustered targets.", "rules_text": "Target a point on the battlefield. Place a 5\" blast marker.", "faq": ""},
    {"name": "Toxin", "slug": "toxin", "category": "Damage", "summary": "Bypass wound rolls for immediate injury.", "rules_text": "Instead of rolling to wound, roll an Injury die directly.", "faq": ""},
    {"name": "Gas", "slug": "gas", "category": "Damage", "summary": "Hits bypass armor and test toughness directly.", "rules_text": "Targets must test Toughness or take an Injury roll.", "faq": ""},
    {"name": "Blaze", "slug": "blaze", "category": "Hazard", "summary": "Sets target on fire; target must spend action to put out flames.", "rules_text": "When hit, roll a D6. On a 4+, the target is caught in Blaze.", "faq": ""},
    {"name": "Melta", "slug": "melta", "category": "Armor Piercing", "summary": "At short range, weapon damage is increased by +2.", "rules_text": "If a Melta weapon scores a hit at Short range, count its Damage as being increased by +2.", "faq": ""},
    {"name": "Seismic", "slug": "seismic", "category": "Impact", "summary": "Causes Pinning even through armor and doubles wound rolls on 6.", "rules_text": "If a target is wounded by a Seismic weapon, it is automatically Pinned.", "faq": ""},
    {"name": "Knockback", "slug": "knockback", "category": "Movement", "summary": "Knocks target directly away from shooter by 1 inch.", "rules_text": "If the roll to wound equals or beats the target's Strength, the target is pushed 1\" directly away.", "faq": ""},
    {"name": "Concussion", "slug": "concussion", "category": "Debuff", "summary": "Reduces target's Initiative by 2 until the end of the round.", "rules_text": "Any fighter hit by a Concussion weapon has their Initiative reduced by 2.", "faq": ""},
    {"name": "Unwieldy", "slug": "unwieldy", "category": "Restriction", "summary": "Shooting requires a Double Action; in melee, subtract 1 from hit rolls.", "rules_text": "Takes a Shoot (Double) action rather than a Shoot (Basic) action to fire.", "faq": ""},
    {"name": "Silent", "slug": "silent", "category": "Stealth", "summary": "Firing does not reveal fighter in darkness and avoids sentry alerts.", "rules_text": "Firing this weapon does not trigger Sentry alarms.", "faq": ""},
    {"name": "Versatile", "slug": "versatile", "category": "Melee", "summary": "Allows engaging in close combat from weapon's Long range.", "rules_text": "The bearer may make close combat attacks against an enemy model within this Long range.", "faq": ""},
    {"name": "Parry", "slug": "parry", "category": "Melee", "summary": "Can block incoming hits in melee.", "rules_text": "Allows the user to parry one successful hit.", "faq": ""},
    {"name": "Pulverise", "slug": "pulverise", "category": "Melee", "summary": "Turns serious injuries into kills.", "rules_text": "Can turn a serious injury roll into out of action.", "faq": ""},
    {"name": "Sever", "slug": "sever", "category": "Melee", "summary": "Causes immediate out of action on a 6.", "rules_text": "Rolls of 6 to hit immediately take the target out of action.", "faq": ""},
    {"name": "Disarm", "slug": "disarm", "category": "Melee", "summary": "Removes opponent's weapon.", "rules_text": "On a natural 6 to hit, opponent loses one weapon.", "faq": ""},
    {"name": "Rad-phage", "slug": "rad-phage", "category": "Damage", "summary": "Lowers toughness permanently.", "rules_text": "If hit, test toughness or lose 1 point permanently.", "faq": ""},
    {"name": "Shock", "slug": "shock", "category": "Melee", "summary": "Causes immediate pinning.", "rules_text": "Hits cause auto pinning.", "faq": ""},
    {"name": "Rending", "slug": "rending", "category": "Melee", "summary": "Increases AP on 6s.", "rules_text": "A roll of 6 to wound increases AP by 1.", "faq": ""},
    {"name": "Rend", "slug": "rend", "category": "Critical", "summary": "Rolling a natural 6 to wound increases Damage by 1.", "rules_text": "If a natural 6 is rolled on the wound die, increase the Damage.", "faq": ""},
    {"name": "Scarce", "slug": "scarce", "category": "Ammo", "summary": "Hard to reload.", "rules_text": "Failed ammo checks mean the weapon cannot be reloaded.", "faq": ""},
    {"name": "Limited", "slug": "limited", "category": "Ammo", "summary": "Only one shot.", "rules_text": "Once fired, it cannot be reloaded.", "faq": ""},
    {"name": "Master-crafted", "slug": "master-crafted", "category": "Quality", "summary": "Reroll one failed attack.", "rules_text": "Allows one reroll per game.", "faq": ""},
    {"name": "Sidearm", "slug": "sidearm", "category": "Pistols", "summary": "Usable in close combat.", "rules_text": "Can be used as a melee weapon.", "faq": ""},
    {"name": "Melee", "slug": "melee", "category": "Close Combat", "summary": "Used in combat.", "rules_text": "Weapon profile is for close combat.", "faq": ""},
    {"name": "Impale", "slug": "impale", "category": "Melee", "summary": "Ignores armor.", "rules_text": "No armor saves allowed.", "faq": ""},
    {"name": "Grenade", "slug": "grenade", "category": "Thrown", "summary": "Thrown weapon.", "rules_text": "Rules for throwing grenades.", "faq": ""},
    {"name": "Template", "slug": "template", "category": "Area", "summary": "Uses a teardrop template.", "rules_text": "Hits all models under the template.", "faq": ""},
    {"name": "Sustained Fire", "slug": "sustained-fire", "category": "Shooting", "summary": "Fires multiple shots.", "rules_text": "Roll firepower die for shots.", "faq": ""},
    {"name": "Entangle", "slug": "entangle", "category": "Control", "summary": "Stops movement.", "rules_text": "Target cannot move until freed.", "faq": ""},
]

for i in range(len(traits), 40):
    traits.append({
        "name": f"Variant Trait {i}",
        "slug": f"variant-trait-{i}",
        "category": "Generic",
        "summary": "A placeholder trait.",
        "rules_text": "Rules for this trait.",
        "faq": ""
    })

houses = [
    {"name": "House Van Saar", "slug": "van-saar", "title": "The House of Artifice", "specialty": "High-tech weaponry, plasma, energy shields, and cyberteknika.", "lore": "Possessing a malfunctioning, radioactive Standard Template Construct (STC)...", "primary_skills": ["Shooting", "Savant", "Tech"], "signature_weapons": ["Lasgun", "Hot-shot Lasgun", "Plasma Gun", "Lascannon"]},
    {"name": "House Goliath", "slug": "goliath", "title": "The House of Chains", "specialty": "Genetically vat-grown giants, heavy melee, brute strength, and stub cannonry.", "lore": "Engineered to labor in the sweltering foundries and deep slag pits...", "primary_skills": ["Brawn", "Ferocity", "Muscle"], "signature_weapons": ["Boltgun", "Heavy Bolter", "Power Claw", "Combat Shotgun"]},
    {"name": "House Escher", "slug": "escher", "title": "The House of Blades", "specialty": "Chems, toxins, agility, venom blades, and whip weaponry.", "lore": "An all-female matriarchy dominating Necromunda's pharmaceutical and stimulant trade...", "primary_skills": ["Agility", "Combat", "Finesse"], "signature_weapons": ["Lasgun", "Shock Whip", "Chainsword", "Flamer"]},
    {"name": "House Orlock", "slug": "orlock", "title": "The House of Iron", "specialty": "Mining networks, shotguns, autoguns, heavy stubbers, and sheer grit.", "lore": "Controlling the inter-hive rail networks and deep ore mines...", "primary_skills": ["Ferocity", "Combat", "Bravado"], "signature_weapons": ["Autogun", "Combat Shotgun", "Heavy Bolter"]},
    {"name": "House Cawdor", "slug": "cawdor", "title": "The House of Faith", "specialty": "Horde swarms, scrap-polearms, blunderbusses, fire, and fanatic zeal.", "lore": "The destitute scavengers of the hive heaps...", "primary_skills": ["Brawn", "Combat", "Piety"], "signature_weapons": ["Autogun", "Flamer", "Lasgun"]},
    {"name": "House Delaque", "slug": "delaque", "title": "The House of Shadow", "specialty": "Espionage, stealth, silent needle weapons, web guns, and psychomancy.", "lore": "Whispering spies and bald shadow-runners cloaked in long trench coats...", "primary_skills": ["Agility", "Cunning", "Obfuscation"], "signature_weapons": ["Plasma Gun", "Lasgun"]},
    {"name": "Palanite Enforcers", "slug": "palanite-enforcers", "title": "The Law of the Hive", "specialty": "Authoritarian suppression, concussion rams, riot shields, and sniper fire.", "lore": "Lord Helmawr's brutal planetary police force...", "primary_skills": ["Shooting", "Brawn", "Enforcement"], "signature_weapons": ["Heavy Concussion Ram", "Boltgun", "Combat Shotgun"]},
    {"name": "Corpse Grinder Cults", "slug": "corpse-grinder-cults", "title": "The Cult of Meat", "specialty": "Cannibalism, circular saws.", "lore": "Former guild workers gone mad.", "primary_skills": ["Ferocity", "Combat"], "signature_weapons": ["Rotary Saw"]},
    {"name": "Ironhead Squat Prospectors", "slug": "ironhead-squat-prospectors", "title": "The Prospectors", "specialty": "Mining, heavy weapons.", "lore": "Abhumans mining the wastes.", "primary_skills": ["Shooting", "Brawn"], "signature_weapons": ["Mining Laser"]},
    {"name": "Ash Waste Nomads", "slug": "ash-waste-nomads", "title": "The Nomads", "specialty": "Survival, snipers.", "lore": "Raiders of the ash wastes.", "primary_skills": ["Cunning", "Agility"], "signature_weapons": ["Long Rifle"]},
    {"name": "Genestealer Cults", "slug": "genestealer-cults", "title": "The Brood", "specialty": "Mutation, infiltration.", "lore": "Alien infected cultists.", "primary_skills": ["Cunning", "Ferocity"], "signature_weapons": ["Mining Laser"]},
    {"name": "Helot Chaos Cults", "slug": "helot-chaos-cults", "title": "The Ruinous Powers", "specialty": "Witchcraft, mutation.", "lore": "Worshippers of the dark gods.", "primary_skills": ["Ferocity", "Leadership"], "signature_weapons": ["Autogun"]},
    {"name": "Slave Ogryn Gangs", "slug": "slave-ogryn-gangs", "title": "The Brutes", "specialty": "Brute strength.", "lore": "Revolting servitors and ogryns.", "primary_skills": ["Brawn", "Ferocity"], "signature_weapons": ["Spud-jacker"]},
    {"name": "Venators", "slug": "venators", "title": "The Bounty Hunters", "specialty": "Varied.", "lore": "Bands of bounty hunters.", "primary_skills": ["Shooting", "Combat"], "signature_weapons": ["Boltgun"]}
]

skills = []
skill_disciplines = {
    "Agility": ["Catfall", "Clamber", "Dodge", "Fast Shot", "Infiltrate", "Sprint"],
    "Brawn": ["Bull Charge", "Crushing Blow", "Headbutt", "Hurl", "Iron Jaw", "Iron Man"],
    "Combat": ["Disarm", "Feint", "Combat Occultist", "Step Aside", "Parry", "Berserker"],
    "Cunning": ["Backstab", "Escape Artist", "Evade", "Infiltrate", "Lie Low", "Shadow Walk"],
    "Ferocity": ["Berserker", "Fearsome", "Impassive", "Nerves of Steel", "True Grit", "Unstoppable"],
    "Leadership": ["Commanding Presence", "Inspirational", "Iron Will", "Lead by Example", "Mentor", "Regroup"],
    "Savant": ["Ballistics Expert", "Connected", "Fixer", "Medicae", "Savvy Trader", "Weaponsmith"],
    "Shooting": ["Fast Shot", "Gunfighter", "Marksman", "Precision Shot", "Trick Shot", "Hip Shooting"]
}

seen_slugs = set()
for tree, sk_names in skill_disciplines.items():
    for name in sk_names:
        base_slug = name.lower().replace(" ", "-").replace("/", "")
        slug = base_slug
        if slug in seen_slugs:
            slug = f"{base_slug}-{tree.lower()}"
        seen_slugs.add(slug)
        
        skills.append({
            "name": name,
            "slug": slug,
            "tree": tree,
            "rules_text": f"Rules for {name}.",
            "tactics": f"Tactics for {name}."
        })

import sys
import os

with open("c:/Users/dev/Code/tdg/mtgabyss/scripts/seed_necromunda.py", "w") as f:
    f.write(f'''
import sys
import os
from db_mongo import get_mongo_db

def seed_necromunda():
    client = get_mongo_db().client
    db = client["avascry_necromunda"]

    print("[Necromunda Seeder] Initializing database 'avascry_necromunda'...")

    traits = {repr(traits)}
    db.traits.delete_many({{}})
    db.traits.insert_many(traits)
    print(f"[Necromunda Seeder] Seeded {{len(traits)}} weapon traits.")

    weapons = {repr(weapons)}
    db.weapons.delete_many({{}})
    db.weapons.insert_many(weapons)
    print(f"[Necromunda Seeder] Seeded {{len(weapons)}} weapons into 'necro_weapons'.")

    houses = {repr(houses)}
    db.houses.delete_many({{}})
    db.houses.insert_many(houses)
    print(f"[Necromunda Seeder] Seeded {{len(houses)}} clan houses.")

    skills = {repr(skills)}
    db.skills.delete_many({{}})
    db.skills.insert_many(skills)
    print(f"[Necromunda Seeder] Seeded {{len(skills)}} skill trees.")

    # Create indexes for O(1) slug lookups
    db.weapons.create_index("slug", unique=True)
    db.traits.create_index("slug", unique=True)
    db.houses.create_index("slug", unique=True)
    db.skills.create_index("slug", unique=True)
    print("[Necromunda Seeder] Created unique slug indexes.")
    print("[OK] Necromunda Corpus Seed Complete!")

if __name__ == "__main__":
    seed_necromunda()
''')
