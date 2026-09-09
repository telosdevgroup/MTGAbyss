"""
Download and locally cache canonical Minecraft Java Edition 1.21.4 textures
(Items, Blocks, Mob Effects) and update MongoDB records with SEO-optimized image paths.
"""

import os
import sys
import json
import urllib.request
import concurrent.futures
from pymongo import UpdateOne

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db

VERSION = "1.21.4"
EDITION = "java"
DB_NAME = "avascry_minecraft"

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "minecraft", "textures"))
ITEMS_DIR = os.path.join(STATIC_DIR, "items")
BLOCKS_DIR = os.path.join(STATIC_DIR, "blocks")
EFFECTS_DIR = os.path.join(STATIC_DIR, "effects")

BASE_URL = f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/{VERSION}"

def ensure_dirs():
    os.makedirs(ITEMS_DIR, exist_ok=True)
    os.makedirs(BLOCKS_DIR, exist_ok=True)
    os.makedirs(EFFECTS_DIR, exist_ok=True)

def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "AvaScry-TextureDownloader/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def download_file(args):
    url, dest_path = args
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return dest_path, True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AvaScry-TextureDownloader/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        return dest_path, True
    except Exception as e:
        return dest_path, False

def run_download():
    ensure_dirs()
    print("Fetching texture manifest maps from PrismarineJS/minecraft-assets...")

    # Manifests
    items_textures = fetch_json(f"{BASE_URL}/items_textures.json")
    blocks_textures = fetch_json(f"{BASE_URL}/blocks_textures.json")
    
    # Query git tree to find all available PNGs
    tree_data = fetch_json("https://api.github.com/repos/PrismarineJS/minecraft-assets/git/trees/master?recursive=1")
    available_paths = {
        x["path"].replace(f"data/{VERSION}/", ""): x["path"]
        for x in tree_data.get("tree", [])
        if x["path"].startswith(f"data/{VERSION}/") and x["path"].endswith(".png")
    }
    print(f"Found {len(available_paths)} available 1.21.4 PNG textures in upstream repo.")

    download_queue = []
    
    # Map of namespaced_id -> local static path
    item_image_map = {}
    block_image_map = {}

    # 1. Prepare Item downloads
    for entry in items_textures:
        name = entry["name"]
        raw_tex = entry.get("texture", "")
        if not raw_tex or raw_tex == "minecraft:missingno":
            continue

        # e.g. "minecraft:items/diamond_pickaxe" or "minecraft:block/stone"
        tex_path = raw_tex.replace("minecraft:", "")
        if tex_path.startswith("block/"):
            rel_png = f"blocks/{tex_path[6:]}.png"
            dest = os.path.join(BLOCKS_DIR, f"{tex_path[6:]}.png")
            web_path = f"/static/minecraft/textures/blocks/{tex_path[6:]}.png"
        elif tex_path.startswith("blocks/"):
            rel_png = f"blocks/{tex_path[7:]}.png"
            dest = os.path.join(BLOCKS_DIR, f"{tex_path[7:]}.png")
            web_path = f"/static/minecraft/textures/blocks/{tex_path[7:]}.png"
        elif tex_path.startswith("items/"):
            rel_png = f"items/{tex_path[6:]}.png"
            dest = os.path.join(ITEMS_DIR, f"{tex_path[6:]}.png")
            web_path = f"/static/minecraft/textures/items/{tex_path[6:]}.png"
        elif tex_path.startswith("item/"):
            rel_png = f"items/{tex_path[5:]}.png"
            dest = os.path.join(ITEMS_DIR, f"{tex_path[5:]}.png")
            web_path = f"/static/minecraft/textures/items/{tex_path[5:]}.png"
        else:
            rel_png = f"{tex_path}.png"
            dest = os.path.join(ITEMS_DIR, f"{os.path.basename(tex_path)}.png")
            web_path = f"/static/minecraft/textures/items/{os.path.basename(tex_path)}.png"

        if rel_png in available_paths:
            download_url = f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/{available_paths[rel_png]}"
            download_queue.append((download_url, dest))
            item_image_map[f"minecraft:{name}"] = web_path

    # Direct name matches for any missing items
    for p in available_paths:
        if p.startswith("items/"):
            base_name = os.path.splitext(os.path.basename(p))[0]
            namespaced = f"minecraft:{base_name}"
            dest = os.path.join(ITEMS_DIR, os.path.basename(p))
            if namespaced not in item_image_map:
                download_queue.append((f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/{available_paths[p]}", dest))
                item_image_map[namespaced] = f"/static/minecraft/textures/items/{os.path.basename(p)}"

    # 2. Prepare Block downloads
    for entry in blocks_textures:
        name = entry["name"]
        raw_tex = entry.get("texture", "")
        if not raw_tex or raw_tex == "minecraft:missingno":
            continue

        tex_path = raw_tex.replace("minecraft:", "")
        if tex_path.startswith("blocks/"):
            rel_png = f"blocks/{tex_path[7:]}.png"
            dest = os.path.join(BLOCKS_DIR, f"{tex_path[7:]}.png")
            web_path = f"/static/minecraft/textures/blocks/{tex_path[7:]}.png"
        elif tex_path.startswith("block/"):
            rel_png = f"blocks/{tex_path[6:]}.png"
            dest = os.path.join(BLOCKS_DIR, f"{tex_path[6:]}.png")
            web_path = f"/static/minecraft/textures/blocks/{tex_path[6:]}.png"
        else:
            rel_png = f"blocks/{tex_path}.png"
            dest = os.path.join(BLOCKS_DIR, f"{os.path.basename(tex_path)}.png")
            web_path = f"/static/minecraft/textures/blocks/{os.path.basename(tex_path)}.png"

        if rel_png in available_paths:
            download_url = f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/{available_paths[rel_png]}"
            download_queue.append((download_url, dest))
            block_image_map[f"minecraft:{name}"] = web_path

    # Direct name matches for blocks
    for p in available_paths:
        if p.startswith("blocks/"):
            base_name = os.path.splitext(os.path.basename(p))[0]
            namespaced = f"minecraft:{base_name}"
            dest = os.path.join(BLOCKS_DIR, os.path.basename(p))
            if namespaced not in block_image_map:
                download_queue.append((f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/{available_paths[p]}", dest))
                block_image_map[namespaced] = f"/static/minecraft/textures/blocks/{os.path.basename(p)}"

    # 3. Effects
    for p in available_paths:
        if p.startswith("mob_effect/"):
            base_name = os.path.splitext(os.path.basename(p))[0]
            dest = os.path.join(EFFECTS_DIR, os.path.basename(p))
            download_queue.append((f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/{available_paths[p]}", dest))

    # Deduplicate download queue
    unique_downloads = list({dest: url for url, dest in download_queue}.items())
    unique_args = [(url, dest) for dest, url in unique_downloads]
    print(f"Downloading {len(unique_args)} unique texture PNGs in parallel...")

    success_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        results = executor.map(download_file, unique_args)
        for _, ok in results:
            if ok:
                success_count += 1

    print(f"Downloaded/verified {success_count} / {len(unique_args)} texture files.")

    # Save mapping index
    map_path = os.path.join(STATIC_DIR, "texture_map.json")
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump({"items": item_image_map, "blocks": block_image_map}, f, indent=2)
    print(f"Saved texture map index to {map_path}")

    # 4. Update MongoDB records with facts.image_url
    client = get_mongo_db().client
    db = client[DB_NAME]

    print("Updating MongoDB items with image URLs...")
    item_updates = []
    for eid, img_url in item_image_map.items():
        item_updates.append(
            UpdateOne(
                {"edition": EDITION, "version": VERSION, "entity_id": eid},
                {"$set": {"facts.image_url": img_url}}
            )
        )
    if item_updates:
        res = db.items.bulk_write(item_updates, ordered=False)
        print(f"Updated {res.modified_count} items with facts.image_url.")

    print("Updating MongoDB blocks with image URLs...")
    block_updates = []
    for eid, img_url in block_image_map.items():
        block_updates.append(
            UpdateOne(
                {"edition": EDITION, "version": VERSION, "entity_id": eid},
                {"$set": {"facts.image_url": img_url}}
            )
        )
    if block_updates:
        res = db.blocks.bulk_write(block_updates, ordered=False)
        print(f"Updated {res.modified_count} blocks with facts.image_url.")

    print("Texture download and database indexing finished successfully!")

if __name__ == "__main__":
    run_download()
