import yfinance as yf
import pandas as pd

def test_detailed_holders(ticker_symbol):
    print(f"--- Fetching Detailed Holders for {ticker_symbol} ---")
    ticker = yf.Ticker(ticker_symbol)
    
    try:
        # 1. Institutional Holders
        print("\n[Institutional Holders]:")
        inst = ticker.institutional_holders
        if inst is not None and not inst.empty:
            print(inst.head())
            print(inst.columns)
        else:
            print("No institutional holders.")

        # 2. Mutual Fund Holders
        print("\n[Mutual Fund Holders]:")
        mf = ticker.mutualfund_holders
        if mf is not None and not mf.empty:
            print(mf.head())
            print(mf.columns)
        else:
            print("No mutual fund holders.")

        # 3. Insider Roster / Holders (Checking available attributes)
        # Note: yfinance has 'insider_purchases', 'insider_transactions', 'major_holders'
        # Let's check 'insiders' if it exists or 'major_holders' again.
        
        print("\n[Insider Transactions (proxy for names?)]: dict check")
        # There isn't a direct 'insider_holders' list usually, but let's check 'insider_roster_holders' if valid in this version
        # Or just 'insider_purchases'
        
        # Checking for 'insider_roster_holders' specifically
        try:
            print("\n[Insider Roster Holders?]:")
            # This is available in some versions
            roster = ticker.insider_roster_holders
            if roster is not None and not roster.empty:
                print(roster.head())
            else:
                 print("No insider roster found.")
        except Exception as e:
            print(f"insider_roster_holders not available: {e}")

    except Exception as e:
        print(f"Error fetching holders: {e}")

if __name__ == "__main__":
    test_detailed_holders("UBER")
