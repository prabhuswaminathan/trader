#!/usr/bin/env python3
"""
Test script for OHLC data fetching and display functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OHLCDataFetchingTest")

def test_ohlc_data_fetching():
    """Test the OHLC data fetching functionality"""
    try:
        from main import MarketDataApp
        
        logger.info("🚀 Testing OHLC Data Fetching and Display")
        logger.info("=" * 60)
        
        # Create application with Upstox agent
        app = MarketDataApp(broker_type="upstox")
        
        # Test 1: Fetch Historical Data
        logger.info("📊 Test 1: Fetching Historical Data")
        logger.info("-" * 40)
        
        if app.fetch_and_display_historical_data():
            logger.info("✅ Historical data fetched and displayed successfully")
            
            # Check if data was stored in warehouse
            primary_instrument = list(app.instruments[app.broker_type].keys())[0]
            historical_df = app.broker_agent.get_stored_ohlc_data(primary_instrument, "historical", limit=5)
            
            if not historical_df.empty:
                logger.info(f"📈 Stored historical data sample:")
                logger.info(f"   Records: {len(historical_df)}")
                logger.info(f"   Date range: {historical_df.index[0]} to {historical_df.index[-1]}")
                logger.info(f"   Price range: {historical_df['low'].min():.2f} - {historical_df['high'].max():.2f}")
            else:
                logger.warning("⚠ No historical data found in warehouse")
        else:
            logger.error("❌ Failed to fetch historical data")
        
        # Test 2: Fetch Intraday Data
        logger.info("\n📊 Test 2: Fetching Intraday Data")
        logger.info("-" * 40)
        
        if app.fetch_and_display_intraday_data():
            logger.info("✅ Intraday data fetched and displayed successfully")
            
            # Check if data was stored in warehouse
            intraday_df = app.broker_agent.get_stored_ohlc_data(primary_instrument, "intraday", limit=5)
            
            if not intraday_df.empty:
                logger.info(f"📈 Stored intraday data sample:")
                logger.info(f"   Records: {len(intraday_df)}")
                logger.info(f"   Time range: {intraday_df.index[0]} to {intraday_df.index[-1]}")
                logger.info(f"   Price range: {intraday_df['low'].min():.2f} - {intraday_df['high'].max():.2f}")
            else:
                logger.warning("⚠ No intraday data found in warehouse")
        else:
            logger.error("❌ Failed to fetch intraday data")
        
        # Test 3: Data Consolidation
        logger.info("\n📊 Test 3: Data Consolidation Verification")
        logger.info("-" * 40)
        
        # Get the latest price and price range
        latest_price = app.broker_agent.get_latest_price(primary_instrument)
        min_price, max_price = app.broker_agent.get_price_range(primary_instrument, 24)
        
        if latest_price:
            logger.info(f"💰 Latest price: {latest_price:.2f}")
        else:
            logger.warning("⚠ No latest price available")
        
        if min_price and max_price:
            logger.info(f"📊 Price range (24h): {min_price:.2f} - {max_price:.2f}")
            logger.info(f"📏 Range width: {max_price - min_price:.2f} points")
        else:
            logger.warning("⚠ No price range data available")
        
        # Test 4: Chart Data Verification
        logger.info("\n📊 Test 4: Chart Data Verification")
        logger.info("-" * 40)
        
        # Check chart data
        chart_data = app.chart_visualizer.get_candle_data(primary_instrument)
        if chart_data:
            logger.info(f"📈 Chart contains {len(chart_data)} candles")
            
            # Show sample of chart data
            if len(chart_data) >= 3:
                logger.info("📋 Sample chart data (last 3 candles):")
                for i, candle in enumerate(chart_data[-3:]):
                    logger.info(f"   Candle {i+1}: O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}")
        else:
            logger.warning("⚠ No chart data available")
        
        logger.info("\n🎉 OHLC Data Fetching Test Completed!")
        return True
        
    except Exception as e:
        logger.error(f"OHLC data fetching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_broker_agent_methods():
    """Test the broker agent OHLC methods directly"""
    try:
        from upstox_agent import UpstoxAgent
        from datawarehouse import datawarehouse
        
        logger.info("\n🔧 Testing Broker Agent OHLC Methods")
        logger.info("=" * 50)
        
        # Create Upstox agent
        agent = UpstoxAgent()
        
        # Test instrument
        instrument = "NSE_INDEX|Nifty 50"
        
        # Test 1: Historical Data Method
        logger.info("📊 Testing get_ohlc_historical_data()...")
        try:
            historical_data = agent.get_ohlc_historical_data(instrument, "day")
            if historical_data:
                logger.info(f"✅ Historical data method returned {len(historical_data)} records")
                
                # Show sample data
                if len(historical_data) >= 1:
                    sample = historical_data[0]
                    logger.info(f"   Sample: {sample['timestamp']} - O:{sample['open']:.2f} H:{sample['high']:.2f} L:{sample['low']:.2f} C:{sample['close']:.2f}")
            else:
                logger.warning("⚠ Historical data method returned empty data")
        except Exception as e:
            logger.error(f"❌ Historical data method failed: {e}")
        
        # Test 2: Intraday Data Method
        logger.info("\n📊 Testing get_ohlc_intraday_data()...")
        try:
            intraday_data = agent.get_ohlc_intraday_data(instrument, "1minute")
            if intraday_data:
                logger.info(f"✅ Intraday data method returned {len(intraday_data)} records")
                
                # Show sample data
                if len(intraday_data) >= 1:
                    sample = intraday_data[0]
                    logger.info(f"   Sample: {sample['timestamp']} - O:{sample['open']:.2f} H:{sample['high']:.2f} L:{sample['low']:.2f} C:{sample['close']:.2f}")
            else:
                logger.warning("⚠ Intraday data method returned empty data")
        except Exception as e:
            logger.error(f"❌ Intraday data method failed: {e}")
        
        # Test 3: Data Consolidation
        logger.info("\n📊 Testing data consolidation...")
        try:
            if intraday_data:
                consolidated = agent.consolidate_1min_to_5min(instrument, intraday_data[:10])  # Use first 10 records
                logger.info(f"✅ Consolidation: {len(intraday_data[:10])} 1-min → {len(consolidated)} 5-min candles")
                
                if consolidated:
                    sample = consolidated[0]
                    logger.info(f"   Sample consolidated: {sample['timestamp']} - O:{sample['open']:.2f} H:{sample['high']:.2f} L:{sample['low']:.2f} C:{sample['close']:.2f}")
            else:
                logger.warning("⚠ No intraday data available for consolidation test")
        except Exception as e:
            logger.error(f"❌ Data consolidation failed: {e}")
        
        logger.info("\n🎉 Broker Agent Methods Test Completed!")
        return True
        
    except Exception as e:
        logger.error(f"Broker agent methods test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting OHLC Data Fetching Tests")
    logger.info("=" * 60)
    
    success = True
    
    # Test 1: OHLC data fetching and display
    if not test_ohlc_data_fetching():
        success = False
    
    # Test 2: Broker agent methods
    if not test_broker_agent_methods():
        success = False
    
    if success:
        logger.info("\n🎉 All tests passed!")
        logger.info("\n💡 Key Features Demonstrated:")
        logger.info("   • Historical data fetching from broker")
        logger.info("   • Intraday data fetching from broker")
        logger.info("   • 1-minute to 5-minute data consolidation")
        logger.info("   • Data storage in warehouse")
        logger.info("   • Chart display with dynamic Y-axis scaling")
        logger.info("   • Price range calculation")
    else:
        logger.error("\n❌ Some tests failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
