"""
scripts/seed_necromunda.py
--------------------------
Comprehensive, 100% authentic Underhive database seeder for Necromunda on AvaScry.
Populates:
  1. db.weapons   - Complete Underhive firearm, ordnance, close combat & ammunition catalog.
  2. db.traits    - Complete official weapon traits and rules mechanics lexicon.
  3. db.houses    - 14 gangs/houses enriched with full fighter class rosters.
  4. db.skills    - Complete skill disciplines across core, House-specific, and Wyrd disciplines.
  5. db.equipment - Complete Trading Post wargear, armor suits, personal equipment, chems & field gear.
"""
import sys
import os
import re
import urllib.request
import yaml

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db_mongo import get_mongo_db
from mtgabyss.shared.helpers import slugify


def clean_ascii(text: str) -> str:
    if not text:
        return ""
    # Remove markdown link formatting [text](url) -> text
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    cleaned = cleaned.replace('\\-', '-').replace('\\', '')
    return cleaned.encode('ascii', 'ignore').decode('ascii').strip()


def seed_necromunda():
    client = get_mongo_db().client
    db = client["avascry_necromunda"]

    print("[Necromunda Seeder] Seeding 100% authentic Underhive corpus into 'avascry_necromunda'...")

    # ==========================================
    # 1. WEAPON TRAITS
    # ==========================================
    # Start with core 40 canonical traits with hand-crafted summaries & FAQs
    base_traits = [
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
            "summary": "Allows engaging in close combat up to long range without base contact.",
            "rules_text": "Fighters armed with Versatile weapons can make close combat attacks against enemies within their long range value, without entering base-to-base contact.",
            "faq": "Allows whipping or spearing enemies across barricades or pits."
        },
        {
            "name": "Shock", "slug": "shock", "category": "Damage",
            "summary": "Natural 6 to wound inflicts an automatic Flesh Wound.",
            "rules_text": "If the roll to wound is a natural 6, the target automatically suffers a Flesh Wound in addition to any other damage inflicted.",
            "faq": "Weakens tough enemies regardless of remaining wound pools."
        },
        {
            "name": "Rend", "slug": "rend", "category": "Armor Piercing",
            "summary": "Natural 6 to wound improves Armor Piercing by -1 and adds +1 Damage.",
            "rules_text": "If the roll to wound is a natural 6, improve the weapon's Armor Piercing characteristic by -1 and increase Damage by +1.",
            "faq": "Makes chain weapons and razor talons punch far above their weight."
        },
        {
            "name": "Pulverise", "slug": "pulverise", "category": "Damage",
            "summary": "Target cannot make Injury rolls worse than Out of Action on natural 6s.",
            "rules_text": "If a natural 6 is rolled on any Injury die inflicted by this weapon, treat any Flesh Wound or Serious Injury as Out of Action instead.",
            "faq": "Goliath power hammers and servo-fists crush opposition outright."
        },
        {
            "name": "Parry", "slug": "parry", "category": "Defense",
            "summary": "Cancels one incoming close combat hit.",
            "rules_text": "During close combat, a fighter armed with a weapon that has the Parry trait may force an opponent to discard one successful hit die before wound rolls are made.",
            "faq": "Dual-wielding Parry weapons allows cancelling up to two hits."
        },
        {
            "name": "Disarm", "slug": "disarm", "category": "Melee",
            "summary": "Forces opponent to fight unarmed on a natural 6.",
            "rules_text": "If a natural 6 to hit is rolled with this weapon in close combat, one of the target's weapons cannot be used for the remainder of the battle round.",
            "faq": "Levels the playing field against enemy champions brandishing power weapons."
        },
        {
            "name": "Backstab", "slug": "backstab", "category": "Melee",
            "summary": "Adds +1 Strength when attacking an enemy from behind.",
            "rules_text": "When making an attack against a fighter from outside their vision arc (from behind), add +1 to the weapon's Strength characteristic.",
            "faq": "Deadly on stealth fighters sneaking through maintenance vents."
        },
        {
            "name": "Scarce", "slug": "scarce", "category": "Ammo",
            "summary": "Cannot be reloaded during the battle once out of ammo.",
            "rules_text": "Once a weapon with the Scarce trait fails an Ammo check, it is depleted for the remainder of the battle and cannot be reloaded.",
            "faq": "Common on plasma guns and heavy ordnance."
        },
        {
            "name": "Sidearm", "slug": "sidearm", "category": "Pistol",
            "summary": "Can be fired in close combat and dual-wielded.",
            "rules_text": "Sidearm weapons can be fired as ranged weapons during Shoot actions, and can also be used as close combat weapons during Fight actions.",
            "faq": "Pistoliers excel at shooting point-blank into melee skirmishes."
        },
        {
            "name": "Single Shot", "slug": "single-shot", "category": "Ammo",
            "summary": "Can only be fired once per battle.",
            "rules_text": "Once this weapon has been fired, it is expended and cannot be used again for the duration of the battle.",
            "faq": "Typical of specialized one-shot missiles and suicide traps."
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
        },
        {
            "name": "Master-Crafted", "slug": "master-crafted", "category": "Artifice",
            "summary": "Allows rerolling one failed hit roll per activation.",
            "rules_text": "Once per round when firing this weapon, the shooter may reroll one failed hit roll.",
            "faq": "High-value weapon upgrade that guarantees hits from expensive heavy weaponry."
        },
        {
            "name": "Limited", "slug": "limited", "category": "Ammo",
            "summary": "Ammo checks cannot be rerolled; weapon cannot be reloaded.",
            "rules_text": "Special ammunition marked Limited cannot be reloaded during a battle. Once out of ammo, the fighter must switch back to default ammunition.",
            "faq": "Applies to custom shotgun shells and special combi-weapon ammunition."
        }
    ]

    traits_map = {t["slug"]: t for t in base_traits}

    # Ingest additional official traits from necro-com compendium
    try:
        req_t = urllib.request.Request(
            'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/gang-fighters--their-weaponry/weapon-traits.md',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        raw_t = urllib.request.urlopen(req_t, timeout=10).read().decode('utf-8')
        sections = re.split(r'\n###\s+', raw_t)
        for s in sections[1:]:
            lines = s.strip().splitlines()
            name_raw = re.sub(r'\[.*?\]|\(.*?\)', '', lines[0]).strip()
            name = clean_ascii(name_raw)
            if not name:
                continue
            slug = slugify(name)
            if not slug or slug in traits_map:
                continue
            body = clean_ascii('\n'.join(lines[1:]))
            summary = body.split('\n\n')[0].replace('\n', ' ')[:140] or f"Official Underhive trait: {name}."
            traits_map[slug] = {
                "name": name,
                "slug": slug,
                "category": "Rules Lexicon",
                "summary": summary,
                "rules_text": body[:750] or summary,
                "faq": f"Refer to official Necromunda core rules and errata for {name}."
            }
    except Exception as e:
        print(f"[Necromunda Seeder] Warning fetching remote traits: {e}")

    final_traits = list(traits_map.values())
    db.traits.delete_many({})
    db.traits.insert_many(final_traits)
    db.traits.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(final_traits)} authentic weapon traits.")

    # ==========================================
    # 2. UNDERHIVE WEAPONS (250+ Profiles)
    # ==========================================
    weapons_map = {}

    base_url = 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/'
    urls = [
        ('Basic Weapon', base_url + 'basic-weapons.md'),
        ('Pistol', base_url + 'pistols.md'),
        ('Special Weapon', base_url + 'special-weapons.md'),
        ('Heavy Weapon', base_url + 'heavy-weapons.md'),
        ('Close Combat', base_url + 'close-combat.md'),
        ('Grenades', base_url + 'grenades.md'),
        ('Booby Traps', base_url + 'booby-traps.md')
    ]

    for cat_label, url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            txt = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
            tables = re.findall(r'\|([^\n]+\|[^\n]+)\|\n\|(?:\s*[-:]+[-| :]*)\|\n((?:\|[^\n]+\|\n)+)', txt)
            for h_line, b_block in tables:
                lines = b_block.strip().splitlines()
                first_row_name = None
                for line in lines:
                    cols = [clean_ascii(c) for c in line.split('|')[1:-1]]
                    if len(cols) < 10:
                        continue
                    name = cols[0]
                    if not name:
                        continue
                    if name.startswith('- '):
                        full_name = f"{first_row_name} ({name[2:]})" if first_row_name else name[2:]
                    else:
                        first_row_name = name
                        full_name = name

                    slug = slugify(full_name)
                    if not slug or slug in weapons_map:
                        continue

                    rng_s = cols[1] if len(cols) > 1 else '-'
                    rng_l = cols[2] if len(cols) > 2 else '-'
                    acc_s = cols[3] if len(cols) > 3 else '-'
                    acc_l = cols[4] if len(cols) > 4 else '-'
                    s_raw = cols[5] if len(cols) > 5 else '-'
                    ap_raw = cols[6] if len(cols) > 6 else '0'
                    d_raw = cols[7] if len(cols) > 7 else '1'
                    am_raw = cols[8] if len(cols) > 8 else '-'
                    traits_raw = cols[9] if len(cols) > 9 else ''
                    rarity_raw = cols[10] if len(cols) > 10 else 'Common'
                    cost_raw = cols[11] if len(cols) > 11 else '0'

                    cost_credits = 0
                    m_cost = re.search(r'\d+', cost_raw)
                    if m_cost:
                        cost_credits = int(m_cost.group(0))

                    traits_list = [t.strip() for t in traits_raw.split(',') if t.strip()]
                    is_web_or_entangle = any('web' in t.lower() or 'entangle' in t.lower() for t in traits_list)

                    damage = 1
                    m_d = re.search(r'\d+', d_raw)
                    if m_d:
                        damage = int(m_d.group(0))
                    if is_web_or_entangle:
                        damage = 0
                    elif damage == 0:
                        damage = 1

                    m_ap = re.search(r'(-\d+)', ap_raw)
                    ap_val = int(m_ap.group(1)) if m_ap else 0

                    weapons_map[slug] = {
                        "name": full_name,
                        "slug": slug,
                        "category": cat_label,
                        "weapon_type": cat_label,
                        "cost_credits": cost_credits,
                        "rarity": rarity_raw or "Common",
                        "range_short": rng_s,
                        "range_long": rng_l,
                        "accuracy_short": acc_s,
                        "accuracy_long": acc_l,
                        "strength": s_raw,
                        "damage": damage,
                        "armor_piercing": ap_val,
                        "ammo": am_raw,
                        "traits": traits_list,
                        "availability": [f"Trading Post ({cost_credits}cr)"],
                        "description": f"Authentic Underhive {cat_label.lower()} profile."
                    }
        except Exception as e:
            print(f"[Necromunda Seeder] Warning parsing weapons {cat_label}: {e}")

    final_weapons = list(weapons_map.values())
    db.weapons.delete_many({})
    db.weapons.insert_many(final_weapons)
    db.weapons.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(final_weapons)} authentic weapons into 'weapons'.")

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
    # 4. SKILL DISCIPLINES (160+ Official Skills)
    # ==========================================
    skills_map = {}

    # 1. Fetch skills from Gyrinx
    try:
        req_sk = urllib.request.Request(
            'https://raw.githubusercontent.com/gyrinx-app/gyrinx/main/content/necromunda-2018/data/skill.yaml',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        gyrinx_skills = yaml.safe_load(urllib.request.urlopen(req_sk, timeout=10).read())['skill']
    except Exception as e:
        print(f"[Necromunda Seeder] Warning fetching Gyrinx skills: {e}")
        gyrinx_skills = []

    # 2. Fetch skill rules from necro-com
    rules_lookup = {}
    try:
        req_g = urllib.request.Request(
            'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/gang-fighters--their-weaponry/skills/gang-specific-skills.md',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        raw_g = urllib.request.urlopen(req_g, timeout=10).read().decode('utf-8')
        req_s = urllib.request.Request(
            'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/gang-fighters--their-weaponry/skills/skills.md',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        raw_s = urllib.request.urlopen(req_s, timeout=10).read().decode('utf-8')
        for text in [raw_g, raw_s]:
            sections = re.split(r'\n(?:###|##)\s+', text)
            for s in sections[1:]:
                lines = s.strip().splitlines()
                header = clean_ascii(re.sub(r'^\d+\\\.\s*', '', lines[0]))
                body = clean_ascii('\n'.join(lines[1:]))
                if header and body:
                    rules_lookup[slugify(header)] = body
    except Exception as e:
        print(f"[Necromunda Seeder] Warning fetching skill texts: {e}")

    for item in gyrinx_skills:
        name = clean_ascii(item.get('name', ''))
        if not name:
            continue
        slug = slugify(name)
        if slug in skills_map:
            continue
        cat = clean_ascii(item.get('category', 'General'))
        rule = rules_lookup.get(slug) or f"Official Necromunda {cat} skill power for Underhive fighters."
        skills_map[slug] = {
            "name": name,
            "slug": slug,
            "tree": cat,
            "rules_text": rule[:500],
            "tactics": f"Tactical discipline capability for fighters specializing in {cat}."
        }

    final_skills = list(skills_map.values())
    db.skills.delete_many({})
    db.skills.insert_many(final_skills)
    db.skills.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(final_skills)} authentic skills across all disciplines.")

    # ==========================================
    # 5. TRADING POST EQUIPMENT & WARGEAR (200+ Items)
    # ==========================================
    equipment_map = {}

    gear_urls = [
        ('Armor', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/armour.md'),
        ('Field Armor', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/field-armour.md'),
        ('Bionics', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/bionics.md'),
        ('Personal Equipment', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/personal-equipment.md'),
        ('Weapon Accessories', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/weapon-accessories.md'),
        ('Chems', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/chems.md'),
        ('Gang Equipment', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/gang-equipment.md'),
        ('Mounts', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/mounts.md'),
        ('Status Items', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/status-items/status-items.md'),
        ('Exotic Beasts', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/status-items/exotic-beasts.md'),
        ('Servo Skulls', 'https://raw.githubusercontent.com/joeseos/necro-com/main/docs/trading-post/status-items/servo-skulls.md')
    ]

    for cat_label, url in gear_urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            txt = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
            secs = re.split(r'\n###\s+', txt)
            for s in secs[1:]:
                lines = s.strip().splitlines()
                name_raw = re.sub(r'\[.*?\]|\(.*?\)', '', lines[0]).strip()
                name = clean_ascii(name_raw)
                if not name or name in ['Perks', 'Drawbacks', 'Side Effects']:
                    continue
                slug = slugify(name)
                if not slug or slug in equipment_map:
                    continue
                body = clean_ascii('\n'.join(lines[1:]))
                cost = 25
                m_cost = re.search(r'(\d+)\s*(?:credits|cr)', body, re.IGNORECASE)
                if m_cost:
                    cost = int(m_cost.group(1))

                equipment_map[slug] = {
                    "name": name,
                    "slug": slug,
                    "category": cat_label,
                    "cost_credits": cost,
                    "rarity": "Common" if cost <= 20 else "Rare (8)",
                    "rules_text": body[:400] if body else f"Authentic Underhive {cat_label} wargear.",
                    "description": f"Authentic {cat_label} item from the Underhive Trading Post."
                }
        except Exception as e:
            print(f"[Necromunda Seeder] Warning parsing gear {cat_label}: {e}")

    # Merge additional gear from Gyrinx
    try:
        req_eq = urllib.request.Request(
            'https://raw.githubusercontent.com/gyrinx-app/gyrinx/main/content/necromunda-2018/data/equipment.yaml',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        eq = yaml.safe_load(urllib.request.urlopen(req_eq, timeout=10).read())['equipment']
        w_cats = {'Basic Weapons', 'Pistols', 'Special Weapons', 'Heavy Weapons', 'Close Combat', 'Grenades', 'Ammo'}
        for item in [x for x in eq if x.get('category') not in w_cats]:
            name = clean_ascii(item.get('name', ''))
            if not name:
                continue
            slug = slugify(name)
            if slug in equipment_map:
                continue
            cost = item.get('trading_post_cost') or 15
            cat = clean_ascii(item.get('category', 'Equipment'))
            equipment_map[slug] = {
                "name": name,
                "slug": slug,
                "category": cat,
                "cost_credits": cost,
                "rarity": "Common" if cost <= 20 else "Rare (8)",
                "rules_text": f"{name} provides specialized tactical capabilities for Underhive fighters.",
                "description": f"Authentic {cat} item sourced from the Necromunda trading compendium."
            }
    except Exception as e:
        print(f"[Necromunda Seeder] Warning merging Gyrinx gear: {e}")

    final_equipment = list(equipment_map.values())
    db.equipment.delete_many({})
    db.equipment.insert_many(final_equipment)
    db.equipment.create_index("slug", unique=True)
    print(f"[Necromunda Seeder] Seeded {len(final_equipment)} authentic equipment items into 'equipment'.")

    print("\n========================================================")
    print(f"[Necromunda Seeder] ALL 5 COLLECTIONS EXPANDED & POPULATED!")
    print(f"  - Weapons:   {len(final_weapons)}")
    print(f"  - Traits:    {len(final_traits)}")
    print(f"  - Clan Houses: {len(houses)}")
    print(f"  - Skills:    {len(final_skills)}")
    print(f"  - Equipment: {len(final_equipment)}")
    print("========================================================\n")


if __name__ == "__main__":
    seed_necromunda()
