
import requests
import json
import os
import time

# List from generate_govt_contracts.py + some manual ones
KNOWN_GOVT_CONTRACTORS = {
    "LMT": "Lockheed Martin",
    "RTX": "Raytheon Technologies", 
    "GD": "General Dynamics",
    "NOC": "Northrop Grumman",
    "BA": "Boeing",
    "HII": "Huntington Ingalls",
    "LHX": "L3Harris",
    "KTOS": "Kratos Defense",
    "AVAV": "AeroVironment",
    "LDOS": "Leidos", 
    "BAH": "Booz Allen Hamilton",
    "SAIC": "SAIC",
    "CACI": "CACI International",
    "TXT": "Textron",
    "BWXT": "BWX Technologies",
    "VEC": "V2X",
    "CW": "Curtiss-Wright",
    "HEI": "Heico",
    "TDG": "TransDigm",
    "SPR": "Spirit AeroSystems",
    "GE": "General Electric",
    "HON": "Honeywell",
    "PLTR": "Palantir"
}

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "../app/data/uei_mapping.json")

def build_mapping():
    mapping = {}
    print(f"Building UEI mapping for {len(KNOWN_GOVT_CONTRACTORS)} companies...")

    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

    for ticker, name in KNOWN_GOVT_CONTRACTORS.items():
        print(f"  Searching for {ticker} ({name})...", end="", flush=True)
        
        payload = {
            "filters": {
                "keywords": [name],
                "award_type_codes": ["A", "B", "C", "D"]
            },
            "fields": ["Recipient Name", "Recipient UEI", "Award Amount"],
            "limit": 5, # Check top 5 biggest awards
            "sort": "Award Amount",
            "order": "desc"
        }

        try:
            res = requests.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                
                if results:
                    # Pick the UEI from the largest award
                    top_match = results[0]
                    uei = top_match.get("Recipient UEI")
                    recipient_name = top_match.get("Recipient Name")
                    
                    if uei:
                        mapping[ticker] = {
                            "uei": uei,
                            "name": recipient_name, # Store the official govt name
                            "search_term": name
                        }
                        print(f" Found: {uei} ({recipient_name})")
                    else:
                        print(" No UEI in top result.")
                else:
                    print(" No results found.")
            else:
                print(f" Error: {res.status_code}")
                
        except Exception as e:
            print(f" Exception: {e}")
        
        # Rate limit
        time.sleep(0.5)

    print(f"\nSaving mapping to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(mapping, f, indent=2)
    print("Done.")

if __name__ == "__main__":
    build_mapping()
