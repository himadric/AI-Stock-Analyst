import yfinance as yf
import json

try:
    ticker = "AAPL"
    stock = yf.Ticker(ticker)
    news = stock.news
    print(f"Total raw news items: {len(news)}")
    
    if len(news) > 0:
        item = news[0]
        print(f"Top level keys: {list(item.keys())}")
        if 'content' in item:
            print("Found 'content' key. Dumping content:")
            print(json.dumps(item['content'], indent=2))
        else:
            print("No 'content' key found. Dumping item:")
            print(json.dumps(item, indent=2))
except Exception as e:
    print(f"Error: {e}")
