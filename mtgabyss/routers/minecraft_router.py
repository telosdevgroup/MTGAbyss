"""
AvaScry Minecraft Router for minecraft.avascry.com.
Connects directly to MongoDB database 'avascry_minecraft'.
Serves HTML, Markdown (.md), JSON, and llms.txt endpoints for bots and humans.
"""

from datetime import datetime, timezone
import json
import time
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db_mongo import get_mongo_db
from mtgabyss.shared.cache import RAM_CACHE, set_ram_cache
from mtgabyss.shared.helpers import slugify

def human_name(val: str) -> str:
    if not val:
        return ""
    # strip namespace prefix like minecraft:
    s = str(val).split(":")[-1]
    # replace underscores/dashes with spaces and title-case
    return s.replace("_", " ").replace("-", " ").title()


def mc_slugify(val: str) -> str:
    if not val:
        return ""
    s = str(val).split(":")[-1]
    return slugify(s)


def normalize_mc_slug(slug: str) -> str:
    if not slug:
        return ""
    s = slug.strip().lower()
    for prefix in ["minecraft:", "minecraft-", "minecraft_"]:
        if s.startswith(prefix):
            return slugify(s[len(prefix):])
    if s.startswith("minecraft") and len(s) > 9:
        return slugify(s[9:])
    return s


minecraft_router = APIRouter(prefix="", tags=["Minecraft"])
templates = Jinja2Templates(directory="templates")
templates.env.filters["slugify"] = mc_slugify
templates.env.filters["human_name"] = human_name

EDITION = "java"
VERSION = "1.21.4"


def get_minecraft_db():
    client = get_mongo_db().client
    return client["avascry_minecraft"]


def get_base_prefix(request: Request) -> str:
    host = request.headers.get("host", "")
    from mtgabyss.network_router import extract_subdomain
    if extract_subdomain(host) == "minecraft":
        return ""
    return "/minecraft"


def get_current_user(request: Request):
    return request.session.get("user") if "session" in request.scope else None


@minecraft_router.get("", response_class=HTMLResponse)
@minecraft_router.get("/", response_class=HTMLResponse)
async def minecraft_home(request: Request):
    cache_key = f"mc:home_data:{int(time.time() // 3600)}"
    cached = RAM_CACHE.get(cache_key)
    if not cached:
        db = get_minecraft_db()
        items = list(db.items.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))
        blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))
        recipes = list(db.recipes.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))
        entities = list(db.entities.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))
        enchantments = list(db.enchantments.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))
        effects = list(db.effects.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))

        # Iconic items with visual textures
        sample_item_slugs = ['diamond-sword', 'diamond-pickaxe', 'netherite-ingot', 'elytra', 'golden-apple', 'bow', 'ender-pearl']
        sample_items = [it for it in items if it.get("slug") in sample_item_slugs]
        if len(sample_items) < 6:
            sample_items = [it for it in items if it.get("facts", {}).get("image_url")][:7]

        # Iconic blocks with visual textures
        sample_block_slugs = ['diamond-ore', 'obsidian', 'ancient-debris', 'crafting-table', 'furnace', 'enchanting-table', 'beacon']
        sample_blocks = [b for b in blocks if b.get("slug") in sample_block_slugs]
        if len(sample_blocks) < 6:
            sample_blocks = [b for b in blocks if b.get("facts", {}).get("image_url")][:7]

        # Iconic recipes with outputs
        sample_recipe_slugs = ['diamond-pickaxe', 'diamond-sword', 'crafting-table', 'furnace', 'beacon', 'enchanting-table', 'shield']
        sample_recipes = []
        item_img_map = {it["entity_id"]: it.get("facts", {}).get("image_url") for it in items if it.get("facts", {}).get("image_url")}
        for r in recipes:
            if r.get("slug") in sample_recipe_slugs:
                out_id = r.get("derived", {}).get("output_item", "")
                r_copy = dict(r)
                r_copy["image_url"] = item_img_map.get(out_id)
                r_copy["display_name"] = human_name(out_id or r["slug"])
                sample_recipes.append(r_copy)

        # Iconic entities & mobs
        sample_entity_slugs = ['creeper', 'ender-dragon', 'enderman', 'warden', 'iron-golem', 'blaze', 'zombie']
        sample_entities = [e for e in entities if e.get("slug") in sample_entity_slugs]
        if len(sample_entities) < 6:
            sample_entities = entities[:7]

        cached = {
            "total_items": len(items),
            "total_blocks": len(blocks),
            "total_recipes": len(recipes),
            "total_entities": len(entities),
            "total_enchantments": len(enchantments),
            "total_effects": len(effects),
            "sample_items": sample_items,
            "sample_blocks": sample_blocks,
            "sample_recipes": sample_recipes,
            "sample_entities": sample_entities
        }
        set_ram_cache(cache_key, cached)

    base_prefix = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="minecraft/home.html",
        context={
            "base_prefix": base_prefix,
            "user": get_current_user(request),
            **cached
        }
    )


@minecraft_router.get("/llms.txt", response_class=PlainTextResponse)
async def minecraft_llms_txt():
    """Agentic LLMs Navigation Directory for AvaScry Minecraft."""
    return (
        "# AvaScry Minecraft — Java Edition Vanilla Data Atlas\n\n"
        "> Deterministic, version-pinned machine-readable knowledge base for Minecraft Java Edition.\n"
        f"> Target Release: Java {VERSION} (Vanilla, unmodded)\n\n"
        "## Master Indexes\n"
        "- [Atlas Home](https://minecraft.avascry.com/)\n"
        "- [Items Catalog](https://minecraft.avascry.com/items)\n"
        "- [Blocks Catalog](https://minecraft.avascry.com/blocks)\n"
        "- [Builder Palette Generator](https://minecraft.avascry.com/palette)\n"
        "- [Recipes Catalog](https://minecraft.avascry.com/recipes)\n"
        "- [Entities Catalog](https://minecraft.avascry.com/entities)\n"
        "- [Enchantments Catalog](https://minecraft.avascry.com/enchantments)\n"
        "- [Effects Catalog](https://minecraft.avascry.com/effects)\n"
        "- [Full LLM Corpus](https://minecraft.avascry.com/llms-full.txt)\n\n"
        "## Tri-Surface Endpoints\n"
        "- Item Detail: https://minecraft.avascry.com/item/{slug} (.md, .json)\n"
        "- Block Detail: https://minecraft.avascry.com/block/{slug} (.md, .json)\n"
        "- Builder Palette: https://minecraft.avascry.com/palette/{slug} (.md, .json)\n"
        "- Recipe Detail: https://minecraft.avascry.com/recipe/{slug} (.md, .json)\n"
        "- Entity Detail: https://minecraft.avascry.com/entity/{slug} (.md, .json)\n\n"
        "## Multi-Modal Vector Embeddings\n"
        "- `functional_substitutes`: Semantic mechanics, combat, and utility affinity.\n"
        "- `palette_matches`: Architectural chroma, material texture, and aesthetic harmony.\n"
        "- `progression_neighbors`: DAG crafting dependencies and survival tech tree depth.\n\n"
        "## Data Integrity Invariants\n"
        "- MC-01 through MC-14 verified via SiteBlaster automated test suite.\n"
        "- Zero client-side JavaScript required. Machine-first design.\n"
    )


@minecraft_router.get("/llms-full.txt", response_class=PlainTextResponse)
async def minecraft_llms_full_txt():
    """Complete vanilla corpus for direct LLM grounding."""
    db = get_minecraft_db()
    items = list(db.items.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))
    blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))
    recipes = list(db.recipes.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))
    entities = list(db.entities.find({"edition": EDITION, "version": VERSION}, {"_id": 0}))

    lines = [
        f"# AvaScry Minecraft — Complete Vanilla Data Atlas (Java {VERSION})",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Total Items: {len(items)}",
        f"Total Blocks: {len(blocks)}",
        f"Total Recipes: {len(recipes)}",
        f"Total Entities: {len(entities)}\n",
        "---",
        "## ITEMS & TOOLS\n"
    ]
    for itm in items:
        f = itm.get("facts", {})
        d = itm.get("derived", {})
        lines.append(f"### {f.get('display_name', itm['slug'])} ({itm['entity_id']})")
        lines.append(f"Slug: {itm['slug']}")
        lines.append(f"Stack Size: {f.get('stack_size', 64)}")
        if "durability" in f:
            lines.append(f"Durability: {f['durability']}")
        if "mining_tier" in f:
            lines.append(f"Mining Tier: {f['mining_tier']}")
        if d.get("crafted_from_recipes"):
            lines.append(f"Crafted From: {', '.join(d['crafted_from_recipes'])}")
        if d.get("used_in_recipes"):
            lines.append(f"Used In Recipes: {', '.join(d['used_in_recipes'])}")
        if d.get("can_mine_blocks"):
            lines.append(f"Can Mine Blocks: {', '.join(d['can_mine_blocks'])}")
        lines.append("")

    lines.append("---\n## BLOCKS\n")
    for blk in blocks:
        f = blk.get("facts", {})
        d = blk.get("derived", {})
        lines.append(f"### {f.get('display_name', blk['slug'])} ({blk['entity_id']})")
        lines.append(f"Slug: {blk['slug']}")
        lines.append(f"Hardness: {f.get('hardness')} | Resistance: {f.get('resistance')}")
        lines.append(f"Tool Required: {f.get('tool_required')}")
        if d.get("harvest_tools"):
            lines.append(f"Harvest Tools: {', '.join(d['harvest_tools'])}")
        lines.append("")

    return "\n".join(lines)


# ---------------- SITEMAP & CRAWLER ROUTES ----------------

@minecraft_router.get("/robots.txt", response_class=PlainTextResponse)
@minecraft_router.head("/robots.txt")
async def minecraft_robots_txt():
    """Standard crawl directives and sitemap declarations for Minecraft subdomain."""
    return PlainTextResponse(
        """# Allow standard search engines & AI Knowledge Engines
User-agent: Googlebot
User-agent: Bingbot
User-agent: YandexBot
User-agent: Slurp
User-agent: DuckDuckBot
User-agent: GPTBot
User-agent: ChatGPT-User
User-agent: OAI-SearchBot
User-agent: Anthropic-AI
User-agent: Claude-Web
User-agent: ClaudeBot
User-agent: Claude-SearchBot
User-agent: Claude-User
User-agent: PerplexityBot
User-agent: Perplexity-User
User-agent: CCBot
User-agent: cohere-ai
User-agent: Applebot
User-agent: Applebot-Extended
User-agent: Amazonbot
User-agent: ByteSpider
User-agent: Meta-ExternalAgent
User-agent: FacebookBot
Allow: /

# Block aggressive SEO backlink scrapers
User-agent: AhrefsBot
User-agent: SemrushBot
User-agent: DotBot
User-agent: Rogerbot
User-agent: MJ12bot
Disallow: /

# Allow all other visitors & polite bots
User-agent: *
Allow: /
Disallow: /api/

Sitemap: https://minecraft.avascry.com/sitemap.xml
Sitemap: https://minecraft.avascry.com/sitemap.html
Sitemap: https://minecraft.avascry.com/sitemap.md
""",
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=86400, stale-while-revalidate=604800"}
    )


@minecraft_router.get("/sitemap.xml")
async def minecraft_sitemap_xml():
    db = get_minecraft_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    items = list(db.items.find({"edition": EDITION, "version": VERSION}, {"slug": 1}))
    blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION}, {"slug": 1}))
    recipes = list(db.recipes.find({"edition": EDITION, "version": VERSION}, {"slug": 1}))
    entities = list(db.entities.find({"edition": EDITION, "version": VERSION}, {"slug": 1}))

    urls = [
        f'  <url><loc>https://minecraft.avascry.com/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/items</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/blocks</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/recipes</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/entities</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/sitemap.html</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/sitemap.md</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/llms.txt</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/llms-full.txt</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/about</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/contact</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/privacy</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.3</priority></url>',
        f'  <url><loc>https://minecraft.avascry.com/terms</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.3</priority></url>',
    ]

    for itm in items:
        slug = itm["slug"]
        urls.append(f'  <url><loc>https://minecraft.avascry.com/item/{slug}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
        urls.append(f'  <url><loc>https://minecraft.avascry.com/item/{slug}.md</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
        urls.append(f'  <url><loc>https://minecraft.avascry.com/item/{slug}.json</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')

    for blk in blocks:
        slug = blk["slug"]
        urls.append(f'  <url><loc>https://minecraft.avascry.com/block/{slug}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
        urls.append(f'  <url><loc>https://minecraft.avascry.com/block/{slug}.md</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
        urls.append(f'  <url><loc>https://minecraft.avascry.com/block/{slug}.json</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '\n'.join(urls)
    xml += '\n</urlset>'
    return Response(content=xml, media_type="application/xml")


@minecraft_router.get("/sitemap.html", response_class=HTMLResponse)
async def minecraft_sitemap_html(request: Request):
    db = get_minecraft_db()
    items = list(db.items.find({"edition": EDITION, "version": VERSION}, {"_id": 0}).sort("entity_id", 1))
    blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION}, {"_id": 0}).sort("entity_id", 1))
    recipes = list(db.recipes.find({"edition": EDITION, "version": VERSION}, {"_id": 0}).sort("entity_id", 1))
    entities = list(db.entities.find({"edition": EDITION, "version": VERSION}, {"_id": 0}).sort("entity_id", 1))

    return templates.TemplateResponse(
        request=request,
        name="minecraft/sitemap.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "items": items,
            "blocks": blocks,
            "recipes": recipes,
            "entities": entities
        }
    )


@minecraft_router.get("/sitemap.md", response_class=PlainTextResponse)
async def minecraft_sitemap_md():
    db = get_minecraft_db()
    items = list(db.items.find({"edition": EDITION, "version": VERSION}, {"slug": 1, "facts.display_name": 1}).sort("entity_id", 1))
    blocks = list(db.blocks.find({"edition": EDITION, "version": VERSION}, {"slug": 1, "facts.display_name": 1}).sort("entity_id", 1))
    recipes = list(db.recipes.find({"edition": EDITION, "version": VERSION}, {"slug": 1}).sort("entity_id", 1))
    entities = list(db.entities.find({"edition": EDITION, "version": VERSION}, {"slug": 1, "facts.display_name": 1}).sort("entity_id", 1))

    lines = [
        f"# AvaScry Minecraft — Sitemap & Knowledge Directory (Markdown)",
        f"",
        f"> Java Edition {VERSION} Vanilla Data Atlas index linking all entities and machine formats.",
        f"",
        f"## Core Manifests & Indexes",
        f"- [Atlas Home](https://minecraft.avascry.com/)",
        f"- [HTML Sitemap](https://minecraft.avascry.com/sitemap.html)",
        f"- [XML Sitemap](https://minecraft.avascry.com/sitemap.xml)",
        f"- [Agent LLM Manifest (`/llms.txt`)](https://minecraft.avascry.com/llms.txt)",
        f"- [Full Knowledge Corpus (`/llms-full.txt`)](https://minecraft.avascry.com/llms-full.txt)",
        f"",
        f"## Items ({len(items)})",
    ]
    for itm in items:
        name = itm.get("facts", {}).get("display_name", itm["slug"])
        slug = itm["slug"]
        lines.append(f"- [{name}](https://minecraft.avascry.com/item/{slug}) • [MD](https://minecraft.avascry.com/item/{slug}.md) • [JSON](https://minecraft.avascry.com/item/{slug}.json)")

    lines.append(f"\n## Blocks ({len(blocks)})")
    for blk in blocks:
        name = blk.get("facts", {}).get("display_name", blk["slug"])
        slug = blk["slug"]
        lines.append(f"- [{name}](https://minecraft.avascry.com/block/{slug}) • [MD](https://minecraft.avascry.com/block/{slug}.md) • [JSON](https://minecraft.avascry.com/block/{slug}.json)")

    lines.append(f"\n## Recipes ({len(recipes)})")
    for r in recipes:
        slug = r["slug"]
        lines.append(f"- [{slug}](https://minecraft.avascry.com/recipe/{slug}) • [MD](https://minecraft.avascry.com/recipe/{slug}.md) • [JSON](https://minecraft.avascry.com/recipe/{slug}.json)")

    lines.append(f"\n## Entities ({len(entities)})")
    for ent in entities:
        name = ent.get("facts", {}).get("display_name", ent["slug"])
        slug = ent["slug"]
        lines.append(f"- [{name}](https://minecraft.avascry.com/entity/{slug}) • [MD](https://minecraft.avascry.com/entity/{slug}.md) • [JSON](https://minecraft.avascry.com/entity/{slug}.json)")

    return "\n".join(lines)


# ---------------- SEARCH & API ROUTES ----------------

@minecraft_router.get("/api/search")
async def minecraft_api_search(q: str = ""):
    """Lightweight search endpoint across items, blocks, recipes, and entities."""
    query = q.strip()
    if not query:
        return JSONResponse({"results": []})

    db = get_minecraft_db()
    regex = {"$regex": query, "$options": "i"}
    results = []

    # Search items
    items = list(db.items.find(
        {"edition": EDITION, "version": VERSION, "$or": [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]},
        {"_id": 0, "slug": 1, "entity_id": 1, "facts.display_name": 1, "facts.image_url": 1}
    ).limit(8))
    for itm in items:
        results.append({
            "type": "item",
            "name": itm.get("facts", {}).get("display_name", itm["slug"]),
            "slug": itm["slug"],
            "id": itm["entity_id"],
            "image": itm.get("facts", {}).get("image_url"),
            "url": f"/item/{itm['slug']}"
        })

    # Search blocks
    blocks = list(db.blocks.find(
        {"edition": EDITION, "version": VERSION, "$or": [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]},
        {"_id": 0, "slug": 1, "entity_id": 1, "facts.display_name": 1, "facts.image_url": 1}
    ).limit(8))
    for blk in blocks:
        results.append({
            "type": "block",
            "name": blk.get("facts", {}).get("display_name", blk["slug"]),
            "slug": blk["slug"],
            "id": blk["entity_id"],
            "image": blk.get("facts", {}).get("image_url"),
            "url": f"/block/{blk['slug']}"
        })

    # Search entities
    entities = list(db.entities.find(
        {"edition": EDITION, "version": VERSION, "$or": [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]},
        {"_id": 0, "slug": 1, "entity_id": 1, "facts.display_name": 1}
    ).limit(6))
    for ent in entities:
        results.append({
            "type": "entity",
            "name": ent.get("facts", {}).get("display_name", ent["slug"]),
            "slug": ent["slug"],
            "id": ent["entity_id"],
            "url": f"/entity/{ent['slug']}"
        })

    return JSONResponse({"results": results[:20]})


# ---------------- ITEM ROUTES ----------------

@minecraft_router.get("/items", response_class=HTMLResponse)
async def minecraft_items_list(
    request: Request, 
    q: str = "", 
    category: str = "", 
    has_durability: str = "", 
    stack_size: str = "", 
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}

    # Text search filter
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    # Category / Class facet
    if category == "tools":
        query_filter["$or"] = [
            {"slug": {"$regex": "pickaxe|axe|shovel|hoe|shears|fishing_rod|flint_and_steel"}},
            {"entity_id": {"$regex": "pickaxe|axe|shovel|hoe|shears|fishing_rod|flint_and_steel"}}
        ]
    elif category == "weapons":
        query_filter["$or"] = [
            {"slug": {"$regex": "sword|bow|crossbow|trident|mace"}},
            {"entity_id": {"$regex": "sword|bow|crossbow|trident|mace"}}
        ]
    elif category == "armor":
        query_filter["$or"] = [
            {"slug": {"$regex": "helmet|chestplate|leggings|boots|shield|elytra"}},
            {"entity_id": {"$regex": "helmet|chestplate|leggings|boots|shield|elytra"}}
        ]
    elif category == "ores":
        query_filter["$or"] = [
            {"slug": {"$regex": "ore|raw_|ingot|nugget|diamond|emerald|netherite|quartz|amethyst|lapis"}},
            {"entity_id": {"$regex": "ore|raw_|ingot|nugget|diamond|emerald|netherite|quartz|amethyst|lapis"}}
        ]
    elif category == "food":
        query_filter["$or"] = [
            {"slug": {"$regex": "apple|beef|porkchop|mutton|chicken|bread|carrot|potato|stew|soup|cookie|pie|berries|melon"}},
            {"entity_id": {"$regex": "apple|beef|porkchop|mutton|chicken|bread|carrot|potato|stew|soup|cookie|pie|berries|melon"}}
        ]
    elif category == "redstone":
        query_filter["$or"] = [
            {"slug": {"$regex": "redstone|piston|repeater|comparator|observer|dropper|dispenser|hopper|lever|button|rail"}},
            {"entity_id": {"$regex": "redstone|piston|repeater|comparator|observer|dropper|dispenser|hopper|lever|button|rail"}}
        ]

    # Durability facet
    if has_durability == "yes":
        query_filter["facts.durability"] = {"$ne": None, "$gt": 0}
    elif has_durability == "no":
        query_filter["facts.durability"] = None

    # Stack size facet
    if stack_size:
        try:
            query_filter["facts.stack_size"] = int(stack_size)
        except ValueError:
            pass

    # Sort criteria
    sort_criteria = [("facts.display_name", 1)]
    if sort == "name_desc":
        sort_criteria = [("facts.display_name", -1)]
    elif sort == "durability_desc":
        sort_criteria = [("facts.durability", -1), ("facts.display_name", 1)]
    elif sort == "durability_asc":
        sort_criteria = [("facts.durability", 1), ("facts.display_name", 1)]
    elif sort == "stack_desc":
        sort_criteria = [("facts.stack_size", -1), ("facts.display_name", 1)]

    # Pagination calculation
    limit = max(12, min(96, limit))
    page = max(1, page)
    total_matching = db.items.count_documents(query_filter)
    total_pages = max(1, (total_matching + limit - 1) // limit)
    if page > total_pages:
        page = total_pages
    skip = (page - 1) * limit

    items = list(db.items.find(query_filter, {"_id": 0}).sort(sort_criteria).skip(skip).limit(limit))
    total_unfiltered = db.items.count_documents({"edition": EDITION, "version": VERSION})

    is_filtered = bool(q.strip() or category or has_durability or stack_size or sort != "name_asc")

    return templates.TemplateResponse(
        request=request,
        name="minecraft/list.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "title": "Minecraft Items & Tools",
            "description": "Vanilla item registry with durability, stack limits, and reciprocal recipes.",
            "entries": items,
            "total": total_unfiltered,
            "total_matching": total_matching,
            "current_page": page,
            "total_pages": total_pages,
            "limit": limit,
            "is_filtered": is_filtered,
            "query": q,
            "category": category,
            "has_durability": has_durability,
            "stack_size": stack_size,
            "sort": sort,
            "item_type": "item"
        }
    )


@minecraft_router.get("/items.json")
async def minecraft_items_json(
    q: str = "",
    category: str = "",
    has_durability: str = "",
    stack_size: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    if category == "tools":
        query_filter["$or"] = [
            {"slug": {"$regex": "pickaxe|axe|shovel|hoe|shears|fishing_rod|flint_and_steel"}},
            {"entity_id": {"$regex": "pickaxe|axe|shovel|hoe|shears|fishing_rod|flint_and_steel"}}
        ]
    elif category == "weapons":
        query_filter["$or"] = [
            {"slug": {"$regex": "sword|bow|crossbow|trident|mace"}},
            {"entity_id": {"$regex": "sword|bow|crossbow|trident|mace"}}
        ]
    elif category == "armor":
        query_filter["$or"] = [
            {"slug": {"$regex": "helmet|chestplate|leggings|boots|shield|elytra"}},
            {"entity_id": {"$regex": "helmet|chestplate|leggings|boots|shield|elytra"}}
        ]
    elif category == "ores":
        query_filter["$or"] = [
            {"slug": {"$regex": "ore|raw_|ingot|nugget|diamond|emerald|netherite|quartz|amethyst|lapis"}},
            {"entity_id": {"$regex": "ore|raw_|ingot|nugget|diamond|emerald|netherite|quartz|amethyst|lapis"}}
        ]
    elif category == "food":
        query_filter["$or"] = [
            {"slug": {"$regex": "apple|beef|porkchop|mutton|chicken|bread|carrot|potato|stew|soup|cookie|pie|berries|melon"}},
            {"entity_id": {"$regex": "apple|beef|porkchop|mutton|chicken|bread|carrot|potato|stew|soup|cookie|pie|berries|melon"}}
        ]
    elif category == "redstone":
        query_filter["$or"] = [
            {"slug": {"$regex": "redstone|piston|repeater|comparator|observer|dropper|dispenser|hopper|lever|button|rail"}},
            {"entity_id": {"$regex": "redstone|piston|repeater|comparator|observer|dropper|dispenser|hopper|lever|button|rail"}}
        ]

    if has_durability == "yes":
        query_filter["facts.durability"] = {"$ne": None, "$gt": 0}
    elif has_durability == "no":
        query_filter["facts.durability"] = None

    if stack_size:
        try:
            query_filter["facts.stack_size"] = int(stack_size)
        except ValueError:
            pass

    sort_criteria = [("facts.display_name", 1)]
    if sort == "name_desc":
        sort_criteria = [("facts.display_name", -1)]
    elif sort == "durability_desc":
        sort_criteria = [("facts.durability", -1), ("facts.display_name", 1)]
    elif sort == "durability_asc":
        sort_criteria = [("facts.durability", 1), ("facts.display_name", 1)]
    elif sort == "stack_desc":
        sort_criteria = [("facts.stack_size", -1), ("facts.display_name", 1)]

    limit = max(12, min(96, limit))
    page = max(1, page)
    total_matching = db.items.count_documents(query_filter)
    total_pages = max(1, (total_matching + limit - 1) // limit)
    if page > total_pages:
        page = total_pages
    skip = (page - 1) * limit

    items = list(db.items.find(query_filter, {"_id": 0}).sort(sort_criteria).skip(skip).limit(limit))
    return JSONResponse({
        "edition": EDITION,
        "version": VERSION,
        "category": "items",
        "page": page,
        "limit": limit,
        "total_matching": total_matching,
        "total_pages": total_pages,
        "entries": items
    })


@minecraft_router.get("/items.md", response_class=PlainTextResponse)
async def minecraft_items_md(
    q: str = "",
    category: str = "",
    has_durability: str = "",
    stack_size: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    json_resp = await minecraft_items_json(q=q, category=category, has_durability=has_durability, stack_size=stack_size, sort=sort, page=page, limit=limit)
    import json as pyjson
    data = pyjson.loads(json_resp.body.decode("utf-8"))
    
    lines = [
        f"# Minecraft Java {VERSION} - Items & Tools Catalog",
        f"Page {data['page']} of {data['total_pages']} (Total Matching: {data['total_matching']})\n",
        "| Name | Entity ID | Durability | Stack Size | Link |",
        "| --- | --- | --- | --- | --- |"
    ]
    for it in data["entries"]:
        f = it.get("facts", {})
        name = f.get("display_name", it["slug"])
        eid = it.get("entity_id", "")
        dur = f.get("durability") or "N/A"
        stk = f.get("stack_size", 64)
        url = f"https://minecraft.avascry.com/item/{it['slug']}"
        lines.append(f"| {name} | `{eid}` | {dur} | {stk} | [{it['slug']}]({url}) |")

    return "\n".join(lines)



def hydrate_neighbors(db, neighbors_list: list, default_type: str = "item") -> list:
    """Hydrate neighbor slugs with display names, images, and formatted percentage scores."""
    if not neighbors_list:
        return []
    slugs = [n.get("slug") for n in neighbors_list if n.get("slug")]
    if not slugs:
        return []
    
    # Query items and blocks in bulk
    items_map = {
        doc["slug"]: doc.get("facts", {})
        for doc in db.items.find({"slug": {"$in": slugs}}, {"slug": 1, "facts.display_name": 1, "facts.image_url": 1})
    }
    blocks_map = {
        doc["slug"]: doc.get("facts", {})
        for doc in db.blocks.find({"slug": {"$in": slugs}}, {"slug": 1, "facts.display_name": 1, "facts.image_url": 1})
    }

    hydrated = []
    for n in neighbors_list:
        s = n.get("slug")
        if not s:
            continue
        n_type = n.get("type", default_type)
        score = n.get("score", 0.0)
        pct = int(round(score * 100)) if score <= 1.0 else int(round(score))
        facts = (blocks_map.get(s) if n_type == "block" else (items_map.get(s) or blocks_map.get(s))) or {}
        display_name = facts.get("display_name") or s.replace("-", " ").title()
        image_url = facts.get("image_url")
        hydrated.append({
            "slug": s,
            "type": n_type,
            "score": score,
            "score_pct": pct,
            "display_name": display_name,
            "image_url": image_url
        })
    return hydrated


@minecraft_router.get("/item/{slug}.json")
async def minecraft_item_json(slug: str):
    db = get_minecraft_db()
    item = db.items.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not item:
        norm_slug = normalize_mc_slug(slug)
        if norm_slug != slug:
            item = db.items.find_one({"edition": EDITION, "version": VERSION, "slug": norm_slug}, {"_id": 0})
            if item:
                slug = norm_slug
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    func_rec = db.similar_functional.find_one({"slug": slug}, {"neighbors": 1})
    palette_rec = db.palette_neighbors.find_one({"slug": slug}, {"palette_matches": 1})
    graph_rec = db.graph_neighbors.find_one({"slug": slug}, {"progression_neighbors": 1})

    item["embeddings"] = {
        "functional_substitutes": func_rec.get("neighbors", [])[:8] if func_rec else [],
        "palette_matches": palette_rec.get("palette_matches", [])[:8] if palette_rec else [],
        "progression_neighbors": graph_rec.get("progression_neighbors", [])[:8] if graph_rec else []
    }
    return JSONResponse(item)


@minecraft_router.get("/item/{slug}.md", response_class=PlainTextResponse)
async def minecraft_item_md(slug: str):
    db = get_minecraft_db()
    item = db.items.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not item:
        norm_slug = normalize_mc_slug(slug)
        if norm_slug != slug:
            item = db.items.find_one({"edition": EDITION, "version": VERSION, "slug": norm_slug}, {"_id": 0})
            if item:
                slug = norm_slug
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    func_rec = db.similar_functional.find_one({"slug": slug}, {"neighbors": 1})
    similar_items = func_rec.get("neighbors", [])[:6] if func_rec else []

    palette_rec = db.palette_neighbors.find_one({"slug": slug}, {"palette_matches": 1})
    palette_matches = palette_rec.get("palette_matches", [])[:6] if palette_rec else []

    graph_rec = db.graph_neighbors.find_one({"slug": slug}, {"progression_neighbors": 1})
    progression_matches = graph_rec.get("progression_neighbors", [])[:6] if graph_rec else []

    f = item.get("facts", {})
    d = item.get("derived", {})
    md = f"""---
title: "{f.get('display_name')} - Minecraft Java {VERSION}"
slug: "{item['slug']}"
entity_id: "{item['entity_id']}"
edition: "{item['edition']}"
version: "{item['version']}"
stack_size: {f.get('stack_size', 64)}
durability: {f.get('durability', 'null')}
mining_tier: "{f.get('mining_tier', '')}"
tags: {json.dumps(f.get('tags', []))}
canonical_url: "https://minecraft.avascry.com/item/{slug}"
---

# {f.get('display_name')}

**Namespaced ID:** `{item['entity_id']}`  
**Edition:** {item['edition']} &bull; **Version:** {item['version']} ({item['version_type']})

## Properties
- **Stack Size:** {f.get('stack_size', 64)}
- **Durability:** {f.get('durability', 'N/A')}
- **Mining Tier:** {f.get('mining_tier', 'N/A')}

## Reciprocal Graph Relations
- **Crafted From:** {', '.join([f'[{r}](/recipe/{slugify(r)})' for r in d.get('crafted_from_recipes', [])]) or 'None'}
- **Used In Recipes:** {', '.join([f'[{r}](/recipe/{slugify(r)})' for r in d.get('used_in_recipes', [])]) or 'None'}
- **Can Harvest Blocks:** {', '.join([f'[{b}](/block/{slugify(b)})' for b in d.get('can_mine_blocks', [])]) or 'None'}
- **Dropped By Blocks:** {', '.join([f'[{b}](/block/{slugify(b)})' for b in d.get('dropped_by_blocks', [])]) or 'None'}
- **Dropped By Entities:** {', '.join([f'[{e}](/entity/{slugify(e)})' for e in d.get('dropped_by_entities', [])]) or 'None'}
- **Compatible Enchantments:** {', '.join(d.get('compatible_enchantments', [])) or 'None'}
"""
    if similar_items:
        md += "\n## Functional Substitutes & Alternatives (Vector Mechanics)\n"
        for s in similar_items:
            md += f"- [{s['slug']}](/item/{s['slug']}) — affinity: {s['score']}\n"

    if palette_matches:
        md += "\n## Building Palette & Aesthetic Matches\n"
        for p in palette_matches:
            md += f"- [{p['slug']}](/block/{p['slug']}) — palette harmony: {p['score']}\n"

    if progression_matches:
        md += "\n## Crafting Progression & Tech Tree Neighbors\n"
        for g in progression_matches:
            md += f"- [{g['slug']}](/item/{g['slug']}) — tech tier depth: {g['score']}\n"

    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@minecraft_router.get("/item/{slug}", response_class=HTMLResponse)
async def minecraft_item_detail(request: Request, slug: str):
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return await minecraft_item_json(slug)
    if "text/markdown" in accept and "text/html" not in accept:
        return await minecraft_item_md(slug)

    db = get_minecraft_db()
    item = db.items.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not item:
        norm_slug = normalize_mc_slug(slug)
        if norm_slug != slug:
            item = db.items.find_one({"edition": EDITION, "version": VERSION, "slug": norm_slug}, {"_id": 0})
            if item:
                slug = norm_slug
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Fetch embedding neighbors with visual hydration
    func_rec = db.similar_functional.find_one({"slug": slug}, {"neighbors": 1})
    similar_items = hydrate_neighbors(db, func_rec.get("neighbors", [])[:8], default_type="item") if func_rec else []

    palette_rec = db.palette_neighbors.find_one({"slug": slug}, {"palette_matches": 1})
    palette_matches = hydrate_neighbors(db, palette_rec.get("palette_matches", [])[:8], default_type="block") if palette_rec else []

    graph_rec = db.graph_neighbors.find_one({"slug": slug}, {"progression_neighbors": 1})
    progression_matches = hydrate_neighbors(db, graph_rec.get("progression_neighbors", [])[:8], default_type="item") if graph_rec else []

    # If this item is also a block, fetch corresponding block data for stats
    block_counterpart = db.blocks.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0, "facts": 1})

    return templates.TemplateResponse(
        request=request,
        name="minecraft/item.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "item": item,
            "similar_items": similar_items,
            "palette_matches": palette_matches,
            "progression_matches": progression_matches,
            "block_counterpart": block_counterpart
        }
    )


# ---------------- BLOCK ROUTES ----------------

@minecraft_router.get("/blocks", response_class=HTMLResponse)
async def minecraft_blocks_list(
    request: Request, 
    q: str = "", 
    material: str = "",
    tool_required: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    if material:
        query_filter["facts.material"] = {"$regex": material, "$options": "i"}

    if tool_required == "yes":
        query_filter["facts.tool_required"] = True
    elif tool_required == "no":
        query_filter["facts.tool_required"] = False

    sort_criteria = [("facts.display_name", 1)]
    if sort == "name_desc":
        sort_criteria = [("facts.display_name", -1)]
    elif sort == "hardness_desc":
        sort_criteria = [("facts.hardness", -1), ("facts.display_name", 1)]
    elif sort == "hardness_asc":
        sort_criteria = [("facts.hardness", 1), ("facts.display_name", 1)]

    limit = max(12, min(96, limit))
    page = max(1, page)
    total_matching = db.blocks.count_documents(query_filter)
    total_pages = max(1, (total_matching + limit - 1) // limit)
    if page > total_pages:
        page = total_pages
    skip = (page - 1) * limit

    blocks = list(db.blocks.find(query_filter, {"_id": 0}).sort(sort_criteria).skip(skip).limit(limit))
    total_unfiltered = db.blocks.count_documents({"edition": EDITION, "version": VERSION})
    is_filtered = bool(q.strip() or material or tool_required or sort != "name_asc")

    return templates.TemplateResponse(
        request=request,
        name="minecraft/list.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "title": "Minecraft Blocks & Mining",
            "description": "Block hardness, blast resistance, tool harvest tier requirements, and loot tables.",
            "entries": blocks,
            "total": total_unfiltered,
            "total_matching": total_matching,
            "current_page": page,
            "total_pages": total_pages,
            "limit": limit,
            "is_filtered": is_filtered,
            "query": q,
            "material": material,
            "tool_required": tool_required,
            "sort": sort,
            "item_type": "block"
        }
    )


@minecraft_router.get("/blocks.json")
async def minecraft_blocks_json(
    q: str = "",
    material: str = "",
    tool_required: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    if material:
        query_filter["facts.material"] = {"$regex": material, "$options": "i"}

    if tool_required == "yes":
        query_filter["facts.tool_required"] = True
    elif tool_required == "no":
        query_filter["facts.tool_required"] = False

    sort_criteria = [("facts.display_name", 1)]
    if sort == "name_desc":
        sort_criteria = [("facts.display_name", -1)]
    elif sort == "hardness_desc":
        sort_criteria = [("facts.hardness", -1), ("facts.display_name", 1)]
    elif sort == "hardness_asc":
        sort_criteria = [("facts.hardness", 1), ("facts.display_name", 1)]

    limit = max(12, min(96, limit))
    page = max(1, page)
    total_matching = db.blocks.count_documents(query_filter)
    total_pages = max(1, (total_matching + limit - 1) // limit)
    if page > total_pages:
        page = total_pages
    skip = (page - 1) * limit

    blocks = list(db.blocks.find(query_filter, {"_id": 0}).sort(sort_criteria).skip(skip).limit(limit))
    return JSONResponse({
        "edition": EDITION,
        "version": VERSION,
        "category": "blocks",
        "page": page,
        "limit": limit,
        "total_matching": total_matching,
        "total_pages": total_pages,
        "entries": blocks
    })


@minecraft_router.get("/blocks.md", response_class=PlainTextResponse)
async def minecraft_blocks_md(
    q: str = "",
    material: str = "",
    tool_required: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    json_resp = await minecraft_blocks_json(q=q, material=material, tool_required=tool_required, sort=sort, page=page, limit=limit)
    import json as pyjson
    data = pyjson.loads(json_resp.body.decode("utf-8"))

    lines = [
        f"# Minecraft Java {VERSION} - Blocks Catalog",
        f"Page {data['page']} of {data['total_pages']} (Total Matching: {data['total_matching']})\n",
        "| Name | Entity ID | Hardness | Resistance | Tool Required | Link |",
        "| --- | --- | --- | --- | --- | --- |"
    ]
    for blk in data["entries"]:
        f = blk.get("facts", {})
        name = f.get("display_name", blk["slug"])
        eid = blk.get("entity_id", "")
        h = f.get("hardness") if f.get("hardness") is not None else "N/A"
        r = f.get("resistance") if f.get("resistance") is not None else "N/A"
        tr = "Yes" if f.get("tool_required") else "No"
        url = f"https://minecraft.avascry.com/block/{blk['slug']}"
        lines.append(f"| {name} | `{eid}` | {h} | {r} | {tr} | [{blk['slug']}]({url}) |")

    return "\n".join(lines)



@minecraft_router.get("/block/{slug}.json")
async def minecraft_block_json(slug: str):
    db = get_minecraft_db()
    block_data = db.blocks.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not block_data:
        raise HTTPException(status_code=404, detail="Block not found")

    palette_rec = db.palette_neighbors.find_one({"slug": slug}, {"palette_matches": 1})
    func_rec = db.similar_functional.find_one({"slug": slug}, {"neighbors": 1})
    graph_rec = db.graph_neighbors.find_one({"slug": slug}, {"progression_neighbors": 1})

    block_data["embeddings"] = {
        "palette_matches": palette_rec.get("palette_matches", [])[:8] if palette_rec else [],
        "functional_substitutes": func_rec.get("neighbors", [])[:8] if func_rec else [],
        "progression_neighbors": graph_rec.get("progression_neighbors", [])[:8] if graph_rec else []
    }
    return JSONResponse(block_data)


@minecraft_router.get("/block/{slug}.md", response_class=PlainTextResponse)
async def minecraft_block_md(slug: str):
    db = get_minecraft_db()
    block_data = db.blocks.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not block_data:
        raise HTTPException(status_code=404, detail="Block not found")

    palette_rec = db.palette_neighbors.find_one({"slug": slug}, {"palette_matches": 1})
    palette_matches = palette_rec.get("palette_matches", [])[:6] if palette_rec else []

    func_rec = db.similar_functional.find_one({"slug": slug}, {"neighbors": 1})
    similar_items = func_rec.get("neighbors", [])[:6] if func_rec else []

    graph_rec = db.graph_neighbors.find_one({"slug": slug}, {"progression_neighbors": 1})
    progression_matches = graph_rec.get("progression_neighbors", [])[:6] if graph_rec else []

    f = block_data.get("facts", {})
    d = block_data.get("derived", {})
    md = f"""---
title: "{f.get('display_name')} - Minecraft Java {VERSION}"
slug: "{block_data['slug']}"
entity_id: "{block_data['entity_id']}"
edition: "{block_data['edition']}"
version: "{block_data['version']}"
hardness: {f.get('hardness')}
resistance: {f.get('resistance')}
tool_required: {str(f.get('tool_required')).lower()}
tags: {json.dumps(f.get('tags', []))}
canonical_url: "https://minecraft.avascry.com/block/{slug}"
---

# {f.get('display_name')}

**Namespaced ID:** `{block_data['entity_id']}`  
**Edition:** {block_data['edition']} &bull; **Version:** {block_data['version']}

## Mechanics
- **Hardness:** {f.get('hardness')}
- **Blast Resistance:** {f.get('resistance')}
- **Tool Required:** {'Yes' if f.get('tool_required') else 'No'}

## Harvest Tools
{', '.join([f'[{t}](/item/{slugify(t)})' for t in d.get('harvest_tools', [])]) or 'Any'}

## Drops Summary (Compiled AST)
"""
    for drop in d.get("drops_summary", []):
        md += f"- **Target:** `{drop['target_id']}` | Count: {drop['min']} - {drop['max']} | Conditions: {', '.join(drop.get('conditions', []))}\n"

    if palette_matches:
        md += "\n## Building Palette & Aesthetic Matches\n"
        for p in palette_matches:
            md += f"- [{p['slug']}](/block/{p['slug']}) — palette harmony: {p['score']}\n"

    if similar_items:
        md += "\n## Related & Functional Alternatives\n"
        for s in similar_items:
            md += f"- [{s['slug']}](/block/{s['slug']}) — affinity: {s['score']}\n"

    if progression_matches:
        md += "\n## Crafting Progression & Tech Tree Neighbors\n"
        for g in progression_matches:
            md += f"- [{g['slug']}](/block/{g['slug']}) — tech tier depth: {g['score']}\n"

    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@minecraft_router.get("/block/{slug}", response_class=HTMLResponse)
async def minecraft_block_detail(request: Request, slug: str):
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return await minecraft_block_json(slug)
    if "text/markdown" in accept and "text/html" not in accept:
        return await minecraft_block_md(slug)

    db = get_minecraft_db()
    block_data = db.blocks.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not block_data:
        raise HTTPException(status_code=404, detail="Block not found")

    # Fetch embedding neighbors with visual hydration
    palette_rec = db.palette_neighbors.find_one({"slug": slug}, {"palette_matches": 1})
    palette_matches = hydrate_neighbors(db, palette_rec.get("palette_matches", [])[:8], default_type="block") if palette_rec else []

    func_rec = db.similar_functional.find_one({"slug": slug}, {"neighbors": 1})
    similar_items = hydrate_neighbors(db, func_rec.get("neighbors", [])[:8], default_type="block") if func_rec else []

    graph_rec = db.graph_neighbors.find_one({"slug": slug}, {"progression_neighbors": 1})
    progression_matches = hydrate_neighbors(db, graph_rec.get("progression_neighbors", [])[:8], default_type="block") if graph_rec else []

    # Check if item counterpart exists
    item_counterpart = db.items.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0, "facts": 1, "derived": 1})

    return templates.TemplateResponse(
        request=request,
        name="minecraft/block.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "block_data": block_data,
            "palette_matches": palette_matches,
            "similar_items": similar_items,
            "progression_matches": progression_matches,
            "item_counterpart": item_counterpart
        }
    )


# ---------------- RECIPE ROUTES ----------------

@minecraft_router.get("/recipes", response_class=HTMLResponse)
async def minecraft_recipes_list(
    request: Request, 
    q: str = "", 
    recipe_type: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"derived.output_item": regex}]

    if recipe_type:
        query_filter["type"] = recipe_type

    limit = max(12, min(96, limit))
    page = max(1, page)
    total_matching = db.recipes.count_documents(query_filter)
    total_pages = max(1, (total_matching + limit - 1) // limit)
    if page > total_pages:
        page = total_pages
    skip = (page - 1) * limit

    recipes = list(db.recipes.find(query_filter, {"_id": 0}).sort("entity_id", 1).skip(skip).limit(limit))
    total_unfiltered = db.recipes.count_documents({"edition": EDITION, "version": VERSION})
    is_filtered = bool(q.strip() or recipe_type or sort != "name_asc")

    return templates.TemplateResponse(
        request=request,
        name="minecraft/list.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "title": "Minecraft Recipes",
            "description": "Shaped, shapeless, and smelting crafting matrices with tag substitutions.",
            "entries": recipes,
            "total": total_unfiltered,
            "total_matching": total_matching,
            "current_page": page,
            "total_pages": total_pages,
            "limit": limit,
            "is_filtered": is_filtered,
            "query": q,
            "recipe_type": recipe_type,
            "sort": sort,
            "item_type": "recipe"
        }
    )


@minecraft_router.get("/recipes.json")
async def minecraft_recipes_json(
    q: str = "",
    recipe_type: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"derived.output_item": regex}]

    if recipe_type:
        query_filter["type"] = recipe_type

    limit = max(12, min(96, limit))
    page = max(1, page)
    total_matching = db.recipes.count_documents(query_filter)
    total_pages = max(1, (total_matching + limit - 1) // limit)
    if page > total_pages:
        page = total_pages
    skip = (page - 1) * limit

    recipes = list(db.recipes.find(query_filter, {"_id": 0}).sort("entity_id", 1).skip(skip).limit(limit))
    return JSONResponse({
        "edition": EDITION,
        "version": VERSION,
        "category": "recipes",
        "page": page,
        "limit": limit,
        "total_matching": total_matching,
        "total_pages": total_pages,
        "entries": recipes
    })


@minecraft_router.get("/recipes.md", response_class=PlainTextResponse)
async def minecraft_recipes_md(
    q: str = "",
    recipe_type: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    json_resp = await minecraft_recipes_json(q=q, recipe_type=recipe_type, sort=sort, page=page, limit=limit)
    import json as pyjson
    data = pyjson.loads(json_resp.body.decode("utf-8"))

    lines = [
        f"# Minecraft Java {VERSION} - Recipes Catalog",
        f"Page {data['page']} of {data['total_pages']} (Total Matching: {data['total_matching']})\n",
        "| Recipe Slug | Type | Output Item | Link |",
        "| --- | --- | --- | --- |"
    ]
    for r in data["entries"]:
        rtype = r.get("type", "crafting")
        out = r.get("derived", {}).get("output_item", "N/A")
        url = f"https://minecraft.avascry.com/recipe/{r['slug']}"
        lines.append(f"| {r['slug']} | `{rtype}` | `{out}` | [{r['slug']}]({url}) |")

    return "\n".join(lines)



_RECIPE_NUM_TO_ITEM_CACHE = None

def _get_recipe_num_to_item_map(db):
    global _RECIPE_NUM_TO_ITEM_CACHE
    if _RECIPE_NUM_TO_ITEM_CACHE is not None:
        return _RECIPE_NUM_TO_ITEM_CACHE

    m = {}
    for rec in db.recipes.find({"edition": EDITION, "version": VERSION}, {"facts.raw_recipe": 1, "derived": 1}):
        raw_res = rec.get("facts", {}).get("raw_recipe", {}).get("result")
        out = rec.get("derived", {}).get("output_item")
        if raw_res and isinstance(raw_res, dict) and "id" in raw_res and out:
            m[raw_res["id"]] = out

    for rec in db.recipes.find({"edition": EDITION, "version": VERSION}, {"facts.raw_recipe": 1, "derived": 1}):
        distinct = rec.get("derived", {}).get("distinct_input_items", [])
        raw = rec.get("facts", {}).get("raw_recipe", {})
        if len(distinct) == 1:
            if raw.get("inShape"):
                for row in raw["inShape"]:
                    for cell in row:
                        if cell is not None and cell not in m:
                            m[cell] = distinct[0]
            if raw.get("ingredients"):
                for ing in raw["ingredients"]:
                    if isinstance(ing, int) and ing not in m:
                        m[ing] = distinct[0]

    _RECIPE_NUM_TO_ITEM_CACHE = m
    return m


def compute_ingredient_counts(db, recipe):
    from collections import Counter
    counts = Counter()
    raw = recipe.get("facts", {}).get("raw_recipe", {})
    distinct = recipe.get("derived", {}).get("distinct_input_items", [])
    if not distinct:
        return {}

    num_map = _get_recipe_num_to_item_map(db)

    if raw.get("inShape"):
        for row in raw["inShape"]:
            for cell in row:
                if cell is not None:
                    mapped = num_map.get(cell)
                    if mapped:
                        counts[mapped] += 1
                    elif len(distinct) == 1:
                        counts[distinct[0]] += 1
    elif raw.get("ingredients"):
        for ing in raw["ingredients"]:
            if isinstance(ing, int):
                mapped = num_map.get(ing)
                if mapped:
                    counts[mapped] += 1
                elif len(distinct) == 1:
                    counts[distinct[0]] += 1
            elif isinstance(ing, list):
                found = False
                for sub in ing:
                    mapped = num_map.get(sub)
                    if mapped:
                        counts[mapped] += 1
                        found = True
                        break
                if not found and len(distinct) == 1:
                    counts[distinct[0]] += 1

    for d in distinct:
        if counts[d] == 0:
            counts[d] = 1

    return dict(counts)


def build_crafting_matrix(db, recipe, items_by_id):
    raw = recipe.get("facts", {}).get("raw_recipe", {})
    distinct = recipe.get("derived", {}).get("distinct_input_items", [])
    num_map = _get_recipe_num_to_item_map(db)

    # 3x3 slot grid
    grid = [[None, None, None], [None, None, None], [None, None, None]]
    in_shape = raw.get("inShape")

    if in_shape and isinstance(in_shape, list):
        for r_idx, row in enumerate(in_shape[:3]):
            if isinstance(row, list):
                for c_idx, cell in enumerate(row[:3]):
                    if cell is not None:
                        item_id = num_map.get(cell) or (distinct[0] if len(distinct) == 1 else None)
                        if item_id:
                            doc = items_by_id.get(item_id, {})
                            raw_slug = doc.get("slug")
                            clean_slug = raw_slug if raw_slug else slugify(item_id.split(":")[-1])
                            grid[r_idx][c_idx] = {
                                "entity_id": item_id,
                                "slug": clean_slug,
                                "display_name": doc.get("facts", {}).get("display_name") or human_name(item_id),
                                "image_url": doc.get("facts", {}).get("image_url")
                            }
    elif raw.get("ingredients") and isinstance(raw["ingredients"], list):
        idx = 0
        for ing in raw["ingredients"]:
            if idx < 9:
                r_idx, c_idx = divmod(idx, 3)
                num = ing if isinstance(ing, int) else (ing[0] if isinstance(ing, list) and ing else None)
                item_id = num_map.get(num) or (distinct[0] if len(distinct) == 1 else None)
                if item_id:
                    doc = items_by_id.get(item_id, {})
                    raw_slug = doc.get("slug")
                    clean_slug = raw_slug if raw_slug else slugify(item_id.split(":")[-1])
                    grid[r_idx][c_idx] = {
                        "entity_id": item_id,
                        "slug": clean_slug,
                        "display_name": doc.get("facts", {}).get("display_name") or human_name(item_id),
                        "image_url": doc.get("facts", {}).get("image_url")
                    }
                idx += 1
    elif distinct:
        # Fallback if raw shape is missing
        for idx, item_id in enumerate(distinct[:9]):
            r_idx, c_idx = divmod(idx, 3)
            doc = items_by_id.get(item_id, {})
            raw_slug = doc.get("slug")
            clean_slug = raw_slug if raw_slug else slugify(item_id.split(":")[-1])
            grid[r_idx][c_idx] = {
                "entity_id": item_id,
                "slug": clean_slug,
                "display_name": doc.get("facts", {}).get("display_name") or human_name(item_id),
                "image_url": doc.get("facts", {}).get("image_url")
            }

    return grid


@minecraft_router.get("/recipe/{slug}.json")
async def minecraft_recipe_json(slug: str):
    db = get_minecraft_db()
    recipe = db.recipes.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not recipe:
        norm_slug = normalize_mc_slug(slug)
        if norm_slug != slug:
            recipe = db.recipes.find_one({"edition": EDITION, "version": VERSION, "slug": norm_slug}, {"_id": 0})
            if recipe:
                slug = norm_slug
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return JSONResponse(recipe)


@minecraft_router.get("/recipe/{slug}.md", response_class=PlainTextResponse)
async def minecraft_recipe_md(slug: str):
    db = get_minecraft_db()
    recipe = db.recipes.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not recipe:
        norm_slug = normalize_mc_slug(slug)
        if norm_slug != slug:
            recipe = db.recipes.find_one({"edition": EDITION, "version": VERSION, "slug": norm_slug}, {"_id": 0})
            if recipe:
                slug = norm_slug
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    f = recipe.get("facts", {})
    d = recipe.get("derived", {})
    md = f"""---
title: "Recipe: {recipe['slug']} - Minecraft Java {VERSION}"
slug: "{recipe['slug']}"
entity_id: "{recipe['entity_id']}"
edition: "{recipe['edition']}"
version: "{recipe['version']}"
type: "{recipe['type']}"
output_item: "{d.get('output_item')}"
output_count: {f.get('result', {}).get('count', 1)}
canonical_url: "https://minecraft.avascry.com/recipe/{slug}"
---

# Recipe: {recipe['slug']}

**Namespaced ID:** `{recipe['entity_id']}`  
**Type:** `{recipe['type']}`  
**Edition:** {recipe['edition']} &bull; **Version:** {recipe['version']}

## Output Result
- **Item:** [`{d.get('output_item')}`](/item/{slugify(d.get('output_item', ''))})
- **Count:** {f.get('result', {}).get('count', 1)}

## Distinct Inputs
"""
    for in_item in d.get("distinct_input_items", []):
        md += f"- [`{in_item}`](/item/{slugify(in_item)})\n"

    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@minecraft_router.get("/recipe/{slug}", response_class=HTMLResponse)
async def minecraft_recipe_detail(request: Request, slug: str):
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return await minecraft_recipe_json(slug)
    if "text/markdown" in accept and "text/html" not in accept:
        return await minecraft_recipe_md(slug)

    db = get_minecraft_db()
    recipe = db.recipes.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not recipe:
        norm_slug = normalize_mc_slug(slug)
        if norm_slug != slug:
            recipe = db.recipes.find_one({"edition": EDITION, "version": VERSION, "slug": norm_slug}, {"_id": 0})
            if recipe:
                slug = norm_slug
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    out_item_id = recipe.get("derived", {}).get("output_item", "")
    in_item_ids = recipe.get("derived", {}).get("distinct_input_items", [])
    all_needed_ids = list(set([out_item_id] + in_item_ids)) if out_item_id else in_item_ids

    # Fetch item metadata & sprites (robust lookup)
    items_by_id = {}
    if all_needed_ids:
        for it_doc in db.items.find({"edition": EDITION, "version": VERSION, "entity_id": {"$in": all_needed_ids}}, {"_id": 0, "slug": 1, "entity_id": 1, "facts": 1}):
            items_by_id[it_doc["entity_id"]] = it_doc
        # Fallback if $in was bypassed
        for n_id in all_needed_ids:
            if n_id not in items_by_id:
                single = db.items.find_one({"entity_id": n_id, "edition": EDITION, "version": VERSION}, {"_id": 0, "slug": 1, "entity_id": 1, "facts": 1})
                if single:
                    items_by_id[n_id] = single

    output_item_doc = items_by_id.get(out_item_id)

    # Compute ingredient counts (e.g. 2 bamboo planks, 3 diamonds, 2 sticks)
    ing_counts = compute_ingredient_counts(db, recipe)

    # Ingredients enriched
    ingredients = []
    for i_id in in_item_ids:
        doc = items_by_id.get(i_id, {})
        raw_slug = doc.get("slug")
        clean_slug = raw_slug if raw_slug else slugify(i_id.split(":")[-1])
        cnt = ing_counts.get(i_id, 1)
        ingredients.append({
            "entity_id": i_id,
            "slug": clean_slug,
            "display_name": doc.get("facts", {}).get("display_name") or human_name(i_id),
            "image_url": doc.get("facts", {}).get("image_url"),
            "count": cnt
        })

    # Downstream: What can you craft with the output item?
    downstream_recipes = []
    if out_item_id:
        ds_cursor = db.recipes.find(
            {"edition": EDITION, "version": VERSION, "derived.distinct_input_items": out_item_id},
            {"_id": 0, "slug": 1, "type": 1, "derived.output_item": 1, "facts.result.count": 1}
        ).limit(12)
        for r in ds_cursor:
            r_out = r.get("derived", {}).get("output_item", "")
            y_cnt = r.get("facts", {}).get("result", {}).get("count", 1)
            downstream_recipes.append({
                "slug": r.get("slug"),
                "type": r.get("type"),
                "output_item": r_out,
                "yield_count": y_cnt,
                "display_name": human_name(r_out or r.get("slug"))
            })

    # Upstream: How to craft the input ingredients?
    upstream_recipes = []
    if in_item_ids:
        up_cursor = db.recipes.find(
            {"edition": EDITION, "version": VERSION, "derived.output_item": {"$in": in_item_ids}},
            {"_id": 0, "slug": 1, "type": 1, "derived.output_item": 1, "facts.result.count": 1}
        ).limit(8)
        for r in up_cursor:
            r_out = r.get("derived", {}).get("output_item", "")
            y_cnt = r.get("facts", {}).get("result", {}).get("count", 1)
            upstream_recipes.append({
                "slug": r.get("slug"),
                "type": r.get("type"),
                "output_item": r_out,
                "yield_count": y_cnt,
                "display_name": human_name(r_out or r.get("slug"))
            })

    # Sibling recipes: Other recipes using similar primary ingredients (deterministic graph edge)
    sibling_recipes = []
    if in_item_ids:
        primary_input = in_item_ids[0]
        sib_cursor = db.recipes.find(
            {
                "edition": EDITION,
                "version": VERSION,
                "derived.distinct_input_items": primary_input
            },
            {"_id": 0, "slug": 1, "type": 1, "derived.output_item": 1, "facts.result.count": 1}
        )
        for r in sib_cursor:
            if r.get("slug") != slug:
                r_out = r.get("derived", {}).get("output_item", "")
                y_cnt = r.get("facts", {}).get("result", {}).get("count", 1)
                sibling_recipes.append({
                    "slug": r.get("slug"),
                    "type": r.get("type"),
                    "output_item": r_out,
                    "yield_count": y_cnt,
                    "display_name": human_name(r_out or r.get("slug"))
                })
                if len(sibling_recipes) >= 8:
                    break

    # Bulk hydrate sprites for downstream, upstream, and sibling recipes
    rel_out_ids = list(set(
        [r["output_item"] for r in downstream_recipes + upstream_recipes + sibling_recipes if r.get("output_item")]
    ))
    if rel_out_ids:
        rel_items = {
            doc["entity_id"]: doc.get("facts", {})
            for doc in db.items.find({"edition": EDITION, "version": VERSION, "entity_id": {"$in": rel_out_ids}}, {"entity_id": 1, "facts.display_name": 1, "facts.image_url": 1})
        }
        rel_blocks = {
            doc["entity_id"]: doc.get("facts", {})
            for doc in db.blocks.find({"edition": EDITION, "version": VERSION, "entity_id": {"$in": rel_out_ids}}, {"entity_id": 1, "facts.display_name": 1, "facts.image_url": 1})
        }
        for rec_list in [downstream_recipes, upstream_recipes, sibling_recipes]:
            for item_ref in rec_list:
                out_id = item_ref.get("output_item")
                f_meta = rel_items.get(out_id) or rel_blocks.get(out_id) or {}
                if f_meta.get("image_url"):
                    item_ref["image_url"] = f_meta.get("image_url")
                if f_meta.get("display_name"):
                    item_ref["display_name"] = f_meta.get("display_name")
                item_ref["entity_id"] = out_id

    # Fetch 3 embedding neighbor models for the output item
    target_slug = (output_item_doc.get("slug") if output_item_doc and output_item_doc.get("slug") else slug)
    
    palette_rec = db.palette_neighbors.find_one({"slug": target_slug}, {"palette_matches": 1})
    palette_matches = hydrate_neighbors(db, palette_rec.get("palette_matches", [])[:8], default_type="block") if palette_rec else []

    func_rec = db.similar_functional.find_one({"slug": target_slug}, {"neighbors": 1})
    similar_items = hydrate_neighbors(db, func_rec.get("neighbors", [])[:8], default_type="item") if func_rec else []

    graph_rec = db.graph_neighbors.find_one({"slug": target_slug}, {"progression_neighbors": 1})
    progression_matches = hydrate_neighbors(db, graph_rec.get("progression_neighbors", [])[:8], default_type="item") if graph_rec else []

    # Block counterpart mechanics (if output item is also a placeable block)
    block_counterpart = db.blocks.find_one(
        {"edition": EDITION, "version": VERSION, "slug": target_slug},
        {"_id": 0, "facts": 1, "derived": 1}
    )
    if block_counterpart and block_counterpart.get("facts", {}).get("material"):
        mat = block_counterpart["facts"]["material"]
        if "mineable/" in mat:
            # Fix field-label mismatch: convert mineable tool tag into human tool classification
            tool_part = mat.split("mineable/")[-1].replace(";", ", ").title()
            block_counterpart["facts"]["harvest_tool_tag"] = f"Mineable with {tool_part}"
            block_counterpart["facts"]["material"] = None

    # Construct the 3x3 crafting grid matrix
    crafting_matrix = build_crafting_matrix(db, recipe, items_by_id)

    # Determine primary material name for natural long-tail copy
    primary_material_name = ""
    if ingredients:
        primary_material_name = ingredients[0].get("display_name", "")
    elif in_item_ids:
        primary_material_name = human_name(in_item_ids[0])

    return templates.TemplateResponse(
        request=request,
        name="minecraft/recipe.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "recipe": recipe,
            "crafting_matrix": crafting_matrix,
            "output_item_doc": output_item_doc,
            "ingredients": ingredients,
            "primary_material_name": primary_material_name,
            "downstream_recipes": downstream_recipes,
            "upstream_recipes": upstream_recipes,
            "sibling_recipes": sibling_recipes,
            "palette_matches": palette_matches,
            "similar_items": similar_items,
            "progression_matches": progression_matches,
            "block_counterpart": block_counterpart
        }
    )


# ---------------- ENTITY ROUTES ----------------

@minecraft_router.get("/entities", response_class=HTMLResponse)
async def minecraft_entities_list(
    request: Request, 
    q: str = "", 
    category: str = "",
    immune_to_fire: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    if category:
        query_filter["facts.category"] = {"$regex": category, "$options": "i"}

    if immune_to_fire == "yes":
        query_filter["facts.immune_to_fire"] = True
    elif immune_to_fire == "no":
        query_filter["facts.immune_to_fire"] = False

    sort_criteria = [("facts.display_name", 1)]
    if sort == "name_desc":
        sort_criteria = [("facts.display_name", -1)]
    elif sort == "health_desc":
        sort_criteria = [("facts.max_health", -1), ("facts.display_name", 1)]

    limit = max(12, min(96, limit))
    page = max(1, page)
    total_matching = db.entities.count_documents(query_filter)
    total_pages = max(1, (total_matching + limit - 1) // limit)
    if page > total_pages:
        page = total_pages
    skip = (page - 1) * limit

    entities = list(db.entities.find(query_filter, {"_id": 0}).sort(sort_criteria).skip(skip).limit(limit))
    total_unfiltered = db.entities.count_documents({"edition": EDITION, "version": VERSION})
    is_filtered = bool(q.strip() or category or immune_to_fire or sort != "name_asc")

    return templates.TemplateResponse(
        request=request,
        name="minecraft/list.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "title": "Minecraft Entities & Mobs",
            "description": "Vanilla mob statistics, categories, dimensions, and compiled drops.",
            "entries": entities,
            "total": total_unfiltered,
            "total_matching": total_matching,
            "current_page": page,
            "total_pages": total_pages,
            "limit": limit,
            "is_filtered": is_filtered,
            "query": q,
            "category": category,
            "immune_to_fire": immune_to_fire,
            "sort": sort,
            "item_type": "entity"
        }
    )


@minecraft_router.get("/entities.json")
async def minecraft_entities_json(
    q: str = "",
    category: str = "",
    immune_to_fire: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    if category:
        query_filter["facts.category"] = {"$regex": category, "$options": "i"}

    if immune_to_fire == "yes":
        query_filter["facts.immune_to_fire"] = True
    elif immune_to_fire == "no":
        query_filter["facts.immune_to_fire"] = False

    sort_criteria = [("facts.display_name", 1)]
    if sort == "name_desc":
        sort_criteria = [("facts.display_name", -1)]
    elif sort == "health_desc":
        sort_criteria = [("facts.max_health", -1), ("facts.display_name", 1)]

    limit = max(12, min(96, limit))
    page = max(1, page)
    total_matching = db.entities.count_documents(query_filter)
    total_pages = max(1, (total_matching + limit - 1) // limit)
    if page > total_pages:
        page = total_pages
    skip = (page - 1) * limit

    entities = list(db.entities.find(query_filter, {"_id": 0}).sort(sort_criteria).skip(skip).limit(limit))
    return JSONResponse({
        "edition": EDITION,
        "version": VERSION,
        "category": "entities",
        "page": page,
        "limit": limit,
        "total_matching": total_matching,
        "total_pages": total_pages,
        "entries": entities
    })


@minecraft_router.get("/entities.md", response_class=PlainTextResponse)
async def minecraft_entities_md(
    q: str = "",
    category: str = "",
    immune_to_fire: str = "",
    sort: str = "name_asc",
    page: int = 1,
    limit: int = 36
):
    json_resp = await minecraft_entities_json(q=q, category=category, immune_to_fire=immune_to_fire, sort=sort, page=page, limit=limit)
    import json as pyjson
    data = pyjson.loads(json_resp.body.decode("utf-8"))

    lines = [
        f"# Minecraft Java {VERSION} - Entities & Mobs Catalog",
        f"Page {data['page']} of {data['total_pages']} (Total Matching: {data['total_matching']})\n",
        "| Name | Entity ID | Category | Max Health | Fire Immune | Link |",
        "| --- | --- | --- | --- | --- | --- |"
    ]
    for ent in data["entries"]:
        f = ent.get("facts", {})
        name = f.get("display_name", ent["slug"])
        eid = ent.get("entity_id", "")
        cat = f.get("category", "N/A")
        hp = f.get("max_health") if f.get("max_health") is not None else "N/A"
        fi = "Yes" if f.get("immune_to_fire") else "No"
        url = f"https://minecraft.avascry.com/entity/{ent['slug']}"
        lines.append(f"| {name} | `{eid}` | {cat} | {hp} | {fi} | [{ent['slug']}]({url}) |")

    return "\n".join(lines)



@minecraft_router.get("/entity/{slug}.json")
async def minecraft_entity_json(slug: str):
    db = get_minecraft_db()
    entity = db.entities.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return JSONResponse(entity)


@minecraft_router.get("/entity/{slug}.md", response_class=PlainTextResponse)
async def minecraft_entity_md(slug: str):
    db = get_minecraft_db()
    entity = db.entities.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    f = entity.get("facts", {})
    d = entity.get("derived", {})
    md = f"""---
title: "{f.get('display_name')} - Minecraft Java {VERSION}"
slug: "{entity['slug']}"
entity_id: "{entity['entity_id']}"
category: "{f.get('category')}"
max_health: {f.get('max_health')}
canonical_url: "https://minecraft.avascry.com/entity/{slug}"
---

# {f.get('display_name')}

**Namespaced ID:** `{entity['entity_id']}`  
**Category:** {f.get('category')}  
**Max Health:** {f.get('max_health')} HP

## Drops
"""
    for drop in d.get("drops_summary", []):
        md += f"- **Target:** `{drop['target_id']}` | Count: {drop['min']} - {drop['max']}\n"

    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@minecraft_router.get("/entity/{slug}", response_class=HTMLResponse)
async def minecraft_entity_detail(request: Request, slug: str):
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return await minecraft_entity_json(slug)
    if "text/markdown" in accept and "text/html" not in accept:
        return await minecraft_entity_md(slug)

    db = get_minecraft_db()
    entity = db.entities.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    return templates.TemplateResponse(
        request=request,
        name="minecraft/entity.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "entity": entity
        }
    )


# ---------------- ENCHANTMENTS & EFFECTS ----------------

@minecraft_router.get("/enchantments", response_class=HTMLResponse)
async def minecraft_enchantments_list(request: Request, q: str = ""):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    enchs = list(db.enchantments.find(query_filter, {"_id": 0}).sort("facts.display_name", 1))
    total_unfiltered = db.enchantments.count_documents({"edition": EDITION, "version": VERSION})
    return templates.TemplateResponse(
        request=request,
        name="minecraft/list.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "title": "Minecraft Enchantments",
            "description": "Enchantment levels, target items, and mutual exclusions.",
            "entries": enchs,
            "total": total_unfiltered,
            "total_matching": len(enchs),
            "total_pages": 1,
            "current_page": 1,
            "is_filtered": bool(q.strip()),
            "query": q,
            "item_type": "enchantment"
        }
    )


STATUS_EFFECT_METADATA = {
    "speed": {
        "file": "speed.png",
        "category": "beneficial",
        "description": "Increases movement speed by 20% per level and expands the player's field of view."
    },
    "slowness": {
        "file": "slowness.png",
        "category": "harmful",
        "description": "Reduces movement speed by 15% per level and narrows the player's field of view."
    },
    "haste": {
        "file": "haste.png",
        "category": "beneficial",
        "description": "Increases mining speed by 20% and attack speed by 10% per level."
    },
    "miningfatigue": {
        "file": "mining_fatigue.png",
        "category": "harmful",
        "description": "Severely decreases block-breaking speed and slows melee attack cadence."
    },
    "strength": {
        "file": "strength.png",
        "category": "beneficial",
        "description": "Increases melee attack damage by 3 HP (1.5 hearts) per level."
    },
    "instanthealth": {
        "file": "instant_health.png",
        "category": "beneficial",
        "description": "Instantly restores 4 HP per level (damages undead mobs)."
    },
    "instantdamage": {
        "file": "instant_damage.png",
        "category": "harmful",
        "description": "Instantly inflicts 6 HP damage per level (heals undead mobs)."
    },
    "jumpboost": {
        "file": "jump_boost.png",
        "category": "beneficial",
        "description": "Increases jump height by roughly 0.5 blocks per level and reduces fall damage."
    },
    "nausea": {
        "file": "nausea.png",
        "category": "harmful",
        "description": "Warps, distorts, and wobbles the player's camera perspective."
    },
    "regeneration": {
        "file": "regeneration.png",
        "category": "beneficial",
        "description": "Restores health over time independently of saturation levels."
    },
    "resistance": {
        "file": "resistance.png",
        "category": "beneficial",
        "description": "Reduces incoming damage from almost all sources by 20% per level."
    },
    "fireresistance": {
        "file": "fire_resistance.png",
        "category": "beneficial",
        "description": "Grants complete immunity to fire, lava, blaze fireballs, and burning damage."
    },
    "waterbreathing": {
        "file": "water_breathing.png",
        "category": "beneficial",
        "description": "Prevents the oxygen bar from depleting and improves underwater visibility."
    },
    "invisibility": {
        "file": "invisibility.png",
        "category": "beneficial",
        "description": "Renders the entity model invisible to other players and reduces mob detection range."
    },
    "blindness": {
        "file": "blindness.png",
        "category": "harmful",
        "description": "Impairs vision with a thick black fog and prevents critical hits or sprinting."
    },
    "nightvision": {
        "file": "night_vision.png",
        "category": "beneficial",
        "description": "Brightens the entire world to full daylight levels and clarifies underwater vision."
    },
    "hunger": {
        "file": "hunger.png",
        "category": "harmful",
        "description": "Rapidly drains the player's food saturation and exhaustion meter."
    },
    "weakness": {
        "file": "weakness.png",
        "category": "harmful",
        "description": "Reduces melee attack damage by 4 HP (2 hearts) and enables curing zombie villagers."
    },
    "poison": {
        "file": "poison.png",
        "category": "harmful",
        "description": "Inflicts periodic damage over time down to a minimum of 0.5 hearts (does not kill)."
    },
    "wither": {
        "file": "wither.png",
        "category": "harmful",
        "description": "Inflicts lethal periodic damage over time and turns the player's health hearts black."
    },
    "healthboost": {
        "file": "health_boost.png",
        "category": "beneficial",
        "description": "Adds 4 HP (2 hearts) of extra maximum health capacity per level."
    },
    "absorption": {
        "file": "absorption.png",
        "category": "beneficial",
        "description": "Grants 4 HP (2 gold hearts) of temporary shielding per level that cannot be healed."
    },
    "saturation": {
        "file": "saturation.png",
        "category": "beneficial",
        "description": "Instantly replenishes food hunger points and restores saturation levels."
    },
    "glowing": {
        "file": "glowing.png",
        "category": "harmful",
        "description": "Outlines the entity with an illuminated border visible through solid blocks."
    },
    "levitation": {
        "file": "levitation.png",
        "category": "harmful",
        "description": "Forces the affected entity to float upward uncontrollably at a steady speed."
    },
    "luck": {
        "file": "luck.png",
        "category": "beneficial",
        "description": "Increases the probability of receiving high-tier loot from fishing and select chests."
    },
    "unluck": {
        "file": "unluck.png",
        "category": "harmful",
        "description": "Reduces chances of rare loot drops and increases junk rates when fishing."
    },
    "slowfalling": {
        "file": "slow_falling.png",
        "category": "beneficial",
        "description": "Slows descent speed dramatically and completely eliminates all fall damage."
    },
    "conduitpower": {
        "file": "conduit_power.png",
        "category": "beneficial",
        "description": "Combines water breathing, underwater night vision, and boosted mining haste."
    },
    "dolphinsgrace": {
        "file": "dolphins_grace.png",
        "category": "beneficial",
        "description": "Massively boosts swimming speed when moving through water near dolphins."
    },
    "badomen": {
        "file": "bad_omen.png",
        "category": "harmful",
        "description": "Triggers a village raid or converts into a Trial Omen upon entering trial chambers."
    },
    "heroofthevillage": {
        "file": "hero_of_the_village.png",
        "category": "beneficial",
        "description": "Grants steep discounts on all villager trades and causes villagers to toss gifts."
    },
    "darkness": {
        "file": "darkness.png",
        "category": "harmful",
        "description": "Pulsates and dims environmental lighting when in the presence of the Warden."
    },
    "trialomen": {
        "file": "trial_omen.png",
        "category": "harmful",
        "description": "Upgrades nearby Trial Spawners to Ominous Trials with enhanced mobs and loot."
    },
    "raidomen": {
        "file": "raid_omen.png",
        "category": "harmful",
        "description": "Acts as a 30-second warning countdown before triggering a full village raid."
    },
    "windcharged": {
        "file": "wind_charged.png",
        "category": "harmful",
        "description": "Emits a localized wind burst upon death that launches surrounding entities."
    },
    "weaving": {
        "file": "weaving.png",
        "category": "harmful",
        "description": "Causes the entity to spawn 2-3 cobweb blocks upon death and move faster through webs."
    },
    "oozing": {
        "file": "oozing.png",
        "category": "harmful",
        "description": "Causes two medium slime mobs to spawn upon the entity's death."
    },
    "infested": {
        "file": "infested.png",
        "category": "harmful",
        "description": "Gives a 10% chance to spawn 1-2 silverfish whenever the entity takes damage."
    }
}


@minecraft_router.get("/effects", response_class=HTMLResponse)
async def minecraft_effects_list(request: Request, q: str = ""):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    raw_effs = list(db.effects.find(query_filter, {"_id": 0}).sort("facts.display_name", 1))
    
    # Deduplicate by slug, preferring enriched documents and hydrating textures/explanations
    seen_slugs = set()
    effs = []
    for eff in raw_effs:
        slug = eff.get("slug", "")
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        
        meta = STATUS_EFFECT_METADATA.get(slug, {})
        facts = eff.setdefault("facts", {})
        if meta.get("file"):
            facts["image_url"] = f"/static/minecraft/textures/effects/{meta['file']}"
        if meta.get("description"):
            facts["description"] = meta["description"]
        if meta.get("category"):
            facts["category"] = meta["category"]

        effs.append(eff)

    total_unfiltered = len(set(d["slug"] for d in db.effects.find({"edition": EDITION, "version": VERSION}, {"slug": 1})))
    return templates.TemplateResponse(
        request=request,
        name="minecraft/list.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "title": "Minecraft Status Effects",
            "description": "Beneficial and harmful potion and beacon status modifiers.",
            "entries": effs,
            "total": total_unfiltered,
            "total_matching": len(effs),
            "total_pages": 1,
            "current_page": 1,
            "is_filtered": bool(q.strip()),
            "query": q,
            "item_type": "effect"
        }
    )



@minecraft_router.get("/biomes", response_class=HTMLResponse)
async def minecraft_biomes_list(request: Request, q: str = ""):
    db = get_minecraft_db()
    query_filter = {"edition": EDITION, "version": VERSION}
    if q.strip():
        regex = {"$regex": q.strip(), "$options": "i"}
        query_filter["$or"] = [{"slug": regex}, {"entity_id": regex}, {"facts.display_name": regex}]

    bms = list(db.biomes.find(query_filter, {"_id": 0}).sort("entity_id", 1))
    total_unfiltered = db.biomes.count_documents({"edition": EDITION, "version": VERSION})
    return templates.TemplateResponse(
        request=request,
        name="minecraft/list.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "title": "Minecraft Biomes",
            "description": "Temperature, precipitation, and spawn rules.",
            "entries": bms,
            "total": total_unfiltered,
            "total_matching": len(bms),
            "total_pages": 1,
            "current_page": 1,
            "is_filtered": bool(q.strip()),
            "query": q,
            "item_type": "biome"
        }
    )


# ---------------- LEGAL & SUPPORT ----------------

@minecraft_router.get("/about", response_class=HTMLResponse)
async def minecraft_about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="minecraft/about.html",
        context={"base_prefix": get_base_prefix(request), "user": get_current_user(request)}
    )


@minecraft_router.get("/privacy", response_class=HTMLResponse)
async def minecraft_privacy(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="minecraft/privacy.html",
        context={"base_prefix": get_base_prefix(request), "user": get_current_user(request)}
    )


@minecraft_router.get("/terms", response_class=HTMLResponse)
async def minecraft_terms(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="minecraft/terms.html",
        context={"base_prefix": get_base_prefix(request), "user": get_current_user(request)}
    )


@minecraft_router.get("/contact", response_class=HTMLResponse)
async def minecraft_contact(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="minecraft/contact.html",
        context={"base_prefix": get_base_prefix(request), "user": get_current_user(request), "success": False, "error": None}
    )


@minecraft_router.post("/contact", response_class=HTMLResponse)
async def minecraft_contact_post(request: Request):
    from mtgabyss.shared.contact import process_contact_submission
    result = await process_contact_submission(
        request=request,
        subsite_name="AvaScry Minecraft",
        subsite_color=0x0d9488
    )
    return templates.TemplateResponse(
        request=request,
        name="minecraft/contact.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "success": result["success"],
            "error": result["error"]
        }
    )


# ---------------- BUILDER PALETTE GENERATOR ----------------

ROLE_ASSIGNMENTS = [
    {"role": "Primary Material", "desc": "Main wall surface / dominant volume"},
    {"role": "Secondary Texture", "desc": "Sub-facade, pillar, or floor balance"},
    {"role": "Accent / Framing", "desc": "Trims, lintels, archways, and window borders"},
    {"role": "Foundation / Grounding", "desc": "Base layers, retaining walls, foundation"},
    {"role": "Detail & Highlights", "desc": "Contrasting accents, roofs, and focal features"},
]


def build_palette_payload(db, slug: str):
    """Builds a curated 5-block building palette from vector neighbors."""
    base_block = db.blocks.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})
    if not base_block:
        # Fallback to oak-planks if invalid slug
        slug = "oak-planks"
        base_block = db.blocks.find_one({"edition": EDITION, "version": VERSION, "slug": slug}, {"_id": 0})

    pal_doc = db.palette_neighbors.find_one({"slug": slug})
    matches = pal_doc.get("palette_matches", []) if pal_doc else []
    hydrated = hydrate_neighbors(db, matches[:10], default_type="block")

    # Construct 5 palette tiers
    palette_blocks = []
    # Tier 0 is the base block itself
    palette_blocks.append({
        "role": ROLE_ASSIGNMENTS[0]["role"],
        "description": ROLE_ASSIGNMENTS[0]["desc"],
        "slug": base_block["slug"],
        "display_name": base_block.get("facts", {}).get("display_name", base_block["slug"].replace("-", " ").title()),
        "image_url": base_block.get("facts", {}).get("image_url"),
        "score_pct": 100,
        "is_base": True
    })

    # Pick top distinct hydrated matches for roles 1 through 4
    for idx, match in enumerate(hydrated[:4], 1):
        role_info = ROLE_ASSIGNMENTS[idx] if idx < len(ROLE_ASSIGNMENTS) else {"role": f"Complement {idx}", "desc": "Harmonious material"}
        palette_blocks.append({
            "role": role_info["role"],
            "description": role_info["desc"],
            "slug": match["slug"],
            "display_name": match["display_name"],
            "image_url": match["image_url"],
            "score_pct": match["score_pct"],
            "is_base": False
        })

    return base_block, palette_blocks, hydrated


@minecraft_router.get("/palette/{slug}.json")
async def minecraft_palette_json(slug: str):
    db = get_minecraft_db()
    base_block, palette_blocks, all_matches = build_palette_payload(db, slug)
    return JSONResponse({
        "base_block": base_block.get("slug"),
        "base_name": base_block.get("facts", {}).get("display_name"),
        "palette": palette_blocks,
        "extended_matches": all_matches
    })


@minecraft_router.get("/palette/{slug}.md", response_class=PlainTextResponse)
async def minecraft_palette_md(slug: str):
    db = get_minecraft_db()
    base_block, palette_blocks, all_matches = build_palette_payload(db, slug)
    b_name = base_block.get("facts", {}).get("display_name", base_block["slug"])
    
    md = f"""---
title: "{b_name} Building Palette — Minecraft Java 1.21.4"
base_block: "{base_block['slug']}"
edition: "java"
version: "1.21.4"
canonical_url: "https://minecraft.avascry.com/palette/{base_block['slug']}"
---

# 🎨 Architectural Building Palette: {b_name}

> Generated via multi-dimensional texture, chroma, and material embeddings for Minecraft Java Edition.

## Recommended 5-Block Palette Structure

"""
    for blk in palette_blocks:
        md += f"### {blk['role']}: [{blk['display_name']}](/block/{blk['slug']})\n"
        md += f"- **Purpose:** {blk['description']}\n"
        md += f"- **Affinity Score:** {blk['score_pct']}%\n\n"

    md += "## Extended Aesthetic Matches\n"
    for m in all_matches[:8]:
        md += f"- [{m['display_name']}](/block/{m['slug']}) — harmony: {m['score_pct']}%\n"

    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@minecraft_router.get("/palette", response_class=HTMLResponse)
@minecraft_router.get("/palette/{slug}", response_class=HTMLResponse)
async def minecraft_palette_view(request: Request, slug: str = "deepslate-tiles"):
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return await minecraft_palette_json(slug)
    if "text/markdown" in accept and "text/html" not in accept:
        return await minecraft_palette_md(slug)

    db = get_minecraft_db()
    base_block, palette_blocks, all_matches = build_palette_payload(db, slug)

    # Popular curated base blocks for quick navigation
    curated_slugs = [
        "deepslate-tiles", "oak-planks", "copper-block", "mud-bricks",
        "warped-planks", "prismarine-bricks", "blackstone", "smooth-stone",
        "red-sandstone", "calcite"
    ]
    curated_blocks = list(db.blocks.find(
        {"slug": {"$in": curated_slugs}},
        {"slug": 1, "facts.display_name": 1, "facts.image_url": 1}
    ))

    return templates.TemplateResponse(
        request=request,
        name="minecraft/palette.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "base_block": base_block,
            "palette_blocks": palette_blocks,
            "all_matches": all_matches,
            "curated_blocks": curated_blocks
        }
    )


@minecraft_router.get("/guides", response_class=HTMLResponse)
async def minecraft_guides_index(request: Request):
    """Guides & Strategy index for Minecraft."""
    from mtgabyss.data.minecraft_guides import MINECRAFT_GUIDES
    guides = list(MINECRAFT_GUIDES.values())
    return templates.TemplateResponse(
        request=request,
        name="minecraft/guides/index.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "guides": guides
        }
    )


@minecraft_router.get("/guides/{slug}", response_class=HTMLResponse)
async def minecraft_guide_detail(request: Request, slug: str):
    """Guide detail view for Minecraft."""
    from mtgabyss.data.minecraft_guides import MINECRAFT_GUIDES
    guide = MINECRAFT_GUIDES.get(slug)
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found")
    return templates.TemplateResponse(
        request=request,
        name="minecraft/guides/detail.html",
        context={
            "base_prefix": get_base_prefix(request),
            "user": get_current_user(request),
            "guide": guide
        }
    )

