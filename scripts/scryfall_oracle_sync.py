import argparse
import os
import json
import urllib.request
import urllib.error
import shutil

def main():
    parser = argparse.ArgumentParser(description="Sync oracle_cards bulk data from Scryfall.")
    parser.add_argument("--force", action="store_true", help="Force download even if unchanged")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (do not download or write files)")
    parser.add_argument("--output-dir", default="data/scryfall/bulk", help="Directory to save bulk data")
    parser.add_argument("--user-agent", default="MTGAbyss/0.1 local-dev", help="User-Agent header for Scryfall requests")

    args = parser.parse_args()

    output_dir = args.output_dir
    user_agent = args.user_agent

    manifest_url = "https://api.scryfall.com/bulk-data"

    print("Fetching manifest...")
    try:
        req = urllib.request.Request(manifest_url, headers={"User-Agent": user_agent, "Accept": "*/*"})
        with urllib.request.urlopen(req) as res:
            manifest_data = json.loads(res.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching manifest: {e}")
        return

    # Find the bulk item with type 'oracle_cards'
    oracle_item = None
    if "data" in manifest_data:
        for item in manifest_data["data"]:
            if item.get("type") == "oracle_cards":
                oracle_item = item
                break

    if not oracle_item:
        print("Error: Could not find oracle_cards bulk item in manifest.")
        return

    updated_at = oracle_item.get("updated_at")
    download_uri = oracle_item.get("download_uri")
    print(f"oracle_cards updated_at: {updated_at}")

    # Local files paths
    manifest_path = os.path.join(output_dir, "manifest.json")
    oracle_path = os.path.join(output_dir, "oracle_cards.json")
    metadata_path = os.path.join(output_dir, "metadata.json")

    # Read local metadata
    local_metadata = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                local_metadata = json.load(f)
        except Exception:
            pass

    local_updated_at = local_metadata.get("oracle_cards", {}).get("updated_at")
    oracle_exists = os.path.exists(oracle_path)

    # Determine status
    if not oracle_exists:
        status = "missing"
    elif args.force:
        status = "stale" # Force download
    elif local_updated_at != updated_at:
        status = "stale"
    else:
        status = "unchanged"

    print(f"Local oracle_cards: {status}")

    if status == "unchanged":
        print("Done.")
        return

    if args.dry_run:
        print(f"[Dry Run] Would download oracle_cards from {download_uri}")
        print(f"[Dry Run] Would save files to {output_dir}")
        print("Done.")
        return

    # Make output directory
    os.makedirs(output_dir, exist_ok=True)

    print("Downloading oracle_cards...")
    part_path = oracle_path + ".part"
    try:
        # Download safely
        req = urllib.request.Request(download_uri, headers={"User-Agent": user_agent, "Accept": "*/*"})
        with urllib.request.urlopen(req) as res, open(part_path, "wb") as f_out:
            shutil.copyfileobj(res, f_out)

        # Validate JSON parse
        with open(part_path, "r", encoding="utf-8") as f_in:
            parsed_data = json.load(f_in)
            records_count = len(parsed_data) if isinstance(parsed_data, list) else 0

        # Replace oracle_cards.json only after successful parse
        if os.path.exists(oracle_path):
            os.remove(oracle_path)
        os.rename(part_path, oracle_path)
        print("Saved oracle_cards.json")
        print(f"Records: {records_count}")

        # Update metadata.json and manifest.json
        local_metadata["oracle_cards"] = {
            "updated_at": updated_at,
            "download_uri": download_uri
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(local_metadata, f, indent=2)

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

    except Exception as e:
        print(f"Error during download or validation: {e}")
        if os.path.exists(part_path):
            try:
                os.remove(part_path)
            except Exception:
                pass
        return

    print("Done.")

if __name__ == "__main__":
    main()
