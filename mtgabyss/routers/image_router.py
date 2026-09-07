"""
mtgabyss.routers.image_router
-------------------------------
Card image serving with O(1) in-memory prefix index.
Builds an IMAGE_PREFIX_MAP on startup in a background daemon thread.
resolve_card_images in shared.helpers imports IMAGE_PREFIX_MAP from here (lazy import).
"""
import os
import asyncio
import threading

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from db_mongo import get_mongo_db
from mtgabyss.shared.helpers import get_scryfall_direct_uris, _download_and_save_image

image_router = APIRouter()

# In-memory prefix index for O(1) resolution of multi-face, art-series, and extensionless card slugs
IMAGE_PREFIX_MAP = {"normal": {}, "large": {}}


def build_image_prefix_index():
    """Build in-memory prefix hash table in background thread on startup (takes ~1s for 340k files)."""
    for size_type in ("normal", "large"):
        folder = os.path.join("public", "images", size_type)
        if not os.path.isdir(folder):
            continue
        try:
            m = {}
            for f in os.listdir(folder):
                if f.endswith((".jpg", ".png", ".webp")):
                    base = os.path.splitext(f)[0]
                    m[base] = f
                    parts = f.split("-")
                    for i in range(1, len(parts)):
                        prefix = "-".join(parts[:i])
                        if prefix not in m:
                            m[prefix] = f
            IMAGE_PREFIX_MAP[size_type] = m
            print(f"[Image Index] Cached {len(m):,} prefix entries for {size_type} in RAM.")
        except Exception as e:
            print(f"[Image Index Error] {e}")


# Start background indexing on module import (fires once at startup)
threading.Thread(target=build_image_prefix_index, daemon=True).start()


# Serve card images with long-lived Cache-Control so Cloudflare caches them at the edge
@image_router.get("/images/{rest_of_path:path}", include_in_schema=False)
async def serve_image(rest_of_path: str):
    file_path = os.path.join("public", "images", rest_of_path)

    # 1. Direct O(1) file match on disk
    if os.path.isfile(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
        return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

    # 2. Fast O(1) checks for missing extensions and multi-face suffixes
    for ext_try in [".jpg", ".webp", ".png", ".jpeg", "_0.jpg", "_1.jpg"]:
        candidate = file_path + ext_try
        if os.path.isfile(candidate):
            ext = os.path.splitext(candidate)[1].lower()
            media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
            return FileResponse(candidate, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

    # 3. Instant in-memory prefix lookup (resolves murder-murder, cecil-dark-knight...)
    parts = rest_of_path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] in ("normal", "large"):
        size_type = parts[0]
        slug_or_name = os.path.splitext(parts[1])[0]

        matched_filename = IMAGE_PREFIX_MAP.get(size_type, {}).get(slug_or_name)
        if matched_filename:
            target_path = os.path.join("public", "images", size_type, matched_filename)
            if os.path.isfile(target_path):
                ext = os.path.splitext(target_path)[1].lower()
                media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/jpeg")
                return FileResponse(target_path, media_type=media_type, headers={"Cache-Control": "public, max-age=2592000, immutable"})

        # 4. Fallback indexed lookup if card is completely un-cached
        clean_name = slug_or_name.replace("-", " ").title()

        def _lookup_card():
            db = get_mongo_db()
            return db["cards"].find_one(
                {"lang": "en", "$or": [{"slug": slug_or_name}, {"name": clean_name}]},
                {"image_uris": 1, "card_faces": 1, "raw": 1}
            ) or db["cards"].find_one(
                {"$or": [{"slug": slug_or_name}, {"name": clean_name}]},
                {"image_uris": 1, "card_faces": 1, "raw": 1}
            )

        try:
            card = await asyncio.to_thread(_lookup_card)
            if card:
                _, cdn_normal, cdn_large = get_scryfall_direct_uris(card)
                cdn_url = cdn_large if size_type == "large" else cdn_normal
                if cdn_url:
                    dest_save = file_path if file_path.endswith('.jpg') else file_path + '.jpg'
                    asyncio.create_task(_download_and_save_image(cdn_url, dest_save))
                    return RedirectResponse(url=cdn_url, status_code=307)
        except Exception as e:
            print(f"[Image Resolver Error] {e}")

    raise HTTPException(status_code=404)
