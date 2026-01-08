from fastapi import APIRouter, HTTPException
from pymongo import MongoClient
import os
from typing import List, Dict, Any

router = APIRouter()

def get_db():
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    client = MongoClient(uri)
    return client["ai_stock_analyst"]

@router.get("/trades")
async def get_senate_trades():
    """
    Returns US Senate trades from the automated tracker (stored in MongoDB).
    """
    try:
        db = get_db()
        collection = db["senate_tracker"]
        doc = collection.find_one({"type": "recent_trades"})
        
        if not doc:
            # Fallback (e.g. if script hasn't run yet)
            return {"trades": [], "status": "no_data"}
            
        trades = doc.get("data", [])
        
        return {"trades": trades, "updated_at": doc.get("updated_at")}
        
    except Exception as e:
        print(f"Error fetching senate trades: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
