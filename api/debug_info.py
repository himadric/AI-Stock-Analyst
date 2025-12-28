import yfinance as yf
import json

def check_keys(ticker_symbol):
    print(f"--- Info Keys for {ticker_symbol} ---")
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    
    keys_to_check = [
        "forwardPE",
        "pegRatio",
        "priceToSalesTrailing12Months",
        "profitMargins",
        "returnOnEquity",
        "freeCashflow",
        "debtToEquity",
        "currentRatio",
        "industry",
        "sector",
        "trailingPE"
    ]
    
    result = {k: info.get(k, "MISSING") for k in keys_to_check}
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    check_keys("AAPL")
