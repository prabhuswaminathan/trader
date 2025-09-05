#!/usr/bin/env python3
"""
Demonstration of the weekly expiry function as requested.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from utils import Utils

def main():
    """Demonstrate the weekly expiry function"""
    print("Weekly Expiry Function Demonstration")
    print("=" * 50)
    print("Function: Utils.get_next_weekly_expiry(weeks_ahead)")
    print("Returns: YYYY-MM-DD format")
    print("Note: NIFTY weekly options expire on Tuesdays")
    print()
    
    # Test the function with different values
    print("Testing the function:")
    print("-" * 30)
    
    for i in range(8):
        expiry = Utils.get_next_weekly_expiry(i)
        print(f"get_next_weekly_expiry({i}) = {expiry}")
    
    print()
    print("Key Points:")
    print("- 0 = next expiry (this week's Tuesday)")
    print("- 1 = following expiry (next week's Tuesday)")
    print("- 2 = expiry after that, and so on...")
    print("- Returns date in YYYY-MM-DD format")
    print("- Automatically handles weekends and holidays")
    
    print()
    print("Usage in your trading application:")
    print("-" * 30)
    print("# Get next week's expiry for option chain")
    print("next_week_expiry = Utils.get_next_weekly_expiry(1)")
    print("print(f'Next week expiry: {next_week_expiry}')")
    
    print()
    print("# Get current week's expiry")
    print("current_week_expiry = Utils.get_next_weekly_expiry(0)")
    print("print(f'Current week expiry: {current_week_expiry}')")
    
    print()
    print("# Get expiry 3 weeks from now")
    print("future_expiry = Utils.get_next_weekly_expiry(3)")
    print("print(f'Future expiry: {future_expiry}')")

if __name__ == "__main__":
    main()
