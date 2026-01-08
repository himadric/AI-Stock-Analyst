import sys
import os
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load .env explicitly from api/ directory
env_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(env_path)

# Add api directory to path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.finance import FinanceService
from app.db import db

DATA_DIR = os.path.join(os.path.dirname(__file__), "../app/data")
INDICES_FILE = os.path.join(DATA_DIR, "sp_indices.json")
UEI_MAPPING_FILE = os.path.join(DATA_DIR, "uei_mapping.json")

KNOWN_GOVT_CONTRACTORS = {
    "LMT", "RTX", "GD", "NOC", "BA", "HII", "LHX", "KTOS", "AVAV", "LDOS", 
    "BAH", "SAIC", "CACI", "TXT", "BWXT", "VEC", "CW", "HEI", "TDG", "SPR"
}

def generate_govt_contract_data():
    print("Starting Govt Contracts generation...", flush=True)
    service = FinanceService()
    
    if not os.path.exists(INDICES_FILE):
        print(f"Indices file not found at {INDICES_FILE}", flush=True)
        return

    with open(INDICES_FILE, "r") as f:
        indices = json.load(f)

    # Load UEI Mapping
    uei_map = {}
    if os.path.exists(UEI_MAPPING_FILE):
        try:
            with open(UEI_MAPPING_FILE, "r") as f:
                uei_map = json.load(f)
            print(f"Loaded {len(uei_map)} UEI mappings.", flush=True)
        except Exception as e:
             print(f"Error loading UEI mapping: {e}", flush=True)

    # Map Category Str to DB ID
    cat_map = {
        "Small Cap": "small_cap",
        "Mid Cap": "mid_cap",
        "Large Cap": "large_cap"
    }

    mongo_db = db.get_db()
    collection = mongo_db["govt_contacts"]

    # Reverse map indices for category lookup
    ticker_to_category = {}
    for category, tickers in indices.items():
        for ticker in tickers:
            ticker_to_category[ticker] = category

    # We will collect all results into a single list
    all_contractors = []

    print(f"Starting generation using {len(uei_map)} known contractors...", flush=True)

    for ticker, uei_data in uei_map.items():
        uei = uei_data.get("uei")
        name = uei_data.get("name")
        
        print(f"Processing {ticker} ({name})...", flush=True)
        
        try:
            # Fetch Backlog
            backlog_data = service.get_govt_backlog(ticker, uei=uei)
            
            if backlog_data:
                # Determine Category (Default to Large Cap if unknown)
                category = ticker_to_category.get(ticker, "Large Cap")
                
                # Add category to data for filtering later
                backlog_data["category"] = category
                
                all_contractors.append(backlog_data)
                
                # Rate limit
                time.sleep(0.2)
            else:
                 print(f"  No backlog data found for {ticker}", flush=True)

        except Exception as e:
            print(f"  Error processing {ticker}: {e}", flush=True)
            time.sleep(0.2)

    # Save to MongoDB (Single Document)
    mongo_db = db.get_db()
    collection = mongo_db["govt_contracts"] # Fixed typo: contacts -> contracts

    if not all_contractors:
        print("No contractors found, skipping save.", flush=True)
        return

    # Sort all by book to bill
    all_contractors.sort(key=lambda x: x["book_to_bill_ratio"], reverse=True)
    
    print(f"Saving {len(all_contractors)} records to MongoDB (govt_contracts.contractors)...", flush=True)
    try:
        result = collection.update_one(
            {"_id": "contractors"},
            {
                "$set": {
                    "companies": all_contractors,
                    "last_updated": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        print(f"Saved. Modified: {result.modified_count}, Upserted: {result.upserted_id}", flush=True)
    except Exception as e:
        print(f"Error saving to MongoDB: {e}", flush=True)

    print("\nGovt Contracts generation complete.", flush=True)

if __name__ == "__main__":
    generate_govt_contract_data()
