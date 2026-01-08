import yfinance as yf
import json

def check_news(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    news = ticker.news
    print(json.dumps(news, indent=2))

if __name__ == "__main__":
    check_news("ONON")
