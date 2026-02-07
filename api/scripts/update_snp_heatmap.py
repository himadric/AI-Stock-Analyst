import sys
import os
import json
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pymongo import MongoClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add parent directory to path to import app modules if needed
api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(api_dir)

def update_snp_heatmap():
    print("Starting S&P 500 Heatmap Update...")

    # 1. Fetch S&P 500 Tickers from Wikipedia
    print("Fetching S&P 500 list from Wikipedia...")
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        tables = pd.read_html(response.text)
        df_snp = tables[0]
        tickers = df_snp['Symbol'].tolist()
        # Replace dots with dashes for yfinance (e.g. BRK.B -> BRK-B)
        tickers = [t.replace('.', '-') for t in tickers]
        # Map tickers to sectors for later
        sector_map = df_snp.set_index('Symbol')['GICS Sector'].to_dict()
        # Adjust keys in sector map to match yfinance tickers
        sector_map = {k.replace('.', '-'): v for k, v in sector_map.items()}
        
        print(f"Found {len(tickers)} tickers.")
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")
        sys.exit(1)

    # 2. Add SPY to the list for comparison baseline
    download_tickers = tickers + ['SPY']

    # 3. Download Historical Data (6 months)
    print("Downloading historical data using yfinance (this may take a while)...")
    start_date = (datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d')
    
    try:
        # Download 'Close' (Adj Close might be missing or auto-adjusted to Close)
        data = yf.download(download_tickers, start=start_date, progress=True)['Close']
        
        # Check if data is empty
        if data.empty:
            print("No data downloaded. Exiting.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error downloading yfinance data: {e}")
        sys.exit(1)
        
    print("Data download complete. Calculating metrics...")

    # 4. Calculate Relative Strength
    # Periods: 1m (21 trading days), 3m (63 trading days), 6m (126 trading days)
    # Relative Strength = (Stock_Return - SPY_Return)
    
    spy_data = data['SPY']
    
    heatmap_data = []
    
    # Get Market Caps separately (batch download info is slow, might need separate call or use Ticker object for loop)
    # yfinance batch download doesn't strictly provide market cap in the history dataframe.
    # We need to fetch market caps. Doing it for 500 tickers one-by-one is slow.
    # Optimization: Use yfinance Tickers object to fetch info, but it can still be slow. 
    # Alternative: For this MVP, we might skip live market cap or try to fetch it efficiently.
    # Let's try Tickers object for metadata. If too slow, we might need a fallback or just use cached if available.
    # Actually, for the heatmap "Size", market cap is crucial.
    # Let's try to fetch market caps via Tickers object.
    
    print("Fetching Market Caps (batch)...")
    tickers_obj = yf.Tickers(' '.join(tickers))
    
    for ticker in tickers:
        try:
            # Calculate Returns
            if ticker not in data.columns:
                print(f"Skipping {ticker}: No price data.")
                continue
                
            series = data[ticker].dropna()
            spy_series = spy_data.dropna()
            
            # Align dates
            common_dates = series.index.intersection(spy_series.index)
            series = series.loc[common_dates]
            spy_s = spy_series.loc[common_dates]
            
            if len(series) < 2:
                continue
                
            current_price = series.iloc[-1]
            
            # Helper for return calc
            def get_pct_change(days):
                if len(series) <= days:
                    return 0.0
                # pct_change is (new - old) / old
                stock_ret = (series.iloc[-1] - series.iloc[-1-days]) / series.iloc[-1-days]
                spy_ret = (spy_s.iloc[-1] - spy_s.iloc[-1-days]) / spy_s.iloc[-1-days]
                return stock_ret - spy_ret # Relative Strength (Difference in returns)

            rs_1m = get_pct_change(21)
            rs_3m = get_pct_change(63)
            rs_6m = get_pct_change(126)
            
            # Fetch Market Cap - access via logic that doesn't trigger full scraping for every ticker
            # yfinance's .info property triggers a web request per ticker.
            # This is slow for 500 tickers.
            # We will try to rely on fast_info if available or accept the slowness for the daily job.
            # Since this is a daily cron job, slowness (e.g. 5-10 mins) is acceptable.
            
            try:
                # Use fast_info for market cap (no extra request usually)
                # Note: yfinance Ticker object access
                t = tickers_obj.tickers[ticker]
                market_cap = t.fast_info.market_cap
            except Exception as e:
                # Fallback or 0
                market_cap = 0
            
            record = {
                "ticker": ticker,
                "sector": sector_map.get(ticker, "Unknown"),
                "current_price": float(current_price),
                "market_cap": float(market_cap),
                "relative_strength": {
                    "1m": float(rs_1m),
                    "3m": float(rs_3m),
                    "6m": float(rs_6m)
                },
                "last_updated": datetime.utcnow()
            }
            heatmap_data.append(record)
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue

    print(f"Processed {len(heatmap_data)} companies successfully.")

    # 5. Connect to MongoDB
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    if not uri:
        print("MONGO_URI not found in environment variables.")
        sys.exit(1)

    print("Connecting to MongoDB...")
    client = MongoClient(uri)
    db = client["ai_stock_analyst"]
    collection = db["snp_heatmap_data"]

    # 6. Upsert Data
    print("Upserting data to MongoDB...")
    
    # We can do bulk write for efficiency
    from pymongo import UpdateOne
    
    operations = []
    for item in heatmap_data:
        operations.append(
            UpdateOne(
                {"ticker": item["ticker"]},
                {"$set": item},
                upsert=True
            )
        )
        
    if operations:
        result = collection.bulk_write(operations)
        print(f"Bulk write result: Matched {result.matched_count}, Modified {result.modified_count}, Upserted {result.upserted_count}")
    
    print("S&P 500 Heatmap Update Finished.")

if __name__ == "__main__":
    update_snp_heatmap()
