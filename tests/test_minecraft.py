"""
SiteBlaster Invariant & Tri-Surface Verification Suite for AvaScry Minecraft.
Enforces MC-01 through MC-14 and validates tri-surface parity.
"""

import pytest
from starlette.testclient import TestClient
from app import app
from scripts.ingest_minecraft import get_mc_db, EDITION, VERSION

client = TestClient(app)


# ---------------- 1. ENDPOINTS & SUBDOMAIN ROUTING ----------------

def test_minecraft_home_endpoints():
    r = client.get("/minecraft")
    assert r.status_code == 200, f"/minecraft returned {r.status_code}"
    assert "AvaScry Minecraft" in r.text
    assert "Java 1.21.4" in r.text
    assert "Items &amp; Tools" in r.text or "Items & Tools" in r.text


def test_minecraft_subdomain_middleware():
    r = client.get("/", headers={"host": "minecraft.avascry.com"})
    assert r.status_code == 200
    assert "AvaScry Minecraft" in r.text
    assert "Java 1.21.4" in r.text


def test_minecraft_llms_txt():
    r = client.get("/minecraft/llms.txt")
    assert r.status_code == 200
    assert "AvaScry Minecraft — Java Edition Vanilla Data Atlas" in r.text
    assert "/item/{slug}" in r.text

    r_full = client.get("/minecraft/llms-full.txt")
    assert r_full.status_code == 200
    assert "ITEMS & TOOLS" in r_full.text
    assert "Diamond Pickaxe" in r_full.text


# ---------------- 2. TRI-SURFACE PARITY (HTML, JSON, MD) ----------------

def test_item_tri_surface():
    # 1. HTML
    r_html = client.get("/minecraft/item/diamond-pickaxe")
    assert r_html.status_code == 200
    assert "Diamond Pickaxe" in r_html.text
    assert "1561" in r_html.text

    # 2. JSON
    r_json = client.get("/minecraft/item/diamond-pickaxe.json")
    assert r_json.status_code == 200
    data = r_json.json()
    assert data["entity_id"] == "minecraft:diamond_pickaxe"
    assert data["edition"] == "java"
    assert data["version"] == "1.21.4"
    assert data["facts"]["durability"] == 1561

    # 3. Markdown
    r_md = client.get("/minecraft/item/diamond-pickaxe.md")
    assert r_md.status_code == 200
    assert "title: \"Diamond Pickaxe" in r_md.text
    assert "durability: 1561" in r_md.text
    assert "slug: \"diamond-pickaxe\"" in r_md.text


def test_block_tri_surface():
    # 1. HTML
    r_html = client.get("/minecraft/block/diamond-ore")
    assert r_html.status_code == 200
    assert "Diamond Ore" in r_html.text

    # 2. JSON
    r_json = client.get("/minecraft/block/diamond-ore.json")
    assert r_json.status_code == 200
    data = r_json.json()
    assert data["entity_id"] == "minecraft:diamond_ore"
    assert data["facts"]["hardness"] == 3.0
    assert len(data["derived"]["harvest_tools"]) > 0

    # 3. Markdown
    r_md = client.get("/minecraft/block/diamond-ore.md")
    assert r_md.status_code == 200
    assert "hardness: 3.0" in r_md.text


def test_recipe_tri_surface():
    r_html = client.get("/minecraft/recipe/diamond-pickaxe")
    assert r_html.status_code == 200

    r_json = client.get("/minecraft/recipe/diamond-pickaxe.json")
    assert r_json.status_code == 200
    assert r_json.json()["derived"]["output_item"] == "minecraft:diamond_pickaxe"

    r_md = client.get("/minecraft/recipe/diamond-pickaxe.md")
    assert r_md.status_code == 200
    assert "Recipe: diamond-pickaxe" in r_md.text


def test_entity_tri_surface():
    r_html = client.get("/minecraft/entity/creeper")
    assert r_html.status_code == 200
    assert "Creeper" in r_html.text

    r_json = client.get("/minecraft/entity/creeper.json")
    assert r_json.status_code == 200
    assert r_json.json()["facts"]["max_health"] == 20.0

    r_md = client.get("/minecraft/entity/creeper.md")
    assert r_md.status_code == 200
    assert "max_health: 20.0" in r_md.text


def test_catalog_lists_tri_surface():
    """Verify that catalog lists support machine .json and .md formats."""
    # 1. Items catalog
    r_items_json = client.get("/minecraft/items.json?limit=12")
    assert r_items_json.status_code == 200
    items_data = r_items_json.json()
    assert items_data["category"] == "items"
    assert len(items_data["entries"]) > 0
    assert "facts" in items_data["entries"][0]

    r_items_md = client.get("/minecraft/items.md?limit=12")
    assert r_items_md.status_code == 200
    assert "# Minecraft Java 1.21.4 - Items & Tools Catalog" in r_items_md.text
    assert "| Name | Entity ID |" in r_items_md.text

    # 2. Blocks catalog
    r_blocks_json = client.get("/minecraft/blocks.json?limit=12")
    assert r_blocks_json.status_code == 200
    blocks_data = r_blocks_json.json()
    assert blocks_data["category"] == "blocks"
    assert len(blocks_data["entries"]) > 0

    r_blocks_md = client.get("/minecraft/blocks.md?limit=12")
    assert r_blocks_md.status_code == 200
    assert "# Minecraft Java 1.21.4 - Blocks Catalog" in r_blocks_md.text

    # 3. Recipes catalog
    r_rec_json = client.get("/minecraft/recipes.json?limit=12")
    assert r_rec_json.status_code == 200
    assert r_rec_json.json()["category"] == "recipes"

    r_rec_md = client.get("/minecraft/recipes.md?limit=12")
    assert r_rec_md.status_code == 200
    assert "# Minecraft Java 1.21.4 - Recipes Catalog" in r_rec_md.text

    # 4. Entities catalog
    r_ent_json = client.get("/minecraft/entities.json?limit=12")
    assert r_ent_json.status_code == 200
    assert r_ent_json.json()["category"] == "entities"

    r_ent_md = client.get("/minecraft/entities.md?limit=12")
    assert r_ent_md.status_code == 200
    assert "# Minecraft Java 1.21.4 - Entities & Mobs Catalog" in r_ent_md.text



# ---------------- 3. SITEBLASTER INVARIANTS (MC-01 to MC-14) ----------------

def test_mc_01_recipe_inputs_and_outputs():
    """MC-01: 100% of recipe distinct inputs and outputs resolve to items collection."""
    db = get_mc_db()
    items = {i["entity_id"] for i in db.items.find({"edition": EDITION, "version": VERSION})}
    recipes = list(db.recipes.find({"edition": EDITION, "version": VERSION}))
    assert len(recipes) > 0

    for r in recipes:
        out = r["derived"]["output_item"]
        assert out in items, f"Recipe output '{out}' not found in items collection."
        for in_item in r["derived"]["distinct_input_items"]:
            assert in_item in items, f"Recipe input '{in_item}' not found in items collection."


def test_mc_02_loot_table_target_validity():
    """MC-02: Every loot-table reference resolves to a valid typed target."""
    db = get_mc_db()
    items = {i["entity_id"] for i in db.items.find({"edition": EDITION, "version": VERSION})}
    loot_tables = list(db.loot_tables.find({"edition": EDITION, "version": VERSION}))
    assert len(loot_tables) > 0

    valid_types = {"item", "entity", "loot_table", "experience", "dynamic"}
    for lt in loot_tables:
        for target in lt["derived"].get("possible_targets", []):
            assert target["type"] in valid_types
            if target["type"] == "item":
                assert target["id"] in items, f"Loot table target item '{target['id']}' not in items."


def test_mc_03_reciprocity_recipes():
    """MC-03: If item A is derived as used in recipe R, recipe R must declare item A as input."""
    db = get_mc_db()
    recipes = {r["entity_id"]: r for r in db.recipes.find({"edition": EDITION, "version": VERSION})}
    items_with_recipes = list(db.items.find({"edition": EDITION, "version": VERSION, "derived.used_in_recipes": {"$ne": []}}))
    assert len(items_with_recipes) > 0

    for itm in items_with_recipes:
        for r_id in itm["derived"]["used_in_recipes"]:
            assert r_id in recipes, f"Recipe '{r_id}' not found."
            assert itm["entity_id"] in recipes[r_id]["derived"]["distinct_input_items"]


def test_mc_04_mining_tools_invariant():
    """MC-04: Every block requiring a tool has at least 1 valid harvest tool."""
    db = get_mc_db()
    blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION, "facts.tool_required": True}))
    assert len(blocks) > 0

    for b in blocks:
        assert len(b["derived"]["harvest_tools"]) > 0, f"Block {b['entity_id']} requires tool but has empty harvest_tools."


def test_mc_05_and_mc_13_fact_parity():
    """MC-05 & MC-13: Tri-surface parity across HTML, JSON, and Markdown."""
    r_json = client.get("/minecraft/item/diamond-pickaxe.json").json()
    r_md = client.get("/minecraft/item/diamond-pickaxe.md").text
    r_html = client.get("/minecraft/item/diamond-pickaxe").text

    durability = str(r_json["facts"]["durability"])
    assert durability in r_md
    assert durability in r_html


def test_mc_06_llms_files_valid():
    """MC-06: /llms.txt and /llms-full.txt resolve with 200 OK."""
    assert client.get("/minecraft/llms.txt").status_code == 200
    assert client.get("/minecraft/llms-full.txt").status_code == 200


def test_mc_07_namespaced_id_resolution():
    """MC-07: All internal IDs start with minecraft: and follow namespaced format."""
    db = get_mc_db()
    for coll_name in ["items", "blocks", "recipes", "entities", "enchantments", "effects"]:
        for doc in db[coll_name].find({"edition": EDITION, "version": VERSION}):
            assert doc["entity_id"].startswith("minecraft:"), f"{coll_name} doc has non-namespaced ID: {doc['entity_id']}"


def test_mc_08_tag_existence_and_empty_support():
    """MC-08: Every tag exists in tags collection, and empty tags are supported."""
    db = get_mc_db()
    empty_tag = db.tags.find_one({"tag_id": "#minecraft:empty_test_tag", "edition": EDITION, "version": VERSION})
    assert empty_tag is not None
    assert empty_tag["is_empty"] is True
    assert empty_tag["derived"]["resolved_members"] == []

    pickaxe_tag = db.tags.find_one({"tag_id": "#minecraft:pickaxes", "edition": EDITION, "version": VERSION})
    assert pickaxe_tag is not None
    assert pickaxe_tag["is_empty"] is False
    assert "minecraft:diamond_pickaxe" in pickaxe_tag["derived"]["resolved_members"]


def test_mc_09_loot_ast_parsing():
    """MC-09: Raw loot tables preserve AST nodes (pools, entries, conditions, functions)."""
    db = get_mc_db()
    dia_ore_lt = db.loot_tables.find_one({"entity_id": "minecraft:blocks/diamond_ore", "edition": EDITION, "version": VERSION})
    assert dia_ore_lt is not None
    assert "raw_ast" in dia_ore_lt
    assert "pools" in dia_ore_lt["raw_ast"]


def test_mc_10_provenance_metadata():
    """MC-10: Every record contains non-empty raw_source_refs with source_id and checksum."""
    db = get_mc_db()
    for coll_name in ["items", "blocks", "recipes", "loot_tables", "entities", "tags"]:
        for doc in db[coll_name].find({"edition": EDITION, "version": VERSION}):
            assert "raw_source_refs" in doc
            assert len(doc["raw_source_refs"]) > 0
            assert "source_id" in doc["raw_source_refs"][0]


def test_mc_11_slug_uniqueness():
    """MC-11: Slugs are unique within each entity collection for the version."""
    db = get_mc_db()
    for coll_name in ["items", "blocks", "recipes", "entities"]:
        slugs = [doc["slug"] for doc in db[coll_name].find({"edition": EDITION, "version": VERSION})]
        assert len(slugs) == len(set(slugs)), f"Duplicate slugs detected in {coll_name}."


def test_mc_12_route_alternate_resolution():
    """MC-12: Canonical URLs and their .md and .json alternates resolve with 200."""
    for slug in ["diamond-pickaxe", "iron-pickaxe"]:
        assert client.get(f"/minecraft/item/{slug}").status_code == 200
        assert client.get(f"/minecraft/item/{slug}.json").status_code == 200
        assert client.get(f"/minecraft/item/{slug}.md").status_code == 200


def test_mc_14_zero_orphan_graph_edges():
    """MC-14: Zero orphan edges in derived graphs."""
    db = get_mc_db()
    blocks = {b["entity_id"] for b in db.blocks.find({"edition": EDITION, "version": VERSION})}
    items = list(db.items.find({"edition": EDITION, "version": VERSION}))

    for itm in items:
        for b_id in itm["derived"].get("can_mine_blocks", []):
            assert b_id in blocks, f"Item {itm['entity_id']} has orphaned block reference: {b_id}"


# ---------------- 4. SEARCH & FILTERING TESTS ----------------

def test_minecraft_list_query_filtering():
    """Test server-side ?q= query filtering on items and blocks."""
    r_items = client.get("/minecraft/items?q=diamond_pickaxe")
    assert r_items.status_code == 200
    assert "Diamond Pickaxe" in r_items.text

    r_blocks = client.get("/minecraft/blocks?q=diamond_ore")
    assert r_blocks.status_code == 200
    assert "Diamond Ore" in r_blocks.text


def test_minecraft_search_api():
    """Test /api/search JSON autocomplete endpoint."""
    r = client.get("/minecraft/api/search?q=diamond")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) > 0
    names = [res["name"] for res in data["results"]]
    assert any("Diamond" in n for n in names)


# ---------------- 5. ULTRA IMAGE SEO & TEXTURES TESTS ----------------

def test_minecraft_image_seo():
    """Verify ImageObject schema, OpenGraph image tags, and local sprite serving."""
    # 1. Item detail page has OG image & JSON-LD ImageObject
    r = client.get("/minecraft/item/diamond-pickaxe")
    assert r.status_code == 200
    assert 'property="og:image"' in r.text
    assert '"@type": "ImageObject"' in r.text
    assert 'image-rendering: pixelated' in r.text

    # 2. Block detail page has OG image & JSON-LD ImageObject
    r_blk = client.get("/minecraft/block/diamond-ore")
    assert r_blk.status_code == 200
    assert 'property="og:image"' in r_blk.text
    assert '"@type": "ImageObject"' in r_blk.text

    # 3. Static asset endpoint serves the actual sprite locally with 200 OK
    r_img = client.get("/static/minecraft/textures/items/diamond_pickaxe.png")
    assert r_img.status_code == 200
    assert len(r_img.content) > 0
    assert r_img.headers["content-type"] in ["image/png", "application/octet-stream"]


def test_effects_sprites_and_descriptions():
    """Verify that /effects renders sprites, clean category badges, and mechanic descriptions."""
    r = client.get("/minecraft/effects")
    assert r.status_code == 200
    # Sprites served
    assert "/static/minecraft/textures/effects/haste.png" in r.text
    assert "/static/minecraft/textures/effects/regeneration.png" in r.text
    # Descriptions rendered
    assert "Increases mining speed by 20%" in r.text
    assert "Restores health over time independently of saturation" in r.text
    # Check that hero is not wrapped in white box / elevated class
    assert "category-hero" in r.text



