#!/usr/bin/env python3
"""
Example usage of Utils class for trading operations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from utils import Utils
from datetime import datetime

def main():
    """Main example function"""
    print("Utils Class Usage Examples")
    print("=" * 50)
    
    # Example 1: Get next weekly expiry (as requested)
    print("\n1. Next Weekly Expiry (Thursday)")
    print("-" * 30)
    for i in range(5):
        expiry = Utils.get_next_weekly_expiry(i)
        print(f"Next {i} weeks: {expiry}")
    
    # Example 2: Get next Tuesday expiry (as originally requested)
    print("\n2. Next Tuesday Expiry")
    print("-" * 30)
    for i in range(5):
        expiry = Utils.get_next_tuesday_expiry(i)
        print(f"Next {i} weeks (Tuesday): {expiry}")
    
    # Example 3: Get monthly expiries
    print("\n3. Monthly Expiries")
    print("-" * 30)
    current_date = datetime.now().date()
    for i in range(3):
        target_date = current_date + (i * 30)
        expiry = Utils.get_monthly_expiry(target_date.year, target_date.month)
        print(f"Monthly expiry {target_date.year}-{target_date.month:02d}: {expiry}")
    
    # Example 4: Get expiry series for option chain
    print("\n4. Expiry Series for Option Chain")
    print("-" * 30)
    weekly_series = Utils.get_expiry_series("weekly", 4)
    print(f"Weekly expiries: {weekly_series}")
    
    tuesday_series = Utils.get_expiry_series("tuesday", 4)
    print(f"Tuesday expiries: {tuesday_series}")
    
    # Example 5: Market hours and trading status
    print("\n5. Market Status")
    print("-" * 30)
    is_open = Utils.is_market_open()
    next_open = Utils.get_next_market_open()
    print(f"Market open now: {is_open}")
    print(f"Next market open: {next_open}")
    
    # Example 6: Strike price calculations
    print("\n6. Strike Price Calculations")
    print("-" * 30)
    nifty_price = 24567.89
    formatted_strike = Utils.format_strike_price(nifty_price)
    nearest_strikes = Utils.get_nearest_strikes(nifty_price, 10)
    
    print(f"NIFTY price: {nifty_price}")
    print(f"Formatted strike: {formatted_strike}")
    print(f"Nearest strikes: {nearest_strikes}")
    
    # Example 7: Expiry information and analysis
    print("\n7. Expiry Analysis")
    print("-" * 30)
    next_expiry = Utils.get_next_weekly_expiry(0)
    expiry_info = Utils.get_expiry_info(next_expiry)
    days_to_expiry = Utils.calculate_days_to_expiry(next_expiry)
    is_today = Utils.is_expiry_today(next_expiry)
    
    print(f"Next expiry: {next_expiry}")
    print(f"Days to expiry: {days_to_expiry}")
    print(f"Is expiry today: {is_today}")
    print(f"Expiry info: {expiry_info}")
    
    # Example 8: Practical trading scenario
    print("\n8. Practical Trading Scenario")
    print("-" * 30)
    print("Scenario: Setting up an Iron Condor for next week")
    
    # Get next week's expiry
    next_week_expiry = Utils.get_next_weekly_expiry(1)
    print(f"Target expiry: {next_week_expiry}")
    
    # Get strike prices around current level
    current_price = 24500.0
    strikes = Utils.get_nearest_strikes(current_price, 8)
    print(f"Available strikes around {current_price}: {strikes}")
    
    # Check if we can trade
    can_trade = Utils.is_market_open()
    if can_trade:
        print("✅ Market is open - can place trades now")
    else:
        print(f"⏰ Market is closed - next trading session: {Utils.get_next_market_open()}")
    
    # Calculate days to expiry
    days = Utils.calculate_days_to_expiry(next_week_expiry)
    print(f"Days to expiry: {days}")
    
    if days < 7:
        print("⚠️  Warning: Less than 7 days to expiry - high time decay risk")
    elif days < 14:
        print("⚠️  Caution: Less than 14 days to expiry - moderate time decay risk")
    else:
        print("✅ Good: More than 14 days to expiry - lower time decay risk")
    
    # Example 9: Multiple expiry analysis
    print("\n9. Multiple Expiry Analysis")
    print("-" * 30)
    print("Analyzing next 4 weekly expiries:")
    
    for i, expiry in enumerate(weekly_series):
        info = Utils.get_expiry_info(expiry)
        days = info['days_to_expiry']
        weekday = info['weekday']
        
        status = "TODAY" if info['is_today'] else f"{days} days"
        print(f"  {i+1}. {expiry} ({weekday}) - {status}")
    
    print("\n✅ All examples completed successfully!")

if __name__ == "__main__":
    main()

