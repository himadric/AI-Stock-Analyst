from fastapi import APIRouter, HTTPException, Query
from app.services.finance import FinanceService

router = APIRouter()
finance_service = FinanceService()

@router.get("/info/{ticker}")
def get_company_info(ticker: str):
    data = finance_service.get_company_info(ticker)
    if not data:
        raise HTTPException(status_code=404, detail="Company not found")
    return data

@router.get("/quotes")
def get_quotes(symbols: str):
    # symbols is a comma separated string "AAPL,MSFT,GOOG"
    ticker_list = symbols.split(",")
    data = finance_service.get_quotes(ticker_list)
    if not data:
        return []
    return data

@router.get("/macro")
def get_macro_data():
    return finance_service.get_macro_indicators()

@router.get("/history/{ticker}")
def get_stock_history(
    ticker: str, 
    period: str = Query("1y", description="Time period (1d, 5d, 1mo, 1y, etc)"),
    interval: str = Query("1d", description="Data interval (1m, 5m, 1h, 1d, 1wk, 1mo)")
):
    data = finance_service.get_stock_history(ticker, period, interval)
    if not data:
        raise HTTPException(status_code=404, detail="Data not found")
    return data

@router.get("/news/{ticker}")
def get_company_news(ticker: str):
    return finance_service.get_company_news(ticker)

@router.get("/financials/{ticker}")
def get_quarterly_financials(ticker: str):
    data = finance_service.get_quarterly_financials(ticker)
    if not data:
        # Return empty list instead of 404 so frontend can handle gracefully
        return [] 
    return data

@router.get("/financials/balance-sheet/{ticker}")
def get_quarterly_balance_sheet(ticker: str):
    data = finance_service.get_quarterly_balance_sheet(ticker)
    if not data:
        return []
    return data

@router.get("/financials/cash-flow/{ticker}")
def get_quarterly_cash_flow(ticker: str):
    data = finance_service.get_quarterly_cash_flow(ticker)
    if not data:
        return []
    return data

@router.get("/financials/ratios/{ticker}")
async def get_ratios(ticker: str):
    return finance_service.get_quarterly_ratios(ticker)

@router.get("/forecast/{ticker}")
async def get_forecast(ticker: str):
    data = finance_service.get_forecast(ticker)
    if not data:
        return []
    return data

@router.get("/forecast/actions/{ticker}")
async def get_analyst_actions(ticker: str):
    return finance_service.get_analyst_actions(ticker)

@router.get("/ownership/{ticker}")
async def get_ownership(ticker: str):
    return finance_service.get_ownership(ticker)

@router.get("/ownership/details/{ticker}")
async def get_ownership_details(ticker: str):
    return finance_service.get_ownership_details(ticker)
