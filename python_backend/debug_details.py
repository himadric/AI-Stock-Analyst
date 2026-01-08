import yfinance as yf
import pandas as pd

def test_analyst_details(ticker_symbol):
    print(f"--- Fetching Analyst Details for {ticker_symbol} ---")
    ticker = yf.Ticker(ticker_symbol)
    
    try:
        # Check upgrades_downgrades
        upgrades = ticker.upgrades_downgrades
        print("\n[Upgrades/Downgrades Data Head]:")
        if upgrades is not None and not upgrades.empty:
            print(upgrades.head())
            print(upgrades.columns)
        else:
            print("No upgrades/downgrades data found.")
            
    except Exception as e:
        print(f"Error fetching upgrades: {e}")

if __name__ == "__main__":
    test_analyst_details("UBER")
