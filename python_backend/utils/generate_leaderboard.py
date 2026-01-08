import sys
import os
import json
import random
import time
from datetime import datetime

# Add api directory to path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.finance import FinanceService
from app.db import db

DATA_DIR = os.path.join(os.path.dirname(__file__), "../app/data")
INDICES_FILE = os.path.join(DATA_DIR, "sp_indices.json")

def generate_leaderboard():
    print("Starting leaderboard generation (MongoDB Version)...")
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
    collection = mongo_db["leaderboard"]

    for category, tickers in indices.items():
        doc_id = cat_map.get(category)
        if not doc_id:
            print(f"Skipping unknown category: {category}")
            continue

        print(f"\nProcessing {category} -> {doc_id} ({len(tickers)} tickers)...")
        
        candidates = tickers
        # candidates = tickers[:5] # DEBUG: Remove for prod
        print(f"Processing full list: {len(candidates)} candidates.")
        
        ranked_companies = []
        
        total = len(candidates)
        for i, ticker in enumerate(candidates):
            try:
                # Progress indicator
                print(f"  [{i+1}/{total}] Scoring {ticker}...", end="", flush=True)
                
                score_data = service.get_future_leader_score(ticker)
                
                if score_data:
                    score = score_data['total_score']
                    print(f" Score: {score:.1f}", end="")
                    
                    if score >= 5:
                        print(" [Added]")
                        ranked_companies.append({
                            "ticker": ticker,
                            "rank": 0, 
                            "total_score": score,
                            "factors": score_data["factors"]
                        })
                    else:
                        print(" [Skipped < 5]")
                else:
                    print(" No data")
                
                # Rate limit delay as requested
                time.sleep(0.1)
                
            except Exception as e:
                print(f" Error: {e}")
                time.sleep(1) # Longer pause on error

        print(f"  Completed {category}. Found data for {len(ranked_companies)}/{len(candidates)} companies.")

        # Sort by score descending
        ranked_companies.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Assign ranks
        for i, company in enumerate(ranked_companies):
            company["rank"] = i + 1
            
        # Save to MongoDB
        print(f"Saving {len(ranked_companies)} records to MongoDB ({doc_id})...")
        try:
            result = collection.update_one(
                {"_id": doc_id},
                {
                    "$set": {
                        "companies": ranked_companies,
                        "last_updated": datetime.utcnow()
                    }
                },
                upsert=True
            )
            print(f"Saved. Modified: {result.modified_count}, Upserted: {result.upserted_id}")
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")

    print("\nLeaderboard generation complete.")

if __name__ == "__main__":
    generate_leaderboard()
