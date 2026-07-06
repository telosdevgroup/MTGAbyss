import argparse
import os
import json
import urllib.request
import urllib.error
import time
from datetime import datetime

CATALOGS = [
    "card-names", "artist-names", "word-bank", "supertypes", "card-types",
    "artifact-types", "battle-types", "creature-types", "enchantment-types",
    "land-types", "planeswalker-types", "spell-types", "powers", "toughnesses",
    "loyalties", "keyword-abilities", "keyword-actions", "ability-words",
    "flavor-words", "watermarks"
]

def main():
    parser = argparse.ArgumentParser(description="Sync Scryfall catalog data.")
    parser.add_argument("--only", help="Comma-separated list of catalogs to sync")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (do not download or write files)")
    parser.add_argument("--force", action="store_true", help="Force download even if already cached (not used/necessary since we always fetch, but kept for CLI compatibility)")
    parser.add_argument("--output-dir", default="data/scryfall/catalogs", help="Directory to save catalog JSONs")
    parser.add_argument("--user-agent", default="MTGAbyss/0.1 local-dev", help="User-Agent header")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay in seconds between requests")

    args = parser.parse_args()

    output_dir = args.output_dir
    user_agent = args.user_agent
    delay = args.delay

    # Filter catalogs if --only is specified
    targets = CATALOGS
    if args.only:
        only_list = [c.strip() for c in args.only.split(",") if c.strip()]
        targets = [c for c in CATALOGS if c in only_list]
        # Check for invalid targets
        invalid = [c for c in only_list if c not in CATALOGS]
        if invalid:
            print(f"Warning: Ignored invalid catalog names: {', '.join(invalid)}")

    if not targets:
        print("No valid catalogs to sync.")
        return

    print("Syncing Scryfall catalogs...")

    # Load existing metadata if any
    metadata_path = os.path.join(output_dir, "metadata.json")
    metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass

    for i, catalog in enumerate(targets):
        if i > 0 and not args.dry_run:
            time.sleep(delay)

        endpoint = f"https://api.scryfall.com/catalog/{catalog}"
        file_path = os.path.join(output_dir, f"{catalog}.json")

        print(f"Downloading {catalog}...")

        if args.dry_run:
            print(f"[Dry Run] Would download {endpoint} to {file_path}")
            continue

        os.makedirs(output_dir, exist_ok=True)
        part_path = file_path + ".part"

        status = "failed"
        error_msg = None
        item_count = 0
        now_str = datetime.now().isoformat()

        try:
            req = urllib.request.Request(endpoint, headers={"User-Agent": user_agent, "Accept": "application/json"})
            with urllib.request.urlopen(req) as res:
                response_data = json.loads(res.read().decode("utf-8"))

            if "data" not in response_data or not isinstance(response_data["data"], list):
                raise ValueError("Response JSON does not contain a 'data' array.")

            item_count = len(response_data["data"])

            # Save part file
            with open(part_path, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2)

            # Atomically replace final file
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(part_path, file_path)

            print(f"Saved {catalog}.json: {item_count} items")
            status = "success"

        except Exception as e:
            error_msg = str(e)
            print(f"Error downloading {catalog}: {error_msg}")
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass

        # Update metadata entry
        metadata[catalog] = {
            "catalog_name": catalog,
            "endpoint": endpoint,
            "local_path": os.path.relpath(file_path, start=os.getcwd()).replace("\\", "/"),
            "item_count": item_count if status == "success" else metadata.get(catalog, {}).get("item_count", 0),
            "downloaded_at": now_str,
            "status": status
        }
        if error_msg:
            metadata[catalog]["error"] = error_msg
        else:
            metadata[catalog].pop("error", None)

    # Save metadata.json
    if not args.dry_run:
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata file: {e}")

    print("Done.")

if __name__ == "__main__":
    main()
