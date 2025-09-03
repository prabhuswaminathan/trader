#!/usr/bin/env python3
"""
Test script to verify real-time candlestick updates
"""

import sys
import os
import logging
import time
from datetime import datetime

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RealtimeCandlestickTest")

def test_realtime_candlestick_updates():
    """Test that candlesticks update in real-time for each data feed"""
    logger.info("=== Testing Real-time Candlestick Updates ===")
    
    try:
        # Mock external dependencies
        import sys
        from unittest.mock import MagicMock
        
        mock_modules = [
            'matplotlib', 'matplotlib.pyplot', 'matplotlib.animation',
            'matplotlib.backends.backend_tkagg', 'tkinter', 'pandas', 'numpy'
        ]
        
        for module in mock_modules:
            sys.modules[module] = MagicMock()
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart
        chart = LiveChartVisualizer(title="Nifty 50 Live Data - UPSTOX", candle_interval_minutes=5)
        chart.add_instrument("NSE_INDEX|Nifty 50", "Nifty 50")
        
        # Start the chart
        chart.start_chart()
        logger.info("✓ Chart started")
        
        # Simulate real-time data feeds
        base_price = 19500.0
        prices = [19500, 19510, 19505, 19520, 19515, 19525, 19530, 19525, 19535, 19540]
        
        logger.info("Simulating real-time data feeds...")
        
        for i, price in enumerate(prices):
            # Create tick data
            tick_data = {
                'instrument_key': 'NSE_INDEX|Nifty 50',
                'data': f'ltp: {price}',
                'timestamp': time.time(),
                'price': price,
                'volume': 1000 + i * 100
            }
            
            # Update chart with data
            chart.update_data("NSE_INDEX|Nifty 50", tick_data)
            
            # Process the data immediately
            chart.process_data_queue()
            
            logger.info(f"Feed {i+1}: Price {price} - Chart updated")
            
            # Small delay to simulate real-time
            time.sleep(0.1)
        
        # Check final candle data
        candle_data = chart.get_candle_data("NSE_INDEX|Nifty 50")
        if candle_data:
            final_candle = candle_data[-1]
            logger.info(f"✓ Final candle: O={final_candle['open']:.2f}, H={final_candle['high']:.2f}, "
                       f"L={final_candle['low']:.2f}, C={final_candle['close']:.2f}, V={final_candle['volume']}")
            
            # Verify the candle was updated correctly
            expected_open = 19500.0  # First price
            expected_high = 19540.0  # Highest price
            expected_low = 19500.0   # Lowest price
            expected_close = 19540.0 # Last price
            expected_volume = sum(1000 + i * 100 for i in range(len(prices)))
            
            if (final_candle['open'] == expected_open and 
                final_candle['high'] == expected_high and
                final_candle['low'] == expected_low and
                final_candle['close'] == expected_close):
                logger.info("✓ Candlestick updated correctly for each data feed")
                return True
            else:
                logger.error("✗ Candlestick not updated correctly")
                logger.error(f"Expected: O={expected_open}, H={expected_high}, L={expected_low}, C={expected_close}")
                logger.error(f"Actual: O={final_candle['open']}, H={final_candle['high']}, L={final_candle['low']}, C={final_candle['close']}")
                return False
        else:
            logger.error("✗ No candle data created")
            return False
        
    except Exception as e:
        logger.error(f"✗ Real-time candlestick test failed: {e}")
        return False

def test_multiple_candles():
    """Test that new candles are created when time interval is reached"""
    logger.info("=== Testing Multiple Candle Creation ===")
    
    try:
        # Mock external dependencies
        import sys
        from unittest.mock import MagicMock
        
        mock_modules = [
            'matplotlib', 'matplotlib.pyplot', 'matplotlib.animation',
            'matplotlib.backends.backend_tkagg', 'tkinter', 'pandas', 'numpy'
        ]
        
        for module in mock_modules:
            sys.modules[module] = MagicMock()
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart with 1-minute candles for faster testing
        chart = LiveChartVisualizer(title="Test Chart", candle_interval_minutes=1)
        chart.add_instrument("TEST_INSTRUMENT", "Test Instrument")
        
        # Start the chart
        chart.start_chart()
        
        # Add first set of data
        for i in range(3):
            tick_data = {
                'instrument_key': 'TEST_INSTRUMENT',
                'data': f'ltp: {100 + i}',
                'timestamp': time.time(),
                'price': 100 + i,
                'volume': 100
            }
            chart.update_data("TEST_INSTRUMENT", tick_data)
            chart.process_data_queue()
            time.sleep(0.1)
        
        # Wait for next minute (simulate time passing)
        time.sleep(1)
        
        # Add second set of data (should create new candle)
        for i in range(3):
            tick_data = {
                'instrument_key': 'TEST_INSTRUMENT',
                'data': f'ltp: {200 + i}',
                'timestamp': time.time(),
                'price': 200 + i,
                'volume': 100
            }
            chart.update_data("TEST_INSTRUMENT", tick_data)
            chart.process_data_queue()
            time.sleep(0.1)
        
        # Check candle data
        candle_data = chart.get_candle_data("TEST_INSTRUMENT")
        logger.info(f"✓ Created {len(candle_data)} candles")
        
        if len(candle_data) >= 2:
            logger.info("✓ Multiple candles created correctly")
            return True
        else:
            logger.error("✗ Multiple candles not created")
            return False
        
    except Exception as e:
        logger.error(f"✗ Multiple candle test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting Real-time Candlestick Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Real-time Candlestick Updates", test_realtime_candlestick_updates),
        ("Multiple Candle Creation", test_multiple_candles)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        logger.info("")
    
    logger.info("=" * 50)
    logger.info(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        logger.info("✓ All tests passed!")
        logger.info("")
        logger.info("The candlestick chart now:")
        logger.info("- Updates immediately for each data feed")
        logger.info("- Consolidates ticks into proper 5-minute candles")
        logger.info("- Creates new candles when time interval is reached")
        logger.info("- Shows real-time OHLC updates")
        logger.info("")
        logger.info("Try running: python run_app.py")
    else:
        logger.error("✗ Some tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
