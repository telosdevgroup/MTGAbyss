def calculate_similar_cards(db, oracle_id, all_embeddings=None):
    """
    Fetches pre-calculated similar cards directly from the MongoDB collection.
    Returns a sorted list of (similarity, oracle_id) tuples.
    """
    doc = db["similar_cards"].find_one({"oracle_id": oracle_id})
    if not doc or not doc.get("similar"):
        return []
        
    res = []
    for item in doc["similar"]:
        res.append((item["similarity"], item["oracle_id"]))
        
    return res
