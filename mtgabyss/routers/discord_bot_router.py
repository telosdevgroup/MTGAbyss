"""
discord_bot_router.py — Unified AvaScry Discord Slash Commands & HTTP Interactions.

Receives interaction webhooks directly from Discord (POST /api/discord/interactions),
verifies Ed25519 signatures with zero external socket daemons, and provides rich embeds
for Necromunda (/necro), Star Wars: Unlimited (/swu), and Minecraft (/mc).
"""

import os
import re
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import JSONResponse
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from db_mongo import get_mongo_db
from mtgabyss.routers.necromunda_router import get_necromunda_db
from mtgabyss.swu_router import get_swu_db

discord_bot_router = APIRouter(prefix="/api/discord", tags=["Discord Bot"])

DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()

def verify_discord_signature(signature_hex: str, timestamp: str, body_bytes: bytes, public_key_hex: str) -> bool:
    """Verifies Discord Ed25519 signature per Discord developer specification."""
    if not signature_hex or not timestamp or not public_key_hex:
        return False
    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
        verify_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        verify_key.verify(sig_bytes, timestamp.encode("utf-8") + body_bytes)
        return True
    except (InvalidSignature, ValueError, Exception):
        return False

def handle_necro_command(subcommand: str, options: Dict[str, Any]) -> Dict[str, Any]:
    db = get_necromunda_db()
    query = options.get("name", "").strip()
    if not query:
        return {"content": "⚠️ Please provide a weapon name. Example: `/necro weapon bolter`"}

    regex = re.compile(re.escape(query), re.IGNORECASE)
    weapon = db.weapons.find_one({"name": regex}) or db.weapons.find_one({"slug": regex})

    if not weapon:
        return {"content": f"🔍 No Necromunda weapon found matching `{query}`."}

    name = weapon.get("name")
    slug = weapon.get("slug")
    category = weapon.get("category", "Weapon")
    cost = weapon.get("cost_credits", 0)
    rarity = weapon.get("rarity", "-")
    traits = ", ".join(weapon.get("traits", [])) or "None"
    url = f"https://necromunda.avascry.com/weapon/{slug}"

    r_s = weapon.get("range_short") or "-"
    r_l = weapon.get("range_long") or "-"
    acc_s = weapon.get("accuracy_short") or "-"
    acc_l = weapon.get("accuracy_long") or "-"
    str_val = weapon.get("strength") or "-"
    dmg = weapon.get("damage") or "-"
    ap = weapon.get("armor_piercing") or "-"
    ammo = weapon.get("ammo") or "-"

    embed = {
        "title": f"🔫 {name} ({category})",
        "url": url,
        "color": 0xff5722,
        "description": f"**Cost:** `{cost} credits` | **Rarity:** `{rarity}`\n**Traits:** {traits}",
        "fields": [
            {"name": "Range (S / L)", "value": f"{r_s} / {r_l}", "inline": True},
            {"name": "Acc (S / L)", "value": f"{acc_s} / {acc_l}", "inline": True},
            {"name": "Str / Dmg", "value": f"{str_val} / {dmg}", "inline": True},
            {"name": "AP", "value": str(ap), "inline": True},
            {"name": "Ammo Check", "value": str(ammo), "inline": True},
            {"name": "Database", "value": f"[View on Underhive Armory]({url})", "inline": True}
        ],
        "footer": {
            "text": "AvaScry Underhive Armory • necromunda.avascry.com"
        }
    }
    return {"embeds": [embed]}

def handle_swu_command(subcommand: str, options: Dict[str, Any]) -> Dict[str, Any]:
    db = get_swu_db()
    query = options.get("name", "").strip()
    if not query:
        return {"content": "⚠️ Please provide a card name. Example: `/swu card luke`"}

    regex = re.compile(re.escape(query), re.IGNORECASE)
    card = db.cards.find_one({"title": regex}) or db.cards.find_one({"name": regex}) or db.cards.find_one({"slug": regex})

    if not card:
        return {"content": f"🔍 No Star Wars: Unlimited card found matching `{query}`."}

    title = card.get("title") or card.get("name")
    subtitle = card.get("subtitle") or ""
    slug = card.get("slug")
    card_type = card.get("type", "Card")
    cost = card.get("cost")
    power = card.get("power")
    hp = card.get("hp")
    aspects = ", ".join(card.get("aspects", [])) or "Neutral"
    text = (card.get("text") or card.get("rules") or "").strip()
    url = f"https://swu.avascry.com/card/{slug}"

    aspect_colors = {
        "Vigilance": 0x38bdf8,
        "Command": 0x22c55e,
        "Aggression": 0xef4444,
        "Cunning": 0xfacc15,
        "Heroism": 0xf8fafc,
        "Villainy": 0x0f172a
    }
    primary_aspect = (card.get("aspects") or ["Heroism"])[0]
    color = aspect_colors.get(primary_aspect, 0xfacc15)

    embed_title = f"{title}: {subtitle}" if subtitle else title
    embed = {
        "title": f"⚡ {embed_title}",
        "url": url,
        "color": color,
        "description": f"**Type:** {card_type} | **Aspects:** {aspects}",
        "fields": []
    }
    if cost is not None:
        embed["fields"].append({"name": "Cost", "value": f"{cost} ⬡", "inline": True})
    if power is not None and hp is not None:
        embed["fields"].append({"name": "Stats (P / HP)", "value": f"{power} / {hp}", "inline": True})
    if text:
        short_text = text[:300] + ("..." if len(text) > 300 else "")
        embed["fields"].append({"name": "Ability", "value": short_text, "inline": False})

    embed["fields"].append({"name": "Official Entry", "value": f"[View Full Details & Rulings]({url})", "inline": False})
    
    art = card.get("art_front") or card.get("front_image")
    if art and art.startswith("http"):
        embed["thumbnail"] = {"url": art}

    embed["footer"] = {"text": "AvaScry Star Wars Unlimited • swu.avascry.com"}
    return {"embeds": [embed]}

def handle_minecraft_command(subcommand: str, options: Dict[str, Any]) -> Dict[str, Any]:
    db = get_mongo_db()
    query = options.get("name", "").strip()
    if not query:
        return {"content": "⚠️ Please provide an item or block name. Example: `/mc item redstone`"}

    regex = re.compile(re.escape(query), re.IGNORECASE)
    mc_db = db.client["avascry_minecraft"] if hasattr(db, "client") else db
    item = (
        mc_db.items.find_one({"facts.display_name": regex})
        or mc_db.items.find_one({"slug": regex})
        or mc_db.items.find_one({"entity_id": regex})
    )

    if not item:
        return {"content": f"🔍 No Minecraft item found matching `{query}`."}

    facts = item.get("facts") or {}
    name = facts.get("display_name") or item.get("slug", "").replace("-", " ").title()
    slug = item.get("slug")
    stack_size = facts.get("stack_size", 64)
    url = f"https://minecraft.avascry.com/item/{slug}"

    embed = {
        "title": f"⛏️ {name}",
        "url": url,
        "color": 0x10b981,
        "description": f"**Item ID:** `{item.get('entity_id', slug)}` | **Max Stack:** `{stack_size}`",
        "fields": [
            {"name": "Item Specs", "value": f"[View Crafting Chain & Palette Matches]({url})", "inline": False}
        ],
        "footer": {
            "text": "AvaScry Minecraft Database • minecraft.avascry.com"
        }
    }
    return {"embeds": [embed]}

@discord_bot_router.post("/interactions")
async def discord_interactions(request: Request):
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")
    body_bytes = await request.body()

    # If DISCORD_PUBLIC_KEY is configured, enforce strict cryptographic check
    pub_key = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()
    if pub_key:
        if not verify_discord_signature(signature, timestamp, body_bytes, pub_key):
            raise HTTPException(status_code=401, detail="Invalid request signature")

    import json
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    interaction_type = data.get("type")

    # Discord PING (Type 1)
    if interaction_type == 1:
        return JSONResponse({"type": 1})

    # Discord APPLICATION_COMMAND (Type 2)
    if interaction_type == 2:
        cmd_data = data.get("data", {})
        root_command = cmd_data.get("name", "").lower()

        options_list = cmd_data.get("options", [])
        subcommand = ""
        param_dict = {}

        if options_list and "options" in options_list[0]:
            subcommand = options_list[0].get("name", "")
            for opt in options_list[0].get("options", []):
                param_dict[opt.get("name")] = opt.get("value")
        else:
            for opt in options_list:
                param_dict[opt.get("name")] = opt.get("value")

        response_data = {}
        if root_command in ("necro", "necromunda"):
            response_data = handle_necro_command(subcommand, param_dict)
        elif root_command in ("swu", "starwars"):
            response_data = handle_swu_command(subcommand, param_dict)
        elif root_command in ("mc", "minecraft"):
            response_data = handle_minecraft_command(subcommand, param_dict)
        else:
            response_data = {"content": f"AvaScry Bot active. Unknown command: `{root_command}`."}

        # Type 4: CHANNEL_MESSAGE_WITH_SOURCE
        return JSONResponse({
            "type": 4,
            "data": response_data
        })

    return JSONResponse({"type": 4, "data": {"content": "Unsupported interaction type."}})
