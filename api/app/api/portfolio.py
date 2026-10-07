from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import db
from app.services.finance import FinanceService

router = APIRouter()
finance_service = FinanceService()


class AddPositionRequest(BaseModel):
    ticker: str
    shares: float
    cost_basis: float


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


# def, not async def: get_quotes() calls yfinance, which blocks - see
# CLAUDE.md "Backend" conventions. watchlist.py's async handlers calling
# yfinance directly are a known, pre-existing bug (see ARCHITECTURE.md's
# known-issues table), not a pattern to copy here.
@router.get("")
def get_portfolio():
    database = db.get_db()
    positions = list(database.portfolio.find({}))
    open_positions = [p for p in positions if p.get("status") == "open"]
    closed_positions = [p for p in positions if p.get("status") == "closed"]

    quotes_by_ticker = {}
    if open_positions:
        tickers = [p["ticker"] for p in open_positions]
        quotes_by_ticker = {q["ticker"]: q for q in finance_service.get_quotes(tickers)}

    open_out = []
    for p in open_positions:
        p = _serialize(p)
        quote = quotes_by_ticker.get(p["ticker"])
        current_price = quote["price"] if quote else None
        if current_price is not None:
            market_value = current_price * p["shares"]
            gain_loss = (current_price - p["cost_basis"]) * p["shares"]
            cost_total = p["cost_basis"] * p["shares"]
            gain_loss_percent = (gain_loss / cost_total * 100) if cost_total else 0
        else:
            market_value = gain_loss = gain_loss_percent = None
        open_out.append({
            **p,
            "current_price": current_price,
            "market_value": market_value,
            "gain_loss": gain_loss,
            "gain_loss_percent": gain_loss_percent,
        })

    closed_out = []
    for p in closed_positions:
        p = _serialize(p)
        cost_total = p["cost_basis"] * p["shares"]
        proceeds = (p.get("sell_price") or 0) * p["shares"]
        realized_gain_loss = proceeds - cost_total
        realized_gain_loss_percent = (realized_gain_loss / cost_total * 100) if cost_total else 0
        closed_out.append({
            **p,
            "realized_gain_loss": realized_gain_loss,
            "realized_gain_loss_percent": realized_gain_loss_percent,
        })

    return {"open": open_out, "closed": closed_out}


@router.post("")
def add_position(request: AddPositionRequest):
    ticker = request.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker cannot be empty")
    if request.shares <= 0:
        raise HTTPException(status_code=400, detail="Shares must be positive")

    database = db.get_db()
    # At most one open position per ticker at a time - keeps the ticker-keyed
    # sell flow below unambiguous (which position to close). A real brokerage
    # tracks multiple lots; this is a demo portfolio, not that.
    if database.portfolio.find_one({"ticker": ticker, "status": "open"}):
        raise HTTPException(status_code=400, detail=f"Already have an open position in {ticker}")

    doc = {
        "ticker": ticker,
        "shares": request.shares,
        "cost_basis": request.cost_basis,
        "purchase_date": datetime.now(timezone.utc).isoformat(),
        "status": "open",
        "sell_price": None,
        "sell_date": None,
    }
    result = database.portfolio.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc)


@router.post("/{ticker}/sell")
def sell_position(ticker: str):
    ticker = ticker.upper().strip()
    database = db.get_db()
    position = database.portfolio.find_one({"ticker": ticker, "status": "open"})
    if not position:
        raise HTTPException(status_code=404, detail=f"No open position in {ticker}")

    quotes = finance_service.get_quotes([ticker])
    if not quotes:
        raise HTTPException(status_code=502, detail=f"Could not fetch a current price for {ticker}")
    sell_price = quotes[0]["price"]

    database.portfolio.update_one(
        {"_id": position["_id"]},
        {"$set": {
            "status": "closed",
            "sell_price": sell_price,
            "sell_date": datetime.now(timezone.utc).isoformat(),
        }},
    )
    position = database.portfolio.find_one({"_id": position["_id"]})
    return _serialize(position)


@router.delete("/{position_id}")
def delete_position(position_id: str):
    from bson import ObjectId
    from bson.errors import InvalidId

    database = db.get_db()
    try:
        oid = ObjectId(position_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid position id")

    result = database.portfolio.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"message": "Position removed"}
