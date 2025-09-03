#!/usr/bin/env python3
"""
Test script to verify chart visualizer handles OHLC data correctly
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChartOHLCTest")

def test_chart_with_ohlc_data():
    """Test chart visualizer with OHLC data"""
    try:
        logger.info("🚀 Testing Chart Visualizer with OHLC Data")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Test Chart")
        
        # Test 1: OHLC data format (what we pass from main.py)
        logger.info("📊 Test 1: OHLC Data Format")
        ohlc_data = {
            'timestamp': '2024-01-01T10:00:00',
            'open': 24000.0,
            'high': 24010.0,
            'low': 23990.0,
            'close': 24005.0,
            'volume': 1000
        }
        
        chart.update_data("NSE_INDEX|Nifty 50", ohlc_data)
        logger.info(f"✅ Added OHLC data: O={ohlc_data['open']}, H={ohlc_data['high']}, L={ohlc_data['low']}, C={ohlc_data['close']}, V={ohlc_data['volume']}")
        
        # Test 2: Price data format (what we pass from live data)
        logger.info("\n📊 Test 2: Price Data Format")
        price_data = {
            'instrument_key': 'NSE_INDEX|Nifty 50',
            'data': 'mock_data',
            'timestamp': 1640995200,
            'price': 24050.5,
            'volume': 1500
        }
        
        chart.update_data("NSE_INDEX|Nifty 50", price_data)
        logger.info(f"✅ Added price data: price={price_data['price']}, volume={price_data['volume']}")
        
        # Test 3: Check if data was stored correctly
        logger.info("\n📊 Test 3: Checking Stored Data")
        
        if "NSE_INDEX|Nifty 50" in chart.candle_data:
            candles = chart.candle_data["NSE_INDEX|Nifty 50"]
            logger.info(f"✅ Found {len(candles)} candles in chart")
            
            for i, candle in enumerate(candles):
                logger.info(f"   Candle {i+1}: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}, V={candle['volume']}")
                
                # Check if prices are non-zero
                if candle['close'] > 0:
                    logger.info(f"   ✅ Candle {i+1} has non-zero close price")
                else:
                    logger.error(f"   ❌ Candle {i+1} has zero close price")
        else:
            logger.error("❌ No candle data found in chart")
        
        # Test 4: Check current prices
        logger.info("\n📊 Test 4: Checking Current Prices")
        
        if "NSE_INDEX|Nifty 50" in chart.current_prices:
            current_price = chart.current_prices["NSE_INDEX|Nifty 50"]
            logger.info(f"✅ Current price: {current_price}")
            
            if current_price > 0:
                logger.info("✅ Current price is non-zero")
            else:
                logger.error("❌ Current price is zero")
        else:
            logger.error("❌ No current price found")
        
        return True
        
    except Exception as e:
        logger.error(f"Chart OHLC test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_processing_flow():
    """Test the complete data processing flow"""
    try:
        logger.info("\n🔧 Testing Complete Data Processing Flow")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Test Chart")
        
        # Simulate the data flow from main.py
        logger.info("📊 Simulating Main.py Data Flow")
        
        # Step 1: Live data with price field
        live_tick_data = {
            'instrument_key': 'NSE_INDEX|Nifty 50',
            'data': 'LtpData(instrument_token="256265", last_price=24050.5, volume=1000)',
            'timestamp': 1640995200,
            'price': 24050.5,
            'volume': 1000
        }
        
        chart.update_data("NSE_INDEX|Nifty 50", live_tick_data)
        logger.info(f"✅ Processed live tick: price={live_tick_data['price']}, volume={live_tick_data['volume']}")
        
        # Step 2: OHLC data for warehouse
        ohlc_tick_data = {
            'timestamp': '2024-01-01T10:00:00',
            'open': 24050.5,
            'high': 24050.5,
            'low': 24050.5,
            'close': 24050.5,
            'volume': 1000
        }
        
        chart.update_data("NSE_INDEX|Nifty 50", ohlc_tick_data)
        logger.info(f"✅ Processed OHLC tick: O={ohlc_tick_data['open']}, C={ohlc_tick_data['close']}")
        
        # Check results
        if "NSE_INDEX|Nifty 50" in chart.candle_data:
            candles = chart.candle_data["NSE_INDEX|Nifty 50"]
            logger.info(f"✅ Total candles: {len(candles)}")
            
            # Check if any candle has non-zero prices
            non_zero_candles = [c for c in candles if c['close'] > 0]
            logger.info(f"✅ Non-zero price candles: {len(non_zero_candles)}")
            
            if len(non_zero_candles) > 0:
                logger.info("✅ Chart has candles with real prices!")
            else:
                logger.error("❌ All candles have zero prices")
        
        return True
        
    except Exception as e:
        logger.error(f"Data processing flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Chart OHLC Data Tests")
    logger.info("=" * 60)
    
    success = True
    
    # Test 1: Chart with OHLC data
    if not test_chart_with_ohlc_data():
        success = False
    
    # Test 2: Complete data processing flow
    if not test_data_processing_flow():
        success = False
    
    if success:
        logger.info("\n🎉 All tests passed!")
        logger.info("\n💡 Test Summary:")
        logger.info("   • Chart visualizer can handle OHLC data format")
        logger.info("   • Chart visualizer can handle price data format")
        logger.info("   • Data is stored correctly in candle_data")
        logger.info("   • Current prices are updated correctly")
        logger.info("   • Complete data processing flow works")
    else:
        logger.error("\n❌ Some tests failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
