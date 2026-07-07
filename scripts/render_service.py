import os
import sys
import subprocess
import argparse
from flask import Flask, request, jsonify

app = Flask(__name__)

# Absolute paths
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GENERATOR_SCRIPT = os.path.join(WORKSPACE_DIR, "generate_card_page.py")

def slugify_name(s):
    import re
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s.strip('-')

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/render/card", methods=["POST"])
def render_card():
    try:
        data = request.json or {}
        card_name = data.get("card_name")
        
        if not card_name:
            return jsonify({"error": "Missing 'card_name' in payload"}), 400
            
        print(f"Running generator subprocess for: '{card_name}'")
        
        # Run generate_card_page.py <card_name>
        result = subprocess.run(
            [sys.executable, GENERATOR_SCRIPT, card_name],
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Subprocess failed with code {result.returncode}")
            print(f"Stderr: {result.stderr}")
            return jsonify({
                "error": "Generator subprocess failed",
                "code": result.returncode,
                "stderr": result.stderr,
                "stdout": result.stdout
            }), 500
            
        # Determine the output path based on slugified name
        slug = slugify_name(card_name)
        output_path = os.path.join(WORKSPACE_DIR, "public", "card", slug, "index.html")
        
        if not os.path.exists(output_path):
            # Try searching the directory for the generated file in case slug is slightly different
            # (e.g. generate_card_page prints output path at the end, we can parse it or guess)
            print(f"Expected file not found at: {output_path}")
            return jsonify({"error": f"Generated HTML file not found at expected path: {output_path}"}), 500
            
        with open(output_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        return html_content, 200, {"Content-Type": "text/html"}

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Generator subprocess timed out (30s limit)"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subprocess Render Service")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to")
    parser.add_argument("--port", type=int, default=5001, help="Port to run server on")
    args = parser.parse_args()

    print(f"Starting Subprocess Render Service on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
