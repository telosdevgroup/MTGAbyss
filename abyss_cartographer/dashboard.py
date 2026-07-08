import os
import sys
import json
from flask import Flask, render_template, request, redirect, url_for

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abyss_cartographer.db import get_db, get_stat

app = Flask(__name__)

@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Fetch general stats
    cursor.execute("SELECT COUNT(*) FROM cards")
    total_cards = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT source_oracle_id) FROM edges")
    edges_built = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM travel_profiles")
    profiles_done = cursor.fetchone()[0]
    
    stats = {
        "sync_status": get_stat("sync_status", "Unknown"),
        "total_cards": total_cards,
        "edges_built": edges_built,
        "profiles_done": profiles_done
    }
    
    # 2. Get top 15 global histogram cards
    cursor.execute("SELECT profile_data FROM travel_profiles")
    global_counts = {}
    for row in cursor.fetchall():
        try:
            profile = json.loads(row[0])
            for oid, count in profile.items():
                global_counts[oid] = global_counts.get(oid, 0) + count
        except Exception:
            continue
            
    # Map OIDs to card names
    sorted_global = sorted(global_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    top_global = []
    for oid, count in sorted_global:
        cursor.execute("SELECT name, oracle_id FROM cards WHERE oracle_id = ?", (oid,))
        c_row = cursor.fetchone()
        name = c_row["name"] if c_row else oid
        top_global.append({"name": name, "oracle_id": oid, "count": count})
        
    # 3. Get recent walks
    cursor.execute("SELECT start_name, path_text, created_at FROM walk_history ORDER BY id DESC LIMIT 15")
    recent_walks = [{
        "start_name": r["start_name"],
        "path_text": r["path_text"],
        "created_at": r["created_at"]
    } for r in cursor.fetchall()]
    
    # 4. Dropdown list of cards
    cursor.execute("SELECT oracle_id, name FROM cards ORDER BY name ASC LIMIT 300")
    dropdown_cards = [{"oracle_id": r["oracle_id"], "name": r["name"]} for r in cursor.fetchall()]
    
    conn.close()
    return render_template(
        "dashboard.html",
        stats=stats,
        top_global=top_global,
        recent_walks=recent_walks,
        dropdown_cards=dropdown_cards
    )

@app.route("/card/<oracle_id>")
def card_profile(oracle_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Card details
    cursor.execute("SELECT name, slug FROM cards WHERE oracle_id = ?", (oracle_id,))
    card = cursor.fetchone()
    if not card:
        conn.close()
        return "Card not found", 404
        
    # Outgoing edges
    cursor.execute("""
        SELECT e.target_oracle_id, e.similarity, c.name FROM edges e
        LEFT JOIN cards c ON e.target_oracle_id = c.oracle_id
        WHERE e.source_oracle_id = ?
        ORDER BY e.similarity DESC
    """, (oracle_id,))
    edges = [{
        "oracle_id": r["target_oracle_id"],
        "name": r["name"] or r["target_oracle_id"],
        "similarity": round(r["similarity"], 4)
    } for r in cursor.fetchall()]
    
    # Travel profile histogram
    cursor.execute("SELECT profile_data, simulations_run FROM travel_profiles WHERE oracle_id = ?", (oracle_id,))
    prof_row = cursor.fetchone()
    destinations = []
    
    if prof_row:
        profile = json.loads(prof_row["profile_data"])
        sims = prof_row["simulations_run"]
        sorted_dests = sorted(profile.items(), key=lambda x: x[1], reverse=True)
        for dest_oid, count in sorted_dests:
            cursor.execute("SELECT name FROM cards WHERE oracle_id = ?", (dest_oid,))
            c_row = cursor.fetchone()
            name = c_row["name"] if c_row else dest_oid
            destinations.append({
                "name": name,
                "oracle_id": dest_oid,
                "percentage": round(count / sims * 100, 2)
            })
            
    conn.close()
    return render_template(
        "card_profile.html",
        card=card,
        oracle_id=oracle_id,
        edges=edges,
        destinations=destinations
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085)
