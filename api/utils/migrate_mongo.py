import sys
import os
import json
from datetime import datetime

# Add api to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db import db

LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), "../app/data/leaderboard.json")

def migrate():
    print("Starting migration to MongoDB...")
    
    if not os.path.exists(LEADERBOARD_FILE):
        print("Leaderboard file not found!")
        return

    with open(LEADERBOARD_FILE, "r") as f:
        data = json.load(f)

    mongo_db = db.get_db()
    collection = mongo_db["leaderboard"]

    # Map JSON keys to requested Document IDs
    mapping = {
        "Small Cap": "small_cap",
        "Mid Cap": "mid_cap",
        "Large Cap": "large_cap"
    }

    for json_key, doc_id in mapping.items():
        if json_key in data:
            print(f"Migrating {json_key} -> {doc_id}...")
            companies = data[json_key]
            
            # Upsert document
            result = collection.update_one(
                {"_id": doc_id},
                {
                    "$set": {
                        "companies": companies,
                        "last_updated": datetime.utcnow()
                    }
                },
                upsert=True
            )
            print(f"  Matched: {result.matched_count}, Modified: {result.modified_count}, Upserted: {result.upserted_id}")
        else:
            print(f"Skipping {json_key} (Not found in JSON)")

    print("Migration complete.")

if __name__ == "__main__":
    migrate()
