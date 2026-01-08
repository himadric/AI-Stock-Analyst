import requests
import json
from datetime import datetime, timedelta

def get_new_contracts(recipient_name, days=90):
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    print(f"Fetching contracts for {recipient_name} from {start_date} to {end_date}...")
    
    payload = {
        "filters": {
            "keywords": [recipient_name],
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "award_type_codes": ["A", "B", "C", "D"]
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Description", "Start Date"],
        "limit": 20,
        "page": 1,
        "sort": "Start Date",
        "order": "desc"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        if 'response' in locals():
             print(response.text)
        return None

if __name__ == "__main__":
    # Test with Lockheed Martin
    data = get_new_contracts("Lockheed Martin")
    
    if data and "results" in data:
        results = data["results"]
        total_awarded = sum(item.get("Award Amount", 0) for item in results)
        print(f"\nFound {len(results)} awards.")
        print(f"Total Amount (Top 20): ${total_awarded:,.2f}")
        
        for item in results[:5]:
            print(f" - {item.get('Start Date', 'N/A')}: ${item['Award Amount']:,.2f} | {item['Description']}")
    else:
        print("No results found.")
