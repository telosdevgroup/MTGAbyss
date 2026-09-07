"""
mtgabyss.routers.static_router
--------------------------------
All static / well-known file endpoints: sitemap, robots, llms, ads,
indexnow key file, rules, legalities, manifest, heartbeat, etc.
"""
import os

from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse

from mtgabyss.shared.helpers import INDEXNOW_KEY

static_router = APIRouter()

@static_router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")

@static_router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    return FileResponse("public/sitemap.xml", media_type="application/xml")

@static_router.get("/sitemap-{name}.xml", include_in_schema=False)
async def sub_sitemap_xml(name: str):
    file_path = os.path.join("public", f"sitemap-{name}.xml")
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/xml")
    return PlainTextResponse("Sitemap not found", status_code=404)

@static_router.get("/sitemap.html", include_in_schema=False)
async def sitemap_html():
    return FileResponse("public/sitemap.html", media_type="text/html; charset=utf-8")

@static_router.get("/sitemaps/{filename}", include_in_schema=False)
async def sitemaps_file(filename: str):
    file_path = os.path.join("public", "sitemaps", filename)
    if os.path.exists(file_path):
        if filename.endswith(".md"):
            return FileResponse(file_path, media_type="text/markdown; charset=utf-8")
        return FileResponse(file_path, media_type="text/html; charset=utf-8")
    return PlainTextResponse("Sitemap not found", status_code=404)

@static_router.get("/sitemap.md", include_in_schema=False)
async def sitemap_md():
    return FileResponse("public/sitemap.md", media_type="text/markdown; charset=utf-8")

@static_router.get("/rules.md", include_in_schema=False)
async def rules_md():
    return FileResponse("public/rules.md", media_type="text/markdown; charset=utf-8", headers={"Link": '</rules.json>; rel="alternate"; type="application/json"'})

@static_router.get("/rules.json", include_in_schema=False)
async def rules_json():
    return FileResponse("public/rules.json", media_type="application/json", headers={"Link": '</rules.md>; rel="alternate"; type="text/markdown"'})

@static_router.get("/legalities.md", include_in_schema=False)
async def legalities_md():
    return FileResponse("public/legalities.md", media_type="text/markdown; charset=utf-8", headers={"Link": '</legalities.json>; rel="alternate"; type="application/json"'})

@static_router.get("/legalities.json", include_in_schema=False)
async def legalities_json():
    return FileResponse("public/legalities.json", media_type="application/json", headers={"Link": '</legalities.md>; rel="alternate"; type="text/markdown"'})

@static_router.get("/sets.md", include_in_schema=False)
async def sets_md():
    return FileResponse("public/sets.md", media_type="text/markdown; charset=utf-8")

@static_router.get("/.well-known/ai-content", include_in_schema=False)
async def well_known_ai_content():
    return FileResponse("public/.well-known/ai-content", media_type="text/plain; charset=utf-8")

@static_router.get("/manifest.json", include_in_schema=False)
async def manifest_json():
    return FileResponse("public/manifest.json", media_type="application/manifest+json")

@static_router.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    return FileResponse("public/robots.txt", media_type="text/plain")

@static_router.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    return FileResponse("public/llms.txt", media_type="text/plain; charset=utf-8")

@static_router.get("/llms-full.txt", include_in_schema=False)
async def llms_full_txt():
    return FileResponse("public/llms-full.txt", media_type="text/plain; charset=utf-8")

@static_router.get("/heartbeat.txt", include_in_schema=False)
async def heartbeat_txt():
    return FileResponse("public/heartbeat.txt", media_type="text/plain; charset=utf-8")

@static_router.get("/ads.txt", response_class=PlainTextResponse, include_in_schema=False)
async def ads_txt():
    return "google.com, pub-7283717447639840, DIRECT, f08c47fec0942fa0\n"

@static_router.get("/b3901b0f58d0445bb8d15a9e334df58a.txt", response_class=PlainTextResponse, include_in_schema=False)
async def indexnow_key_txt():
    return f"{INDEXNOW_KEY}\n"
