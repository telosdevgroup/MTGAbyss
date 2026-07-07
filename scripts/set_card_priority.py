import os
import sys
import argparse
import pymongo

# Add parent directory to path to allow importing db_mongo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db_mongo import get_mongo_db

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Bulk set base_priority on cards and card printings.")
    parser.add_argument("--base-priority", type=int, help="Priority value to set (higher number = higher priority)")
    parser.add_argument("--clear", action="store_true", help="Clear (remove) base_priority field from matched cards")
    
    # Selection criteria
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--names", type=str, help="Comma-separated exact card names to target")
    group.add_argument("--name-contains", type=str, help="Substring to match card names case-insensitively")
    group.add_argument("--file", type=str, help="Path to file containing card names (one per line)")
    group.add_argument("--tag", type=str, help="Target cards that have this tag")
    group.add_argument("--oracle-ids", type=str, help="Comma-separated oracle_ids to target")
    group.add_argument("--all", action="store_true", help="Target all cards in the database")

    args = parser.parse_args()

    if not args.clear and args.base_priority is None:
        print("Error: You must specify --base-priority or --clear.")
        sys.exit(1)

    db = get_mongo_db()

    # Step 1: Resolve the query for 'cards' collection
    query = {}
    if args.names:
        names_list = [n.strip() for n in args.names.split(",") if n.strip()]
        query["name"] = {"$in": names_list}
    elif args.name_contains:
        query["name"] = {"$regex": args.name_contains, "$options": "i"}
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: File '{args.file}' does not exist.")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            names_list = [line.strip() for line in f if line.strip()]
        query["name"] = {"$in": names_list}
    elif args.tag:
        query["tags.tag"] = args.tag
    elif args.oracle_ids:
        ids_list = [i.strip() for i in args.oracle_ids.split(",") if i.strip()]
        query["oracle_id"] = {"$in": ids_list}
    elif args.all:
        query = {}

    # Step 2: Determine update operation
    if args.clear:
        update_op = {"$unset": {"base_priority": ""}}
        action_str = "Cleared base_priority"
    else:
        update_op = {"$set": {"base_priority": args.base_priority}}
        action_str = f"Set base_priority={args.base_priority}"

    # Step 3: Perform updates on 'cards'
    print(f"Finding cards matching query: {query}")
    matched_cards = list(db["cards"].find(query, {"oracle_id": 1, "name": 1}))
    matched_count = len(matched_cards)

    if matched_count == 0:
        print("No cards matched the criteria. No updates performed.")
        return

    print(f"Found {matched_count} matching card(s). Performing update...")
    cards_result = db["cards"].update_many(query, update_op)
    print(f"Updated {cards_result.modified_count} document(s) in 'cards' collection.")

    # Step 4: Perform updates on 'card_prints' using the oracle_ids of matched cards
    oracle_ids = [c["oracle_id"] for c in matched_cards if c.get("oracle_id")]
    if oracle_ids:
        print(f"Updating printings in 'card_prints' collection for {len(oracle_ids)} oracle_id(s)...")
        prints_result = db["card_prints"].update_many(
            {"oracle_id": {"$in": oracle_ids}},
            update_op
        )
        print(f"Updated {prints_result.modified_count} document(s) in 'card_prints' collection.")
    else:
        print("No valid oracle_ids found to update printings.")

    print("\nBulk priority update finished successfully.")

if __name__ == "__main__":
    main()
