
import sys
import os
import json

# Add api directory to sys.path to resolve imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.finance import FinanceService

def verify_fix(ticker="AAPL"):
    print(f"Verifying FinanceService.get_ownership_details for {ticker}...")
    service = FinanceService()
    data = service.get_ownership_details(ticker)
    
    insiders = data.get("insiders", [])
    print(f"\nFound {len(insiders)} insiders.")
    
    if insiders:
        print("Top 3 Insiders:")
        for i, holder in enumerate(insiders[:3]):
            print(f"{i+1}. {holder['holder']} - Shares: {holder['shares']} - Date: {holder['date_reported']}")
            
        # Check if shares are non-zero
        zero_shares = [h for h in insiders if h['shares'] == 0]
        if len(zero_shares) < len(insiders):
             print("\nSUCCESS: Found non-zero insider shares.")
        else:
             print("\nFAILURE: All insider shares are still 0.")
    else:
        print("No insiders returned.")

    institutions = data.get("institutions", [])
    print(f"\nFound {len(institutions)} institutions.")
    if institutions:
        print("Top 3 Institutions:")
        for i, holder in enumerate(institutions[:3]):
             change_pct = holder.get('change_percent', 0)
             print(f"{i+1}. {holder['holder']} - Shares: {holder['shares']} - Change: {change_pct*100:.2f}%")
        
        # Verify change percent exists
        has_change = any(h.get('change_percent', 0) != 0 for h in institutions)
        if has_change:
             print("\nSUCCESS: Found non-zero institutional change %.")
        else:
             print("\nWARNING: All institutional change % are 0 (might be valid depending on data).")
    else:
        print("No institutions returned.")

if __name__ == "__main__":
    verify_fix()
