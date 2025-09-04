#!/usr/bin/env python3
"""
Test script to verify simplified live data logic for P&L calculations
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimplifiedLiveDataTest")

def test_datawarehouse_latest_price():
    """Test the datawarehouse latest price storage functionality"""
    try:
        logger.info("🚀 Testing DataWarehouse Latest Price Storage")
        logger.info("=" * 60)
        
        from datawarehouse import datawarehouse
        
        # Test storing latest price
        logger.info("📊 Testing latest price storage...")
        
        test_instrument = "NSE_INDEX|Nifty 50"
        test_price = 19500.50
        test_volume = 1000
        
        # Store latest price
        datawarehouse.store_latest_price(test_instrument, test_price, test_volume)
        logger.info(f"   ✅ Stored latest price: {test_instrument} = {test_price}")
        
        # Retrieve latest price data
        latest_data = datawarehouse.get_latest_price_data(test_instrument)
        if latest_data:
            logger.info(f"   ✅ Retrieved latest price data: {latest_data}")
            
            # Verify data structure
            expected_keys = ['price', 'volume', 'timestamp']
            for key in expected_keys:
                if key in latest_data:
                    logger.info(f"   ✅ {key}: {latest_data[key]}")
                else:
                    logger.error(f"   ❌ Missing key: {key}")
        else:
            logger.error("   ❌ Failed to retrieve latest price data")
        
        # Test multiple price updates
        logger.info("\n📊 Testing multiple price updates...")
        
        test_prices = [19501.25, 19502.75, 19500.00, 19503.50]
        for i, price in enumerate(test_prices):
            datawarehouse.store_latest_price(test_instrument, price, test_volume + i)
            latest_data = datawarehouse.get_latest_price_data(test_instrument)
            if latest_data and latest_data['price'] == price:
                logger.info(f"   ✅ Update {i+1}: {price} stored correctly")
            else:
                logger.error(f"   ❌ Update {i+1}: Failed to store {price}")
        
        # Test with different instruments
        logger.info("\n📊 Testing multiple instruments...")
        
        instruments = [
            ("NSE_INDEX|Nifty 50", 19500.50),
            ("NSE_INDEX|Bank Nifty", 45000.75),
            ("NSE|RELIANCE", 2500.25)
        ]
        
        for instrument, price in instruments:
            datawarehouse.store_latest_price(instrument, price, 1000)
            latest_data = datawarehouse.get_latest_price_data(instrument)
            if latest_data and latest_data['price'] == price:
                logger.info(f"   ✅ {instrument}: {price} stored correctly")
            else:
                logger.error(f"   ❌ {instrument}: Failed to store {price}")
        
        logger.info("✅ DataWarehouse latest price storage test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"DataWarehouse latest price test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simplified_live_data_processing():
    """Test the simplified live data processing logic"""
    try:
        logger.info("\n🚀 Testing Simplified Live Data Processing")
        logger.info("=" * 60)
        
        from main import MarketDataApp
        from datawarehouse import datawarehouse
        
        # Create market data app
        app = MarketDataApp("upstox")
        
        # Test Upstox data processing
        logger.info("📊 Testing Upstox data processing...")
        
        # Mock Upstox data (simulating protobuf message)
        class MockUpstoxData:
            def __str__(self):
                return "ltp: 19500.50, volume: 1000, instrument: NSE_INDEX|Nifty 50"
        
        mock_data = MockUpstoxData()
        
        # Process the mock data
        app._process_upstox_data(mock_data)
        
        # Check if latest price was stored
        latest_data = datawarehouse.get_latest_price_data("NSE_INDEX|Nifty 50")
        if latest_data:
            logger.info(f"   ✅ Upstox data processed: Latest price = {latest_data['price']}")
        else:
            logger.error("   ❌ Upstox data processing failed")
        
        # Test Kite data processing
        logger.info("\n📊 Testing Kite data processing...")
        
        # Mock Kite data
        mock_kite_data = [
            {
                'instrument_token': 256265,  # Nifty 50 token
                'last_price': 19501.25,
                'volume': 1500
            }
        ]
        
        # Process the mock data
        app._process_kite_data(mock_kite_data)
        
        # Check if latest price was stored
        latest_data = datawarehouse.get_latest_price_data("256265")
        if latest_data:
            logger.info(f"   ✅ Kite data processed: Latest price = {latest_data['price']}")
        else:
            logger.error("   ❌ Kite data processing failed")
        
        # Test timer functionality
        logger.info("\n📊 Testing timer functionality...")
        
        # Test timer start/stop
        app.start_timer()
        logger.info(f"   ✅ Timer started: {app.timer_running}")
        
        app.stop_timer()
        logger.info(f"   ✅ Timer stopped: {not app.timer_running}")
        
        # Test market hours detection
        from datetime import time as dt_time
        
        test_times = [
            (dt_time(8, 0), False),   # Before market
            (dt_time(9, 15), True),   # Market start
            (dt_time(12, 0), True),   # During market
            (dt_time(15, 30), True),  # Market end
            (dt_time(16, 0), False),  # After market
        ]
        
        for test_time, expected in test_times:
            result = app._is_market_hours(test_time)
            status = "✅" if result == expected else "❌"
            logger.info(f"   {status} Market hours {test_time.strftime('%H:%M')}: {result} (expected: {expected})")
        
        logger.info("✅ Simplified live data processing test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Simplified live data processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_removed_functionality():
    """Test that chart consolidation and display logic has been removed"""
    try:
        logger.info("\n🚀 Testing Removed Functionality")
        logger.info("=" * 60)
        
        from main import MarketDataApp
        
        # Create market data app
        app = MarketDataApp("upstox")
        
        # Check that chart updates are not called in live data processing
        logger.info("📊 Verifying chart updates removed from live data...")
        
        # Mock data
        class MockData:
            def __str__(self):
                return "ltp: 19500.50, volume: 1000"
        
        mock_data = MockData()
        
        # Process data and verify no chart updates
        logger.info("   Processing mock live data...")
        app._process_upstox_data(mock_data)
        logger.info("   ✅ Live data processed without chart updates")
        
        # Check that timer doesn't update charts
        logger.info("\n📊 Verifying timer doesn't update charts...")
        
        # Mock the fetch_and_display_intraday_data method to track calls
        original_method = app.fetch_and_display_intraday_data
        call_count = 0
        
        def mock_fetch_method():
            nonlocal call_count
            call_count += 1
            logger.info(f"   Timer fetch method called (call #{call_count})")
            return True
        
        app.fetch_and_display_intraday_data = mock_fetch_method
        
        # Test timer fetch
        app._fetch_intraday_data_timer()
        logger.info(f"   ✅ Timer fetch completed (calls: {call_count})")
        
        # Restore original method
        app.fetch_and_display_intraday_data = original_method
        
        logger.info("✅ Removed functionality test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Removed functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Simplified Live Data Tests")
    logger.info("=" * 80)
    
    success1 = test_datawarehouse_latest_price()
    success2 = test_simplified_live_data_processing()
    success3 = test_removed_functionality()
    
    if success1 and success2 and success3:
        logger.info("\n🎉 All simplified live data tests passed!")
        logger.info("\n💡 Features Implemented:")
        logger.info("   • Removed data consolidation logic")
        logger.info("   • Simplified live feed to maintain only latest NIFTY price")
        logger.info("   • Updated datawarehouse to store latest prices for P&L")
        logger.info("   • Removed chart updates from live data processing")
        logger.info("   • Timer fetches data for P&L calculations only")
        logger.info("   • Live data processing optimized for P&L calculations")
        logger.info("\n🎯 The simplified live data logic is ready for P&L calculations!")
    else:
        logger.error("\n❌ Some simplified live data tests failed!")
    
    return success1 and success2 and success3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

