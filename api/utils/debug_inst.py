
import yfinance as yf
import pandas as pd

def debug_inst_holders(ticker="AAPL"):
    print(f"Fetching institutional holders for {ticker}...")
    stock = yf.Ticker(ticker)
    
    try:
        inst_df = stock.institutional_holders
        if inst_df is not None and not inst_df.empty:
            print("\nColumns:", inst_df.columns.tolist())
            print("\nFirst 2 Rows:")
            print(inst_df.head(2))
        else:
            print("No institutional holders found.")
            
    except Exception as e:
        print(f"Error fetching institutions: {e}")

if __name__ == "__main__":
    debug_inst_holders()
