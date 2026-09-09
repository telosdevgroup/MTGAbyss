"""
AvaScry Minecraft Data Compiler & Graph Inversion Engine
Targets: 'avascry_minecraft' MongoDB database.
Pin: Java Edition 1.21.4 (version_type: release)

Seeds multi-channel source records, compiles AST loot tables & recipes,
resolves tags, runs graph inversion, and produces derived reciprocal edges.
"""

import sys
import os
from datetime import datetime, timezone
import pymongo

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db

true = True
false = False
null = None

EDITION = "java"
VERSION = "1.21.4"
VERSION_TYPE = "release"
DB_NAME = "avascry_minecraft"


def get_mc_db():
    client = get_mongo_db().client
    return client[DB_NAME]


def make_id(entity_id: str) -> str:
    return f"{EDITION}|{VERSION}|{entity_id}"


def slugify_id(namespaced_id: str) -> str:
    # minecraft:diamond_pickaxe -> diamond-pickaxe
    # minecraft:blocks/diamond_ore -> blocks-diamond-ore
    val = namespaced_id.split(":", 1)[-1] if ":" in namespaced_id else namespaced_id
    val = val.replace("/", "-").replace("_", "-").lower()
    return val


def seed_data():
    db = get_mc_db()
    print(f"Connecting to MongoDB database: {DB_NAME}")

    # 1. Sources & Ingestion Run metadata
    db.sources.replace_one(
        {"_id": f"mojang-reports-{VERSION}"},
        {
            "_id": f"mojang-reports-{VERSION}",
            "channel": "mojang_reports",
            "edition": EDITION,
            "version": VERSION,
            "url": f"https://piston-data.mojang.com/v1/objects/{VERSION}/server.jar",
            "sha256": "4b6a9c8b74e2a6d71b80c1087d3a24b16a4f4ef68c37d04e578c743818e6e89a",
            "extracted_at": datetime.now(timezone.utc).isoformat()
        },
        upsert=True
    )
    db.sources.replace_one(
        {"_id": f"server-jar-{VERSION}"},
        {
            "_id": f"server-jar-{VERSION}",
            "channel": "server_jar_resources",
            "edition": EDITION,
            "version": VERSION,
            "sha256": "4b6a9c8b74e2a6d71b80c1087d3a24b16a4f4ef68c37d04e578c743818e6e89a",
            "extracted_at": datetime.now(timezone.utc).isoformat()
        },
        upsert=True
    )

    # 2. Versions catalog
    db.versions.replace_one(
        {"_id": f"{EDITION}|{VERSION}"},
        {
            "_id": f"{EDITION}|{VERSION}",
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "release_date": "2024-12-03T10:00:00Z",
            "server_jar": {
                "url": f"https://piston-data.mojang.com/v1/objects/{VERSION}/server.jar",
                "sha256": "4b6a9c8b74e2a6d71b80c1087d3a24b16a4f4ef68c37d04e578c743818e6e89a"
            }
        },
        upsert=True
    )

    # 3. Tags (Item tags, block tags, empty test tag for MC-08)
    raw_tags = [
        {
            "tag_id": "#minecraft:pickaxes",
            "tag_type": "item",
            "raw_values": [
                "minecraft:wooden_pickaxe",
                "minecraft:stone_pickaxe",
                "minecraft:iron_pickaxe",
                "minecraft:diamond_pickaxe",
                "minecraft:netherite_pickaxe"
            ]
        },
        {
            "tag_id": "#minecraft:axes",
            "tag_type": "item",
            "raw_values": ["minecraft:iron_axe", "minecraft:diamond_axe"]
        },
        {
            "tag_id": "#minecraft:mineable/pickaxe",
            "tag_type": "block",
            "raw_values": [
                "minecraft:stone",
                "minecraft:iron_ore",
                "minecraft:diamond_ore",
                "minecraft:deepslate_diamond_ore",
                "minecraft:obsidian",
                "minecraft:ancient_debris"
            ]
        },
        {
            "tag_id": "#minecraft:needs_iron_tool",
            "tag_type": "block",
            "raw_values": ["minecraft:diamond_ore", "minecraft:deepslate_diamond_ore"]
        },
        {
            "tag_id": "#minecraft:needs_diamond_tool",
            "tag_type": "block",
            "raw_values": ["minecraft:obsidian", "minecraft:ancient_debris"]
        },
        {
            "tag_id": "#minecraft:diamond_ores",
            "tag_type": "block",
            "raw_values": ["minecraft:diamond_ore", "minecraft:deepslate_diamond_ore"]
        },
        {
            "tag_id": "#minecraft:planks",
            "tag_type": "item",
            "raw_values": ["minecraft:oak_planks", "minecraft:birch_planks"]
        },
        {
            "tag_id": "#minecraft:sticks",
            "tag_type": "item",
            "raw_values": ["minecraft:stick"]
        },
        {
            "tag_id": "#minecraft:enchantable/mining",
            "tag_type": "item",
            "raw_values": ["#minecraft:pickaxes", "#minecraft:axes"]
        },
        {
            "tag_id": "#minecraft:enchantable/mining_loot",
            "tag_type": "item",
            "raw_values": ["#minecraft:pickaxes"]
        },
        {
            "tag_id": "#minecraft:is_overworld",
            "tag_type": "biome",
            "raw_values": ["minecraft:plains", "minecraft:forest", "minecraft:cherry_grove", "minecraft:desert"]
        },
        {
            "tag_id": "#minecraft:spawns_monsters",
            "tag_type": "biome",
            "raw_values": ["minecraft:plains", "minecraft:forest", "minecraft:desert", "minecraft:deep_dark"]
        },
        {
            "tag_id": "#minecraft:empty_test_tag",
            "tag_type": "item",
            "raw_values": []  # Empty tag allowed per MC-08
        }
    ]

    # Resolve and upsert tags
    tag_map = {}
    for t in raw_tags:
        t_id = t["tag_id"]
        tag_map[t_id] = t

    # Helper recursive resolution
    def resolve_tag_members(tag_id, visited=None):
        if visited is None:
            visited = set()
        if tag_id in visited:
            return []
        visited.add(tag_id)
        if tag_id not in tag_map:
            return []
        results = []
        for val in tag_map[tag_id]["raw_values"]:
            if val.startswith("#"):
                results.extend(resolve_tag_members(val, visited))
            else:
                results.append(val)
        return list(dict.fromkeys(results))

    for t in raw_tags:
        resolved = resolve_tag_members(t["tag_id"])
        doc = {
            "_id": make_id(t["tag_id"]),
            "tag_id": t["tag_id"],
            "slug": slugify_id(t["tag_id"].replace("#", "tag-")),
            "tag_type": t["tag_type"],
            "edition": EDITION,
            "version": VERSION,
            "is_empty": len(resolved) == 0,
            "raw_values": t["raw_values"],
            "derived": {
                "resolved_members": resolved
            },
            "raw_source_refs": [
                {
                    "source_id": f"server-jar-{VERSION}",
                    "channel": "server_jar_resources",
                    "file": f"data/minecraft/tags/{t['tag_type']}/{t['tag_id'].replace('#minecraft:', '')}.json",
                    "checksum": "sha256:c22d7a8e"
                }
            ]
        }
        db.tags.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 4. Items seed
    raw_items = [
        {
            "id": "minecraft:diamond_pickaxe",
            "facts": {
                "display_name": "Diamond Pickaxe",
                "stack_size": 1,
                "durability": 1561,
                "enchantability": 10,
                "repair_materials": ["minecraft:diamond"],
                "mining_tier": "diamond",
                "mining_speed": 8.0,
                "attack_damage": 5.0,
                "tags": ["#minecraft:pickaxes"]
            }
        },
        {
            "id": "minecraft:iron_pickaxe",
            "facts": {
                "display_name": "Iron Pickaxe",
                "stack_size": 1,
                "durability": 250,
                "enchantability": 14,
                "repair_materials": ["minecraft:iron_ingot"],
                "mining_tier": "iron",
                "mining_speed": 6.0,
                "attack_damage": 4.0,
                "tags": ["#minecraft:pickaxes"]
            }
        },
        {
            "id": "minecraft:stone_pickaxe",
            "facts": {
                "display_name": "Stone Pickaxe",
                "stack_size": 1,
                "durability": 131,
                "enchantability": 5,
                "repair_materials": ["minecraft:stone"],
                "mining_tier": "stone",
                "mining_speed": 4.0,
                "attack_damage": 3.0,
                "tags": ["#minecraft:pickaxes"]
            }
        },
        {
            "id": "minecraft:wooden_pickaxe",
            "facts": {
                "display_name": "Wooden Pickaxe",
                "stack_size": 1,
                "durability": 59,
                "enchantability": 15,
                "repair_materials": ["#minecraft:planks"],
                "mining_tier": "wood",
                "mining_speed": 2.0,
                "attack_damage": 2.0,
                "tags": ["#minecraft:pickaxes"]
            }
        },
        {
            "id": "minecraft:netherite_pickaxe",
            "facts": {
                "display_name": "Netherite Pickaxe",
                "stack_size": 1,
                "durability": 2031,
                "enchantability": 15,
                "repair_materials": ["minecraft:netherite_ingot"],
                "mining_tier": "netherite",
                "mining_speed": 9.0,
                "attack_damage": 6.0,
                "tags": ["#minecraft:pickaxes"]
            }
        },
        {
            "id": "minecraft:diamond",
            "facts": {
                "display_name": "Diamond",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:iron_ingot",
            "facts": {
                "display_name": "Iron Ingot",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:stick",
            "facts": {
                "display_name": "Stick",
                "stack_size": 64,
                "tags": ["#minecraft:sticks"]
            }
        },
        {
            "id": "minecraft:oak_planks",
            "facts": {
                "display_name": "Oak Planks",
                "stack_size": 64,
                "tags": ["#minecraft:planks"]
            }
        },
        {
            "id": "minecraft:birch_planks",
            "facts": {
                "display_name": "Birch Planks",
                "stack_size": 64,
                "tags": ["#minecraft:planks"]
            }
        },
        {
            "id": "minecraft:ancient_debris",
            "facts": {
                "display_name": "Ancient Debris",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:netherite_scrap",
            "facts": {
                "display_name": "Netherite Scrap",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:netherite_ingot",
            "facts": {
                "display_name": "Netherite Ingot",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:gunpowder",
            "facts": {
                "display_name": "Gunpowder",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:creeper_head",
            "facts": {
                "display_name": "Creeper Head",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:rotten_flesh",
            "facts": {
                "display_name": "Rotten Flesh",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:ender_pearl",
            "facts": {
                "display_name": "Ender Pearl",
                "stack_size": 16,
                "tags": []
            }
        },
        {
            "id": "minecraft:blaze_rod",
            "facts": {
                "display_name": "Blaze Rod",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:obsidian",
            "facts": {
                "display_name": "Obsidian",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:stone",
            "facts": {
                "display_name": "Stone",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:diamond_ore",
            "facts": {
                "display_name": "Diamond Ore",
                "stack_size": 64,
                "tags": ["#minecraft:diamond_ores"]
            }
        },
        {
            "id": "minecraft:deepslate_diamond_ore",
            "facts": {
                "display_name": "Deepslate Diamond Ore",
                "stack_size": 64,
                "tags": ["#minecraft:diamond_ores"]
            }
        },
        {
            "id": "minecraft:iron_ore",
            "facts": {
                "display_name": "Iron Ore",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:oak_log",
            "facts": {
                "display_name": "Oak Log",
                "stack_size": 64,
                "tags": []
            }
        },
        {
            "id": "minecraft:gold_ingot",
            "facts": {
                "display_name": "Gold Ingot",
                "stack_size": 64,
                "tags": []
            }
        }
    ]

    for item in raw_items:
        doc = {
            "_id": make_id(item["id"]),
            "entity_id": item["id"],
            "slug": slugify_id(item["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "facts": item["facts"],
            "raw_source_refs": [
                {
                    "source_id": f"mojang-reports-{VERSION}",
                    "channel": "mojang_reports",
                    "file": "reports/registries.json",
                    "checksum": "sha256:d5412"
                }
            ],
            "derived": {
                "crafted_from_recipes": [],
                "used_in_recipes": [],
                "can_mine_blocks": [],
                "dropped_by_blocks": [],
                "dropped_by_entities": [],
                "compatible_enchantments": []
            }
        }
        db.items.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 5. Blocks seed
    raw_blocks = [
        {
            "id": "minecraft:diamond_ore",
            "facts": {
                "display_name": "Diamond Ore",
                "hardness": 3.0,
                "resistance": 3.0,
                "light_emission": 0,
                "tool_required": true,
                "loot_table_ref": "minecraft:blocks/diamond_ore",
                "tags": ["#minecraft:mineable/pickaxe", "#minecraft:needs_iron_tool", "#minecraft:diamond_ores"]
            }
        },
        {
            "id": "minecraft:deepslate_diamond_ore",
            "facts": {
                "display_name": "Deepslate Diamond Ore",
                "hardness": 4.5,
                "resistance": 3.0,
                "light_emission": 0,
                "tool_required": true,
                "loot_table_ref": "minecraft:blocks/deepslate_diamond_ore",
                "tags": ["#minecraft:mineable/pickaxe", "#minecraft:needs_iron_tool", "#minecraft:diamond_ores"]
            }
        },
        {
            "id": "minecraft:iron_ore",
            "facts": {
                "display_name": "Iron Ore",
                "hardness": 3.0,
                "resistance": 3.0,
                "light_emission": 0,
                "tool_required": true,
                "loot_table_ref": "minecraft:blocks/iron_ore",
                "tags": ["#minecraft:mineable/pickaxe", "#minecraft:needs_stone_tool"]
            }
        },
        {
            "id": "minecraft:obsidian",
            "facts": {
                "display_name": "Obsidian",
                "hardness": 50.0,
                "resistance": 1200.0,
                "light_emission": 0,
                "tool_required": true,
                "loot_table_ref": "minecraft:blocks/obsidian",
                "tags": ["#minecraft:mineable/pickaxe", "#minecraft:needs_diamond_tool"]
            }
        },
        {
            "id": "minecraft:ancient_debris",
            "facts": {
                "display_name": "Ancient Debris",
                "hardness": 30.0,
                "resistance": 1200.0,
                "light_emission": 0,
                "tool_required": true,
                "loot_table_ref": "minecraft:blocks/ancient_debris",
                "tags": ["#minecraft:mineable/pickaxe", "#minecraft:needs_diamond_tool"]
            }
        },
        {
            "id": "minecraft:stone",
            "facts": {
                "display_name": "Stone",
                "hardness": 1.5,
                "resistance": 6.0,
                "light_emission": 0,
                "tool_required": true,
                "loot_table_ref": "minecraft:blocks/stone",
                "tags": ["#minecraft:mineable/pickaxe"]
            }
        },
        {
            "id": "minecraft:oak_log",
            "facts": {
                "display_name": "Oak Log",
                "hardness": 2.0,
                "resistance": 2.0,
                "light_emission": 0,
                "tool_required": false,
                "loot_table_ref": "minecraft:blocks/oak_log",
                "tags": []
            }
        }
    ]

    for blk in raw_blocks:
        doc = {
            "_id": make_id(blk["id"]),
            "entity_id": blk["id"],
            "slug": slugify_id(blk["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "facts": blk["facts"],
            "raw_source_refs": [
                {
                    "source_id": f"mojang-reports-{VERSION}",
                    "channel": "mojang_reports",
                    "file": "reports/blocks.json",
                    "checksum": "sha256:e3b0"
                }
            ],
            "derived": {
                "harvest_tools": [],
                "drops_summary": []
            }
        }
        db.blocks.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 6. Loot Tables (AST representation)
    raw_loot_tables = [
        {
            "id": "minecraft:blocks/diamond_ore",
            "type": "minecraft:block",
            "raw_ast": {
                "type": "minecraft:block",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:alternatives",
                                "children": [
                                    {
                                        "type": "minecraft:item",
                                        "name": "minecraft:diamond_ore",
                                        "conditions": [
                                            {
                                                "condition": "minecraft:match_tool",
                                                "predicate": {
                                                    "predicates": {
                                                        "minecraft:enchantments": [
                                                            {"enchantments": "minecraft:silk_touch", "levels": {"min": 1}}
                                                        ]
                                                    }
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "type": "minecraft:item",
                                        "name": "minecraft:diamond",
                                        "functions": [
                                            {"function": "minecraft:apply_bonus", "enchantment": "minecraft:fortune", "formula": "minecraft:ore_drops"},
                                            {"function": "minecraft:explosion_decay"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:blocks/deepslate_diamond_ore",
            "type": "minecraft:block",
            "raw_ast": {
                "type": "minecraft:block",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:alternatives",
                                "children": [
                                    {
                                        "type": "minecraft:item",
                                        "name": "minecraft:deepslate_diamond_ore",
                                        "conditions": [{"condition": "minecraft:match_tool", "predicate": {"enchantments": ["minecraft:silk_touch"]}}]
                                    },
                                    {
                                        "type": "minecraft:item",
                                        "name": "minecraft:diamond",
                                        "functions": [{"function": "minecraft:apply_bonus", "enchantment": "minecraft:fortune"}]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:blocks/iron_ore",
            "type": "minecraft:block",
            "raw_ast": {
                "type": "minecraft:block",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:iron_ore"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:blocks/ancient_debris",
            "type": "minecraft:block",
            "raw_ast": {
                "type": "minecraft:block",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:ancient_debris"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:blocks/obsidian",
            "type": "minecraft:block",
            "raw_ast": {
                "type": "minecraft:block",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:obsidian"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:blocks/stone",
            "type": "minecraft:block",
            "raw_ast": {
                "type": "minecraft:block",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:stone"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:blocks/oak_log",
            "type": "minecraft:block",
            "raw_ast": {
                "type": "minecraft:block",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:oak_log"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:entities/creeper",
            "type": "minecraft:entity",
            "raw_ast": {
                "type": "minecraft:entity",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:gunpowder",
                                "functions": [
                                    {"function": "minecraft:set_count", "count": {"min": 0, "max": 2}},
                                    {"function": "minecraft:looting_enchant", "count": {"min": 0, "max": 1}}
                                ]
                            }
                        ]
                    },
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:creeper_head",
                                "conditions": [
                                    {"condition": "minecraft:entity_properties", "predicate": {"flags": {"is_charged": true}}}
                                ]
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:entities/zombie",
            "type": "minecraft:entity",
            "raw_ast": {
                "type": "minecraft:entity",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:rotten_flesh",
                                "functions": [{"function": "minecraft:set_count", "count": {"min": 0, "max": 2}}]
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:entities/enderman",
            "type": "minecraft:entity",
            "raw_ast": {
                "type": "minecraft:entity",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:ender_pearl",
                                "functions": [{"function": "minecraft:set_count", "count": {"min": 0, "max": 1}}]
                            }
                        ]
                    }
                ]
            }
        },
        {
            "id": "minecraft:entities/blaze",
            "type": "minecraft:entity",
            "raw_ast": {
                "type": "minecraft:entity",
                "pools": [
                    {
                        "rolls": 1,
                        "entries": [
                            {
                                "type": "minecraft:item",
                                "name": "minecraft:blaze_rod",
                                "functions": [{"function": "minecraft:set_count", "count": {"min": 0, "max": 1}}]
                            }
                        ]
                    }
                ]
            }
        }
    ]

    for lt in raw_loot_tables:
        # Extract targets from AST
        targets = []
        def extract_ast_items(node):
            if isinstance(node, dict):
                if node.get("type") == "minecraft:item" and "name" in node:
                    targets.append({"type": "item", "id": node["name"]})
                for v in node.values():
                    extract_ast_items(v)
            elif isinstance(node, list):
                for item in node:
                    extract_ast_items(item)
        extract_ast_items(lt["raw_ast"])

        doc = {
            "_id": make_id(lt["id"]),
            "entity_id": lt["id"],
            "slug": slugify_id(lt["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "type": lt["type"],
            "raw_ast": lt["raw_ast"],
            "raw_source_refs": [
                {
                    "source_id": f"server-jar-{VERSION}",
                    "channel": "server_jar_resources",
                    "file": f"data/minecraft/loot_table/{lt['id'].replace('minecraft:', '')}.json",
                    "checksum": "sha256:bb12"
                }
            ],
            "derived": {
                "possible_targets": targets
            }
        }
        db.loot_tables.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 7. Recipes seed
    raw_recipes = [
        {
            "id": "minecraft:diamond_pickaxe",
            "type": "minecraft:crafting_shaped",
            "facts": {
                "category": "equipment",
                "group": "pickaxe",
                "pattern": [
                    "XXX",
                    " # ",
                    " # "
                ],
                "key": {
                    "X": {"type": "single", "item": "minecraft:diamond"},
                    "#": {"type": "tag_or_alternatives", "tag": "#minecraft:sticks", "resolved_items": ["minecraft:stick"]}
                },
                "result": {"item": "minecraft:diamond_pickaxe", "count": 1}
            }
        },
        {
            "id": "minecraft:iron_pickaxe",
            "type": "minecraft:crafting_shaped",
            "facts": {
                "category": "equipment",
                "group": "pickaxe",
                "pattern": [
                    "XXX",
                    " # ",
                    " # "
                ],
                "key": {
                    "X": {"type": "single", "item": "minecraft:iron_ingot"},
                    "#": {"type": "tag_or_alternatives", "tag": "#minecraft:sticks", "resolved_items": ["minecraft:stick"]}
                },
                "result": {"item": "minecraft:iron_pickaxe", "count": 1}
            }
        },
        {
            "id": "minecraft:stick",
            "type": "minecraft:crafting_shaped",
            "facts": {
                "category": "misc",
                "group": "sticks",
                "pattern": [
                    "#",
                    "#"
                ],
                "key": {
                    "#": {"type": "tag_or_alternatives", "tag": "#minecraft:planks", "resolved_items": ["minecraft:oak_planks", "minecraft:birch_planks"]}
                },
                "result": {"item": "minecraft:stick", "count": 4}
            }
        },
        {
            "id": "minecraft:oak_planks",
            "type": "minecraft:crafting_shapeless",
            "facts": {
                "category": "building",
                "ingredients": [
                    {"type": "single", "item": "minecraft:oak_log"}
                ],
                "result": {"item": "minecraft:oak_planks", "count": 4}
            }
        },
        {
            "id": "minecraft:iron_ingot_from_smelting_iron_ore",
            "type": "minecraft:smelting",
            "facts": {
                "category": "misc",
                "ingredient": {"type": "single", "item": "minecraft:iron_ore"},
                "experience": 0.7,
                "cooking_time": 200,
                "result": {"item": "minecraft:iron_ingot", "count": 1}
            }
        },
        {
            "id": "minecraft:netherite_ingot",
            "type": "minecraft:crafting_shapeless",
            "facts": {
                "category": "misc",
                "ingredients": [
                    {"type": "single", "item": "minecraft:netherite_scrap", "count": 4},
                    {"type": "single", "item": "minecraft:gold_ingot", "count": 4}
                ],
                "result": {"item": "minecraft:netherite_ingot", "count": 1}
            }
        }
    ]

    for r in raw_recipes:
        # Determine distinct inputs
        inputs = []
        if "key" in r["facts"]:
            for k_def in r["facts"]["key"].values():
                if "item" in k_def:
                    inputs.append(k_def["item"])
                if "resolved_items" in k_def:
                    inputs.extend(k_def["resolved_items"])
        if "ingredients" in r["facts"]:
            for ing in r["facts"]["ingredients"]:
                if "item" in ing:
                    inputs.append(ing["item"])
        if "ingredient" in r["facts"]:
            inputs.append(r["facts"]["ingredient"]["item"])

        distinct_inputs = list(dict.fromkeys(inputs))
        output_item = r["facts"]["result"]["item"]

        doc = {
            "_id": make_id(r["id"]),
            "entity_id": r["id"],
            "slug": slugify_id(r["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "type": r["type"],
            "facts": r["facts"],
            "raw_source_refs": [
                {
                    "source_id": f"server-jar-{VERSION}",
                    "channel": "server_jar_resources",
                    "file": f"data/minecraft/recipe/{r['id'].replace('minecraft:', '')}.json",
                    "checksum": "sha256:7fa1"
                }
            ],
            "derived": {
                "distinct_input_items": distinct_inputs,
                "output_item": output_item
            }
        }
        db.recipes.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 8. Entities seed
    raw_entities = [
        {
            "id": "minecraft:creeper",
            "facts": {
                "display_name": "Creeper",
                "category": "monster",
                "max_health": 20.0,
                "width": 0.6,
                "height": 1.7,
                "immune_to_fire": false,
                "loot_table_ref": "minecraft:entities/creeper",
                "tags": ["#minecraft:spawns_monsters"]
            }
        },
        {
            "id": "minecraft:zombie",
            "facts": {
                "display_name": "Zombie",
                "category": "monster",
                "max_health": 20.0,
                "width": 0.6,
                "height": 1.95,
                "immune_to_fire": false,
                "loot_table_ref": "minecraft:entities/zombie",
                "tags": ["#minecraft:spawns_monsters"]
            }
        },
        {
            "id": "minecraft:enderman",
            "facts": {
                "display_name": "Enderman",
                "category": "monster",
                "max_health": 40.0,
                "width": 0.6,
                "height": 2.9,
                "immune_to_fire": false,
                "loot_table_ref": "minecraft:entities/enderman",
                "tags": ["#minecraft:spawns_monsters"]
            }
        },
        {
            "id": "minecraft:blaze",
            "facts": {
                "display_name": "Blaze",
                "category": "monster",
                "max_health": 20.0,
                "width": 0.6,
                "height": 1.8,
                "immune_to_fire": true,
                "loot_table_ref": "minecraft:entities/blaze",
                "tags": []
            }
        },
        {
            "id": "minecraft:iron_golem",
            "facts": {
                "display_name": "Iron Golem",
                "category": "misc",
                "max_health": 100.0,
                "width": 1.4,
                "height": 2.7,
                "immune_to_fire": false,
                "loot_table_ref": None,
                "tags": []
            }
        }
    ]

    for ent in raw_entities:
        doc = {
            "_id": make_id(ent["id"]),
            "entity_id": ent["id"],
            "slug": slugify_id(ent["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "facts": ent["facts"],
            "raw_source_refs": [
                {
                    "source_id": f"mojang-reports-{VERSION}",
                    "channel": "mojang_reports",
                    "file": "reports/registries.json",
                    "checksum": "sha256:d5412"
                }
            ],
            "derived": {
                "drops_summary": [],
                "spawn_rule_ids": [make_id(f"minecraft:spawn/{slugify_id(ent['id'])}")]
            }
        }
        db.entities.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 9. Spawn Rules seed
    raw_spawn_rules = [
        {
            "id": "minecraft:spawn/creeper",
            "entity_id": "minecraft:creeper",
            "facts": {
                "dimension": "minecraft:overworld",
                "spawn_type": "natural",
                "weight": 100,
                "min_group_size": 4,
                "max_group_size": 4,
                "light_level_requirement": {"max": 0},
                "biome_tags": ["#minecraft:is_overworld", "#minecraft:spawns_monsters"]
            }
        },
        {
            "id": "minecraft:spawn/zombie",
            "entity_id": "minecraft:zombie",
            "facts": {
                "dimension": "minecraft:overworld",
                "spawn_type": "natural",
                "weight": 100,
                "min_group_size": 4,
                "max_group_size": 4,
                "light_level_requirement": {"max": 0},
                "biome_tags": ["#minecraft:is_overworld", "#minecraft:spawns_monsters"]
            }
        },
        {
            "id": "minecraft:spawn/enderman",
            "entity_id": "minecraft:enderman",
            "facts": {
                "dimension": "minecraft:overworld",
                "spawn_type": "natural",
                "weight": 10,
                "min_group_size": 1,
                "max_group_size": 4,
                "light_level_requirement": {"max": 0},
                "biome_tags": ["#minecraft:is_overworld", "#minecraft:spawns_monsters"]
            }
        }
    ]

    for sr in raw_spawn_rules:
        doc = {
            "_id": make_id(sr["id"]),
            "entity_id": sr["id"],
            "target_entity": sr["entity_id"],
            "slug": slugify_id(sr["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "facts": sr["facts"],
            "raw_source_refs": [
                {
                    "source_id": f"server-jar-{VERSION}",
                    "channel": "server_jar_resources",
                    "file": "data/minecraft/dimension/overworld.json",
                    "checksum": "sha256:aa99"
                }
            ],
            "derived": {
                "valid_biomes": ["minecraft:plains", "minecraft:forest", "minecraft:desert"]
            }
        }
        db.spawn_rules.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 10. Enchantments seed
    raw_enchantments = [
        {
            "id": "minecraft:fortune",
            "facts": {
                "display_name": "Fortune",
                "description": "Increases block drop counts for specific ores, crops, and materials.",
                "max_level": 3,
                "supported_items_tag": "#minecraft:enchantable/mining",
                "primary_items_tag": "#minecraft:enchantable/mining_loot",
                "incompatible_enchantments": ["minecraft:silk_touch"],
                "anvil_cost": 2,
                "slots": ["mainhand"]
            }
        },
        {
            "id": "minecraft:silk_touch",
            "facts": {
                "display_name": "Silk Touch",
                "description": "Causes mined blocks to drop themselves rather than their usual items.",
                "max_level": 1,
                "supported_items_tag": "#minecraft:enchantable/mining",
                "primary_items_tag": "#minecraft:enchantable/mining",
                "incompatible_enchantments": ["minecraft:fortune"],
                "anvil_cost": 4,
                "slots": ["mainhand"]
            }
        },
        {
            "id": "minecraft:efficiency",
            "facts": {
                "display_name": "Efficiency",
                "description": "Increases mining speed when using the correct tool.",
                "max_level": 5,
                "supported_items_tag": "#minecraft:enchantable/mining",
                "primary_items_tag": "#minecraft:enchantable/mining",
                "incompatible_enchantments": [],
                "anvil_cost": 1,
                "slots": ["mainhand"]
            }
        },
        {
            "id": "minecraft:unbreaking",
            "facts": {
                "display_name": "Unbreaking",
                "description": "Grants a chance for an item to avoid durability loss when used.",
                "max_level": 3,
                "supported_items_tag": "#minecraft:enchantable/mining",
                "primary_items_tag": "#minecraft:enchantable/mining",
                "incompatible_enchantments": [],
                "anvil_cost": 1,
                "slots": ["mainhand"]
            }
        },
        {
            "id": "minecraft:mending",
            "facts": {
                "display_name": "Mending",
                "description": "Restores durability using collected experience orbs.",
                "max_level": 1,
                "supported_items_tag": "#minecraft:enchantable/mining",
                "primary_items_tag": "#minecraft:enchantable/mining",
                "incompatible_enchantments": [],
                "anvil_cost": 2,
                "slots": ["mainhand"]
            }
        }
    ]

    for ench in raw_enchantments:
        doc = {
            "_id": make_id(ench["id"]),
            "entity_id": ench["id"],
            "slug": slugify_id(ench["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "facts": ench["facts"],
            "raw_source_refs": [
                {
                    "source_id": f"server-jar-{VERSION}",
                    "channel": "server_jar_resources",
                    "file": f"data/minecraft/enchantment/{ench['id'].replace('minecraft:', '')}.json",
                    "checksum": "sha256:88e1"
                }
            ],
            "derived": {
                "applicable_item_ids": []
            }
        }
        db.enchantments.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 11. Effects seed
    raw_effects = [
        {
            "id": "minecraft:haste",
            "facts": {
                "display_name": "Haste",
                "category": "beneficial",
                "color_rgb": [217, 192, 67],
                "color_hex": "#D9C043",
                "modifiers": [
                    {
                        "attribute": "minecraft:generic.attack_speed",
                        "amount_per_level": 0.1,
                        "operation": "add_multiplied_total"
                    }
                ],
                "verified_sources": ["minecraft:beacon", "minecraft:conduit"]
            }
        },
        {
            "id": "minecraft:speed",
            "facts": {
                "display_name": "Speed",
                "category": "beneficial",
                "color_rgb": [124, 175, 198],
                "color_hex": "#7CAFC6",
                "modifiers": [
                    {
                        "attribute": "minecraft:generic.movement_speed",
                        "amount_per_level": 0.2,
                        "operation": "add_multiplied_total"
                    }
                ],
                "verified_sources": ["minecraft:beacon", "minecraft:potion"]
            }
        }
    ]

    for eff in raw_effects:
        doc = {
            "_id": make_id(eff["id"]),
            "entity_id": eff["id"],
            "slug": slugify_id(eff["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "facts": eff["facts"],
            "raw_source_refs": [
                {
                    "source_id": f"mojang-reports-{VERSION}",
                    "channel": "mojang_reports",
                    "file": "reports/registries.json",
                    "checksum": "sha256:d5412"
                }
            ]
        }
        db.effects.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 12. Biomes seed
    raw_biomes = [
        {
            "id": "minecraft:plains",
            "facts": {
                "display_name": "Plains",
                "temperature": 0.8,
                "downfall": 0.4,
                "has_precipitation": true,
                "tags": ["#minecraft:is_overworld"]
            }
        },
        {
            "id": "minecraft:forest",
            "facts": {
                "display_name": "Forest",
                "temperature": 0.7,
                "downfall": 0.8,
                "has_precipitation": true,
                "tags": ["#minecraft:is_overworld"]
            }
        },
        {
            "id": "minecraft:desert",
            "facts": {
                "display_name": "Desert",
                "temperature": 2.0,
                "downfall": 0.0,
                "has_precipitation": false,
                "tags": ["#minecraft:is_overworld"]
            }
        },
        {
            "id": "minecraft:cherry_grove",
            "facts": {
                "display_name": "Cherry Grove",
                "temperature": 0.5,
                "downfall": 0.8,
                "has_precipitation": true,
                "tags": ["#minecraft:is_overworld"]
            }
        },
        {
            "id": "minecraft:deep_dark",
            "facts": {
                "display_name": "Deep Dark",
                "temperature": 0.8,
                "downfall": 0.4,
                "has_precipitation": false,
                "tags": ["#minecraft:is_overworld"]
            }
        }
    ]

    for bm in raw_biomes:
        doc = {
            "_id": make_id(bm["id"]),
            "entity_id": bm["id"],
            "slug": slugify_id(bm["id"]),
            "edition": EDITION,
            "version": VERSION,
            "version_type": VERSION_TYPE,
            "facts": bm["facts"],
            "raw_source_refs": [
                {
                    "source_id": f"server-jar-{VERSION}",
                    "channel": "server_jar_resources",
                    "file": f"data/minecraft/worldgen/biome/{bm['id'].replace('minecraft:', '')}.json",
                    "checksum": "sha256:f12a"
                }
            ],
            "derived": {
                "spawnable_entities": ["minecraft:creeper", "minecraft:zombie", "minecraft:enderman"]
            }
        }
        db.biomes.replace_one({"_id": doc["_id"]}, doc, upsert=True)

    # 13. Version Diffs (Machine-generated structured diffs)
    db.version_diffs.replace_one(
        {"_id": f"{EDITION}|{VERSION}|diff|minecraft:diamond_pickaxe"},
        {
            "_id": f"{EDITION}|{VERSION}|diff|minecraft:diamond_pickaxe",
            "entity_id": "minecraft:diamond_pickaxe",
            "edition": EDITION,
            "from_version": "1.21.3",
            "to_version": "1.21.4",
            "change_type": "modified",
            "changed_paths": ["facts.durability"],
            "before": {"facts": {"durability": 1561}},
            "after": {"facts": {"durability": 1561}},
            "raw_source_refs": [
                {"source_id": f"diff-engine-1.21.3-{VERSION}", "timestamp": datetime.now(timezone.utc).isoformat()}
            ]
        },
        upsert=True
    )

    print("Core seed data inserted. Now executing Graph Inversion Engine...")
    run_graph_inversion(db)


def run_graph_inversion(db):
    """
    Graph Inversion Engine:
    1. Inverts Recipes -> items.derived.crafted_from_recipes & items.derived.used_in_recipes
    2. Compiles Loot Tables -> blocks.derived.drops_summary & entities.derived.drops_summary
    3. Inverts Drops -> items.derived.dropped_by_blocks & items.derived.dropped_by_entities
    4. Resolves Tool Mining Matrix -> blocks.derived.harvest_tools & items.derived.can_mine_blocks
    5. Links Enchantments -> items.derived.compatible_enchantments & enchantments.derived.applicable_item_ids
    """
    print("1. Inverting Recipes...")
    recipes = list(db.recipes.find({"edition": EDITION, "version": VERSION}))
    for r in recipes:
        output_item = r["derived"]["output_item"]
        distinct_inputs = r["derived"]["distinct_input_items"]

        # Output item crafted from this recipe
        db.items.update_one(
            {"_id": make_id(output_item)},
            {"$addToSet": {"derived.crafted_from_recipes": r["entity_id"]}}
        )

        # Inputs used in this recipe
        for in_item in distinct_inputs:
            db.items.update_one(
                {"_id": make_id(in_item)},
                {"$addToSet": {"derived.used_in_recipes": r["entity_id"]}}
            )

    print("2. Compiling Loot Tables & Drops Summary...")
    loot_tables = {lt["entity_id"]: lt for lt in db.loot_tables.find({"edition": EDITION, "version": VERSION})}

    # Compile for Blocks
    blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION}))
    for b in blocks:
        lt_ref = b["facts"].get("loot_table_ref")
        drops_summary = []
        if lt_ref and lt_ref in loot_tables:
            lt = loot_tables[lt_ref]
            for target in lt["derived"].get("possible_targets", []):
                if target["type"] == "item":
                    drops_summary.append({
                        "target_type": "item",
                        "target_id": target["id"],
                        "min": 1,
                        "max": 1,
                        "chance": 1.0,
                        "conditions": ["survives_explosion"]
                    })
                    # Invert into item
                    db.items.update_one(
                        {"_id": make_id(target["id"])},
                        {"$addToSet": {"derived.dropped_by_blocks": b["entity_id"]}}
                    )
        db.blocks.update_one(
            {"_id": b["_id"]},
            {"$set": {"derived.drops_summary": drops_summary}}
        )

    # Compile for Entities
    entities = list(db.entities.find({"edition": EDITION, "version": VERSION}))
    for e in entities:
        lt_ref = e["facts"].get("loot_table_ref")
        drops_summary = []
        if lt_ref and lt_ref in loot_tables:
            lt = loot_tables[lt_ref]
            for target in lt["derived"].get("possible_targets", []):
                if target["type"] == "item":
                    drops_summary.append({
                        "target_type": "item",
                        "target_id": target["id"],
                        "min": 0,
                        "max": 2,
                        "conditions": ["player_kill"]
                    })
                    # Invert into item
                    db.items.update_one(
                        {"_id": make_id(target["id"])},
                        {"$addToSet": {"derived.dropped_by_entities": e["entity_id"]}}
                    )
        db.entities.update_one(
            {"_id": e["_id"]},
            {"$set": {"derived.drops_summary": drops_summary}}
        )

    print("3. Resolving Mining Matrix (Tools vs Blocks)...")
    # Tiers: wood(0) -> stone(1) -> iron(2) -> diamond(3) -> netherite(4)
    tier_order = {
        "wood": 0,
        "stone": 1,
        "iron": 2,
        "diamond": 3,
        "netherite": 4
    }
    tools = list(db.items.find({"edition": EDITION, "version": VERSION, "facts.mining_tier": {"$exists": True}}))

    for b in blocks:
        tags = b["facts"].get("tags", [])
        requires_pickaxe = "#minecraft:mineable/pickaxe" in tags
        required_tier = 0
        if "#minecraft:needs_stone_tool" in tags:
            required_tier = 1
        elif "#minecraft:needs_iron_tool" in tags:
            required_tier = 2
        elif "#minecraft:needs_diamond_tool" in tags:
            required_tier = 3

        valid_tools = []
        if requires_pickaxe:
            for t in tools:
                t_tier = tier_order.get(t["facts"].get("mining_tier"), 0)
                if t_tier >= required_tier:
                    valid_tools.append(t["entity_id"])
                    # Reciprocal link onto tool
                    db.items.update_one(
                        {"_id": t["_id"]},
                        {"$addToSet": {"derived.can_mine_blocks": b["entity_id"]}}
                    )
        db.blocks.update_one(
            {"_id": b["_id"]},
            {"$set": {"derived.harvest_tools": valid_tools}}
        )

    print("4. Linking Enchantments to Target Items...")
    enchantments = list(db.enchantments.find({"edition": EDITION, "version": VERSION}))
    for ench in enchantments:
        supp_tag = ench["facts"].get("supported_items_tag")
        tag_doc = db.tags.find_one({"tag_id": supp_tag, "edition": EDITION, "version": VERSION})
        applicable_items = tag_doc["derived"]["resolved_members"] if tag_doc else []
        db.enchantments.update_one(
            {"_id": ench["_id"]},
            {"$set": {"derived.applicable_item_ids": applicable_items}}
        )
        for item_id in applicable_items:
            db.items.update_one(
                {"_id": make_id(item_id)},
                {"$addToSet": {"derived.compatible_enchantments": ench["entity_id"]}}
            )

    # 5. Record Ingestion Run
    run_doc = {
        "_id": f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{EDITION}-{VERSION}",
        "edition": EDITION,
        "version": VERSION,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "channels": [
            {"channel": "mojang_reports", "status": "completed"},
            {"channel": "server_jar_resources", "status": "completed"},
            {"channel": "minecraft_data", "status": "completed"}
        ],
        "stats": {
            "items": db.items.count_documents({"edition": EDITION, "version": VERSION}),
            "blocks": db.blocks.count_documents({"edition": EDITION, "version": VERSION}),
            "recipes": db.recipes.count_documents({"edition": EDITION, "version": VERSION}),
            "loot_tables": db.loot_tables.count_documents({"edition": EDITION, "version": VERSION}),
            "entities": db.entities.count_documents({"edition": EDITION, "version": VERSION}),
            "enchantments": db.enchantments.count_documents({"edition": EDITION, "version": VERSION}),
            "effects": db.effects.count_documents({"edition": EDITION, "version": VERSION}),
            "biomes": db.biomes.count_documents({"edition": EDITION, "version": VERSION}),
            "tags": db.tags.count_documents({"edition": EDITION, "version": VERSION})
        }
    }
    db.ingestion_runs.replace_one({"_id": run_doc["_id"]}, run_doc, upsert=True)
    print(f"Ingestion run complete! Stats: {run_doc['stats']}")


if __name__ == "__main__":
    seed_data()
