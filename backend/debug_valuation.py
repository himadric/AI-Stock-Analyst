from app.services.finance import FinanceService
from app.services.ai import AIService
import asyncio

async def debug_valuation():
    print("Initializing services...")
    finance = FinanceService()
    ai = AIService()
    ticker = "UBER"

    print(f"Fetching info for {ticker}...")
    info = finance.get_company_info(ticker)
    print("Info keys:", info.keys())

    print(f"Fetching financials for {ticker}...")
    try:
        # mimicking api/ai.py line: financials = finance_service.get_quarterly_financials(request.ticker)
        financials = finance.get_quarterly_financials(ticker)
        print(f"Financials type: {type(financials)}")
        if isinstance(financials, list):
            print(f"Financials len: {len(financials)}")
            if len(financials) > 0:
                print(f"First item type: {type(financials[0])}")
        else:
            print("Financials is not a list!")
    except AttributeError:
        print("ERROR: FinanceService has no attribute 'get_financials'")
        return

    print("Calling analyze_valuation...")
    try:
        result = ai.analyze_valuation(ticker, info, financials)
        print("Result length:", len(result))
        print("First 100 chars:", result[:100])
    except Exception as e:
        print(f"ERROR in analyze_valuation: {e}")

if __name__ == "__main__":
    asyncio.run(debug_valuation())
