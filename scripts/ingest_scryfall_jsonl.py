import os
import sys
import json
import sqlite3
import time
import re
from concurrent.futures import ProcessPoolExecutor

# Slugify function
def slugify(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

def parse_lines_chunk(lines):
    """Parse a list of JSON string lines into Python dicts."""
    results = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                results.append(json.loads(line))
            except Exception as e:
                # If error, return raw or print to stderr
                pass
    return results

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    # Apply PRAGMAs for speed
    conn.execute("PRAGMA journal_mode = MEMORY;")
    conn.execute("PRAGMA synchronous = OFF;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -1000000;")
    return conn

def setup_database(conn):
    conn.execute("DROP TABLE IF EXISTS cards;")
    conn.execute("DROP TABLE IF EXISTS rulings;")
    conn.execute("DROP TABLE IF EXISTS oracle_tags;")
    
    conn.execute("""
    CREATE TABLE cards (
        oracle_id TEXT PRIMARY KEY,
        name TEXT,
        slug TEXT,
        layout TEXT,
        mana_cost TEXT,
        cmc REAL,
        type_line TEXT,
        oracle_text TEXT,
        power TEXT,
        toughness TEXT,
        loyalty TEXT,
        colors_json TEXT,
        color_identity_json TEXT,
        keywords_json TEXT,
        legalities_json TEXT,
        vintage_legality TEXT,
        reserved INTEGER,
        reprint INTEGER,
        games_json TEXT,
        produced_mana_json TEXT,
        image_uris_json TEXT,
        card_faces_json TEXT,
        all_parts_json TEXT,
        related_uris_json TEXT,
        purchase_uris_json TEXT,
        scryfall_uri TEXT,
        source_json TEXT
    );
    """)
    
    conn.execute("""
    CREATE TABLE rulings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oracle_id TEXT,
        source TEXT,
        published_at TEXT,
        comment TEXT,
        source_json TEXT
    );
    """)
    
    conn.execute("""
    CREATE TABLE oracle_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oracle_id TEXT,
        tag TEXT,
        namespace TEXT,
        category TEXT,
        source TEXT,
        source_json TEXT
    );
    """)
    conn.commit()

def create_indexes(conn):
    print("Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_slug ON cards(slug);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_vintage_legality ON cards(vintage_legality);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_oracle_id ON cards(oracle_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rulings_oracle_id ON rulings(oracle_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_oracle_tags_oracle_id ON oracle_tags(oracle_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_oracle_tags_tag ON oracle_tags(tag);")
    conn.commit()

def read_jsonl_in_parallel(filepath, executor, chunk_size=5000):
    """Read a JSONL file and parse using ProcessPoolExecutor."""
    with open(filepath, 'r', encoding='utf-8') as f:
        chunk = []
        futures = []
        for line in f:
            chunk.append(line)
            if len(chunk) >= chunk_size:
                futures.append(executor.submit(parse_lines_chunk, chunk))
                chunk = []
        if chunk:
            futures.append(executor.submit(parse_lines_chunk, chunk))
        
        # Yield results as they complete, but in order or as they finish
        for future in futures:
            yield future.result()

def main():
    db_path = "data/mtgabyss.sqlite"
    os.makedirs("data", exist_ok=True)
    
    # Locate files
    files = os.listdir('.')
    cards_file = next((f for f in files if f.startswith('oracle-cards') and f.endswith('.jsonl')), None)
    tags_file = next((f for f in files if f.startswith('oracle-tags') and f.endswith('.jsonl')), None)
    rulings_file = next((f for f in files if f.startswith('rulings') and f.endswith('.jsonl')), None)
    
    if not (cards_file and tags_file and rulings_file):
        print("Missing one or more Scryfall JSONL files in project root!")
        sys.exit(1)
        
    start_time = time.time()
    
    print(f"Connecting to database at {db_path}...")
    conn = get_db_connection(db_path)
    setup_database(conn)
    
    # We will use 16 workers
    max_workers = 16
    print(f"Starting parallel parsing with {max_workers} workers...")
    
    # Ingest cards
    cards_count = 0
    cards_batches_inserted = 0
    cards_batch_data = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        print(f"Reading and parsing cards from {cards_file}...")
        for parsed_chunk in read_jsonl_in_parallel(cards_file, executor, chunk_size=3000):
            for card in parsed_chunk:
                oracle_id = card.get('oracle_id')
                if not oracle_id:
                    continue
                
                name = card.get('name')
                slug = slugify(name)
                layout = card.get('layout')
                mana_cost = card.get('mana_cost')
                cmc = card.get('cmc')
                type_line = card.get('type_line')
                oracle_text = card.get('oracle_text')
                power = card.get('power')
                toughness = card.get('toughness')
                loyalty = card.get('loyalty')
                
                colors_json = json.dumps(card.get('colors', []))
                color_identity_json = json.dumps(card.get('color_identity', []))
                keywords_json = json.dumps(card.get('keywords', []))
                legalities_json = json.dumps(card.get('legalities', {}))
                
                legalities = card.get('legalities', {})
                vintage_legality = legalities.get('vintage', 'not_legal')
                
                reserved = 1 if card.get('reserved') else 0
                reprint = 1 if card.get('reprint') else 0
                
                games_json = json.dumps(card.get('games', []))
                produced_mana_json = json.dumps(card.get('produced_mana', []))
                image_uris_json = json.dumps(card.get('image_uris', {}))
                card_faces_json = json.dumps(card.get('card_faces', []))
                all_parts_json = json.dumps(card.get('all_parts', []))
                related_uris_json = json.dumps(card.get('related_uris', {}))
                purchase_uris_json = json.dumps(card.get('purchase_uris', {}))
                scryfall_uri = card.get('scryfall_uri')
                
                source_json = json.dumps(card)
                
                cards_batch_data.append((
                    oracle_id, name, slug, layout, mana_cost, cmc, type_line, oracle_text,
                    power, toughness, loyalty, colors_json, color_identity_json, keywords_json,
                    legalities_json, vintage_legality, reserved, reprint, games_json,
                    produced_mana_json, image_uris_json, card_faces_json, all_parts_json,
                    related_uris_json, purchase_uris_json, scryfall_uri, source_json
                ))
                
                cards_count += 1
                if cards_count % 5000 == 0:
                    print(f"Reading oracle cards {cards_count}...")
                    
            if len(cards_batch_data) >= 5000:
                conn.executemany("""
                INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
                """, cards_batch_data)
                conn.commit()
                cards_batches_inserted += 1
                print(f"Inserting cards batch {cards_batches_inserted}...")
                cards_batch_data = []
                
        if cards_batch_data:
            conn.executemany("""
            INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
            """, cards_batch_data)
            conn.commit()
            cards_batches_inserted += 1
            print(f"Inserting cards batch {cards_batches_inserted}...")
            
    # Ingest rulings
    rulings_count = 0
    rulings_batches_inserted = 0
    rulings_batch_data = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        print(f"Reading and parsing rulings from {rulings_file}...")
        for parsed_chunk in read_jsonl_in_parallel(rulings_file, executor, chunk_size=5000):
            for ruling in parsed_chunk:
                oracle_id = ruling.get('oracle_id')
                source = ruling.get('source')
                published_at = ruling.get('published_at')
                comment = ruling.get('comment')
                source_json = json.dumps(ruling)
                
                rulings_batch_data.append((
                    oracle_id, source, published_at, comment, source_json
                ))
                rulings_count += 1
                
                if rulings_count % 10000 == 0:
                    print(f"Reading rulings {rulings_count}...")
                    
            if len(rulings_batch_data) >= 10000:
                conn.executemany("""
                INSERT INTO rulings (oracle_id, source, published_at, comment, source_json)
                VALUES (?, ?, ?, ?, ?);
                """, rulings_batch_data)
                conn.commit()
                rulings_batches_inserted += 1
                print(f"Inserting rulings batch {rulings_batches_inserted}...")
                rulings_batch_data = []
                
        if rulings_batch_data:
            conn.executemany("""
            INSERT INTO rulings (oracle_id, source, published_at, comment, source_json)
            VALUES (?, ?, ?, ?, ?);
            """, rulings_batch_data)
            conn.commit()
            rulings_batches_inserted += 1
            print(f"Inserting rulings batch {rulings_batches_inserted}...")
            
    # Ingest tags
    tags_count = 0
    tags_batches_inserted = 0
    tags_batch_data = []
    detected_tags_fields = set()
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        print(f"Reading and parsing tags from {tags_file}...")
        for parsed_chunk in read_jsonl_in_parallel(tags_file, executor, chunk_size=1000):
            for tag_obj in parsed_chunk:
                for k in tag_obj.keys():
                    detected_tags_fields.add(k)
                
                taggings = tag_obj.get('taggings', [])
                tag_slug = tag_obj.get('slug') or tag_obj.get('label')
                namespace = tag_obj.get('type')
                category = tag_obj.get('category')
                source = tag_obj.get('uri')
                source_json = json.dumps(tag_obj)
                
                for tagging in taggings:
                    oracle_id = tagging.get('oracle_id')
                    if oracle_id:
                        tags_batch_data.append((
                            oracle_id, tag_slug, namespace, category, source, source_json
                        ))
                        tags_count += 1
                        
            if len(tags_batch_data) >= 10000:
                conn.executemany("""
                INSERT INTO oracle_tags (oracle_id, tag, namespace, category, source, source_json)
                VALUES (?, ?, ?, ?, ?, ?);
                """, tags_batch_data)
                conn.commit()
                tags_batches_inserted += 1
                print(f"Inserting tags batch {tags_batches_inserted}...")
                tags_batch_data = []
                
        if tags_batch_data:
            conn.executemany("""
            INSERT INTO oracle_tags (oracle_id, tag, namespace, category, source, source_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, tags_batch_data)
            conn.commit()
            tags_batches_inserted += 1
            print(f"Inserting tags batch {tags_batches_inserted}...")
            
    create_indexes(conn)
    conn.close()
    
    elapsed = time.time() - start_time
    print("\nIngest complete!")
    print(f"Cards ingested: {cards_count}")
    print(f"Rulings ingested: {rulings_count}")
    print(f"Tags ingested: {tags_count}")
    print(f"Elapsed ingest time: {elapsed:.2f} seconds")
    print(f"Oracle-tags detected field shape: {sorted(list(detected_tags_fields))}")

if __name__ == '__main__':
    main()
