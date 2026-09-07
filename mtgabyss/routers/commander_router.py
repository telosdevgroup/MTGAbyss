import re
from typing import Optional
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import JSONResponse
from db_mongo import get_mongo_db
from mtgabyss.shared.helpers import slugify
from mtgabyss.shared.cache import RAM_CACHE, set_ram_cache

commander_router = APIRouter()

@commander_router.get("/api/commander/search")
async def commander_search(
    q: Optional[str] = Query(None),
    colors: Optional[str] = Query(None),
    do_random: Optional[bool] = Query(False),
    limit: int = Query(24, le=60)
):
    db = get_mongo_db()
    mongo_filter = {
        "lang": "en",
        "$or": [
            {"type_line": re.compile(r"Legendary.*Creature", re.I)},
            {"oracle_text": re.compile(r"can be your commander", re.I)},
            {"card_faces.0.type_line": re.compile(r"Legendary.*Creature", re.I)},
        ]
    }

    # Color identity filter
    if colors:
        selected = [c.strip().upper() for c in colors.split(",") if c.strip()]
        if selected:
            mongo_filter["color_identity"] = {"$not": {"$elemMatch": {"$nin": selected}}}

    # Keyword search on name + oracle_text + type_line
    if q and q.strip():
        words = q.strip().split()
        word_filters = []
        for w in words:
            pattern = re.compile(re.escape(w), re.I)
            word_filters.append({"$or": [
                {"name": pattern},
                {"oracle_text": pattern},
                {"type_line": pattern},
                {"keywords": pattern},
            ]})
        if word_filters:
            mongo_filter["$and"] = word_filters

    try:
        projection = {"name": 1, "set": 1, "type_line": 1, "color_identity": 1,
                      "image_uris": 1, "card_faces": 1, "oracle_text": 1, "keywords": 1}
        if do_random or not (q and q.strip()):
            pipeline = [
                {"$match": mongo_filter},
                {"$sample": {"size": limit}},
                {"$project": projection}
            ]
            docs = list(db["cards"].aggregate(pipeline))
        else:
            docs = list(db["cards"].find(mongo_filter, projection).limit(limit))
    except Exception as e:
        print(f"Commander search error: {e}")
        docs = []

    results = []
    for doc in docs:
        name = doc.get("name") or "Unknown"
        c_set = (doc.get("set") or "").lower()
        printing_slug = f"{slugify(name)}-{c_set}" if c_set else slugify(name)
        img = (doc.get("image_uris") or {})
        if not img and doc.get("card_faces"):
            img = (doc["card_faces"][0].get("image_uris") or {})
        results.append({
            "name": name,
            "printing_slug": printing_slug,
            "type_line": doc.get("type_line", ""),
            "color_identity": doc.get("color_identity", []),
            "oracle_text": (doc.get("oracle_text") or "")[:220],
            "image_normal": img.get("normal") or img.get("large") or "",
            "image_art_crop": img.get("art_crop") or "",
        })

    return JSONResponse({"commanders": results})


@commander_router.get("/api/commander/suggest")
async def commander_suggest(q: str = Query("")):
    """Fast autocomplete for commander names — prefix match, deduplicated by oracle_id (cached)."""
    q_clean = q.strip().lower()
    if not q_clean:
        return JSONResponse({"suggestions": []})
    
    cache_key = f"cmd_sug:{q_clean}"
    if cache_key in RAM_CACHE:
        return JSONResponse({"suggestions": RAM_CACHE[cache_key]})

    db = get_mongo_db()
    pattern = re.compile(f"^{re.escape(q.strip())}", re.I)
    commander_filter = {
        "lang": "en",
        "name": pattern,
        "$or": [
            {"type_line": re.compile(r"Legendary.*Creature", re.I)},
            {"oracle_text": re.compile(r"can be your commander", re.I)},
            {"card_faces.0.type_line": re.compile(r"Legendary.*Creature", re.I)},
        ]
    }
    pipeline = [
        {"$match": commander_filter},
        {"$sort": {"released_at": -1}},
        {
            "$group": {
                "_id": "$oracle_id",
                "name": {"$first": "$name"},
                "set": {"$first": "$set"},
                "type_line": {"$first": "$type_line"},
                "color_identity": {"$first": "$color_identity"},
                "oracle_text": {"$first": "$oracle_text"},
                "image_uris": {"$first": "$image_uris"},
                "card_faces": {"$first": "$card_faces"}
            }
        },
        {"$limit": 8}
    ]
    docs = list(db["cards"].aggregate(pipeline))

    suggestions = []
    for doc in docs:
        img = (doc.get("image_uris") or {})
        if not img and doc.get("card_faces"):
            img = (doc["card_faces"][0].get("image_uris") or {})
        name = doc.get("name", "")
        c_set = (doc.get("set") or "").lower()
        suggestions.append({
            "name": name,
            "oracle_id": doc.get("_id", ""),
            "printing_slug": f"{slugify(name)}-{c_set}" if c_set else slugify(name),
            "type_line": doc.get("type_line", ""),
            "color_identity": doc.get("color_identity", []),
            "oracle_text": doc.get("oracle_text", ""),
            "image_normal": img.get("normal") or img.get("large") or "",
            "image_art_crop": img.get("art_crop") or "",
        })
    set_ram_cache(cache_key, suggestions)
    return JSONResponse({"suggestions": suggestions})


@commander_router.get("/api/commander/profile")
async def commander_profile(oracle_id: str = Query(...)):
    """Return full commander card data by oracle_id."""
    db = get_mongo_db()
    doc = db["cards"].find_one(
        {"oracle_id": oracle_id, "lang": "en"},
        {"name": 1, "oracle_id": 1, "type_line": 1, "color_identity": 1,
         "oracle_text": 1, "keywords": 1, "image_uris": 1, "card_faces": 1,
         "mana_cost": 1, "cmc": 1, "set": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Commander not found")
    img = (doc.get("image_uris") or {})
    if not img and doc.get("card_faces"):
        img = (doc["card_faces"][0].get("image_uris") or {})
    name = doc.get("name", "")
    c_set = (doc.get("set") or "").lower()
    return JSONResponse({
        "name": name,
        "oracle_id": doc.get("oracle_id", ""),
        "printing_slug": f"{slugify(name)}-{c_set}" if c_set else slugify(name),
        "type_line": doc.get("type_line", ""),
        "color_identity": doc.get("color_identity", []),
        "oracle_text": doc.get("oracle_text", ""),
        "mana_cost": doc.get("mana_cost", ""),
        "image_normal": img.get("normal") or img.get("large") or "",
        "image_art_crop": img.get("art_crop") or "",
        "image_large": img.get("large") or img.get("normal") or "",
    })


@commander_router.post("/api/commander/discover")
async def commander_discover(request: Request):
    """
    Interactive draft search:
    Accepts commander oracle_id, color_identity, and a natural language query/theme
    (e.g., 'red creature 4 mana', '10 lands', 'card draw').
    Returns deduplicated Oracle cards clamped to the commander's color identity.
    """
    body = await request.json()
    oracle_id: str = body.get("oracle_id", "")
    theme: str = body.get("theme", "").strip()
    color_identity: list = body.get("color_identity", [])
    limit: int = int(body.get("limit", 24))

    new_db = get_mongo_db()

    # Base query clamped to commander's color identity and English
    base_match = {"lang": "en"}
    if color_identity:
        base_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
    if oracle_id:
        base_match["oracle_id"] = {"$ne": oracle_id}

    # Parse query parameters (e.g. cmc/mana, card types, terms)
    theme_lower = theme.lower()
    and_conditions = []

    # CMC parsing (e.g. "4 mana", "cmc 3", "3-mana", "mana value 2")
    cmc_match = re.search(r'(\d+)\s*(?:mana|cmc)', theme_lower) or re.search(r'(?:mana|cmc)\s*(?:value\s*)?(\d+)', theme_lower)
    if cmc_match:
        try:
            target_cmc = float(cmc_match.group(1))
            and_conditions.append({"cmc": target_cmc})
        except ValueError:
            pass

    # Type line parsing
    type_tokens = []
    for t_kw in ["creature", "instant", "sorcery", "enchantment", "artifact", "planeswalker", "land", "battle"]:
        if t_kw in theme_lower:
            type_tokens.append(t_kw)
    if type_tokens:
        type_pattern = "|".join(type_tokens)
        and_conditions.append({"type_line": {"$regex": type_pattern, "$options": "i"}})

    # Color words in query
    color_map = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G", "colorless": "C"}
    explicit_colors = [c_code for c_name, c_code in color_map.items() if c_name in theme_lower]
    if explicit_colors and "C" not in explicit_colors:
        and_conditions.append({"colors": {"$in": explicit_colors}})

    # Remaining descriptive words / mechanics (e.g. "flying", "deathtouch", "draw", "counter")
    stopwords = {"mana", "cmc", "a", "an", "the", "for", "with", "and", "or", "in", "my", "deck", "want", "some", "good", "best", "different", "card", "cards", "what", "exists", "available", "show", "me", "that", "have", "has"}
    tokens = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', theme_lower) if w not in stopwords and w not in type_tokens and w not in color_map]
    
    # Require EVERY meaningful descriptive token (e.g. "flying") to match
    for token in tokens:
        token_regex = re.compile(re.escape(token), re.I)
        and_conditions.append({
            "$or": [
                {"name": token_regex},
                {"oracle_text": token_regex},
                {"type_line": token_regex},
                {"keywords": token_regex}
            ]
        })

    if and_conditions:
        base_match["$and"] = and_conditions

    # If no search theme query entered, serve top 4096-dim Qwen 8B neural synergies directly!
    docs = []
    if not theme and oracle_id:
        sim_doc = new_db["similar_cards"].find_one({"oracle_id": oracle_id})
        if sim_doc:
            similar_raw = sim_doc.get("similar", [])
            sim_oids = [s if isinstance(s, str) else s.get("oracle_id") for s in similar_raw]
            sim_oids = [oid for oid in sim_oids if oid and oid != oracle_id]
            
            fb_match = {
                "oracle_id": {"$in": sim_oids},
                "lang": "en"
            }
            if color_identity:
                fb_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
            
            raw_docs = list(new_db["cards"].find(fb_match, {
                "oracle_id": 1, "name": 1, "set": 1, "type_line": 1, "color_identity": 1,
                "oracle_text": 1, "mana_cost": 1, "cmc": 1, "image_uris": 1, "card_faces": 1, "image_slug": 1
            }))
            doc_map = {}
            for d in raw_docs:
                oid = d.get("oracle_id")
                if oid and oid not in doc_map:
                    doc_map[oid] = d
            
            docs = [doc_map[oid] for oid in sim_oids if oid in doc_map][:limit]

    if not docs:
        # Aggregation pipeline: group by oracle_id to strictly guarantee 1 printing per oracle card
        pipeline = [
            {"$match": base_match},
            {"$sort": {"released_at": -1}},
            {
                "$group": {
                    "_id": "$oracle_id",
                    "name": {"$first": "$name"},
                    "set": {"$first": "$set"},
                    "type_line": {"$first": "$type_line"},
                    "color_identity": {"$first": "$color_identity"},
                    "oracle_text": {"$first": "$oracle_text"},
                    "mana_cost": {"$first": "$mana_cost"},
                    "cmc": {"$first": "$cmc"},
                    "image_uris": {"$first": "$image_uris"},
                    "card_faces": {"$first": "$card_faces"},
                    "image_slug": {"$first": "$image_slug"}
                }
            },
            {"$limit": max(limit, 60)}
        ]
        docs = list(new_db["cards"].aggregate(pipeline))

    # Always fall back to 4096-dim neural vector similarity when strict token matching returns nothing
    is_fallback = False
    if len(docs) == 0 and oracle_id:
        is_fallback = True
        sim_doc = new_db["similar_cards"].find_one({"oracle_id": oracle_id})
        if sim_doc:
            similar_raw = sim_doc.get("similar", [])
            sim_oids = [s if isinstance(s, str) else s.get("oracle_id") for s in similar_raw]
            sim_oids = [oid for oid in sim_oids if oid and oid != oracle_id]
            fallback_match = {
                "oracle_id": {"$in": sim_oids},
                "lang": "en"
            }
            if color_identity:
                fallback_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
            
            raw_docs = list(new_db["cards"].find(fallback_match, {
                "oracle_id": 1, "name": 1, "set": 1, "type_line": 1, "color_identity": 1,
                "oracle_text": 1, "mana_cost": 1, "cmc": 1, "image_uris": 1, "card_faces": 1, "image_slug": 1
            }))
            doc_map = {}
            for d in raw_docs:
                oid = d.get("oracle_id")
                if oid and oid not in doc_map:
                    doc_map[oid] = d
            docs = [doc_map[oid] for oid in sim_oids if oid in doc_map][:limit]

        # Final safety net: if no similar_cards either, just return good staples in color
        if len(docs) == 0:
            safety_match = {"lang": "en", "edhrec_rank": {"$lte": 500}}
            if color_identity:
                safety_match["color_identity"] = {"$not": {"$elemMatch": {"$nin": color_identity}}}
            if oracle_id:
                safety_match["oracle_id"] = {"$ne": oracle_id}
            docs = list(new_db["cards"].aggregate([
                {"$match": safety_match},
                {"$sort": {"edhrec_rank": 1}},
                {"$group": {
                    "_id": "$oracle_id",
                    "name": {"$first": "$name"},
                    "set": {"$first": "$set"},
                    "type_line": {"$first": "$type_line"},
                    "color_identity": {"$first": "$color_identity"},
                    "oracle_text": {"$first": "$oracle_text"},
                    "mana_cost": {"$first": "$mana_cost"},
                    "cmc": {"$first": "$cmc"},
                    "image_uris": {"$first": "$image_uris"},
                    "card_faces": {"$first": "$card_faces"}
                }},
                {"$limit": limit}
            ]))

    # Check RAM Cache first
    cache_key = f"discover:{oracle_id}:{','.join(sorted(color_identity))}:{theme_lower}:{limit}"
    if cache_key in RAM_CACHE:
        return JSONResponse(RAM_CACHE[cache_key])

    results = []
    for doc in docs:
        img = (doc.get("image_uris") or {})
        if not img and doc.get("card_faces"):
            img = (doc["card_faces"][0].get("image_uris") or {})
        name = doc.get("name", "")
        c_set = (doc.get("set") or "").lower()
        oid = str(doc.get("oracle_id") or doc.get("_id") or "")
        results.append({
            "name": name,
            "oracle_id": oid,
            "printing_slug": f"{slugify(name)}-{c_set}" if c_set else slugify(name),
            "type_line": doc.get("type_line", ""),
            "color_identity": doc.get("color_identity", []),
            "oracle_text": doc.get("oracle_text") or "",
            "mana_cost": doc.get("mana_cost", ""),
            "image_normal": img.get("normal") or img.get("large") or "",
            "image_large": img.get("large") or img.get("normal") or "",
        })

    response_data = {"cards": results, "query": theme, "total": len(results), "fallback": is_fallback}
    set_ram_cache(cache_key, response_data)
    return JSONResponse(response_data)
