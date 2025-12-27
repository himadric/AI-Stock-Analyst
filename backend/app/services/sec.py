import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

class SECService:
    def __init__(self):
        # User-Agent is REQUIRED by SEC.gov
        self.headers = {
            "User-Agent": "AIAnalyst/1.0 (himadric@gmail.com)"
        }
        self.ticker_cik_map = {} 
        # Cache for search list: [{"ticker": "AAPL", "title": "Apple Inc."}, ...]
        self.search_cache = []
        self._load_ticker_map()

    def _load_ticker_map(self):
        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                for item in data.values():
                    self.ticker_cik_map[item['ticker']] = item['cik_str']
                    self.search_cache.append({
                        "ticker": item['ticker'],
                        "title": item['title']
                    })
        except Exception as e:
            print(f"Error loading ticker map: {e}")

    def get_cik(self, ticker: str):
        return self.ticker_cik_map.get(ticker.upper())
    
    def search_tickers(self, query: str):
        query = query.upper()
        # Simple contains search
        results = [
            item for item in self.search_cache 
            if query in item['ticker'] or query in item['title'].upper()
        ]
        return results[:10] # Limit to 10 results

    def get_filing_text(self, url: str):
        """
        Fetches the text content of a filing URL.
        """
        try:
            # SEC requires the user agent even for archives
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Naive text extraction
                text = soup.get_text(separator=' ', strip=True)
                return text
            return ""
        except Exception as e:
            print(f"Error fetching text: {e}")
            return ""

    def get_filings(self, ticker: str, form_types=["10-K", "10-Q", "20-F", "6-K"]):
        cik = self.get_cik(ticker)
        if not cik:
            return {"error": "Ticker not found"}

        cik_padded = str(cik).zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return {"error": f"Failed to fetch data from SEC: {response.status_code}"}
            
            data = response.json()
            filings = data.get("filings", {}).get("recent", {})
            
            result = []
            if filings:
                for i in range(len(filings['accessionNumber'])):
                    form = filings['form'][i]
                    if form in form_types:
                        accession_number = filings['accessionNumber'][i]
                        primary_doc = filings['primaryDocument'][i]
                        accession_no_dashes = accession_number.replace("-", "")
                        link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primary_doc}"
                        
                        result.append({
                            "accessionNumber": accession_number,
                            "filingDate": filings['filingDate'][i],
                            "reportDate": filings['reportDate'][i],
                            "form": form,
                            "size": filings['size'][i],
                            "isXBRL": filings['isXBRL'][i],
                            "link": link
                        })
                result.sort(key=lambda x: x['filingDate'], reverse=True)
                return result[:4]
            return []
            
        except Exception as e:
            print(f"Error fetching filings: {e}")
            return []
