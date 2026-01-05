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

@router.get("/peers/{ticker}")
def get_peer_comparison(ticker: str):
    data = finance_service.get_peer_comparison(ticker)
    # Return empty list is fine if no peers found
    return data

@router.get("/market-map")
def get_market_map(map_type: str = "sector"):
    if map_type == "factor":
        return finance_service.get_factor_allocations()
    return finance_service.get_sector_allocations()

@router.get("/historical-metrics/{ticker}")
def get_historical_metrics(ticker: str):
    return finance_service.get_historical_metrics(ticker)

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

@router.get("/sectors")
def get_sector_data():
    return finance_service.get_sector_performance()

@router.get("/history/{ticker}")
def get_stock_history(
    ticker: str, 
    period: str = Query("1y", description="Time period (1d, 5d, 1mo, 1y, etc)"),
    interval: str = Query("1d", description="Data interval (1m, 5m, 1h, 1d, 1wk, 1mo)")
):
    data = finance_service.get_stock_history(ticker, period, interval)
    if not data:
        return []
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

@router.get("/score/{ticker}")
def get_future_leader_score(ticker: str):
    data = finance_service.get_future_leader_score(ticker)
    if not data:
        # Return partial/empty structure or let frontend handle null
        return None
    return data

@router.get("/rankings")
def get_rankings(
    category: str = "Small Cap",
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
):
    return finance_service.get_rankings(category, page, limit)

@router.get("/govt/backlog/{ticker}")
def get_govt_backlog(ticker: str):
    data = finance_service.get_govt_backlog(ticker)
    if not data:
        raise HTTPException(status_code=404, detail="Company or Government Data not found")
    return data

@router.get("/govt/rankings")
@router.get("/govt/rankings")
def get_govt_rankings():
    return finance_service.get_govt_rankings()
