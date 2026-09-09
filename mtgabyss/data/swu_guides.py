"""
mtgabyss.data.swu_guides
------------------------
Comprehensive, engaging articles and listicle primers for Star Wars: Unlimited (SWU).
Encompasses listicles, meta reviews, mechanical deep dives, and pilot guides.
Zero dates, zero fake editorial bylines, and rich entity linkage with wrap-up hooks.
"""

SWU_GUIDES = {
    "7-great-synergies-with-rey": {
        "slug": "7-great-synergies-with-rey",
        "title": "7 Great Synergies with Rey (More Than a Scavenger)",
        "subtitle": "How to turn low-power utility units into unstoppable threats using Rey's Experience acceleration.",
        "category": "Synergies & Top Lists",
        "read_time": "5 min read",
        "hero_card": {
            "name": "Rey",
            "subtitle": "More Than a Scavenger",
            "slug": "rey-more-than-a-scavenger-shd-4",
            "cost": 6,
            "aspects": ["Vigilance", "Heroism"]
        },
        "summary": "Rey: More Than a Scavenger gives an Experience token to any unit with 2 or less power every turn for just 1 resource. That transforms low-cost defensive walls, utility pilots, and cantrip units into terrifying mid-game brawlers.",
        "takeaways": [
            "Rey's ability targets current power: once a 2-power unit gets an Experience token and reaches 3 power, it can no longer receive more tokens until it is damaged, reset, or unless boosted differently.",
            "Restored ARC-170 and Yoda provide repeated healing and card filtering while scaling aggressively out of early removal range.",
            "Shield and Sentinel units benefit disproportionately because high HP combined with growing power forces unfavorable trades.",
            "Deploying Rey at 6 resources gives you Restore 3 and an On-Attack Experience pump without paying the 1-resource exhaust tax."
        ],
        "sections": [
            {
                "heading": "1. Restored ARC-170: Space Lane Dominance & Base Preservation",
                "paragraphs": [
                    "Restored ARC-170 enters the Space arena as a 2/3 for 2 resources with Restore 1. In standard play, a 2-power space unit struggles to defeat aggressive shielded fighters like Green Squadron A-Wing or TIE Advanced.",
                    "With Rey's ability on Turn 2, the ARC-170 immediately swings as a 3/4 Restore 1. It survives multiple combats in the space arena while continuously repairing base damage, buying you the exact buffer required to reach Rey's 6-resource deployment."
                ],
                "cards": [
                    {"name": "Restored ARC-170", "slug": "restored-arc-170-sor-44", "cost": 2, "role": "Space Anchor & Restore"}
                ]
            },
            {
                "heading": "2. Yoda (Old Master): The Cantrip Engine",
                "paragraphs": [
                    "Yoda is already one of the most efficient 3-cost units in Heroism Vigilance. Entering as a 2/4 with Restore 2 and When Defeated: Choose any number of players to draw 1 card.",
                    "Opponents hate killing Yoda because of his death trigger, but they cannot ignore him either. Pumping Yoda to a 3/5 with Rey puts him out of range of Open Fire and Force Choke. He becomes a steady 3-damage battering ram that heals your base for 2 every turn."
                ],
                "cards": [
                    {"name": "Yoda", "subtitle": "Old Master", "slug": "yoda-old-master-sor-45", "cost": 3, "role": "Card Draw & Mid-Range Bulwark"}
                ]
            },
            {
                "heading": "3. Guardian of the Whills: Turn 1 Value Spike",
                "paragraphs": [
                    "Guardian of the Whills costs 2 resources and boasts 2 power and 3 HP with the Force trait. Crucially, playing upgrades on Force units costs 1 less.",
                    "Rey curves naturally with Guardian: play Guardian on Turn 1, then on Turn 2 give Guardian an Experience token with Rey's action, or equip an upgrade at a discount. A 3/4 Force unit attacking on Turn 2 establishes instant arena initiative."
                ],
                "cards": [
                    {"name": "Guardian of the Whills", "slug": "guardian-of-the-whills-sor-61", "cost": 2, "role": "Force Upgrade Anchor"}
                ]
            },
            {
                "heading": "4. Ezra Bridger (Resourceful Troublemaker): Free Card Acceleration",
                "paragraphs": [
                    "Ezra Bridger enters as a 2/3 for 3 resources with When this unit attacks: Look at the top card of your deck. You may play it or leave it on top.",
                    "Ezra's only vulnerability is his fragile 2/3 stat line. One Experience token from Rey turns him into a 3/4, allowing him to attack safely into early enemy ground units like Death Star Stormtrooper or Viper Probe Droid while constantly giving you card selection."
                ],
                "cards": [
                    {"name": "Ezra Bridger", "subtitle": "Resourceful Troublemaker", "slug": "ezra-bridger-resourceful-troublemaker-sor-192", "cost": 3, "role": "Deck Top Filtering & Free Casts"}
                ]
            },
            {
                "heading": "5. R2-D2 (Ignoring Protocol): 1-Cost Sifting Machine",
                "paragraphs": [
                    "R2-D2 costs 1 resource and comes with 1 power and 4 HP. Whenever R2-D2 attacks or is played, you look at the top card of your deck and may place it on the bottom.",
                    "At 1 power, R2-D2 is normally just an intelligence scout. But with Rey, R2-D2 can be buffed on Turn 2 to a 2/5, and subsequently to a 3/6 if another source provides a second token. A 1-cost unit that controls deck flow while threatening 2 to 3 combat damage is absurd value."
                ],
                "cards": [
                    {"name": "R2-D2", "subtitle": "Ignoring Protocol", "slug": "r2-d2-ignoring-protocol-sor-236", "cost": 1, "role": "Early Scout & Scry"}
                ]
            },
            {
                "heading": "6. Bright Hope (The Last Transport): Sentinel Wall & Bounce",
                "paragraphs": [
                    "Bright Hope enters the Space arena for 4 resources with Sentinel and 2 power / 6 HP. When played, you can return a friendly ground unit to its owner's hand to draw a card.",
                    "Because Bright Hope has exactly 2 power, Rey can place an Experience token onto this mammoth 6-HP Sentinel! A 3/7 Space Sentinel shuts down Rebel A-Wings, TIE Fighters, and Firesprays alike, completely sealing the skies."
                ],
                "cards": [
                    {"name": "Bright Hope", "subtitle": "The Last Transport", "slug": "bright-hope-the-last-transport-sor-99", "cost": 4, "role": "Space Sentinel & Recycler"}
                ]
            },
            {
                "heading": "7. Kanan Jarrus (Revealed Jedi): Saboteur Deterrent & Base Recovery",
                "paragraphs": [
                    "Kanan Jarrus is a 4-cost 4/5 unit that heals 1 damage from your base whenever you play an Aspect card. But notice his synergy with Rey's leader unit flip: once Rey deploys at 6 resources, her Restore 3 stacks with Kanan's healing.",
                    "Together with Luke's Lightsaber attached to Rey or Kanan, you can heal 5 to 7 damage per turn, rendering enemy burn or aggro rushes completely obsolete."
                ],
                "cards": [
                    {"name": "Kanan Jarrus", "subtitle": "Revealed Jedi", "slug": "kanan-jarrus-revealed-jedi-sor-47", "cost": 4, "role": "Aspect Healing Synergy"}
                ]
            }
        ],
        "tactical_hook": {
            "title": "Tactical Pilot Briefing: The 2-Power Threshold",
            "summary": "Rey pilots should remember the golden rule: never buff a unit above 2 power with external cards before activating Rey. Activate Rey's Experience trigger first while the unit is at 2 or lower, then apply equipment, upgrades, or lightsabers afterward to maximize token yield."
        },
        "deckbuilder_cta": {
            "title": "Test This Rey Mid-Range Engine in the Deck Builder",
            "description": "Ready to take command? Load Rey with her core Vigilance and Heroism unit package directly into our interactive deck builder and draw a sample opening hand.",
            "leader_slug": "rey-more-than-a-scavenger-shd-4",
            "base_slug": "echo-base-sor-24",
            "recommended_cards": [
                {"name": "Yoda (Old Master)", "slug": "yoda-old-master-sor-45", "role": "Hand Advantage"},
                {"name": "Restored ARC-170", "slug": "restored-arc-170-sor-44", "role": "Space Control"},
                {"name": "Bright Hope", "slug": "bright-hope-the-last-transport-sor-99", "role": "Space Sentinel"}
            ],
            "builder_query": "leader=rey-more-than-a-scavenger-shd-4&base=echo-base-sor-24&deck=restored-arc-170-sor-44:3,yoda-old-master-sor-45:3,guardian-of-the-whills-sor-61:3,bright-hope-the-last-transport-sor-99:2,r2-d2-ignoring-protocol-sor-236:3,kanan-jarrus-revealed-jedi-sor-47:2"
        },
        "related_guides": [
            {"slug": "action-economy-and-the-initiative", "title": "Mastering the Initiative: Why Taking the Token Wins Star Wars: Unlimited", "category": "Core Strategy"},
            {"slug": "aspect-color-pie-and-deck-craft", "title": "The SWU Aspect Philosophy: Finding Your Two-Color Identity", "category": "Deck Craft"}
        ]
    },

    "top-bounty-hunter-payoffs-boba-fett": {
        "slug": "top-bounty-hunter-payoffs-boba-fett",
        "title": "5 Brutal Bounty Hunter Payoffs with Boba Fett",
        "subtitle": "Harnessing temporary exhaust triggers, free resource readying, and bounty payouts in competitive Cunning Villainy.",
        "category": "Synergies & Top Lists",
        "read_time": "6 min read",
        "hero_card": {
            "name": "Boba Fett",
            "subtitle": "Collecting the Bounty",
            "slug": "boba-fett-collecting-the-bounty-sor-15",
            "cost": 5,
            "aspects": ["Cunning", "Villainy"]
        },
        "summary": "Boba Fett: Collecting the Bounty has reigned as one of the premier competitive leaders in Star Wars: Unlimited. His leader ability readies a resource the first time an enemy unit leaves play each round, generating unmatched tempo when combined with cheap bounties.",
        "takeaways": [
            "Boba's resource readying triggers on ANY enemy departure: defeat, bounce (Waylay), or capture.",
            "Deploying Boba at 5 resources gives you a 4/7 body that readies two resources when enemy cards leave play.",
            "Stacking Wanted or Bounty Hunter payoffs lets you gain up to 4 extra effective resources in a single turn.",
            "Tempo over raw value: Boba doesn't grind for turn 10; he overwhelms the opponent on turns 3 through 5."
        ],
        "sections": [
            {
                "heading": "1. Jango Fett (Renowned Bounty Hunter): Free Exhaust Pressure",
                "paragraphs": [
                    "Jango Fett enters for 4 resources as a 4/4 with When this unit attacks or an enemy unit is defeated: You may exhaust an enemy unit with equal or lower power.",
                    "Combined with Boba Fett, defeating an enemy minion readies Boba's resource while simultaneously letting Jango lock down the opponent's biggest surviving threat. This prevents counter-attacks and preserves your board control completely."
                ],
                "cards": [
                    {"name": "Jango Fett", "subtitle": "Renowned Bounty Hunter", "slug": "jango-fett-renowned-bounty-hunter-shd-138", "cost": 4, "role": "Board Freeze & Exhaust"}
                ]
            },
            {
                "heading": "2. Bossk (Deadly Stalker): Multi-Arena Ping Damage",
                "paragraphs": [
                    "Bossk is a 4/5 for 4 resources in Cunning Villainy with Ambush. When Bossk attacks, he deals 2 damage to a ground unit or base.",
                    "Ambush allows Bossk to immediately strike an enemy unit the turn he is played. When that target dies, Boba Fett's passive triggers immediately, refunding 1 resource back into your pool to spend on an Event or Upgrade in the very next action."
                ],
                "cards": [
                    {"name": "Bossk", "subtitle": "Deadly Stalker", "slug": "bossk-deadly-stalker-sor-182", "cost": 4, "role": "Ambush Removal & Double Tempo"}
                ]
            },
            {
                "heading": "3. Wanted: The 0-Cost Resource Rocket",
                "paragraphs": [
                    "Wanted is a 0-cost Bounty upgrade. You attach it to an enemy unit. When that unit is defeated or captured, its bounty reads: Ready 2 resources.",
                    "Combine Wanted with Boba Fett: defeat the target unit, Boba readies 1 resource, and Wanted readies 2 resources. You net 3 ready resources in a single turn! This enables catastrophic tempo swings, allowing you to cast Fett's Firespray multiple turns ahead of schedule."
                ],
                "cards": [
                    {"name": "Wanted", "slug": "wanted-shd-221", "cost": 0, "role": "Bounty Acceleration"}
                ]
            },
            {
                "heading": "4. Fett's Firespray: The Aerial Game Ender",
                "paragraphs": [
                    "Fett's Firespray is a 5/6 Space unit for 6 resources. When played, if you control Boba Fett or Jango Fett, you may ready Fett's Firespray.",
                    "Dropping Firespray with Boba deployed means you immediately swing for 5 space damage the moment it hits the board. Because Boba's leader flip produces extra resources, Firespray frequently enters on Turn 4 instead of Turn 5, catching space defenders totally unprepared."
                ],
                "cards": [
                    {"name": "Fett's Firespray", "subtitle": "Pursuing the Bounty", "slug": "fetts-firespray-pursuing-the-bounty-sor-184", "cost": 6, "role": "Immediate Space Ambush"}
                ]
            },
            {
                "heading": "5. Waylay & No Good to Me Dead: Non-Lethal Tempo Engines",
                "paragraphs": [
                    "Opponents often think they can stall Boba by playing massive Sentinel cards like Reinforcement Walker or Devastator. But Cunning gives Boba access to Waylay and No Good to Me Dead.",
                    "Returning a 7-cost unit to the opponent's hand triggers Boba Fett's resource readying, resets their entire turn of progress, and leaves their base completely undefended."
                ],
                "cards": [
                    {"name": "Waylay", "slug": "waylay-sor-222", "cost": 3, "role": "Tempo Bounce Trigger"},
                    {"name": "No Good to Me Dead", "slug": "no-good-to-me-dead-sor-186", "cost": 3, "role": "Freeze Lockdown"}
                ]
            }
        ],
        "tactical_hook": {
            "title": "Tactical Pilot Briefing: Timing the Ready Trigger",
            "summary": "Remember that Boba's leader ability only triggers once per round while on his leader side. Do not waste the trigger when all your resources are already ready! Spend your resources first on an action or event, then trigger the kill to immediately recover your spent resource."
        },
        "deckbuilder_cta": {
            "title": "Build and Test Boba Cunning Villainy",
            "description": "Assemble the premiere bounty hunting strike team with our deck builder. Check your resource curve and draw opening hands against the clock.",
            "leader_slug": "boba-fett-collecting-the-bounty-sor-15",
            "base_slug": "tarkintown-sor-25",
            "recommended_cards": [
                {"name": "Bossk (Deadly Stalker)", "slug": "bossk-deadly-stalker-sor-182", "role": "Ambush Striker"},
                {"name": "Wanted", "slug": "wanted-shd-221", "role": "Resource Engine"},
                {"name": "Fett's Firespray", "slug": "fetts-firespray-pursuing-the-bounty-sor-184", "role": "Aerial Finisher"}
            ],
            "builder_query": "leader=boba-fett-collecting-the-bounty-sor-15&base=tarkintown-sor-25&deck=bossk-deadly-stalker-sor-182:3,jango-fett-renowned-bounty-hunter-shd-138:3,wanted-shd-221:3,fetts-firespray-pursuing-the-bounty-sor-184:2,waylay-sor-222:3,no-good-to-me-dead-sor-186:3"
        },
        "related_guides": [
            {"slug": "action-economy-and-the-initiative", "title": "Mastering the Initiative: Why Taking the Token Wins Star Wars: Unlimited", "category": "Core Strategy"},
            {"slug": "smuggle-mechanics-and-resource-math", "title": "The Smuggle Engine: Turning Resource Piles into Hidden Hands", "category": "Card Mechanics"}
        ]
    },

    "sampling-key-expansions-sor-shd-twi": {
        "slug": "sampling-key-expansions-sor-shd-twi",
        "title": "Sampling Key Expansions: Spark of Rebellion to Twilight of the Republic",
        "subtitle": "How the mechanical identity of SWU evolved across its premiere releases.",
        "category": "Expansions & Meta",
        "read_time": "7 min read",
        "hero_card": {
            "name": "Darth Vader",
            "subtitle": "Dark Lord of the Sith",
            "slug": "darth-vader-dark-lord-of-the-sith-sor-10",
            "cost": 7,
            "aspects": ["Aggression", "Villainy"]
        },
        "summary": "Every SWU expansion introduces distinct design philosophies and mechanics. From the foundational raw stat lines of Spark of Rebellion (SOR) to the underworld contracts of Shadows of the Galaxy (SHD) and the token swarms of Twilight of the Republic (TWI), here is how the game evolved.",
        "takeaways": [
            "Spark of Rebellion (SOR) established clean foundational keywords: Sentinel, Ambush, Shield, and Experience.",
            "Shadows of the Galaxy (SHD) added Smuggle and Bounty, transforming the resource pile from passive fuel into an interactive second hand.",
            "Twilight of the Republic (TWI) shifted the game toward Clone Trooper and Droid token swarms via Coordinate and Exploit mechanics.",
            "Cross-set synergy is where modern deckbuilding thrives: using SHD Smuggle cards to smooth out high-cost SOR bombs."
        ],
        "sections": [
            {
                "heading": "Spark of Rebellion (SOR): The Foundational Pillars",
                "paragraphs": [
                    "Released as the premiere base set, Spark of Rebellion focused on pure tactical combat. The design emphasized dual-arena balance between Ground and Space units, rewarding players for understanding card economy and lane presence.",
                    "Key staples from SOR—like Luke Skywalker (Faithful Friend), Darth Vader (Commanding presence), and Superlaser Technician—remain cornerstones of the competitive landscape because of their raw efficiency and unconditional power."
                ],
                "cards": [
                    {"name": "Darth Vader", "subtitle": "Dark Lord of the Sith", "slug": "darth-vader-dark-lord-of-the-sith-sor-10", "cost": 7, "role": "Premier Late-Game Finisher"},
                    {"name": "Superlaser Technician", "slug": "superlaser-technician-sor-83", "cost": 3, "role": "Universal Ramp"}
                ]
            },
            {
                "heading": "Shadows of the Galaxy (SHD): The Underworld Revolution",
                "paragraphs": [
                    "Shadows of the Galaxy fundamentally altered how players view the resource row. Prior to SHD, once a card was placed facedown as a resource, it was gone forever.",
                    "The introduction of Smuggle allowed players to cast cards directly from their resource row by paying a smuggle cost and replacing the card with the top of their deck. Combined with Capture and Bounties, SHD rewarded dynamic risk calculation and reactive play."
                ],
                "cards": [
                    {"name": "Rey", "subtitle": "More Than a Scavenger", "slug": "rey-more-than-a-scavenger-shd-4", "cost": 6, "role": "Experience Engine"},
                    {"name": "Wanted", "slug": "wanted-shd-221", "cost": 0, "role": "Underworld Bounty"}
                ]
            },
            {
                "heading": "Twilight of the Republic (TWI): The Clone Wars & Swarm Tactics",
                "paragraphs": [
                    "Twilight of the Republic brought the massive armies of the Clone Wars to life. Featuring Jedi Generals and Separatist commanders, TWI introduced Token Units (Clone Troopers and Battle Droids) that flood the board.",
                    "Mechanics like Coordinate reward you for controlling 3 or more units, while Exploit lets you defeat friendly token units to discount massive battlecruisers and war machines, creating explosive combo turns."
                ],
                "cards": [
                    {"name": "Obi-Wan Kenobi", "subtitle": "Patient Mentor", "slug": "obi-wan-kenobi-patient-mentor-twi-3", "cost": 6, "role": "Token Commander"},
                    {"name": "R2-D2", "subtitle": "Full of Solutions", "slug": "r2-d2-full-of-solutions-twi-193", "cost": 2, "role": "Token Support"}
                ]
            }
        ],
        "tactical_hook": {
            "title": "Tactical Pilot Briefing: Blending Set Philosophies",
            "summary": "When building decks across multiple expansions, avoid the trap of isolating set mechanics. The strongest decks blend SOR's efficient removal (Takedown, Overwhelming Barrage) with SHD's resource flexibility (Smuggle) and TWI's board width (Exploit)."
        },
        "deckbuilder_cta": {
            "title": "Experiment with Multi-Set Deck Archetypes",
            "description": "Filter by expansion and craft hybrid tournament lists with our deck builder and opening hand simulator.",
            "leader_slug": "darth-vader-dark-lord-of-the-sith-sor-10",
            "base_slug": "command-center-sor-23",
            "recommended_cards": [
                {"name": "Darth Vader", "slug": "darth-vader-dark-lord-of-the-sith-sor-10", "role": "Late Game"},
                {"name": "Superlaser Technician", "slug": "superlaser-technician-sor-83", "role": "Resource Ramp"},
                {"name": "Wanted", "slug": "wanted-shd-221", "role": "Tempo Bounty"}
            ],
            "builder_query": "leader=darth-vader-dark-lord-of-the-sith-sor-10&base=command-center-sor-23&deck=superlaser-technician-sor-83:3,wanted-shd-221:3"
        },
        "related_guides": [
            {"slug": "aspect-color-pie-and-deck-craft", "title": "The SWU Aspect Philosophy: Finding Your Two-Color Identity", "category": "Deck Craft"},
            {"slug": "smuggle-mechanics-and-resource-math", "title": "The Smuggle Engine: Turning Resource Piles into Hidden Hands", "category": "Card Mechanics"}
        ]
    },

    "action-economy-and-the-initiative": {
        "slug": "action-economy-and-the-initiative",
        "title": "Mastering the Initiative: Why Taking the Token Wins Star Wars: Unlimited",
        "subtitle": "A masterclass in alternating tempo, passing psychology, and knowing when to claim the token over attacking.",
        "category": "Core Strategy",
        "read_time": "6 min read",
        "hero_card": {
            "name": "Sabine Wren",
            "subtitle": "Galvanized Revolutionary",
            "slug": "sabine-wren-galvanized-revolutionary-sor-14",
            "cost": 4,
            "aspects": ["Aggression", "Heroism"]
        },
        "summary": "Unlike games where one player executes an entire turn before passing, Star Wars: Unlimited alternates action-by-action. Taking the Initiative token is not just an afterthought—it dictates who strikes first in the next round.",
        "takeaways": [
            "Taking the initiative costs your current action, but guarantees you make the first move next turn.",
            "Going first on a leader deployment turn (e.g. Turn 4 or 5) lets you attack or remove enemy units before the opposing leader can swing.",
            "The 'Pass Bluff': Waiting out opponent activations with cheap cantrips forces them to commit their big threats into your open removal.",
            "Aggro decks prioritize the initiative token to prevent mid-range decks from stabilizing with Sentinels."
        ],
        "sections": [
            {
                "heading": "The Alternating Action Trap",
                "paragraphs": [
                    "In SWU, every single card play, attack, or ability activation passes priority back to the opponent. If you attack their base, they immediately have the chance to attack your unit, play an ambush unit, or drop a sentinel.",
                    "Novice pilots often exhaust all their units to deal maximum face damage, only to watch their opponent grab the Initiative token for free. Next round, the opponent deploys their leader and wipes out your board before your units even untap."
                ]
            },
            {
                "heading": "The Leader Deployment Threshold",
                "paragraphs": [
                    "Most leaders deploy at 5, 6, or 7 resources. The round immediately preceding that deployment is known as the 'Threshold Round'.",
                    "If you have 4 resources and will deploy Boba Fett or Sabine Wren next turn, claiming the initiative token in the current round ensures your leader swings or triggers abilities first. Allowing your opponent to take initiative means they can immediately play an Event like Takedown or Waylay before you ever attack."
                ],
                "cards": [
                    {"name": "Sabine Wren", "subtitle": "Galvanized Revolutionary", "slug": "sabine-wren-galvanized-revolutionary-sor-14", "cost": 4, "role": "Fast Aggro Leader"},
                    {"name": "Waylay", "slug": "waylay-sor-222", "cost": 3, "role": "Initiative Punisher"}
                ]
            }
        ],
        "tactical_hook": {
            "title": "Tactical Pilot Briefing: The Calculation of Leaving 1 Attack on the Table",
            "summary": "If you have one small unit left that could deal 2 damage to the enemy base, but claiming initiative prevents the enemy from deploying and attacking with a 6-power unit first next turn, claim the initiative immediately. 2 damage now is never worth losing board parity next round."
        },
        "deckbuilder_cta": {
            "title": "Test Aggressive Initiative Curves",
            "description": "Construct high-tempo aggressive decks in our deck builder and verify how many Turn 1 through Turn 3 plays you have.",
            "leader_slug": "sabine-wren-galvanized-revolutionary-sor-14",
            "base_slug": "chopper-base-sor-30",
            "recommended_cards": [
                {"name": "Sabine Wren", "slug": "sabine-wren-galvanized-revolutionary-sor-14", "role": "Aggro Commander"},
                {"name": "Green Squadron A-Wing", "slug": "green-squadron-a-wing-sor-141", "role": "Turn 1 Aggro"},
                {"name": "Fighters for Freedom", "slug": "fighters-for-freedom-sor-143", "role": "Burn Ping"}
            ],
            "builder_query": "leader=sabine-wren-galvanized-revolutionary-sor-14&base=chopper-base-sor-30&deck=green-squadron-a-wing-sor-141:3,fighters-for-freedom-sor-143:3"
        },
        "related_guides": [
            {"slug": "7-great-synergies-with-rey", "title": "7 Great Synergies with Rey (More Than a Scavenger)", "category": "Synergies & Top Lists"},
            {"slug": "top-bounty-hunter-payoffs-boba-fett", "title": "5 Brutal Bounty Hunter Payoffs with Boba Fett", "category": "Synergies & Top Lists"}
        ]
    },

    "aspect-color-pie-and-deck-craft": {
        "slug": "aspect-color-pie-and-deck-craft",
        "title": "The SWU Aspect Philosophy: Finding Your Two-Color Identity",
        "subtitle": "Breaking down Vigilance, Command, Aggression, and Cunning alongside the Heroism/Villainy divide.",
        "category": "Core Strategy",
        "read_time": "7 min read",
        "hero_card": {
            "name": "Grand Moff Tarkin",
            "subtitle": "Oversector Governor",
            "slug": "grand-moff-tarkin-oversector-governor-sor-7",
            "cost": 5,
            "aspects": ["Command", "Villainy"]
        },
        "summary": "Every deck in Star Wars: Unlimited is defined by its Leader and Base aspects. Understanding the mechanical philosophies of Blue, Green, Red, and Yellow is the key to mastering deck construction.",
        "takeaways": [
            "Vigilance (Blue): Control, defense, healing, and Sentinel walls.",
            "Command (Green): Ramp, resource acceleration, and high-stat military powerhouses.",
            "Aggression (Red): Direct base damage, burn events, and explosive Saboteur rushers.",
            "Cunning (Yellow): Bounce, exhaust, discard, trickery, and smuggle mechanics.",
            "The Out-of-Aspect Penalty (+2 Cost): Sometimes paying 2 extra resources for an off-aspect bomb is game-winning."
        ],
        "sections": [
            {
                "heading": "Vigilance (Blue) & Command (Green): The Mid-Range & Ramp Kings",
                "paragraphs": [
                    "Blue is about longevity: healing your base with Restore, neutralizing incoming attacks with Sentinels, and eliminating key targets with defeat spells. Pairing Blue with Green allows you to ramp resources with Superlaser Technician and drop giant endgame threats turns ahead of curve."
                ],
                "cards": [
                    {"name": "Superlaser Technician", "slug": "superlaser-technician-sor-83", "cost": 3, "role": "Command Ramp"},
                    {"name": "Obi-Wan Kenobi", "subtitle": "Following Fate", "slug": "obi-wan-kenobi-following-fate-sor-49", "cost": 6, "role": "Vigilance Sentinel & Buff"}
                ]
            },
            {
                "heading": "Aggression (Red) & Cunning (Yellow): Maximum Pressure & Disruption",
                "paragraphs": [
                    "Red wants the match over as quickly as possible. Every unit is evaluated on how many points of damage it delivers per resource spent.",
                    "Yellow acts as the force multiplier: exhausting enemy blockers, stealing tempo with bounce effects like Waylay, and generating surprise burst attacks with Ambush units."
                ],
                "cards": [
                    {"name": "Sabine Wren", "subtitle": "Explosives Artist", "slug": "sabine-wren-explosives-artist-sor-142", "cost": 2, "role": "Aggressive Face Pressure"},
                    {"name": "Waylay", "slug": "waylay-sor-222", "cost": 3, "role": "Cunning Tempo Tool"}
                ]
            }
        ],
        "tactical_hook": {
            "title": "Tactical Pilot Briefing: Evaluating the Aspect Penalty",
            "summary": "Do not fear the +2 aspect penalty when an off-aspect card solves your deck's fundamental weakness. An aggressive Sabine deck might gladly pay 4 resources for a 2-cost Vigilance card if it prevents an opponent from stabilizing."
        },
        "deckbuilder_cta": {
            "title": "Craft Multi-Aspect Decks in Our Deck Builder",
            "description": "Select your Leader and Base to instantly view your deck's aspect balance, cost curve, and arena split.",
            "leader_slug": "grand-moff-tarkin-oversector-governor-sor-7",
            "base_slug": "command-center-sor-23",
            "recommended_cards": [
                {"name": "Grand Moff Tarkin", "slug": "grand-moff-tarkin-oversector-governor-sor-7", "role": "Imperial Commander"},
                {"name": "Superlaser Technician", "slug": "superlaser-technician-sor-83", "role": "Command Ramp"}
            ],
            "builder_query": "leader=grand-moff-tarkin-oversector-governor-sor-7&base=command-center-sor-23"
        },
        "related_guides": [
            {"slug": "sampling-key-expansions-sor-shd-twi", "title": "Sampling Key Expansions: Spark of Rebellion to Twilight of the Republic", "category": "Expansions & Meta"},
            {"slug": "action-economy-and-the-initiative", "title": "Mastering the Initiative: Why Taking the Token Wins Star Wars: Unlimited", "category": "Core Strategy"}
        ]
    },

    "smuggle-mechanics-and-resource-math": {
        "slug": "smuggle-mechanics-and-resource-math",
        "title": "The Smuggle Engine: Turning Resource Piles into Hidden Hands",
        "subtitle": "How card valuation changes when facedown resources can be played directly to the board.",
        "category": "Card Mechanics",
        "read_time": "5 min read",
        "hero_card": {
            "name": "Han Solo",
            "subtitle": "Audacious Smuggler",
            "slug": "han-solo-audacious-smuggler-sor-17",
            "cost": 6,
            "aspects": ["Cunning", "Heroism"]
        },
        "summary": "Introduced in Shadows of the Galaxy, the Smuggle keyword fundamentally changed hand management in SWU. Instead of agonizing over whether to resource a situational card, Smuggle cards can be safely tucked away and cast later.",
        "takeaways": [
            "Smuggle reads: Pay [cost] to play this card from your resources. If you do, put the top card of your deck into your resources facedown.",
            "Smuggle never reduces your total resource count: the played card is immediately replaced by the top card of your deck.",
            "Resource manipulation leaders like Han Solo can cheat Smuggle cards into play early.",
            "Late game card advantage: In top-deck wars, having 2 or 3 Smuggle cards in your resources gives you extra playable options without needing cards in hand."
        ],
        "sections": [
            {
                "heading": "Why Smuggle Eliminates Resource Regret",
                "paragraphs": [
                    "In most TCGs, committing a late-game card as a resource on Turn 1 feels disastrous if the game drags out. Smuggle completely eliminates this psychological friction.",
                    "When you resource a Smuggle card early, you are not discarding it; you are placing it into a secondary, protected hand that your opponent cannot discard with cards like Spark of Rebellion."
                ],
                "cards": [
                    {"name": "Han Solo", "subtitle": "Audacious Smuggler", "slug": "han-solo-audacious-smuggler-sor-17", "cost": 6, "role": "Resource Cheating Leader"},
                    {"name": "Spark of Rebellion", "slug": "spark-of-rebellion-sor-200", "cost": 2, "role": "Hand Discard"}
                ]
            },
            {
                "heading": "The Smuggle Math: Paying for Virtual Card Draw",
                "paragraphs": [
                    "Smuggle cards typically cost 1 to 2 resources more when cast via Smuggle compared to casting them from hand. However, because casting via Smuggle does not consume a card from your hand and replaces itself in the resource row, it is effectively equivalent to: Cast this card and draw a card.",
                    "In a high-attrition game, casting even one Smuggle unit can swing the game by maintaining pressure while preserving your hand."
                ]
            }
        ],
        "tactical_hook": {
            "title": "Tactical Pilot Briefing: Memorizing Your Resource Order",
            "summary": "While facedown resources cannot be rearranged at will, the rules permit you to look at your own facedown resources at any time. Take note of which slot your Smuggle cards occupy so you can activate them instantly when your resource total hits the smuggle requirement."
        },
        "deckbuilder_cta": {
            "title": "Build a Smuggle-Fueled Cunning Deck",
            "description": "Construct and simulate Han Solo and Cunning decks in our deck builder to see how Smuggle optimizes early resource choices.",
            "leader_slug": "han-solo-audacious-smuggler-sor-17",
            "base_slug": "administrators-tower-sor-29",
            "recommended_cards": [
                {"name": "Han Solo", "slug": "han-solo-audacious-smuggler-sor-17", "role": "Smuggler Leader"},
                {"name": "Crafty Smuggler", "slug": "crafty-smuggler-sor-207", "role": "Early Unblockable"}
            ],
            "builder_query": "leader=han-solo-audacious-smuggler-sor-17&base=administrators-tower-sor-29"
        },
        "related_guides": [
            {"slug": "7-great-synergies-with-rey", "title": "7 Great Synergies with Rey (More Than a Scavenger)", "category": "Synergies & Top Lists"},
            {"slug": "top-bounty-hunter-payoffs-boba-fett", "title": "5 Brutal Bounty Hunter Payoffs with Boba Fett", "category": "Synergies & Top Lists"}
        ]
    }
}
