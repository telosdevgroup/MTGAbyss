"""
mtgabyss.data.dominion_guides
-----------------------------
Comprehensive, authoritative strategy primers for Dominion.
Focuses purely on high-craft game theory, card math, and kingdom combos.
"""

DOMINION_GUIDES = {
    "mathematics-of-trashing": {
        "slug": "mathematics-of-trashing",
        "title": "The Mathematics of Trashing: Why Card Density Wins 80% of Games",
        "subtitle": "A quantitative look at turn-to-turn hand cycling velocity, the terminal trashing threshold, and why a 12-card deck crushes a 25-card deck.",
        "category": "Strategy & Mechanics",
        "read_time": "6 min read",
        "hero_card": {
            "name": "Chapel",
            "slug": "chapel",
            "cost": 2,
            "set_name": "Base"
        },
        "summary": "Beginner players often hesitate to trash their starting Coppers and Estates. But mathematically, starting cards are actively harmful dead weight that dilute your buying power. Trashing creates card density, ensuring you draw your high-value cards every single turn.",
        "takeaways": [
            "Your 7 starting Coppers and 3 Estates give you an average card value of just $0.70 per draw.",
            "Trashing 4 starting cards in the first two shuffles doubles your probability of drawing Gold and key Actions on curve.",
            "The 'Terminal Trashing Threshold': Stop trashing when your deck can reliably generate $8+ each shuffle without stalling.",
            "Fast trashers (Chapel, Steward, Sentry) outpace passive trashers by reaching the critical 12-card density 3 to 4 turns earlier."
        ],
        "sections": [
            {
                "heading": "The Starting Deck Trap: Calculating Draw Density",
                "paragraphs": [
                    "Every game of Dominion begins with a 10-card deck: 7 Coppers and 3 Estates. In your opening hands, your average card delivers just $0.70 in purchasing power ($7 divided by 10 cards). The 3 Estates contribute $0.00 to your economy while consuming 30% of your hand slots.",
                    "When you purchase a Silver or a $5 Action, adding it to an untrashed 10-card deck dilutes its impact. In a 12-card deck, that key card only appears once every 2.4 turns. But if you trash 4 Coppers and 3 Estates, reducing your deck to 5 high-impact cards, you draw that exact card virtually every single turn.",
                    "This is the principle of card density: winning Dominion is rarely about how many cards you own; it is about how frequently your best cards hit the table."
                ]
            },
            {
                "heading": "Chapel vs. Steward vs. Sentry: Trashing Velocity",
                "paragraphs": [
                    "Different kingdom trashers accomplish thinning at radically different speeds:",
                    "1. Chapel ($2): The undisputed king of trashing. Trashing up to 4 cards in a single action allows a player to purge all 3 Estates and a Copper on Turn 3, instantly transforming deck velocity.",
                    "2. Steward ($3): A versatile modal trasher. While it only trashes 2 cards at a time, its flexibility (+2 Cards or +$2) means it never becomes a dead draw in the late game after your deck is thinned.",
                    "3. Sentry ($5): The modern powerhouse. As a non-terminal cantrip (+1 Card, +1 Action), Sentry allows you to inspect the top 2 cards, trashing junk without consuming your Action slot."
                ],
                "cards": [
                    {"name": "Chapel", "slug": "chapel", "cost": 2, "role": "Maximum Velocity"},
                    {"name": "Steward", "slug": "steward", "cost": 3, "role": "Modal Flexibility"},
                    {"name": "Sentry", "slug": "sentry", "cost": 5, "role": "Non-Terminal Cantrip"}
                ]
            },
            {
                "heading": "The Terminal Trashing Threshold",
                "paragraphs": [
                    "A classic error in aggressive trashing is over-thinning: trashing down so small that you lack the purchasing power to buy Provinces. The golden rule is the Terminal Trashing Threshold.",
                    "Once your deck consistently produces $8 (or $8 + an extra Buy) every single turn, stop using your trashing actions and pivot 100% into victory points (greening). In a clean 10-to-12 card deck consisting of 2 Golds, 2 Silvers, and supporting Actions, you will claim a Province every single shuffle."
                ]
            }
        ],
        "combo_cta": {
            "title": "The Classic Trashing Engine Combo",
            "description": "Pairing Chapel with early Silver is the fundamental benchmark of competitive Dominion. To enrich this combo into an unstoppable mid-game engine, add these 3 companion kingdom cards:",
            "core_cards": [
                {"name": "Chapel", "slug": "chapel"},
                {"name": "Silver", "slug": "silver"}
            ],
            "companions": [
                {
                    "name": "Market",
                    "slug": "market",
                    "cost": 5,
                    "reason": "+1 Buy & Cantrip: Converts high single-turn cash into multiple Provinces once your deck is thinned."
                },
                {
                    "name": "Militia",
                    "slug": "militia",
                    "cost": 4,
                    "reason": "Hand Choke Attack: Punishes opponents with clogged, untrashed decks while giving you +$2."
                },
                {
                    "name": "Sentry",
                    "slug": "sentry",
                    "cost": 5,
                    "reason": "Deck Filtering: Sifts through upcoming draws so your remaining Golds never get buried."
                }
            ],
            "generator_query": "chapel,silver,market,militia,sentry"
        }
    },
    "engine-architecture": {
        "slug": "engine-architecture",
        "title": "The Engine Architecture: Action Economy & The 'Village-Smithy' Balance",
        "subtitle": "How to design infinite-draw kingdoms without terminal collision, calculate the golden ratio of Actions to Draw, and secure multiple Buys.",
        "category": "Deckbuilding & Theory",
        "read_time": "7 min read",
        "hero_card": {
            "name": "Village",
            "slug": "village",
            "cost": 3,
            "set_name": "Base"
        },
        "summary": "Building a full Dominion engine allows you to draw your entire deck every single turn, generate massive coin, and buy 2 to 3 Provinces in a single round. Here is the mathematical framework for balancing Action generators against raw card draw.",
        "takeaways": [
            "Every turn starts with exactly 1 Action. Any Action card that does not provide '+2 Actions' is a terminal action.",
            "The Golden Ratio: For every raw draw card (Smithy, Council Room), you need at least 1.5 to 2 Action providers (Village, Festival, Worker's Village).",
            "Draw before buying: Always resolve your Villages and draw spells before playing terminal payload cards like Militia or Moneylender.",
            "Without '+Buy' (Market, Festival, Bridge), an engine with $18 is wasted because it can still only purchase 1 Province."
        ],
        "sections": [
            {
                "heading": "The Terminal Collision Problem",
                "paragraphs": [
                    "The most frequent pitfall for new engine builders is terminal collision: holding 3 powerful Action cards in hand (such as Smithy, Militia, and Witch) with only 1 Action to spend.",
                    "Playing one card means the other two are wasted for the turn. To solve this, your deck must include dedicated Action generators like Village (+1 Card, +2 Actions) or Festival (+2 Actions, +$2, +1 Buy).",
                    "When sequenced properly, a Village provides the surplus action required to play Smithy (+3 Cards), which in turn draws into more Villages, allowing you to sustain an unbroken chain of actions until your entire deck is in hand."
                ]
            },
            {
                "heading": "The Golden Ratio: Actions to Draw Cards",
                "paragraphs": [
                    "A functioning engine requires a precise ratio of card categories:",
                    "1. Action Starters (Village, Worker's Village): Produce +2 Actions net. You want roughly 4 to 6 of these in a 20-card engine.",
                    "2. Mass Draw (Smithy, Council Room, Patrol): Draw 3 to 4 cards net. You typically need 2 to 3 of these. Too many draw cards without villages causes immediate terminal stalling.",
                    "3. Non-Terminal Cantrips (Laboratory, Market, Poacher): Replace themselves (+1 Card, +1 Action). These are 'free' cards that increase reliability without altering your action count.",
                    "4. Payload & Buys (Festival, Market, Bridge): Convert your drawn cards into purchasing power and multiple Buys."
                ],
                "cards": [
                    {"name": "Village", "slug": "village", "cost": 3, "role": "Action Generator"},
                    {"name": "Smithy", "slug": "smithy", "cost": 4, "role": "Mass Card Draw"},
                    {"name": "Market", "slug": "market", "cost": 5, "role": "Payload & Extra Buy"}
                ]
            },
            {
                "heading": "Why Extra Buys Win Games",
                "paragraphs": [
                    "A common tragedy in engine construction is generating $16 in coins while holding only 1 Buy. You buy 1 Province and discard the remaining $8.",
                    "Meanwhile, a simpler player with two Silvers and a Gold buys 1 Province as well. Your entire intricate engine accomplished nothing more than their basic turn.",
                    "True engine superiority comes from '+Buy'. Cards like Festival, Market, or Bridge allow you to buy 2 or 3 Provinces per turn in the endgame, ending the match before opponents can react."
                ]
            }
        ],
        "combo_cta": {
            "title": "The Classic Village-Smithy Engine Combo",
            "description": "Village + Smithy is the foundational draw loop of Dominion. To transform this simple cycle into a game-winning double-Province powerhouse, add these 3 companion kingdom cards:",
            "core_cards": [
                {"name": "Village", "slug": "village"},
                {"name": "Smithy", "slug": "smithy"}
            ],
            "companions": [
                {
                    "name": "Festival",
                    "slug": "festival",
                    "cost": 5,
                    "reason": "Actions + Buy: Provides both +2 Actions and the critical +1 Buy without needing copper or gold."
                },
                {
                    "name": "Remodel",
                    "slug": "remodel",
                    "cost": 4,
                    "reason": "Payload Conversion: Upgrades drained Silvers and $5 Actions directly into Provinces in the late game."
                },
                {
                    "name": "Laboratory",
                    "slug": "laboratory",
                    "cost": 5,
                    "reason": "Pure Fluidity: +2 Cards, +1 Action cantrip that keeps the draw chain flowing without action strain."
                }
            ],
            "generator_query": "village,smithy,festival,remodel,laboratory"
        }
    },
    "big-money-vs-engine": {
        "slug": "big-money-vs-engine",
        "title": "Big Money vs. Engine: When to Pivot and When to Sprint",
        "subtitle": "How to recognize boards where building an engine is an elaborate trap, calculate the Smithy-Money benchmark, and know when to green.",
        "category": "Strategy & Mechanics",
        "read_time": "6 min read",
        "hero_card": {
            "name": "Gold",
            "slug": "gold",
            "cost": 6,
            "set_name": "Base"
        },
        "summary": "Every aspiring Dominion player falls in love with complex action chains. But on kingdoms lacking efficient trashing, extra Buys, or reliable villages, pure Big Money will crush an unfinished engine in 14 turns flat.",
        "takeaways": [
            "The Smithy-Money Benchmark: 1 Smithy + pure Silver/Gold reliably buys 4 Provinces by Turn 14.",
            "Board Evaluation Rubric: If a kingdom lacks strong trashing OR lacks +Buy, engines usually lose to streamlined treasure strategies.",
            "The Greening Pivot: In Big Money, buy your first Province at $8 regardless of what turn it is; do not get greedy for a 4th Gold.",
            "Duchy Threshold: When 4 to 5 Provinces remain, pivot immediately into purchasing Duchies to secure the points lead."
        ],
        "sections": [
            {
                "heading": "The Smithy-Money Benchmark",
                "paragraphs": [
                    "In competitive Dominion theory, 'Smithy-Big Money' is the fundamental speed test. The strategy is almost brainless: buy 1 Smithy on Turn 1 or 2, buy Silver whenever you have $3–$5, buy Gold at $6–$7, and buy Province at $8+.",
                    "Despite its simplicity, this deck achieves 4 Provinces between Turns 13 and 15 on average. If your proposed engine cannot buy 4 or more Provinces before Turn 14, your engine is mathematically inferior to buying basic treasures."
                ]
            },
            {
                "heading": "The 3 Pillars of an Engine Kingdom",
                "paragraphs": [
                    "Before attempting to build an engine, examine the kingdom for three mandatory pillars:",
                    "1. Trashing: Is there a way to eliminate at least 5 starting cards? If no, an engine will choke on green and dead Coppers.",
                    "2. Village Effect: Is there a +2 Action card? If no, every action you buy competes for a single action slot.",
                    "3. Plus Buy: Is there a way to purchase multiple cards per turn? If no, you can never outscore a money player who buys 1 Province every turn."
                ],
                "cards": [
                    {"name": "Gold", "slug": "gold", "cost": 6, "role": "Economy Engine"},
                    {"name": "Silver", "slug": "silver", "cost": 3, "role": "Baseline Fuel"},
                    {"name": "Council Room", "slug": "council-room", "cost": 5, "role": "Mass Draw & Buy"}
                ]
            },
            {
                "heading": "The Endgame Sprint: Duchies & Pile-Outs",
                "paragraphs": [
                    "Big Money wins by sprinting to the finish line before complex decks come online. Once the Province pile drops to 4, every turn spent buying Gold is wasted.",
                    "Switching to Duchies (and even Estates when sitting on $2) creates an insurmountable points deficit that an opponent with an elaborate 25-card engine cannot bridge in time."
                ]
            }
        ],
        "combo_cta": {
            "title": "The Classic Big Money Velocity Combo",
            "description": "Smithy paired with Gold represents pure raw velocity. To test or counter this foundational strategy, pair it with these 3 companion kingdom cards:",
            "core_cards": [
                {"name": "Smithy", "slug": "smithy"},
                {"name": "Gold", "slug": "gold"}
            ],
            "companions": [
                {
                    "name": "Militia",
                    "slug": "militia",
                    "cost": 4,
                    "reason": "Choke Advantage: Money decks thrive on 5-card hands; Militia cuts engine builders down to 3 cards before they can combo."
                },
                {
                    "name": "Witch",
                    "slug": "witch",
                    "cost": 5,
                    "reason": "Curse Pressure: Clogging an opponent's deck with Curses shuts down engine consistency permanently."
                },
                {
                    "name": "Council Room",
                    "slug": "council-room",
                    "cost": 5,
                    "reason": "Alternative Draw: Gives +4 Cards and +1 Buy, allowing money decks to buy a Province and a Duchy on the same turn."
                }
            ],
            "generator_query": "smithy,gold,militia,witch,council-room"
        }
    },
    "1e-vs-2e-evolution": {
        "slug": "1e-vs-2e-evolution",
        "title": "1st Edition vs. 2nd Edition: The Evolution of Donald X. Card Design",
        "subtitle": "Why Feast, Woodcutter, Chancellor, and Spy were retired, and the modern design philosophy that replaced them.",
        "category": "Rules & History",
        "read_time": "8 min read",
        "hero_card": {
            "name": "Poacher",
            "slug": "poacher",
            "cost": 4,
            "set_name": "Base"
        },
        "summary": "In 2016, Donald X. Vaccarino released Second Editions of the Base game and Intrigue, cutting 6 cards from each set. Analyzing why these cards were removed reveals the modern core of Dominion design philosophy: active decision-making over passive dead weight.",
        "takeaways": [
            "Passive terminal cards (Woodcutter, Chancellor) were replaced by dynamic cycling cantrips (Merchant, Harbinger).",
            "One-shot sacrifice cards like Feast ($4) were replaced by reusable engines like Artisan ($6).",
            "Interactive attacks shifted from tedious micro-management (Spy) to decisive deck disruption (Bandit, Poacher).",
            "Second Edition cards drastically reduce dead turns by providing immediate velocity upon purchase."
        ],
        "sections": [
            {
                "heading": "The Death of Woodcutter & Chancellor",
                "paragraphs": [
                    "In 1st Edition Base, Woodcutter ($3) provided +1 Buy and +$2, but zero card draw. It was almost universally ignored because playing it consumed your only Action without advancing your hand.",
                    "Similarly, Chancellor ($3) offered +$2 and the option to discard your deck. Mathematically, discarding your deck was almost always either unnecessary or active self-sabotage.",
                    "Donald X. replaced these with Merchant (+1 Card, +1 Action, +$1 on first Silver) and Harbinger (+1 Card, +1 Action, topdeck from discard). Notice the modern design pattern: both are non-terminal cantrips that never clog your hand."
                ]
            },
            {
                "heading": "From Feast to Artisan: Reusable Value",
                "paragraphs": [
                    "Feast cost $4, required you to trash it, and gained a card costing up to $5. Essentially, you spent $4 and an Action on Turn 3 to gain a $5 card on Turn 4.",
                    "This single-use sacrifice created tempo loss. Second Edition introduced Artisan ($6): gain a card costing up to $5 into your hand, and topdeck a card. Artisan generates repeatable, targeted value turn after turn without destroying itself."
                ],
                "cards": [
                    {"name": "Merchant", "slug": "merchant", "cost": 3, "role": "Modern Cantrip"},
                    {"name": "Harbinger", "slug": "harbinger", "cost": 3, "role": "Topdeck Control"},
                    {"name": "Artisan", "slug": "artisan", "cost": 6, "role": "Reusable Gainer"}
                ]
            },
            {
                "heading": "Why Spy Was Replaced by Bandit",
                "paragraphs": [
                    "Spy (+1 Card, +1 Action, reveal top card of each player's deck and decide whether to discard it) was cut for two reasons: slow gameplay and negligible impact.",
                    "In a 4-player game, resolving Spy took 30 to 45 seconds of tedious questions ('Do you want to keep that Copper?'). Yet the game state barely changed.",
                    "Bandit ($5) replaced it: immediately gain a Gold, and trash an opponent's revealed Silver or Gold. Bandit is fast to resolve, dramatically affects the economy, and accelerates the game."
                ]
            }
        ],
        "combo_cta": {
            "title": "The Modern 2nd Edition Synergy Combo",
            "description": "Merchant and Harbinger exemplify the clean non-terminal cantrip philosophy of 2nd Edition. To build a modern high-cycling deck, pair them with these 3 companion cards:",
            "core_cards": [
                {"name": "Merchant", "slug": "merchant"},
                {"name": "Harbinger", "slug": "harbinger"}
            ],
            "companions": [
                {
                    "name": "Poacher",
                    "slug": "poacher",
                    "cost": 4,
                    "reason": "Cycling Pressure: +1 Card, +1 Action, +$1 that scales with empty supply piles, penalizing sloppy play."
                },
                {
                    "name": "Artisan",
                    "slug": "artisan",
                    "cost": 6,
                    "reason": "Direct-to-Hand Gainer: Combines with Harbinger to ensure high-cost cards are drawn immediately."
                },
                {
                    "name": "Bandit",
                    "slug": "bandit",
                    "cost": 5,
                    "reason": "Economic Acceleration: Injects free Golds into your deck while destroying opponent treasures."
                }
            ],
            "generator_query": "merchant,harbinger,poacher,artisan,bandit"
        }
    },
    "landscapes-and-alternate-scoring": {
        "slug": "landscapes-and-alternate-scoring",
        "title": "Landscapes & Alternate Scoring: Mastering Events, Landmarks, Projects & Ways",
        "subtitle": "How horizontal supply mechanics transform Dominion from a Province race into an asymmetric points puzzle.",
        "category": "Advanced Theory",
        "read_time": "7 min read",
        "hero_card": {
            "name": "Advance",
            "slug": "advance",
            "cost": 0,
            "set_name": "Adventures"
        },
        "summary": "Landscapes exist outside the 10 kingdom card piles. From Events that offer one-off effects to Landmarks that reward bizarre deck compositions, mastering landscapes is what separates intermediate players from championship competitors.",
        "takeaways": [
            "Events bypass deck dilution: Buying an Event gives you an effect immediately without adding a card to your deck.",
            "Landmarks change the victory condition: Cards like Wolf Den and Tomb reward strategies that ignore Provinces entirely.",
            "Projects are permanent engine buffs: Investing early in Projects pays compounding dividends across 10+ turns.",
            "Ways turn terminal dead actions into universal draw or silver generators on demand."
        ],
        "sections": [
            {
                "heading": "Events: Immediate Velocity Without Deck Bloat",
                "paragraphs": [
                    "The fundamental constraint of Dominion is that buying cards dilutes your draw pile. Events shatter this rule. When you purchase an Event like Advance, Bonfire, or Dominate, you pay the cost and resolve the effect immediately.",
                    "A player using Bonfire to trash 2 Action cards cleans their deck instantly without waiting for a trasher to cycle through their deck. Understanding when to buy Events over physical cards is the key to high-tempo play."
                ]
            },
            {
                "heading": "Landmarks: Asymmetric Victory Points",
                "paragraphs": [
                    "Standard Dominion is a race to 4 or 5 Provinces. Landmarks fundamentally rewrite that rulebook.",
                    "For example, 'Tomb' awards 1 VP every time you trash a card. Suddenly, cards like Forager, Remodel, and Rats generate 10 to 20 victory points in pure trashing actions, completely invalidating an opponent trying to buy Provinces.",
                    "Evaluating whether a Landmark outpaces standard greening is mandatory before making your opening Turn 1 buy."
                ],
                "cards": [
                    {"name": "Advance", "slug": "advance", "cost": 0, "role": "Action Elevation"},
                    {"name": "Bonfire", "slug": "bonfire", "cost": 3, "role": "Instant Trashing"},
                    {"name": "Dominate", "slug": "dominate", "cost": 14, "role": "Mass Victory"}
                ]
            },
            {
                "heading": "Ways: Overcoming Terminal Collision",
                "paragraphs": [
                    "Introduced in Menagerie, Ways allow players to treat any Action card as an alternative action. If 'Way of the Ox' is in play, any Action card in your hand can be played for +2 Actions.",
                    "This eliminates terminal collision: an extra Smithy in hand is no longer a dead draw—it can be converted into the 2 Actions required to play your next card."
                ]
            }
        ],
        "combo_cta": {
            "title": "The Landscape Synergy Combo",
            "description": "Using non-supply mechanics alongside flexible Action cards unlocks asymmetric victory points. To test these interactions, pair Advance with these 3 companion kingdom cards:",
            "core_cards": [
                {"name": "Advance", "slug": "advance"},
                {"name": "Market", "slug": "market"}
            ],
            "companions": [
                {
                    "name": "Festival",
                    "slug": "festival",
                    "cost": 5,
                    "reason": "Double Action Fuel: Provides the surplus actions and +$2 needed to purchase high-cost Events."
                },
                {
                    "name": "Sentry",
                    "slug": "sentry",
                    "cost": 5,
                    "reason": "Topdeck Filter: Ensures you always reveal Action cards suitable for landscape transformations."
                },
                {
                    "name": "Artisan",
                    "slug": "artisan",
                    "cost": 6,
                    "reason": "Targeted Gainer: Gains specific Action cards into hand to feed immediately into Event triggers."
                }
            ],
            "generator_query": "advance,market,festival,sentry,artisan"
        }
    },
    "attack-and-defense-dynamics": {
        "slug": "attack-and-defense-dynamics",
        "title": "Attack & Defense Dynamics: Hand Size Chokes, Curses & Junking Denial",
        "subtitle": "How to calculate the net swing of attack cards, neutralize Witch and Militia, and weaponize junking denial.",
        "category": "Strategy & Mechanics",
        "read_time": "6 min read",
        "hero_card": {
            "name": "Witch",
            "slug": "witch",
            "cost": 5,
            "set_name": "Base"
        },
        "summary": "Attack cards in Dominion do not just slow your opponent down—they create asymmetric mathematical swings in purchasing power. Here is how to quantify attack value, decide when Moat is worth buying, and counter junking attacks.",
        "takeaways": [
            "Witch creates a 2-point VP swing and a permanent dead card in the opponent's deck for every Curse distributed.",
            "Hand Choke Attacks (Militia, Goons) reduce an opponent's average purchasing power from $7.50 to under $4.20.",
            "Reaction traps: Moat ($2) is often a trap unless drawn consistently; aggressive trashing is usually a better counter to Curses.",
            "Attack Denial: In a Witch game, rushing to drain the 10 Curses yourself before your opponent can is the primary objective."
        ],
        "sections": [
            {
                "heading": "Quantifying the Curse Swing",
                "paragraphs": [
                    "Witch is widely recognized as the single strongest 5-cost card in the Base game. To understand why, calculate the net swing per play:",
                    "You draw 2 cards and give every opponent a Curse. That Curse represents -1 Victory Point and a completely useless card that clogs their deck forever.",
                    "If you distribute 5 Curses while your opponent distributes 0, you have created a 10-point victory deficit and injected 5 turns of stalled hands into their engine."
                ]
            },
            {
                "heading": "Hand-Size Reduction: The Militia Math",
                "paragraphs": [
                    "Militia forces opponents down to 3 cards in hand. In standard probabilities, a 5-card hand draws $6+ with high frequency.",
                    "A 3-card hand, however, produces an average of $3 to $4. By playing Militia, you systematically prevent opponents from ever reaching the $8 threshold required to purchase Provinces or high-cost engines."
                ],
                "cards": [
                    {"name": "Witch", "slug": "witch", "cost": 5, "role": "Curse Delivery"},
                    {"name": "Militia", "slug": "militia", "cost": 4, "role": "Hand Size Choke"},
                    {"name": "Moat", "slug": "moat", "cost": 2, "role": "Reaction Shield"}
                ]
            },
            {
                "heading": "Why Moat Is Often a Trap",
                "paragraphs": [
                    "Novice players see Witch on the board and immediately buy two Moats. This is almost always a losing move.",
                    "Moat is a terminal action (+2 Cards) that only protects you if it happens to be sitting in your 5-card hand when the attack occurs. In an untrashed deck, that probability is less than 40%.",
                    "A far superior defense is aggressive trashing (Chapel, Sentry): instead of hoping to block the Curse, simply trash the Curses as fast as they arrive while building a superior economy."
                ]
            }
        ],
        "combo_cta": {
            "title": "The Attack & Defense Pressure Combo",
            "description": "Combining Witch with Militia exerts dual-axis pressure: clogging the opponent's deck with Curses while choking their hand down to 3 cards. To build the ultimate control kingdom, add these 3 companion cards:",
            "core_cards": [
                {"name": "Witch", "slug": "witch"},
                {"name": "Militia", "slug": "militia"}
            ],
            "companions": [
                {
                    "name": "Chapel",
                    "slug": "chapel",
                    "cost": 2,
                    "reason": "Counter-Trashing: Purges incoming Curses while keeping your own deck thin and lethal."
                },
                {
                    "name": "Village",
                    "slug": "village",
                    "cost": 3,
                    "reason": "Action Sustainer: Allows you to play both Witch and Militia in the same turn without terminal collision."
                },
                {
                    "name": "Council Room",
                    "slug": "council-room",
                    "cost": 5,
                    "reason": "Hand Refuel: Draws 4 cards to maintain momentum even if an opponent attacks you back."
                }
            ],
            "generator_query": "witch,militia,chapel,village,council-room"
        }
    },

"7-synergies-with-workshop": {
        "slug": "7-synergies-with-workshop",
        "title": "7 Synergies with Workshop: High-Dimensional Gaining Engines",
        "subtitle": "How semantic vector embeddings reveal the closest mechanical and strategic relatives to Dominion's premiere 4-cost gainer.",
        "category": "Synergies & Top Lists",
        "read_time": "7 min read",
        "hero_card": {
            "name": "Workshop",
            "slug": "workshop",
            "cost": 3,
            "set_name": "Base"
        },
        "summary": "Workshop is the archetype-defining gainer of Dominion: a modest $3 terminal action that bypasses coin totals to directly place cards costing up to $4 into your discard pile. High-dimensional vector analysis across all 500+ kingdom cards isolates the exact 7 cards that cluster closest in mechanical intent, tempo curve, and pile-draining power.",
        "takeaways": [
            "Gaining vs Buying: Workshop ignores copper totals, allowing you to flood your deck with key $4 cards without ever generating cash in hand.",
            "Vector embedding nearest neighbor Ironworks ($4) directly solves Workshop's terminal action limitation by refunding +1 Action whenever gaining Action cards.",
            "Top-deck gainers like Armory and Artisan trade the discard pile for immediate next-turn access, dramatically increasing engine ramp speed.",
            "The Workshop-Gardens rush is one of the oldest clock strategies in Dominion, aiming to empty 3 supply piles before big money engines achieve consistency."
        ],
        "sections": [
            {
                "heading": "1. Ironworks ($4): The Fluid Non-Terminal Upgrade",
                "paragraphs": [
                    "Ranking as the #1 closest embedding neighbor to Workshop, Ironworks takes the 'Gain a card costing up to $4' core mechanic and layers on conditional tempo refunds.",
                    "While Workshop is strictly terminal (consuming your sole Action), Ironworks gives +1 Action when gaining an Action card, +$1 when gaining a Treasure, and +1 Card when gaining a Victory card. When building a mid-game engine, chaining multiple Ironworks together lets you grab an entire army of Villages or Cantrips in a single turn without ever stalling out."
                ],
                "cards": [
                    {"name": "Ironworks", "slug": "ironworks", "cost": 4, "role": "Non-Terminal Action Gainer"}
                ]
            },
            {
                "heading": "2. Artisan ($6): The Heavyweight Top-Deck Engine",
                "paragraphs": [
                    "Where Workshop costs $3 and gains cards to the discard pile, Artisan occupies the heavyweight $6 slot. It gains a card costing up to $5 directly into your hand, then top-decks a card from hand.",
                    "In vector space, Artisan mirrors Workshop's ability to manufacture key engine pieces out of thin air, but elevates it to the crucial $5 cost bracket (securing Witch, Market, or Laboratory) while solving the immediate tempo lag by putting the gained card directly in play."
                ],
                "cards": [
                    {"name": "Artisan", "slug": "artisan", "cost": 6, "role": "Direct-to-Hand $5 Gainer"}
                ]
            },
            {
                "heading": "3. Devil's Workshop ($4): The Escalating Night Phase Harvest",
                "paragraphs": [
                    "Devil's Workshop lives in the Night phase, meaning it never consumes an Action slot. Its modal payoff directly scales with how active your gaining engine was during the day.",
                    "If you gained 1 card earlier this turn (for example, with a standard Workshop or Buy), Devil's Workshop gains another card costing up to $4. If you gained 2 or more cards, it grants an Imp—a devastating +2 Cards, +1 Action cantrip. Pairing Workshop with Devil's Workshop turns simple 4-cost gains into relentless Imp spam."
                ],
                "cards": [
                    {"name": "Devil's Workshop", "slug": "devils-workshop", "cost": 4, "role": "Action-Free Night Gainer"}
                ]
            },
            {
                "heading": "4. Armory ($4): Top-Deck Staging for Zero Shuffle Lag",
                "paragraphs": [
                    "Armory matches Workshop's exact gaining threshold: 'Gain a card costing up to $4 Coins'. However, instead of exiling the newly gained card to the bottom of your discard pile, Armory places it directly on top of your deck.",
                    "This guarantees you draw that Silver, Village, or Militia in your very next hand. When timing is critical—such as setting up a Village-Smithy turn on Turn 3 or 4—Armory completely removes the variance of card cycling."
                ],
                "cards": [
                    {"name": "Armory", "slug": "armory", "cost": 4, "role": "Top-Deck Staging Gainer"}
                ]
            },
            {
                "heading": "5. Carpenter ($4): The Adaptive Modal Pivot",
                "paragraphs": [
                    "Carpenter provides a dual personality that vector embeddings cluster tightly with Workshop's pile-pressure profile. Early in the game while no piles are empty, Carpenter gives +1 Action and gains a card costing up to $4.",
                    "Once any supply pile empties (often accelerated by your own early Workshop picks), Carpenter pivots into a Remodel: trashing a junk card from hand to gain a card costing up to $2 more. It solves Workshop's biggest late-game flaw: dead draw clutter once $4 cards are no longer needed."
                ],
                "cards": [
                    {"name": "Carpenter", "slug": "carpenter", "cost": 4, "role": "Action Refund & Late-Game Trash-Upgrade"}
                ]
            },
            {
                "heading": "6. Craftsman ($3): Low-Cost Heavy Lifting with Debt",
                "paragraphs": [
                    "Costing $3 just like Workshop, Craftsman achieves immediate access to the elite $5 cost tier by taking on +2 Debt upon play.",
                    "In kingdoms where reaching key $5 cards on Turn 2 or Turn 3 is paramount, Craftsman acts as an accelerated Workshop. It bypasses early coin limitations, grabs the pivotal card immediately, and lets you pay off the 2 Debt with passive economy later."
                ],
                "cards": [
                    {"name": "Craftsman", "slug": "craftsman", "cost": 3, "role": "Early $5 Debt Surge"}
                ]
            },
            {
                "heading": "7. Wheelwright ($5): Discard-Driven Action Velocity",
                "paragraphs": [
                    "Wheelwright costs $5 and provides +1 Card, +1 Action cantrip reliability alongside an optional discard-to-gain trigger.",
                    "By discarding an unwanted card from hand (such as an Estate or redundant Copper), Wheelwright allows you to gain an Action card costing as much or less. It preserves your hand size while maintaining the rapid card acquisition tempo that Workshop pioneered."
                ],
                "cards": [
                    {"name": "Wheelwright", "slug": "wheelwright", "cost": 5, "role": "Cantrip Filter & Selective Gainer"}
                ]
            }
        ],
        "tactical_hook": {
            "title": "Tactical Pilot Briefing: The 3-Pile Clock Calculation",
            "summary": "Workshop and its embedding neighbors are not just economy tools—they control the game timer. When paired with alternate victory cards like Gardens, aggressive gaining allows you to exhaust 3 kingdom piles by Turn 10 to 12. Always monitor opponent deck sizes and end the match before traditional engine decks hit their Gold and Province stride."
        },
        "combo_cta": {
            "title": "The Infinite Workshop Swarm",
            "description": "Pairing Workshop with Ironworks and Armory creates an autonomous gaining machine that drains $4 action piles in rapid succession. Test this gaining engine in the Kingdom Generator:",
            "core_cards": [
                {"name": "Workshop", "slug": "workshop"},
                {"name": "Ironworks", "slug": "ironworks"}
            ],
            "companions": [
                {
                    "name": "Armory",
                    "slug": "armory",
                    "cost": 4,
                    "reason": "Immediate Top-Decking: Ensures gained cards skip the discard pile and hit play on the next turn."
                },
                {
                    "name": "Carpenter",
                    "slug": "carpenter",
                    "cost": 4,
                    "reason": "Pile Drain Adaptation: Gives +1 Action early, then converts cheap cards into $6 bombs once piles empty."
                },
                {
                    "name": "Gardens",
                    "slug": "gardens",
                    "cost": 4,
                    "reason": "Victory Scaler: Converts massive deck thickness into an unassailable point total."
                }
            ],
            "generator_query": "workshop,ironworks,armory,carpenter,gardens"
        }
    },

    "7-action-enablers-with-village": {
        "slug": "7-action-enablers-with-village",
        "title": "7 Action Enablers with Village: The Action Multiplying Frontier",
        "subtitle": "Analyzing the closest mathematical and functional relatives to Dominion's quintessential +2 Actions cantrip.",
        "category": "Synergies & Top Lists",
        "read_time": "7 min read",
        "hero_card": {
            "name": "Village",
            "slug": "village",
            "cost": 3,
            "set_name": "Base"
        },
        "summary": "Every engine in Dominion lives and dies on Action economy. Village provides the canonical baseline: +1 Card, +2 Actions for $3. High-dimensional vector clustering identifies the 7 cards whose mechanical profiles align most intimately with Village, illustrating how designers evolved action generation across different expansions.",
        "takeaways": [
            "The Action Surplus Rule: You need an average of 1.5 Village effects for every terminal draw or attack card to prevent terminal action collision.",
            "Worker's Village ($4) introduces +1 Buy, converting pure action velocity into multi-province victory turns.",
            "Fishing Village ($3) represents Duration efficiency: carrying actions and coin into the subsequent turn to guarantee uninterrupted flow.",
            "Border Village ($6) eliminates the opportunity cost of buying actions by granting a free card costing less upon gain."
        ],
        "sections": [
            {
                "heading": "1. Worker's Village ($4): The Engine Architect's Holy Grail",
                "paragraphs": [
                    "Clustering as the #1 closest embedding neighbor to Village, Worker's Village provides +1 Card, +2 Actions, and +1 Buy.",
                    "In high-performance engines, drawing your entire deck is meaningless if you are capped at a single Buy. Worker's Village provides the identical action output of standard Village while naturally layering on the extra Buy needed to acquire multiple Provinces on mega-turns."
                ],
                "cards": [
                    {"name": "Worker's Village", "slug": "workers-village", "cost": 4, "role": "Action + Buy Engine Keystone"}
                ]
            },
            {
                "heading": "2. Fishing Village ($3): Two-Turn Continuity & Economy",
                "paragraphs": [
                    "Fishing Village costs $3 and introduces the Duration mechanic: giving +2 Actions and +$1 immediately, and +1 Action and +$1 at the start of your next turn.",
                    "Because it carries actions forward, Fishing Village guarantees that you begin your next turn with 2 Actions before playing a single card from hand, virtually immunizing your engine against starting terminal brick hands."
                ],
                "cards": [
                    {"name": "Fishing Village", "slug": "fishing-village", "cost": 3, "role": "Duration Action Bridge"}
                ]
            },
            {
                "heading": "3. Snowy Village ($3): The Mega-Action Sprint with a Hard Ceiling",
                "paragraphs": [
                    "Snowy Village delivers an astronomical stat line for $3: +1 Card, +4 Actions, and +1 Buy. However, it imposes a strict condition: ignore any further +Actions you get this turn.",
                    "Vector embeddings place Snowy Village close to standard Village because it solves catastrophic action deficits in a single stroke, making it ideal as the final action in hands loaded with heavy terminal cards like Smithy or Witch."
                ],
                "cards": [
                    {"name": "Snowy Village", "slug": "snowy-village", "cost": 3, "role": "Terminal Action Explosion"}
                ]
            },
            {
                "heading": "4. Rustic Village ($4): Sun Token Synergy and Hand Cycling",
                "paragraphs": [
                    "Rustic Village provides +1 Card, +2 Actions, and +1 Sun Token, along with the ability to discard 2 cards to draw another.",
                    "It functions as an agile Village variant, providing the crucial +2 Actions while smoothing out clumsy draws by turning dead Coppers or Victory cards into fresh draws."
                ],
                "cards": [
                    {"name": "Rustic Village", "slug": "rustic-village", "cost": 4, "role": "Action & Sift Cantrip"}
                ]
            },
            {
                "heading": "5. Border Village ($6): Zero Opportunity Cost Acceleration",
                "paragraphs": [
                    "Border Village gives the classic +1 Card, +2 Actions, but costs $6. Its vector signature is unique because of its on-gain trigger: 'When you gain this, gain a card costing less than this'.",
                    "Gaining Border Village effectively nets you a free $5 card (such as a Witch, Laboratory, or Bandit). It completely eliminates the dilemma between drafting action generation and drafting draw power."
                ],
                "cards": [
                    {"name": "Border Village", "slug": "border-village", "cost": 6, "role": "Two-for-One Action Pivot"}
                ]
            },
            {
                "heading": "6. Harbor Village ($4): Conditional Coin Multiplier",
                "paragraphs": [
                    "Harbor Village gives +1 Card, +2 Actions, plus a conditional financial bonus: if the next Action you play gives you coin, Harbor Village gives you +$1 as well.",
                    "When paired with action cards that produce income (like Market, Festival, or Militia), Harbor Village accelerates your purchasing power while maintaining the action chain."
                ],
                "cards": [
                    {"name": "Harbor Village", "slug": "harbor-village", "cost": 4, "role": "Action & Income Synergist"}
                ]
            },
            {
                "heading": "7. Bustling Village ($5): The Settlers Reunion",
                "paragraphs": [
                    "Bustling Village delivers +1 Card, +3 Actions, and lets you retrieve a Settlers from your discard pile directly into your hand.",
                    "Generating a net surplus of +2 Actions per play, Bustling Village is a dream fuel source for complex draw engines that rely on multiple terminal draw cards."
                ],
                "cards": [
                    {"name": "Bustling Village", "slug": "bustling-village", "cost": 5, "role": "+3 Actions Surplus Engine"}
                ]
            }
        ],
        "tactical_hook": {
            "title": "Tactical Pilot Briefing: Avoiding the Terminal Collision Trap",
            "summary": "Never draft heavy terminal draw cards (Smithy, Council Room, Torturer) until your deck has at least one Village or Duration action generator in active circulation. A hand with three Smithies and zero Villages results in two wasted actions and a stalled engine turn."
        },
        "combo_cta": {
            "title": "The Golden Village-Smithy Engine",
            "description": "Village paired with Smithy is the archetype that birthed modern deckbuilding. To push this engine into full multi-Province overdrive, add these 3 companion kingdom cards:",
            "core_cards": [
                {"name": "Village", "slug": "village"},
                {"name": "Smithy", "slug": "smithy"}
            ],
            "companions": [
                {
                    "name": "Worker's Village",
                    "slug": "workers-village",
                    "cost": 4,
                    "reason": "+1 Buy Integrator: Turns massive single-turn card cycling into multiple Province purchases."
                },
                {
                    "name": "Fishing Village",
                    "slug": "fishing-village",
                    "cost": 3,
                    "reason": "Turn-to-Turn Bridge: Insulates your opening draws against terminal bricking."
                },
                {
                    "name": "Market",
                    "slug": "market",
                    "cost": 5,
                    "reason": "Cantrip Economy: Adds buying power and card flow without consuming action space."
                }
            ],
            "generator_query": "village,smithy,workers-village,fishing-village,market"
        }
    }
}
