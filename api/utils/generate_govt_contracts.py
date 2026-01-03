import sys
import os
import json
import time
from datetime import datetime

# Add api directory to path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.finance import FinanceService
from app.db import db

DATA_DIR = os.path.join(os.path.dirname(__file__), "../app/data")
INDICES_FILE = os.path.join(DATA_DIR, "sp_indices.json")

KNOWN_GOVT_CONTRACTORS = {
    "LMT", "RTX", "GD", "NOC", "BA", "HII", "LHX", "KTOS", "AVAV", "LDOS", 
    "BAH", "SAIC", "CACI", "TXT", "BWXT", "VEC", "CW", "HEI", "TDG", "SPR"
}

def generate_govt_contract_data():
    print("Starting Govt Contracts generation...")
    service = FinanceService()
    
    if not os.path.exists(INDICES_FILE):
        print(f"Indices file not found at {INDICES_FILE}")
        return

    with open(INDICES_FILE, "r") as f:
        indices = json.load(f)

    # Map Category Str to DB ID
    cat_map = {
        "Small Cap": "small_cap",
        "Mid Cap": "mid_cap",
        "Large Cap": "large_cap"
    }

    mongo_db = db.get_db()
    collection = mongo_db["govt_contacts"]

    for category, tickers in indices.items():
        doc_id = cat_map.get(category)
        if not doc_id:
            continue

        print(f"\nProcessing {category} -> {doc_id} ({len(tickers)} tickers)...")
        
        govt_contractors = []
        
        # Optimize: Check known tickers first if we want to skip broad scanning, 
        # but user asked to use sp_indices. So we scan efficiently.
        
        total = len(tickers)
        for i, ticker in enumerate(tickers):
            try:
                # Progress every 10 tickers or valid detections
                if i % 10 == 0:
                    print(f"  [{i+1}/{total}] Scanning... (Found {len(govt_contractors)})")

                # 1. Filter Check
                is_contractor = False
                if ticker in KNOWN_GOVT_CONTRACTORS:
                    is_contractor = True
                else:
                    # Fetch basic info to check industry
                    # We accept "Aerospace & Defense" as industry
                    info = service.get_company_info(ticker)
                    if info:
                        industry = info.get("industry", "")
                        if "Defense" in industry or "Aerospace" in industry:
                            is_contractor = True
                            print(f"    Found Govt Contractor: {ticker} ({industry})")
                
                if not is_contractor:
                    # Skip non-defense
                    continue

                # 2. Fetch Backlog Data
                print(f"    Fetching Backlog for {ticker}...")
                backlog_data = service.get_govt_backlog(ticker)
                
                if backlog_data:
                    govt_contractors.append(backlog_data)
                    # Rate limit slightly for USAspending
                    time.sleep(1)

            except Exception as e:
                print(f"    Error processing {ticker}: {e}")
                time.sleep(1)

        print(f"  Completed {category}. Found {len(govt_contractors)} contractors.")

        # Sort by Ratio? Or total Orders?
        # User approach: "Same as leaderboard". Leaderboard sorts by Score.
        # Here, "Ratio > 1.0" is the buy signal. Sort by Ratio descending.
        govt_contractors.sort(key=lambda x: x["book_to_bill_ratio"], reverse=True)
        
        # Save to MongoDB
        print(f"Saving {len(govt_contractors)} records to MongoDB ({doc_id})...")
        try:
            result = collection.update_one(
                {"_id": doc_id},
                {
                    "$set": {
                        "companies": govt_contractors,
                        "last_updated": datetime.utcnow()
                    }
                },
                upsert=True
            )
            print(f"Saved. Modified: {result.modified_count}, Upserted: {result.upserted_id}")
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")

    print("\nGovt Contracts generation complete.")

if __name__ == "__main__":
    generate_govt_contract_data()
