import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from db_mongo import get_mongo_db
import i18n
from mtgabyss.shared.helpers import templates
from mtgabyss.routers.auth_router import send_discord_notification

user_router = APIRouter()

@user_router.get("/api/me")
async def api_me(request: Request):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"authenticated": False, "user": None})
    return JSONResponse({"authenticated": True, "user": user})

@user_router.get("/api/decks")
async def list_user_decks(request: Request):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"authenticated": False, "decks": []})
    
    db = get_mongo_db()
    decks = list(db["decks"].find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("updated_at", -1).limit(50))
    return JSONResponse({"authenticated": True, "decks": decks})

@user_router.get("/api/deck/{deck_id}")
async def get_user_deck(deck_id: str, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    db = get_mongo_db()
    deck = db["decks"].find_one(
        {"deck_id": deck_id, "user_id": user["id"]},
        {"_id": 0}
    )
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return JSONResponse({"deck": deck})

@user_router.post("/api/deck/save")
async def save_user_deck(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to save decks")
    
    body = await request.json()
    deck_id = body.get("deck_id") or str(uuid.uuid4())[:12]
    name = (body.get("name") or "Untitled Deck").strip()
    commander_data = body.get("commander") or {}
    cards = body.get("cards") or [] # [{oracle_id, name, count, image_normal, printing_slug}, ...]
    active_query = (body.get("active_query") or "").strip()

    db = get_mongo_db()
    now = datetime.now(timezone.utc).isoformat()
    
    deck_doc = {
        "deck_id": deck_id,
        "user_id": user["id"],
        "name": name,
        "commander": commander_data,
        "cards": cards,
        "active_query": active_query,
        "card_count": sum(c.get("count", 1) for c in cards),
        "updated_at": now
    }
    
    upsert_res = db["decks"].update_one(
        {"deck_id": deck_id, "user_id": user["id"]},
        {
            "$set": deck_doc,
            "$setOnInsert": {"created_at": now}
        },
        upsert=True
    )
    
    if upsert_res.upserted_id is not None:
        user_display = user.get("name") or user.get("discord_username") or "Planeswalker"
        commander_name = commander_data.get("name", "None") if commander_data else "None"
        card_count = deck_doc["card_count"]
        asyncio.create_task(send_discord_notification(
            title="🃏 New Deck Created",
            description=f"**{user_display}** created a new deck: **{name}**!",
            color=0x2ECC71,
            fields=[
                {"name": "Deck Name", "value": name, "inline": True},
                {"name": "Commander", "value": commander_name, "inline": True},
                {"name": "Cards", "value": str(card_count), "inline": True},
                {"name": "Deck ID", "value": deck_id, "inline": True}
            ]
        ))
    
    return JSONResponse({"status": "saved", "deck_id": deck_id, "updated_at": now})

@user_router.delete("/api/deck/{deck_id}")
async def delete_user_deck(deck_id: str, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    db = get_mongo_db()
    result = db["decks"].delete_one({"deck_id": deck_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Deck not found")
    return JSONResponse({"status": "deleted", "deck_id": deck_id})

@user_router.post("/api/deck/{deck_id}/clone")
async def clone_user_deck(deck_id: str, request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    db = get_mongo_db()
    original = db["decks"].find_one({"deck_id": deck_id})
    if not original:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    new_deck_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    
    is_owner = (original.get("user_id") == user["id"])
    clone_name = f"{original.get('name', 'Deck')} (Copy)" if is_owner else original.get("name", "Cloned Deck")
    
    cloned_doc = {
        "deck_id": new_deck_id,
        "user_id": user["id"],
        "name": clone_name,
        "commander": original.get("commander", {}),
        "cards": original.get("cards", []),
        "active_query": original.get("active_query", ""),
        "card_count": original.get("card_count", 0),
        "created_at": now,
        "updated_at": now
    }
    db["decks"].insert_one(cloned_doc)
    return JSONResponse({"status": "cloned", "new_deck_id": new_deck_id})

@user_router.get("/deck/{deck_id}", response_class=HTMLResponse)
async def public_deck_view(deck_id: str, request: Request):
    db = get_mongo_db()
    deck = db["decks"].find_one({"deck_id": deck_id})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found in the Abyss")
        
    user = request.session.get("user")
    is_owner = bool(user and user.get("id") == deck.get("user_id"))
    
    # Creator info: ONLY use Discord username or explicit handle, never Google real names
    discord_handle = None
    try:
        from bson import ObjectId
        creator = db["users"].find_one({"_id": ObjectId(deck.get("user_id"))})
        if creator:
            discord_handle = creator.get("discord_username")
    except Exception:
        pass
        
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="deck_detail.html",
        context={
            "active_nav": "commander",
            "current_lang": lang,
            "deck": deck,
            "is_owner": is_owner,
            "discord_handle": discord_handle,
            "user": user
        }
    )

@user_router.post("/api/user/settings")
async def update_user_settings(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    body = await request.json()
    new_name = (body.get("name") or "").strip()
    fav_format = (body.get("favorite_format") or "Commander / EDH").strip()
    
    db = get_mongo_db()
    update_fields = {
        "favorite_format": fav_format,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if new_name:
        update_fields["name"] = new_name
        # Update session display name as well
        request.session["user"]["name"] = new_name
        
    from bson import ObjectId
    user_filter = {"_id": ObjectId(user["id"])} if user.get("id") else {"google_sub": user.get("google_sub")}
    db["users"].update_one(
        user_filter,
        {"$set": update_fields}
    )
    return JSONResponse({"status": "updated", "name": new_name or user.get("name", "Player"), "favorite_format": fav_format})

@user_router.post("/api/saved-cards/toggle")
async def toggle_saved_card(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    body = await request.json()
    oracle_id = body.get("oracle_id")
    card_id = body.get("card_id")
    name = (body.get("name") or "").strip()
    slug = (body.get("slug") or "").strip()
    image_url = (body.get("image_url") or "").strip()
    set_name = (body.get("set_name") or "").strip()
    
    if not name:
        raise HTTPException(status_code=400, detail="Card name is required")
        
    db = get_mongo_db()
    query = {"user_id": user["id"]}
    if oracle_id:
        query["oracle_id"] = oracle_id
    elif card_id:
        query["card_id"] = card_id
    else:
        query["name"] = name
        
    existing = db["saved_cards"].find_one(query)
    if existing:
        db["saved_cards"].delete_one({"_id": existing["_id"]})
        return JSONResponse({"status": "removed", "saved": False})
    else:
        now = datetime.now(timezone.utc).isoformat()
        db["saved_cards"].insert_one({
            "user_id": user["id"],
            "oracle_id": oracle_id,
            "card_id": card_id,
            "name": name,
            "slug": slug,
            "image_url": image_url,
            "set_name": set_name,
            "saved_at": now
        })
        return JSONResponse({"status": "saved", "saved": True})

@user_router.post("/api/saved-cards/push-to-deck")
async def push_saved_card_to_deck(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    body = await request.json()
    deck_id = body.get("deck_id")
    card_item = body.get("card") # {oracle_id, name, slug, image_url, count}
    
    if not deck_id or not card_item:
        raise HTTPException(status_code=400, detail="deck_id and card are required")
        
    db = get_mongo_db()
    deck = db["decks"].find_one({"deck_id": deck_id, "user_id": user["id"]})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
        
    cards = deck.get("cards", [])
    card_name = card_item.get("name")
    oracle_id = card_item.get("oracle_id")
    
    # Check if already in deck
    found = False
    for c in cards:
        if (oracle_id and c.get("oracle_id") == oracle_id) or (c.get("name", "").lower() == card_name.lower()):
            c["count"] = c.get("count", 1) + 1
            found = True
            break
            
    if not found:
        cards.append({
            "oracle_id": oracle_id,
            "name": card_name,
            "printing_slug": card_item.get("slug") or card_item.get("printing_slug"),
            "image_normal": card_item.get("image_url") or card_item.get("image_normal"),
            "count": card_item.get("count", 1)
        })
        
    now = datetime.now(timezone.utc).isoformat()
    db["decks"].update_one(
        {"deck_id": deck_id, "user_id": user["id"]},
        {
            "$set": {
                "cards": cards,
                "card_count": sum(c.get("count", 1) for c in cards),
                "updated_at": now
            }
        }
    )
    return JSONResponse({"status": "added", "deck_name": deck.get("name")})

@user_router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/auth/login?next=/dashboard", status_code=303)
    
    from bson import ObjectId
    db = get_mongo_db()
    user_doc = {}
    if user.get("id"):
        try:
            user_doc = db["users"].find_one({"_id": ObjectId(user["id"])}) or {}
        except Exception:
            pass
    if not user_doc and user.get("google_sub"):
        user_doc = db["users"].find_one({"google_sub": user["google_sub"]}) or {}
    decks = list(db["decks"].find(
        {"user_id": user["id"]}
    ).sort("updated_at", -1))
    saved_cards = list(db["saved_cards"].find(
        {"user_id": user["id"]}
    ).sort("saved_at", -1))
    
    lang = i18n.get_locale(request)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_nav": "dashboard",
            "current_lang": lang,
            "profile": user_doc,
            "decks": decks,
            "deck_count": len(decks),
            "saved_cards": saved_cards,
            "saved_card_count": len(saved_cards)
        }
    )
