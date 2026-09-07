"""
Necromunda Underhive Lexicon & Armory Router for necromunda.avascry.com.
Connects directly to MongoDB database 'avascry_necromunda'.
Serves HTML, Markdown (.md), JSON, sitemaps, and llms.txt endpoints for bots and humans.
"""

from datetime import datetime, timezone
import json
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from db_mongo import get_mongo_db

from mtgabyss.shared.cache import RAM_CACHE, set_ram_cache

necromunda_router = APIRouter(prefix="", tags=["Necromunda"])
templates = Jinja2Templates(directory="templates")


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
    cache_key = "necro:home_data"
    cached = RAM_CACHE.get(cache_key)
    if not cached:
        db = get_necromunda_db()
        cached = {
            "weapons": list(db.weapons.find({}, {"_id": 0}).sort("name", 1)),
            "traits": list(db.traits.find({}, {"_id": 0}).sort("name", 1)),
            "houses": list(db.houses.find({}, {"_id": 0}).sort("name", 1)),
            "skills": list(db.skills.find({}, {"_id": 0}).sort("name", 1)),
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
            "total_weapons": len(cached["weapons"]),
            "total_traits": len(cached["traits"]),
            "total_houses": len(cached["houses"]),
            "total_skills": len(cached["skills"]),
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
        "- Skill Tree: https://necromunda.avascry.com/skill/{slug} (.md, .json)\n"
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

    weapons = list(db.weapons.find({}, {"slug": 1}))
    traits = list(db.traits.find({}, {"slug": 1}))
    houses = list(db.houses.find({}, {"slug": 1}))
    skills = list(db.skills.find({}, {"slug": 1}))

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
    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/traits.html",
        context={
            "base_path": base_path,
            "traits": traits,
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
    base_path = get_base_prefix(request)
    return templates.TemplateResponse(
        request=request,
        name="necromunda/skills.html",
        context={
            "base_path": base_path,
            "skills": skills,
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
