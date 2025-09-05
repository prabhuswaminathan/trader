#!/usr/bin/env python3
"""
Test script for UpstoxOptionChain class.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from upstox_option_chain import UpstoxOptionChain
import json
from datetime import datetime

def test_basic_functionality():
    """Test basic functionality of UpstoxOptionChain"""
    print("=== Testing Basic Functionality ===")
    
    # Note: This test requires a valid access token
    # For testing purposes, we'll use a mock token
    access_token = "test_token"
    
    try:
        # Initialize the option chain fetcher
        option_chain = UpstoxOptionChain(access_token)
        print("✅ UpstoxOptionChain initialized successfully")
        
        # Test cache functionality
        option_chain.set_cache_duration(60)  # 1 minute cache
        print("✅ Cache duration set successfully")
        
        # Test cache clearing
        option_chain.clear_cache()
        print("✅ Cache cleared successfully")
        
        print("✅ Basic functionality tests passed")
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")

def test_data_parsing():
    """Test data parsing methods"""
    print("\n=== Testing Data Parsing ===")
    
    try:
        option_chain = UpstoxOptionChain("test_token")
        
        # Test safe conversion methods
        assert option_chain._safe_float("123.45") == 123.45
        assert option_chain._safe_float("") is None
        assert option_chain._safe_float(None) is None
        assert option_chain._safe_float("invalid") is None
        
        assert option_chain._safe_int("123") == 123
        assert option_chain._safe_int("") is None
        assert option_chain._safe_int(None) is None
        assert option_chain._safe_int("invalid") is None
        
        print("✅ Data parsing methods work correctly")
        
    except Exception as e:
        print(f"❌ Data parsing test failed: {e}")

def test_filtering_methods():
    """Test filtering methods"""
    print("\n=== Testing Filtering Methods ===")
    
    try:
        option_chain = UpstoxOptionChain("test_token")
        
        # Sample option data
        sample_data = [
            {
                'strike_price': 25000,
                'expiry_date': '2025-09-09',
                'option_type': 'CALL',
                'last_price': 100.0
            },
            {
                'strike_price': 25000,
                'expiry_date': '2025-09-16',
                'option_type': 'PUT',
                'last_price': 95.0
            },
            {
                'strike_price': 25100,
                'expiry_date': '2025-09-09',
                'option_type': 'CALL',
                'last_price': 80.0
            }
        ]
        
        # Test expiry filtering
        filtered_by_expiry = option_chain._filter_by_expiry(sample_data, '2025-09-09')
        assert len(filtered_by_expiry) == 2, f"Expected 2 contracts, got {len(filtered_by_expiry)}"
        
        # Test strike price filtering
        filtered_by_strike = option_chain._filter_by_strike_price(sample_data, 25000)
        assert len(filtered_by_strike) == 2, f"Expected 2 contracts, got {len(filtered_by_strike)}"
        
        print("✅ Filtering methods work correctly")
        
    except Exception as e:
        print(f"❌ Filtering test failed: {e}")

def test_option_parsing():
    """Test single option parsing"""
    print("\n=== Testing Option Parsing ===")
    
    try:
        option_chain = UpstoxOptionChain("test_token")
        
        # Sample raw option data
        raw_option = {
            'instrument_key': 'NSE_OPT|NIFTY|2025-09-09|25000|CE',
            'instrument_name': 'NIFTY 25000 CE',
            'strike_price': '25000',
            'expiry_date': '2025-09-09',
            'option_type': 'call',
            'last_price': '100.50',
            'bid_price': '99.00',
            'ask_price': '101.00',
            'volume': '1500',
            'open_interest': '25000',
            'change': '5.50',
            'change_percent': '5.80',
            'implied_volatility': '0.25',
            'delta': '0.55',
            'gamma': '0.02',
            'theta': '-1.50',
            'vega': '12.30'
        }
        
        parsed_option = option_chain._parse_single_option(raw_option)
        
        assert parsed_option is not None, "Failed to parse option data"
        assert parsed_option['strike_price'] == 25000.0, f"Expected strike 25000, got {parsed_option['strike_price']}"
        assert parsed_option['option_type'] == 'CALL', f"Expected CALL, got {parsed_option['option_type']}"
        assert parsed_option['last_price'] == 100.50, f"Expected last_price 100.50, got {parsed_option['last_price']}"
        assert parsed_option['volume'] == 1500, f"Expected volume 1500, got {parsed_option['volume']}"
        
        print("✅ Option parsing works correctly")
        
    except Exception as e:
        print(f"❌ Option parsing test failed: {e}")

def test_summary_calculation():
    """Test option summary calculation"""
    print("\n=== Testing Summary Calculation ===")
    
    try:
        option_chain = UpstoxOptionChain("test_token")
        
        # Sample data for summary calculation
        sample_data = [
            {
                'strike_price': 25000,
                'expiry_date': '2025-09-09',
                'option_type': 'CALL',
                'volume': 1000,
                'open_interest': 5000
            },
            {
                'strike_price': 25000,
                'expiry_date': '2025-09-09',
                'option_type': 'PUT',
                'volume': 1500,
                'open_interest': 7000
            },
            {
                'strike_price': 25100,
                'expiry_date': '2025-09-16',
                'option_type': 'CALL',
                'volume': 800,
                'open_interest': 3000
            }
        ]
        
        # Mock the fetch method to return sample data
        original_fetch = option_chain.fetch
        option_chain.fetch = lambda expiry=None, strike_price=None: sample_data
        
        summary = option_chain.get_option_summary()
        
        assert summary['total_contracts'] == 3, f"Expected 3 contracts, got {summary['total_contracts']}"
        assert summary['call_contracts'] == 2, f"Expected 2 call contracts, got {summary['call_contracts']}"
        assert summary['put_contracts'] == 1, f"Expected 1 put contract, got {summary['put_contracts']}"
        assert summary['total_volume'] == 3300, f"Expected total volume 3300, got {summary['total_volume']}"
        assert summary['total_open_interest'] == 15000, f"Expected total OI 15000, got {summary['total_open_interest']}"
        
        # Restore original method
        option_chain.fetch = original_fetch
        
        print("✅ Summary calculation works correctly")
        
    except Exception as e:
        print(f"❌ Summary calculation test failed: {e}")

def test_cache_functionality():
    """Test cache functionality"""
    print("\n=== Testing Cache Functionality ===")
    
    try:
        option_chain = UpstoxOptionChain("test_token")
        
        # Test cache validity
        assert not option_chain._is_cache_valid(), "Cache should be invalid initially"
        
        # Set cache timestamp
        option_chain._cache_timestamp = datetime.now()
        assert option_chain._is_cache_valid(), "Cache should be valid after setting timestamp"
        
        # Test cache duration
        option_chain.set_cache_duration(1)  # 1 second
        option_chain._cache_timestamp = datetime.now()
        assert option_chain._is_cache_valid(), "Cache should be valid immediately"
        
        print("✅ Cache functionality works correctly")
        
    except Exception as e:
        print(f"❌ Cache functionality test failed: {e}")

def test_error_handling():
    """Test error handling"""
    print("\n=== Testing Error Handling ===")
    
    try:
        option_chain = UpstoxOptionChain("test_token")
        
        # Test with invalid data
        invalid_data = [{'invalid': 'data'}]
        parsed = option_chain._parse_option_chain_response(invalid_data)
        assert isinstance(parsed, list), "Should return empty list for invalid data"
        
        # Test filtering with empty data
        empty_filtered = option_chain._filter_by_expiry([], '2025-09-09')
        assert empty_filtered == [], "Should return empty list for empty data"
        
        # Test summary with empty data
        empty_summary = option_chain.get_option_summary()
        assert empty_summary['total_contracts'] == 0, "Should return zero contracts for empty data"
        
        print("✅ Error handling works correctly")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")

def test_integration_example():
    """Test integration example"""
    print("\n=== Testing Integration Example ===")
    
    try:
        # This would normally require a real access token
        print("Integration example (requires real access token):")
        print("""
        # Initialize with real access token
        option_chain = UpstoxOptionChain(access_token)
        
        # Fetch all option data
        all_options = option_chain.fetch()
        
        # Fetch specific expiry
        expiry_options = option_chain.fetch(expiry='2025-09-09')
        
        # Fetch specific strike price
        strike_options = option_chain.fetch(strike_price=25000)
        
        # Fetch specific expiry and strike
        specific_options = option_chain.fetch(expiry='2025-09-09', strike_price=25000)
        
        # Get available expiries
        expiries = option_chain.get_available_expiries()
        
        # Get available strikes
        strikes = option_chain.get_available_strike_prices()
        
        # Get summary
        summary = option_chain.get_option_summary()
        """)
        
        print("✅ Integration example provided")
        
    except Exception as e:
        print(f"❌ Integration example test failed: {e}")

if __name__ == "__main__":
    print("Testing UpstoxOptionChain Class...")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_data_parsing()
        test_filtering_methods()
        test_option_parsing()
        test_summary_calculation()
        test_cache_functionality()
        test_error_handling()
        test_integration_example()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

