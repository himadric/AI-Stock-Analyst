import numpy as np
import pandas as pd
import json
from app.services.finance import FinanceService

def test_sanitize():
    fs = FinanceService()
    
    test_cases = [
        {"name": "NaN float", "input": float('nan'), "expected": None},
        {"name": "Numpy NaN", "input": np.nan, "expected": None},
        {"name": "Infinity", "input": float('inf'), "expected": None},
        {"name": "Numpy Infinity", "input": np.inf, "expected": None},
        {"name": "Nested Dict", "input": {"a": 1, "b": np.nan}, "expected": {"a": 1, "b": None}},
        {"name": "Nested List", "input": [1, np.nan, 3], "expected": [1, None, 3]},
        {"name": "Pandas NA", "input": pd.NA, "expected": None},
        {"name": "Pandas NaT", "input": pd.NaT, "expected": None}, # Depending on handling
        {"name": "Mixed", "input": {"x": [np.nan, {"y": float('inf')}]}, "expected": {"x": [None, {"y": None}]}}
    ]

    print("Testing _sanitize_data...")
    failures = 0
    for case in test_cases:
        # Note: current implementation returns 0, so we might expect 0 or None depending on what we want.
        # But let's see what it DOES first.
        
        # We really want to know if it's JSON serializable.
        try:
            cleaned = fs._sanitize_data(case["input"])
            json.dumps(cleaned)
            print(f"[PASS] Serialized {case['name']}: {cleaned}")
        except Exception as e:
            print(f"[FAIL] Serialization failed for {case['name']}: {e}")
            failures += 1
            
    if failures == 0:
        print("\nAll cases serializable!")
    else:
        print(f"\n{failures} cases failed serialization.")
        
if __name__ == "__main__":
    test_sanitize()
