import os
import sys
import json
import base64
import argparse
import urllib.request
import urllib.parse
from datetime import datetime

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db

def extract_image_and_meta(card_doc):
    raw = card_doc.get("raw", {})
    
    # Extract illustration_id and identifiers
    illustration_id = raw.get("illustration_id") or card_doc.get("illustration_id")
    oracle_id = raw.get("oracle_id") or card_doc.get("oracle_id")
    card_name = card_doc.get("name") or raw.get("name", "Unknown")
    artist = card_doc.get("artist") or raw.get("artist", "Unknown")
    set_code = card_doc.get("set") or raw.get("set", "").upper()
    collector_number = card_doc.get("collector_number") or raw.get("collector_number", "")
    
    # Image resolution: prefer art_crop
    image_url = None
    image_uris = raw.get("image_uris") or card_doc.get("image_uris")
    if image_uris and isinstance(image_uris, dict):
        image_url = image_uris.get("art_crop") or image_uris.get("normal") or image_uris.get("large")
    
    if not image_url:
        card_faces = raw.get("card_faces") or card_doc.get("card_faces")
        if card_faces and isinstance(card_faces, list) and len(card_faces) > 0:
            face_uris = card_faces[0].get("image_uris")
            if face_uris and isinstance(face_uris, dict):
                image_url = face_uris.get("art_crop") or face_uris.get("normal") or face_uris.get("large")
                
    meta = {
        "illustration_id": illustration_id,
        "oracle_id": oracle_id,
        "card_name": card_name,
        "artist": artist,
        "set": set_code,
        "collector_number": collector_number,
        "image_url": image_url
    }
    return image_url, meta

def fetch_image_b64(image_source):
    if os.path.exists(image_source):
        with open(image_source, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    req = urllib.request.Request(
        image_source,
        headers={"User-Agent": "MTGAbyss-VL-Tester/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return base64.b64encode(resp.read()).decode("utf-8")

def call_ollama_vl(ollama_url, model, image_b64, prompt):
    url = f"{ollama_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=300) as response:
        res = json.loads(response.read().decode("utf-8"))
        if "response" in res and res["response"]:
            return res["response"].strip()
        return json.dumps(res, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Blinded Vision-Language analysis on a single MTG card illustration.")
    parser.add_argument("--card", default="The Ur-Dragon", help="Card name to search in DB")
    parser.add_argument("--set", dest="card_set", default=None, help="Set code (optional)")
    parser.add_argument("--image-url", default=None, help="Direct image URL override")
    parser.add_argument("--model", default="qwen3-vl:latest", help="Ollama vision model to use")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama API base URL")
    args = parser.parse_args()

    image_url = args.image_url
    meta = {}

    if not image_url:
        db = get_mongo_db()
        query = {"name": {"$regex": f"^{args.card}$", "$options": "i"}}
        if args.card_set:
            query["set"] = args.card_set.lower()
            
        card_doc = db.cards.find_one(query)
        if not card_doc:
            card_doc = db.cards.find_one({"name": {"$regex": args.card, "$options": "i"}})
            
        if not card_doc:
            print(f"[!] Error: Could not find card '{args.card}' in MongoDB.")
            sys.exit(1)
            
        image_url, meta = extract_image_and_meta(card_doc)
        if not image_url:
            print(f"[!] Error: No image URI found for card '{args.card}'.")
            sys.exit(1)
    else:
        meta = {"image_url": image_url}

    print(f"[*] Fetching art-crop: {image_url}")
    image_b64 = fetch_image_b64(image_url)
    print(f"[*] Image ready ({len(image_b64)} b64 chars).")
    print(f"[*] Querying {args.model} (100% blinded prompt, keep_alive=1h)...")

    # Strictly blinded prompt: NO card name, NO artist, NO lore, NO set.
    blinded_prompt = """You are an objective visual analyst. Inspect only the visual pixels of this image.
Describe literally what is depicted without guessing card names, named characters, or game lore.
Return valid JSON matching this schema:
{
  "visual_summary": "1-2 literal, objective sentences describing what is visible in the frame",
  "subjects": ["major distinct depicted focal entities or groups only; for crowded scenes group them (e.g. 'crowd of armored figures'); if a pure landscape/environment with no focal subject, use empty list []"],
  "setting": ["environment type", "background features"],
  "dominant_colors": ["color1", "color2", "color3"],
  "lighting": "visible illumination, highlights, shadows, contrast, and apparent direction of light; do not claim an object is the light source unless visually unambiguous",
  "composition": "focal point, perspective angle, framing (e.g. close-up, wide shot), foreground/midground/background depth",
  "style_descriptors": ["visible aesthetic/stylistic qualities only (e.g. textured, painterly, geometric, surreal, high-contrast, soft-edged, line-heavy, minimalist, flat-color); do NOT guess physical medium, digital tools, scanner artifacts, compression, or printing process (avoid 'oil painting', 'digital art', 'acrylic', 'scanned', 'pixels')"],
  "visible_objects": ["discernible items, props, garments, weapons, architectural elements, natural elements"],
  "mood_keywords": ["atmospheric or emotional tone only (e.g. serene, foreboding, chaotic, whimsical, somber); do NOT use visual-quality or style terms like 'detailed' or 'digital'"],
  "uncertain_elements": ["ambiguous, obscured, or cropped shapes/features that cannot be definitively identified; leave as empty list [] if none"]
}"""

    start_t = datetime.now()
    raw_response = call_ollama_vl(args.ollama_url, args.model, image_b64, blinded_prompt)
    duration = (datetime.now() - start_t).total_seconds()

    print(f"\n[+] Blinded VL analysis completed in {duration:.2f}s:")
    print("=" * 60)

    parsed_vl = None
    try:
        # Strip code fences if present
        clean_text = raw_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        parsed_vl = json.loads(clean_text.strip())
    except Exception as e:
        print(f"[!] Could not parse JSON directly: {e}")

    # Combine deterministic DB metadata (supplied by MTGAbyss) with pure VL observation
    combined_result = {
        "metadata_from_db": meta,
        "vision_observations": parsed_vl if parsed_vl else raw_response
    }

    print(json.dumps(combined_result, indent=2))
    print("=" * 60)

if __name__ == "__main__":
    main()
