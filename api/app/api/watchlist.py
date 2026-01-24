from fastapi import APIRouter, HTTPException, Body
from app.db import db
from pydantic import BaseModel
import yfinance as yf
from typing import List

router = APIRouter()

class WatchlistItem(BaseModel):
    ticker: str

@router.get("")
async def get_watchlist():
    database = db.get_db()
    cursor = database.watchlist.find({})
    watchlist_items = list(cursor)
    
    if not watchlist_items:
        return []

    data = []
    
    for item in watchlist_items:
        t = item['ticker']
        # Use stored name if available, otherwise fallback to ticker
        name = item.get('name', t)
        
        try:
            ticker_obj = yf.Ticker(t)
            # fast_info provides quick access to price data without full info request
            price = ticker_obj.fast_info.last_price
            prev_close = ticker_obj.fast_info.previous_close
            
            change = 0.0
            change_percent = 0.0
            
            if price is not None and prev_close is not None and prev_close != 0:
                change = price - prev_close
                change_percent = (change / prev_close) * 100
            
            data.append({
                "ticker": t,
                "name": name,
                "price": price if price is not None else 0.0,
                "change": change,
                "change_percent": change_percent
            })
        except Exception as e:
            print(f"Error fetching data for {t}: {e}")
            data.append({
                "ticker": t,
                "name": name,
                "price": 0.0,
                "change": 0.0,
                "change_percent": 0.0
            })
            
    return data

@router.post("")
async def add_to_watchlist(item: WatchlistItem):
    database = db.get_db()
    ticker = item.ticker.upper().strip()
    
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker cannot be empty")
    
    # Check if exists
    if database.watchlist.find_one({"ticker": ticker}):
        # Return success even if exists, or message
        return {"message": "Ticker already in watchlist"}
    
    # Fetch name using yfinance to store it
    name = ticker
    try:
        ticker_obj = yf.Ticker(ticker)
        # Ideally we want the name. info call can be slow but it's only once per add.
        # fast_info doesn't have name.
        info = ticker_obj.info
        name = info.get('shortName') or info.get('longName') or ticker
    except Exception as e:
        print(f"Could not fetch name for {ticker}: {e}")
        # Proceed with just ticker as name if fetch fails
        
    database.watchlist.insert_one({"ticker": ticker, "name": name})
    return {"message": "Ticker added", "name": name}

@router.delete("/{ticker}")
async def remove_from_watchlist(ticker: str):
    database = db.get_db()
    result = database.watchlist.delete_one({"ticker": ticker.upper()})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return {"message": "Ticker removed"}
