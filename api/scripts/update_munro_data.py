import sys
import os
import json
from datetime import datetime
from pymongo import MongoClient

try:
    from dotenv import load_dotenv
    # Load env from .env file (for local run)
    load_dotenv()
except ImportError:
    pass

# Add parent directory to path to import app modules
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(api_dir)

from app.services.institution_service import InstitutionService

def update_db():
    print("Initializing InstitutionService...")
    service = InstitutionService()
    
    print("Fetching Munro Partners trades (Top 100)...")
    # This might take 30-60s
    data = service.get_munro_trades(limit=100)
    
    if "error" in data:
        print(f"Error fetching data: {data['error']}")
        sys.exit(1)
        
    print(f"Fetch complete. Report Date: {data.get('report_date')}")
    
    # MongoDB Connection
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    if not uri:
        print("MONGO_URI not found in environment variables.")
        sys.exit(1)
        
    client = MongoClient(uri)
    # Explicitly use the database name provided by user
    db = client["ai_stock_analyst"]
    collection = db["munro_tracker"]
    
    # Prepare documents
    doc_buy = {
        "type": "buy",
        "updated_at": datetime.utcnow(),
        "report_date": data.get("report_date"),
        "prev_report_date": data.get("prev_report_date"),
        "data": data.get("top_buys", [])
    }
    
    doc_sell = {
        "type": "sell",
        "updated_at": datetime.utcnow(),
        "report_date": data.get("report_date"),
        "prev_report_date": data.get("prev_report_date"),
        "data": data.get("top_sells", [])
    }
    
    print("Upserting to MongoDB collection 'munro_tracker'...")
    
    # Update Buys
    res_buy = collection.replace_one(
        {"type": "buy"},
        doc_buy,
        upsert=True
    )
    print(f"Buy Doc: Matched {res_buy.matched_count}, Modified {res_buy.modified_count}, Upserted {res_buy.upserted_id}")

    # Update Sells
    res_sell = collection.replace_one(
        {"type": "sell"},
        doc_sell,
        upsert=True
    )
    print(f"Sell Doc: Matched {res_sell.matched_count}, Modified {res_sell.modified_count}, Upserted {res_sell.upserted_id}")
    
    print("Database update complete.")

if __name__ == "__main__":
    update_db()
