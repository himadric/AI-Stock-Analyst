import yfinance as yf
import pandas as pd
import json

try:
    ticker = "AAPL"
    stock = yf.Ticker(ticker)
    # helper to check for ratios/valuation
    print("--- Valuation / Ratios ---")
    try:
        # Some versions have .valuation_measures or similar
        # checking standard info first
        info_keys = [k for k in stock.info.keys() if 'ratio' in k.lower() or 'margin' in k.lower()]
        print("Info Keys (Current Ratios):", info_keys)

        # accessing getting specific historical strings if possible?
        # Usually requires manual calculation, but let's check if 'valuation_measures' exists (sometimes available)
        # It's not a standard yf property in recent versions but worth a try or checking alternatives
        pass
    except Exception as e:
        print(f"Error checking ratios: {e}")

except Exception as e:
    print(f"Error: {e}")
