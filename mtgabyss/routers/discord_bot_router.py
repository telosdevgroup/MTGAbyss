"""
discord_bot_router.py — Unified AvaScry Discord Slash Commands & HTTP Interactions.

Receives interaction webhooks directly from Discord (POST /api/discord/interactions),
verifies Ed25519 signatures with zero external socket daemons, and provides rich embeds
for Necromunda (/necro), Star Wars: Unlimited (/swu), and Minecraft (/mc).
"""

import os
import re
import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from db_mongo import get_mongo_db
from mtgabyss.routers.necromunda_router import get_necromunda_db
from mtgabyss.swu_router import get_swu_db

discord_bot_router = APIRouter(prefix="/api/discord", tags=["Discord Bot"])

DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()
DISCORD_APPLICATION_ID = os.environ.get("DISCORD_APPLICATION_ID", "1547376653129224282").strip()

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

def fetch_image_bytes(url: str, timeout: float = 3.141, max_retries: int = 2) -> Optional[bytes]:
    """Fetches image bytes using prime timeout and prime-jitter backoff retry ladder."""
    if not url:
        return None
    # Check local static/images first if it references avascry.com
    if "avascry.com/images/normal/" in url:
        fname = url.split("avascry.com/images/normal/")[-1].split("?")[0]
        local_path = os.path.join("public", "images", "normal", fname)
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    return f.read()
            except Exception:
                pass

    from mtgabyss.shared.prime_jitter import get_prime_backoff
    import urllib.request
    import time

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception as e:
            if attempt < max_retries:
                delay = get_prime_backoff(attempt)
                time.sleep(delay)
            else:
                print(f"[DISCORD-BOT] Failed to fetch image bytes for {url} (attempt {attempt+1}): {e}", flush=True)
    return None

def log_discord(msg: str):
    """Writes timestamped diagnostic message to discord.log and stdout."""
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    print(f"[DISCORD-BOT] {msg}", flush=True)
    try:
        os.makedirs(r"C:\avascry_data\logs", exist_ok=True)
        with open(r"C:\avascry_data\logs\discord.log", "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass

def with_discord_bot_utm(url: str) -> str:
    """Appends utm_source=discord_bot to outbound web URLs."""
    if not url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source=discord_bot"

def update_discord_original_interaction_with_attachment(app_id: str, interaction_token: str, response_data: dict, img_url: str):
    """Sends deferred message update with direct image attachment rendering cleanly across all clients."""
    log_discord(f"Starting background attachment update for {img_url} (app_id={app_id})")
    try:
        import requests
        import json
        img_bytes = fetch_image_bytes(img_url)

        # Build clean message text from embed fields
        embed = response_data.get("embeds", [{}])[0] if response_data.get("embeds") else {}
        title = embed.get("title", "")
        desc = embed.get("description", "")
        fields = embed.get("fields", [])

        lines = []
        if title:
            lines.append(f"**{title}**")
        if desc:
            lines.append(desc)
        for f in fields:
            f_name = f.get("name", "")
            f_val = f.get("value", "")
            if f_name and f_val:
                lines.append(f"• **{f_name}**: {f_val}")

        text_content = "\n\n".join(lines) if lines else response_data.get("content", "")

        patch_payload = {
            "content": text_content,
            "embeds": []  # Clear embeds so Discord renders clean text or message body
        }
        patch_url = f"https://discord.com/api/v10/webhooks/{app_id}/{interaction_token}/messages/@original"

        if not img_bytes:
            log_discord(f"Background update: could not fetch image for {img_url}, falling back to text-only")
            resp = requests.patch(
                patch_url,
                json=patch_payload,
                timeout=10.0
            )
            log_discord(f"Background text fallback status: {resp.status_code}")
            return

        fname = "card.png" if img_url.lower().endswith(".png") else "card.jpg"
        mime = "image/png" if fname.endswith(".png") else "image/jpeg"

        resp = requests.patch(
            patch_url,
            data={"payload_json": json.dumps(patch_payload)},
            files={"files[0]": (fname, img_bytes, mime)},
            timeout=10.0
        )
        try:
            rjson = resp.json()
            att_len = len(rjson.get("attachments", []))
            log_discord(f"Background edit status: {resp.status_code}, attachments: {att_len}")
        except Exception:
            log_discord(f"Background edit status: {resp.status_code}")
    except Exception as e:
        log_discord(f"Background update exception: {e}")





def handle_necro_command(subcommand: str, options: Dict[str, Any]) -> Dict[str, Any]:
    db = get_necromunda_db()
    subcmd = (subcommand or "").strip().lower()

    # Check if this is a Lasting Injury roll or lookup
    is_injury = (
        subcmd in ("injury", "roll-injury", "lasting-injury")
        or options.get("action") in ("injury", "roll-injury")
        or options.get("name", "").strip().lower() in ("injury", "roll-injury", "lasting-injury")
        or "roll" in options
    )
    if is_injury:
        import random
        from mtgabyss.data.necromunda_injuries import get_injury

        raw_roll = options.get("roll")
        d1, d2, d66 = 0, 0, 0
        is_manual = False
        if raw_roll:
            try:
                r_int = int(raw_roll)
                t_tens = r_int // 10
                t_ones = r_int % 10
                if 1 <= t_tens <= 6 and 1 <= t_ones <= 6:
                    d1, d2, d66 = t_tens, t_ones, r_int
                    is_manual = True
            except (ValueError, TypeError):
                pass

        if not is_manual:
            d1 = random.randint(1, 6)
            d2 = random.randint(1, 6)
            d66 = d1 * 10 + d2

        injury = get_injury(d66) or {
            "title": f"Unknown Result ({d66})",
            "category": "Unclassified",
            "effect": "Fighter crawls back into the air vents. Consult Arbites.",
            "flavor": "Unusual underhive anomaly.",
            "remedy": "Visit Rogue Doc.",
            "severity": "moderate",
            "color": 0xf59e0b,
            "emoji": "🎲"
        }

        fighter_name = options.get("fighter") or ""
        raw_name = options.get("name", "").strip()
        if not fighter_name and raw_name and raw_name.lower() not in ("injury", "roll-injury", "lasting-injury"):
            fighter_name = raw_name

        title_prefix = f"🎲 D66 [{d1}, {d2}] ➔ {d66}"
        embed_title = f"{title_prefix}: {injury['emoji']} {injury['title']}"
        if fighter_name:
            desc_header = f"**Casualty Report:** `{fighter_name}`\n*{injury['flavor']}*"
        else:
            desc_header = f"*{injury['flavor']}*"

        url = with_discord_bot_utm("https://necromunda.avascry.com/guides/underhive-black-market-and-exotic-beasts")

        embed = {
            "title": embed_title,
            "url": url,
            "color": injury["color"],
            "description": desc_header,
            "fields": [
                {"name": "Mechanical Effect", "value": f"**{injury['effect']}**", "inline": False},
                {"name": "Category", "value": f"`{injury['category']}`", "inline": True},
                {"name": "Roster Status", "value": "In Recovery" if injury["severity"] != "fatal" else "**DEAD** (Remove from Roster)", "inline": True},
                {"name": "Campaign Remedy", "value": injury["remedy"], "inline": False},
            ],
            "footer": {
                "text": "AvaScry Underhive Tactica • Core Rules D66 Table • necromunda.avascry.com"
            }
        }
        return {"embeds": [embed]}

    query = options.get("name", "").strip()

    # Subcommand: trait
    if subcmd == "trait":
        if not query:
            return {"content": "⚠️ Please provide a trait name. Example: `/necro trait Rapid Fire`"}
        regex = re.compile(re.escape(query), re.IGNORECASE)
        trait = db.traits.find_one({"name": regex}) or db.traits.find_one({"slug": regex})
        if not trait:
            return {"content": f"🔍 No Necromunda weapon trait found matching `{query}`."}

        name = trait.get("name", query)
        slug = trait.get("slug", "")
        rules_text = trait.get("rules_text", "No rules text recorded.")
        faq = trait.get("faq", "")
        url = with_discord_bot_utm(f"https://necromunda.avascry.com/trait/{slug}") if slug else with_discord_bot_utm("https://necromunda.avascry.com/traits")

        fields = [{"name": "Rules Effect", "value": rules_text, "inline": False}]
        if faq:
            fields.append({"name": "FAQ & Clarification", "value": faq, "inline": False})
        fields.append({"name": "Database", "value": f"[View on Underhive Trait Lexicon]({url})", "inline": True})

        embed = {
            "title": f"⚡ Trait: {name}",
            "url": url,
            "color": 0xeab308,
            "description": f"Official Underhive weapon trait and special rule.",
            "fields": fields,
            "footer": {"text": "AvaScry Underhive Trait Lexicon • necromunda.avascry.com"}
        }
        return {"embeds": [embed]}

    # Subcommand: house
    if subcmd == "house":
        if not query:
            return {"content": "⚠️ Please provide a Clan House name. Example: `/necro house Van Saar`"}
        regex = re.compile(re.escape(query), re.IGNORECASE)
        house = db.houses.find_one({"name": regex}) or db.houses.find_one({"slug": regex})
        if not house:
            return {"content": f"🔍 No Necromunda Clan House found matching `{query}`."}

        name = house.get("name", query)
        title = house.get("title", "Clan House")
        slug = house.get("slug", "")
        specialty = house.get("specialty", "Tactical Skirmish")
        sig_weapons = ", ".join(house.get("signature_weapons", [])) or "Standard Issue"
        primary_skills = ", ".join(house.get("primary_skills", [])) or "Varied"
        lore = house.get("lore", "")
        if len(lore) > 280:
            lore = lore[:277] + "..."
        url = with_discord_bot_utm(f"https://necromunda.avascry.com/house/{slug}") if slug else with_discord_bot_utm("https://necromunda.avascry.com/houses")

        display_name = name if name.lower().startswith("house ") else f"House {name}"
        embed = {
            "title": f"🏛️ {display_name} ({title})",
            "url": url,
            "color": 0x3b82f6,
            "description": lore,
            "fields": [
                {"name": "Doctrine & Specialty", "value": f"`{specialty}`", "inline": True},
                {"name": "Primary Skills", "value": primary_skills, "inline": True},
                {"name": "Favored Arsenal", "value": sig_weapons, "inline": False},
                {"name": "Database", "value": f"[View Clan Gang Profile]({url})", "inline": True}
            ],
            "footer": {"text": "AvaScry Underhive Clan Registry • necromunda.avascry.com"}
        }
        return {"embeds": [embed]}

    # Subcommand: skill
    if subcmd == "skill":
        if not query:
            return {"content": "⚠️ Please provide a skill name. Example: `/necro skill Fast Shot`"}
        regex = re.compile(re.escape(query), re.IGNORECASE)
        skill = db.skills.find_one({"name": regex}) or db.skills.find_one({"slug": regex})
        if not skill:
            return {"content": f"🔍 No Necromunda skill found matching `{query}`."}

        name = skill.get("name", query)
        tree = skill.get("tree", "General")
        slug = skill.get("slug", "")
        rules_text = skill.get("rules_text", "No rules text recorded.")
        tactics = skill.get("tactics", "")
        url = with_discord_bot_utm(f"https://necromunda.avascry.com/skill/{slug}") if slug else with_discord_bot_utm("https://necromunda.avascry.com/skills")

        fields = [{"name": "Discipline", "value": f"`{tree}`", "inline": True}]
        fields.append({"name": "Rules Effect", "value": rules_text, "inline": False})
        if tactics:
            fields.append({"name": "Tactical Application", "value": tactics, "inline": False})
        fields.append({"name": "Database", "value": f"[View Skill Detail]({url})", "inline": True})

        embed = {
            "title": f"🧠 Skill: {name} [{tree}]",
            "url": url,
            "color": 0x10b981,
            "description": f"Official Underhive fighter capability and skill tree rule.",
            "fields": fields,
            "footer": {"text": "AvaScry Underhive Skill Matrix • necromunda.avascry.com"}
        }
        return {"embeds": [embed]}

    # Subcommand: equipment
    if subcmd in ("equipment", "gear", "wargear"):
        if not query:
            return {"content": "⚠️ Please provide equipment or wargear name. Example: `/necro equipment Armoured Undersuit`"}
        regex = re.compile(re.escape(query), re.IGNORECASE)
        eq = db.equipment.find_one({"name": regex}) or db.equipment.find_one({"slug": regex})
        if not eq:
            return {"content": f"🔍 No Necromunda equipment found matching `{query}`."}

        name = eq.get("name", query)
        category = eq.get("category", "Equipment")
        cost = eq.get("cost_credits", 0)
        rarity = eq.get("rarity", "-")
        rules_text = eq.get("rules_text", "")
        desc = eq.get("description", "")
        slug = eq.get("slug", "")
        url = with_discord_bot_utm(f"https://necromunda.avascry.com/equipment/{slug}") if slug else with_discord_bot_utm("https://necromunda.avascry.com/equipment")

        fields = [
            {"name": "Cost / Rarity", "value": f"`{cost} creds` | `{rarity}`", "inline": True},
            {"name": "Category", "value": f"`{category}`", "inline": True}
        ]
        if rules_text:
            fields.append({"name": "Rules", "value": rules_text, "inline": False})
        fields.append({"name": "Database", "value": f"[View Trading Post Listing]({url})", "inline": True})

        embed = {
            "title": f"🛡️ {name} ({category})",
            "url": url,
            "color": 0x8b5cf6,
            "description": desc or rules_text or "Underhive Trading Post equipment.",
            "fields": fields,
            "footer": {"text": "AvaScry Underhive Trading Post • necromunda.avascry.com"}
        }
        return {"embeds": [embed]}

    # Default / Subcommand: weapon (or flat command fallback)
    if not query:
        return {"content": "⚠️ Please provide a weapon name or use `/necro injury`. Example: `/necro weapon bolter`"}

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
    url = with_discord_bot_utm(f"https://necromunda.avascry.com/weapon/{slug}")

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
        "thumbnail": {
            "url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f52b.png"
        },
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
    # Prefer canonical / standard printing (Normal variant, earliest set)
    card = (
        db.cards.find_one({"title": regex, "variant_type": "Normal"})
        or db.cards.find_one({"name": regex, "variant_type": "Normal"})
        or db.cards.find_one({"title": regex, "variant_type": {"$in": ["Normal", None, ""]}})
        or db.cards.find_one({"name": regex, "variant_type": {"$in": ["Normal", None, ""]}})
        or db.cards.find_one({"title": regex})
        or db.cards.find_one({"name": regex})
        or db.cards.find_one({"slug": regex})
    )

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
    url = with_discord_bot_utm(f"https://swu.avascry.com/card/{slug}")

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

    # Primary ("Oracle" / canonical print) card image
    front_img = card.get("art_front") or card.get("front_image")
    back_img = card.get("art_back") or card.get("back_image")

    if front_img and front_img.startswith("http"):
        embed["image"] = {"url": front_img}

    # Search for alternate art / premium variant (Showcase, Hyperspace, etc.)
    alt_matches = list(db.cards.find({"title": title, "subtitle": subtitle}))
    variants = [v for v in alt_matches if v.get("slug") != slug]

    def alt_priority(v):
        vt = str(v.get("variant_type") or "").lower()
        if "showcase" in vt:
            return 1
        if "hyperspace" in vt:
            return 2
        if "foil" in vt:
            return 3
        return 4

    variants.sort(key=alt_priority)
    alt_card = None
    for v in variants:
        v_art = v.get("art_front") or v.get("front_image")
        if v_art and v_art.startswith("http") and v_art != front_img:
            alt_card = v
            break

    embeds = [embed]
    paired_img = None
    paired_label = None

    set_code = (card.get("expansion") or {}).get("code") or card.get("set_code") or ""
    card_num = card.get("card_number") or card.get("number") or ""
    standard_label = f"{set_code} #{card_num} (Standard)" if set_code and card_num else "Standard"

    if alt_card:
        paired_img = alt_card.get("art_front") or alt_card.get("front_image")
        alt_vt = alt_card.get("variant_type") or "Alt Art"
        alt_set = (alt_card.get("expansion") or {}).get("code") or alt_card.get("set_code") or ""
        alt_num = alt_card.get("card_number") or alt_card.get("number") or ""
        paired_label = f"{alt_set} #{alt_num} ({alt_vt})" if alt_set and alt_num else f"{alt_vt} Art"
    elif card_type == "Leader" and back_img and back_img.startswith("http"):
        paired_img = back_img
        paired_label = "Deployed Leader Unit"

    if paired_img:
        embed["footer"] = {
            "text": f"AvaScry SWU • Left: {standard_label} | Right: {paired_label}"
        }
        # Discord groups multiple embeds with the exact same URL into a 2-column image collage
        paired_embed = {
            "url": url,
            "image": {"url": paired_img}
        }
        embeds.append(paired_embed)
    else:
        embed["footer"] = {"text": "AvaScry Star Wars Unlimited • swu.avascry.com"}

    return {"embeds": embeds}

def handle_mtg_visual_search(query: str) -> Dict[str, Any]:
    """Natural language visual search across 33,400+ blinded MTG artwork analyses."""
    db = get_mongo_db()
    clean_q = (query or "").strip()
    if not clean_q:
        return {"content": "⚠️ Please provide a visual expression to search. Example: `/mtg visual-search query:moody blue merfolk`"}

    tokens = [w.strip() for w in re.split(r"\s+", clean_q) if len(w.strip()) > 1]

    # 1. Try strict $and across tokens
    and_clauses = []
    for t in tokens[:5]:
        and_clauses.append({
            "$or": [
                {"vision_observations.visual_summary": {"$regex": re.escape(t), "$options": "i"}},
                {"vision_observations.subjects": {"$regex": re.escape(t), "$options": "i"}},
                {"vision_observations.dominant_colors": {"$regex": re.escape(t), "$options": "i"}},
                {"vision_observations.mood_keywords": {"$regex": re.escape(t), "$options": "i"}},
                {"vision_observations.style_descriptors": {"$regex": re.escape(t), "$options": "i"}},
                {"source.card_name": {"$regex": re.escape(t), "$options": "i"}}
            ]
        })

    docs = list(db.vl_art_analysis.find({"status": "complete", "$and": and_clauses}).limit(4))

    # 2. If strict $and finds nothing, fall back to $or across tokens
    if not docs and len(tokens) > 1:
        or_clauses = []
        for t in tokens[:5]:
            or_clauses.append({"vision_observations.visual_summary": {"$regex": re.escape(t), "$options": "i"}})
            or_clauses.append({"vision_observations.subjects": {"$regex": re.escape(t), "$options": "i"}})
            or_clauses.append({"vision_observations.dominant_colors": {"$regex": re.escape(t), "$options": "i"}})
            or_clauses.append({"vision_observations.mood_keywords": {"$regex": re.escape(t), "$options": "i"}})
        docs = list(db.vl_art_analysis.find({"status": "complete", "$or": or_clauses}).limit(4))

    if not docs:
        return {"content": f"🔍 No artwork found matching visual expression `{clean_q}`."}

    first_doc = docs[0]
    first_src = first_doc.get("source", {})
    primary_img = first_src.get("image_url", "").split("?")[0]

    fields = []
    for idx, d in enumerate(docs[:3], 1):
        src = d.get("source", {})
        obs = d.get("vision_observations", {})
        c_name = src.get("card_name", "Card")
        c_artist = src.get("artist", "Unknown Artist")
        c_set = (src.get("set") or "").upper()
        summary = (obs.get("visual_summary") or "")[:110]
        if len(obs.get("visual_summary") or "") > 110:
            summary += "..."
        colors = ", ".join(obs.get("dominant_colors", [])) or "N/A"
        moods = ", ".join(obs.get("mood_keywords", [])) or "N/A"
        ill_id = d.get("illustration_id", "")
        art_link = f"https://avascry.com/art/{ill_id}" if ill_id else "https://avascry.com"

        f_val = f"*{summary}*\n🎨 **Palette:** {colors} • **Mood:** {moods}\n🔗 **[View Art Graph & Neighbors]({with_discord_bot_utm(art_link)})**"
        fields.append({
            "name": f"{idx}. {c_name} — {c_artist} ({c_set})",
            "value": f_val,
            "inline": False
        })

    embed = {
        "title": f"🎨 Visual Art Search: \"{clean_q}\"",
        "url": with_discord_bot_utm(f"https://avascry.com/art/{first_doc.get('illustration_id')}"),
        "color": 0x38bdf8,
        "description": f"Found **{len(docs)}** artworks matching your visual expression across AvaScry's blinded vision corpus.",
        "fields": fields,
        "footer": {"text": "AvaScry Visual Intelligence • 33,400+ Blinded Art Analyses • avascry.com"}
    }
    if primary_img:
        embed["image"] = {"url": primary_img}
        embed["thumbnail"] = {"url": primary_img}

    return {"embeds": [embed]}


def handle_mtg_similar_art(card_name: str) -> Dict[str, Any]:
    """Finds visually similar MTG artwork by precomputed nearest neighbors."""
    db = get_mongo_db()
    from mtgabyss.shared.helpers import slugify

    clean_name = (card_name or "").strip()
    if not clean_name:
        return {"content": "⚠️ Please provide a card name to find similar art. Example: `/mtg similar-art card:Damnation`"}

    c_slug = slugify(clean_name)
    card = db.cards.find_one({"slug": c_slug, "lang": "en"}) or db.cards.find_one({"name": clean_name, "lang": "en"})
    if not card:
        regex = re.compile(re.escape(clean_name), re.IGNORECASE)
        card = db.cards.find_one({"name": regex, "lang": "en"}) or db.cards.find_one({"slug": regex, "lang": "en"})

    if not card:
        return {"content": f"🔍 No Magic card found matching `{clean_name}`."}

    resolved_name = card.get("name", clean_name)
    artist = card.get("artist", "Unknown Artist")
    set_code = (card.get("set") or "").upper()
    ill_id = card.get("illustration_id") or card.get("raw", {}).get("illustration_id")

    sim_doc = None
    if ill_id:
        sim_doc = db.vl_art_similarities.find_one({"illustration_id": ill_id})

    # If no precomputed similarity doc yet, fall back to visual search using card name
    if not sim_doc:
        return handle_mtg_visual_search(resolved_name)

    top_vibe = sim_doc.get("top_neighbors", {}).get("by_vibe", [])
    top_subject = sim_doc.get("top_neighbors", {}).get("by_subject", [])
    neighbors = top_vibe[:3] or top_subject[:3]

    if not neighbors:
        return handle_mtg_visual_search(resolved_name)

    primary_img = neighbors[0].get("image_url", "").split("?")[0]
    art_page_url = with_discord_bot_utm(f"https://avascry.com/art/{ill_id}")

    fields = []
    for idx, n in enumerate(neighbors, 1):
        n_name = n.get("card_name", "Card")
        n_artist = n.get("artist", "Unknown Artist")
        n_set = (n.get("set") or "").upper()
        n_ill_id = n.get("illustration_id", "")
        n_link = with_discord_bot_utm(f"https://avascry.com/art/{n_ill_id}") if n_ill_id else art_page_url

        fields.append({
            "name": f"{idx}. {n_name} ({n_set})",
            "value": f"**Artist:** {n_artist}\n🔗 **[Explore Artwork]({n_link})**",
            "inline": True
        })

    fields.append({
        "name": "Visual Knowledge Graph",
        "value": f"Explore complete nearest-neighbor vectors and lighting observations on **[AvaScry Visual Art Detail]({art_page_url})**.",
        "inline": False
    })

    embed = {
        "title": f"✨ Visually Similar Art: {resolved_name}",
        "url": art_page_url,
        "color": 0xec4899,
        "description": f"Card artwork sharing visual themes, lighting, and aesthetic composition with **{resolved_name}** (*{artist}*, `{set_code}`).",
        "fields": fields,
        "footer": {"text": "AvaScry Visual Intelligence • 3-Dimensional Multimodal Graph • avascry.com"}
    }
    if primary_img:
        embed["image"] = {"url": primary_img}
        embed["thumbnail"] = {"url": primary_img}

    return {"embeds": [embed]}


def handle_mtg_command(subcommand: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Handles /mtg or /card command looking up Magic: The Gathering cards."""
    subcmd = (subcommand or "").strip().lower()

    # Route 1: Visual Search (natural language expression)
    if subcmd in ("visual-search", "vibe-search", "art-search", "vibe") or "query" in options:
        q_val = options.get("query") or options.get("name") or options.get("expression") or ""
        return handle_mtg_visual_search(q_val)

    # Route 2: Similar Art (card-based nearest neighbors)
    if subcmd in ("similar-art", "similar", "vibe-neighbors") or "card" in options or options.get("action") == "similar":
        c_val = options.get("card") or options.get("name") or ""
        return handle_mtg_similar_art(c_val)

    # Route 3: Standard Card Lookup (Optimized <1ms indexed slug check)
    db = get_mongo_db()
    from mtgabyss.shared.helpers import slugify
    query = options.get("name", "").strip()
    if not query:
        return {"content": "⚠️ Please provide a card name. Example: `/mtg card Sol Ring`"}

    c_slug = slugify(query)
    card = db.cards.find_one({"slug": c_slug, "lang": "en"}) or db.cards.find_one({"name": query, "lang": "en"})
    if not card:
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

    url = with_discord_bot_utm(f"https://avascry.com/card/{slug}")

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

    from mtgabyss.shared.helpers import slugify
    c_slug = slug or slugify(name)
    printing_slug = card.get("printing_slug") or (f"{c_slug}-{set_code.lower()}" if set_code else c_slug)
    printing_url = with_discord_bot_utm(f"https://avascry.com/printing/{printing_slug}")

    title_display = f"✨ {name} {mana_cost}".strip()
    embed = {
        "title": title_display,
        "url": url,
        "color": color,
        "description": f"**{type_line}**\n\n{oracle_text}" if oracle_text else f"**{type_line}**",
        "fields": [
            {"name": "Set", "value": f"[{set_name} (`{set_code}`)]({printing_url})", "inline": True},
        ]
    }

    # Add Power/Toughness or Loyalty if present
    if card.get("power") is not None and card.get("toughness") is not None:
        embed["fields"].append({"name": "P / T", "value": f"{card.get('power')} / {card.get('toughness')}", "inline": True})
    elif card.get("loyalty") is not None:
        embed["fields"].append({"name": "Loyalty", "value": str(card.get("loyalty")), "inline": True})

    embed["fields"].append({"name": "Database", "value": f"[View Rulings, Prints & Visual Graph]({url})", "inline": False})

    # Resolve card image URL (prefer direct Scryfall CDN URI so Discordbot proxy bypasses Cloudflare challenge)
    def _get_card_image(card_doc: dict) -> str:
        # 1. Primary: High-resolution Scryfall CDN image
        img_uris = card_doc.get("image_uris") or {}
        if isinstance(img_uris, dict) and img_uris:
            cdn_url = img_uris.get("normal") or img_uris.get("large") or img_uris.get("png")
            if cdn_url and cdn_url.startswith("http"):
                return cdn_url

        from mtgabyss.shared.helpers import slugify
        try:
            from mtgabyss.routers.image_router import IMAGE_PREFIX_MAP
        except Exception:
            IMAGE_PREFIX_MAP = {"normal": {}, "large": {}}
        c_slug = slugify(card_doc.get("name") or "")
        set_slug = slugify(card_doc.get("set_name") or "")
        artist_slug = slugify(card_doc.get("artist") or "")
        c_num = str(card_doc.get("collector_number") or "").strip()
        set_code = str(card_doc.get("set") or "").lower()

        # Check exact filenames
        specific = f"{c_slug}-{set_slug}-{artist_slug}-{c_num}.jpg"
        if os.path.exists(os.path.join("public", "images", "normal", specific)):
            return f"https://avascry.com/images/normal/{specific}"

        # Check prefix map
        for prefix_try in [
            f"{c_slug}-{set_slug}-{c_num}" if c_num else None,
            f"{c_slug}-{set_code}-{c_num}" if c_num else None,
            f"{c_slug}-{set_slug}",
            f"{c_slug}-{set_code}"
        ]:
            if prefix_try and prefix_try in IMAGE_PREFIX_MAP.get("normal", {}):
                fname = IMAGE_PREFIX_MAP["normal"][prefix_try]
                return f"https://avascry.com/images/normal/{fname}"

        generic = f"{c_slug}.jpg"
        if os.path.exists(os.path.join("public", "images", "normal", generic)):
            return f"https://avascry.com/images/normal/{generic}"

        # Fallback to avascry canonical slug image URL
        return f"https://avascry.com/images/normal/{c_slug}.jpg"

    card_img_url = _get_card_image(card)
    if card_img_url:
        # Strip timestamp cache query string so Discord's image caching proxy resolves cleanly
        clean_img_url = card_img_url.split("?")[0] if "cards.scryfall.io" in card_img_url else card_img_url
        embed["image"] = {"url": clean_img_url}
        embed["thumbnail"] = {"url": clean_img_url}

    embed["footer"] = {"text": "AvaScry Magic Engine • avascry.com"}
    return {"embeds": [embed]}

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
    url = with_discord_bot_utm(f"https://dominion.avascry.com/card/{slug}")

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
    cost_str = ", ".join(cost_parts) if cost_parts else "$0"
    cost_display = f" ({cost_str})" if cost_parts else ""

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

    fields = [
        {"name": "Expansion", "value": expansion, "inline": True},
        {"name": "Cost", "value": cost_str, "inline": True},
    ]

    if types_str:
        fields.append({"name": "Type", "value": types_str, "inline": True})

    if text:
        # Blockquote formatting renders prominent and distinct in Discord embeds
        formatted_text = "\n".join(f"> {line}" for line in text.split("\n"))
        fields.append({"name": "Card Text", "value": formatted_text, "inline": False})

    fields.append({
        "name": "Codex Entry",
        "value": f"[View Official Errata & Combos]({url})",
        "inline": False
    })

    embed = {
        "title": f"🏰 {name} • {cost_str}",
        "url": url,
        "color": color,
        "description": f"**{types_str}** • {expansion}" if types_str else f"**{expansion}**",
        "fields": fields
    }

    # High-resolution image URL
    raw_img = card.get("image_url")
    canonical_img = f"https://dominion.avascry.com/images/{slug}.jpg"
    final_img = raw_img if (raw_img and raw_img.startswith("http")) else canonical_img

    embed["image"] = {"url": final_img}

    embed["footer"] = {"text": "AvaScry Dominion Codex • dominion.avascry.com"}
    return {"embeds": [embed]}


def handle_minecraft_command(subcommand: str, options: Dict[str, Any]) -> Dict[str, Any]:
    db = get_mongo_db()
    query = options.get("name", "").strip()
    if not query:
        return {"content": "⚠️ Please provide an item, block, or mob name. Example: `/mc item redstone`"}

    regex = re.compile(re.escape(query), re.IGNORECASE)
    mc_db = db.client["avascry_minecraft"] if hasattr(db, "client") else db

    # Search items, blocks, and entities in order
    record = (
        mc_db.items.find_one({"facts.display_name": regex})
        or mc_db.blocks.find_one({"facts.display_name": regex})
        or mc_db.entities.find_one({"facts.display_name": regex})
        or mc_db.items.find_one({"slug": regex})
        or mc_db.blocks.find_one({"slug": regex})
        or mc_db.entities.find_one({"slug": regex})
        or mc_db.items.find_one({"entity_id": regex})
        or mc_db.blocks.find_one({"entity_id": regex})
        or mc_db.entities.find_one({"entity_id": regex})
    )

    if not record:
        return {"content": f"🔍 No Minecraft record found matching `{query}`."}

    facts = record.get("facts") or {}
    derived = record.get("derived") or {}
    slug = record.get("slug")
    entity_id = record.get("entity_id", slug)
    name = facts.get("display_name") or slug.replace("-", " ").title()

    # Determine type and URL path
    is_block = "hardness" in facts or "material" in facts or mc_db.blocks.find_one({"slug": slug}) is not None
    is_entity = "max_health" in facts or mc_db.entities.find_one({"slug": slug}) is not None

    if is_entity:
        rec_type = "Mob / Entity"
        url = with_discord_bot_utm(f"https://minecraft.avascry.com/entity/{slug}")
        color = 0xef4444 if "hostile" in str(facts.get("category", "")).lower() else 0x10b981
    elif is_block:
        rec_type = "Block"
        url = with_discord_bot_utm(f"https://minecraft.avascry.com/block/{slug}")
        color = 0x0ea5e9
    else:
        rec_type = "Item & Tool"
        url = with_discord_bot_utm(f"https://minecraft.avascry.com/item/{slug}")
        color = 0x10b981

    # Format header description
    desc_lines = [f"### {name}"]
    desc_lines.append(f"**Namespaced ID:** `{entity_id}`")

    fields = []

    # Stack size / Durability / Hardness / Health
    if facts.get("durability"):
        fields.append({"name": "Durability", "value": f"**{facts['durability']}** uses", "inline": True})
    elif facts.get("stack_size"):
        fields.append({"name": "Stack Size", "value": f"Up to **{facts['stack_size']}**", "inline": True})

    if facts.get("hardness") is not None:
        blast = facts.get("resistance", "N/A")
        fields.append({"name": "Hardness / Blast", "value": f"**{facts['hardness']}** / **{blast}**", "inline": True})

    if facts.get("max_health"):
        cat = facts.get("category", "Entity").title()
        fields.append({"name": "Health / Type", "value": f"**{facts['max_health']} HP** • {cat}", "inline": True})

    # Crafting & Usage Quick Summary
    used_in = derived.get("used_in_recipes", [])
    crafted_from = derived.get("crafted_from_recipes", [])
    if crafted_from:
        fields.append({"name": "Craftable", "value": f"**{len(crafted_from)}** crafting recipe(s)", "inline": True})
    if used_in:
        fields.append({"name": "Ingredient In", "value": f"**{len(used_in)}** recipe(s)", "inline": True})

    fields.append({
        "name": "Atlas & Crafting Tree",
        "value": f"🔗 **[Open Interactive Spec & Palette Generator]({url})**",
        "inline": False
    })

    embed = {
        "title": f"⛏️ {name} ({rec_type})",
        "url": url,
        "color": color,
        "description": "\n".join(desc_lines),
        "fields": fields,
        "footer": {
            "text": "AvaScry Minecraft Atlas • Java 1.21.4 • minecraft.avascry.com"
        }
    }

    # Resolve High-Resolution Asset Image
    raw_img = facts.get("image_url")
    if raw_img:
        # Convert internal /static/minecraft/textures path to public raw asset CDN so Discordbot proxy bypasses Cloudflare challenge
        clean_img = raw_img.strip()
        if "/textures/items/" in clean_img:
            item_name = clean_img.split("/textures/items/")[-1]
            full_img_url = f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/1.21/assets/minecraft/textures/item/{item_name}"
        elif "/textures/blocks/" in clean_img:
            block_name = clean_img.split("/textures/blocks/")[-1]
            full_img_url = f"https://raw.githubusercontent.com/InventivetalentDev/minecraft-assets/1.21/assets/minecraft/textures/block/{block_name}"
        elif clean_img.startswith("/"):
            full_img_url = f"https://minecraft.avascry.com{clean_img}"
        else:
            full_img_url = clean_img

        # For items and blocks, a thumbnail renders crisp; for entities, a large image renders best
        if is_entity:
            embed["image"] = {"url": full_img_url}
        else:
            embed["thumbnail"] = {"url": full_img_url}

    return {"embeds": [embed]}

@discord_bot_router.post("/interactions")
async def discord_interactions(request: Request, background_tasks: BackgroundTasks):
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

        log_discord(f"Received command: {root_command}, subcommand: {subcommand}, params: {param_dict}")
        response_data = {}
        try:
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
                        "• `/mtg <name>` — Magic: The Gathering\n"
                        "• `/dom <name>` — Dominion Kingdom Cards\n"
                        "• `/swu <name>` — Star Wars: Unlimited\n"
                        "• `/necro <name>` — Necromunda Armory\n"
                        "• `/mc <name>` — Minecraft Codex"
                    )
                }
        except Exception as e:
            import traceback
            traceback.print_exc()
            log_discord(f"Error processing command {root_command}: {e}")
            response_data = {"content": f"⚠️ Error processing command: {str(e)}"}

        interaction_token = data.get("token", "")
        app_id = data.get("application_id", "") or DISCORD_APPLICATION_ID

        # If response has an embed with an image, defer (Type 5) and patch original message with image attachment via Discord Webhook API
        if "embeds" in response_data and response_data["embeds"] and interaction_token:
            first_embed = response_data["embeds"][0]
            img_obj = first_embed.get("image") or first_embed.get("thumbnail")
            if img_obj and isinstance(img_obj, dict) and img_obj.get("url"):
                orig_url = img_obj["url"]
                log_discord(f"Scheduling deferred background attachment update for {orig_url}")
                background_tasks.add_task(
                    update_discord_original_interaction_with_attachment,
                    app_id=app_id,
                    interaction_token=interaction_token,
                    response_data=response_data,
                    img_url=orig_url
                )
                # Type 5: DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE (tells Discord bot is thinking, then background task edits message)
                return JSONResponse({"type": 5})

        # Log what we're sending back to Discord
        if "embeds" in response_data and response_data["embeds"]:
            img_info = response_data["embeds"][0].get("image")
            log_discord(f"Sending embed image to Discord (immediate Type 4): {img_info}")

        # Type 4: CHANNEL_MESSAGE_WITH_SOURCE
        return JSONResponse({
            "type": 4,
            "data": response_data
        })

    return JSONResponse({"type": 4, "data": {"content": "Unsupported interaction type."}})

