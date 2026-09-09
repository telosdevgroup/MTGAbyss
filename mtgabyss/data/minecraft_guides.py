"""
mtgabyss.data.minecraft_guides
------------------------------
Evergreen reference guides and technical primers for Minecraft Java Edition.
Structured sections, key rules of thumb, block/item references, and Schema.org metadata.
No visible front-end published dates.
"""

MINECRAFT_GUIDES = {
    "optimal-ore-generation-mining-levels": {
        "slug": "optimal-ore-generation-mining-levels",
        "title": "Optimal Mining Y-Levels & Ore Distribution in Minecraft 1.21+",
        "subtitle": "Complete triangular distribution charts, deepslate break times, and cave caving vs. branch mining strategies.",
        "category": "Survival & Mining",
        "read_time": "6 min read",
        "author": "AvaScry Technical Team",
        "summary": "Modern Minecraft ore generation uses triangular and uniform distribution spreads rather than uniform flat layers. Understanding exact peak generation altitudes is the single biggest multiplier for diamond, iron, and ancient debris yields.",
        "takeaways": [
            "Diamonds generate with triangular distribution between Y=-144 and Y=16, peaking at Y=-58 (just above bedrock).",
            "Iron peaks at two distinct altitudes: Y=232 in towering mountain peaks, and Y=16 underground.",
            "Gold peaks at Y=-16 in standard biomes, but badlands biomes generate massive gold deposits between Y=32 and Y=256.",
            "Deepslate blocks take double the mining time of regular stone; caving through large cheese caves yields 2.5x more diamonds per hour than branch mining."
        ],
        "sections": [
            {
                "heading": "The Triangular Distribution Shift",
                "paragraphs": [
                    "Prior to the Caves & Cliffs world generation update, ores generated uniformly across predetermined height ranges. In Java 1.18 through 1.21+, Mojang introduced triangular generation.",
                    "In a triangular spread, the probability of finding an ore vein increases linearly towards the center (peak) of its range and falls off at the extremes. Mining at the peak altitude produces dramatically higher yields per block cleared."
                ]
            },
            {
                "heading": "Ore Generation Reference Matrix",
                "paragraphs": [
                    "• Coal: Y=95 to Y=136 (peaks at Y=96). Large exposed veins in hills and mountain biomes; stops generating below Y=0.",
                    "• Copper: Y=-16 to Y=112 (peaks at Y=48). Massive vein generation with granite clusters in dripstone caves.",
                    "• Iron: Dual peak. Mountain peaks (Y=232) offer massive surface veins. Underground iron peaks at Y=16.",
                    "• Lapis Lazuli: Y=-64 to Y=64 (peaks sharply at Y=0).",
                    "• Gold: Standard biomes peak at Y=-16. Badlands biomes generate huge veins from Y=32 up to Y=256.",
                    "• Redstone: Uniform below Y=-32, then increases triangularly down to Y=-64.",
                    "• Diamond: Triangular from Y=16 down to Y=-64. Maximum density is at Y=-58 to Y=-59, just before bedrock fog."
                ]
            },
            {
                "heading": "Deepslate Mining Efficiency: Caving vs. Strip Mining",
                "paragraphs": [
                    "Deepslate has a hardness rating of 3.0 compared to stone's 1.5. A Netherite pickaxe with Efficiency V instamines regular stone under Haste II, but requires 0.25 seconds per deepslate block.",
                    "Because of this 100% time penalty, branch mining at Y=-58 is significantly less resource-efficient than large-scale spelunking. Exploring massive cheese caves with Night Vision and Water Buckets exposes hundreds of square meters of deepslate surface area with zero pickaxe durability expenditure."
                ]
            },
            {
                "heading": "Fortune III vs. Silk Touch Optimization",
                "paragraphs": [
                    "Always prioritize Silk Touch while exploring deep caves to preserve inventory space. A single stack of 64 Diamond Ore saves multiple slots of loose diamonds.",
                    "Process ore blocks back at base with a Fortune III pickaxe over a hopper collection system, yielding an average of 2.2x diamonds per ore block mined."
                ]
            }
        ]
    },
    "villager-trading-hall-mechanics": {
        "slug": "villager-trading-hall-mechanics",
        "title": "Mastering Villager Trading Halls: Workstations, Restocks & Optimal Enchants",
        "subtitle": "How to engineer a permanent trading hall, manipulate trade rolls, lock tier-1 enchants, and manage zombie discounts.",
        "category": "Economy & Automation",
        "read_time": "8 min read",
        "author": "AvaScry Technical Team",
        "summary": "Villagers represent the most powerful renewable economy in Minecraft. With a properly architected trading hall, players obtain infinite diamond armor, tools, food, and every enchanted book without touching an anvil or enchanting table.",
        "takeaways": [
            "Villagers only claim workstations during work hours (ticks 2,000 to 9,000) and require clear pathfinding or eye-level placement.",
            "Breaking and replacing a lectern before trading allows infinite rerolls for Mending, Unbreaking III, or Protection IV.",
            "Trading with a villager even once permanently locks their profession and trade table.",
            "Curing zombie villagers grants stacking price discounts down to 1 Emerald per trade in current versions."
        ],
        "sections": [
            {
                "heading": "The Anatomy of a Trading Cell",
                "paragraphs": [
                    "A secure trading cell prevents iron golem spawning interference, lightning strikes, and wandering behavior. The gold standard footprint is a 1x1 holding pen where the villager stands on a trapdoor or slab directly adjacent to their dedicated workstation.",
                    "Workstations must be isolated so neighbors cannot accidentally bind to them. Keep villagers within a single coordinate column to avoid desyncing their bed schedule."
                ]
            },
            {
                "heading": "Lectern Rerolling for Top Enchantments",
                "paragraphs": [
                    "Librarians offer enchanted books at Novice level. By placing a Lectern, checking the trade, breaking the Lectern with an axe, and placing it down again, you reset their trade inventory within seconds.",
                    "Essential first-round targets: Mending (10-20 emeralds), Unbreaking III (15-30 emeralds), Efficiency V, and Fortune III. Once the desired trade appears, trade once immediately to permanently lock the profession."
                ]
            },
            {
                "heading": "The Master Toolsmith, Armorer & Weaponsmith Trinity",
                "paragraphs": [
                    "Leveling Armorers, Weaponsmiths, and Toolsmiths to Master tier yields a full set of Diamond Armor and Diamond Tools for raw emeralds. Combine this with Fletchers (trading sticks for emeralds) to convert renewable tree farms directly into top-tier endgame gear."
                ]
            },
            {
                "heading": "Work Hours, Restocks & Gossip Mechanics",
                "paragraphs": [
                    "Villagers restock their depleted trades up to twice per day during work hours (daylight ticks 2,000 to 9,000). They do not need direct access to a bed to restock trades, but they must be able to physically touch their assigned workstation.",
                    "Avoid hitting villagers or allowing golems to take damage nearby; negative gossip increases prices and triggers hostility from nearby iron defenders."
                ]
            }
        ]
    },
    "architectural-palette-theory": {
        "slug": "architectural-palette-theory",
        "title": "Architectural Palette Theory: Color Harmonies, Texture & Visual Depth",
        "subtitle": "How professional builders combine gradients, contrast trim, and structural framing to elevate vanilla builds.",
        "category": "Design & Building",
        "read_time": "7 min read",
        "author": "AvaScry Design Team",
        "summary": "Great builds are not defined by scale alone—they are defined by cohesive material palettes, visual weight, and deliberate depth. Learn how to combine primary structures, secondary contrast, and micro-texturing.",
        "takeaways": [
            "Follow the 60-30-10 palette rule: 60% dominant base material, 30% structural framing/contrast, 10% accent highlights.",
            "Use gradients (e.g. Deepslate -> Basalt -> Blackstone -> Gray Concrete) to simulate natural weathering, soot, and shadow.",
            "Establish depth by pulling pillars and structural beams 1 block forward from wall paneling.",
            "Mix textured blocks of identical value (e.g., Stone, Andesite, Stone Bricks, Cracked Bricks) to eliminate flat surfaces."
        ],
        "sections": [
            {
                "heading": "The 60-30-10 Rule in Block Form",
                "paragraphs": [
                    "Borrowed from interior design, the 60-30-10 rule prevents builds from looking either monochromatic or chaotic:",
                    "- 60% Dominant Foundation: Your wall and surface mass (e.g., Oak Planks, Smooth Sandstone, or Mud Bricks).",
                    "- 30% Secondary Structure: Roof framing, foundation trim, and structural pillars (e.g., Dark Oak Logs, Deepslate Tiles, or Spruce).",
                    "- 10% Accent Energy: Doors, lighting, fence gates, trapdoors, and floral accents (e.g., Lanterns, Copper Grates, Mangrove buttons)."
                ]
            },
            {
                "heading": "Building Vertical Gradients",
                "paragraphs": [
                    "Gradients simulate atmospheric lighting, rising damp, and weathered age. On tall towers or cliff faces, place darker and rougher blocks at the base and blend upwards into smoother, lighter variants.",
                    "A classic dark stone gradient: Bedrock / Deepslate (Y bottom) -> Tuff -> Cobblestone -> Stone -> Andesite -> Light Gray Concrete (Y top). Blend rows with alternating 2-to-1 ratios to make transitions organic rather than rigid stripes."
                ]
            },
            {
                "heading": "Depth, Layering and Negative Space",
                "paragraphs": [
                    "A flat wall always feels artificial. Push window sills back by 1 block, push foundation logs forward by 1 block, and use stairs, slabs, and walls to create shadow lines.",
                    "AvaScry's interactive Builder Palette tool helps you preview harmonious blocks side-by-side before grinding resources in your survival world."
                ]
            }
        ]
    },
    "redstone-logic-essentials": {
        "slug": "redstone-logic-essentials",
        "title": "Redstone Logic Essentials: Clocks, T-Flip-Flops & Signal Control",
        "subtitle": "The foundational circuits that power automated sorting systems, hidden doors, and compact item transportation.",
        "category": "Technical & Redstone",
        "read_time": "9 min read",
        "author": "AvaScry Technical Team",
        "summary": "Redstone is a Turing-complete computing medium within Minecraft. Mastering a handful of fundamental components unlocks virtually every complex contraption, from piston doors to multi-item storage sorters.",
        "takeaways": [
            "Redstone dust signal strength degrades by 1 every block, traveling a maximum of 15 blocks before requiring a repeater.",
            "A Comparator measures container fullness (0-15) and can compare or subtract signals in realtime.",
            "A T-Flip-Flop turns a momentary button pulse into a permanent ON/OFF toggle switch.",
            "Hopper clocks provide lag-friendly, configurable timing cycles for mob farms and smelters."
        ],
        "sections": [
            {
                "heading": "Signal Strength, Ticks and Repeaters",
                "paragraphs": [
                    "Minecraft runs at 20 game ticks per second (1 redstone tick = 2 game ticks = 0.1s). Redstone dust transmits power up to 15 blocks. When the signal drops to 0, it ceases activating mechanisms.",
                    "A Redstone Repeater serves three distinct purposes: boosting signal strength back to 15, introducing precise delays (1 to 4 redstone ticks), and creating diodes (unidirectional flow preventing backpower)."
                ]
            },
            {
                "heading": "Comparators: Reading Container Inventories",
                "paragraphs": [
                    "The Redstone Comparator outputs a signal proportional to the fullness of the container behind it (Chest, Hopper, Dropper, Barrel, or Chiseled Bookshelf).",
                    "The formula: Signal = floor(1 + (Filled Slots Value / Total Slots) * 14). This mathematical rule enables item sorters: when a hopper contains 41 filter items + 1 incoming item, the signal increases from 1 to 2, unlocking the lower hopper."
                ]
            },
            {
                "heading": "Essential Survival Circuits",
                "paragraphs": [
                    "- The Hopper Clock: Two hoppers pointing into each other with a comparator reading one side and a sticky piston mechanism. Change the item count to tune clock speed from 0.8s to several minutes.",
                    "- Piston T-Flip-Flop: A sticky piston pushing a redstone block with a 1-tick pulse drops the block, creating an instantaneous toggle with zero delay.",
                    "- Pulse Extender: Two comparators facing opposite directions loop signal decay, turning a brief stone button click into a 5-second open gate."
                ]
            },
            {
                "heading": "Lag Prevention & Server Health",
                "paragraphs": [
                    "On multiplayer servers, avoid massive redstone dust lines that cause frequent light and block updates. Substitute dropper lines, rail lines, or locked hopper channels to keep tick rates at a steady 20.0 TPS."
                ]
            }
        ]
    }
}
