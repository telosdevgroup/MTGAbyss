import os
from typing import Optional
from fastapi import APIRouter, Request, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from db_mongo import get_mongo_db
import i18n
from mtgabyss.shared.helpers import slugify, templates

pages_router = APIRouter()

@pages_router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    featured = []
    try:
        sample_slugs = ["black-lotus", "atraxa-praetors-voice", "the-ur-dragon", "sol-ring", "rhystic-study", "cyclonic-rift", "demonic-tutor", "mana-crypt", "force-of-will", "lightning-bolt", "smothering-tithe", "doubling-season"]
        cards_cursor = list(db["cards"].find({"slug": {"$in": sample_slugs}, "lang": "en"}).limit(18))
        for c in cards_cursor:
            img = c.get("image_uris")
            if not img and c.get("card_faces"):
                img = c["card_faces"][0].get("image_uris") or {}
            img = img or {}
            c_name = c.get("name") or "Card"
            c_set = (c.get("set") or "").lower()
            c_slug = slugify(c_name)
            p_slug = f"{c_slug}-{c_set}" if c_set else c_slug
            featured.append({
                "name": c_name,
                "slug": p_slug,
                "large_image_url": img.get("large") or img.get("normal") or f"/images/large/{c_slug}.jpg",
                "image_url": img.get("normal") or f"/images/normal/{c_slug}.jpg"
            })
    except Exception as e:
        print(f"Error loading homepage featured cards: {e}")

    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "active_nav": "home",
            "featured_cards": featured,
            "current_lang": lang,
            "q": ""
        }
    )

@pages_router.get("/random", response_class=HTMLResponse)
@pages_router.get("/set/{code}/random", response_class=HTMLResponse)
async def random_card(request: Request, code: Optional[str] = None):
    db = get_mongo_db()
    set_param = (code or request.query_params.get("set") or "").strip().lower()
    try:
        match_query = {"lang": "en"}
        if set_param:
            match_query["set"] = set_param
        sample = list(db["cards"].aggregate([
            {"$match": match_query},
            {"$sample": {"size": 1}}
        ]))
        if sample:
            c = sample[0]
            c_set = (c.get("set") or "").lower()
            c_slug = slugify(c.get("name") or "")
            target = f"{c_slug}-{c_set}" if c_set else (c.get("id") or c_slug)
            return RedirectResponse(url=f"/printing/{target}", status_code=303)
    except Exception as e:
        print(f"Error selecting random card: {e}")
    fallback = f"/set/{set_param}" if set_param else "/printing/black-lotus-lea"
    return RedirectResponse(url=fallback, status_code=303)

@pages_router.get("/commander", response_class=HTMLResponse)
async def commander_chooser(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="commander.html",
        context={
            "active_nav": "commander",
            "current_lang": lang
        }
    )

@pages_router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={"current_lang": lang, "active_nav": "about"}
    )

@pages_router.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="contact.html",
        context={"current_lang": lang, "active_nav": "contact"}
    )

@pages_router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="privacy.html",
        context={"current_lang": lang}
    )

@pages_router.get("/terms", response_class=HTMLResponse)
async def terms_of_service(request: Request):
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="terms.html",
        context={"current_lang": lang}
    )

@pages_router.get("/developers", response_class=HTMLResponse)
@pages_router.head("/developers")
async def developers_hub(request: Request):
    format_param = request.query_params.get("format", "").lower()
    accept_header = request.headers.get("accept", "").lower()
    if format_param == "md" or "text/markdown" in accept_header:
        return await developers_hub_markdown(request)
    if format_param == "json" or "application/json" in accept_header:
        return await developers_hub_json(request)

    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="developers.html",
        context={
            "current_lang": lang,
            "languages": i18n.LANGUAGES,
            "active_nav": "developers"
        },
        headers={
            "Link": '</developers.md>; rel="alternate"; type="text/markdown", </developers.json>; rel="alternate"; type="application/json"'
        }
    )

@pages_router.get("/developers.md")
@pages_router.head("/developers.md")
async def developers_hub_markdown(request: Request):
    lang = i18n.get_locale(request)
    title = i18n.t('dev_page_title', lang)
    subtitle = i18n.t('dev_hero_subtitle', lang)
    ai_desc = i18n.t('dev_ai_desc', lang)
    api_desc = i18n.t('dev_api_desc', lang)
    vec_desc = i18n.t('dev_vector_desc', lang)
    cockatrice_desc = i18n.t('dev_cockatrice_desc', lang)
    rss_desc = i18n.t('dev_rss_desc', lang)

    md = f"""# {title}

> {subtitle}

- **Language:** {lang}
- **Corpus-Version:** 1.0
- **Canonical-Host:** https://avascry.com

## 1. AI Agent & LLM Ingestion (Markdown Surface)
{ai_desc}

### Endpoints
- Card Rules: `https://avascry.com/printing/<slug>-<set>.md`
- 4096-Dim Synergies: `https://avascry.com/similar/<slug>.md`
- Set Checklists: `https://avascry.com/set/<set-code>.md`
- Artist Portfolios: `https://avascry.com/artist/<artist-slug>.md`
- Comprehensive Rules: `https://avascry.com/rules.md`
- Format Legalities: `https://avascry.com/legalities.md`

## 2. Ultra-Fast REST JSON API
{api_desc}

### Endpoints
- Card Printing: `https://avascry.com/printing/<slug>-<set>.json`
- Card Synergies: `https://avascry.com/similar/<slug>.json`
- Set Details: `https://avascry.com/set/<set-code>.json`
- Artist Portfolio: `https://avascry.com/artist/<artist-slug>.json`
- Rules Corpus: `https://avascry.com/rules.json`
- Legalities Corpus: `https://avascry.com/legalities.json`

## 3. 4096-Dimensional Neural Vectors (Qwen 8B)
{vec_desc}

- Endpoint: `https://avascry.com/vector/<card-slug>.json`

## 4. Cockatrice Desktop Simulator XML
{cockatrice_desc}

- Endpoint: `https://avascry.com/set/<set-code>/cockatrice.xml`

## 5. Discord Webhooks & Live RSS 2.0 Feeds
{rss_desc}

- Sets Feed: `https://avascry.com/feed/sets.xml`
- Rulings Feed: `https://avascry.com/feed/rulings.xml`
"""
    return Response(
        content=md.strip(),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Vary": "Accept, Accept-Language",
            "Link": '</developers>; rel="alternate"; type="text/html", </developers.json>; rel="alternate"; type="application/json"'
        }
    )

@pages_router.get("/developers.json")
@pages_router.head("/developers.json")
async def developers_hub_json(request: Request):
    lang = i18n.get_locale(request)
    return JSONResponse(
        content={
            "name": "AvaScry AI & Developer Ecosystem",
            "version": "1.0",
            "language": lang,
            "canonical_host": "https://avascry.com",
            "endpoints": {
                "markdown": {
                    "card": "https://avascry.com/printing/{slug}-{set}.md",
                    "similar": "https://avascry.com/similar/{slug}.md",
                    "set": "https://avascry.com/set/{code}.md",
                    "artist": "https://avascry.com/artist/{slug}.md",
                    "rules": "https://avascry.com/rules.md",
                    "legalities": "https://avascry.com/legalities.md"
                },
                "json": {
                    "card": "https://avascry.com/printing/{slug}-{set}.json",
                    "similar": "https://avascry.com/similar/{slug}.json",
                    "set": "https://avascry.com/set/{code}.json",
                    "artist": "https://avascry.com/artist/{slug}.json",
                    "vector": "https://avascry.com/vector/{slug}.json",
                    "rules": "https://avascry.com/rules.json",
                    "legalities": "https://avascry.com/legalities.json"
                },
                "xml": {
                    "cockatrice_set": "https://avascry.com/set/{code}/cockatrice.xml",
                    "feed_sets": "https://avascry.com/feed/sets.xml",
                    "feed_rulings": "https://avascry.com/feed/rulings.xml"
                }
            }
        },
        headers={
            "Link": '</developers>; rel="alternate"; type="text/html", </developers.md>; rel="alternate"; type="text/markdown"'
        }
    )
