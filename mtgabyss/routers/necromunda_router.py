"""
Necromunda Underhive Lexicon & Armory Router for necromunda.avascry.com.
Connects directly to MongoDB database 'avascry_necromunda'.
Serves HTML, Markdown (.md), JSON, sitemaps, and llms.txt endpoints for bots and humans.
"""

from datetime import datetime, timezone
import json
import random
import time
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from db_mongo import get_mongo_db

from mtgabyss.shared.cache import RAM_CACHE, set_ram_cache
from mtgabyss.shared.helpers import slugify

necromunda_router = APIRouter(prefix="", tags=["Necromunda"])
templates = Jinja2Templates(directory="templates")
templates.env.filters["slugify"] = slugify


def get_necromunda_db():
    client = get_mongo_db().client
    return client["avascry_necromunda"]


def get_base_prefix(request: Request) -> str:
    host = request.headers.get("host", "")
    from mtgabyss.network_router import extract_subdomain
    if extract_subdomain(host) == "necromunda":
        return ""
    return "/necromunda"


@necromunda_router.get("", response_class=HTMLResponse)
@necromunda_router.get("/", response_class=HTMLResponse)
async def necromunda_home(request: Request):
    cache_key = f"necro:home_data:{int(time.time() // 3600)}"
    cached = RAM_CACHE.get(cache_key)
    if not cached:
        db = get_necromunda_db()
        weapons = list(db.weapons.find({}, {"_id": 0}))
        traits = list(db.traits.find({}, {"_id": 0}))
        houses = list(db.houses.find({}, {"_id": 0}))
        skills = list(db.skills.find({}, {"_id": 0}))

        total_w, total_t, total_h, total_s = len(weapons), len(traits), len(houses), len(skills)
        random.shuffle(weapons)
        random.shuffle(traits)
        random.shuffle(houses)
        random.shuffle(skills)

        cached = {
            "weapons": weapons,
            "traits": traits,
            "houses": houses,
            "skills": skills,
            "total_weapons": total_w,
            "total_traits": total_t,
            "total_houses": total_h,
            "total_skills": total_s,
        }
        set_ram_cache(cache_key, cached)

    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/home.html",
        context={
            "base_path": base_path,
            "weapons": cached["weapons"],
            "traits": cached["traits"],
            "houses": cached["houses"],
            "skills": cached["skills"],
            "total_weapons": cached["total_weapons"],
            "total_traits": cached["total_traits"],
            "total_houses": cached["total_houses"],
            "total_skills": cached["total_skills"],
        }
    )


# ==========================================
# LLMS.TXT & LLMS-FULL.TXT & SITEMAP
# ==========================================

@necromunda_router.get("/llms.txt", response_class=PlainTextResponse)
async def necromunda_llms_txt(request: Request):
    """Navigational manifest for LLM search agents."""
    return (
        "# AvaScry Necromunda Underhive Lexicon & Armory\n\n"
        "> Structured Necromunda Underhive skirmish armory, weapon profiles, rule traits, clan houses, and skill trees.\n\n"
        "## Start here\n"
        "- [Armory Hub](https://necromunda.avascry.com/)\n"
        "- [Weapons Armory](https://necromunda.avascry.com/weapons)\n"
        "- [Trait Lexicon](https://necromunda.avascry.com/traits)\n"
        "- [Clan Houses](https://necromunda.avascry.com/houses)\n"
        "- [Skills & Tactics](https://necromunda.avascry.com/skills)\n"
        "- [Full LLM Corpus](https://necromunda.avascry.com/llms-full.txt)\n"
        "- [XML Sitemap](https://necromunda.avascry.com/sitemap.xml)\n\n"
        "## Tri-Surface Endpoints\n"
        "- Weapon Detail: https://necromunda.avascry.com/weapon/{slug} (.md, .json)\n"
        "- Trait Detail: https://necromunda.avascry.com/trait/{slug} (.md, .json)\n"
        "- Clan House: https://necromunda.avascry.com/house/{slug} (.md, .json)\n"
        "- Skill Tree: https://necromunda.avascry.com/skill/{slug} (.md, .json)\n\n"
        "## Unified Discord Identity & Network SSO\n"
        "- Part of the unified AvaScry Card Network (MTG, SWU, Dominion, Necromunda).\n"
        "- Single Discord OAuth sign-in shared network-wide across necromunda.avascry.com and all sister domains.\n"
        "- Built for Underhive skirmish campaigns with weapon and fighter tactics sharing directly to Discord.\n"
    )


@necromunda_router.get("/llms-full.txt", response_class=PlainTextResponse)
async def necromunda_llms_full_txt():
    """Full plain-text game corpus for direct model ingestion."""
    db = get_necromunda_db()
    weapons = list(db.weapons.find({}, {"_id": 0}).sort("name", 1))
    traits = list(db.traits.find({}, {"_id": 0}).sort("name", 1))
    houses = list(db.houses.find({}, {"_id": 0}).sort("name", 1))
    skills = list(db.skills.find({}, {"_id": 0}).sort("name", 1))

    lines = [
        "# AvaScry Necromunda — Complete Underhive Database & Tactics Lexicon",
        "Game: Necromunda (Games Workshop)",
        f"Total Weapons: {len(weapons)}",
        f"Total Traits: {len(traits)}",
        f"Total Houses: {len(houses)}",
        f"Total Skills: {len(skills)}\n",
        "## Authentication & Discord Integration Architecture",
        "- Network SSO: Single Discord authentication session operates network-wide across avascry.com, swu.avascry.com, dominion.avascry.com, and necromunda.avascry.com.",
        "- Zero-Password Tabletop Identity: User profile and gang loadouts synchronize via Discord without email or password management.",
        "- Discord Bot Ready: Structured weapon, trait, and clan house endpoints are optimized for Discord community bots and skirmish lookups.\n",
        "---",
        "## WEAPON TRAITS\n"
    ]
    for t in traits:
        lines.append(f"### Trait: {t['name']}")
        lines.append(f"Slug: {t.get('slug')}")
        lines.append(f"Rules: {t.get('rules_text')}")
        lines.append(f"FAQ: {t.get('faq')}\n")

    lines.append("---\n## ARMORY WEAPONS\n")
    for w in weapons:
        lines.append(f"### Weapon: {w['name']} [{w.get('category')}]")
        lines.append(f"Cost: {w.get('cost_credits')} credits | Rarity: {w.get('rarity')}")
        lines.append(f"Range: Short {w.get('range_short')} / Long {w.get('range_long')}")
        lines.append(f"Accuracy: Short {w.get('accuracy_short')} / Long {w.get('accuracy_long')}")
        lines.append(f"Profile: Str {w.get('strength')} | Dmg {w.get('damage')} | AP {w.get('armor_piercing')} | Ammo {w.get('ammo')}")
        lines.append(f"Traits: {', '.join(w.get('traits', []))}")
        lines.append(f"Description: {w.get('description')}\n")

    lines.append("---\n## CLAN HOUSES\n")
    for h in houses:
        lines.append(f"### Clan House: {h['name']} ({h.get('title')})")
        lines.append(f"Specialty: {h.get('specialty')}")
        lines.append(f"Favored Weapons: {', '.join(h.get('signature_weapons', []))}")
        lines.append(f"Primary Skills: {', '.join(h.get('primary_skills', []))}")
        lines.append(f"Lore: {h.get('lore')}\n")

    lines.append("---\n## SKILLS\n")
    for s in skills:
        lines.append(f"### Skill: {s['name']} [{s.get('tree')}]")
        lines.append(f"Rules: {s.get('rules_text')}")
        lines.append(f"Tactics: {s.get('tactics')}\n")

    return "\n".join(lines)


@necromunda_router.get("/sitemap.xml")
async def necromunda_sitemap(request: Request):
    """Dynamically generated XML sitemap for Necromunda underhive corpus."""
    db = get_necromunda_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    weapons = list(db.weapons.find({}, {"slug": 1}).sort("name", 1).limit(7))
    traits = list(db.traits.find({}, {"slug": 1}).sort("name", 1).limit(7))
    houses = list(db.houses.find({}, {"slug": 1}).sort("name", 1).limit(7))
    skills = list(db.skills.find({}, {"slug": 1}).sort("name", 1).limit(7))

    urls = [
        f'  <url><loc>https://necromunda.avascry.com/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>',
        f'  <url><loc>https://necromunda.avascry.com/weapons</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://necromunda.avascry.com/traits</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://necromunda.avascry.com/houses</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://necromunda.avascry.com/skills</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>',
        f'  <url><loc>https://necromunda.avascry.com/llms.txt</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>',
        f'  <url><loc>https://necromunda.avascry.com/llms-full.txt</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>',
    ]

    for w in weapons:
        slug = w["slug"]
        urls.append(f'  <url><loc>https://necromunda.avascry.com/weapon/{slug}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
        urls.append(f'  <url><loc>https://necromunda.avascry.com/weapon/{slug}.md</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
        urls.append(f'  <url><loc>https://necromunda.avascry.com/weapon/{slug}.json</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')

    for t in traits:
        slug = t["slug"]
        urls.append(f'  <url><loc>https://necromunda.avascry.com/trait/{slug}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
        urls.append(f'  <url><loc>https://necromunda.avascry.com/trait/{slug}.md</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
        urls.append(f'  <url><loc>https://necromunda.avascry.com/trait/{slug}.json</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')

    for h in houses:
        slug = h["slug"]
        urls.append(f'  <url><loc>https://necromunda.avascry.com/house/{slug}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
        urls.append(f'  <url><loc>https://necromunda.avascry.com/house/{slug}.md</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
        urls.append(f'  <url><loc>https://necromunda.avascry.com/house/{slug}.json</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')

    for s in skills:
        slug = s["slug"]
        urls.append(f'  <url><loc>https://necromunda.avascry.com/skill/{slug}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
        urls.append(f'  <url><loc>https://necromunda.avascry.com/skill/{slug}.md</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')
        urls.append(f'  <url><loc>https://necromunda.avascry.com/skill/{slug}.json</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>')

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '\n'.join(urls)
    xml += '\n</urlset>'
    return Response(content=xml, media_type="application/xml")


@necromunda_router.get("/sitemap.html", response_class=HTMLResponse)
async def necromunda_sitemap_html(request: Request):
    """HTML master sitemap directory with discrete .md and .json format badges."""
    cache_key = "necro:sitemap_data"
    cached = RAM_CACHE.get(cache_key)
    if not cached:
        db = get_necromunda_db()
        weapons = list(db.weapons.find({}, {"_id": 0}).sort("name", 1))
        traits = list(db.traits.find({}, {"_id": 0}).sort("name", 1))
        houses = list(db.houses.find({}, {"_id": 0}).sort("name", 1))
        skills = list(db.skills.find({}, {"_id": 0}).sort("name", 1))

        # Group weapons by category
        weapon_groups = {}
        for w in weapons:
            cat = w.get("category", "General Weapons")
            weapon_groups.setdefault(cat, []).append(w)

        # Group skills by tree
        skill_groups = {}
        for s in skills:
            tree = s.get("tree", "General Skills")
            skill_groups.setdefault(tree, []).append(s)

        cached = {
            "weapons": weapons,
            "traits": traits,
            "houses": houses,
            "skills": skills,
            "weapon_groups": weapon_groups,
            "skill_groups": skill_groups,
        }
        set_ram_cache(cache_key, cached)

    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/sitemap.html",
        context={
            "base_path": base_path,
            "weapons": cached["weapons"],
            "traits": cached["traits"],
            "houses": cached["houses"],
            "skills": cached["skills"],
            "weapon_groups": cached["weapon_groups"],
            "skill_groups": cached["skill_groups"],
        }
    )


@necromunda_router.get("/sitemap.md", response_class=PlainTextResponse)
async def necromunda_sitemap_md():
    """Markdown sitemap linking all Underhive entities, rules, and machine manifests."""
    db = get_necromunda_db()
    weapons = list(db.weapons.find({}, {"name": 1, "slug": 1, "category": 1, "_id": 0}).sort("name", 1))
    traits = list(db.traits.find({}, {"name": 1, "slug": 1, "_id": 0}).sort("name", 1))
    houses = list(db.houses.find({}, {"name": 1, "slug": 1, "title": 1, "_id": 0}).sort("name", 1))
    skills = list(db.skills.find({}, {"name": 1, "slug": 1, "tree": 1, "_id": 0}).sort("name", 1))

    lines = [
        "# AvaScry Necromunda — Master Sitemap & Knowledge Directory (Markdown)",
        "",
        "> Structured Necromunda Underhive skirmish armory, weapon profiles, rule traits, clan houses, and skill trees.",
        "",
        "## Core Manifests & Indexes",
        "- [Armory Hub](https://necromunda.avascry.com/)",
        "- [HTML Master Sitemap](https://necromunda.avascry.com/sitemap.html)",
        "- [XML Sitemap Index](https://necromunda.avascry.com/sitemap.xml)",
        "- [LLM Navigational Manifest (`/llms.txt`)](https://necromunda.avascry.com/llms.txt)",
        "- [Full Knowledge Corpus (`/llms-full.txt`)](https://necromunda.avascry.com/llms-full.txt)",
        "",
        f"## Clan Houses & Gang Rosters ({len(houses)})",
    ]
    for h in houses:
        lines.append(f"- [{h['name']}](https://necromunda.avascry.com/house/{h['slug']}) • [MD](https://necromunda.avascry.com/house/{h['slug']}.md) • [JSON](https://necromunda.avascry.com/house/{h['slug']}.json)")

    lines.append(f"\n## Armory Weapons ({len(weapons)})")
    # Group weapons by category
    cat_map = {}
    for w in weapons:
        cat_map.setdefault(w.get("category", "General"), []).append(w)

    for cat, cat_weps in cat_map.items():
        lines.append(f"\n### {cat} ({len(cat_weps)})")
        for w in cat_weps:
            lines.append(f"- [{w['name']}](https://necromunda.avascry.com/weapon/{w['slug']}) • [MD](https://necromunda.avascry.com/weapon/{w['slug']}.md) • [JSON](https://necromunda.avascry.com/weapon/{w['slug']}.json)")

    lines.append(f"\n## Weapon Traits Lexicon ({len(traits)})")
    for t in traits:
        lines.append(f"- [{t['name']}](https://necromunda.avascry.com/trait/{t['slug']}) • [MD](https://necromunda.avascry.com/trait/{t['slug']}.md) • [JSON](https://necromunda.avascry.com/trait/{t['slug']}.json)")

    lines.append(f"\n## Skills & Tactics ({len(skills)})")
    tree_map = {}
    for s in skills:
        tree_map.setdefault(s.get("tree", "General"), []).append(s)

    for tree, tree_sk in tree_map.items():
        lines.append(f"\n### {tree} ({len(tree_sk)})")
        for s in tree_sk:
            lines.append(f"- [{s['name']}](https://necromunda.avascry.com/skill/{s['slug']}) • [MD](https://necromunda.avascry.com/skill/{s['slug']}.md) • [JSON](https://necromunda.avascry.com/skill/{s['slug']}.json)")

    return PlainTextResponse("\n".join(lines), media_type="text/markdown; charset=utf-8")



# ==========================================
# WEAPONS CATALOG & DETAIL (TRI-SURFACE)
# ==========================================

@necromunda_router.get("/weapons", response_class=HTMLResponse)
async def necromunda_weapons_list(request: Request):
    db = get_necromunda_db()
    weapons = list(db.weapons.find({}, {"_id": 0}).sort("name", 1))
    categories = sorted(list(set(w.get("category", "General") for w in weapons)))
    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/weapons.html",
        context={
            "base_path": base_path,
            "weapons": weapons,
            "categories": categories,
            "total_weapons": len(weapons)
        }
    )


@necromunda_router.get("/weapon/{slug}.json")
async def necromunda_weapon_json(slug: str):
    db = get_necromunda_db()
    weapon = db.weapons.find_one({"slug": slug}, {"_id": 0})
    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon not found")
    return JSONResponse(weapon)


@necromunda_router.get("/weapon/{slug}.md", response_class=PlainTextResponse)
async def necromunda_weapon_md(slug: str):
    db = get_necromunda_db()
    weapon = db.weapons.find_one({"slug": slug}, {"_id": 0})
    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon not found")

    md = f"""---
title: "{weapon['name']} - Necromunda Underhive Armory"
slug: "{weapon['slug']}"
category: "{weapon.get('category', '')}"
weapon_type: "{weapon.get('weapon_type', '')}"
cost_credits: {weapon.get('cost_credits', 0)}
rarity: "{weapon.get('rarity', '')}"
traits: {json.dumps(weapon.get('traits', []))}
canonical_url: "https://necromunda.avascry.com/weapon/{slug}"
---

# {weapon['name']}

**Category:** {weapon.get('category')} ({weapon.get('weapon_type')})  
**Cost:** {weapon.get('cost_credits')} credits | **Rarity:** {weapon.get('rarity')}

## Weapon Characteristics
| Range (Short / Long) | Accuracy (Short / Long) | Strength | Damage | Armor Piercing | Ammo |
| :---: | :---: | :---: | :---: | :---: | :---: |
| {weapon.get('range_short')} / {weapon.get('range_long')} | {weapon.get('accuracy_short')} / {weapon.get('accuracy_long')} | {weapon.get('strength')} | {weapon.get('damage')} | {weapon.get('armor_piercing')} | {weapon.get('ammo')} |

## Weapon Traits
{', '.join([f'`{t}`' for t in weapon.get('traits', [])])}

## Underhive Description & Lore
{weapon.get('description', '')}

## Gang Availability
{', '.join(weapon.get('availability', []))}
"""
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@necromunda_router.get("/weapon/{slug}", response_class=HTMLResponse)
async def necromunda_weapon_detail(request: Request, slug: str):
    db = get_necromunda_db()
    weapon = db.weapons.find_one({"slug": slug}, {"_id": 0})
    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon not found")

    # Fetch trait definitions for cross-linking
    trait_names = weapon.get("traits", [])
    clean_trait_names = [t.split("(")[0].strip() for t in trait_names]
    traits_data = list(db.traits.find({
        "$or": [
            {"name": {"$in": trait_names}},
            {"name": {"$in": clean_trait_names}}
        ]
    }, {"_id": 0}))

    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/weapon_detail.html",
        context={
            "base_path": base_path,
            "weapon": weapon,
            "traits_data": traits_data,
        }
    )


# ==========================================
# TRAITS LEXICON & DETAIL (TRI-SURFACE)
# ==========================================

@necromunda_router.get("/traits", response_class=HTMLResponse)
async def necromunda_traits_list(request: Request):
    db = get_necromunda_db()
    traits = list(db.traits.find({}, {"_id": 0}).sort("name", 1))
    categories = sorted(list(set(t.get("category") for t in traits if t.get("category"))))
    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/traits.html",
        context={
            "base_path": base_path,
            "traits": traits,
            "categories": categories,
            "total_traits": len(traits)
        }
    )


@necromunda_router.get("/trait/{slug}.json")
async def necromunda_trait_json(slug: str):
    db = get_necromunda_db()
    trait = db.traits.find_one({"slug": slug}, {"_id": 0})
    if not trait:
        raise HTTPException(status_code=404, detail="Trait not found")
    return JSONResponse(trait)


@necromunda_router.get("/trait/{slug}.md", response_class=PlainTextResponse)
async def necromunda_trait_md(slug: str):
    db = get_necromunda_db()
    trait = db.traits.find_one({"slug": slug}, {"_id": 0})
    if not trait:
        raise HTTPException(status_code=404, detail="Trait not found")

    weapons_with_trait = list(db.weapons.find(
        {"traits": {"$regex": trait["name"], "$options": "i"}},
        {"_id": 0, "name": 1, "slug": 1, "category": 1}
    ).sort("name", 1))

    weapons_bullets = "\n".join([f"- [{w['name']}](https://necromunda.avascry.com/weapon/{w['slug']}) ({w.get('category')})" for w in weapons_with_trait])

    md = f"""---
title: "{trait['name']} - Necromunda Weapon Trait Lexicon"
slug: "{trait['slug']}"
category: "{trait.get('category', '')}"
canonical_url: "https://necromunda.avascry.com/trait/{slug}"
---

# Weapon Trait: {trait['name']}

**Category:** {trait.get('category')}  
**Summary:** {trait.get('summary')}

## Official Underhive Effect
{trait.get('rules_text')}

## Tactical Notes & FAQ
{trait.get('faq')}

## Weapons Featuring {trait['name']}
{weapons_bullets if weapons_bullets else 'No armory weapons currently registered with this trait.'}
"""
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@necromunda_router.get("/trait/{slug}", response_class=HTMLResponse)
async def necromunda_trait_detail(request: Request, slug: str):
    db = get_necromunda_db()
    trait = db.traits.find_one({"slug": slug}, {"_id": 0})
    if not trait:
        raise HTTPException(status_code=404, detail="Trait not found")

    weapons = list(db.weapons.find(
        {"traits": {"$regex": trait["name"], "$options": "i"}},
        {"_id": 0}
    ).sort("name", 1))

    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/trait_detail.html",
        context={
            "base_path": base_path,
            "trait": trait,
            "weapons": weapons,
        }
    )


# ==========================================
# CLAN HOUSES & DETAIL (TRI-SURFACE)
# ==========================================

@necromunda_router.get("/houses", response_class=HTMLResponse)
async def necromunda_houses_list(request: Request):
    db = get_necromunda_db()
    houses = list(db.houses.find({}, {"_id": 0}).sort("name", 1))
    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/houses.html",
        context={
            "base_path": base_path,
            "houses": houses,
            "total_houses": len(houses)
        }
    )


@necromunda_router.get("/house/{slug}.json")
async def necromunda_house_json(slug: str):
    db = get_necromunda_db()
    house = db.houses.find_one({"slug": slug}, {"_id": 0})
    if not house:
        raise HTTPException(status_code=404, detail="Clan House not found")
    return JSONResponse(house)


@necromunda_router.get("/house/{slug}.md", response_class=PlainTextResponse)
async def necromunda_house_md(slug: str):
    db = get_necromunda_db()
    house = db.houses.find_one({"slug": slug}, {"_id": 0})
    if not house:
        raise HTTPException(status_code=404, detail="Clan House not found")

    favored = ", ".join(house.get("signature_weapons", []))
    skills = ", ".join(house.get("primary_skills", []))

    md = f"""---
title: "{house['name']} ({house.get('title')}) - Necromunda Clan House"
slug: "{house['slug']}"
canonical_url: "https://necromunda.avascry.com/house/{slug}"
---

# Clan House: {house['name']}
*{house.get('title')}*

## Tactical Profile
- **Specialty:** {house.get('specialty')}
- **Signature Weaponry:** {favored}
- **Primary Skill Disciplines:** {skills}

## Clan Lore
{house.get('lore')}
"""
    if house.get("roster"):
        md += "\n## Official Fighter Class Roster\n| Class | Role | Base Cost | M | WS | BS | S | T | W | I | A | Ld | Cl | Wil | Int |\n"
        md += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for f in house["roster"]:
            md += f"| {f['title']} | {f['role']} | {f['cost_credits']}cr | {f['m']} | {f['ws']} | {f['bs']} | {f['s']} | {f['t']} | {f['w']} | {f['i']} | {f['a']} | {f['ld']} | {f['cl']} | {f['wil']} | {f['int']} |\n"

    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@necromunda_router.get("/house/{slug}", response_class=HTMLResponse)
async def necromunda_house_detail(request: Request, slug: str):
    db = get_necromunda_db()
    house = db.houses.find_one({"slug": slug}, {"_id": 0})
    if not house:
        raise HTTPException(status_code=404, detail="Clan House not found")

    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/house_detail.html",
        context={
            "base_path": base_path,
            "house": house,
        }
    )


# ==========================================
# SKILLS LEXICON & DETAIL (TRI-SURFACE)
# ==========================================

@necromunda_router.get("/skills", response_class=HTMLResponse)
async def necromunda_skills_list(request: Request):
    db = get_necromunda_db()
    skills = list(db.skills.find({}, {"_id": 0}).sort("name", 1))
    trees = sorted(list(set(s.get("tree") for s in skills if s.get("tree"))))
    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/skills.html",
        context={
            "base_path": base_path,
            "skills": skills,
            "trees": trees,
            "total_skills": len(skills)
        }
    )


@necromunda_router.get("/skill/{slug}.json")
async def necromunda_skill_json(slug: str):
    db = get_necromunda_db()
    skill = db.skills.find_one({"slug": slug}, {"_id": 0})
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return JSONResponse(skill)


@necromunda_router.get("/skill/{slug}.md", response_class=PlainTextResponse)
async def necromunda_skill_md(slug: str):
    db = get_necromunda_db()
    skill = db.skills.find_one({"slug": slug}, {"_id": 0})
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    md = f"""---
title: "{skill['name']} [{skill.get('tree')}] - Necromunda Skill"
slug: "{skill['slug']}"
tree: "{skill.get('tree')}"
canonical_url: "https://necromunda.avascry.com/skill/{slug}"
---

# Skill: {skill['name']}
**Discipline Tree:** {skill.get('tree')}

## Rules
{skill.get('rules_text')}

## Tactics
{skill.get('tactics')}
"""
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@necromunda_router.get("/skill/{slug}", response_class=HTMLResponse)
async def necromunda_skill_detail(request: Request, slug: str):
    db = get_necromunda_db()
    skill = db.skills.find_one({"slug": slug}, {"_id": 0})
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/skill_detail.html",
        context={
            "base_path": base_path,
            "skill": skill,
        }
    )


@necromunda_router.get("/about", response_class=HTMLResponse)
async def necromunda_about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="necromunda/about.html",
        context={"base_path": get_base_prefix(request)}
    )


@necromunda_router.get("/privacy", response_class=HTMLResponse)
async def necromunda_privacy(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="necromunda/privacy.html",
        context={"base_path": get_base_prefix(request)}
    )


@necromunda_router.get("/terms", response_class=HTMLResponse)
async def necromunda_terms(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="necromunda/terms.html",
        context={"base_path": get_base_prefix(request)}
    )


@necromunda_router.get("/contact", response_class=HTMLResponse)
async def necromunda_contact(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="necromunda/contact.html",
        context={"base_path": get_base_prefix(request), "success": False, "error": None}
    )


@necromunda_router.post("/contact", response_class=HTMLResponse)
async def necromunda_contact_post(request: Request):
    from mtgabyss.shared.contact import process_contact_submission
    result = await process_contact_submission(
        request=request,
        subsite_name="AvaScry Necromunda",
        subsite_color=0xff5722
    )
    return templates.TemplateResponse(
        request=request,
        name="necromunda/contact.html",
        context={
            "base_path": get_base_prefix(request),
            "success": result["success"],
            "error": result["error"],
            "values": result.get("values", {})
        }
    )


