import os
import sys
import re
from collections import defaultdict

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db

def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def get_old_base_slug(doc):
    card_name = doc.get('name') or 'unknown'
    set_name = doc.get('set_name') or doc.get('set') or 'unknown'
    artist = doc.get('artist') or 'unknown'
    
    slug_parts = [slugify(card_name), slugify(set_name), slugify(artist)]
    slug_parts = [p for p in slug_parts if p]
    return "-".join(slug_parts)

def get_base_slug(doc):
    card_name = doc.get('name') or 'unknown'
    set_name = doc.get('set_name') or doc.get('set') or 'unknown'
    artist = doc.get('artist') or 'unknown'
    collector_number = doc.get('collector_number') or doc.get('raw', {}).get('collector_number') or ''
    
    slug_parts = [
        slugify(card_name), 
        slugify(set_name), 
        slugify(artist),
        slugify(collector_number)
    ]
    slug_parts = [p for p in slug_parts if p]
    return "-".join(slug_parts)

def main():
    db = get_mongo_db()
    
    print("Reading all card printings from MongoDB...")
    # Read prints and representative cards including collector_number
    prints = list(db["card_prints"].find({}, {"id": 1, "name": 1, "set_name": 1, "set": 1, "artist": 1, "card_faces": 1, "collector_number": 1}))
    cards = list(db["cards"].find({}, {"id": 1, "name": 1, "set_name": 1, "set": 1, "artist": 1, "raw.card_faces": 1, "raw.collector_number": 1, "collector_number": 1}))
    
    print(f"Loaded {len(prints):,} prints and {len(cards):,} representative cards.")
    
    # Map to track card_id -> final unique slug
    id_to_slug = {}
    slug_to_id = {}
    
    # Map to track card_id -> old slug (without collector_number) for recovery
    id_to_old_slug = {}
    slug_to_id_old = {}
    
    # Process all unique printings and cards to build conflict-free slugs
    all_docs = []
    seen_ids = set()
    
    for doc in prints + cards:
        card_id = doc.get("id")
        if not card_id or card_id in seen_ids:
            continue
        seen_ids.add(card_id)
        all_docs.append(doc)
        
    print(f"Processing {len(all_docs):,} unique card IDs...")
    
    for doc in all_docs:
        card_id = doc["id"]
        
        # Calculate new slug (with collector_number)
        base_slug = get_base_slug(doc)
        candidate_slug = base_slug
        suffix = 1
        while candidate_slug in slug_to_id and slug_to_id[candidate_slug] != card_id:
            candidate_slug = f"{base_slug}-{suffix}"
            suffix += 1
        slug_to_id[candidate_slug] = card_id
        id_to_slug[card_id] = candidate_slug
        
        # Calculate old slug (without collector_number)
        base_slug_old = get_old_base_slug(doc)
        candidate_slug_old = base_slug_old
        suffix_old = 1
        while candidate_slug_old in slug_to_id_old and slug_to_id_old[candidate_slug_old] != card_id:
            candidate_slug_old = f"{base_slug_old}-{suffix_old}"
            suffix_old += 1
        slug_to_id_old[candidate_slug_old] = card_id
        id_to_old_slug[card_id] = candidate_slug_old

    print(f"Generated {len(id_to_slug):,} unique image slugs.")
    
    # 1. Update MongoDB documents
    print("Updating MongoDB documents with 'image_slug'...")
    
    # Bulk write to cards
    cards_updated = 0
    for card_doc in cards:
        card_id = card_doc.get("id")
        if card_id in id_to_slug:
            db["cards"].update_one({"id": card_id}, {"$set": {"image_slug": id_to_slug[card_id]}})
            cards_updated += 1
            
    # Bulk write to card_prints
    prints_updated = 0
    for print_doc in prints:
        card_id = print_doc.get("id")
        if card_id in id_to_slug:
            db["card_prints"].update_one({"id": card_id}, {"$set": {"image_slug": id_to_slug[card_id]}})
            prints_updated += 1
            
    print(f"Database updated: {cards_updated} cards and {prints_updated} prints updated.")
    
    # 2. Write rename_remote.sh (shell script for the VPS)
    print("Generating 'rename_remote.sh' for VPS...")
    with open("rename_remote.sh", "w", newline="\n", encoding="utf-8") as f:
        f.write("#!/bin/bash\n")
        f.write("echo 'Starting image rename operations...'\n")
        f.write("mkdir -p images/normal images/large images/art_crop\n")
        
        for doc in all_docs:
            card_id = doc["id"]
            slug = id_to_slug[card_id]
            old_slug = id_to_old_slug.get(card_id)
            
            # Check for multi-faced cards (faces suffix)
            faces = doc.get("card_faces") or doc.get("raw", {}).get("card_faces") or []
            has_faces = bool(faces)
            suffix = "_0" if has_faces else ""
            
            # Normal size
            src_norm_uuid = f"images/normal/{card_id}{suffix}.jpg"
            src_norm_old = f"images/normal/{old_slug}{suffix}.jpg"
            dst_norm = f"images/normal/{slug}{suffix}.jpg"
            f.write(f"[ -f {src_norm_uuid} ] && mv {src_norm_uuid} {dst_norm}\n")
            f.write(f"[ -f {src_norm_old} ] && [ \"{src_norm_old}\" != \"{dst_norm}\" ] && mv {src_norm_old} {dst_norm}\n")
            
            # Large size
            src_large_uuid = f"images/large/{card_id}{suffix}.jpg"
            src_large_old = f"images/large/{old_slug}{suffix}.jpg"
            dst_large = f"images/large/{slug}{suffix}.jpg"
            f.write(f"[ -f {src_large_uuid} ] && mv {src_large_uuid} {dst_large}\n")
            f.write(f"[ -f {src_large_old} ] && [ \"{src_large_old}\" != \"{dst_large}\" ] && mv {src_large_old} {dst_large}\n")
            
            # Art crop
            src_art_uuid = f"images/art_crop/{card_id}{suffix}.jpg"
            src_art_old = f"images/art_crop/{old_slug}{suffix}.jpg"
            dst_art = f"images/art_crop/{slug}{suffix}.jpg"
            f.write(f"[ -f {src_art_uuid} ] && mv {src_art_uuid} {dst_art}\n")
            f.write(f"[ -f {src_art_old} ] && [ \"{src_art_old}\" != \"{dst_art}\" ] && mv {src_art_old} {dst_art}\n")
            
        f.write("echo 'Rename operations completed!'\n")
        
    print("Generated 'rename_remote.sh' successfully.")
    
    # 3. Write rename_local.py (Python script for Beast)
    print("Generating 'scripts/rename_local.py' for local rename...")
    with open("scripts/rename_local.py", "w", encoding="utf-8") as f:
        f.write(f"""import os

def rename_files():
    id_to_slug = {repr(id_to_slug)}
    id_to_old_slug = {repr(id_to_old_slug)}
    
    norm_path = "public/images/normal"
    large_path = "public/images/large"
    art_path = "public/images/art_crop"
    
    print("Renaming local files in public/images...")
    
    operations = []
    
    for card_id, slug in id_to_slug.items():
        old_slug = id_to_old_slug.get(card_id)
        for suffix in ["", "_0"]:
            uuid_file = f"{{card_id}}{{suffix}}.jpg"
            old_slug_file = f"{{old_slug}}{{suffix}}.jpg"
            dst_file = f"{{slug}}{{suffix}}.jpg"
            
            # Normal
            src_norm_uuid = os.path.join(norm_path, uuid_file)
            src_norm_old = os.path.join(norm_path, old_slug_file)
            dst_norm = os.path.join(norm_path, dst_file)
            
            if os.path.exists(src_norm_uuid):
                operations.append((src_norm_uuid, dst_norm))
            elif os.path.exists(src_norm_old) and src_norm_old != dst_norm:
                operations.append((src_norm_old, dst_norm))
                
            # Large
            src_large_uuid = os.path.join(large_path, uuid_file)
            src_large_old = os.path.join(large_path, old_slug_file)
            dst_large = os.path.join(large_path, dst_file)
            
            if os.path.exists(src_large_uuid):
                operations.append((src_large_uuid, dst_large))
            elif os.path.exists(src_large_old) and src_large_old != dst_large:
                operations.append((src_large_old, dst_large))
                
            # Art Crop
            src_art_uuid = os.path.join(art_path, uuid_file)
            src_art_old = os.path.join(art_path, old_slug_file)
            dst_art = os.path.join(art_path, dst_file)
            
            if os.path.exists(src_art_uuid):
                operations.append((src_art_uuid, dst_art))
            elif os.path.exists(src_art_old) and src_art_old != dst_art:
                operations.append((src_art_old, dst_art))
                
    print(f"Found {{len(operations):,}} local rename operations to perform.")
    
    renamed_count = 0
    for src, dst in operations:
        try:
            # Check if destination already exists to avoid overwriting or errors
            if not os.path.exists(dst):
                os.rename(src, dst)
                renamed_count += 1
            else:
                # If target exists and source exists, we just delete source since they are duplicates
                os.remove(src)
        except Exception as e:
            print(f"Error renaming {{src}}: {{e}}")
            
    print(f"Local renaming complete! {{renamed_count:,}} files renamed.")

if __name__ == '__main__':
    rename_files()
""")
        
    print("Generated 'scripts/rename_local.py' successfully.")

if __name__ == '__main__':
    main()
