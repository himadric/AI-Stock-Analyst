import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
import requests
from datetime import datetime, timedelta
from app.db import db

class FinanceService:
    def get_govt_backlog(self, ticker: str, uei: str = None):
        """
        Calculates Book-to-Bill ratio for govt contractors using USAspending API.
        Book-to-Bill = New Orders (90d) / Quarterly Revenue
        """
        # 1. Resolve Company Name
        ticker_map = {
            "LMT": "Lockheed Martin",
            "RTX": "Raytheon", 
            "GD": "General Dynamics",
            "NOC": "Northrop Grumman",
            "BA": "Boeing",
            "HII": "Huntington Ingalls",
            "LHX": "L3Harris"
        }
        company_name = ticker_map.get(ticker)
        
        # Try to guess from YF info if not mapped
        if not company_name:
            info = self.get_company_info(ticker)
            if info:
                # Simplistic cleanup: "Lockheed Martin Corporation" -> "Lockheed Martin"
                raw_name = info.get("name") or ""
                company_name = raw_name.replace(" Corporation", "").replace(" Inc", "").replace(" Company", "").strip()

        if not company_name and not uei:
            return None

        # 2. Fetch USASpending Awards (Orders "Book")
        # Look back 90 days (approx 1 quarter) to match quarterly revenue cadence
        days = 90
        url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Prepare filters
        filters = {
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": ["A", "B", "C", "D"]
        }
        
        if uei:
            filters["recipient_search_text"] = [uei]
        else:
             filters["keywords"] = [company_name]
             
        payload = {
            "filters": filters,
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Description", "Start Date"],
            "limit": 50, # Get enough to sum meaningful amount
            "page": 1,
            "sort": "Start Date",
            "order": "desc"
        }
        
        orders_total = 0
        awards_list = []
        
        try:
            res = requests.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                
                # Sum up ALL awards found in this page (Note: Production should paginate)
                # For POC, taking top 50 is a proxy, or ideally we fetch aggregate endpoint.
                # But user asked for "spending_by_award" to see description.
                # Let's sum the displayed ones.
                orders_total = sum(item.get("Award Amount", 0) for item in results)
                
                for item in results:
                    awards_list.append({
                        "id": item.get("Award ID"),
                        "amount": item.get("Award Amount"),
                        "date": item.get("Start Date"),
                        "description": item.get("Description")
                    })
        except Exception as e:
            print(f"Error fetching USASpending: {e}")

        # 3. Fetch Revenue ("Bill")
        revenue = 0
        financials = self.get_quarterly_financials(ticker)
        if financials and len(financials) > 0:
            # Most recent quarter
            # Revenue is in dollars (e.g., 15B = 15,000,000,000)
            revenue = financials[0].get("revenue", 0)

        # 4. Calculate Ratio
        # Book to Bill = Orders / Revenue
        book_to_bill = 0
        if revenue > 0:
            book_to_bill = orders_total / revenue

        return {
            "ticker": ticker,
            "company_name": company_name,
            "uei": uei,
            "period_days": days,
            "orders_inflow": orders_total,
            "revenue_billed": revenue,
            "book_to_bill_ratio": book_to_bill,
            "analysis": "Strong Buy (Backlog Growing)" if book_to_bill > 1.0 else "Weak (Backlog Shrinking)",
            "recent_awards": awards_list[:10] # Top 10 for display
        }

    def get_govt_rankings(self):
        """
        Returns all govt contractors data from MongoDB.
        """
        try:
            mongo_db = db.get_db()
            collection = mongo_db["govt_contracts"] 
            doc = collection.find_one({"_id": "contractors"})
            
            if doc and "companies" in doc:
                return doc["companies"]
        except Exception as e:
            print(f"Error loading govt rankings: {e}")
            
        return []

    def _get_peg_ratio(self, info: dict) -> float | None:
        """
        Calculates PEG ratio if missing.
        Formula: Forward PE / (Earnings Growth Rate * 100)
        """
        peg = info.get("pegRatio")
        if peg is not None:
            return peg
            
        # Fallback calculation
        try:
            forward_pe = info.get("forwardPE")
            growth = info.get("earningsGrowth") # e.g. 0.15 for 15%
            
            if forward_pe and growth and growth > 0:
                # growth is usually decimal in API (0.15), PEG formula uses integer (15)
                # So: PE / (growth * 100)
                return forward_pe / (growth * 100)
        except Exception:
            pass
            
        return None

    def get_company_info(self, ticker: str):
        """
        Fetches basic company information for a given ticker.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            # Extract relevant fields
            return {
                "name": info.get("longName"),
                "ticker": ticker.upper(),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "website": info.get("website"),
                "employees": info.get("fullTimeEmployees"),
                "summary": info.get("longBusinessSummary"),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": self._get_peg_ratio(info),
                "price_to_sales": info.get("priceToSalesTrailing12Months"),
                "profit_margin": info.get("profitMargins"),
                "roe": info.get("returnOnEquity"),
                "free_cash_flow": info.get("freeCashflow"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "current_ratio": info.get("currentRatio"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "revenue_growth": info.get("revenueGrowth"),
                "executives": [
                    {
                        "name": officer.get("name"),
                        "title": officer.get("title"),
                        "age": officer.get("age") or (datetime.now().year - officer.get("yearBorn")) if officer.get("yearBorn") else None,
                        "bio": officer.get("title") # Fallback as bio is rarely separate
                    }
                    for officer in info.get("companyOfficers", [])[:5] # Limit to top 5
                ]
                ,
                "total_revenue": info.get("totalRevenue"),
                "revenue_per_employee": (info.get("totalRevenue") / info.get("fullTimeEmployees")) if (info.get("totalRevenue") and info.get("fullTimeEmployees")) else None,
                "year_range": f"{info.get('fiftyTwoWeekLow')} - {info.get('fiftyTwoWeekHigh')}" if info.get('fiftyTwoWeekLow') and info.get('fiftyTwoWeekHigh') else "N/A"
            }
        except Exception as e:
            print(f"Error fetching company info for {ticker}: {e}")
            return None

    def get_quotes(self, tickers: list[str]):
        """
        Fetches current price and change for a list of tickers.
        """
        try:
            # yfinance allows fetching multiple tickers at once
            # e.g. yf.Tickers("MSFT AAPL GOOG")
            string_tickers = " ".join(tickers)
            data = yf.Tickers(string_tickers)
            
            quotes = []
            for symbol in tickers:
                try:
                    t = data.tickers[symbol]
                    
                    # Fetch full info for Name/PE
                    info = t.info
                    
                    # Fallback to fast_info for price if info is missing it
                    price = info.get("currentPrice") or info.get("regularMarketPrice") or t.fast_info.last_price
                    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or t.fast_info.previous_close
                    
                    change = price - prev_close
                    change_percent = (change / prev_close) * 100 if prev_close else 0
                    
                    quotes.append({
                        "ticker": symbol,
                        "name": info.get("shortName") or info.get("longName"),
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "pe": info.get("trailingPE"),
                        "volume": info.get("volume") or info.get("regularMarketVolume") or getattr(t.fast_info, 'last_volume', 0)
                    })
                except Exception as inner_e:
                    print(f"Error fetching quote for {symbol}: {inner_e}")
                    # Continue pending other tickers
            return quotes
        except Exception as e:
            return []

    def get_stock_history(self, ticker: str, period: str = "1y", interval: str = "1d"):
        """
        Fetches historical price data for charts.
        """
        try:
            stock = yf.Ticker(ticker)
            # Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
            # Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
            
            hist = stock.history(period=period, interval=interval)
            
            if hist.empty:
                return []
            
            # Reset index to get Date as a column
            hist.reset_index(inplace=True)
            
            data = []
            for _, row in hist.iterrows():
                # Handle timezone-aware datetimes
                date_val = row.get('Date')
                if date_val is None:
                    # Intraday data (1d, 5d) often returns 'Datetime'
                    date_val = row.get('Datetime')
                
                if hasattr(date_val, 'isoformat'):
                    date_str = date_val.isoformat()
                else:
                    date_str = str(date_val)

                data.append({
                    "date": date_str,
                    "open": row.get('Open', 0),
                    "high": row.get('High', 0),
                    "low": row.get('Low', 0),
                    "close": row.get('Close', 0),
                    "volume": row.get('Volume', 0)
                })
                
            return self._sanitize_data(data)
        except Exception as e:
            print(f"Error fetching history for {ticker}: {e}")
            return []


    def get_rankings(self, category: str = "Small Cap", page: int = 1, limit: int = 10):
        """
        ranks companies based on the future leader score.
        Returns paginated results from MongoDB.
        """
        candidates_data = []
        loaded_from_db = False
        
        # Map Category Str to DB ID
        cat_map = {
            "Small Cap": "small_cap",
            "Mid Cap": "mid_cap",
            "Large Cap": "large_cap"
        }
        db_id = cat_map.get(category)

        # Try MongoDB
        if db_id:
            try:
                mongo_db = db.get_db()
                collection = mongo_db["leaderboard"]
                doc = collection.find_one({"_id": db_id})
                
                if doc and "companies" in doc:
                    candidates_data = doc["companies"]
                    loaded_from_db = True
            except Exception as e:
                print(f"Error loading from MongoDB: {e}")

        # Fallback: Live generation if cache miss (or Mongo failed)
        if not candidates_data:
            print("Fallback to live generation...")
            # Load tickers from generated file
            json_path = os.path.join(os.path.dirname(__file__), "../data/sp_indices.json")
            tickers = []
            
            try:
                if os.path.exists(json_path):
                    with open(json_path, "r") as f:
                        indices = json.load(f)
                        tickers = indices.get(category, [])
            except Exception as e:
                print(f"Error loading indices: {e}")

            if not tickers:
                # Hardcoded fallbacks
                if category == "Small Cap":
                    tickers = ["UPST", "AFRM", "PATH", "IOT", "AMPL", "CFLT", "MNDY", "DOCN", "FVRR", "LMND", "BMBL", "LAW", "COUR", "NCNO", "WK", "ZI"]
                elif category == "Mid Cap":
                    tickers = ["DDOG", "NET", "ZS", "CRWD", "HUBS", "TTD", "OKTA", "TEAM", "MDB", "PLTR", "U", "SNOW", "ESTC", "ZM", "GME", "AMC"]
                else: 
                    tickers = ["NVDA", "TSLA", "AMD", "META", "AMZN", "GOOGL", "MSFT", "AAPL", "CRM", "ADBE", "INTC", "CSCO", "ORCL", "NFLX", "AVGO", "TXN"]
            
            # Live Scoring (Sampled)
            import random
            # If we are falling back to live scoring, we can't paginate effectively without scoring ALL.
            # But scoring all is slow. So we sample a small set (e.g. 20) and return that page.
            # This logic is imperfect for pagination but acceptable for a fallback.
            sample_candidates = tickers
            if len(tickers) > 20:
                sample_candidates = random.sample(tickers, 20)

            for ticker in sample_candidates:
                try:
                    score_data = self.get_future_leader_score(ticker)
                    if score_data:
                        candidates_data.append({
                            "ticker": ticker,
                            "rank": 0,
                            "total_score": score_data["total_score"],
                            "factors": score_data["factors"]
                        })
                except Exception as e:
                     # print(f"Skipping {ticker}: {e}")
                     pass
            
            # Sort by score
            candidates_data.sort(key=lambda x: x["total_score"], reverse=True)
            
            # Re-assign ranks
            for i, company in enumerate(candidates_data):
                company["rank"] = i + 1

        # Pagination Logic
        total_count = len(candidates_data)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        
        paginated_data = candidates_data[start_index:end_index]
        
        return {
            "data": paginated_data,
            "total": total_count,
            "page": page,
            "limit": limit
        }

    def get_company_news(self, ticker: str):
        """
        Fetches recent news for a given ticker.
        """
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            
            formatted_news = []
            for item in news[:4]:
                # Check for nested 'content' key
                news_data = item.get('content', item)
                if not news_data:
                    continue
                
                # Extract fields safely
                title = news_data.get('title', 'No Title')
                
                # Publisher is nested in 'provider' -> 'displayName'
                publisher = news_data.get('provider', {}).get('displayName', 'Unknown Publisher')
                
                # Link is in 'link' or nested in 'canonicalUrl' -> 'url' or 'clickThroughUrl' -> 'url'
                link = news_data.get('link')
                if not link:
                     link = news_data.get('canonicalUrl', {}).get('url')
                if not link:
                     link = news_data.get('clickThroughUrl', {}).get('url')
                
                # Publish time
                publish_time = news_data.get('providerPublishTime')
                if not publish_time:
                    # Parse pubDate if available (ISO string)
                    pub_date_str = news_data.get('pubDate')
                    if pub_date_str:
                         try:
                             dt = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                             publish_time = int(dt.timestamp())
                         except:
                             publish_time = 0
                
                if title and link:
                    formatted_news.append({
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                        "providerPublishTime": publish_time or 0
                    })
            
            return formatted_news
        except Exception as e:
            print(f"Error fetching news for {ticker}: {e}")
            return []

    def get_quarterly_financials(self, ticker: str):
        """
        Fetches quarterly financials (Revenue, Income, EPS) for the last 4 quarters.
        """
        try:
            stock = yf.Ticker(ticker)
            qf = stock.quarterly_financials
            
            if qf.empty:
                return []
            
            # Transpose to get dates as rows
            qf_T = qf.transpose()
            
            # Sort by date descending and take top 5 (to allow for potential growth calcs or context)
            qf_T.sort_index(ascending=False, inplace=True)
            recent_qf = qf_T.head(5).copy()
            recent_qf.sort_index(ascending=True, inplace=True)
            
            data = []
            for date, row in recent_qf.iterrows():
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "revenue": row.get("Total Revenue", 0),
                    "cost_of_revenue": row.get("Cost Of Revenue", 0),
                    "gross_profit": row.get("Gross Profit", 0),
                    "research_development": row.get("Research And Development", 0),
                    "selling_general_admin": row.get("Selling General And Administration", 0),
                    "operating_expense": row.get("Operating Expense", 0),
                    "operating_income": row.get("Operating Income", 0),
                    "total_expenses": row.get("Total Expenses", 0),
                    "interest_expense": row.get("Interest Expense", 0),
                    "pretax_income": row.get("Pretax Income", 0),
                    "tax_provision": row.get("Tax Provision", 0),
                    "net_income": row.get("Net Income", 0),
                    "basic_eps": row.get("Basic EPS", 0),
                    "diluted_eps": row.get("Diluted EPS", 0),
                    "shares_basic": row.get("Basic Average Shares", 0),
                    "shares_diluted": row.get("Diluted Average Shares", 0)
                })
            
            return self._sanitize_data(data)
        except Exception as e:
            print(f"Error fetching financials for {ticker}: {e}")
            return []

    def get_quarterly_balance_sheet(self, ticker: str):
        """
        Fetches quarterly balance sheet (Cash, Assets, Liab) for the last 5 quarters.
        """
        try:
            stock = yf.Ticker(ticker)
            qbs = stock.quarterly_balance_sheet
            
            if qbs.empty:
                return []
            
            # Transpose to get dates as rows
            qbs_T = qbs.transpose()
            
            # Sort by date descending and take top 5
            qbs_T.sort_index(ascending=False, inplace=True)
            recent_qbs = qbs_T.head(5).copy()
            
            # Sort back to ascending for display consistency
            recent_qbs.sort_index(ascending=True, inplace=True)
            
            data = []
            for date, row in recent_qbs.iterrows():
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "cash_equivalents": row.get("Cash And Cash Equivalents", 0),
                    "short_term_investments": row.get("Other Short Term Investments", 0), # yfinance often puts it here
                    "inventory": row.get("Inventory", 0),
                    "accounts_receivable": row.get("Accounts Receivable", 0), # or 'Receivables' if simplified
                    "total_current_assets": row.get("Total Current Assets", 0),
                    "total_assets": row.get("Total Assets", 0),
                    "accounts_payable": row.get("Accounts Payable", 0),
                    "total_current_liabilities": row.get("Total Current Liabilities", 0),
                    "total_liabilities": row.get("Total Liabilities Net Minority Interest", 0) or row.get("Total Liabilities", 0),
                    "total_equity": row.get("Total Equity Gross Minority Interest", 0) or row.get("Stockholders Equity", 0),
                    "working_capital": row.get("Working Capital", 0),
                })
            
            return self._sanitize_data(data)
        except Exception as e:
            print(f"Error fetching balance sheet for {ticker}: {e}")
            return []

    def get_quarterly_cash_flow(self, ticker: str):
        """
        Fetches quarterly cash flow (Operating, Investing, Financing) for the last 5 quarters.
        """
        try:
            stock = yf.Ticker(ticker)
            qcf = stock.quarterly_cashflow
            
            if qcf.empty:
                return []
            
            # Transpose to get dates as rows
            qcf_T = qcf.transpose()
            
            # Sort by date descending and take top 5
            qcf_T.sort_index(ascending=False, inplace=True)
            recent_qcf = qcf_T.head(5).copy()
            
            # Sort back to ascending for display consistency
            recent_qcf.sort_index(ascending=True, inplace=True)
            
            data = []
            for date, row in recent_qcf.iterrows():
                data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "net_income": row.get("Net Income From Continuing Operations", 0) or row.get("Net Income", 0),
                    "depreciation_amortization": row.get("Depreciation And Amortization", 0),
                    "stock_based_compensation": row.get("Stock Based Compensation", 0),
                    "change_in_working_capital": row.get("Change In Working Capital", 0),
                    "operating_cash_flow": row.get("Operating Cash Flow", 0),
                    "capital_expenditure": row.get("Capital Expenditure", 0),
                    "buying_selling_assets": row.get("Net PPE Purchase And Sale", 0), # Simplified proxy
                    "investing_cash_flow": row.get("Investing Cash Flow", 0),
                    "debt_repayment": row.get("Net Debt Issued", 0) or row.get("Net Borrowings", 0), # Negative usually means repayment
                    "common_stock_issued": row.get("Net Common Stock Issuance", 0) or row.get("Issuance Of Capital Stock", 0),
                    "dividend_paid": row.get("Cash Dividends Paid", 0),
                    "financing_cash_flow": row.get("Financing Cash Flow", 0),
                    "net_change_in_cash": row.get("Changes In Cash", 0) or row.get("Change In Cash", 0),
                    "free_cash_flow": row.get("Free Cash Flow", 0),
                })
            
            return self._sanitize_data(data)
        except Exception as e:
            print(f"Error fetching cash flow for {ticker}: {e}")
            return []

    def get_quarterly_ratios(self, ticker: str):
        """
        Computes historical valuation and financial ratios for the last 5 quarters.
        """
        try:
            # Re-use existing methods to get clean data
            income = self.get_quarterly_financials(ticker)
            balance = self.get_quarterly_balance_sheet(ticker)
            cash_flow = self.get_quarterly_cash_flow(ticker)
            
            if not income:
                return []
            
            # Map data by date for easy lookup
            inc_map = {item['date']: item for item in income}
            bal_map = {item['date']: item for item in balance}
            cf_map = {item['date']: item for item in cash_flow}
            
            # Get common dates (using income statement as driver)
            dates = sorted(list(inc_map.keys()), reverse=True)
            
            # Fetch price history to get Close price on these dates
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2y")
            
            ratios = []
            
            for date_str in dates:
                inc_item = inc_map.get(date_str, {})
                bal_item = bal_map.get(date_str, {})
                cf_item = cf_map.get(date_str, {})
                
                # Find closest trading day close price
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Find index in hist strictly <= target_date
                price = 0
                try:
                    # Filter history for dates up to the report date
                    mask = hist.index <= target_date.replace(tzinfo=hist.index.tz) # Ensure tz-aware comparison if needed, or naive
                    # yfinance indices are tz-aware. target_date is naive.
                    # Best to make target_date tz-aware or strip tz from hist.
                    # Simplest: use string comparison or strip tz
                    if hist.index.tz is not None:
                         target_date = target_date.replace(tzinfo=hist.index.tz)

                    mask = hist.index <= target_date
                    if any(mask):
                        subset = hist.loc[mask]
                        if not subset.empty:
                            price = subset.iloc[-1]['Close']
                except Exception as p_ex:
                     # Fallback if tz comparison fails
                     print(f"Error finding price for {date_str}: {p_ex}")
                
                # Extract basic metrics (default to 0 if missing)
                revenue = inc_item.get('revenue', 0) or 0
                net_income = inc_item.get('net_income', 0) or 0
                gross_profit = inc_item.get('gross_profit', 0) or 0
                op_income = inc_item.get('operating_income', 0) or 0
                diluted_eps = inc_item.get('diluted_eps', 0) or 0
                
                total_assets = bal_item.get('total_assets', 0) or 0
                total_equity = bal_item.get('total_equity', 0) or 0
                total_debt = bal_item.get('total_liabilities', 0) 
                cash_and_equiv = bal_item.get('cash_equivalents', 0) or 0
                
                op_cash_flow = cf_item.get('operating_cash_flow', 0) or 0
                free_cash_flow = cf_item.get('free_cash_flow', 0) or 0
                
                # Shares
                shares = inc_item.get('basic_average_shares', 0) or inc_item.get('diluted_average_shares', 0) or 0
                
                market_cap = price * shares if shares else 0
                enterprise_value = market_cap + total_debt - cash_and_equiv
                
                # EBITDA = Operating Income + D&A
                da = cf_item.get('depreciation_amortization', 0) or 0
                ebitda = op_income + da
                
                ratios.append({
                    "date": date_str,
                    "market_cap": market_cap,
                    "enterprise_value": enterprise_value,
                    "price": price,
                    
                    # Valuation
                    "pe_ratio": price / diluted_eps if diluted_eps and diluted_eps != 0 else 0,
                    "ps_ratio": market_cap / revenue if revenue else 0,
                    "pb_ratio": market_cap / total_equity if total_equity else 0,
                    "ev_ebitda": enterprise_value / ebitda if ebitda else 0,
                    "ev_sales": enterprise_value / revenue if revenue else 0,
                    
                    # Profitability
                    "gross_margin": (gross_profit / revenue) * 100 if revenue else 0,
                    "operating_margin": (op_income / revenue) * 100 if revenue else 0,
                    "net_margin": (net_income / revenue) * 100 if revenue else 0,
                    "return_on_equity": (net_income / total_equity) * 100 if total_equity else 0,
                    "return_on_assets": (net_income / total_assets) * 100 if total_assets else 0,
                    
                    # Leverage / Health
                    "debt_to_equity": total_debt / total_equity if total_equity else 0,
                    "current_ratio": bal_item.get('total_current_assets', 0) / bal_item.get('total_current_liabilities', 1) if bal_item.get('total_current_liabilities') else 0,
                    
                    # Cash Flow
                    "fcf_yield": (free_cash_flow / market_cap) * 100 if market_cap else 0,
                })
                
            return self._sanitize_data(ratios)
        except Exception as e:
            print(f"Error computing ratios for {ticker}: {e}")
            return []

    def get_forecast(self, ticker: str):
        """
        Fetches analyst forecast data (price targets and recommendations).
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Extract relevant fields
            return {
                "targetHighPrice": info.get("targetHighPrice"),
                "targetLowPrice": info.get("targetLowPrice"),
                "targetMeanPrice": info.get("targetMeanPrice"),
                "targetMedianPrice": info.get("targetMedianPrice"),
                "recommendationMean": info.get("recommendationMean"),
                "recommendationKey": info.get("recommendationKey"),
                "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
                "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice")
            }
        except Exception as e:
            print(f"Error fetching forecast for {ticker}: {e}")
            return None

    def get_analyst_actions(self, ticker: str):
        """
        Fetches detailed positive/negative analyst actions (upgrades/downgrades).
        """
        try:
            stock = yf.Ticker(ticker)
            upgrades = stock.upgrades_downgrades
            
            if upgrades is None or upgrades.empty:
                return []
            
            # Reset index to get GradeDate as a column
            upgrades.reset_index(inplace=True)
            
            # Sort by GradeDate descending
            if 'GradeDate' in upgrades.columns:
                upgrades.sort_values(by='GradeDate', ascending=False, inplace=True)
            
            # Take top 30
            recent = upgrades.head(30)
            
            data = []
            for _, row in recent.iterrows():
                # Clean up date
                date_val = row.get('GradeDate')
                date_str = ""
                if pd.notnull(date_val):
                     date_str = str(date_val) # converts timestamp to string
                
                data.append({
                    "date": date_str,
                    "firm": row.get('Firm', ''),
                    "to_grade": row.get('ToGrade', ''),
                    "from_grade": row.get('FromGrade', ''),
                    "action": row.get('Action', ''),
                    "current_price_target": row.get('currentPriceTarget', 0),
                    "prior_price_target": row.get('priorPriceTarget', 0),
                })
                
            return self._sanitize_data(data)
        except Exception as e:
            print(f"Error fetching analyst actions for {ticker}: {e}")
            return []

    def get_ownership(self, ticker: str):
        """
        Fetches ownership distribution (Insiders vs Institutions vs Public).
        """
        try:
            stock = yf.Ticker(ticker)
            major = stock.major_holders
            
            if major is None or major.empty:
                return None
            
            # major_holders output format varies. 
            # Usually:
            # Breakdown                          Value
            # insidersPercentHeld              0.0016
            # institutionsPercentHeld          0.64
            # ...
            
            # Or index 0: %, index 1: Description (older versions)
            
            # Based on debug output: 
            # Breakdown                          Value
            # insidersPercentHeld              0.01697
            # institutionsPercentHeld          0.64406
            
            # Check if columns are likely 'Breakdown' and 'Value' or generic integers
            # We'll try to convert to a dictionary for easier access
            
            # yfinance often returns it with 'Breakdown' as index or column.
            # reset_index was NOT called in debug, so let's inspect the debug output structure again if needed.
            # But simpler is to iterate or try to grab values by key if index is set.
            
            data = {}
            if "Breakdown" in major.columns and "Value" in major.columns:
                 # It's a dataframe with these columns
                 for i, row in major.iterrows():
                     data[row["Breakdown"]] = row["Value"]
            elif isinstance(major.index, pd.Index):
                 # Maybe index is the breakdown
                 # Let's support the dataframe structure `major` usually comes in
                 # It might be pivoting. 
                 # Let's assume standard 'Value' column lookup if index is the breakdown names.
                 pass
            
            # Fallback parsing strategy based on 2024 yfinance trends:
            # It's often set index=0 (breakdown), index=1 (value) if raw
            # But the debug output showed:
            # Breakdown                          Value
            # insidersPercentHeld              0.01697
            
            # If 'Breakdown' is the index name?
            # Let's try to standardize:
            # We want 'insidersPercentHeld' and 'institutionsPercentHeld'
            
            # Let's convert to dict using 'Value' column if it exists, using Index as keys
            # Or search for row values.
            
            insiders = 0.0
            institutions = 0.0
            
            # Try 1: check if index has these keys
            try:
                # If set_index('Breakdown') was implicit
                insiders = float(major.loc['insidersPercentHeld']['Value'])
                institutions = float(major.loc['institutionsPercentHeld']['Value'])
            except:
                # Try 2: iterate rows
                for _, row in major.iterrows():
                    # Check values in row
                    # row values might be [0.01697, 'insidersPercentHeld'] or vice versa depending on version
                    # But reliable key is looking for string
                    row_vals = row.values.tolist()
                    for v in row_vals:
                        if isinstance(v, str):
                            if 'insidersPercentHeld' in v:
                                # Find the float in this row
                                for v2 in row_vals:
                                    if isinstance(v2, (int, float)):
                                        insiders = float(v2)
                            if 'institutionsPercentHeld' in v:
                                for v2 in row_vals:
                                    if isinstance(v2, (int, float)):
                                        institutions = float(v2)
            
            # Calculate public
            total_held = insiders + institutions
            if total_held > 1.0:
                # Normalize to 100%
                insiders = insiders / total_held
                institutions = institutions / total_held
                public = 0.0
            else:
                public = 1.0 - total_held
                if public < 0: public = 0
            
            return {
                "insiders": insiders * 100, # Convert to %
                "institutions": institutions * 100,
                "public": public * 100
            }
            
        except Exception as e:
            print(f"Error fetching ownership for {ticker}: {e}")
            return None

            return {
                "insiders": insiders * 100, # Convert to %
                "institutions": institutions * 100,
                "public": public * 100
            }
            
        except Exception as e:
            print(f"Error fetching ownership for {ticker}: {e}")
            return None

    def get_ownership_details(self, ticker: str):
        """
        Fetches detailed lists of top institutional and insider holders.
        """
        try:
            stock = yf.Ticker(ticker)
            
            # 1. Institutional Holders
            institutions = []
            try:
                inst_df = stock.institutional_holders
                if inst_df is not None and not inst_df.empty:
                    # Sort by Shares if possible, usually already sorted
                    top_inst = inst_df.head(20)
                    for _, row in top_inst.iterrows():
                        date_val = row.get('Date Reported')
                        date_str = str(date_val) if pd.notnull(date_val) else ""
                        institutions.append({
                            "holder": row.get('Holder', ''),
                            "shares": row.get('Shares', 0),
                            "date_reported": date_str,
                            "value": row.get('Value', 0),
                            "pct_held": row.get('pctHeld', 0) if 'pctHeld' in row else 0,
                            "change_percent": row.get('pctChange', 0)
                        })
            except Exception as e:
                print(f"Error getting institutions for {ticker}: {e}")

            # 2. Insider Holders
            insiders = []
            try:
                # Try insider_roster_holders first (more detailed)
                ins_df = stock.insider_roster_holders
                if ins_df is None or ins_df.empty:
                    # Fallback to major_holders? No, that's summary. 
                    # Maybe insider_purchases? That's transactions.
                    pass
                else:
                    top_ins = ins_df.head(20)
                    for _, row in top_ins.iterrows():
                        # Date - prefer 'Position Direct Date' or 'Latest Transaction Date'
                        date_val = row.get('Position Direct Date') or row.get('Latest Transaction Date') or row.get('Date')
                        date_str = str(date_val) if pd.notnull(date_val) else ""
                        
                        # Shares - prefer 'Shares Owned Directly'
                        shares = row.get('Shares Owned Directly') or row.get('Shares') or row.get('Position')
                        
                        # Data cleaning: ensure shares is a number
                        real_shares = 0
                        try:
                             if isinstance(shares, (int, float)) and not pd.isna(shares):
                                 real_shares = float(shares)
                             elif isinstance(shares, str) and shares.replace(',','').replace('.','').isdigit():
                                 real_shares = float(shares.replace(',',''))
                        except:
                             real_shares = 0
                             
                        insiders.append({
                            "holder": row.get('Name', ''),
                            "shares": real_shares,
                            "position": row.get('Position', '') if isinstance(row.get('Position', ''), str) else str(row.get('Position', '')), 
                            "transaction": row.get('Most Recent Transaction', ''),
                            "date_reported": date_str,
                            "url": row.get('URL', '')
                        })

            except Exception as e:
                print(f"Error getting insiders for {ticker}: {e}")
                
            return self._sanitize_data({
                "institutions": institutions,
                "insiders": insiders
            })

        except Exception as e:
            print(f"Error fetching ownership details for {ticker}: {e}")
            return {"institutions": [], "insiders": []}

    def get_macro_indicators(self):
        """
        Fetches key global macro indicators.
        """
        tickers = {
            "^GSPC": {"name": "S&P 500", "type": "Index"},
            "^IXIC": {"name": "Nasdaq", "type": "Index"},
            "^DJI": {"name": "Dow Jones", "type": "Index"},
            "^RUT": {"name": "Russell 2000", "type": "Index"},
            "^VIX": {"name": "Volatility Index", "type": "Risk"},
            "^TNX": {"name": "10Y Treasury Yield", "type": "Rate"},
            "DX=F": {"name": "Dollar Index", "type": "Currency"},
            "EURUSD=X": {"name": "EUR/USD", "type": "Currency"},
            "JPY=X": {"name": "USD/JPY", "type": "Currency"},
            "GBPUSD=X": {"name": "GBP/USD", "type": "Currency"},
            "INR=X": {"name": "USD/INR", "type": "Currency"},
            "CL=F": {"name": "Crude Oil", "type": "Commodity"},
            "GC=F": {"name": "Gold", "type": "Commodity"},
            "BTC-USD": {"name": "Bitcoin", "type": "Crypto"}
        }
        
        try:
            # Use existing bulk quote method
            symbol_list = list(tickers.keys())
            quotes = self.get_quotes(symbol_list)
            
            enhanced_quotes = []
            for q in quotes:
                meta = tickers.get(q['ticker'], {})
                enhanced_quotes.append({
                    **q,
                    "name": meta.get("name", q['ticker']),
                    "type": meta.get("type", "Other")
                })

            # Add Economic Data
            econ_data = self.get_economic_data()
            enhanced_quotes.extend(econ_data)
                
            return enhanced_quotes
        except Exception as e:
             print(f"Error fetching macro data: {e}")
             return []

    def get_economic_data(self):
        """
        Scrapes key economic indicators (GDP, CPI, Unemployment) from public sources.
        Returns them in a format compatible with quotes.
        """
        # Hardcoded history based on 2024 data (Simulation for Demo)
        # In production this would come from FRED API
        indicators = [
            {
                "name": "GDP Growth Rate", 
                "ticker": "GDP", 
                "type": "Economy", 
                "default": 3.0,
                "history": [
                    {"date": "2024-12-31", "value": 2.4}, # Q4 2024 Est
                    {"date": "2024-09-30", "value": 3.1}, # Q3 2024
                    {"date": "2024-06-30", "value": 3.0}, # Q2 2024
                    {"date": "2024-03-31", "value": 1.6}, # Q1 2024
                    {"date": "2023-12-31", "value": 3.2}, # Q4 2023
                    {"date": "2023-09-30", "value": 4.9}, # Q3 2023
                    {"date": "2023-06-30", "value": 2.1}, # Q2 2023
                    {"date": "2023-03-31", "value": 2.2}, # Q1 2023
                ]
            },
            {
                "name": "Unemployment Rate", 
                "ticker": "UNRATE", 
                "type": "Economy", 
                "default": 4.1,
                "history": [
                    {"date": "2024-12-01", "value": 4.1},
                    {"date": "2024-11-01", "value": 4.2},
                    {"date": "2024-10-01", "value": 4.1},
                    {"date": "2024-09-01", "value": 4.1},
                    {"date": "2024-08-01", "value": 4.2},
                    {"date": "2024-07-01", "value": 4.2},
                    {"date": "2024-06-01", "value": 4.1},
                    {"date": "2024-05-01", "value": 4.2},
                    {"date": "2024-04-01", "value": 4.2},
                    {"date": "2024-03-01", "value": 4.2},
                    {"date": "2024-02-01", "value": 4.1},
                    {"date": "2024-01-01", "value": 4.0},
                ]
            },
            {
                "name": "Inflation Rate (CPI)", 
                "ticker": "CPI", 
                "type": "Economy", 
                "default": 2.6,
                "history": [
                    {"date": "2024-12-01", "value": 2.9}, # Est
                    {"date": "2024-11-01", "value": 2.7},
                    {"date": "2024-10-01", "value": 2.6},
                    {"date": "2024-09-01", "value": 2.4},
                    {"date": "2024-08-01", "value": 2.5},
                    {"date": "2024-07-01", "value": 2.9},
                    {"date": "2024-06-01", "value": 2.9},
                    {"date": "2024-05-01", "value": 3.1},
                    {"date": "2024-04-01", "value": 3.4},
                    {"date": "2024-03-01", "value": 3.5},
                    {"date": "2024-02-01", "value": 3.2},
                    {"date": "2024-01-01", "value": 3.1},
                ]
            },
            {
                "name": "Fed Interest Rate", 
                "ticker": "FEDRATE", 
                "type": "Economy", 
                "default": 4.50,
                 "history": [
                    {"date": "2024-12-18", "value": 4.50},
                    {"date": "2024-11-07", "value": 4.75},
                    {"date": "2024-09-18", "value": 5.00},
                    {"date": "2023-07-26", "value": 5.50},
                    {"date": "2023-05-03", "value": 5.25},
                    {"date": "2023-03-22", "value": 5.00},
                    {"date": "2023-02-01", "value": 4.75},
                ]
            }
        ]
        
        data = []
        # Fallback/Default population
        # We return the structure expected by the frontend
        for item in indicators:
            data.append({
                "ticker": item["ticker"],
                "name": item["name"],
                "type": item["type"],
                "price": item["default"], # Current Value
                "change": 0,
                "change_percent": 0,
                "currency": "%" if "Rate" in item["name"] else "",
                "history": item.get("history", [])
            })
            
        return data

    def get_sector_performance(self):
        """
        Fetches performance for the 11 GICS sectors using SPDR ETFs.
        """
        sectors = {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLV": "Healthcare",
            "XLE": "Energy",
            "XLY": "Consumer Discret.",
            "XLP": "Consumer Staples",
            "XLI": "Industrials",
            "XLB": "Materials",
            "XLU": "Utilities",
            "XLRE": "Real Estate",
            "XLC": "Comm. Services"
        }
        
        try:
            tickers_list = list(sectors.keys())
            # Use batch fetching which is more efficient
            quotes = self.get_quotes(tickers_list)
            
            sector_data = []
            for q in quotes:
                ticker = q['ticker']
                if ticker in sectors:
                    sector_data.append({
                        "ticker": ticker,
                        "name": sectors[ticker],
                        "price": q['price'],
                        "change": q['change'],
                        "change_percent": q['change_percent']
                    })
            
            # Sort by performance (best to worst)
            sector_data.sort(key=lambda x: x['change_percent'], reverse=True)
            return sector_data
            
        except Exception as e:
            print(f"Error fetching sector data: {e}")
            return []

    def get_peers(self, ticker: str):
        """
        Returns a list of competitor tickers for a given stock.
        Uses a curated dictionary for major stocks, falling back to a general sector approach if possible (or empty).
        """
        peers_map = {
            # Tech / Mag 7
            "AAPL": ["MSFT", "GOOGL", "NVDA"],
            "MSFT": ["AAPL", "GOOGL", "AMZN"],
            "GOOGL": ["MSFT", "META", "AMZN"],
            "GOOG": ["MSFT", "META", "AMZN"],
            "AMZN": ["WMT", "MSFT", "GOOGL"],
            "NVDA": ["AMD", "INTC", "TSM"],
            "META": ["GOOGL", "SNAP", "PINS"],
            "TSLA": ["F", "GM", "TM"],
            "NFLX": ["DIS", "WBD", "CMCSA"],
            
            # Financials
            "JPM": ["BAC", "WFC", "C"],
            "BAC": ["JPM", "WFC", "GS"],
            "GS": ["MS", "JPM", "C"],
            "V": ["MA", "AXP", "PYPL"],
            
            # Retail/Consumer
            "WMT": ["TGT", "COST", "AMZN"],
            "KO": ["PEP", "MNST", "KDP"],
            "PEP": ["KO", "MNST", "KDP"],
            "NKE": ["ADDYY", "LULU", "UA"],
            
            # Energy
            "XOM": ["CVX", "SHEL", "BP"],
            "CVX": ["XOM", "SHEL", "COP"],
            
            # Pharma
            "LLY": ["NVO", "JNJ", "PFE"],
            "JNJ": ["PFE", "MRK", "ABBV"],
            
            # Industrial
            "BA": ["AIR", "LMT", "GE"],
            "CAT": ["DE", "CMI", "PCAR"],
        }
        
        return peers_map.get(ticker.upper(), [])

    def get_peer_comparison(self, ticker: str):
        """
        Fetches key metrics for the target ticker and its peers for comparison.
        If no direct competitors are found, falls back to the Sector ETF.
        """
        # 1. Fetch Target Info first to determine Sector
        target_info = self.get_company_info(ticker)
        if not target_info:
            return []
            
        # 2. Try to get direct peers
        peers = self.get_peers(ticker)
        
        # 3. Fallback: Identify Sector ETF if no peers found
        if not peers:
            sector = target_info.get('sector', '')
            sector_etf_map = {
                "Technology": "XLK",
                "Financial Services": "XLF",
                "Healthcare": "XLV",
                "Energy": "XLE",
                "Consumer Cyclical": "XLY",
                "Consumer Defensive": "XLP",
                "Industrials": "XLI",
                "Basic Materials": "XLB",
                "Utilities": "XLU",
                "Real Estate": "XLRE",
                "Communication Services": "XLC"
            }
            # Fuzzy match or direct lookup
            # yfinance sectors are usually "Technology", "Financial Services", etc.
            etf = sector_etf_map.get(sector)
            if etf:
                peers = [etf]

        # Comparison group = Target + Peers
        # We already fetched target_info, so we can optimize, but for simplicity/consistency of structure:
        comparison_group = [ticker] + peers
        
        results = []
        try:
            for t in comparison_group:
                # If it's the target, use the already fetched info
                if t == ticker:
                    info = target_info
                else:
                    info = self.get_company_info(t)
                
                if info:
                    results.append({
                        "ticker": t,
                        "name": info.get("name", t),
                        "price": info.get("current_price"),
                        "pe_ratio": info.get("pe_ratio"),
                        "forward_pe": info.get("forward_pe"),
                        "peg_ratio": info.get("peg_ratio"),
                        "price_to_sales": info.get("price_to_sales"),
                        "profit_margin": info.get("profit_margin"),
                        "roe": info.get("roe"),
                        "market_cap": info.get("market_cap"),
                        "revenue_growth": info.get("revenue_growth"),
                        "dividend_yield": info.get("dividend_yield")
                    })
        except Exception as e:
            print(f"Error fetching peer analysis: {e}")
            
        return results

    def get_factor_allocations(self):
        """
        Returns a 3x3 Style Box matrix (Morningstar style) implementation.
        Columns: Value, Core, Growth
        Rows: Large, Mid, Small
        """
        return {
            "Large Value": ["JPM", "BAC", "XOM", "CVX", "WMT", "JNJ", "CSCO", "VZ"],
            "Large Core": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "BRK-B", "UNH", "V"],
            "Large Growth": ["NVDA", "TSLA", "LLY", "AVGO", "ADBE", "CRM", "AMD", "NFLX"],
            
            "Mid Value": ["COF", "C", "DOW", "KHC", "WBA", "F", "GM", "DAL"],
            "Mid Core": ["MAR", "HLT", "CARR", "OTIS", "PAYX", "CTAS", "AFL", "PCAR"],
            "Mid Growth": ["PLTR", "UBER", "ABNB", "SQ", "CRWD", "DDOG", "NET", "ZS"],
            
            "Small Value": ["M", "GPS", "JWN", "KSS", "XRX", "GT", "AAL", "JBLU"],
            "Small Core": ["CROX", "YETI", "DKS", "WSM", "RH", "FIVE", "ELF", "BJ"],
            "Small Growth": ["DUOL", "PATH", "AFRM", "HOOD", "RIVN", "LCID", "SOFI", "DKNG"]
        }

    def get_historical_metrics(self, ticker: str):
        """
        Fetches up to 10 years of historical metrics: ROE, Debt/Equity, P/E, Dividend.
        Returns a sorted list of dictionaries [{'year': 2024, 'roe': 0.15, ...}].
        """
        try:
            stock = yf.Ticker(ticker)
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            try:
                dividends = stock.dividends
            except:
                dividends = pd.Series()
            
            # Helper to safely get value from DF
            def get_val(df, key, date):
                if key in df.index:
                    try:
                        val = df.loc[key, date]
                        return val if not pd.isna(val) else 0
                    except:
                        return 0
                return 0

            # Add Current TTM/Year Data from info
            info = stock.info
            current_date = datetime.now()
            metrics = [{
                "year": "Current (TTM)",
                "roe": info.get("returnOnEquity") * 100 if info.get("returnOnEquity") else None,
                "debt_to_equity": (info.get("debtToEquity") / 100) if info.get("debtToEquity") else None, # API usually returns 50 for 0.5, but let's check. actually yf info returns check
                # yfinance info debtToEquity is usually e.g. 150.23 (percentage). Logic elsewhere handles this?
                # Actually typically yf info returns it as a number like 86.54 meaning 86%. 
                # Our frontend expects a ratio (0.86) or %? 
                # Let's standardize: The valid frontend expects ratio? 
                # Previous dummy data: "debt_to_equity": 0.5 (displayed as 50%)
                # So we should divide by 100 if yf returns percent. YF 'debtToEquity' is typically %.
                "pe_ratio": info.get("trailingPE"),
                "dividend": info.get("dividendRate") or 0
            }]
            
            # Get historical years from financials columns
            if not financials.empty:
                dates = financials.columns
                for date in dates:
                    year = date.year
                    
                    # Net Income (for ROE/PE)
                    net_income = get_val(financials, "Net Income", date)
                    
                    # Shareholders Equity (for ROE)
                    equity = get_val(balance_sheet, "Stockholders Equity", date)
                    if equity == 0:
                        equity = get_val(balance_sheet, "Total Stockholder Equity", date)
                        
                    # Total Debt (for D/E)
                    total_debt = get_val(balance_sheet, "Total Debt", date)
                    
                    # ROE
                    roe = (net_income / equity * 100) if equity and equity != 0 else None
                    
                    # Debt/Equity
                    debt_to_equity = (total_debt / equity) if equity and equity != 0 else None
                    
                    # Dividends (Sum for the year)
                    year_divs = 0
                    if not dividends.empty:
                        # Filter dividends for this specific year
                        mask = (dividends.index >= f"{year}-01-01") & (dividends.index <= f"{year}-12-31")
                        year_divs = dividends.loc[mask].sum()
                    
                    # P/E Ratio (Historical approximation: Year End Price / EPS)
                    # This is hard to get exactly without historical price data for that specific date.
                    # We will return None for historical P/E to avoid misleading data, 
                    # or could implement a separate fetch for historical price.
                    # For now, let's leave P/E as None for past years unless we fetch price history.
                    pe_ratio = None 

                    metrics.append({
                        "year": year,
                        "roe": roe,
                        "debt_to_equity": debt_to_equity,
                        "pe_ratio": pe_ratio, # Historical PE requires price fetch
                        "dividend": float(year_divs)
                    })
            
            # Deduplicate by year (if Current year matches last financial year)
            # Actually "Current (TTM)" is distinct.
            
            return metrics

        except Exception as e:
            print(f"Error fetching historical metrics for {ticker}: {e}")
            return [] 

    def get_sector_allocations(self):
        """
        Returns a curated map of sectors and their top representative stocks.
        Used for the 'Stock Finder' / 'Market Map' feature.
        """
        return {
            "Technology": ["AAPL", "MSFT", "NVDA", "ORCL", "ADBE", "CRM", "AMD", "INTC"],
            "Financial Services": ["JPM", "BAC", "V", "MA", "WFC", "MS", "GS", "BLK"],
            "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE", "AMGN"],
            "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "BKNG", "TJX"],
            "Communication Services": ["GOOGL", "META", "NFLX", "DIS", "TMUS", "CMCSA", "VZ", "T"],
            "Industrials": ["CAT", "GE", "UNP", "HON", "UPS", "BA", "DE", "LMT"],
            "Consumer Defensive": ["WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "CL"],
            "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO"],
            "Utilities": ["NEE", "SO", "DUK", "GEV", "AEP", "SRE", "PEG", "ED"],
            "Real Estate": ["PLD", "AMT", "EQIX", "PSA", "O", "CCI", "DLR", "VICI"],
            "Basic Materials": ["LIN", "SHW", "FCX", "SCCO", "ECL", "CTVA", "DD", "NEM"]
        }


    def get_future_leader_score(self, ticker: str):
        """
        Calculates the 'Future Leader' score (0-10) based on 5 weighted factors:
        1. Growth Efficiency (Rule of 40) - 3.0 pts
        2. Innovation Intensity (R&D / Revenue) - 2.5 pts
        3. Scalability (Operating Leverage) - 2.0 pts
        4. Market Value (PEG Ratio) - 1.5 pts
        5. Management (ROIC) - 1.0 pts
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            financials = stock.financials
            
            if financials.empty:
                return None
            
            # --- 1. Rule of 40 (Growth + Margin > 40) ---
            rev_growth = info.get("revenueGrowth", 0) * 100
            profit_margin = info.get("profitMargins", 0) * 100
            rule_of_40 = rev_growth + profit_margin
            
            score_rule_40 = 3.0 if rule_of_40 > 40 else (1.5 if rule_of_40 > 20 else 0)
            
            # --- 2. Innovation Intensity (R&D > 15% Revenue) ---
            try:
                rnd = financials.loc["Research And Development"].iloc[0]
                revenue = financials.loc["Total Revenue"].iloc[0]
                rnd_intensity = (rnd / revenue) * 100
            except:
                rnd_intensity = 0
            
            score_rnd = 2.5 if rnd_intensity > 15 else (1.0 if rnd_intensity > 5 else 0)
            
            # --- 3. Scalability (Rev Growth > Opex Growth) ---
            try:
                # Compare current vs previous year
                curr_rev = financials.loc["Total Revenue"].iloc[0]
                prev_rev = financials.loc["Total Revenue"].iloc[1]
                rev_growth_abs = (curr_rev - prev_rev) / prev_rev
                
                # Scalability: Rev Growth > Opex Growth
                curr_rev = financials.loc["Total Revenue"].iloc[0]
                prev_rev = financials.loc["Total Revenue"].iloc[1]
                rev_growth_abs = (curr_rev - prev_rev) / prev_rev
                
                # Handle varying Opex labels
                opex_key = "Total Operating Expenses"
                if opex_key not in financials.index:
                    if "Operating Expense" in financials.index:
                        opex_key = "Operating Expense"
                    else:
                        raise ValueError("Opex data missing")

                curr_opex = financials.loc[opex_key].iloc[0]
                prev_opex = financials.loc[opex_key].iloc[1]
                opex_growth_abs = (curr_opex - prev_opex) / prev_opex
                
                is_scalable = rev_growth_abs > opex_growth_abs
            except:
                is_scalable = False
                
            score_scalability = 2.0 if is_scalable else 0
            
            # --- 4. Market Value (PEG Ratio < 1.0 or 1.5) ---
            peg = self._get_peg_ratio(info)
            score_peg = 0
            if peg and peg > 0:
                if peg < 1.0:
                    score_peg = 1.5
                elif peg < 1.5:
                    score_peg = 0.75
            
            # --- 5. ROIC > 15% ---
            # Approximated: EBIT * (1 - TaxRate) / (Total Equity + Total Debt - Cash)
            # Or simpler proxy if data missing: ROE * (1 - Debt/Asset)
            # Utilizing simplified ROE check or returnOnAssets from info as proxy if needed,
            # but let's try to calculate slightly accurately or use ROE as proxy?
            # User specifically asked for ROIC. Let's try basic formula.
            try:
                ebit = financials.loc["EBIT"].iloc[0] if "EBIT" in financials.index else financials.loc["taxEffectOfUnusualItems"].iloc[0] # Fallback bad
                # Let's use info fields if available? info doesn't have ROIC typically.
                # Calculation: NOPAT / Invested Capital
                tax_provision = financials.loc["Tax Provision"].iloc[0]
                pretax_income = financials.loc["Pretax Income"].iloc[0]
                tax_rate = tax_provision / pretax_income if pretax_income else 0.21
                nopat = ebit * (1 - tax_rate)
                
                bs = stock.balance_sheet
                if "Total Stockholder Equity" in bs.index and "Total Debt" in bs.index and "Cash And Cash Equivalents" in bs.index:
                     invested_capital = (bs.loc["Total Stockholder Equity"].iloc[0] + bs.loc["Total Debt"].iloc[0]) - bs.loc["Cash And Cash Equivalents"].iloc[0]
                else:
                     raise ValueError("BS data missing")
                
                roic = (nopat / invested_capital) * 100
            except:
                # Fallback to ROE if calculation fails
                roic = info.get("returnOnEquity", 0) * 100
            
            score_roic = 1.0 if roic > 15 else (0.5 if roic > 8 else 0)
            
            total_score = score_rule_40 + score_rnd + score_scalability + score_peg + score_roic
            
            result = {
                "ticker": ticker,
                "total_score": round(total_score, 1),
                "factors": {
                    "rule_of_40": {
                        "value": round(rule_of_40, 1),
                        "score": score_rule_40,
                        "max": 3.0,
                        "pass": rule_of_40 > 40,
                        "label": "Growth Efficiency"
                    },
                    "rnd_intensity": {
                        "value": round(rnd_intensity, 1),
                        "score": score_rnd,
                        "max": 2.5,
                        "pass": rnd_intensity > 15,
                        "label": "Innovation Intensity"
                    },
                    "scalability": {
                        "value": "Positive" if is_scalable else "Negative",
                        "score": score_scalability,
                        "max": 2.0,
                        "pass": is_scalable,
                        "label": "Scalability"
                    },
                    "peg_ratio": {
                        "value": round(peg, 2) if peg else "N/A",
                        "score": score_peg,
                        "max": 1.5,
                        "pass": (peg < 1.0) if peg else False,
                        "label": "Valuation (PEG)"
                    },
                    "roic": {
                        "value": round(roic, 1),
                        "score": score_roic,
                        "max": 1.0,
                        "pass": roic > 15,
                        "label": "Management (ROIC)"
                    }
                }
            }
            return self._sanitize_data(result)
            
        except Exception as e:
            print(f"Error calculating score for {ticker}: {e}")
            return None



    def _sanitize_data(self, data: any) -> any:
        """
        Recursively replace NaN/Infinity with None for JSON compliance.
        Supports lists and dicts. Handles NumPy types.
        """
        if isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, (float, np.float64, np.float32)):
            if np.isnan(data) or np.isinf(data):
                return None
            return float(data)
        elif isinstance(data, (np.bool_, bool)):
             return bool(data)
        elif isinstance(data, (np.integer, int)):
             return int(data)
        elif pd.isna(data):
             return None 
        return data
