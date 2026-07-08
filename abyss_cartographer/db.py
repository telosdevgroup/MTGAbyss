import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cartographer.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Cards metadata table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cards (
        oracle_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL
    )
    """)
    
    # Directed similarity edges table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS edges (
        source_oracle_id TEXT,
        target_oracle_id TEXT,
        similarity REAL,
        PRIMARY KEY (source_oracle_id, target_oracle_id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_oracle_id)")
    
    # Travel profiles / walk histograms table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS travel_profiles (
        oracle_id TEXT PRIMARY KEY,
        profile_data TEXT NOT NULL, -- JSON string mapping target_oracle_id -> count
        simulations_run INTEGER DEFAULT 0
    )
    """)
    
    # Walk history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS walk_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_name TEXT,
        path_text TEXT, -- Comma-separated or arrow-separated names
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Stats table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

def save_stat(key, value):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO stats (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_stat(key, default=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM stats WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["value"]
    return default
