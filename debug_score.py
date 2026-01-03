import sys
import os

# Add api/ directory to python path
sys.path.append(os.path.join(os.getcwd(), 'api'))

from app.services.finance import FinanceService

try:
    print("Initializing FinanceService...")
    import yfinance as yf
    stock = yf.Ticker("AAPL")
    
    print("\n--- INFO KEYS (PEG Check) ---")
    info = stock.info
    print(f"pegRatio in info: {'pegRatio' in info}")
    print(f"PEG value: {info.get('pegRatio')}")
    # Print generic match for 'peg'
    peg_keys = [k for k in info.keys() if 'peg' in k.lower()]
    print(f"Keys matching 'peg': {peg_keys}")

    print("\n--- FINANCIALS INDEX (Scalability Check) ---")
    fin = stock.financials
    print(fin.index.tolist())
    
    # Check specific rows
    print(f"Has 'Total Revenue': {'Total Revenue' in fin.index}")
    print(f"Has 'Total Operating Expenses': {'Total Operating Expenses' in fin.index}")
    if 'Total Operating Expenses' not in fin.index:
        # fuzzy match
        opex_keys = [k for k in fin.index if 'Operat' in str(k)]
        print(f"Potential Opex keys: {opex_keys}")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
