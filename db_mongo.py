import os
import pymongo

_CLIENT = None

def get_mongo_db():
    global _CLIENT
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://192.168.1.213:27017")
    db_name = os.environ.get("MONGODB_DB", "mtgabyss")
    if _CLIENT is None:
        _CLIENT = pymongo.MongoClient(mongo_uri)
        try:
            # Enforce 73GB (Prime!) WiredTiger in-memory cache on connection startup
            _CLIENT.admin.command({"setParameter": 1, "wiredTigerEngineRuntimeConfig": "cache_size=73G"})
        except Exception:
            pass
    return _CLIENT[db_name]

def get_old_db():
    """Returns the mtgabyss database (card_embeddings, similar_cards)."""
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = pymongo.MongoClient(mongo_uri)
    return client["mtgabyss"]

def ensure_indexes(db):
    # Cards collection indexes
    cards = db["cards"]
    cards.create_index("id", unique=True)
    cards.create_index("oracle_id")
    cards.create_index("slug")
    cards.create_index("name")
    cards.create_index("lang")
    cards.create_index("tags.tag")
    cards.create_index("base_priority")
    
    # Generated sections collection indexes
    generated_sections = db["generated_sections"]
    # oracle_id + language + section_type + persona + prompt_hash unique if practical
    generated_sections.create_index(
        [("oracle_id", pymongo.ASCENDING), 
         ("language", pymongo.ASCENDING), 
         ("section_type", pymongo.ASCENDING),
         ("persona", pymongo.ASCENDING),
         ("prompt_hash", pymongo.ASCENDING)], 
        unique=True
    )
    generated_sections.create_index("card_slug")
    generated_sections.create_index("status")

    # Generation jobs collection indexes
    generation_jobs = db["generation_jobs"]
    generation_jobs.create_index("status")
    generation_jobs.create_index("priority")
    generation_jobs.create_index("claimed_by")
    # compound index on oracle_id + language + section_type
    generation_jobs.create_index(
        [("oracle_id", pymongo.ASCENDING), 
         ("language", pymongo.ASCENDING), 
         ("section_type", pymongo.ASCENDING)]
    )
    
    # Rulings collection indexes
    rulings = db["rulings"]
    rulings.create_index("oracle_id")
    
    # Build runs collection indexes
    build_runs = db["build_runs"]
    build_runs.create_index("started_at")

    # Scryfall catalogs collection indexes
    scryfall_catalogs = db["scryfall_catalogs"]
    scryfall_catalogs.create_index("catalog_key", unique=True)
    scryfall_catalogs.create_index("synced_at")

    # Mechanics collection indexes
    mechanics = db["mechanics"]
    mechanics.create_index("slug", unique=True)
    mechanics.create_index("term_type")
    mechanics.create_index("status")
    mechanics.create_index("source_catalog")

    # Abysses collection indexes
    abysses = db["abysses"]
    abysses.create_index([("entity_type", pymongo.ASCENDING), ("oracle_id", pymongo.ASCENDING)], unique=True)
    abysses.create_index("slug")
    abysses.create_index("content.lure.status")
    abysses.create_index("content.hook.status")

    # Image metadata collection indexes
    image_metadata = db["image_metadata"]
    image_metadata.create_index([("scryfall_id", pymongo.ASCENDING), ("size", pymongo.ASCENDING), ("face_index", pymongo.ASCENDING)], unique=True)
    image_metadata.create_index("oracle_id")

    # Lite card printings collection indexes
    card_prints = db["card_prints"]
    card_prints.create_index("id", unique=True)
    card_prints.create_index("oracle_id")
    card_prints.create_index("name")
    card_prints.create_index("lang")
    card_prints.create_index("base_priority")






