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

def handle_mtg_command(subcommand: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Handles /mtg or /card command looking up Magic: The Gathering cards."""
    db = get_mongo_db()
    query = options.get("name", "").strip()
    if not query:
        return {"content": "⚠️ Please provide a card name. Example: `/mtg card Sol Ring`"}

    regex = re.compile(re.escape(query), re.IGNORECASE)
    card = db.cards.find_one({"name": regex, "lang": "en"}) or db.cards.find_one({"slug": regex, "lang": "en"})
    if not card:
        card = db.cards.find_one({"name": regex}) or db.cards.find_one({"slug": regex})

    if not card:
        return {"content": f"🔍 No Magic card found matching `{query}`."}

    name = card.get("name", "Unknown Card")
    mana_cost = card.get("mana_cost", "")
    type_line = card.get("type_line", "")
    oracle_text = card.get("oracle_text", "")
    set_code = (card.get("set") or "").upper()
    set_name = card.get("set_name") or set_code
    slug = card.get("slug") or name.lower().replace(" ", "-")

    url = f"https://avascry.com/card/{slug}"

    # Determine embed color by card colors
    colors = card.get("colors") or []
    if len(colors) > 1:
        color = 0xfacc15  # Gold / Multicolor
    elif "W" in colors:
        color = 0xf8fafc
    elif "U" in colors:
        color = 0x38bdf8
    elif "B" in colors:
        color = 0x64748b
    elif "R" in colors:
        color = 0xef4444
    elif "G" in colors:
        color = 0x22c55e
    elif "Artifact" in type_line:
        color = 0x94a3b8
    elif "Land" in type_line:
        color = 0xa16207
    else:
        color = 0x6366f1

    title_display = f"✨ {name} {mana_cost}".strip()
    embed = {
        "title": title_display,
        "url": url,
        "color": color,
        "description": f"**{type_line}**\n\n{oracle_text}" if oracle_text else f"**{type_line}**",
        "fields": [
            {"name": "Set", "value": f"{set_name} (`{set_code}`)", "inline": True},
        ]
    }

    # Add Power/Toughness or Loyalty if present
    if card.get("power") is not None and card.get("toughness") is not None:
        embed["fields"].append({"name": "P / T", "value": f"{card.get('power')} / {card.get('toughness')}", "inline": True})
    elif card.get("loyalty") is not None:
        embed["fields"].append({"name": "Loyalty", "value": str(card.get("loyalty")), "inline": True})

    embed["fields"].append({"name": "Database", "value": f"[View Rulings, Prints & Visual Graph]({url})", "inline": False})

    # Images - display full card image prominently plus avatar thumbnail
    img_uris = card.get("image_uris")
    if not img_uris and card.get("card_faces"):
        img_uris = card["card_faces"][0].get("image_uris") or {}
    img_uris = img_uris or {}
    
    full_card_url = img_uris.get("normal") or img_uris.get("large")
    art_crop_url = img_uris.get("art_crop")
    
    if full_card_url:
        embed["image"] = {"url": full_card_url}
    if art_crop_url:
        embed["thumbnail"] = {"url": art_crop_url}

    # Fetch oldest printing for visual comparison (Alpha/Beta/first printing vs modern)
    embeds = [embed]
    oracle_id = card.get("oracle_id")
    if oracle_id:
        try:
            oldest_docs = list(
                db.cards.find({"oracle_id": oracle_id, "lang": "en"})
                .sort("released_at", 1)
                .limit(1)
            )
            if oldest_docs:
                oldest_card = oldest_docs[0]
                old_img_uris = oldest_card.get("image_uris")
                if not old_img_uris and oldest_card.get("card_faces"):
                    old_img_uris = oldest_card["card_faces"][0].get("image_uris") or {}
                old_img_uris = old_img_uris or {}
                old_card_url = old_img_uris.get("normal") or old_img_uris.get("large")

                # If oldest printing has a valid image and is a different printing from current
                if old_card_url and (oldest_card.get("id") != card.get("id") or full_card_url != old_card_url):
                    old_set_name = oldest_card.get("set_name") or (oldest_card.get("set") or "").upper()
                    old_year = (oldest_card.get("released_at") or "")[:4]
                    year_label = f" ({old_year})" if old_year else ""

                    embed["footer"] = {
                        "text": f"AvaScry • Left: {set_name} | Right: {old_set_name}{year_label} (Original)"
                    }

                    # Discord groups embeds sharing the exact same URL into a multi-image gallery/collage
                    old_embed = {
                        "url": url,
                        "image": {"url": old_card_url}
                    }
                    embeds.append(old_embed)
        except Exception:
            pass

    if "footer" not in embed:
        embed["footer"] = {"text": "AvaScry Magic Engine • avascry.com"}

    return {"embeds": embeds}

def handle_dominion_command(subcommand: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Handles /dom or /dominion command looking up Dominion kingdom cards."""
    from mtgabyss.dominion_router import format_dominion_rules_plain, format_expansion_name
    client = get_mongo_db().client
    dom_db = client["avascry_dominion"]
    query = options.get("name", "").strip()
    if not query:
        return {"content": "⚠️ Please provide a card name. Example: `/dom card Village`"}

    all_cards = list(dom_db.cards.find({}, {"_id": 0}))
    q_lower = query.lower()

    # Exact match first, then prefix match, then substring match
    card = next((c for c in all_cards if c.get("name", "").lower() == q_lower or c.get("slug", "").lower() == q_lower), None)
    if not card:
        card = next((c for c in all_cards if c.get("name", "").lower().startswith(q_lower) or c.get("slug", "").lower().startswith(q_lower)), None)
    if not card:
        card = next((c for c in all_cards if q_lower in c.get("name", "").lower() or q_lower in c.get("slug", "").lower()), None)

    if not card:
        return {"content": f"🔍 No Dominion card found matching `{query}`."}

    name = card.get("name", "Unknown Card")
    slug = card.get("slug", "")
    url = f"https://dominion.avascry.com/card/{slug}"

    # Resolve richest card version (preferring 2nd edition or standard expansion versions)
    versions = list(dom_db.card_versions.find({"card_id": f"card:{slug}"}))
    def score_version(v: dict) -> int:
        ed = str(v.get("edition", "")).lower()
        stag = str(v.get("expansion_tag", "")).lower()
        score = 0
        if "2e" in ed or "2nd" in stag:
            score += 10
        if "removed" in stag:
            score -= 5
        return score

    best_v = sorted(versions, key=score_version, reverse=True)[0] if versions else {}

    # Types
    types = best_v.get("types") or card.get("card_kinds") or []
    types_str = " - ".join([t.title() for t in types]) if isinstance(types, list) else str(types).title()

    # Cost
    cost_obj = best_v.get("cost") or {}
    cost_parts = []
    if cost_obj.get("coins") is not None:
        cost_parts.append(f"${cost_obj['coins']}")
    if cost_obj.get("debt"):
        cost_parts.append(f"{cost_obj['debt']} Debt")
    if cost_obj.get("potion"):
        cost_parts.append("1 Potion")
    cost_display = f" ({', '.join(cost_parts)})" if cost_parts else ""

    # Expansion
    exp_map = {e.get("set_tag", "").lower(): e.get("name") for e in dom_db.expansions.find({}, {"set_tag": 1, "name": 1})}
    exp_tag = best_v.get("expansion_tag", "") or card.get("expansion", "")
    expansion = format_expansion_name(exp_tag, exp_map=exp_map) if exp_tag else "Base"

    # Rules text
    raw_text = best_v.get("printed_rules_text", "") or card.get("text", "") or card.get("description", "")
    text = format_dominion_rules_plain(raw_text)

    # Embed color based on primary type
    color = 0x2563eb  # Action blue default
    types_lower = types_str.lower()
    if "treasure" in types_lower:
        color = 0xeab308  # Gold
    elif "victory" in types_lower:
        color = 0x16a34a  # Green
    elif "curse" in types_lower:
        color = 0x9333ea  # Purple
    elif "attack" in types_lower:
        color = 0xef4444  # Red
    elif "night" in types_lower:
        color = 0x1e1b4b  # Dark slate
    elif "duration" in types_lower:
        color = 0xf97316  # Orange
    elif "reaction" in types_lower:
        color = 0x0284c7  # Light blue

    desc_lines = [f"**Expansion:** {expansion}"]
    if types_str:
        desc_lines.append(f"**Type:** {types_str}")
    if text:
        desc_lines.append(f"\n{text}")

    embed = {
        "title": f"🏰 {name}{cost_display}",
        "url": url,
        "color": color,
        "description": "\n".join(desc_lines),
        "fields": [
            {"name": "Codex Entry", "value": f"[View Official Errata & Combos]({url})", "inline": False}
        ]
    }

    # High-resolution canonical image URL
    canonical_img = f"https://dominion.avascry.com/images/{slug}.jpg"
    embed["image"] = {"url": canonical_img}

    embed["footer"] = {"text": "AvaScry Dominion Codex • dominion.avascry.com"}
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

    # Check public key (accept active env var or fallback to current application key)
    configured_key = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()
    active_keys = [k for k in [configured_key, "1deb34918d8cb7c6598e89ec11ec5b1bc65077db56f7a38b266927dc602e542a"] if k]
    
    if active_keys:
        verified = any(verify_discord_signature(signature, timestamp, body_bytes, k) for k in active_keys)
        if not verified:
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
        if root_command in ("mtg", "card", "magic"):
            response_data = handle_mtg_command(subcommand, param_dict)
        elif root_command in ("dom", "dominion"):
            response_data = handle_dominion_command(subcommand, param_dict)
        elif root_command in ("necro", "necromunda"):
            response_data = handle_necro_command(subcommand, param_dict)
        elif root_command in ("swu", "starwars"):
            response_data = handle_swu_command(subcommand, param_dict)
        elif root_command in ("mc", "minecraft"):
            response_data = handle_minecraft_command(subcommand, param_dict)
        else:
            response_data = {
                "content": (
                    f"AvaScry Gaming Bot active. Unknown command: `{root_command}`.\n"
                    "Supported games:\n"
                    "• `/mtg card <name>` — Magic: The Gathering\n"
                    "• `/dom card <name>` — Dominion Kingdom Cards\n"
                    "• `/swu card <name>` — Star Wars: Unlimited\n"
                    "• `/necro weapon <name>` — Necromunda Armory\n"
                    "• `/mc item <name>` — Minecraft Codex"
                )
            }

        # Type 4: CHANNEL_MESSAGE_WITH_SOURCE
        return JSONResponse({
            "type": 4,
            "data": response_data
        })

    return JSONResponse({"type": 4, "data": {"content": "Unsupported interaction type."}})
