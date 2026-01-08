
import sys
import os
import json

# Add api directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.finance import FinanceService

def verify_distribution(ticker="DUOL"):
    print(f"Verifying FinanceService.get_ownership for {ticker}...")
    service = FinanceService()
    ownership = service.get_ownership(ticker)
    
    if ownership:
        print("\nResult:")
        print(json.dumps(ownership, indent=2))
        
        total = ownership['insiders'] + ownership['institutions'] + ownership['public']
        print(f"\nTotal Sum: {total:.2f}%")
        
        if abs(total - 100.0) < 0.01:
            print("SUCCESS: Total sums to 100%")
        else:
            print(f"FAILURE: Total sums to {total}%")
    else:
        print("No ownership data returned.")

if __name__ == "__main__":
    verify_distribution()
