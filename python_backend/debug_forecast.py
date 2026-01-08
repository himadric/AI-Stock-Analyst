import yfinance as yf
import json

def test_analyst_data(ticker_symbol):
    print(f"--- Fetching Analyst Data for {ticker_symbol} ---")
    ticker = yf.Ticker(ticker_symbol)
    
    # 1. Recommendations / Consensus
    try:
        recommendations = ticker.recommendations
        print("\n[Recommendations Data Head]:")
        if recommendations is not None and not recommendations.empty:
            print(recommendations.tail())
        else:
            print("No recommendations data found.")
            
        # Summary (Strong Buy, Buy, etc.) often comes from 'recommendations_summary' or similar in newer yfinance versions
        # Let's check info dict for 'targetMeanPrice', 'targetHighPrice', etc.
        info = ticker.info
        print("\n[Info Dict Key Analyst Metrics]:")
        keys_to_check = [
            'targetHighPrice', 'targetLowPrice', 'targetMeanPrice', 'targetMedianPrice',
            'recommendationMean', 'recommendationKey', 'numberOfAnalystOpinions',
            'currentPrice'
        ]
        found_data = {k: info.get(k) for k in keys_to_check}
        print(json.dumps(found_data, indent=2))
        
    except Exception as e:
        print(f"Error fetching recommendations: {e}")

if __name__ == "__main__":
    test_analyst_data("UBER")
    test_analyst_data("AAPL")
