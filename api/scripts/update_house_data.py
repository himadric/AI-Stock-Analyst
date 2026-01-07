import sys
import os
import json
import requests
from datetime import datetime
from pymongo import MongoClient

try:
    from dotenv import load_dotenv
    # Load env from .env file (for local run)
    load_dotenv()
except ImportError:
    pass

# Add parent directory to path to import app modules if needed
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(api_dir)

def update_house_db():
    print("Fetching US House trades from FMP...")
    
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        print("Error: FMP_API_KEY not found in environment variables.")
        sys.exit(1)

    url = f"https://financialmodelingprep.com/stable/house-latest?apikey={api_key}&limit=10"
    
    try:
        res = requests.get(url)
        if res.status_code != 200:
            print(f"Error fetching data: {res.status_code} {res.text}")
            sys.exit(1)
            
        data = res.json()
        print(f"Fetched {len(data)} records.")
        
    except Exception as e:
        print(f"Network error: {e}")
        sys.exit(1)
        
    # MongoDB Connection
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    if not uri:
        print("MONGO_URI not found in environment variables.")
        sys.exit(1)
        
    client = MongoClient(uri)
    # Explicit connection to ai_stock_analyst
    db = client["ai_stock_analyst"]
    collection = db["house_tracker"]
    
    # We will store this as a single document for "recent trades" to match Vanguard pattern
    # This makes frontend fetching very simple (one doc)
    
    doc = {
        "type": "recent_trades",
        "updated_at": datetime.utcnow(),
        "source": "FMP stable/house-latest",
        "count": len(data),
        "data": data 
    }
    
    print(f"Upserting to MongoDB collection 'house_tracker'...")
    
    result = collection.replace_one(
        {"type": "recent_trades"},
        doc,
        upsert=True
    )
    
    print(f"Result: Matched {result.matched_count}, Modified {result.modified_count}, Upserted {result.upserted_id}")
    print("Database update complete.")

if __name__ == "__main__":
    update_house_db()
