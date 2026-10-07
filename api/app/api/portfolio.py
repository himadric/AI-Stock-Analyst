from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.portfolio_service import PortfolioService

router = APIRouter()
portfolio_service = PortfolioService()


class AddPositionRequest(BaseModel):
    ticker: str
    shares: float
    cost_basis: float


# def, not async def: PortfolioService calls yfinance, which blocks - see
# CLAUDE.md "Backend" conventions. watchlist.py's async handlers calling
# yfinance directly are a known, pre-existing bug (see ARCHITECTURE.md's
# known-issues table), not a pattern to copy here.
@router.get("")
def get_portfolio():
    return portfolio_service.get_portfolio()


@router.post("")
def add_position(request: AddPositionRequest):
    try:
        return portfolio_service.add_position(request.ticker, request.shares, request.cost_basis)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{ticker}/sell")
def sell_position(ticker: str):
    try:
        return portfolio_service.sell_position(ticker)
    except ValueError as e:
        status_code = 404 if "No open position" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e))


@router.delete("/{position_id}")
def delete_position(position_id: str):
    try:
        portfolio_service.delete_position(position_id)
    except ValueError as e:
        status_code = 404 if "not found" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    return {"message": "Position removed"}
