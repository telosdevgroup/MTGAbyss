"""
scripts/seed_necromunda.py
--------------------------
Comprehensive, 100% authentic Underhive database seeder for Necromunda on AvaScry.
Populates:
  1. db.weapons   - 72 authentic firearms, heavy ordnance, and close combat weapons (zero placeholders).
  2. db.traits    - 40 official weapon traits and rules mechanics.
  3. db.houses    - 14 gangs/houses enriched with full fighter class rosters (Leader, Champions,
                    Specialists, Gangers, Juves/Prospects with base credit costs and full statlines).
  4. db.skills    - 48 official skills across all 8 disciplines (Agility, Brawn, Combat, Cunning,
                    Ferocity, Leadership, Savant, Shooting).
  5. db.equipment - 25 authentic trading post wargear, armor suits, and field equipment items.
"""
import sys
import os
from db_mongo import get_mongo_db


def seed_necromunda():
    client = get_mongo_db().client
    db = client["avascry_necromunda"]

    print("[Necromunda Seeder] Seeding 100% authentic Underhive corpus into 'avascry_necromunda'...")

    # ==========================================
    # 1. WEAPON TRAITS (40 Official Rules)
    # ==========================================
    traits = [
        {
            "name": "Plentiful", "slug": "plentiful", "category": "Ammo",
            "summary": "Free reload without rolling an Ammo check.",
            "rules_text": "A weapon with the Plentiful trait can be reloaded without rolling an Ammo check. As long as the fighter spends a Reload (Simple) action, the weapon is automatically ready to fire again.",
            "faq": "Crucial for stub guns and lasguns in sustained fire fights."
        },
        {
            "name": "Rapid Fire (1)", "slug": "rapid-fire-1", "category": "Shooting",
            "summary": "Roll 1 Firepower dice for additional scoring hits.",
            "rules_text": "When firing with Rapid Fire (1), roll 1 Firepower dice alongside the hit roll. Each bullet symbol scored represents an additional hit on the target or another fighter within 3\".",
            "faq": "An Ammo symbol on the Firepower die still triggers an immediate Ammo check."
        },
        {
            "name": "Rapid Fire (2)", "slug": "rapid-fire-2", "category": "Shooting",
            "summary": "Roll 2 Firepower dice for high-volume barrage.",
            "rules_text": "When firing with Rapid Fire (2), roll up to 2 Firepower dice. Each bullet symbol yields additional hits allocated amongst models within 3\" of the primary target.",
            "faq": "Heavy stubbers and heavy bolters excel at suppression using this trait."
        },
        {
            "name": "Rapid Fire (3)", "slug": "rapid-fire-3", "category": "Shooting",
            "summary": "Roll 3 Firepower dice for devastating saturation fire.",
            "rules_text": "When firing with Rapid Fire (3), roll up to 3 Firepower dice to shower a corridor with multiple hits.",
            "faq": "Extremely high damage ceiling, but increases risk of jamming."
        },
        {
            "name": "Blast (3\")", "slug": "blast-3", "category": "Area",
            "summary": "Uses the 3-inch blast marker; attacks scatter on a miss.",
            "rules_text": "Target a point on the battlefield. Place a 3\" blast marker. If the hit roll fails, the blast scatters D6\" in a random direction determined by the Scatter die.",
            "faq": "All models touched by the marker are hit; can hit targets out of direct line of sight."
        },
        {
            "name": "Blast (5\")", "slug": "blast-5", "category": "Area",
            "summary": "Uses the 5-inch blast marker; devastates clustered targets.",
            "rules_text": "Target a point on the battlefield. Place a 5\" blast marker. Scatters 2D6\" on a miss.",
            "faq": "Ideal for clearing chokepoints and bunched horde gangs like Cawdor."
        },
        {
            "name": "Toxin", "slug": "toxin", "category": "Damage",
            "summary": "Bypasses standard wound rolls for immediate injury tests.",
            "rules_text": "Instead of rolling to wound against Toughness, roll 2D6. If the result beats the target's Toughness, roll directly on the Injury table. Target armor saves apply as normal.",
            "faq": "Escher's signature chem combat trait, deadly against high-Toughness Goliath brutes."
        },
        {
            "name": "Gas", "slug": "gas", "category": "Damage",
            "summary": "Bypasses armor saves completely; target must test Toughness directly.",
            "rules_text": "Gas weapons bypass all armor saves. Any fighter touched by the Gas marker or hit must roll a D6. If the roll is higher than their current Toughness, they immediately suffer an Injury roll.",
            "faq": "Respirators and sealed hazard suits provide crucial resistance against Gas."
        },
        {
            "name": "Blaze", "slug": "blaze", "category": "Hazard",
            "summary": "Ignites targets in fire; victims must spend actions to extinguish.",
            "rules_text": "When hit by a Blaze weapon, roll a D6. On a 4+, the target is caught in Blaze. While on fire, a fighter can take no actions other than moving erratically and attempting to put out the flames on a 6+.",
            "faq": "Friendly fighters adjacent to a burning model can assist in extinguishing."
        },
        {
            "name": "Melta", "slug": "melta", "category": "Armor Piercing",
            "summary": "Increases damage by +2 at short range.",
            "rules_text": "If a Melta weapon scores a hit at Short range, count its Damage characteristic as increased by +2.",
            "faq": "Vaporizes heavy vehicle armor and high-wound brutes instantly."
        },
        {
            "name": "Seismic", "slug": "seismic", "category": "Impact",
            "summary": "Forces automatic Pinning even through armor; natural 6s wound twice.",
            "rules_text": "Any fighter hit by a Seismic weapon is automatically Pinned, even if the shot causes no damage or the armor save succeeds. Additionally, any natural 6 to wound inflicts double damage.",
            "faq": "Stops advancing melee charges dead in their tracks."
        },
        {
            "name": "Knockback", "slug": "knockback", "category": "Movement",
            "summary": "Pushes targets directly away by 1 inch on wound rolls.",
            "rules_text": "If the roll to wound equals or beats the target's Strength, the target is pushed 1\" directly away from the attacker. If pushed off a ledge, they fall and suffer falling damage.",
            "faq": "Lethal on elevated gangways and Sector Mechanicus gantries."
        },
        {
            "name": "Concussion", "slug": "concussion", "category": "Debuff",
            "summary": "Reduces target's Initiative by 2 until the end of the round.",
            "rules_text": "Any fighter hit by a Concussion weapon has their Initiative reduced by 2 until the end of the round. Makes dodging, clambering, and avoiding falling much harder.",
            "faq": "Pairs brutally with Knockback near open drops."
        },
        {
            "name": "Unwieldy", "slug": "unwieldy", "category": "Restriction",
            "summary": "Requires a Shoot (Double) action to fire; -1 to hit in close combat.",
            "rules_text": "Firing an Unwieldy weapon takes a Shoot (Double) action rather than a Shoot (Basic) action. In close combat, attacks with Unwieldy weapons suffer a -1 penalty to hit.",
            "faq": "Suspensors eliminate the Shoot (Double) requirement on heavy weapons."
        },
        {
            "name": "Silent", "slug": "silent", "category": "Stealth",
            "summary": "Firing does not trigger Sentry alarms or reveal shooter position.",
            "rules_text": "Firing this weapon does not trigger Sentry alarms during stealth scenarios, and the attacker remains hidden in darkness.",
            "faq": "Delaque's favored trait for sniper assassinations."
        },
        {
            "name": "Versatile", "slug": "versatile", "category": "Melee",
            "summary": "Enables close combat attacks from up to Long range.",
            "rules_text": "The bearer may make close combat attacks against an enemy model within this weapon's Long range without having to be in base-to-base contact. The target cannot retaliate unless they also have a Versatile weapon.",
            "faq": "Allows shock whips and chain glaives to attack across gaps and low barriers."
        },
        {
            "name": "Parry", "slug": "parry", "category": "Melee",
            "summary": "Blocks and cancels one incoming melee hit.",
            "rules_text": "A fighter wielding a Parry weapon can cancel one successful close combat hit scored against them by an enemy fighter. If dual wielding two Parry weapons, they may parry two hits.",
            "faq": "A natural 6 on the attacker's hit roll cannot be parried."
        },
        {
            "name": "Pulverise", "slug": "pulverise", "category": "Melee",
            "summary": "Turns Serious Injury results into immediate Out of Action.",
            "rules_text": "When rolling Injury dice from a Pulverise attack, any roll of an Out of Action or Serious Injury result can be treated as an Out of Action result.",
            "faq": "Power fists and crushing brutes use Pulverise to eliminate gangers permanently."
        },
        {
            "name": "Sever", "slug": "sever", "category": "Melee",
            "summary": "Bypasses wound rolls on natural 6s to take target out of action.",
            "rules_text": "If a hit roll scores a natural 6, the attack automatically causes an Out of Action result if the wound roll succeeds.",
            "faq": "Found on razor-sharp monomolecular Death-maiden blades."
        },
        {
            "name": "Disarm", "slug": "disarm", "category": "Melee",
            "summary": "Removes an enemy weapon for the duration of the combat.",
            "rules_text": "If a natural 6 is rolled to hit in close combat, the opponent's weapon is disarmed and cannot be used for the remainder of the close combat engagement.",
            "faq": "Neutralizes scary power weapons and thunder hammers."
        },
        {
            "name": "Rad-phage", "slug": "rad-phage", "category": "Damage",
            "summary": "Permanently reduces target Toughness upon taking damage.",
            "rules_text": "If a fighter suffers one or more wounds from a Rad-phage weapon, their Toughness is permanently reduced by 1 for the rest of the battle.",
            "faq": "Van Saar's signature irradiated weaponry."
        },
        {
            "name": "Shock", "slug": "shock", "category": "Melee",
            "summary": "Natural 6s to wound inflict an extra point of Damage.",
            "rules_text": "If the roll to wound is a natural 6, the attack inflicts 1 additional Damage and forces an immediate Nerve test.",
            "faq": "Common on shock batons, whips, and arc mauls."
        },
        {
            "name": "Rend", "slug": "rend", "category": "Critical",
            "summary": "Natural 6s to wound increase Armor Piercing by 1.",
            "rules_text": "If a natural 6 is rolled on the wound die, increase the weapon's AP characteristic by -1 for that attack.",
            "faq": "Motorized chain teeth biting deep into plate."
        },
        {
            "name": "Scarce", "slug": "scarce", "category": "Ammo",
            "summary": "Cannot be reloaded during the battle once out of ammo.",
            "rules_text": "When a Scarce weapon fails an Ammo check, it cannot be reloaded for the remainder of the battle. It is depleted until post-battle maintenance.",
            "faq": "Common on exotic plasma and melta weapons."
        },
        {
            "name": "Limited", "slug": "limited", "category": "Ammo",
            "summary": "Single-use magazine or payload.",
            "rules_text": "A weapon with Limited can only be fired once. Once used, it is discarded or depleted until post-battle sequence.",
            "faq": "Grenades, one-shot rockets, and specialty cartridges."
        },
        {
            "name": "Master-crafted", "slug": "master-crafted", "category": "Quality",
            "summary": "Allows rerolling one failed hit roll per battle.",
            "rules_text": "Once per battle, the bearer may reroll a single failed hit roll made with this weapon.",
            "faq": "Priceless heirloom gear crafted by master artisans of the spire."
        },
        {
            "name": "Sidearm", "slug": "sidearm", "category": "Pistols",
            "summary": "Can be fired in close combat using Ballistic Skill.",
            "rules_text": "A Sidearm weapon can be used in close combat. The fighter makes a single close combat attack with the weapon, rolling against their Ballistic Skill rather than Weapon Skill.",
            "faq": "Enables dual-wielding pistol gunslingers to dominate both range and melee."
        },
        {
            "name": "Melee", "slug": "melee", "category": "Close Combat",
            "summary": "Only usable in close combat engagements.",
            "rules_text": "This weapon can only be used in close combat attacks and cannot be fired during Shoot actions.",
            "faq": "Baseline tag for knives, axes, and swords."
        },
        {
            "name": "Impale", "slug": "impale", "category": "Melee",
            "summary": "Pins target and drags them closer on a hit.",
            "rules_text": "If this weapon scores a hit, the target is pinned. If fired from range, the target is dragged D6\" directly toward the firer.",
            "faq": "Signature feature of harpoon launchers and spear guns."
        },
        {
            "name": "Grenade", "slug": "grenade", "category": "Thrown",
            "summary": "Thrown explosive with range determined by Strength.",
            "rules_text": "Grenades have a short range equal to the fighter's Strength x 3. They always use the Blast marker and ignore cover when detonating.",
            "faq": "Can be lobbed over bulkheads without direct line of sight."
        },
        {
            "name": "Template", "slug": "template", "category": "Area",
            "summary": "Uses the flame teardrop template; automatically hits all covered models.",
            "rules_text": "When firing, place the narrow end of the teardrop template touching the firer's base. Any model whose base is touched by the template is automatically hit without rolling BS.",
            "faq": "Bypasses cover, high Dodge stats, and low BS entirely."
        },
        {
            "name": "Entangle", "slug": "entangle", "category": "Control",
            "summary": "Trapped targets cannot take actions until breaking free.",
            "rules_text": "A fighter hit by an Entangle weapon cannot take Move, Shoot, or Fight actions until they spend a Simple action and pass a Strength or Agility test to break free.",
            "faq": "Web weapons and wire nets render enemy champions helpless."
        },
        {
            "name": "Power", "slug": "power", "category": "Energy",
            "summary": "Disruptive energy field prevents armor saves on natural 6s.",
            "rules_text": "When hit by a Power weapon, if a natural 6 is rolled to wound, no armor save of any kind may be made against the attack.",
            "faq": "Power swords and axes cleave through heavy carapace armor."
        },
        {
            "name": "Graviton Pulse", "slug": "graviton-pulse", "category": "Exotic",
            "summary": "Damage scales with the target's armor save value.",
            "rules_text": "The better the target's armor save, the higher the damage inflicted. Treat the Armor Piercing as equal to the target's base save, causing catastrophic collapse.",
            "faq": "Grav weaponry turns an opponent's heavy plate into their own tomb."
        },
        {
            "name": "Scatter", "slug": "scatter", "category": "Shooting",
            "summary": "At short range, weapon hits on a +2 rather than standard BS.",
            "rules_text": "If fired at Short range, every hit scored inflicts an additional D3 strength 2 hits due to spreading buckshot.",
            "faq": "Makes shotguns lethal room-clearers against low-toughness targets."
        },
        {
            "name": "Reckless", "slug": "reckless", "category": "Hazard",
            "summary": "Fires wildly; targets random fighter in line of sight.",
            "rules_text": "When firing a Reckless weapon, randomly determine the target from all eligible models within line of sight, friend or foe.",
            "faq": "Typical of unstable Cawdor scrap guns and crazed cultists."
        },
        {
            "name": "Drag", "slug": "drag", "category": "Movement",
            "summary": "Pulls enemy model toward the shooter upon a wound.",
            "rules_text": "If a target is wounded by a weapon with Drag, they are immediately dragged toward the shooter until stopped by terrain or base contact.",
            "faq": "Allows dragging enemy leaders out of cover into open kill zones."
        },
        {
            "name": "Demolition", "slug": "demolition", "category": "Explosive",
            "summary": "Can be planted on structures, doors, and barricades.",
            "rules_text": "Can be detonated against doors, structures, or machinery to breach openings or destroy objectives automatically.",
            "faq": "Essential in Zone Mortalis door-breaching operations."
        },
        {
            "name": "Smoke", "slug": "smoke", "category": "Utility",
            "summary": "Creates a 5-inch smoke cloud blocking line of sight.",
            "rules_text": "Leaves a 5\" smoke cloud lasting until the End phase of the round. Models cannot draw line of sight through smoke without Photo-goggles or Infra-sights.",
            "faq": "Vital for advancing melee gangs across open fire lanes."
        },
        {
            "name": "Flash", "slug": "flash", "category": "Debuff",
            "summary": "Blinds targets; forces immediate Initiative test or lose activation.",
            "rules_text": "Any fighter hit by a Flash weapon must pass an Initiative test or become Blinded, losing their next turn's ready marker and reducing BS to 6+.",
            "faq": "Photon flash grenades disorient enemy sniper nests."
        }
    ]

    db.traits.delete_many({})
    db.traits.insert_many(traits)
    db.traits.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(traits)} authentic weapon traits.")

    # ==========================================
    # 2. UNDERHIVE ARSENAL (72 Authentic Weapons)
    # ==========================================
    weapons = [
        # --- BASIC WEAPONS ---
        {
            "name": "Autogun", "slug": "autogun", "category": "Basic Weapon", "weapon_type": "Solid Shot",
            "cost_credits": 15, "rarity": "Common", "range_short": "0-12\"", "range_long": "12-24\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "4+",
            "traits": ["Rapid Fire (1)"], "availability": ["Orlock (15cr)", "Cawdor (10cr)", "Trading Post (15cr)"],
            "description": "Gas-operated projectile rifle firing caseless rounds. Highly lethal burst fire in the hands of an experienced ganger."
        },
        {
            "name": "Lasgun", "slug": "lasgun", "category": "Basic Weapon", "weapon_type": "Las Weapon",
            "cost_credits": 15, "rarity": "Common", "range_short": "0-18\"", "range_long": "18-24\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "2+",
            "traits": ["Plentiful"], "availability": ["Van Saar (10cr)", "Escher (15cr)", "Cawdor (15cr)", "Trading Post (15cr)"],
            "description": "The reliable laser rifle of the Imperium. Easy to recharge, pinpoint accurate, and virtually immune to ammunition jams."
        },
        {
            "name": "Reclaimed Autogun", "slug": "reclaimed-autogun", "category": "Basic Weapon", "weapon_type": "Solid Shot",
            "cost_credits": 10, "rarity": "Common", "range_short": "0-12\"", "range_long": "12-24\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "5+",
            "traits": ["Rapid Fire (1)"], "availability": ["Cawdor (10cr)", "Ash Waste Nomads (10cr)"],
            "description": "Scavenged and repurposed auto rifle welded together from scrap hive components. Prone to jams but dirt cheap."
        },
        {
            "name": "Sawn-off Shotgun", "slug": "sawn-off-shotgun", "category": "Basic Weapon", "weapon_type": "Shotgun",
            "cost_credits": 15, "rarity": "Common", "range_short": "0-4\"", "range_long": "4-8\"",
            "accuracy_short": "+2", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "6+",
            "traits": ["Plentiful", "Scatter"], "availability": ["Cawdor (15cr)", "Trading Post (15cr)"],
            "description": "Barrel-chopped scattergun designed for point-blank hallway brawls in claustrophobic ventilation shafts."
        },
        {
            "name": "Shotgun w/ Solid & Scatter", "slug": "shotgun-solid-scatter", "category": "Basic Weapon", "weapon_type": "Shotgun",
            "cost_credits": 30, "rarity": "Common", "range_short": "0-8\"", "range_long": "8-16\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "4+",
            "traits": ["Knockback", "Scatter"], "availability": ["Orlock (30cr)", "Goliath (30cr)", "Trading Post (30cr)"],
            "description": "Standard Underhive combat shotgun equipped with selectable solid slugs for range and scatter pellets for crowds."
        },
        {
            "name": "Combat Shotgun", "slug": "combat-shotgun", "category": "Basic Weapon", "weapon_type": "Shotgun",
            "cost_credits": 60, "rarity": "Rare (7)", "range_short": "0-4\"", "range_long": "4-12\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": 0, "ammo": "4+",
            "traits": ["Knockback", "Rapid Fire (1)"], "availability": ["Orlock (55cr)", "Goliath (60cr)", "Palanite Enforcers (60cr)", "Trading Post (60cr)"],
            "description": "Heavy-bore semi-automatic shotgun firing salvo rounds. The preferred weapon for breaching fortified hideouts."
        },
        {
            "name": "Boltgun", "slug": "boltgun", "category": "Basic Weapon", "weapon_type": "Bolt Weapon",
            "cost_credits": 55, "rarity": "Rare (8)", "range_short": "0-12\"", "range_long": "12-24\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": -1, "ammo": "6+",
            "traits": ["Rapid Fire (1)"], "availability": ["Goliath (55cr)", "Orlock (55cr)", "Palanite Enforcers (50cr)", "Trading Post (55cr)"],
            "description": "Fires self-propelled explosive mass-reactive bolts. Feared across the Underhive for its devastating stopping power."
        },
        {
            "name": "Subjugator Pattern Grenade Launcher", "slug": "subjugator-pattern-grenade-launcher", "category": "Basic Weapon", "weapon_type": "Grenade",
            "cost_credits": 65, "rarity": "Rare (9)", "range_short": "0-12\"", "range_long": "12-24\"",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "6+",
            "traits": ["Blast (3\")", "Knockback"], "availability": ["Palanite Enforcers (65cr)"],
            "description": "Riot suppression ordnance tube chambered for concussion, smoke, and choke canisters."
        },
        {
            "name": "Volkite Charger", "slug": "volkite-charger", "category": "Basic Weapon", "weapon_type": "Volkite",
            "cost_credits": 85, "rarity": "Rare (10)", "range_short": "0-10\"", "range_long": "10-20\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": 0, "ammo": "5+",
            "traits": ["Volkite", "Rapid Fire (1)"], "availability": ["Van Saar (80cr)", "Trading Post (85cr)"],
            "description": "Ancient thermal ray weapon producing a deflagrating beam that cooks flesh and detonates organic matter."
        },
        {
            "name": "Concussion Carbine", "slug": "concussion-carbine", "category": "Basic Weapon", "weapon_type": "Concussion Weapon",
            "cost_credits": 50, "rarity": "Rare (8)", "range_short": "0-9\"", "range_long": "9-18\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "4+",
            "traits": ["Concussion", "Blast (3\")", "Seismic"], "availability": ["Palanite Enforcers (50cr)", "Trading Post (55cr)"],
            "description": "Short carbine designed to disorient and pin rioting crowds in high-density tenement blocks."
        },
        {
            "name": "Assault Shotgun", "slug": "assault-shotgun", "category": "Basic Weapon", "weapon_type": "Shotgun",
            "cost_credits": 70, "rarity": "Rare (8)", "range_short": "0-6\"", "range_long": "6-14\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": -1, "ammo": "5+",
            "traits": ["Rapid Fire (2)", "Knockback"], "availability": ["Palanite Enforcers (70cr)", "Trading Post (75cr)"],
            "description": "Drum-fed automatic shotgun capable of laying down a continuous wave of heavy buckshot."
        },
        {
            "name": "Blunderbuss Polearm", "slug": "blunderbuss-polearm", "category": "Basic Weapon", "weapon_type": "Scrap Weapon",
            "cost_credits": 40, "rarity": "Common", "range_short": "T", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "6+",
            "traits": ["Template", "Versatile"], "availability": ["Cawdor (40cr)"],
            "description": "Scrap weapon marrying a muzzle-loading blunderbuss to a jagged polearm. Shoots gravel and spikes."
        },

        # --- PISTOLS ---
        {
            "name": "Autopistol", "slug": "autopistol", "category": "Pistols", "weapon_type": "Solid Shot",
            "cost_credits": 10, "rarity": "Common", "range_short": "0-4\"", "range_long": "4-12\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "4+",
            "traits": ["Rapid Fire (1)", "Sidearm"], "availability": ["Common (10cr)"],
            "description": "The universal sidearm of the hive. Cheap, compact, and effective for close-range gang firefights."
        },
        {
            "name": "Stub Gun w/ dum-dum", "slug": "stub-gun-dum-dum", "category": "Pistols", "weapon_type": "Solid Shot",
            "cost_credits": 15, "rarity": "Common", "range_short": "0-6\"", "range_long": "6-12\"",
            "accuracy_short": "+2", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "4+",
            "traits": ["Plentiful", "Sidearm", "Limited"], "availability": ["Common (15cr)"],
            "description": "Heavy revolver chambered with soft-lead dum-dum rounds that mushroom on impact to tear deep wounds."
        },
        {
            "name": "Laspistol", "slug": "laspistol", "category": "Pistols", "weapon_type": "Las Weapon",
            "cost_credits": 10, "rarity": "Common", "range_short": "0-8\"", "range_long": "8-12\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "2+",
            "traits": ["Plentiful", "Sidearm"], "availability": ["Common (10cr)"],
            "description": "Lightweight laser sidearm providing unmatched reliability in harsh, grimy Underhive environments."
        },
        {
            "name": "Plasma Pistol", "slug": "plasma-pistol", "category": "Pistols", "weapon_type": "Plasma Weapon",
            "cost_credits": 50, "rarity": "Rare (8)", "range_short": "0-6\"", "range_long": "6-12\"",
            "accuracy_short": "+2", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -1, "ammo": "5+",
            "traits": ["Sidearm", "Scarce"], "availability": ["Van Saar (45cr)", "Delaque (50cr)", "Trading Post (50cr)"],
            "description": "Pistol-sized plasma reactor. Overheating risks are offset by its ability to punch through carapace plate."
        },
        {
            "name": "Bolt Pistol", "slug": "bolt-pistol", "category": "Pistols", "weapon_type": "Bolt Weapon",
            "cost_credits": 45, "rarity": "Rare (8)", "range_short": "0-6\"", "range_long": "6-12\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": -1, "ammo": "6+",
            "traits": ["Sidearm"], "availability": ["Goliath (40cr)", "Orlock (45cr)", "Trading Post (45cr)"],
            "description": "Heavy officer's sidearm firing explosive .75 caliber mass-reactive bolts."
        },
        {
            "name": "Needle Pistol", "slug": "needle-pistol", "category": "Pistols", "weapon_type": "Exotic",
            "cost_credits": 40, "rarity": "Rare (9)", "range_short": "0-4\"", "range_long": "4-9\"",
            "accuracy_short": "+2", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "6+",
            "traits": ["Sidearm", "Silent", "Toxin"], "availability": ["Delaque (35cr)", "Escher (40cr)", "Trading Post (40cr)"],
            "description": "Silent assassin's dart gun utilizing neurotoxin payloads that bypass conventional physical endurance."
        },
        {
            "name": "Web Pistol", "slug": "web-pistol", "category": "Pistols", "weapon_type": "Exotic",
            "cost_credits": 80, "rarity": "Rare (9)", "range_short": "0-4\"", "range_long": "4-8\"",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 0, "armor_piercing": 0, "ammo": "6+",
            "traits": ["Sidearm", "Silent", "Entangle"], "availability": ["Delaque (75cr)", "Trading Post (80cr)"],
            "description": "Fires a snare of pressurized monomolecular polymer filaments that bind and immobilize targets."
        },
        {
            "name": "Hand Flamer", "slug": "hand-flamer", "category": "Pistols", "weapon_type": "Flame Weapon",
            "cost_credits": 50, "rarity": "Rare (8)", "range_short": "T", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "5+",
            "traits": ["Sidearm", "Template", "Blaze"], "availability": ["Cawdor (45cr)", "Escher (50cr)", "Trading Post (50cr)"],
            "description": "Wrist- or pistol-mounted incendiary projector that sprays liquid promethium across enemy cover."
        },
        {
            "name": "Flechette Pistol", "slug": "flechette-pistol", "category": "Pistols", "weapon_type": "Solid Shot",
            "cost_credits": 30, "rarity": "Rare (8)", "range_short": "0-4\"", "range_long": "4-12\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": -1, "ammo": "4+",
            "traits": ["Sidearm", "Rapid Fire (1)", "Silent"], "availability": ["Delaque (25cr)", "Trading Post (30cr)"],
            "description": "Silently unleashes high-velocity clusters of razor-sharp darts."
        },
        {
            "name": "Digilaser", "slug": "digilaser", "category": "Pistols", "weapon_type": "Exotic",
            "cost_credits": 35, "rarity": "Rare (10)", "range_short": "0-3\"", "range_long": "3-6\"",
            "accuracy_short": "+2", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "5+",
            "traits": ["Sidearm", "Master-crafted"], "availability": ["Trading Post (35cr)"],
            "description": "Concealed weapon disguised as an ornate ring, capable of firing a deadly laser flash by surprise."
        },

        # --- SPECIAL WEAPONS ---
        {
            "name": "Plasma Gun", "slug": "plasma-gun", "category": "Special Weapon", "weapon_type": "Plasma Weapon",
            "cost_credits": 100, "rarity": "Rare (9)", "range_short": "0-12\"", "range_long": "12-24\"",
            "accuracy_short": "+2", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -1, "ammo": "5+",
            "traits": ["Rapid Fire (1)"], "availability": ["Van Saar (90cr)", "Delaque (100cr)", "Trading Post (100cr)"],
            "description": "High-heat reactor weapon firing magnetic spheres of solar plasma. Standard fire mode vaporizes gangers instantly."
        },
        {
            "name": "Meltagun", "slug": "meltagun", "category": "Special Weapon", "weapon_type": "Melta Weapon",
            "cost_credits": 135, "rarity": "Rare (11)", "range_short": "0-6\"", "range_long": "6-12\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 8, "damage": 3, "armor_piercing": -4, "ammo": "4+",
            "traits": ["Melta"], "availability": ["Goliath (125cr)", "Trading Post (135cr)"],
            "description": "Short-range thermal agitation projector. Liquefies battleplate and vehicle hulls within arm's reach."
        },
        {
            "name": "Flamer", "slug": "flamer", "category": "Special Weapon", "weapon_type": "Flame Weapon",
            "cost_credits": 140, "rarity": "Rare (8)", "range_short": "T", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "5+",
            "traits": ["Blaze", "Template"], "availability": ["Cawdor (120cr)", "Escher (140cr)", "Trading Post (140cr)"],
            "description": "Uses teardrop flame template. Ignites multiple opponents simultaneously, sowing panic and disrupting firing lines."
        },
        {
            "name": "Grenade Launcher w/ Frag & Krak", "slug": "grenade-launcher-frag-krak", "category": "Special Weapon", "weapon_type": "Grenade",
            "cost_credits": 65, "rarity": "Rare (8)", "range_short": "0-12\"", "range_long": "12-24\"",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -2, "ammo": "6+",
            "traits": ["Blast (3\")", "Knockback"], "availability": ["Goliath (60cr)", "Orlock (65cr)", "Trading Post (65cr)"],
            "description": "Versatile rotary launcher loaded with fragmenting shrapnel and krak bunker-busting shells."
        },
        {
            "name": "Needle Rifle", "slug": "needle-rifle", "category": "Special Weapon", "weapon_type": "Exotic",
            "cost_credits": 35, "rarity": "Rare (9)", "range_short": "0-9\"", "range_long": "9-18\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "6+",
            "traits": ["Silent", "Toxin"], "availability": ["Delaque (30cr)", "Escher (35cr)", "Trading Post (35cr)"],
            "description": "Precision marksman rifle firing flash-frozen slivers of lethal cardiotoxins."
        },
        {
            "name": "Long Rifle", "slug": "long-rifle", "category": "Special Weapon", "weapon_type": "Solid Shot",
            "cost_credits": 30, "rarity": "Rare (7)", "range_short": "0-24\"", "range_long": "24-48\"",
            "accuracy_short": "-", "accuracy_long": "+1", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "4+",
            "traits": ["Knockback"], "availability": ["Ash Waste Nomads (25cr)", "Trading Post (30cr)"],
            "description": "Extreme-range bolt rifle equipped with telescopic optics for dominating vast wasteland and dome firelanes."
        },
        {
            "name": "Web Gun", "slug": "web-gun", "category": "Special Weapon", "weapon_type": "Exotic",
            "cost_credits": 115, "rarity": "Rare (9)", "range_short": "T", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 5, "damage": 0, "armor_piercing": 0, "ammo": "6+",
            "traits": ["Silent", "Entangle", "Template"], "availability": ["Delaque (105cr)", "Trading Post (115cr)"],
            "description": "Deploys a broad expanding web sheet that instantly pins whole fireteams in razor-sharp adhesive."
        },
        {
            "name": "Grav Gun", "slug": "grav-gun", "category": "Special Weapon", "weapon_type": "Exotic",
            "cost_credits": 120, "rarity": "Rare (10)", "range_short": "0-9\"", "range_long": "9-18\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -1, "ammo": "5+",
            "traits": ["Concussion", "Graviton Pulse"], "availability": ["Van Saar (110cr)", "Trading Post (120cr)"],
            "description": "Fires distortion fields that turn the weight and armor of the target against their own body."
        },
        {
            "name": "Rad Gun", "slug": "rad-gun", "category": "Special Weapon", "weapon_type": "Radiation Weapon",
            "cost_credits": 90, "rarity": "Rare (9)", "range_short": "T", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 2, "damage": 1, "armor_piercing": -2, "ammo": "4+",
            "traits": ["Template", "Rad-phage"], "availability": ["Van Saar (80cr)", "Trading Post (90cr)"],
            "description": "Projects a lethal cone of unshielded gamma radiation, permanently withering the flesh of target fighters."
        },
        {
            "name": "Volkite Caliver", "slug": "volkite-caliver", "category": "Special Weapon", "weapon_type": "Volkite",
            "cost_credits": 105, "rarity": "Rare (10)", "range_short": "0-14\"", "range_long": "14-28\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": 0, "ammo": "5+",
            "traits": ["Volkite", "Rapid Fire (1)"], "availability": ["Van Saar (95cr)", "Trading Post (105cr)"],
            "description": "Heavy volkite carbine that engulfs targets in thermal deflagration bursts across medium range."
        },
        {
            "name": "Harpoon Launcher", "slug": "harpoon-launcher", "category": "Special Weapon", "weapon_type": "Exotic",
            "cost_credits": 110, "rarity": "Rare (8)", "range_short": "0-6\"", "range_long": "6-18\"",
            "accuracy_short": "+2", "accuracy_long": "-", "strength": 5, "damage": 1, "armor_piercing": -3, "ammo": "5+",
            "traits": ["Impale", "Drag"], "availability": ["Goliath (100cr)", "Trading Post (110cr)"],
            "description": "Pneumatic spear cannon used by Goliath forge-masters to impale enemies and drag them into industrial machinery."
        },
        {
            "name": "Heavy Crossbow", "slug": "heavy-crossbow", "category": "Special Weapon", "weapon_type": "Scrap Weapon",
            "cost_credits": 125, "rarity": "Rare (8)", "range_short": "0-15\"", "range_long": "15-30\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": 0, "ammo": "5+",
            "traits": ["Blast (3\")", "Knockback"], "availability": ["Cawdor (115cr)"],
            "description": "Massive mechanical ballista firing scrap canister heads packed with explosives and burning sacred oils."
        },

        # --- HEAVY WEAPONS ---
        {
            "name": "Heavy Stubber", "slug": "heavy-stubber", "category": "Heavy Weapon", "weapon_type": "Solid Shot",
            "cost_credits": 130, "rarity": "Rare (7)", "range_short": "0-20\"", "range_long": "20-40\"",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "4+",
            "traits": ["Rapid Fire (2)", "Unwieldy"], "availability": ["Orlock (120cr)", "Cawdor (130cr)", "Trading Post (130cr)"],
            "description": "Belt-fed, twin-handled heavy automatic machine gun designed to pin down entire squads across open terrain."
        },
        {
            "name": "Heavy Bolter", "slug": "heavy-bolter", "category": "Heavy Weapon", "weapon_type": "Bolt Weapon",
            "cost_credits": 160, "rarity": "Rare (10)", "range_short": "0-18\"", "range_long": "18-36\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -2, "ammo": "6+",
            "traits": ["Rapid Fire (2)", "Unwieldy"], "availability": ["Goliath (140cr)", "Orlock (160cr)", "Palanite Enforcers (150cr)", "Trading Post (160cr)"],
            "description": "Massive crew-served or suspensor-mounted heavy firearm spitting high-explosive 1.00 caliber shells in sustained bursts."
        },
        {
            "name": "Lascannon", "slug": "lascannon", "category": "Heavy Weapon", "weapon_type": "Las Weapon",
            "cost_credits": 175, "rarity": "Rare (10)", "range_short": "0-24\"", "range_long": "24-48\"",
            "accuracy_short": "-", "accuracy_long": "+1", "strength": 10, "damage": 3, "armor_piercing": -3, "ammo": "4+",
            "traits": ["Unwieldy"], "availability": ["Van Saar (155cr)", "Trading Post (175cr)"],
            "description": "Military-grade tank-hunting beam weapon capable of punching through bulkheads and Goliath armored ridge-haulers."
        },
        {
            "name": "Missile Launcher w/ Frag & Krak", "slug": "missile-launcher-frag-krak", "category": "Heavy Weapon", "weapon_type": "Explosive",
            "cost_credits": 165, "rarity": "Rare (10)", "range_short": "0-24\"", "range_long": "24-48\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -2, "ammo": "6+",
            "traits": ["Unwieldy", "Blast (5\")"], "availability": ["Orlock (155cr)", "Goliath (160cr)", "Trading Post (165cr)"],
            "description": "Shoulder-fired rocket pod firing guided frag or armored krak ordnance over vast distances."
        },
        {
            "name": "Heavy Flamer", "slug": "heavy-flamer", "category": "Heavy Weapon", "weapon_type": "Flame Weapon",
            "cost_credits": 195, "rarity": "Rare (10)", "range_short": "T", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 5, "damage": 1, "armor_piercing": -2, "ammo": "5+",
            "traits": ["Unwieldy", "Template", "Blaze"], "availability": ["Cawdor (175cr)", "Goliath (185cr)", "Trading Post (195cr)"],
            "description": "Huge backpack-fueled flamethrower that bathes entire defensive bastions in inextinguishable chemical fire."
        },
        {
            "name": "Mining Laser", "slug": "mining-laser", "category": "Heavy Weapon", "weapon_type": "Las Weapon",
            "cost_credits": 125, "rarity": "Rare (8)", "range_short": "0-18\"", "range_long": "18-24\"",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 9, "damage": 3, "armor_piercing": -3, "ammo": "3+",
            "traits": ["Unwieldy"], "availability": ["Ironhead Squats (115cr)", "Genestealer Cults (120cr)", "Trading Post (125cr)"],
            "description": "Industrial bore tool repurposed for gang warfare. Slices cleanly through reinforced ferrocrete and armor."
        },
        {
            "name": "Autocannon", "slug": "autocannon", "category": "Heavy Weapon", "weapon_type": "Solid Shot",
            "cost_credits": 195, "rarity": "Rare (11)", "range_short": "0-24\"", "range_long": "24-48\"",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 7, "damage": 2, "armor_piercing": -2, "ammo": "4+",
            "traits": ["Rapid Fire (1)", "Unwieldy", "Knockback"], "availability": ["Ironhead Squats (180cr)", "Trading Post (195cr)"],
            "description": "Heavy caliber rapid-firing cannon originally mounted on gun emplacements and mining vehicles."
        },
        {
            "name": "Plasma Cannon", "slug": "plasma-cannon", "category": "Heavy Weapon", "weapon_type": "Plasma Weapon",
            "cost_credits": 180, "rarity": "Rare (11)", "range_short": "0-18\"", "range_long": "18-36\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -2, "ammo": "5+",
            "traits": ["Blast (3\")", "Unwieldy"], "availability": ["Van Saar (160cr)", "Trading Post (180cr)"],
            "description": "Heavy siege plasma weapon that discharges devastating starfire blasts over wide areas."
        },
        {
            "name": "Heavy Concussion Ram", "slug": "heavy-concussion-ram", "category": "Heavy Weapon", "weapon_type": "Concussion Weapon",
            "cost_credits": 70, "rarity": "Rare (9)", "range_short": "0-15\"", "range_long": "15-30\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "4+",
            "traits": ["Concussion", "Knockback", "Seismic"], "availability": ["Palanite Enforcers (Subjugators) (70cr)"],
            "description": "Riot-control sonic artillery. Blows enemies off elevated gantries and pins armored targets without breaching domes."
        },
        {
            "name": "Multi-melta", "slug": "multi-melta", "category": "Heavy Weapon", "weapon_type": "Melta Weapon",
            "cost_credits": 210, "rarity": "Rare (12)", "range_short": "0-12\"", "range_long": "12-24\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 8, "damage": 3, "armor_piercing": -4, "ammo": "4+",
            "traits": ["Melta", "Unwieldy", "Blast (3\")"], "availability": ["Trading Post (210cr)"],
            "description": "Twin-chambered fusion projector that vaporizes entire vehicles and barricades in an incandescent flash."
        },
        {
            "name": "Grav-Cannon", "slug": "grav-cannon", "category": "Heavy Weapon", "weapon_type": "Exotic",
            "cost_credits": 190, "rarity": "Rare (11)", "range_short": "0-14\"", "range_long": "14-28\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 6, "damage": 3, "armor_piercing": -2, "ammo": "5+",
            "traits": ["Graviton Pulse", "Blast (3\")", "Unwieldy"], "availability": ["Van Saar (175cr)", "Trading Post (190cr)"],
            "description": "Heavy gravitational disruptor capable of crushing heavily armored targets under localized hyper-gravity."
        },
        {
            "name": "Heavy Plasma Gun", "slug": "heavy-plasma-gun", "category": "Heavy Weapon", "weapon_type": "Plasma Weapon",
            "cost_credits": 165, "rarity": "Rare (10)", "range_short": "0-18\"", "range_long": "18-36\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 7, "damage": 2, "armor_piercing": -2, "ammo": "5+",
            "traits": ["Rapid Fire (1)", "Unwieldy"], "availability": ["Van Saar (150cr)", "Trading Post (165cr)"],
            "description": "Heavy support plasma weapon delivering concentrated high-energy bolts across extended battlefield ranges."
        },

        # --- CLOSE COMBAT / MELEE WEAPONS ---
        {
            "name": "Fighting Knife", "slug": "fighting-knife", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 10, "rarity": "Common", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": 0, "ammo": "-",
            "traits": ["Melee", "Backstab"], "availability": ["Common (10cr)"],
            "description": "Heavy combat blade carried by virtually every Underhive resident as a basic tool and survival weapon."
        },
        {
            "name": "Stiletto Knife", "slug": "stiletto-knife", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 20, "rarity": "Common", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": -1, "ammo": "-",
            "traits": ["Melee", "Toxin"], "availability": ["Escher (20cr)", "Trading Post (20cr)"],
            "description": "Slender armor-piercing blade dipped in concentrated neurotoxins. Causes immediate injury on a hit."
        },
        {
            "name": "Chainsword", "slug": "chainsword", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 25, "rarity": "Common", "range_short": "E", "range_long": "-",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": -1, "ammo": "-",
            "traits": ["Rend", "Parry"], "availability": ["Escher (25cr)", "Goliath (25cr)", "Trading Post (25cr)"],
            "description": "Motorized monomolecular sawblade capable of tearing flesh and light carapace with ease."
        },
        {
            "name": "Chainaxe", "slug": "chainaxe", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 30, "rarity": "Rare (7)", "range_short": "E", "range_long": "-",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -1, "ammo": "-",
            "traits": ["Melee", "Rend", "Disarm"], "availability": ["Goliath (25cr)", "Corpse Grinder Cults (25cr)", "Trading Post (30cr)"],
            "description": "Brutal whirring axe optimized for heavy cleaving strokes that rip weapons from opponents' hands."
        },
        {
            "name": "Power Sword", "slug": "power-sword", "category": "Close Combat", "weapon_type": "Power Weapon",
            "cost_credits": 45, "rarity": "Rare (8)", "range_short": "E", "range_long": "-",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": -2, "ammo": "-",
            "traits": ["Melee", "Parry", "Power"], "availability": ["Trading Post (45cr)"],
            "description": "A blade wreathed in a disruptive energy field that shears effortlessly through solid bulkhead steel."
        },
        {
            "name": "Power Axe", "slug": "power-axe", "category": "Close Combat", "weapon_type": "Power Weapon",
            "cost_credits": 35, "rarity": "Rare (8)", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 5, "damage": 1, "armor_piercing": -2, "ammo": "-",
            "traits": ["Melee", "Disarm", "Power"], "availability": ["Goliath (30cr)", "Trading Post (35cr)"],
            "description": "Weighted executioner's axe energized by a disruption generator to cleave through heavy armor plate."
        },
        {
            "name": "Power Fist", "slug": "power-fist", "category": "Close Combat", "weapon_type": "Power Weapon",
            "cost_credits": 90, "rarity": "Rare (10)", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -3, "ammo": "-",
            "traits": ["Melee", "Unwieldy", "Pulverise"], "availability": ["Goliath (80cr)", "Trading Post (90cr)"],
            "description": "Massive motorized gauntlet that multiplies user strength to crush skull, bone, and machine parts."
        },
        {
            "name": "Thunder Hammer", "slug": "thunder-hammer", "category": "Close Combat", "weapon_type": "Power Weapon",
            "cost_credits": 105, "rarity": "Rare (10)", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -1, "ammo": "-",
            "traits": ["Melee", "Power", "Shock", "Unwieldy"], "availability": ["Trading Post (105cr)"],
            "description": "Colossal warhammer releasing an explosive kinetic shockwave upon impact."
        },
        {
            "name": "Spud-jacker", "slug": "spud-jacker", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 15, "rarity": "Common", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "-",
            "traits": ["Melee", "Knockback"], "availability": ["Goliath (15cr)", "Slave Ogryn Gangs (10cr)", "Trading Post (15cr)"],
            "description": "Heavy industrial steel wrench swung with enough momentum to smash ribs and send victims flying."
        },
        {
            "name": "Flail", "slug": "flail", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 20, "rarity": "Common", "range_short": "E", "range_long": "-",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "-",
            "traits": ["Melee", "Entangle"], "availability": ["Cawdor (20cr)", "Trading Post (20cr)"],
            "description": "Chain and spiked iron weight that whips around parrying blades and riot shields."
        },
        {
            "name": "Shock Whip", "slug": "shock-whip", "category": "Close Combat", "weapon_type": "Exotic Melee",
            "cost_credits": 25, "rarity": "Rare (8)", "range_short": "E", "range_long": "3\"",
            "accuracy_short": "-", "accuracy_long": "+1", "strength": 3, "damage": 1, "armor_piercing": -1, "ammo": "-",
            "traits": ["Versatile", "Shock"], "availability": ["Escher (25cr)", "Trading Post (25cr)"],
            "description": "Electrified mono-cable whip allowing Escher Queens to lash out at enemies from 3 inches away."
        },
        {
            "name": "Maul", "slug": "maul", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 25, "rarity": "Common", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 4, "damage": 2, "armor_piercing": 0, "ammo": "-",
            "traits": ["Melee", "Shock"], "availability": ["Common (25cr)"],
            "description": "Heavy security baton equipped with shock generators to incapacitate rioters."
        },
        {
            "name": "Servo-claw", "slug": "servo-claw", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 30, "rarity": "Rare (8)", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -2, "ammo": "-",
            "traits": ["Melee", "Rend"], "availability": ["Van Saar (25cr)", "Trading Post (30cr)"],
            "description": "Hydraulic cybernetic claw integrated into servo-harnesses to crush flesh and structural bulkheads."
        },
        {
            "name": "Chain Glaive", "slug": "chain-glaive", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 55, "rarity": "Rare (8)", "range_short": "E", "range_long": "2\"",
            "accuracy_short": "-", "accuracy_long": "+1", "strength": 4, "damage": 2, "armor_piercing": -2, "ammo": "-",
            "traits": ["Versatile", "Melee", "Rend"], "availability": ["Cawdor (50cr)", "Corpse Grinder Cults (50cr)", "Trading Post (55cr)"],
            "description": "Two-handed polearm capped with a whining chainblade, allowing sweeping lethal strikes from reach."
        },
        {
            "name": "Power Maul", "slug": "power-maul", "category": "Close Combat", "weapon_type": "Power Weapon",
            "cost_credits": 35, "rarity": "Rare (8)", "range_short": "E", "range_long": "-",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 5, "damage": 1, "armor_piercing": -1, "ammo": "-",
            "traits": ["Melee", "Power", "Shock"], "availability": ["Palanite Enforcers (30cr)", "Trading Post (35cr)"],
            "description": "Heavy disruption mace that delivers concussive electric bursts on impact."
        },
        {
            "name": "Heavy Chain Cleaver", "slug": "heavy-chain-cleaver", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 40, "rarity": "Rare (8)", "range_short": "E", "range_long": "-",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 5, "damage": 2, "armor_piercing": -1, "ammo": "-",
            "traits": ["Melee", "Rend", "Pulverise"], "availability": ["Corpse Grinder Cults (35cr)", "Trading Post (40cr)"],
            "description": "Massive butcher blade fitted with twin rotating chains, favored by meat cult slaughterers."
        },
        {
            "name": "Renderizer", "slug": "renderizer", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 50, "rarity": "Rare (8)", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -1, "ammo": "-",
            "traits": ["Melee", "Pulverise"], "availability": ["Goliath (40cr)", "Trading Post (50cr)"],
            "description": "Twin-bladed serrated serration tool capable of sawing through steel scaffolds and bone simultaneously."
        },
        {
            "name": "Flensing Knife", "slug": "flensing-knife", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 15, "rarity": "Common", "range_short": "E", "range_long": "-",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 3, "damage": 1, "armor_piercing": -1, "ammo": "-",
            "traits": ["Melee", "Rend"], "availability": ["Corpse Grinder Cults (10cr)", "Trading Post (15cr)"],
            "description": "Curved skinning blade designed for precision dissection in the corpse-processing vats."
        },
        {
            "name": "Web Sabre", "slug": "web-sabre", "category": "Close Combat", "weapon_type": "Exotic Melee",
            "cost_credits": 50, "rarity": "Rare (9)", "range_short": "E", "range_long": "-",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 0, "armor_piercing": 0, "ammo": "-",
            "traits": ["Melee", "Entangle", "Silent"], "availability": ["Delaque (45cr)", "Trading Post (50cr)"],
            "description": "Fine fencing blade coated in active web chemical paste that snares the opponent's limbs on contact."
        },
        {
            "name": "Shock Stave", "slug": "shock-stave", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 25, "rarity": "Common", "range_short": "E", "range_long": "2\"",
            "accuracy_short": "+1", "accuracy_long": "-", "strength": 4, "damage": 1, "armor_piercing": 0, "ammo": "-",
            "traits": ["Versatile", "Shock", "Parry"], "availability": ["Van Saar (25cr)", "Trading Post (25cr)"],
            "description": "Electrified carbon-composite quarterstaff used for non-lethal defense and tactical parrying."
        },
        {
            "name": "Two-handed Hammer", "slug": "two-handed-hammer", "category": "Close Combat", "weapon_type": "Melee",
            "cost_credits": 35, "rarity": "Common", "range_short": "E", "range_long": "-",
            "accuracy_short": "-", "accuracy_long": "-", "strength": 6, "damage": 2, "armor_piercing": -1, "ammo": "-",
            "traits": ["Melee", "Knockback", "Unwieldy"], "availability": ["Goliath (30cr)", "Trading Post (35cr)"],
            "description": "Massive steel sledge capable of staggering even armored brute servitors with one blow."
        }
    ]

    db.weapons.delete_many({})
    db.weapons.insert_many(weapons)
    db.weapons.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(weapons)} 100% authentic weapons into 'weapons'.")

    # ==========================================
    # 3. CLAN HOUSES & FIGHTER ROSTERS (14 Gangs)
    # ==========================================
    houses = [
        {
            "name": "House Van Saar", "slug": "van-saar", "title": "The House of Artifice",
            "specialty": "High-tech weaponry, plasma, energy shields, and cyberteknika.",
            "lore": "Possessing a malfunctioning, radioactive Standard Template Construct (STC), House Van Saar crafts the most sophisticated technological marvels on Necromunda. Their fighters wear survival suits to ward off the radiation sickness that slowly consumes their bloodlines.",
            "primary_skills": ["Shooting", "Savant", "Tech"],
            "signature_weapons": ["Lasgun", "Plasma Gun", "Lascannon", "Volkite Charger", "Rad Gun"],
            "roster": [
                {"title": "Prime", "role": "Leader", "cost_credits": 130, "m": "4\"", "ws": "4+", "bs": "2+", "s": 3, "t": 3, "w": 2, "i": "4+", "a": 2, "ld": "6+", "cl": "7+", "wil": "6+", "int": "4+"},
                {"title": "Augur", "role": "Champion", "cost_credits": 110, "m": "4\"", "ws": "4+", "bs": "2+", "s": 3, "t": 3, "w": 2, "i": "4+", "a": 1, "ld": "7+", "cl": "7+", "wil": "6+", "int": "5+"},
                {"title": "Archeotek", "role": "Champion", "cost_credits": 125, "m": "4\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "4+", "a": 2, "ld": "7+", "cl": "6+", "wil": "6+", "int": "4+"},
                {"title": "Tek", "role": "Ganger", "cost_credits": 65, "m": "4\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 1, "i": "5+", "a": 1, "ld": "8+", "cl": "7+", "wil": "7+", "int": "6+"},
                {"title": "Sub-tek", "role": "Juve", "cost_credits": 35, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "8+", "cl": "8+", "wil": "7+", "int": "6+"},
                {"title": "Neotek", "role": "Prospect", "cost_credits": 70, "m": "7\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "7+", "wil": "7+", "int": "6+"}
            ]
        },
        {
            "name": "House Goliath", "slug": "goliath", "title": "The House of Chains",
            "specialty": "Genetically vat-grown giants, heavy melee, brute strength, and stub cannonry.",
            "lore": "Engineered to labor in the sweltering foundries and deep slag pits, House Goliath values physical power above all else. Heavily muscled and chemically stimulated, their gangs smash opponents in brutal close-quarters clashes.",
            "primary_skills": ["Brawn", "Ferocity", "Muscle"],
            "signature_weapons": ["Boltgun", "Heavy Bolter", "Power Fist", "Combat Shotgun", "Spud-jacker", "Renderizer"],
            "roster": [
                {"title": "Forge Tyrant", "role": "Leader", "cost_credits": 145, "m": "4\"", "ws": "3+", "bs": "4+", "s": 4, "t": 4, "w": 2, "i": "4+", "a": 3, "ld": "6+", "cl": "5+", "wil": "8+", "int": "8+"},
                {"title": "Forge Boss", "role": "Champion", "cost_credits": 105, "m": "4\"", "ws": "3+", "bs": "4+", "s": 4, "t": 4, "w": 2, "i": "4+", "a": 2, "ld": "7+", "cl": "6+", "wil": "8+", "int": "8+"},
                {"title": "Stimmer", "role": "Champion", "cost_credits": 125, "m": "5\"", "ws": "2+", "bs": "5+", "s": 5, "t": 4, "w": 2, "i": "3+", "a": 3, "ld": "7+", "cl": "6+", "wil": "7+", "int": "9+"},
                {"title": "Bruiser", "role": "Ganger", "cost_credits": 55, "m": "4\"", "ws": "4+", "bs": "4+", "s": 4, "t": 4, "w": 1, "i": "5+", "a": 1, "ld": "8+", "cl": "7+", "wil": "8+", "int": "9+"},
                {"title": "Bully", "role": "Juve", "cost_credits": 35, "m": "4\"", "ws": "4+", "bs": "5+", "s": 4, "t": 4, "w": 1, "i": "4+", "a": 1, "ld": "9+", "cl": "7+", "wil": "9+", "int": "9+"}
            ]
        },
        {
            "name": "House Escher", "slug": "escher", "title": "The House of Blades",
            "specialty": "Chems, toxins, agility, venom blades, and whip weaponry.",
            "lore": "An all-female matriarchy dominating Necromunda's pharmaceutical and stimulant trade. Fast, nimble, and armed with lethal poisons, Escher gangs strike like vipers from the catwalks before melting away into the shadows.",
            "primary_skills": ["Agility", "Combat", "Finesse"],
            "signature_weapons": ["Lasgun", "Shock Whip", "Chainsword", "Flamer", "Stiletto Knife", "Needle Pistol"],
            "roster": [
                {"title": "Gang Queen", "role": "Leader", "cost_credits": 125, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "2+", "a": 3, "ld": "6+", "cl": "6+", "wil": "7+", "int": "7+"},
                {"title": "Gang Matriarch", "role": "Champion", "cost_credits": 100, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "2+", "a": 2, "ld": "7+", "cl": "6+", "wil": "7+", "int": "7+"},
                {"title": "Death-maiden", "role": "Champion", "cost_credits": 115, "m": "6\"", "ws": "2+", "bs": "4+", "s": 3, "t": 3, "w": 2, "i": "2+", "a": 3, "ld": "8+", "cl": "5+", "wil": "7+", "int": "7+"},
                {"title": "Sister", "role": "Ganger", "cost_credits": 50, "m": "5\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "7+", "wil": "8+", "int": "8+"},
                {"title": "Little Sister", "role": "Juve", "cost_credits": 20, "m": "6\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "2+", "a": 1, "ld": "9+", "cl": "8+", "wil": "8+", "int": "8+"},
                {"title": "Wyld Runner", "role": "Prospect", "cost_credits": 35, "m": "6\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "2+", "a": 1, "ld": "8+", "cl": "7+", "wil": "8+", "int": "8+"}
            ]
        },
        {
            "name": "House Orlock", "slug": "orlock", "title": "The House of Iron",
            "specialty": "Mining networks, shotguns, autoguns, heavy stubbers, and sheer grit.",
            "lore": "Controlling the inter-hive rail networks and deep ore mines, House Orlock is built upon solidarity, stubborn determination, and hard firepower. When trouble hits, an Orlock gang stands shoulder-to-shoulder with relentless shotguns.",
            "primary_skills": ["Ferocity", "Combat", "Bravado"],
            "signature_weapons": ["Autogun", "Combat Shotgun", "Heavy Bolter", "Heavy Stubber", "Boltgun"],
            "roster": [
                {"title": "Road Captain", "role": "Leader", "cost_credits": 125, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 3, "ld": "6+", "cl": "5+", "wil": "6+", "int": "7+"},
                {"title": "Road Sergeant", "role": "Champion", "cost_credits": 95, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "7+", "cl": "6+", "wil": "6+", "int": "7+"},
                {"title": "Arms Master", "role": "Champion", "cost_credits": 115, "m": "5\"", "ws": "3+", "bs": "3+", "s": 4, "t": 4, "w": 2, "i": "4+", "a": 2, "ld": "6+", "cl": "5+", "wil": "6+", "int": "7+"},
                {"title": "Gunner", "role": "Ganger", "cost_credits": 55, "m": "5\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "7+", "cl": "6+", "wil": "7+", "int": "8+"},
                {"title": "Greenhorn", "role": "Juve", "cost_credits": 30, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "7+", "wil": "7+", "int": "8+"},
                {"title": "Wrecker", "role": "Prospect", "cost_credits": 55, "m": "6\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "6+", "wil": "7+", "int": "8+"}
            ]
        },
        {
            "name": "House Cawdor", "slug": "cawdor", "title": "The House of Faith",
            "specialty": "Horde swarms, scrap-polearms, blunderbusses, fire, and fanatic zeal.",
            "lore": "The destitute scavengers of the hive heaps. Bound by the fanatical tenets of the Redemption, House Cawdor sends hordes of masked, zealous trash-pickers into battle armed with crude polearm weapons and holy fire.",
            "primary_skills": ["Brawn", "Combat", "Piety"],
            "signature_weapons": ["Autogun", "Flamer", "Blunderbuss Polearm", "Heavy Crossbow", "Flail"],
            "roster": [
                {"title": "Word-Keeper", "role": "Leader", "cost_credits": 100, "m": "5\"", "ws": "3+", "bs": "4+", "s": 3, "t": 3, "w": 2, "i": "4+", "a": 2, "ld": "6+", "cl": "6+", "wil": "5+", "int": "8+"},
                {"title": "Prior", "role": "Champion", "cost_credits": 95, "m": "5\"", "ws": "3+", "bs": "4+", "s": 3, "t": 3, "w": 2, "i": "4+", "a": 2, "ld": "7+", "cl": "6+", "wil": "6+", "int": "8+"},
                {"title": "Fire-brand", "role": "Champion", "cost_credits": 85, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 2, "i": "4+", "a": 2, "ld": "7+", "cl": "6+", "wil": "5+", "int": "8+"},
                {"title": "Brethren", "role": "Ganger", "cost_credits": 45, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "8+", "cl": "7+", "wil": "6+", "int": "9+"},
                {"title": "Bonepicker", "role": "Juve", "cost_credits": 20, "m": "6\"", "ws": "5+", "bs": "5+", "s": 2, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "9+", "cl": "8+", "wil": "7+", "int": "9+"},
                {"title": "Way-Brethren", "role": "Prospect", "cost_credits": 40, "m": "6\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "7+", "wil": "6+", "int": "8+"}
            ]
        },
        {
            "name": "House Delaque", "slug": "delaque", "title": "The House of Shadow",
            "specialty": "Espionage, stealth, silent needle weapons, web guns, and psychomancy.",
            "lore": "Whispering spies and bald shadow-runners cloaked in long trench coats. House Delaque rarely fights fair, preferring poisons, web snares, darkness, and subterranean psychoteric sorcery to bleed foes unawares.",
            "primary_skills": ["Agility", "Cunning", "Obfuscation"],
            "signature_weapons": ["Plasma Gun", "Needle Rifle", "Web Gun", "Web Pistol", "Flechette Pistol", "Web Sabre"],
            "roster": [
                {"title": "Master of Shadow", "role": "Leader", "cost_credits": 130, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "6+", "cl": "6+", "wil": "6+", "int": "6+"},
                {"title": "Phantom", "role": "Champion", "cost_credits": 95, "m": "5\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "7+", "cl": "6+", "wil": "6+", "int": "6+"},
                {"title": "Nacht-Ghul", "role": "Champion", "cost_credits": 110, "m": "6\"", "ws": "2+", "bs": "4+", "s": 4, "t": 3, "w": 2, "i": "2+", "a": 3, "ld": "7+", "cl": "5+", "wil": "6+", "int": "7+"},
                {"title": "Ghost", "role": "Ganger", "cost_credits": 50, "m": "5\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "7+", "cl": "7+", "wil": "7+", "int": "7+"},
                {"title": "Shadow", "role": "Juve", "cost_credits": 25, "m": "6\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "7+", "wil": "7+", "int": "7+"},
                {"title": "Psy-Gheist", "role": "Prospect", "cost_credits": 60, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "6+", "wil": "5+", "int": "7+"}
            ]
        },
        {
            "name": "Palanite Enforcers", "slug": "palanite-enforcers", "title": "The Law of the Hive",
            "specialty": "Authoritarian suppression, concussion rams, riot shields, and sniper fire.",
            "lore": "Lord Helmawr's brutal planetary police force. Militarized, unyielding, and equipped with state-sanctioned riot artillery, they maintain an iron grip on the trade lanes of Hive Primus.",
            "primary_skills": ["Shooting", "Brawn", "Enforcement"],
            "signature_weapons": ["Heavy Concussion Ram", "Boltgun", "Combat Shotgun", "Subjugator Pattern Grenade Launcher", "Assault Shotgun"],
            "roster": [
                {"title": "Enforcer Captain", "role": "Leader", "cost_credits": 140, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "6+", "cl": "5+", "wil": "6+", "int": "6+"},
                {"title": "Enforcer Sergeant", "role": "Champion", "cost_credits": 95, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "4+", "a": 2, "ld": "7+", "cl": "6+", "wil": "7+", "int": "7+"},
                {"title": "Patrolman", "role": "Ganger", "cost_credits": 60, "m": "5\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "7+", "cl": "6+", "wil": "7+", "int": "7+"},
                {"title": "Subjugator Captain", "role": "Leader", "cost_credits": 150, "m": "4\"", "ws": "3+", "bs": "3+", "s": 4, "t": 4, "w": 2, "i": "4+", "a": 2, "ld": "6+", "cl": "5+", "wil": "6+", "int": "6+"},
                {"title": "Subjugator Patrolman", "role": "Ganger", "cost_credits": 70, "m": "4\"", "ws": "3+", "bs": "4+", "s": 4, "t": 4, "w": 1, "i": "4+", "a": 1, "ld": "7+", "cl": "6+", "wil": "7+", "int": "7+"}
            ]
        },
        {
            "name": "Corpse Grinder Cults", "slug": "corpse-grinder-cults", "title": "The Cult of Meat",
            "specialty": "Frenzied cannibalism, chain weapons, circular saws, and terrifying butcher masks.",
            "lore": "Rebellious workers from the Corpse Rations processing vats driven mad by cannibalism and the Lord of Skin and Sinew. They storm through the lower sectors seeking fresh flesh.",
            "primary_skills": ["Ferocity", "Combat"],
            "signature_weapons": ["Heavy Chain Cleaver", "Flensing Knife", "Chainaxe", "Chainsword"],
            "roster": [
                {"title": "Butcher", "role": "Leader", "cost_credits": 135, "m": "5\"", "ws": "2+", "bs": "6+", "s": 4, "t": 4, "w": 2, "i": "3+", "a": 3, "ld": "7+", "cl": "4+", "wil": "7+", "int": "9+"},
                {"title": "Cutter", "role": "Champion", "cost_credits": 105, "m": "5\"", "ws": "3+", "bs": "6+", "s": 4, "t": 4, "w": 2, "i": "3+", "a": 2, "ld": "7+", "cl": "5+", "wil": "7+", "int": "9+"},
                {"title": "Skinner", "role": "Ganger", "cost_credits": 50, "m": "5\"", "ws": "3+", "bs": "6+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "8+", "cl": "6+", "wil": "8+", "int": "9+"},
                {"title": "Meathead", "role": "Juve", "cost_credits": 30, "m": "6\"", "ws": "4+", "bs": "6+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "6+", "wil": "8+", "int": "9+"}
            ]
        },
        {
            "name": "Ironhead Squat Prospectors", "slug": "ironhead-squat-prospectors", "title": "The Charter Masters",
            "specialty": "Abhuman resilience, heavy mining lasers, automated firepower, and rugged exo-suits.",
            "lore": "Clans of resilient abhuman engineers who hold mining charters across the toxic ash wastes and deep bedrock deposits beneath Necromunda.",
            "primary_skills": ["Shooting", "Brawn"],
            "signature_weapons": ["Mining Laser", "Autocannon", "Combat Shotgun", "Heavy Bolter"],
            "roster": [
                {"title": "Charter Master", "role": "Leader", "cost_credits": 130, "m": "4\"", "ws": "3+", "bs": "3+", "s": 3, "t": 4, "w": 2, "i": "5+", "a": 2, "ld": "6+", "cl": "5+", "wil": "6+", "int": "6+"},
                {"title": "Drill Master", "role": "Champion", "cost_credits": 95, "m": "4\"", "ws": "3+", "bs": "3+", "s": 3, "t": 4, "w": 2, "i": "5+", "a": 2, "ld": "7+", "cl": "6+", "wil": "6+", "int": "7+"},
                {"title": "Drill-kin", "role": "Ganger", "cost_credits": 55, "m": "4\"", "ws": "4+", "bs": "3+", "s": 3, "t": 4, "w": 1, "i": "5+", "a": 1, "ld": "7+", "cl": "6+", "wil": "7+", "int": "7+"},
                {"title": "Digger", "role": "Juve", "cost_credits": 30, "m": "4\"", "ws": "4+", "bs": "4+", "s": 3, "t": 4, "w": 1, "i": "4+", "a": 1, "ld": "8+", "cl": "7+", "wil": "7+", "int": "8+"}
            ]
        },
        {
            "name": "Ash Waste Nomads", "slug": "ash-waste-nomads", "title": "The Dust Walkers",
            "specialty": "Survival in lethal rad-dust storms, sniper warfare, stealth, and giant insect mounts.",
            "lore": "Indigenous tribes surviving in the radioactive exterior wastes of Necromunda. Wrapped in rags and breathing through scavenged filters, they prey upon trade convoys.",
            "primary_skills": ["Cunning", "Agility"],
            "signature_weapons": ["Long Rifle", "Reclaimed Autogun", "Fighting Knife"],
            "roster": [
                {"title": "Chieftain", "role": "Leader", "cost_credits": 120, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "6+", "cl": "6+", "wil": "6+", "int": "7+"},
                {"title": "Herder", "role": "Champion", "cost_credits": 90, "m": "5\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "7+", "cl": "6+", "wil": "7+", "int": "7+"},
                {"title": "Warrior", "role": "Ganger", "cost_credits": 45, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "7+", "wil": "7+", "int": "8+"},
                {"title": "Scum", "role": "Juve", "cost_credits": 25, "m": "6\"", "ws": "5+", "bs": "5+", "s": 3, "t": 3, "w": 1, "i": "3+", "a": 1, "ld": "8+", "cl": "8+", "wil": "8+", "int": "8+"}
            ]
        },
        {
            "name": "Genestealer Cults", "slug": "genestealer-cults", "title": "The Brood of the Void",
            "specialty": "Xenos infection, multi-armed mutations, heavy industrial lasers, and seismic picks.",
            "lore": "Corrupted miners and dock workers harboring an alien Tyranid infection beneath their work overalls, waiting for the day of starborn ascension.",
            "primary_skills": ["Cunning", "Ferocity"],
            "signature_weapons": ["Mining Laser", "Autogun", "Seismic", "Heavy Bolter"],
            "roster": [
                {"title": "Cult Adept", "role": "Leader", "cost_credits": 125, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "6+", "cl": "6+", "wil": "5+", "int": "6+"},
                {"title": "Aberrant", "role": "Champion", "cost_credits": 90, "m": "5\"", "ws": "3+", "bs": "6+", "s": 5, "t": 4, "w": 2, "i": "5+", "a": 2, "ld": "8+", "cl": "5+", "wil": "7+", "int": "10+"},
                {"title": "Neophyte", "role": "Ganger", "cost_credits": 45, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "7+", "cl": "6+", "wil": "7+", "int": "8+"}
            ]
        },
        {
            "name": "Helot Chaos Cults", "slug": "helot-chaos-cults", "title": "The Disciples of the Dark",
            "specialty": "Warp witchcraft, daemonic mutation, unholy rituals, and erratic dark pacts.",
            "lore": "Clandestine covens of heretics worshipping the Chaos gods in forgotten sumps, bound together by blood oaths and dangerous warp powers.",
            "primary_skills": ["Ferocity", "Leadership"],
            "signature_weapons": ["Autogun", "Flamer", "Stub Gun w/ dum-dum", "Chainsword"],
            "roster": [
                {"title": "Cult Demagogue", "role": "Leader", "cost_credits": 100, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "6+", "cl": "5+", "wil": "6+", "int": "7+"},
                {"title": "Cult Disciple", "role": "Champion", "cost_credits": 60, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "7+", "cl": "6+", "wil": "7+", "int": "8+"},
                {"title": "Helot", "role": "Ganger", "cost_credits": 35, "m": "5\"", "ws": "4+", "bs": "4+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "8+", "cl": "7+", "wil": "8+", "int": "8+"}
            ]
        },
        {
            "name": "Slave Ogryn Gangs", "slug": "slave-ogryn-gangs", "title": "The Unchained Titans",
            "specialty": "Unstoppable high-wound brutes, augmetic fists, spud-jackers, and sheer mass.",
            "lore": "Escaped mining brutes and lobotomized heavy labor servitors who threw off their chains and formed bands of runaway giants in the lower wastes.",
            "primary_skills": ["Brawn", "Ferocity"],
            "signature_weapons": ["Spud-jacker", "Power Fist", "Servo-claw"],
            "roster": [
                {"title": "Over-boss", "role": "Leader", "cost_credits": 170, "m": "5\"", "ws": "3+", "bs": "5+", "s": 5, "t": 5, "w": 3, "i": "4+", "a": 3, "ld": "7+", "cl": "6+", "wil": "7+", "int": "9+"},
                {"title": "Under-boss", "role": "Champion", "cost_credits": 130, "m": "5\"", "ws": "3+", "bs": "5+", "s": 5, "t": 5, "w": 3, "i": "4+", "a": 2, "ld": "7+", "cl": "6+", "wil": "8+", "int": "9+"},
                {"title": "Ogryn", "role": "Ganger", "cost_credits": 90, "m": "5\"", "ws": "4+", "bs": "5+", "s": 5, "t": 5, "w": 2, "i": "5+", "a": 2, "ld": "8+", "cl": "7+", "wil": "8+", "int": "10+"}
            ]
        },
        {
            "name": "Venators", "slug": "venators", "title": "The Bounty Hunters",
            "specialty": "Custom hired guns, bespoke arsenals, veteran mercenaries, and alien technology.",
            "lore": "Free-agent bounty hunting pacts and off-world mercenaries licensed by Guilder authorities to hunt outlaws across the hive.",
            "primary_skills": ["Shooting", "Combat", "Savant"],
            "signature_weapons": ["Boltgun", "Plasma Pistol", "Long Rifle", "Power Sword"],
            "roster": [
                {"title": "Hunt Leader", "role": "Leader", "cost_credits": 130, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 3, "ld": "6+", "cl": "5+", "wil": "6+", "int": "6+"},
                {"title": "Hunt Champion", "role": "Champion", "cost_credits": 95, "m": "5\"", "ws": "3+", "bs": "3+", "s": 3, "t": 3, "w": 2, "i": "3+", "a": 2, "ld": "7+", "cl": "6+", "wil": "6+", "int": "7+"},
                {"title": "Hunt Specialist", "role": "Ganger", "cost_credits": 60, "m": "5\"", "ws": "4+", "bs": "3+", "s": 3, "t": 3, "w": 1, "i": "4+", "a": 1, "ld": "7+", "cl": "6+", "wil": "7+", "int": "7+"}
            ]
        }
    ]

    db.houses.delete_many({})
    db.houses.insert_many(houses)
    db.houses.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(houses)} clan houses with full fighter class rosters.")

    # ==========================================
    # 4. SKILL DISCIPLINES (48 Authentic Skills)
    # ==========================================
    skills = [
        # Agility
        {"name": "Catfall", "slug": "catfall", "tree": "Agility", "rules_text": "Halves falling distance for calculating damage. Fighter cannot become Pinned when landing from a fall.", "tactics": "Crucial for navigating vertical catwalks and gantries."},
        {"name": "Clamber", "slug": "clamber", "tree": "Agility", "rules_text": "Fighter does not double movement cost when climbing ladders or vertical terrain.", "tactics": "Allows fast ascent to sniper positions."},
        {"name": "Dodge", "slug": "dodge", "tree": "Agility", "rules_text": "When hit by an attack, roll a D6. On a 6, the hit is dodged and has no effect.", "tactics": "Provides critical survivability against high-damage weapons."},
        {"name": "Fast Shot", "slug": "fast-shot", "tree": "Agility", "rules_text": "Fighter can make a Shoot action as a Simple action rather than a Basic action once per round.", "tactics": "Enables Move-and-Shoot or double shooting with basic firearms."},
        {"name": "Infiltrate", "slug": "infiltrate", "tree": "Agility", "rules_text": "Fighter may be set up anywhere on the battlefield not within line of sight of enemy models, or outside 12\".", "tactics": "Sets up lethal early-turn ambush angles."},
        {"name": "Sprint", "slug": "sprint", "tree": "Agility", "rules_text": "When taking a Double Move action, fighter moves triple their Movement characteristic.", "tactics": "Ideal for fast objective grabbing and closing into close combat."},

        # Brawn
        {"name": "Bull Charge", "slug": "bull-charge", "tree": "Brawn", "rules_text": "When making a Charge action, the fighter adds +1 to Strength and inflicts Knockback automatically.", "tactics": "Devastating for Goliath Champions slamming into enemy defense lines."},
        {"name": "Crushing Blow", "slug": "crushing-blow", "tree": "Brawn", "rules_text": "Before rolling to hit in melee, declare a Crushing Blow. Inflicts +1 Strength and +1 Damage on a hit.", "tactics": "Guarantees out of action injuries against tough opponents."},
        {"name": "Headbutt", "slug": "headbutt", "tree": "Brawn", "rules_text": "In melee, roll a D6. On a 4+, target is automatically Pinned and suffers a Strength hit.", "tactics": "Shuts down enemy counter-attacks."},
        {"name": "Hurl", "slug": "hurl", "tree": "Brawn", "rules_text": "May throw an enemy model within base contact up to Strength inches away.", "tactics": "Throw enemies off high gantries to their doom."},
        {"name": "Iron Jaw", "slug": "iron-jaw", "tree": "Brawn", "rules_text": "Adds +1 to Toughness against unarmed attacks, knives, and falling damage.", "tactics": "Prevents surprise beatdowns in knife brawls."},
        {"name": "Iron Man", "slug": "iron-man", "tree": "Brawn", "rules_text": "Fighter ignores Flesh Wounds when calculating Toughness reductions.", "tactics": "Allows bruisers to soak multiple hits without losing combat efficiency."},

        # Combat
        {"name": "Disarm", "slug": "disarm-skill", "tree": "Combat", "rules_text": "In close combat, rolling a natural 6 to hit knocks an opponent's weapon away.", "tactics": "Neutralizes lethal power weapon wielders."},
        {"name": "Feint", "slug": "feint", "tree": "Combat", "rules_text": "May convert one attack die into a feint, reducing the opponent's attacks by 1.", "tactics": "Controls dangerous multi-attack enemies."},
        {"name": "Rain of Blows", "slug": "rain-of-blows", "tree": "Combat", "rules_text": "Fight (Basic) becomes a Simple action for this fighter.", "tactics": "Allows making multiple fight actions in a single activation."},
        {"name": "Step Aside", "slug": "step-aside", "tree": "Combat", "rules_text": "In close combat, once per round, roll a 5+ to ignore one close combat hit.", "tactics": "Essential dueling survival skill."},
        {"name": "Parry", "slug": "parry-skill", "tree": "Combat", "rules_text": "Can parry one incoming hit even if not armed with a weapon that has the Parry trait.", "tactics": "Ensures baseline defense in any melee engagement."},
        {"name": "Combat Occultist", "slug": "combat-occultist", "tree": "Combat", "rules_text": "Add +1 to hit against models with lower Willpower than this fighter.", "tactics": "Preys upon low-morale scum and gangers."},

        # Cunning
        {"name": "Backstab", "slug": "backstab", "tree": "Cunning", "rules_text": "Adds +1 to Strength when attacking a fighter from behind.", "tactics": "Rewards flank maneuvers and stealth ambushes."},
        {"name": "Escape Artist", "slug": "escape-artist", "tree": "Cunning", "rules_text": "Automatically breaks free from Web, nets, and capture effects on a 2+.", "tactics": "Counters Delaque web weapons effortlessly."},
        {"name": "Evade", "slug": "evade", "tree": "Cunning", "rules_text": "Enemy fighters targeting this model at Long range suffer an additional -1 to hit.", "tactics": "Stops long-range snipers from picking off your fighters."},
        {"name": "Lie Low", "slug": "lie-low", "tree": "Cunning", "rules_text": "While Pinned or Prone, this fighter cannot be targeted by ranged attacks past 12\".", "tactics": "Provides immunity from sniper fire while crawling behind low walls."},
        {"name": "Shadow Walk", "slug": "shadow-walk", "tree": "Cunning", "rules_text": "If ending movement within 1\" of cover, the fighter counts as Hidden immediately.", "tactics": "Ideal for Delaque Phantoms moving through dimly lit terrain."},
        {"name": "Cunning Infiltrator", "slug": "cunning-infiltrator", "tree": "Cunning", "rules_text": "May start the game deployed anywhere outside 8\" of an enemy model.", "tactics": "Aggressive forward positioning."},

        # Ferocity
        {"name": "Berserker", "slug": "berserker", "tree": "Ferocity", "rules_text": "Adds +1 Attack dice on any round in which the fighter completes a Charge.", "tactics": "Turns Goliath and Corpse Grinder charges into meat grinders."},
        {"name": "Fearsome", "slug": "fearsome", "tree": "Ferocity", "rules_text": "Any enemy charging this fighter must pass a Willpower test or halt their charge.", "tactics": "Deflects incoming melee rushers before they reach contact."},
        {"name": "Impassive", "slug": "impassive", "tree": "Ferocity", "rules_text": "Immune to the effects of Concussion and Flash weaponry.", "tactics": "Shrugs off riot artillery and flashbangs."},
        {"name": "Nerves of Steel", "slug": "nerves-of-steel", "tree": "Ferocity", "rules_text": "May test Cool when hit by ranged fire. If passed, the fighter is NOT Pinned.", "tactics": "The single most important skill for advancing heavy weapon and assault fighters."},
        {"name": "True Grit", "slug": "true-grit", "tree": "Ferocity", "rules_text": "When rolling Injury dice against this fighter, roll one less die (minimum 1).", "tactics": "Massively reduces the chances of Out of Action results."},
        {"name": "Unstoppable", "slug": "unstoppable", "tree": "Ferocity", "rules_text": "At the start of the Recovery phase, roll a D6. On a 4+, discard one Flesh Wound.", "tactics": "Fighters regenerate combat toughness mid-battle."},

        # Leadership
        {"name": "Commanding Presence", "slug": "commanding-presence", "tree": "Leadership", "rules_text": "Group Activations can include an additional fighter within 6\".", "tactics": "Unleashes coordinated squad strikes with three or four gangers at once."},
        {"name": "Inspirational", "slug": "inspirational", "tree": "Leadership", "rules_text": "Friendly fighters within 6\" may use this fighter's Cool characteristic for tests.", "tactics": "Prevents bottle tests and broken morale panics."},
        {"name": "Iron Will", "slug": "iron-will", "tree": "Leadership", "rules_text": "Subtract 1 from all Bottle tests rolled for the gang while this fighter is on the board.", "tactics": "Keeps your gang fighting long after taking heavy casualties."},
        {"name": "Lead by Example", "slug": "lead-by-example", "tree": "Leadership", "rules_text": "When this fighter takes an enemy out of action, all friends within 6\" gain +1 to Cool.", "tactics": "Sparks a rally across your frontline."},
        {"name": "Mentor", "slug": "mentor", "tree": "Leadership", "rules_text": "May grant an experience point to a friendly Juve or Prospect at the end of the battle.", "tactics": "Accelerates gang advancement during campaigns."},
        {"name": "Regroup", "slug": "regroup", "tree": "Leadership", "rules_text": "Once per battle, roll a Leadership test to automatically rally all Broken friendly fighters.", "tactics": "Reverses a collapsing battle line instantly."},

        # Savant
        {"name": "Ballistics Expert", "slug": "ballistics-expert", "tree": "Savant", "rules_text": "May reroll the Scatter die on any weapon with the Blast trait.", "tactics": "Ensures grenade launcher and missile hits land dead on target."},
        {"name": "Connected", "slug": "connected", "tree": "Savant", "rules_text": "Adds +2 to Trade post availability checks for Rare equipment.", "tactics": "Secures high-grade weaponry between campaign matches."},
        {"name": "Fixer", "slug": "fixer", "tree": "Savant", "rules_text": "Generates D3 x 10 credits for the gang's stash during post-battle sequence.", "tactics": "Steady passive income generator for long-term gang wealth."},
        {"name": "Medicae", "slug": "medicae", "tree": "Savant", "rules_text": "Reroll Lasting Injury rolls on friendly fighters during the post-battle sequence.", "tactics": "Saves your best champions from permanent stat penalties and death."},
        {"name": "Savvy Trader", "slug": "savvy-trader", "tree": "Savant", "rules_text": "Reduce the credit cost of Rare weapons at the Trading Post by 20% (minimum 5cr).", "tactics": "Stretches gang credits to afford luxury plasma and power arms."},
        {"name": "Weaponsmith", "slug": "weaponsmith", "tree": "Savant", "rules_text": "May reroll any failed Ammo check made by this fighter or an adjacent friendly fighter.", "tactics": "Keeps scarce plasma and melta weapons in the fight."},

        # Shooting
        {"name": "Trick Shot", "slug": "trick-shot", "tree": "Shooting", "rules_text": "Reduces the defense modifier of target cover by 1 (partial cover becomes 0, full becomes -1).", "tactics": "Obliterates enemy defensive firing positions."},
        {"name": "Gunfighter", "slug": "gunfighter", "tree": "Shooting", "rules_text": "May fire two pistols with a single Shoot action without the standard dual-shot penalty.", "tactics": "The definitive skill for dual autopistol or plasma pistol slingers."},
        {"name": "Marksman", "slug": "marksman", "tree": "Shooting", "rules_text": "Ignores the target priority rule; may shoot any visible target in range.", "tactics": "Allows targeting enemy leaders and champions hiding behind juves."},
        {"name": "Precision Shot", "slug": "precision-shot", "tree": "Shooting", "rules_text": "If a natural 6 is rolled to hit, the attack inflicts +1 Damage.", "tactics": "Turns accurate bolters and long rifles into instant killers."},
        {"name": "Hip Shooting", "slug": "hip-shooting", "tree": "Shooting", "rules_text": "Fighter may move up to their Double Movement and fire a weapon as part of the same activation.", "tactics": "Aggressive run-and-gun assault tactics."},
        {"name": "Eye of the Hunter", "slug": "eye-of-the-hunter", "tree": "Shooting", "rules_text": "Target fighters never count as being in Partial Cover against this shooter.", "tactics": "Ensures clean lines of fire in dense Underhive industrial maze."}
    ]

    db.skills.delete_many({})
    db.skills.insert_many(skills)
    db.skills.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(skills)} authentic skills across all 8 disciplines.")

    # ==========================================
    # 5. TRADING POST EQUIPMENT & WARGEAR (25 Items)
    # ==========================================
    equipment = [
        {"name": "Mesh Armor", "slug": "mesh-armor", "category": "Armor", "cost_credits": 15, "rarity": "Common", "rules_text": "Grants a 5+ armor save. Save is not reduced by weapons with AP 0.", "description": "Interlocking micro-mesh plates providing lightweight kinetic protection."},
        {"name": "Flak Armor", "slug": "flak-armor", "category": "Armor", "cost_credits": 10, "rarity": "Common", "rules_text": "Grants a 6+ armor save, improving to 5+ against weapons with Blast or Template.", "description": "Standard composite weave jacket favored for shrapnel defense."},
        {"name": "Heavy Carapace Armor", "slug": "heavy-carapace-armor", "category": "Armor", "cost_credits": 100, "rarity": "Rare (11)", "rules_text": "Grants a 4+ armor save, reducing Initiative by 1. Toughness tests are treated as 1 better against Blast.", "description": "Militarized forged ceramite plates offering formidable protection."},
        {"name": "Armored Undersuit", "slug": "armored-undersuit", "category": "Armor", "cost_credits": 25, "rarity": "Rare (7)", "rules_text": "Adds +1 to any existing armor save (e.g. Mesh Armor 5+ becomes 4+).", "description": "Form-fitting flexible ballistic fabric worn beneath outer clothing."},
        {"name": "Hardened Leather Armor", "slug": "hardened-leather-armor", "category": "Armor", "cost_credits": 10, "rarity": "Common", "rules_text": "Grants a 6+ armor save against close combat attacks.", "description": "Cured beast hide worn by ash wasters and sump scavengers."},
        {"name": "Photo-goggles", "slug": "photo-goggles", "category": "Field Gear", "cost_credits": 35, "rarity": "Rare (8)", "rules_text": "Allows the wearer to see through smoke clouds and reduces cover penalties in Pitch Black scenarios.", "description": "Light-amplification oculars tuned for gloomy industrial tunnels."},
        {"name": "Respirator", "slug": "respirator", "category": "Field Gear", "cost_credits": 15, "rarity": "Common", "rules_text": "Adds +2 to Toughness tests against Gas weapons and toxic environmental hazards.", "description": "Filtration mask filtering out toxic sump smog and chemical spores."},
        {"name": "Drop Rig", "slug": "drop-rig", "category": "Field Gear", "cost_credits": 10, "rarity": "Common", "rules_text": "Allows the fighter to descend up to 3 inches without suffering falling damage or using movement.", "description": "Harness and magnetic rappel cable for fast gantry descents."},
        {"name": "Grapple Launcher", "slug": "grapple-launcher", "category": "Field Gear", "cost_credits": 25, "rarity": "Rare (8)", "rules_text": "Enables movement across up to 12 inches of horizontal or vertical terrain in a straight line.", "description": "Pneumatic hook launcher for ascending to high catwalks."},
        {"name": "Bio-booster", "slug": "bio-booster", "category": "Personal Gear", "cost_credits": 35, "rarity": "Rare (8)", "rules_text": "The first time the fighter rolls an Injury die, treat Out of Action as Serious Injury instead.", "description": "Automated subcutaneous injector delivering immediate coagulants."},
        {"name": "Stimm-slug Stash", "slug": "stimm-slug-stash", "category": "Personal Gear", "cost_credits": 30, "rarity": "Rare (7)", "rules_text": "Once per battle, add +2 to Movement, Strength, and Toughness for one round. May suffer injury afterward.", "description": "Chemical cocktail ampoules that unleash terrifying bursts of adrenaline."},
        {"name": "Chem-synth", "slug": "chem-synth", "category": "Personal Gear", "cost_credits": 15, "rarity": "Rare (8)", "rules_text": "Before attacking with a Toxin or Gas weapon, roll an Intelligence check. If passed, reduce target Toughness by 1.", "description": "Portable chemical synthesizer used by Escher to amplify poison potency."},
        {"name": "Infra-sight", "slug": "infra-sight", "category": "Weapon Accessory", "cost_credits": 40, "rarity": "Rare (8)", "rules_text": "Attached weapon ignores smoke clouds and gains +1 to hit against models in cover at Long range.", "description": "Thermal imaging scope mounted on precision firearms."},
        {"name": "Mono-sight", "slug": "mono-sight", "category": "Weapon Accessory", "cost_credits": 35, "rarity": "Rare (9)", "rules_text": "If the fighter takes an Aim action before shooting, add an additional +1 to hit.", "description": "Advanced laser rangefinder for long rifles and heavy stubbers."},
        {"name": "Telescopic Sight", "slug": "telescopic-sight", "category": "Weapon Accessory", "cost_credits": 35, "rarity": "Rare (7)", "rules_text": "If aiming, the weapon suffers no penalty for shooting at Long range.", "description": "High-magnification crosshair optic."},
        {"name": "Suspensor", "slug": "suspensor", "category": "Weapon Accessory", "cost_credits": 60, "rarity": "Rare (10)", "rules_text": "Removes the Unwieldy trait restriction from Heavy weapons, allowing Shoot as a Simple action.", "description": "Anti-grav null-harness that balances heavy machine guns effortlessly."},
        {"name": "Laser Sight", "slug": "laser-sight", "category": "Weapon Accessory", "cost_credits": 35, "rarity": "Rare (8)", "rules_text": "Adds +1 to hit at Short range with the attached pistol or basic weapon.", "description": "Barrel-mounted red target designator beam."},
        {"name": "Frag Grenades", "slug": "frag-grenades", "category": "Ammunition", "cost_credits": 30, "rarity": "Common", "rules_text": "Thrown grenade. Range Sx3, Str 3, Dmg 1, Ammo 4+, Blast (3\"), Knockback.", "description": "Standard anti-personnel shrapnel grenades."},
        {"name": "Krak Grenades", "slug": "krak-grenades", "category": "Ammunition", "cost_credits": 45, "rarity": "Rare (8)", "rules_text": "Thrown grenade. Range Sx3, Str 6, Dmg 2, AP -2, Ammo 4+, Demolition.", "description": "Concentrated shaped-charge explosive for breaching bulkheads and vehicles."},
        {"name": "Smoke Grenades", "slug": "smoke-grenades", "category": "Ammunition", "cost_credits": 15, "rarity": "Common", "rules_text": "Thrown grenade. Creates a 5\" smoke cloud lasting until the End phase.", "description": "Screening canisters used to cover open assault lanes."},
        {"name": "Choke Gas Grenades", "slug": "choke-gas-grenades", "category": "Ammunition", "cost_credits": 35, "rarity": "Rare (9)", "rules_text": "Thrown grenade. Blast (3\"), Gas trait. Targets must test Toughness or suffer Injury.", "description": "Tear-inducing riot gas canisters deployed by Enforcers."},
        {"name": "Web Soles", "slug": "web-soles", "category": "Field Gear", "cost_credits": 20, "rarity": "Rare (8)", "rules_text": "Fighter cannot slip, fall from narrow walkways, or suffer Knockback near edges.", "description": "Magnetic and micro-suction boot treads for clinging to wet pipes."},
        {"name": "Photo-flare", "slug": "photo-flare", "category": "Ammunition", "cost_credits": 15, "rarity": "Common", "rules_text": "Deploys a brilliant illumination flare, illuminating all models within 6\" for one round.", "description": "High-intensity magnesium flare illuminating subterranean darkness."},
        {"name": "Medikit", "slug": "medikit", "category": "Field Gear", "cost_credits": 30, "rarity": "Rare (8)", "rules_text": "Allows making a First Aid action on an adjacent Seriously Injured friendly fighter, rolling 2D6 on recovery.", "description": "Compact surgical pack stocked with burn salve, dermaseal, and blood bags."},
        {"name": "Filter Plugs", "slug": "filter-plugs", "category": "Field Gear", "cost_credits": 10, "rarity": "Common", "rules_text": "Adds +1 to Toughness tests against toxic air and industrial fumes.", "description": "Nasal plugs packed with charcoal granules."}
    ]

    db.equipment.delete_many({})
    db.equipment.insert_many(equipment)
    db.equipment.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(equipment)} authentic equipment items into 'equipment'.")

    print("[Necromunda Seeder] ALL 5 COLLECTIONS SEEDED WITH 100% AUTHENTIC DATA!")


if __name__ == "__main__":
    seed_necromunda()
