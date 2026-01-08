import pandas as pd
import json
import os
import requests
from io import StringIO

DATA_FILE = os.path.join(os.path.dirname(__file__), "../app/data/sp_indices.json")

def fetch_sp_indices():
    indices = {
        "Small Cap": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
        "Mid Cap": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
        "Large Cap": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    }
    
    data = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for category, url in indices.items():
        print(f"Fetching {category} from {url}...")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Wrap in StringIO because read_html expects a file-like object or string
            tables = pd.read_html(StringIO(response.text))
            
            # The tickers are usually in the first table, column "Symbol" or "Ticker symbol"
            df = tables[0]
            
            # Find the symbol column
            symbol_col = None
            for col in df.columns:
                if "Symbol" in str(col) or "Ticker" in str(col):
                    symbol_col = col
                    break
            
            if symbol_col:
                tickers = df[symbol_col].tolist()
                # Clean tickers (replace . with - for yfinance compatibility, e.g. BRK.B -> BRK-B)
                tickers = [str(t).replace(".", "-") for t in tickers]
                data[category] = tickers
                print(f"Found {len(tickers)} tickers for {category}")
            else:
                print(f"Could not find Symbol column for {category}")
        except Exception as e:
            print(f"Error fetching {category}: {e}")
            
    # Save to file
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved tickers to {DATA_FILE}")

if __name__ == "__main__":
    fetch_sp_indices()
