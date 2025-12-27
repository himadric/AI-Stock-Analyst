import yfinance as yf
import json

def debug_uber():
    ticker = yf.Ticker("UBER")
    info = ticker.info
    
    print("--- UBER Data Debug ---")
    keys = ["pegRatio", "trailingPE", "forwardPE", "earningsGrowth"]
    for k in keys:
        print(f"{k}: {info.get(k)}")
    
    # Test Calc
    f_pe = info.get("forwardPE")
    growth = info.get("earningsGrowth")
    if f_pe and growth:
        print(f"Calculated PEG: {f_pe / (growth * 100)}")

if __name__ == "__main__":
    debug_uber()
