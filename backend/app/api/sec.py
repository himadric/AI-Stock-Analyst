from fastapi import APIRouter, HTTPException, Query
from app.services.sec import SECService

router = APIRouter()
sec_service = SECService()

@router.get("/filings/{ticker}")
def get_sec_filings(ticker: str):
    data = sec_service.get_filings(ticker)
    if isinstance(data, dict) and "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data

@router.get("/search")
def search_tickers(query: str = Query(..., min_length=1)):
    return sec_service.search_tickers(query)
