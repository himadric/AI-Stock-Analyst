import requests
import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime
import difflib
from app.services.sec import SECService

class InstitutionService:
    def __init__(self):
        self.sec_service = SECService()
        self.headers = self.sec_service.headers
        self.vanguard_cik = "0000102909"
        
        # Build Title -> Ticker map for resolution
        self.title_to_ticker = {}
        for entry in self.sec_service.search_cache:
            # Normalize title: remove punct, uppercase
            clean_title = self._clean_name(entry['title'])
            self.title_to_ticker[clean_title] = entry['ticker']

    def _clean_name(self, name: str) -> str:
        name = name.upper().replace(".", "").replace(",", "")
        remove_words = [" INC", " CORP", " CORPORATION", " COMPANY", " LTD", " PLC", " SA", " NV", " GROUP", " HLDGS", " HOLDINGS"]
        for word in remove_words:
            if name.endswith(word):
                name = name[:-len(word)]
        return name.strip()

    def get_vanguard_trades(self, limit=10):
        """
        Orchestrator: Tries DB first, falls back to live SEC fetch.
        """
        # 1. Try DB
        db_data = self._get_from_db(limit)
        if db_data:
            return db_data
            
        print("Falling back to live SEC data...")
        # 2. Fallback to Live
        return self._fetch_live_vanguard_trades(limit)

    def _get_from_db(self, limit):
        try:
            import os
            from pymongo import MongoClient
            uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
            if not uri: 
                print("DEBUG: No MONGO_URI found in env.")
                return None
            
            print("DEBUG: Attempting to connect to MongoDB...")
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            db = client["ai_stock_analyst"]
            col = db["vanguard_tracker"]
            
            # Fetch Docs
            buy_count = col.count_documents({"type": "buy"})
            print(f"DEBUG: Found {buy_count} buy docs in DB.")
            
            buy_doc = col.find_one({"type": "buy"})
            sell_doc = col.find_one({"type": "sell"})
            
            if not buy_doc or not sell_doc:
                print("DEBUG: Buy or Sell doc missing in DB.")
                return None
            
            print("DEBUG: Successfully loaded data from DB.")
            return {
                "report_date": buy_doc.get("report_date"),
                "prev_report_date": buy_doc.get("prev_report_date"),
                # Slice to requested limit (DB has 100, UI might want 10)
                "top_buys": buy_doc.get("data", [])[:limit],
                "top_sells": sell_doc.get("data", [])[:limit]
            }
        except Exception as e:
            print(f"DB Read Error: {e}")
            return None

    def _fetch_live_vanguard_trades(self, limit=10):
        """
        Fetches last 2 13F filings, compares them, determines top buys/sells.
        (Original Logic)
        """
        try:
            filings = self._get_last_two_13f(self.vanguard_cik)
            if len(filings) < 2:
                return {"error": "Insufficient data"}
            
            # Parse Current and Previous
            df_curr = self._fetch_and_parse_13f(filings[0])
            df_prev = self._fetch_and_parse_13f(filings[1])
            
            if df_curr.empty or df_prev.empty:
                return {"error": "Failed to parse info tables"}
            
            # Merge on CUSIP (more reliable unique ID than name)
            # 13F XML has 'cusip'
            merged = pd.merge(df_curr, df_prev, on="cusip", suffixes=('_curr', '_prev'), how='outer')
            
            # Fill NaNs with 0 (new position or sold out)
            merged.fillna(0, inplace=True)
            
            # Calculate Change
            merged['share_change'] = merged['shares_curr'] - merged['shares_prev']
            merged['value_change'] = merged['value_curr'] - merged['value_prev']
            
            # Resolve Names/Tickers
            # Prefer current issuer name, fallback to prev
            merged['issuer'] = merged.apply(lambda x: x['issuer_curr'] if x['issuer_curr'] != 0 else x['issuer_prev'], axis=1)
            
            # Map to Ticker
            merged['ticker'] = merged['issuer'].apply(self._resolve_ticker)
            
            # Aggregate by Ticker
            agg_dict = {
                'share_change': 'sum',
                'value_change': 'sum',
                'shares_curr': 'sum',
                'shares_prev': 'sum',
                'issuer': 'first' # Just take one name
            }
            
            resolved_df = merged.dropna(subset=['ticker'])
            
            if not resolved_df.empty:
                grouped_resolved = resolved_df.groupby('ticker', as_index=False).agg(agg_dict)
            else:
                grouped_resolved = pd.DataFrame(columns=['ticker', 'share_change', 'value_change', 'shares_curr', 'shares_prev', 'issuer'])
                
            final_df = grouped_resolved
            
            # Filter Top Buys (Value Change > 0)
            buys = final_df[final_df['value_change'] > 0].sort_values('value_change', ascending=False).head(limit)
            
            # Filter Top Sells (Value Change < 0)
            sells = final_df[final_df['value_change'] < 0].sort_values('value_change', ascending=True).head(limit)
            
            def format_rows(df):
                result = []
                for _, row in df.iterrows():
                    result.append({
                        "ticker": row['ticker'] or "N/A",
                        "name": row['issuer'],
                        "shares_change": int(row['share_change']),
                        "value_change": int(row['value_change']), # In thousands
                        "shares_current": int(row['shares_curr']),
                        "percent_change": (row['share_change'] / row['shares_prev'] * 100) if row['shares_prev'] > 0 else 100.0
                    })
                return result

            return {
                "report_date": filings[0]['date'],
                "prev_report_date": filings[1]['date'],
                "top_buys": format_rows(buys),
                "top_sells": format_rows(sells)
            }
            
        except Exception as e:
            print(f"Error getting Vanguard trades: {e}")
            return {"error": str(e)}

    def _resolve_ticker(self, issuer_name: str):
        if not isinstance(issuer_name, str): return None
        clean = self._clean_name(issuer_name)
        # Direct Match
        if clean in self.title_to_ticker:
            return self.title_to_ticker[clean]
        
        # Fuzzy / Partial Match (expensive loop, limit to exact starts in cache?)
        # For simplicity/speed in MVP, we might skip expensive fuzzy match or do simple heuristic
        # Try finding exact word match in dictionary keys
        return None

    def _get_last_two_13f(self, cik):
        cik_padded = str(cik).zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        
        try:
            resp = requests.get(url, headers=self.headers)
            data = resp.json()
            recent = data['filings']['recent']
            
            forms = []
            for i, form in enumerate(recent['form']):
                if form == '13F-HR':
                    forms.append({
                        "acc": recent['accessionNumber'][i],
                        "doc": recent['primaryDocument'][i],
                        "date": recent['filingDate'][i]
                    })
                    if len(forms) >= 2: break
            return forms
        except Exception as e:
            print(f"Error fetching submission history: {e}")
            return []

    def _fetch_and_parse_13f(self, filing_meta):
        # 1. Find info table XML URL via index scraping
        cik = self.vanguard_cik.lstrip('0')
        acc_no_dash = filing_meta['acc'].replace("-", "")
        index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dash}/{filing_meta['acc']}-index.html"
        
        try:
            idx_resp = requests.get(index_url, headers=self.headers)
            if idx_resp.status_code != 200: return pd.DataFrame()
            
            soup = BeautifulSoup(idx_resp.content, 'html.parser')
            xml_url = None
            for row in soup.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) > 3:
                     doc_type = cells[1].text.strip()
                     doc_name = cells[2].text.strip()
                     if "INFORMATION TABLE" in doc_type.upper() and doc_name.endswith(".xml"):
                         xml_href = cells[2].find("a")["href"]
                         xml_url = f"https://www.sec.gov{xml_href}"
                         break
            
            if not xml_url: return pd.DataFrame()
            
            # 2. Parse XML
            xml_resp = requests.get(xml_url, headers=self.headers)
            root = ET.fromstring(xml_resp.content)
            
            holdings = []
            # Handle Namespace blindly
            for info in root.findall(".//{*}infoTable"):
                 try:
                    issuer = info.find(".//{*}nameOfIssuer").text
                    cusip = info.find(".//{*}cusip").text
                    value = float(info.find(".//{*}value").text)
                    shares = float(info.find(".//{*}shrsOrPrnAmt/{*}sshPrnamt").text)
                    
                    holdings.append({
                        "issuer": issuer,
                        "cusip": cusip,
                        "value": value,
                        "shares": shares
                    })
                 except: pass
            
            return pd.DataFrame(holdings)
            
        except Exception as e:
            print(f"Error parsing 13F: {e}")
            return pd.DataFrame()
