from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ai import AIService
from app.services.sec import SECService
from app.services.finance import FinanceService

router = APIRouter()
ai_service = AIService()
sec_service = SECService()
finance_service = FinanceService()

class AnalyzeRequest(BaseModel):
    ticker: str
    url: str

class NewsAnalysisRequest(BaseModel):
    ticker: str
    news: list

class ChartAnalysisRequest(BaseModel):
    ticker: str
    period: str
    interval: str
    chart_image: str | None = None  # base64 PNG of the rendered chart, optionally a data: URL

@router.post("/analyze_filing")
def analyze_filing(request: AnalyzeRequest):
    # 1. Fetch text
    text = sec_service.get_filing_text(request.url)
    if not text:
        raise HTTPException(status_code=400, detail="Failed to fetch filing text")
    
    # 2. Summarize
    # Limit text to 30k chars for basic context window safety
    truncated_text = text[:30000]
    
    summary = ai_service.summarize_filing(truncated_text, request.ticker)
    return {"summary": summary}

@router.post("/analyze_news")
async def analyze_news(request: NewsAnalysisRequest):
    analysis = ai_service.analyze_news_sentiment(request.news, request.ticker)
    return {"analysis": analysis}

@router.post("/analyze_chart")
def analyze_chart(request: ChartAnalysisRequest):
    # def, not async def: get_stock_history() calls yfinance, which blocks -
    # this handler was previously async def with the same blocking call
    # inside it, a pre-existing instance of the bug CLAUDE.md's backend
    # conventions warn against; fixed here since this function is already
    # being rewritten for the image-based analysis below.
    data = finance_service.get_stock_history(request.ticker, request.period, request.interval)
    if not data:
        raise HTTPException(status_code=404, detail="Could not fetch market data for analysis")

    image_b64 = request.chart_image
    if image_b64 and image_b64.startswith("data:"):
        # Strip a data: URL prefix (e.g. "data:image/png;base64,") if the
        # caller sent one instead of raw base64 - Gemini's inline_data wants
        # just the base64 payload.
        image_b64 = image_b64.split(",", 1)[-1]

    analysis = ai_service.analyze_chart_data(request.ticker, request.period, request.interval, data, image_b64=image_b64)
    return {"analysis": analysis}

class ValuationRequest(BaseModel):
    ticker: str

@router.post("/analyze_valuation")
async def analyze_valuation(request: ValuationRequest):
    # 1. Fetch Company Info (Metrics)
    info = finance_service.get_company_info(request.ticker)
    if not info:
        raise HTTPException(status_code=404, detail="Company info not found")

    # 2. Fetch Income Statements (Context)
    # get_financials returns a list of statements (annual? quarterly?) 
    # Usually get_financials returns annual. We want quarterly.
    # We might need to call get_quarterly_financials directly if exposed, or check get_financials impl.
    # FinanceService has get_quarterly_financials but it returns a DataFrame usually.
    # Let's check FinanceService.get_quarterly_financials return type. 
    # It returns a list of records in `get_financials`.
    # Let's inspect `get_financials`.
    
    # We will use finance_service.get_quarterly_financials(ticker) logic.
    # Actually `get_financials(ticker)` in api calls `finance_service.get_financials` which returns `[{"date":..., "revenue":...}, ...]`
    # Let's see if we can get quarterly.
    # The current `get_financials` seems to do annual. 
    # We previously saw `recent_qf` (quarterly financials) in the debug output log, so the service HAS it.
    
    # Let's try to fetch quarterly financials. If not exposed, we'll just use what `get_financials` provides (which might be mixed or annual). 
    # Ideally we want quarterly. The `FinanceService` likely has a method.
    
    # For now, let's fetch `finance_service.get_financials(ticker)` and pass it.
    # If the user specifically said "last 4 quarterly", we should try to ensure we get quarterly.
    financials = finance_service.get_quarterly_financials(request.ticker)
    
    analysis = ai_service.analyze_valuation(request.ticker, info, financials)
    return {"analysis": analysis}

class RiskRequest(BaseModel):
    ticker: str

@router.post("/analyze_risk")
async def analyze_risk(request: RiskRequest):
    # 1. Fetch Company Info (Metrics)
    info = finance_service.get_company_info(request.ticker)
    if not info:
        raise HTTPException(status_code=404, detail="Company info not found")

    # 2. Fetch Financials (Last 4 quarters)
    financials = finance_service.get_quarterly_financials(request.ticker)
    
    # 3. Fetch Ownership (Insider Activity)
    ownership = finance_service.get_ownership_details(request.ticker)

    # 4. Analyze
    analysis = ai_service.analyze_risk(request.ticker, info, financials, ownership)
    return {"analysis": analysis}

class MacroAnalysisRequest(BaseModel):
    macro_data: list
    sector_data: list

@router.post("/analyze_macro_market")
async def analyze_macro_market(request: MacroAnalysisRequest):
    analysis = ai_service.analyze_macro_market(request.macro_data, request.sector_data)
    return {"analysis": analysis}

class EtfAnalysisRequest(BaseModel):
    ticker: str

@router.post("/analyze_etf")
async def analyze_etf(request: EtfAnalysisRequest):
    # 1. Fetch ETF Details
    data = finance_service.get_etf_details(request.ticker)
    if not data:
        raise HTTPException(status_code=404, detail="ETF data not found")
    
    # 2. Analyze
    analysis = ai_service.analyze_etf_quality(request.ticker, data)
    return {"analysis": analysis}
