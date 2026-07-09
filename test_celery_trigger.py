import sys
from celery_app import app
from tasks import generate_embedding, generate_lure, generate_and_deploy_page
from db_mongo import get_mongo_db

def main():
    print("Connecting to MongoDB...")
    db = get_mongo_db()
    
    # Query a card to test
    card = db["cards"].find_one({"name": "Trouble in Pairs"})
    if not card:
        card = db["cards"].find_one({})
    
    if not card:
        print("Error: No cards found in MongoDB database.")
        sys.exit(1)
        
    oracle_id = card["oracle_id"]
    name = card["name"]
    
    print(f"\n--- Celery Verification Tool ---")
    print(f"Target Card: {name}")
    print(f"Oracle ID:   {oracle_id}")
    print(f"---------------------------------")
    print("To queue a test embedding generation task, run:")
    print(f"  python -c \"from tasks import generate_embedding; generate_embedding.delay('{oracle_id}')\"")
    print("\nTo queue a test lure generation task, run:")
    print(f"  python -c \"from tasks import generate_lure; generate_lure.delay('{oracle_id}')\"")
    print("\nTo queue a test page build/deploy task, run:")
    print(f"  python -c \"from tasks import generate_and_deploy_page; generate_and_deploy_page.delay('{name}')\"")

if __name__ == "__main__":
    main()
