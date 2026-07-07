import os
import sys
import json
import urllib.request
import datetime
import shutil

def main():
    manifest_url = "https://api.scryfall.com/bulk-data"
    user_agent = "MTGAbyss/0.1 local-dev"

    print("Fetching Scryfall bulk data manifest...")
    try:
        req = urllib.request.Request(manifest_url, headers={"User-Agent": user_agent, "Accept": "*/*"})
        with urllib.request.urlopen(req) as res:
            manifest_data = json.loads(res.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching manifest: {e}")
        return

    # Find the bulk item with type 'default_cards'
    default_item = None
    if "data" in manifest_data:
        for item in manifest_data["data"]:
            if item.get("type") == "default_cards":
                default_item = item
                break

    if not default_item:
        print("Error: Could not find default_cards bulk item in manifest.")
        return

    download_uri = default_item.get("download_uri")
    updated_at = default_item.get("updated_at")
    print(f"default_cards updated_at: {updated_at}")
    print(f"Downloading from: {download_uri} ...")

    # Save default_cards.json temporarily
    temp_json_path = "default_cards_temp.json"
    try:
        req = urllib.request.Request(download_uri, headers={"User-Agent": user_agent, "Accept": "*/*"})
        with urllib.request.urlopen(req) as res, open(temp_json_path, "wb") as f_out:
            shutil.copyfileobj(res, f_out)
    except Exception as e:
        print(f"Error downloading Default Cards dataset: {e}")
        return

    # Convert JSON array to JSONL
    date_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    jsonl_filename = f"default-cards-{date_str}.jsonl"
    print(f"Converting to JSONL: {jsonl_filename} ...")
    
    try:
        with open(temp_json_path, "r", encoding="utf-8") as f_in:
            cards_list = json.load(f_in)
        
        with open(jsonl_filename, "w", encoding="utf-8") as f_out:
            for card in cards_list:
                f_out.write(json.dumps(card) + "\n")
        
        print(f"Successfully created {jsonl_filename} with {len(cards_list)} card prints.")
        os.remove(temp_json_path)
    except Exception as e:
        print(f"Error converting JSON to JSONL: {e}")

if __name__ == "__main__":
    main()
