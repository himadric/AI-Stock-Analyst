from app.services.finance import FinanceService
import json

def debug_ownership():
    finance = FinanceService()
    ticker = "UBER" 
    
    print(f"Fetching ownership details for {ticker}...")
    try:
        details = finance.get_ownership_details(ticker)
        print("Keys:", details.keys())
        
        print("\n--- Institutions ---")
        inst = details.get('institutions', [])
        print(f"Type: {type(inst)}")
        if isinstance(inst, list):
            print(f"Length: {len(inst)}")
            if len(inst) > 0:
                print("First item:", inst[0])
        else:
            print("Institutions is NOT a list:", inst)

        print("\n--- Insiders ---")
        insiders = details.get('insiders', [])
        print(f"Type: {type(insiders)}")
        if isinstance(insiders, list):
            print(f"Length: {len(insiders)}")
            if len(insiders) > 0:
                print("First item:", insiders[0])
        else:
            print("Insiders is NOT a list:", insiders)
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    debug_ownership()
