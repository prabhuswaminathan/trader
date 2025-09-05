#!/usr/bin/env python3
"""
Test script for Utils class functions.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from utils import Utils
from datetime import datetime, date, timedelta

def test_weekly_expiry():
    """Test weekly expiry calculations"""
    print("=== Testing Weekly Expiry Calculations ===")
    
    try:
        # Test next 5 weekly expiries
        for i in range(5):
            expiry = Utils.get_next_weekly_expiry(i)
            print(f"Next {i} weeks: {expiry}")
            
            # Verify format
            assert len(expiry) == 10, f"Invalid date format: {expiry}"
            assert expiry.count('-') == 2, f"Invalid date format: {expiry}"
            
            # Verify it's a valid date
            parsed_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            assert parsed_date >= date.today(), f"Expiry date is in the past: {expiry}"
        
        print("✅ Weekly expiry calculations passed")
        
    except Exception as e:
        print(f"❌ Weekly expiry test failed: {e}")
        raise

def test_tuesday_expiry():
    """Test Tuesday expiry calculations"""
    print("\n=== Testing Tuesday Expiry Calculations ===")
    
    try:
        # Test next 5 Tuesday expiries
        for i in range(5):
            expiry = Utils.get_next_tuesday_expiry(i)
            print(f"Next {i} weeks (Tuesday): {expiry}")
            
            # Verify format
            assert len(expiry) == 10, f"Invalid date format: {expiry}"
            assert expiry.count('-') == 2, f"Invalid date format: {expiry}"
            
            # Verify it's a valid date
            parsed_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            assert parsed_date >= date.today(), f"Expiry date is in the past: {expiry}"
            
            # Verify it's a Tuesday (weekday 1)
            assert parsed_date.weekday() == 1, f"Expiry is not a Tuesday: {expiry} ({parsed_date.strftime('%A')})"
        
        print("✅ Tuesday expiry calculations passed")
        
    except Exception as e:
        print(f"❌ Tuesday expiry test failed: {e}")
        raise

def test_monthly_expiry():
    """Test monthly expiry calculations"""
    print("\n=== Testing Monthly Expiry Calculations ===")
    
    try:
        # Test current month and next 2 months
        current_date = date.today()
        for i in range(3):
            target_date = current_date + timedelta(days=30 * i)
            expiry = Utils.get_monthly_expiry(target_date.year, target_date.month)
            print(f"Monthly expiry {target_date.year}-{target_date.month:02d}: {expiry}")
            
            # Verify format
            assert len(expiry) == 10, f"Invalid date format: {expiry}"
            assert expiry.count('-') == 2, f"Invalid date format: {expiry}"
            
            # Verify it's a valid date
            parsed_date = datetime.strptime(expiry, "%Y-%m-%d").date()
            assert parsed_date >= date.today(), f"Expiry date is in the past: {expiry}"
        
        print("✅ Monthly expiry calculations passed")
        
    except Exception as e:
        print(f"❌ Monthly expiry test failed: {e}")
        raise

def test_expiry_series():
    """Test expiry series generation"""
    print("\n=== Testing Expiry Series ===")
    
    try:
        # Test weekly series
        weekly_series = Utils.get_expiry_series("weekly", 4)
        print(f"Weekly series: {weekly_series}")
        assert len(weekly_series) == 4, f"Expected 4 weekly expiries, got {len(weekly_series)}"
        
        # Test Tuesday series
        tuesday_series = Utils.get_expiry_series("tuesday", 4)
        print(f"Tuesday series: {tuesday_series}")
        assert len(tuesday_series) == 4, f"Expected 4 Tuesday expiries, got {len(tuesday_series)}"
        
        # Test monthly series
        monthly_series = Utils.get_expiry_series("monthly", 3)
        print(f"Monthly series: {monthly_series}")
        assert len(monthly_series) == 3, f"Expected 3 monthly expiries, got {len(monthly_series)}"
        
        print("✅ Expiry series tests passed")
        
    except Exception as e:
        print(f"❌ Expiry series test failed: {e}")
        raise

def test_market_hours():
    """Test market hours functionality"""
    print("\n=== Testing Market Hours ===")
    
    try:
        # Test current market status
        is_open = Utils.is_market_open()
        print(f"Market open now: {is_open}")
        
        # Test next market open
        next_open = Utils.get_next_market_open()
        print(f"Next market open: {next_open}")
        
        # Verify next market open is in the future
        assert next_open >= datetime.now(), "Next market open should be in the future"
        
        print("✅ Market hours tests passed")
        
    except Exception as e:
        print(f"❌ Market hours test failed: {e}")
        raise

def test_strike_price_formatting():
    """Test strike price formatting"""
    print("\n=== Testing Strike Price Formatting ===")
    
    try:
        # Test various prices
        test_prices = [24567.89, 25000.0, 25001.0, 24999.0, 24500.0]
        
        for price in test_prices:
            formatted = Utils.format_strike_price(price)
            print(f"Price {price} -> Strike {formatted}")
            
            # Verify it's a multiple of 50
            assert formatted % 50 == 0, f"Formatted price {formatted} is not a multiple of 50"
        
        # Test nearest strikes
        price = 24567.89
        strikes = Utils.get_nearest_strikes(price, 5)
        print(f"Nearest strikes for {price}: {strikes}")
        
        assert len(strikes) == 5, f"Expected 5 strikes, got {len(strikes)}"
        assert all(strike % 50 == 0 for strike in strikes), "All strikes should be multiples of 50"
        
        print("✅ Strike price formatting tests passed")
        
    except Exception as e:
        print(f"❌ Strike price formatting test failed: {e}")
        raise

def test_expiry_info():
    """Test expiry information functions"""
    print("\n=== Testing Expiry Information ===")
    
    try:
        # Test with next weekly expiry
        next_expiry = Utils.get_next_weekly_expiry(0)
        info = Utils.get_expiry_info(next_expiry)
        print(f"Expiry info for {next_expiry}: {info}")
        
        # Verify required fields
        required_fields = ['expiry_date', 'days_to_expiry', 'is_today', 'is_past', 'is_future', 'weekday']
        for field in required_fields:
            assert field in info, f"Missing field: {field}"
        
        # Test days to expiry calculation
        days = Utils.calculate_days_to_expiry(next_expiry)
        print(f"Days to expiry: {days}")
        assert days >= 0, f"Days to expiry should be non-negative: {days}"
        
        # Test is expiry today
        is_today = Utils.is_expiry_today(next_expiry)
        print(f"Is expiry today: {is_today}")
        
        print("✅ Expiry information tests passed")
        
    except Exception as e:
        print(f"❌ Expiry information test failed: {e}")
        raise

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n=== Testing Edge Cases ===")
    
    try:
        # Test negative weeks_ahead
        try:
            Utils.get_next_weekly_expiry(-1)
            assert False, "Should have raised ValueError for negative weeks_ahead"
        except ValueError:
            print("✅ Correctly raised ValueError for negative weeks_ahead")
        
        # Test invalid expiry type
        try:
            Utils.get_expiry_series("invalid", 1)
            assert False, "Should have raised ValueError for invalid expiry type"
        except ValueError:
            print("✅ Correctly raised ValueError for invalid expiry type")
        
        # Test invalid date format
        try:
            Utils.calculate_days_to_expiry("invalid-date")
            assert False, "Should have raised ValueError for invalid date format"
        except ValueError:
            print("✅ Correctly raised ValueError for invalid date format")
        
        print("✅ Edge case tests passed")
        
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        raise

def test_integration():
    """Test integration with real-world scenarios"""
    print("\n=== Testing Integration Scenarios ===")
    
    try:
        # Scenario 1: Get next 4 weekly expiries for option chain
        weekly_expiries = Utils.get_expiry_series("weekly", 4)
        print(f"Next 4 weekly expiries: {weekly_expiries}")
        
        # Scenario 2: Get strike prices around current NIFTY level
        nifty_price = 24500.0
        strikes = Utils.get_nearest_strikes(nifty_price, 10)
        print(f"Strikes around NIFTY {nifty_price}: {strikes}")
        
        # Scenario 3: Check if we can trade today
        can_trade = Utils.is_market_open()
        next_trading = Utils.get_next_market_open()
        print(f"Can trade today: {can_trade}")
        print(f"Next trading session: {next_trading}")
        
        # Scenario 4: Get expiry info for all upcoming expiries
        for i, expiry in enumerate(weekly_expiries):
            info = Utils.get_expiry_info(expiry)
            print(f"Expiry {i+1}: {expiry} ({info['days_to_expiry']} days, {info['weekday']})")
        
        print("✅ Integration tests passed")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise

if __name__ == "__main__":
    print("Testing Utils Class Functions...")
    print("=" * 50)
    
    try:
        test_weekly_expiry()
        test_tuesday_expiry()
        test_monthly_expiry()
        test_expiry_series()
        test_market_hours()
        test_strike_price_formatting()
        test_expiry_info()
        test_edge_cases()
        test_integration()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

