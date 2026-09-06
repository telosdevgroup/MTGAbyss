import os
import sys
import datetime
import io
import tarfile
import subprocess
import urllib.request
import json
import pymongo

from celery_app import app
from db_mongo import get_mongo_db
from scripts.generate_card_embeddings import process_card_embedding
from scripts.lure_shared import build_lure_prompt, clean_lure_text
from generate_card_page import generate_page

@app.task
def generate_embedding(oracle_id, model="qwen3-embedding:8b", version="card_context_v1", force=False):
    """
    Generate card embedding using Ollama and store it in MongoDB.
    Runs on the gpu-tasks queue.
    """
    db = get_mongo_db()
    card = db["cards"].find_one({"oracle_id": oracle_id})
    if not card:
        raise ValueError(f"Card with oracle_id {oracle_id} not found.")

    now = datetime.datetime.now(datetime.timezone.utc)
    success = process_card_embedding(
        db=db,
        card=card,
        model=model,
        version=version,
        mock_mode=False,
        worker_id="celery-worker",
        now=now,
        force=force
    )
    if success:
        return f"Successfully generated embedding for '{card.get('name')}'"
    else:
        raise RuntimeError(f"Failed to generate embedding for '{card.get('name')}'")

@app.task
def generate_lure(oracle_id, model=None, force=False):
    """
    Generate the flavor lore lure using Mistral on Ollama and store it in MongoDB.
    Runs on the ai-lures queue.
    """
    if model is None:
        model = os.environ.get("OLLAMA_MODEL", "mistral-small3.2:24b")
    db = get_mongo_db()
    card = db["cards"].find_one({"oracle_id": oracle_id})
    if not card:
        raise ValueError(f"Card with oracle_id {oracle_id} not found.")

    # Check if lure already exists and force is False
    if not force:
        abyss_doc = db["abysses"].find_one({"oracle_id": oracle_id})
        if abyss_doc:
            lure_data = abyss_doc.get("content", {}).get("lure", {})
            if lure_data.get("status") == "generated" and lure_data.get("text"):
                return f"Lure for '{card.get('name')}' already exists, skipping."

    prompt, _ = build_lure_prompt(card)
    
    # Call Ollama generate API
    ollama_host = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    url = f"{ollama_host}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "1h",
        "options": {
            "temperature": 0.7
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    import time
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw_lure = res_data.get("response", "").strip()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"\n[Ollama HTTP Error {e.code}]: {e.reason}\nBody: {error_body}\n")
        raise e
    except Exception as e:
        print(f"\n[Ollama Connection Error]: {e}\n")
        raise e

    gen_time = time.time() - start_time
    lure_text = clean_lure_text(raw_lure)
    
    # Calculate exact remaining lures count from database
    total_cards = db["cards"].count_documents({})
    completed_lures = db["abysses"].count_documents({"content.lure.status": "generated"})
    remaining = max(0, total_cards - completed_lures)

    print(f"\n({remaining} remaining) {card.get('name')}")
    print(lure_text)
    print(f"Generation time: {gen_time:.2f}s\n")

    # Save description text into abysses collection
    db["abysses"].update_one(
        {"oracle_id": oracle_id},
        {
            "$set": {
                "oracle_id": oracle_id,
                "content.lure.status": "generated",
                "content.lure.text": lure_text,
                "content.lure.model": model,
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        },
        upsert=True
    )
    return f"Generated lure for '{card.get('name')}' using {model}"

@app.task
def generate_and_deploy_page(search_term, deploy=True):
    """
    Renders static HTML for the card detail page and deploys it to the remote VPS.
    Runs on the builder-tasks queue (Raspberry Pi/Beast).
    """
    import time
    start_time = time.time()
    db = get_mongo_db()
    
    # Suppress verbose generate_page prints inside the Celery logs
    import sys
    sys_stdout = sys.stdout
    devnull = open(os.devnull, 'w', encoding='utf-8')
    sys.stdout = devnull
    try:
        result = generate_page(search_term, db)
    finally:
        devnull.close()
        sys.stdout = sys_stdout

    if not result:
        raise ValueError(f"Failed to generate page for '{search_term}'")
    
    slug, referenced_images = result
    
    if not deploy:
        remaining = 0
        try:
            broker_db = db.client["celery_broker"]
            remaining = broker_db["messages"].count_documents({"payload": {"$regex": "generate_and_deploy_page"}})
        except Exception:
            pass
        completed = max(0, 37740 - remaining)
        gen_time = time.time() - start_time
        log_entry = f"\n\n{completed}/37740: {search_term}\n(local build, not deployed)\n{gen_time:.2f}s\n\n"
        print(log_entry)
        sys.stdout.flush()
        return log_entry

    # Compress the static files and referenced images
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w:gz") as tar:
        card_dir = f"public/card/{slug}"
        if os.path.exists(card_dir):
            for root, dirs, files in os.walk(card_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, "public")
                    tar.add(file_path, arcname=arcname)
        
        for local_path, target_arcname in referenced_images.items():
            if os.path.exists(local_path):
                tar.add(local_path, arcname=target_arcname)

    tar_bytes = tar_stream.getvalue()
    
    # Upload archive via SSH stream
    remote_cmd = (
        "tar -xzf - -C /srv/www/mtgabyss.com && "
        "find /srv/www/mtgabyss.com/card /srv/www/mtgabyss.com/images -type d -exec chmod 755 {} + && "
        "find /srv/www/mtgabyss.com/card /srv/www/mtgabyss.com/images -type f -exec chmod 644 {} +"
    )
    
    ssh_proc = subprocess.Popen(
        ["ssh", "ubuntu@15.204.113.15", remote_cmd],
        stdin=subprocess.PIPE
    )
    ssh_proc.communicate(input=tar_bytes)
    
    if ssh_proc.returncode != 0:
        raise RuntimeError(f"Deployment failed with exit code: {ssh_proc.returncode}")

    # Fetch remaining count in Celery broker database to compute progress
    remaining = 0
    try:
        broker_db = db.client["celery_broker"]
        remaining = broker_db["messages"].count_documents({"payload": {"$regex": "generate_and_deploy_page"}})
    except Exception:
        pass

    completed = max(0, 37740 - remaining)
    gen_time = time.time() - start_time
    log_entry = f"\n\n{completed}/37740: {search_term}\nhttps://mtgabyss.com/card/{slug}/\n{gen_time:.2f}s\n\n"
    print(log_entry)
    sys.stdout.flush()
    return log_entry


REQUIRED_VL_FIELDS = [
    "visual_summary",
    "subjects",
    "setting",
    "dominant_colors",
    "lighting",
    "composition",
    "style_descriptors",
    "visible_objects",
    "mood_keywords",
    "uncertain_elements",
]

BLINDED_VL_PROMPT = """You are an objective visual analyst. Inspect only the visual pixels of this image.
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


def _clean_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _extract_card_art_info(card_doc: dict):
    raw = card_doc.get("raw", {})
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
        "illustration_id": raw.get("illustration_id") or card_doc.get("illustration_id"),
        "oracle_id": raw.get("oracle_id") or card_doc.get("oracle_id"),
        "card_name": card_doc.get("name") or raw.get("name", "Unknown"),
        "artist": card_doc.get("artist") or raw.get("artist", "Unknown"),
        "set": card_doc.get("set") or raw.get("set", "").upper(),
        "collector_number": card_doc.get("collector_number") or raw.get("collector_number", ""),
        "image_url": image_url,
    }
    return image_url, meta


@app.task(bind=True, queue="vl", max_retries=3, default_retry_delay=15)
def process_art_vl(self, illustration_id: str, force: bool = False, model: str = None, prompt_version: int = 1):
    """
    Blinded Vision-Language processing on MTG card artwork using local Qwen3-VL.
    Runs on the dedicated 'vl' queue across all worker nodes.
    Results are saved into MongoDB collection 'vl_art_analysis'.
    """
    import base64
    import time
    from urllib.error import URLError, HTTPError

    vl_model = model or os.environ.get("OLLAMA_VL_MODEL", "qwen3-vl:latest")
    db = get_mongo_db()
    vl_collection = db["vl_art_analysis"]

    # 1. Skip if completed result already exists for illustration_id + model + prompt_version
    if not force:
        existing = vl_collection.find_one({
            "illustration_id": illustration_id,
            "model": vl_model,
            "prompt_version": prompt_version,
            "status": "complete"
        })
        if existing:
            return f"Illustration {illustration_id} already analyzed (status=complete). Skipping."

    # 2. Query representative English printing with art crop
    card_doc = db["cards"].find_one({
        "$or": [
            {"illustration_id": illustration_id, "lang": "en"},
            {"raw.illustration_id": illustration_id, "lang": "en"},
            {"illustration_id": illustration_id},
            {"raw.illustration_id": illustration_id},
        ]
    })
    if not card_doc:
        raise ValueError(f"No card found in DB matching illustration_id: {illustration_id}")

    image_url, meta = _extract_card_art_info(card_doc)
    if not image_url:
        raise ValueError(f"No image URL found for illustration_id: {illustration_id}")

    card_name = meta.get("card_name", "Unknown")
    print(f"[VL START] {card_name} | {illustration_id[:8]}...")
    sys.stdout.flush()

    # 3. Load or download art crop into base64
    try:
        if os.path.exists(image_url):
            with open(image_url, "rb") as f:
                image_bytes = f.read()
        else:
            req = urllib.request.Request(
                image_url,
                headers={"User-Agent": "AvaScry-VL-Worker/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                image_bytes = resp.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    except (URLError, TimeoutError, ConnectionError) as e:
        print(f"[VL FAIL ] illustration_id={illustration_id} | download error: {e} | retry {self.request.retries + 1}/3")
        raise self.retry(exc=e)

    # 4. Call local Qwen3-VL via Ollama
    ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    api_url = f"{ollama_url}/api/generate"

    ollama_timeout = int(os.environ.get("OLLAMA_TIMEOUT", "600"))

    payload = {
        "model": vl_model,
        "prompt": BLINDED_VL_PROMPT,
        "images": [image_b64],
        "stream": False,
        "format": "json",
        "keep_alive": "1h",
        "options": {
            "temperature": 0.1,
            "num_ctx": 2048,
            "num_predict": 512
        }
    }

    start_time = time.time()
    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=ollama_timeout) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw_text = res_data.get("response", "").strip()
    except (URLError, HTTPError, TimeoutError, ConnectionError) as e:
        print(f"[VL FAIL ] illustration_id={illustration_id} | Ollama error: {e} | retry {self.request.retries + 1}/3")
        raise self.retry(exc=e)

    gen_duration = time.time() - start_time

    # 5. Parse and validate required JSON fields
    cleaned_json = _clean_json_fence(raw_text)
    try:
        observations = json.loads(cleaned_json)
    except Exception as e:
        print(f"[VL FAIL ] illustration_id={illustration_id} | invalid JSON: {e} | retry {self.request.retries + 1}/3")
        raise self.retry(exc=e)

    missing_fields = [f for f in REQUIRED_VL_FIELDS if f not in observations]
    if missing_fields:
        print(f"[VL FAIL ] illustration_id={illustration_id} | missing fields {missing_fields} | retry {self.request.retries + 1}/3")
        raise self.retry(exc=ValueError(f"Missing fields: {missing_fields}"))

    now = datetime.datetime.now(datetime.timezone.utc)

    # 6. Upsert into vl_art_analysis collection
    vl_collection.update_one(
        {
            "illustration_id": illustration_id,
            "model": vl_model,
            "prompt_version": prompt_version
        },
        {
            "$set": {
                "illustration_id": illustration_id,
                "model": vl_model,
                "prompt_version": prompt_version,
                "status": "complete",
                "source": meta,
                "vision_observations": observations,
                "duration_seconds": round(gen_duration, 2),
                "generated_at": now,
            }
        },
        upsert=True
    )

    subj_count = len(observations.get("subjects", []))
    obj_count = len(observations.get("visible_objects", []))
    msg = f"[VL DONE ] {card_name} | {gen_duration:.1f}s | subjects={subj_count} objects={obj_count}"
    print(msg)
    sys.stdout.flush()
    return msg

