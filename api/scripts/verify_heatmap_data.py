import os
import sys
from pymongo import MongoClient
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def verify_heatmap_data():
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    if not uri:
        print("MONGO_URI not found.")
        sys.exit(1)

    try:
        client = MongoClient(uri)
        db = client["ai_stock_analyst"]
        collection = db["snp_heatmap_data"]

        count = collection.count_documents({})
        print(f"Total records in 'snp_heatmap_data': {count}")

        if count > 0:
            sample = collection.find_one({}, {"_id": 0})
            print("\nSample Record:")
            print(json.dumps(sample, indent=2, default=str))
        else:
            print("No data found.")
            
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")

if __name__ == "__main__":
    verify_heatmap_data()
