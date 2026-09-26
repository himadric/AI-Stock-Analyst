import os
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

class SECService:
    def __init__(self):
        # User-Agent is REQUIRED by SEC.gov and must include a contact email: "AppName you@example.com"
        user_agent = os.getenv("SEC_USER_AGENT")
        if not user_agent:
            print("Warning: SEC_USER_AGENT not set; SEC.gov may reject requests without a contact email.")
            user_agent = "AIAnalyst/1.0"
        self.headers = {
            "User-Agent": user_agent
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
            
            # Augment with popular ETFs (Vanguard & others) that might be missing or hard to find
            self._load_additional_etfs()
            
        except Exception as e:
            print(f"Error loading ticker map: {e}")
            # Ensure we at least have the manual list if API fails
            self._load_additional_etfs()

    def _load_additional_etfs(self):
        # Common Popular ETFs (Vanguard, SPDR, Invesco)
        etfs = [
            # Vanguard ETFs
            {"ticker": "VOO", "title": "Vanguard S&P 500 ETF"},
            {"ticker": "VTI", "title": "Vanguard Total Stock Market ETF"},
            {"ticker": "VEA", "title": "Vanguard FTSE Developed Markets ETF"},
            {"ticker": "VUG", "title": "Vanguard Growth ETF"},
            {"ticker": "VTV", "title": "Vanguard Value ETF"},
            {"ticker": "BND", "title": "Vanguard Total Bond Market ETF"},
            {"ticker": "VXUS", "title": "Vanguard Total International Stock ETF"},
            {"ticker": "VWO", "title": "Vanguard FTSE Emerging Markets ETF"},
            {"ticker": "VGT", "title": "Vanguard Information Technology ETF"},
            {"ticker": "VIG", "title": "Vanguard Dividend Appreciation ETF"},
            {"ticker": "VO", "title": "Vanguard Mid-Cap ETF"},
            {"ticker": "BNDX", "title": "Vanguard Total International Bond ETF"},
            {"ticker": "VYM", "title": "Vanguard High Dividend Yield ETF"},
            {"ticker": "VB", "title": "Vanguard Small-Cap ETF"},
            {"ticker": "VT", "title": "Vanguard Total World Stock ETF"},
            {"ticker": "VCIT", "title": "Vanguard Intermediate-Term Corporate Bond ETF"},
            {"ticker": "VEU", "title": "Vanguard FTSE All-World ex-US Index Fund"},
            {"ticker": "VV", "title": "Vanguard Large-Cap ETF"},
            {"ticker": "BSV", "title": "Vanguard Short-Term Bond ETF"},
            {"ticker": "VTEB", "title": "Vanguard Tax-Exempt Bond ETF"},
            {"ticker": "VCSH", "title": "Vanguard Short-Term Corporate Bond ETF"},
            {"ticker": "VGIT", "title": "Vanguard Intermediate-Term Treasury ETF"},
            {"ticker": "VONG", "title": "Vanguard Russell 1000 Growth ETF"},
            {"ticker": "VNQ", "title": "Vanguard Real Estate ETF"},
            {"ticker": "VBR", "title": "Vanguard Small Cap Value ETF"},
            {"ticker": "VGK", "title": "Vanguard FTSE Europe ETF"},
            {"ticker": "MGK", "title": "Vanguard Mega Cap Growth ETF"},
            {"ticker": "BIV", "title": "Vanguard Intermediate-Term Bond ETF"},
            {"ticker": "VGSH", "title": "Vanguard Short-Term Treasury ETF"},
            {"ticker": "VXF", "title": "Vanguard Extended Market ETF"},
            {"ticker": "VOOG", "title": "Vanguard S&P 500 Growth ETF"},
            {"ticker": "VOE", "title": "Vanguard Mid-Cap Value ETF"},
            {"ticker": "VBK", "title": "Vanguard Small-Cap Growth ETF"},
            {"ticker": "VOT", "title": "Vanguard Mid-Cap Growth ETF"},
            {"ticker": "VHT", "title": "Vanguard Health Care ETF"},
            {"ticker": "VYMI", "title": "Vanguard International High Dividend Yield ETF"},
            {"ticker": "VTIP", "title": "Vanguard Short-Term Inflation-Protected Securities ETF"},
            {"ticker": "VONV", "title": "Vanguard Russell 1000 Value ETF"},
            {"ticker": "VMBS", "title": "Vanguard Mortgage-Backed Securities ETF"},
            {"ticker": "VTWO", "title": "Vanguard Russell 2000 ETF"},
            {"ticker": "VFH", "title": "Vanguard Financials ETF"},
            {"ticker": "ESGV", "title": "Vanguard ESG U.S. Stock ETF"},
            {"ticker": "MGV", "title": "Vanguard Mega Cap Value ETF"},
            {"ticker": "VSS", "title": "Vanguard FTSE All-World ex-US Small-Cap ETF"},
            {"ticker": "VGLT", "title": "Vanguard Long-Term Treasury ETF"},
            {"ticker": "MGC", "title": "Vanguard Mega Cap ETF"},
            {"ticker": "VIGI", "title": "Vanguard International Dividend Appreciation ETF"},
            {"ticker": "VPL", "title": "Vanguard FTSE Pacific ETF"},
            {"ticker": "VDE", "title": "Vanguard Energy ETF"},
            {"ticker": "VDC", "title": "Vanguard Consumer Staples ETF"},
            {"ticker": "VPU", "title": "Vanguard Utilities ETF"},
            {"ticker": "VCLT", "title": "Vanguard Long-Term Corporate Bond ETF"},
            {"ticker": "VUSB", "title": "Vanguard Ultra-Short Bond ETF"},
            {"ticker": "VONE", "title": "Vanguard Russell 1000 ETF"},
            {"ticker": "VIS", "title": "Vanguard Industrials ETF"},
            {"ticker": "VCR", "title": "Vanguard Consumer Discretionary ETF"},
            {"ticker": "VOOV", "title": "Vanguard S&P 500 Value ETF"},
            {"ticker": "VOX", "title": "Vanguard Communication Services ETF"},
            {"ticker": "VSGX", "title": "Vanguard ESG International Stock ETF"},
            {"ticker": "VWOB", "title": "Vanguard Emerging Markets Government Bond ETF"},
            {"ticker": "VCRB", "title": "Vanguard Core Bond ETF"},
            {"ticker": "BLV", "title": "Vanguard Long-Term Bond ETF"},
            {"ticker": "VBIL", "title": "Vanguard 0-3 Month Treasury Bill ETF"},
            {"ticker": "VTHR", "title": "Vanguard Russell 3000 ETF"},
            {"ticker": "EDV", "title": "Vanguard Extended Duration Treasury ETF"},
            {"ticker": "VNQI", "title": "Vanguard Global ex-U.S. Real Estate ETF"},
            {"ticker": "VIOO", "title": "Vanguard S&P Small-Cap 600 ETF"},
            {"ticker": "IVOO", "title": "Vanguard S&P Mid-Cap 400 ETF"},
            {"ticker": "VAW", "title": "Vanguard Materials ETF"},
            {"ticker": "VTEC", "title": "Vanguard California Tax-Exempt Bond ETF"},
            {"ticker": "VTES", "title": "Vanguard Short-Term Tax Exempt Bond ETF"},
            {"ticker": "VIOV", "title": "Vanguard S&P Small-Cap 600 Value ETF"},
            {"ticker": "VTC", "title": "Vanguard Total Corporate Bond ETF"},
            {"ticker": "BNDW", "title": "Vanguard Total World Bond ETF"},
            {"ticker": "IVOG", "title": "Vanguard S&P Mid-Cap 400 Growth ETF"},
            {"ticker": "VFMO", "title": "Vanguard U.S. Momentum Factor ETF"},
            {"ticker": "VTWG", "title": "Vanguard Russell 2000 Growth ETF"},
            {"ticker": "VTEI", "title": "Vanguard Intermediate-Term Tax-Exempt Bond ETF"},
            
            # Other Popular ETFs
            {"ticker": "SPY", "title": "SPDR S&P 500 ETF Trust"},
            {"ticker": "IVV", "title": "iShares Core S&P 500 ETF"},
            {"ticker": "QQQ", "title": "Invesco QQQ Trust"},
            {"ticker": "IWM", "title": "iShares Russell 2000 ETF"},
            {"ticker": "EFA", "title": "iShares MSCI EAFE ETF"},
            {"ticker": "AGG", "title": "iShares Core U.S. Aggregate Bond ETF"},
            {"ticker": "GLD", "title": "SPDR Gold Shares"}
        ]
        
        # Add to search cache if not already present (checking ticker)
        existing_tickers = {item['ticker'] for item in self.search_cache}
        
        for etf in etfs:
            if etf['ticker'] not in existing_tickers:
                self.search_cache.append(etf)
                # Note: We don't have CIKs for these easily available for filing lookups, 
                # but this enables SEARCH which is the primary request.


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
