import requests
import os
from datetime import datetime
import pandas as pd
import json

class CongressService:
    def __init__(self):
        self.api_key = os.environ.get("FMP_API_KEY")
        self.base_url = "https://financialmodelingprep.com/api/v4"
    
    def get_recent_trades(self, limit=100):
        trades = []
        errors = []

        # Fetch Data from FMP Stable Endpoints
        try:
            senate_url = f"https://financialmodelingprep.com/stable/senate-latest?apikey={self.api_key}"
            house_url = f"https://financialmodelingprep.com/stable/house-latest?apikey={self.api_key}"
            
            senate_res = requests.get(senate_url)
            house_res = requests.get(house_url)
            
            # Process Senate
            if senate_res.status_code == 200:
                data = senate_res.json()
                for item in data:
                    trades.append({
                        "chamber": "Senate",
                        "representative": item.get("senator", item.get("representative", "Unknown")),
                        "transaction_date": item.get("transactionDate"),
                        "disclosure_date": item.get("disclosureDate"),
                        "ticker": item.get("symbol"),
                        "asset_description": item.get("assetDescription"),
                        "type": item.get("type"), 
                        "amount": item.get("amount"),
                        "party": item.get("party", "N/A"),
                        "link": item.get("link")
                    })
            else:
                 print(f"FMP Senate fetch failed: {senate_res.status_code}")

            # Process House
            if house_res.status_code == 200:
                data = house_res.json()
                for item in data:
                    trades.append({
                        "chamber": "House",
                        "representative": item.get("representative", item.get("senator", "Unknown")),
                        "transaction_date": item.get("transactionDate"),
                        "disclosure_date": item.get("disclosureDate"),
                        "ticker": item.get("symbol"),
                        "asset_description": item.get("assetDescription"),
                        "type": item.get("type"), 
                        "amount": item.get("amount"),
                        "party": item.get("party", "N/A"),
                        "link": item.get("link")
                    })
            else:
                 print(f"FMP House fetch failed: {house_res.status_code}")

        except Exception as e:
            print(f"FMP error: {e}")
            return {"error": str(e)}

        if not trades:
            return {"trades": []}

        df = pd.DataFrame(trades)
        
        # Standardize and Sort
        try:
            # Parse dates to ensure sorting works
            # Different sources might have different formats. 
            # Senate JSON: 'YYYY-MM-DD' usually. FMP: 'YYYY-MM-DD'.
            # We'll just string sort for now or coerce if needed.
            df = df.dropna(subset=['disclosure_date'])
            df.sort_values(by="disclosure_date", ascending=False, inplace=True)
        except Exception as e:
            print(f"Sorting error: {e}")

        df = df.head(limit)
        return {
            "trades": df.to_dict(orient="records"),
            "status": "partial" if errors else "ok"
        }
