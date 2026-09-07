import re
from typing import Optional
from fastapi import APIRouter, Request, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from db_mongo import get_mongo_db
from mtgabyss.shared.helpers import slugify, resolve_card_images, templates

api_router = APIRouter()

@api_router.get("/api/search-suggest", response_class=HTMLResponse)
async def search_suggest(request: Request, background_tasks: BackgroundTasks, q: Optional[str] = Query(None)):
    if not q or len(q.strip()) < 1:
        return HTMLResponse("")
        
    query_str = q.strip()
    db = get_mongo_db()
    
    pattern = re.compile(f"^{re.escape(query_str)}", re.IGNORECASE)
    results = []
    try:
        cursor = db["cards"].find(
            {"name": pattern, "lang": "en"},
            {"name": 1, "slug": 1, "set": 1, "lang": 1, "mana_cost": 1, "type_line": 1, "id": 1, "image_slug": 1, "raw": 1, "image_uris": 1, "card_faces": 1}
        ).limit(8)
        
        for doc in cursor:
            _, img_url, _ = resolve_card_images(doc, background_tasks)
            d_name = doc.get("name") or "card"
            d_set = (doc.get("set") or "").lower()
            d_slug = slugify(d_name)
            d_printing_slug = f"{d_slug}-{d_set}" if d_set else d_slug
            results.append({
                "name": d_name,
                "slug": d_printing_slug,
                "type_line": doc.get("type_line"),
                "mana_cost": doc.get("mana_cost"),
                "image_url": img_url
            })
    except Exception as e:
        print(f"Error in search suggest: {e}")
        
    return templates.TemplateResponse(
        request=request,
        name="partials/search_results.html",
        context={
            "results": results,
            "query": query_str
        }
    )

@api_router.get("/api/card/{slug}/lure", response_class=HTMLResponse)
async def card_lure_partial(request: Request, slug: str):
    db = get_mongo_db()
    card = db["cards"].find_one({"$or": [{"slug": slug}, {"slug": slugify(slug)}]})
    if not card:
        return HTMLResponse("")
        
    oracle_id = card.get("oracle_id")
    lure = None
    if oracle_id:
        try:
            abyss_doc = db["abysses"].find_one({"oracle_id": oracle_id})
            if abyss_doc:
                lure_data = abyss_doc.get("content", {}).get("lure", {})
                if lure_data.get("status") == "generated" and lure_data.get("text"):
                    lure = {
                        "text": lure_data.get("text").strip(),
                        "persona": lure_data.get("persona", "Oracle")
                    }
        except Exception:
            pass
            
    return templates.TemplateResponse(
        request=request,
        name="partials/card_lure.html",
        context={
            "lure": lure
        }
    )

@api_router.get("/api/card/{slug}/similar", response_class=HTMLResponse)
async def card_similar_partial(request: Request, slug: str, background_tasks: BackgroundTasks):
    db = get_mongo_db()
    card = db["cards"].find_one({"$or": [{"slug": slug}, {"slug": slugify(slug)}]})
    if not card:
        return HTMLResponse("")
        
    oracle_id = card.get("oracle_id")
    similar_cards = []
    if oracle_id:
        try:
            from mtgabyss.similar import calculate_similar_cards
            candidates = calculate_similar_cards(db, oracle_id)
            for c in candidates[:12]:
                _, img_url, _ = resolve_card_images(c, background_tasks)
                similar_cards.append({
                    "name": c.get("name"),
                    "slug": c.get("slug") or slugify(c.get("name")),
                    "image_url": img_url,
                    "score": c.get("similarity_score")
                })
        except Exception as e:
            print(f"Error loading similar cards: {e}")
            
    return templates.TemplateResponse(
        request=request,
        name="partials/similar_cards.html",
        context={
            "similar_cards": similar_cards
        }
    )
