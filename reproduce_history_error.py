import yfinance as yf
import pandas as pd
from datetime import datetime
import json
import numpy as np

def get_stock_history(ticker: str, period: str = "1y", interval: str = "1d"):
    print(f"Fetching history for {ticker}, period={period}, interval={interval}")
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        
        hist.reset_index(inplace=True)
        
        data = []
        for index, row in hist.iterrows():
            date_val = row.get("Datetime") or row.get("Date")
            
            date_str = ""
            if pd.notnull(date_val):
                 if isinstance(date_val, (pd.Timestamp, datetime)):
                     date_str = date_val.isoformat()
                 else:
                     date_str = str(date_val)

            record = {
                "date": date_str,
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": row["Volume"]
            }
            
            # Check for NaNs which break JSON serialization
            for k, v in record.items():
                if isinstance(v, float) and np.isnan(v):
                    print(f"WARNING: Found NaN in {k} at index {index}")
            
            data.append(record)
            
        # Try to serialize to JSON to see if it fails
        try:
            json.dumps(data)
            print("Serialization successful")
        except Exception as e:
            print(f"Serialization FAILED: {e}")
            
        return data
    except Exception as e:
        print(f"Error fetching stock history for {ticker}: {e}")
        return []

# Test with a few tickers, including potentially problematic ones
# The user might be viewing a specific ticker, likely 'AAPL' or from the rankings.
# I'll test AAPL and maybe a small cap one.
print("Testing AAPL...")
get_stock_history("AAPL")
print("\nTesting PLTR...")
get_stock_history("PLTR")
