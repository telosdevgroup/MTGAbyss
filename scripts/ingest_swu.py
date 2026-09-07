"""
Standalone ingestion script for Star Wars: Unlimited (SWU) into MongoDB 'avascry_swu'.
Fetches data from canonical swu-db.com API:
- /sets (set metadata)
- /cards/{setId} (cards with aspects, traits, arenas, stats, rules text, front/back images)
"""

import os
import re
import json
import time
import urllib.request
import argparse
from typing import Dict, Any, List, Optional
from pymongo import MongoClient, ASCENDING, DESCENDING

API_BASE = "https://api.swu-db.com"

# Primary canonical sets to ingest by default
CORE_SETS = ["SOR", "SHD", "TWI", "JTL", "LOF", "SEC", "LAW", "ASH", "HMW"]

def slugify(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def fetch_json(url: str) -> Any:
    headers = {"User-Agent": "AvaScry-SWU-Ingester/1.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))

def parse_val(val: Any) -> Optional[int]:
    if val is None or val == "" or val == "-":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None

def extract_aspects(aspect_list: Any) -> List[str]:
    aspects = []
    if not aspect_list:
        return aspects
    for item in aspect_list:
        if isinstance(item, dict) and "S" in item:
            aspects.append(item["S"])
        elif isinstance(item, str):
            aspects.append(item)
    return aspects

def extract_traits(trait_list: Any) -> List[str]:
    traits = []
    if not trait_list:
        return traits
    for item in trait_list:
        if isinstance(item, dict) and "S" in item:
            traits.append(item["S"].title())
        elif isinstance(item, str):
            traits.append(item.title())
    return traits

def normalize_card(raw: Dict[str, Any], set_map: Dict[str, str]) -> Dict[str, Any]:
    set_code = (raw.get("Set") or "").upper()
    number = str(raw.get("Number") or "").zfill(3)
    name = (raw.get("Name") or "").strip()
    subtitle = (raw.get("Subtitle") or "").strip()
    card_type = (raw.get("Type") or "").strip()
    
    # Generate canonical slug e.g. "boba-fett-collecting-the-bounty-sor-15"
    base_slug = slugify(f"{name} {subtitle}" if subtitle else name)
    num_clean = number.lstrip('0') or '0'
    unique_slug = f"{base_slug}-{set_code.lower()}-{num_clean}"
    
    aspects = extract_aspects(raw.get("Aspects"))
    traits = extract_traits(raw.get("Traits"))
    arenas = raw.get("Arenas") or []
    if isinstance(arenas, str):
        arenas = [arenas]

    front_text = raw.get("FrontText") or ""
    back_text = raw.get("BackText") or ""
    epic_action = raw.get("EpicAction") or ""
    
    front_art = raw.get("FrontArt") or ""
    back_art = raw.get("BackArt") or ""
    
    cost = parse_val(raw.get("Cost"))
    power = parse_val(raw.get("Power"))
    hp = parse_val(raw.get("HP"))
    
    rarity = raw.get("Rarity") or "Common"
    unique = bool(raw.get("Unique"))
    double_sided = bool(raw.get("DoubleSided") or back_art or back_text)
    artist = raw.get("Artist") or ""

    set_name = set_map.get(set_code, set_code)

    num_clean_int = int(re.sub(r'\D', '', number) or '0')

    return {
        "cid": str(raw.get("cid") or f"{set_code}_{number}"),
        "slug": unique_slug,
        "base_slug": base_slug,
        "title": name,
        "name": name,
        "subtitle": subtitle,
        "full_name": f"{name}: {subtitle}" if subtitle else name,
        "type": card_type,
        "set_code": set_code,
        "set_name": set_name,
        "expansion": {"code": set_code, "name": set_name},
        "number": number,
        "card_number": num_clean_int,
        "aspects": aspects,
        "traits": traits,
        "arenas": arenas,
        "cost": cost,
        "power": power,
        "hp": hp,
        "text": front_text,
        "front_text": front_text,
        "back_text": back_text,
        "epic_action": epic_action,
        "double_sided": double_sided,
        "art_front": front_art,
        "art_back": back_art,
        "front_image": front_art,
        "back_image": back_art,
        "rarity": rarity,
        "unique": unique,
        "artist": artist,
        "variant_type": raw.get("VariantType") or "Normal",
        "market_price": raw.get("MarketPrice") or "",
        "low_price": raw.get("LowPrice") or "",
        "tcgplayer_id": raw.get("tcgplayerId") or ""
    }

def run_ingest(mongo_uri: str, sets_to_ingest: Optional[List[str]] = None):
    print(f"Connecting to MongoDB at {mongo_uri}...")
    client = MongoClient(mongo_uri)
    db = client["avascry_swu"]

    print("Fetching sets list from API...")
    sets_data = fetch_json(f"{API_BASE}/sets")
    set_map = {}
    if isinstance(sets_data, list):
        for s in sets_data:
            sid = (s.get("setId") or "").upper()
            sname = s.get("fullName") or sid
            if sid:
                set_map[sid] = sname
                db.sets.update_one(
                    {"setId": sid},
                    {"$set": {
                        "setId": sid,
                        "fullName": sname,
                        "numberCards": s.get("numberCards"),
                        "releaseDate": s.get("releaseDate")
                    }},
                    upsert=True
                )
    print(f"Recorded {len(set_map)} sets.")

    target_sets = sets_to_ingest or [s for s in CORE_SETS if s in set_map]
    print(f"Targeting sets for ingestion: {target_sets}")

    all_cards = []

    for set_code in target_sets:
        url = f"{API_BASE}/cards/{set_code.lower()}"
        print(f"Fetching cards for set {set_code} from {url}...")
        try:
            res = fetch_json(url)
            cards_list = res.get("data", []) if isinstance(res, dict) else res
            print(f"  Found {len(cards_list)} card entries.")
            for raw_card in cards_list:
                normalized = normalize_card(raw_card, set_map)
                all_cards.append(normalized)
            time.sleep(0.3)
        except Exception as e:
            print(f"  Error fetching set {set_code}: {e}")

    print(f"Total card variants parsed: {len(all_cards)}")

    # Prefer 'Normal' variant for standard listing
    unique_cards = {}
    for c in all_cards:
        key = f"{c['set_code']}_{c['number']}"
        if key not in unique_cards or (c.get("variant_type") == "Normal" and unique_cards[key].get("variant_type") != "Normal"):
            unique_cards[key] = c

    print(f"Unique card printings to upsert: {len(unique_cards)}")

    # Index setup
    db.cards.create_index([("slug", ASCENDING)], unique=True)
    db.cards.create_index([("name", ASCENDING)])
    db.cards.create_index([("type", ASCENDING)])
    db.cards.create_index([("aspects", ASCENDING)])
    db.cards.create_index([("arenas", ASCENDING)])
    db.cards.create_index([("set_code", ASCENDING), ("number", ASCENDING)])
    db.cards.create_index([("cost", ASCENDING)])

    # Upsert cards
    upserted = 0
    for card in unique_cards.values():
        db.cards.update_one(
            {"slug": card["slug"]},
            {"$set": card},
            upsert=True
        )
        upserted += 1

    print(f"Successfully upserted {upserted} cards into avascry_swu.cards!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Star Wars: Unlimited cards into MongoDB")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017"), help="MongoDB URI")
    parser.add_argument("--sets", nargs="*", default=None, help="Specific sets to ingest (e.g. SOR SHD TWI)")
    args = parser.parse_args()

    run_ingest(args.mongo_uri, args.sets)
