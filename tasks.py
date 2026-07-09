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
def generate_lure(oracle_id, model="mistral-small3.2:24b", force=False):
    """
    Generate the flavor lore lure using Mistral on Ollama and store it in MongoDB.
    Runs on the ai-lures queue.
    """
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
    db = get_mongo_db()
    result = generate_page(search_term, db)
    if not result:
        raise ValueError(f"Failed to generate page for '{search_term}'")
    
    slug, referenced_images = result
    if not deploy:
        return f"Generated page locally for card: {slug}"

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
    
    if ssh_proc.returncode == 0:
        return f"Successfully generated and deployed card page for '{slug}'"
    else:
        raise RuntimeError(f"Deployment failed with exit code: {ssh_proc.returncode}")
