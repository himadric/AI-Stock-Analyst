from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import os
from typing import List, Dict, Any

router = APIRouter()

# MongoDB connection (reusing the one from main app usually, but for simplicity creating new client or using dependency if available)
# In this codebase, services usually manage their own or we use a global db.
# I'll create a simple helper/client here to match logic in institution_service, 
# or better yet, inject it. But for speed and matching the script logic:

def get_db():
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    client = MongoClient(uri)
    return client["ai_stock_analyst"]

@router.get("/trades")
async def get_house_trades():
    """
    Returns US House trades from the automated tracker (stored in MongoDB).
    """
    try:
        db = get_db()
        collection = db["house_tracker"]
        doc = collection.find_one({"type": "recent_trades"})
        
        if not doc:
            # Fallback (e.g. if script hasn't run yet)
            return {"trades": [], "status": "no_data"}
            
        # Helper to convert ObjectId to str if needed, though 'data' is usually clean dicts
        trades = doc.get("data", [])
        
        # Ensure dates are compatible? Usually JSON response is fine.
        return {"trades": trades, "updated_at": doc.get("updated_at")}
        
    except Exception as e:
        print(f"Error fetching house trades: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
