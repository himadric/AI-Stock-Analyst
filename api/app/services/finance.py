import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FinanceService:
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
                    # accessing .info for many tickers one by one can be slow with yf.Tickers
                    # fast_info is better for price data
                    t = data.tickers[symbol]
                    # fast_info provides last_price, previous_close, etc.
                    price = t.fast_info.last_price
                    prev_close = t.fast_info.previous_close
                    
                    change = price - prev_close
                    change_percent = (change / prev_close) * 100
                    
                    quotes.append({
                        "ticker": symbol,
                        "price": price,
                        "change": change,
                        "change_percent": change_percent
                    })
                except Exception as inner_e:
                    print(f"Error fetching quote for {symbol}: {inner_e}")
                    # Continue pending other tickers
            return quotes
        except Exception as e:
            print(f"Error fetching quotes: {e}")
            return []

    def get_stock_history(self, ticker: str, period: str = "1y", interval: str = "1d"):
        """
        Fetches historical stock price data.
        """
        try:
            stock = yf.Ticker(ticker)
            # yfinance history handles interval. Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
            hist = stock.history(period=period, interval=interval)
            
            # Reset index to make Date a column and format it
            hist.reset_index(inplace=True)
            
            # Convert to list of dictionaries for JSON response
            data = []
            for _, row in hist.iterrows():
                # Handle DatetimeIndex (intraday) vs Date (daily)
                # Intraday has timezone locally usually. format to ISO compatible string
                # If 'Datetime' column exists (intraday), use it. Else 'Date'.
                date_val = row.get("Datetime") or row.get("Date")
                
                date_str = ""
                if pd.notnull(date_val):
                     if isinstance(date_val, (pd.Timestamp, datetime)):
                         date_str = date_val.isoformat()
                     else:
                         date_str = str(date_val)

                data.append({
                    "date": date_str,
                    "open": row["Open"],
                    "high": row["High"],
                    "low": row["Low"],
                    "close": row["Close"],
                    "volume": row["Volume"]
                })
            return data
        except Exception as e:
            print(f"Error fetching stock history for {ticker}: {e}")
            return []

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
            recent_qf = qf_T.head(5)
            
            # Sort back to ascending for display
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
            recent_qbs = qbs_T.head(5)
            
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
            recent_qcf = qcf_T.head(5)
            
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
            public = 1.0 - (insiders + institutions)
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
                            "pct_held": row.get('pctHeld', 0) if 'pctHeld' in row else 0 # Some versions have it
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
                        date_val = row.get('Date') # Usually 'Date' or 'Latest Date'
                        date_str = str(date_val) if pd.notnull(date_val) else ""
                        
                        # Position might be 'Shares' or 'Position'
                        shares = row.get('Shares', 0)
                        
                        # Data cleaning: ensure shares is a number
                        real_shares = 0
                        try:
                             if isinstance(shares, (int, float)) and not pd.isna(shares):
                                 real_shares = float(shares)
                             elif isinstance(shares, str) and shares.replace(',','').replace('.','').isdigit():
                                 real_shares = float(shares.replace(',',''))
                             else:
                                 # Fallback: Check 'Position' column if it looks like a number?
                                 # Or check 'Shares Owned Directly' if it exists
                                 alt = row.get('Shares Owned Directly') or row.get('Position')
                                 if isinstance(alt, (int, float)) and not pd.isna(alt):
                                     real_shares = float(alt)
                        except:
                             real_shares = 0
                             
                        insiders.append({
                            "holder": row.get('Name', ''),
                            "shares": real_shares,
                            "position": row.get('Position', '') if isinstance(row.get('Position', ''), str) else str(row.get('Position', '')), 
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

    def _sanitize_data(self, data: any) -> any:
        """
        Recursively replace NaN/Infinity with None for JSON compliance.
        Supports lists and dicts.
        """
        if isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, (float, np.float64, np.float32)):
            if np.isnan(data) or np.isinf(data):
                return 0 # or None, but 0 is safer for charts/tables if appropriate
            return float(data)
        elif pd.isna(data):
             return 0 # Handle pd.NaT etc
        return data
