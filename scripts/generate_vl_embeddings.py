import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db, ensure_indexes

def build_embedding_texts(doc):
    obs = doc.get("vision_observations", {})
    
    # 1. Subject text: Entities, characters, and visible objects
    subjects = obs.get("subjects", [])
    if isinstance(subjects, list):
        subj_str = ", ".join(str(s) for s in subjects if s)
    else:
        subj_str = str(subjects or "")
        
    objects = obs.get("visible_objects", [])
    if isinstance(objects, list):
        obj_str = ", ".join(str(o) for o in objects if o)
    else:
        obj_str = str(objects or "")
        
    subject_text = f"Subjects: {subj_str}. Objects: {obj_str}."
    
    # 2. Vibe text: Style, mood, and lighting aesthetics
    styles = obs.get("style_descriptors", [])
    if isinstance(styles, list):
        style_str = ", ".join(str(s) for s in styles if s)
    else:
        style_str = str(styles or "")
        
    moods = obs.get("mood_keywords", [])
    if isinstance(moods, list):
        mood_str = ", ".join(str(m) for m in moods if m)
    else:
        mood_str = str(moods or "")
        
    lighting = obs.get("lighting", "")
    vibe_text = f"Style: {style_str}. Mood: {mood_str}. Lighting: {lighting}."
    
    # 3. Scene text: Macro visual summary, setting, and environment
    settings = obs.get("setting", [])
    if isinstance(settings, list):
        setting_str = ", ".join(str(s) for s in settings if s)
    else:
        setting_str = str(settings or "")
        
    summary = obs.get("visual_summary", "")
    composition = obs.get("composition", "")
    colors = obs.get("dominant_colors", [])
    color_str = ", ".join(str(c) for c in colors if c) if isinstance(colors, list) else str(colors or "")
    
    scene_text = f"{summary} Setting: {setting_str}. Composition: {composition}. Palette: {color_str}."
    
    return {
        "subject": subject_text.strip(),
        "vibe": vibe_text.strip(),
        "scene": scene_text.strip()
    }

def call_ollama_embed_batch(ollama_url, model, texts):
    url = f"{ollama_url.rstrip('/')}/api/embed"
    payload = {
        "model": model,
        "input": texts,
        "keep_alive": "1h"
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        res = json.loads(response.read().decode("utf-8"))
        embeddings = res.get("embeddings", [])
        if not embeddings and "embedding" in res:
            embeddings = [res["embedding"]]
        return embeddings

def main():
    parser = argparse.ArgumentParser(description="Generate 4096-d visual embeddings across subject, vibe, and scene.")
    parser.add_argument("--model", default="qwen3-embedding:8b", help="Ollama embedding model")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="Ollama API base URL")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size of texts per embedding call")
    parser.add_argument("--smoke-test", type=int, default=None, help="Process N documents and exit")
    parser.add_argument("--force", action="store_true", help="Re-embed already embedded documents")
    args = parser.parse_args()

    db = get_mongo_db()
    ensure_indexes(db)

    print("=" * 60)
    print("MTGAbyss 4096-d Visual Embedding Generator")
    print("=" * 60)
    print(f"Model       : {args.model}")
    print(f"Ollama URL  : {args.ollama_url}")
    print(f"Dimensions  : 4096 (Subject, Vibe, Scene)")
    print(f"Batch Size  : {args.batch_size}")
    print("=" * 60)

    # 1. Fetch completed VL documents
    query = {"status": "complete"}
    total_vl = db.vl_art_analysis.count_documents(query)
    print(f"[*] Total completed VL illustrations: {total_vl:,}")

    # 2. Check already embedded
    if not args.force:
        existing_ids = set(db.vl_art_embeddings.distinct("illustration_id", {"model": args.model}))
        print(f"[*] Already embedded: {len(existing_ids):,}")
    else:
        existing_ids = set()

    cursor = db.vl_art_analysis.find(query).sort("generated_at", -1)
    to_process = []
    for doc in cursor:
        iid = doc.get("illustration_id")
        if iid and (args.force or iid not in existing_ids):
            to_process.append(doc)
            if args.smoke_test and len(to_process) >= args.smoke_test:
                break

    print(f"[*] Illustrations to embed: {len(to_process):,}")
    if not to_process:
        print("[+] All completed illustrations already have embeddings!")
        return

    start_all = time.time()
    processed_count = 0
    total_to_do = len(to_process)

    # Process in chunks of illustrations
    # Each illustration has 3 texts (subject, vibe, scene)
    chunk_size = max(1, args.batch_size // 3)
    for i in range(0, total_to_do, chunk_size):
        chunk = to_process[i:i + chunk_size]
        
        flat_texts = []
        mapping = [] # (illustration_id, doc_meta, source_texts)
        
        for doc in chunk:
            iid = doc["illustration_id"]
            texts = build_embedding_texts(doc)
            flat_texts.extend([texts["subject"], texts["vibe"], texts["scene"]])
            mapping.append((iid, doc.get("source", {}), texts))
            
        t0 = time.time()
        embeddings = call_ollama_embed_batch(args.ollama_url, args.model, flat_texts)
        batch_duration = time.time() - t0

        if len(embeddings) != len(flat_texts):
            print(f"[!] Error: Expected {len(flat_texts)} embeddings, got {len(embeddings)}!")
            continue

        # Save each illustration with its 3 vectors
        now = datetime.now(timezone.utc)
        for idx, (iid, source_meta, texts) in enumerate(mapping):
            subj_vec = embeddings[idx * 3]
            vibe_vec = embeddings[idx * 3 + 1]
            scene_vec = embeddings[idx * 3 + 2]

            db.vl_art_embeddings.update_one(
                {"illustration_id": iid, "model": args.model},
                {
                    "$set": {
                        "illustration_id": iid,
                        "model": args.model,
                        "dimensions": len(subj_vec),
                        "source": source_meta,
                        "texts": texts,
                        "vectors": {
                            "subject": subj_vec,
                            "vibe": vibe_vec,
                            "scene": scene_vec
                        },
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
            processed_count += 1
            card_name = source_meta.get("card_name", "Unknown")
            print(f"[EMBED] ({total_to_do - processed_count} left) {card_name} | {batch_duration:.2f}s | 3x {len(subj_vec)}d")

    total_time = time.time() - start_all
    print(f"\n[+] Successfully generated embeddings for {processed_count:,} illustrations in {total_time:.1f}s.")

if __name__ == "__main__":
    main()
