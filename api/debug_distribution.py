import yfinance as yf
import pandas as pd

def test_ownership_data(ticker_symbol):
    print(f"--- Fetching Ownership Data for {ticker_symbol} ---")
    ticker = yf.Ticker(ticker_symbol)
    
    try:
        # 1. Major Holders
        major = ticker.major_holders
        print("\n[Major Holders]:")
        if major is not None:
            print(major)
        else:
            print("No major holders data.")

        # 2. Institutional Holders
        inst = ticker.institutional_holders
        print("\n[Institutional Holders Head]:")
        if inst is not None and not inst.empty:
            print(inst.head())
        else:
            print("No institutional holders data.")
            
        # 3. Mutual Fund Holders
        mf = ticker.mutualfund_holders
        print("\n[Mutual Fund Holders Head]:")
        if mf is not None and not mf.empty:
            print(mf.head())
        else:
            print("No mutual fund holders data.")

    except Exception as e:
        print(f"Error fetching ownership: {e}")

if __name__ == "__main__":
    test_ownership_data("UBER")
    test_ownership_data("AAPL")
