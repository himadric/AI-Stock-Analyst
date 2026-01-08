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

    # Try to fetch 100 records as requested
    print(f"Fetching US House trades (limit 100)...")
    url = f"https://financialmodelingprep.com/stable/house-latest?apikey={api_key}&limit=100"
    
    new_data = []
    try:
        res = requests.get(url)
        if res.status_code == 200:
            new_data = res.json()
            print(f"Fetched {len(new_data)} new records.")
        elif res.status_code == 402:
             print("Limit 100 failed (Premium restricted). Falling back to limit=10 (Safe Mode)...")
             url = f"https://financialmodelingprep.com/stable/house-latest?apikey={api_key}&limit=10"
             res = requests.get(url)
             if res.status_code == 200:
                 new_data = res.json()
                 print(f"Fetched {len(new_data)} new records (fallback).")
             else:
                 print(f"Fallback failed: {res.status_code} {res.text}")
                 sys.exit(1)
        else:
            print(f"Error fetching data: {res.status_code} {res.text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Network error: {e}")
        sys.exit(1)
        
    # MongoDB Connection
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    if not uri:
        print("MONGO_URI not found in environment variables.")
        sys.exit(1)
        
    client = MongoClient(uri)
    db = client["ai_stock_analyst"]
    collection = db["house_tracker"]
    
    # ACCUMULATION STRATEGY
    # 1. Get existing data
    existing_doc = collection.find_one({"type": "recent_trades"})
    existing_data = existing_doc.get("data", []) if existing_doc else []
    
    # 2. Merge and Deduplicate
    # Create a set of unique identifiers (e.g. disclosureDate + ticker + transactionDate + amount)
    # Link is best if unique, but some might be missing.
    # We'll use a composite key string.
    
    seen = set()
    cleaned_data = []
    
    # Helper to generate ID
    def get_id(item):
        return f"{item.get('disclosureDate')}|{item.get('transactionDate')}|{item.get('symbol')}|{item.get('amount')}|{item.get('firstName')}"

    # Add new items first (to update/ensure they are in)
    for item in new_data:
        uid = get_id(item)
        if uid not in seen:
            seen.add(uid)
            cleaned_data.append(item)
            
    # Add existing items if not duplicates
    for item in existing_data:
        uid = get_id(item)
        if uid not in seen:
            seen.add(uid)
            cleaned_data.append(item)
            
    # Sort by disclosureDate descending
    cleaned_data.sort(key=lambda x: x.get('disclosureDate', ''), reverse=True)
    
    # Optional: Trim to e.g. 1000 items to prevent infinite growth
    cleaned_data = cleaned_data[:1000]

    doc = {
        "type": "recent_trades",
        "updated_at": datetime.utcnow(),
        "source": "FMP stable/house-latest (Accumulating)",
        "count": len(cleaned_data),
        "data": cleaned_data
    }
    
    print(f"Upserting {len(cleaned_data)} accumulated records to MongoDB...")
    
    result = collection.replace_one(
        {"type": "recent_trades"},
        doc,
        upsert=True
    )
    
    print(f"Result: Matched {result.matched_count}, Modified {result.modified_count}, Upserted {result.upserted_id}")
    print("Database update complete.")

if __name__ == "__main__":
    update_house_db()
