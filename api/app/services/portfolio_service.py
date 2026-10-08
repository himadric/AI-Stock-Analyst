"""
Demo portfolio - not a real brokerage link. Pulled out as a real service
(rather than living directly in the router, the way watchlist.py's logic
does) specifically because agent/multi_agent.py needs the same add/sell
logic the router uses, for auto-executed trade proposals under
AUTO_EXECUTE_THRESHOLD. Importing api/portfolio.py directly from
multi_agent.py creates a circular import (app/api/__init__.py pulls in
agent.py, which pulls in multi_agent.py) - routers are meant to be a thin
layer callers go THROUGH, not one they import FROM. This is the service
layer both the router and the agent sit on top of instead.

Raises plain ValueError on business-rule failures (not HTTPException -
that's a router-layer concern); callers translate as appropriate.
"""
from datetime import datetime, timezone

from app.db import db
from app.services.finance import FinanceService


class PortfolioService:
    def __init__(self):
        self.finance_service = FinanceService()

    def _serialize(self, doc: dict) -> dict:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return doc

    def get_open_position(self, ticker: str) -> dict | None:
        position = db.get_db().portfolio.find_one({"ticker": ticker.upper(), "status": "open"})
        return self._serialize(position) if position else None

    def get_portfolio(self) -> dict:
        database = db.get_db()
        positions = list(database.portfolio.find({}))
        open_positions = [p for p in positions if p.get("status") == "open"]
        closed_positions = [p for p in positions if p.get("status") == "closed"]

        quotes_by_ticker = {}
        if open_positions:
            tickers = [p["ticker"] for p in open_positions]
            quotes_by_ticker = {q["ticker"]: q for q in self.finance_service.get_quotes(tickers)}

        open_out = []
        for p in open_positions:
            p = self._serialize(p)
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
            p = self._serialize(p)
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

    def add_position(self, ticker: str, shares: float, cost_basis: float) -> dict:
        ticker = ticker.upper().strip()
        if not ticker:
            raise ValueError("Ticker cannot be empty")
        if shares <= 0:
            raise ValueError("Shares must be positive")

        database = db.get_db()
        # At most one open position per ticker at a time - keeps the
        # ticker-keyed sell flow below unambiguous (which position to
        # close). A real brokerage tracks multiple lots; this is a demo
        # portfolio, not that.
        if database.portfolio.find_one({"ticker": ticker, "status": "open"}):
            raise ValueError(f"Already have an open position in {ticker}")

        doc = {
            "ticker": ticker,
            "shares": shares,
            "cost_basis": cost_basis,
            "purchase_date": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "sell_price": None,
            "sell_date": None,
        }
        result = database.portfolio.insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._serialize(doc)

    def sell_position(self, ticker: str) -> dict:
        """Always sells at today's live price - fetched here, not passed in,
        so every caller (the manual Sell button, an auto-executed trade
        proposal, a gated one a human confirmed) gets the same real price
        at the moment the sale actually happens."""
        ticker = ticker.upper().strip()
        database = db.get_db()
        position = database.portfolio.find_one({"ticker": ticker, "status": "open"})
        if not position:
            raise ValueError(f"No open position in {ticker}")

        quotes = self.finance_service.get_quotes([ticker])
        if not quotes:
            raise ValueError(f"Could not fetch a current price for {ticker}")
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
        return self._serialize(position)

    def delete_position(self, position_id: str) -> None:
        from bson import ObjectId
        from bson.errors import InvalidId

        database = db.get_db()
        try:
            oid = ObjectId(position_id)
        except InvalidId:
            raise ValueError("Invalid position id")

        result = database.portfolio.delete_one({"_id": oid})
        if result.deleted_count == 0:
            raise ValueError("Position not found")
