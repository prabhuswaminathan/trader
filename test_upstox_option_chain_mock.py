#!/usr/bin/env python3
"""
Test script for UpstoxOptionChainMock class.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from upstox_option_chain_mock import UpstoxOptionChainMock
import json
from datetime import datetime

def test_basic_functionality():
    """Test basic functionality of UpstoxOptionChainMock"""
    print("=== Testing Basic Functionality ===")
    
    try:
        # Initialize the option chain fetcher
        option_chain = UpstoxOptionChainMock("test_token")
        print("✅ UpstoxOptionChainMock initialized successfully")
        
        # Test cache functionality
        option_chain.set_cache_duration(60)  # 1 minute cache
        print("✅ Cache duration set successfully")
        
        # Test cache clearing
        option_chain.clear_cache()
        print("✅ Cache cleared successfully")
        
        print("✅ Basic functionality tests passed")
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")

def test_data_fetching():
    """Test data fetching methods"""
    print("\n=== Testing Data Fetching ===")
    
    try:
        option_chain = UpstoxOptionChainMock("test_token")
        
        # Test fetching all data
        all_data = option_chain.fetch()
        assert len(all_data) > 0, "Should return some option data"
        print(f"✅ Fetched {len(all_data)} option contracts")
        
        # Test fetching with expiry filter using Utils
        next_expiry = option_chain.get_next_weekly_expiry()
        if next_expiry:
            expiry_data = option_chain.fetch(expiry=next_expiry)
            assert len(expiry_data) > 0, "Should return data for specific expiry"
            print(f"✅ Fetched {len(expiry_data)} contracts for expiry {next_expiry}")
        
        # Test fetching with strike price filter
        strikes = option_chain.get_available_strike_prices()
        if strikes:
            strike_data = option_chain.fetch(strike_price=strikes[0])
            assert len(strike_data) > 0, "Should return data for specific strike"
            print(f"✅ Fetched {len(strike_data)} contracts for strike {strikes[0]}")
        
        # Test fetching with both filters
        if next_expiry and strikes:
            filtered_data = option_chain.fetch(expiry=next_expiry, strike_price=strikes[0])
            assert len(filtered_data) > 0, "Should return data for specific expiry and strike"
            print(f"✅ Fetched {len(filtered_data)} contracts for expiry {next_expiry} and strike {strikes[0]}")
        
        print("✅ Data fetching tests passed")
        
    except Exception as e:
        print(f"❌ Data fetching test failed: {e}")

def test_filtering_methods():
    """Test filtering methods"""
    print("\n=== Testing Filtering Methods ===")
    
    try:
        option_chain = UpstoxOptionChainMock("test_token")
        
        # Get sample data
        all_data = option_chain.fetch()
        assert len(all_data) > 0, "Should have some data to filter"
        
        # Test expiry filtering using Utils
        next_expiry = option_chain.get_next_weekly_expiry()
        if next_expiry:
            filtered_by_expiry = option_chain._filter_by_expiry(all_data, next_expiry)
            assert len(filtered_by_expiry) > 0, f"Should have data for expiry {next_expiry}"
            print(f"✅ Expiry filtering: {len(filtered_by_expiry)} contracts for {next_expiry}")
        
        # Test strike price filtering
        strikes = option_chain.get_available_strike_prices()
        if strikes:
            filtered_by_strike = option_chain._filter_by_strike_price(all_data, strikes[0])
            assert len(filtered_by_strike) > 0, f"Should have data for strike {strikes[0]}"
            print(f"✅ Strike filtering: {len(filtered_by_strike)} contracts for strike {strikes[0]}")
        
        print("✅ Filtering methods tests passed")
        
    except Exception as e:
        print(f"❌ Filtering methods test failed: {e}")

def test_data_structure():
    """Test data structure and content"""
    print("\n=== Testing Data Structure ===")
    
    try:
        option_chain = UpstoxOptionChainMock("test_token")
        
        # Get sample data
        data = option_chain.fetch()
        assert len(data) > 0, "Should have some data"
        
        # Check data structure
        sample = data[0]
        required_fields = [
            'instrument_key', 'instrument_name', 'strike_price', 'expiry_date',
            'option_type', 'last_price', 'bid_price', 'ask_price', 'volume',
            'open_interest', 'change', 'change_percent', 'implied_volatility',
            'delta', 'gamma', 'theta', 'vega'
        ]
        
        for field in required_fields:
            assert field in sample, f"Missing required field: {field}"
        
        # Check data types
        assert isinstance(sample['strike_price'], (int, float)), "strike_price should be numeric"
        assert isinstance(sample['expiry_date'], str), "expiry_date should be string"
        assert sample['option_type'] in ['CALL', 'PUT'], "option_type should be CALL or PUT"
        assert isinstance(sample['volume'], int), "volume should be integer"
        
        print("✅ Data structure tests passed")
        
    except Exception as e:
        print(f"❌ Data structure test failed: {e}")

def test_summary_calculation():
    """Test option summary calculation"""
    print("\n=== Testing Summary Calculation ===")
    
    try:
        option_chain = UpstoxOptionChainMock("test_token")
        
        # Test overall summary
        summary = option_chain.get_option_summary()
        
        assert 'total_contracts' in summary, "Summary should have total_contracts"
        assert 'call_contracts' in summary, "Summary should have call_contracts"
        assert 'put_contracts' in summary, "Summary should have put_contracts"
        assert 'expiries' in summary, "Summary should have expiries"
        assert 'strike_range' in summary, "Summary should have strike_range"
        assert 'total_volume' in summary, "Summary should have total_volume"
        assert 'total_open_interest' in summary, "Summary should have total_open_interest"
        
        assert summary['total_contracts'] > 0, "Should have some contracts"
        assert summary['call_contracts'] > 0, "Should have some call contracts"
        assert summary['put_contracts'] > 0, "Should have some put contracts"
        assert len(summary['expiries']) > 0, "Should have some expiries"
        
        print(f"✅ Summary: {summary['total_contracts']} total contracts")
        print(f"   Calls: {summary['call_contracts']}, Puts: {summary['put_contracts']}")
        print(f"   Expiries: {len(summary['expiries'])}")
        print(f"   Strike range: {summary['strike_range']['min']} - {summary['strike_range']['max']}")
        
        # Test summary for specific expiry using Utils
        next_expiry = option_chain.get_next_weekly_expiry()
        if next_expiry:
            expiry_summary = option_chain.get_option_summary(expiry=next_expiry)
            assert expiry_summary['total_contracts'] > 0, "Should have contracts for specific expiry"
            print(f"✅ Expiry summary for {next_expiry}: {expiry_summary['total_contracts']} contracts")
        
        print("✅ Summary calculation tests passed")
        
    except Exception as e:
        print(f"❌ Summary calculation test failed: {e}")

def test_cache_functionality():
    """Test cache functionality"""
    print("\n=== Testing Cache Functionality ===")
    
    try:
        option_chain = UpstoxOptionChainMock("test_token")
        
        # Test cache validity
        assert not option_chain._is_cache_valid(), "Cache should be invalid initially"
        
        # Fetch data to populate cache
        data1 = option_chain.fetch()
        assert option_chain._is_cache_valid(), "Cache should be valid after fetching"
        
        # Fetch same data again (should use cache)
        data2 = option_chain.fetch()
        assert len(data1) == len(data2), "Cached data should be same length"
        
        # Test cache clearing
        option_chain.clear_cache()
        assert not option_chain._is_cache_valid(), "Cache should be invalid after clearing"
        
        print("✅ Cache functionality tests passed")
        
    except Exception as e:
        print(f"❌ Cache functionality test failed: {e}")

def test_error_handling():
    """Test error handling"""
    print("\n=== Testing Error Handling ===")
    
    try:
        option_chain = UpstoxOptionChainMock("test_token")
        
        # Test with invalid expiry
        invalid_expiry_data = option_chain.fetch(expiry="2025-13-45")  # Invalid date
        assert len(invalid_expiry_data) == 0, "Should return empty list for invalid expiry"
        
        # Test with invalid strike price
        invalid_strike_data = option_chain.fetch(strike_price=999999)  # Non-existent strike
        assert len(invalid_strike_data) == 0, "Should return empty list for invalid strike"
        
        # Test filtering with empty data
        empty_filtered = option_chain._filter_by_expiry([], "2025-09-09")
        assert empty_filtered == [], "Should return empty list for empty data"
        
        print("✅ Error handling tests passed")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")

def test_integration_example():
    """Test integration example"""
    print("\n=== Testing Integration Example ===")
    
    try:
        # Initialize with mock data
        option_chain = UpstoxOptionChainMock("test_token")
        
        print("Integration example with mock data:")
        
        # Fetch all option data
        all_options = option_chain.fetch()
        print(f"  Total options: {len(all_options)}")
        
        # Get next weekly expiry using Utils
        next_expiry = option_chain.get_next_weekly_expiry()
        print(f"  Next weekly expiry: {next_expiry}")
        
        # Fetch specific expiry
        if next_expiry:
            expiry_options = option_chain.fetch(expiry=next_expiry)
            print(f"  Options for {next_expiry}: {len(expiry_options)}")
        
        # Get available strikes
        strikes = option_chain.get_available_strike_prices()
        print(f"  Available strikes: {strikes[:5]}...")  # Show first 5
        
        # Fetch specific strike price
        if strikes:
            strike_options = option_chain.fetch(strike_price=strikes[0])
            print(f"  Options for strike {strikes[0]}: {len(strike_options)}")
        
        # Fetch specific expiry and strike
        if next_expiry and strikes:
            specific_options = option_chain.fetch(expiry=next_expiry, strike_price=strikes[0])
            print(f"  Options for {next_expiry} strike {strikes[0]}: {len(specific_options)}")
        
        # Get summary
        summary = option_chain.get_option_summary()
        print(f"  Summary: {summary['total_contracts']} total contracts")
        
        print("✅ Integration example completed successfully")
        
    except Exception as e:
        print(f"❌ Integration example test failed: {e}")

def test_performance():
    """Test performance with large datasets"""
    print("\n=== Testing Performance ===")
    
    try:
        option_chain = UpstoxOptionChainMock("test_token")
        
        # Time the initial fetch
        start_time = datetime.now()
        data = option_chain.fetch()
        end_time = datetime.now()
        
        fetch_time = (end_time - start_time).total_seconds()
        print(f"✅ Initial fetch: {len(data)} contracts in {fetch_time:.3f} seconds")
        
        # Time cached fetch
        start_time = datetime.now()
        cached_data = option_chain.fetch()
        end_time = datetime.now()
        
        cached_time = (end_time - start_time).total_seconds()
        print(f"✅ Cached fetch: {len(cached_data)} contracts in {cached_time:.3f} seconds")
        
        # Time filtering operations
        start_time = datetime.now()
        next_expiry = option_chain.get_next_weekly_expiry()
        strikes = option_chain.get_available_strike_prices()
        summary = option_chain.get_option_summary()
        end_time = datetime.now()
        
        filter_time = (end_time - start_time).total_seconds()
        print(f"✅ Filtering operations: {filter_time:.3f} seconds")
        
        print("✅ Performance tests passed")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")

if __name__ == "__main__":
    print("Testing UpstoxOptionChainMock Class...")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_data_fetching()
        test_filtering_methods()
        test_data_structure()
        test_summary_calculation()
        test_cache_functionality()
        test_error_handling()
        test_integration_example()
        test_performance()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
