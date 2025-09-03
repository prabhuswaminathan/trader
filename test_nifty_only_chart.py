#!/usr/bin/env python3
"""
Test script to verify Nifty-only chart functionality
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
logger = logging.getLogger("NiftyOnlyTest")

def test_nifty_only_configuration():
    """Test that only Nifty 50 is configured"""
    logger.info("=== Testing Nifty-Only Configuration ===")
    
    try:
        # Mock external dependencies
        import sys
        from unittest.mock import MagicMock
        
        mock_modules = [
            'upstox_client', 'kiteconnect', 'matplotlib', 'matplotlib.pyplot',
            'matplotlib.animation', 'matplotlib.backends.backend_tkagg',
            'tkinter', 'pandas', 'numpy', 'dotenv'
        ]
        
        for module in mock_modules:
            sys.modules[module] = MagicMock()
        
        from main import MarketDataApp
        
        # Test Upstox configuration
        app_upstox = MarketDataApp(broker_type="upstox")
        upstox_instruments = app_upstox.instruments["upstox"]
        logger.info(f"Upstox instruments: {upstox_instruments}")
        
        # Test Kite configuration
        app_kite = MarketDataApp(broker_type="kite")
        kite_instruments = app_kite.instruments["kite"]
        logger.info(f"Kite instruments: {kite_instruments}")
        
        # Verify only Nifty 50 is configured
        if len(upstox_instruments) == 1 and "NSE_INDEX|Nifty 50" in upstox_instruments:
            logger.info("✓ Upstox configuration correct - only Nifty 50")
        else:
            logger.error("✗ Upstox configuration incorrect")
            return False
        
        if len(kite_instruments) == 1 and 256265 in kite_instruments:
            logger.info("✓ Kite configuration correct - only Nifty 50")
        else:
            logger.error("✗ Kite configuration incorrect")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False

def test_single_chart_display():
    """Test that only a single chart is displayed"""
    logger.info("=== Testing Single Chart Display ===")
    
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
        chart = LiveChartVisualizer(title="Nifty 50 Live Data - UPSTOX")
        chart.add_instrument("NSE_INDEX|Nifty 50", "Nifty 50")
        
        logger.info("✓ Chart created with single instrument")
        
        # Check that volume_ax is None (no volume chart)
        if chart.volume_ax is None:
            logger.info("✓ Volume chart removed - only price chart exists")
        else:
            logger.error("✗ Volume chart still exists")
            return False
        
        # Check that price_ax exists
        if chart.price_ax is not None:
            logger.info("✓ Price chart exists")
        else:
            logger.error("✗ Price chart missing")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Single chart test failed: {e}")
        return False

def test_candlestick_display():
    """Test candlestick display with Nifty data"""
    logger.info("=== Testing Candlestick Display ===")
    
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
        
        # Add some mock Nifty data
        base_price = 19500.0
        for i in range(5):
            price = base_price + (i * 10)  # Simulate price movement
            tick_data = {
                'instrument_key': 'NSE_INDEX|Nifty 50',
                'data': f'ltp: {price}',
                'timestamp': time.time(),
                'price': price,
                'volume': 1000
            }
            
            chart.update_data("NSE_INDEX|Nifty 50", tick_data)
            time.sleep(0.1)
        
        # Process the data
        chart.process_data_queue()
        
        # Check candle data
        candle_data = chart.get_candle_data("NSE_INDEX|Nifty 50")
        if candle_data:
            candle = candle_data[-1]
            logger.info(f"✓ Candlestick created: O={candle['open']:.2f}, H={candle['high']:.2f}, "
                       f"L={candle['low']:.2f}, C={candle['close']:.2f}")
            
            # Verify OHLC values are reasonable
            if (candle['open'] > 0 and candle['high'] > 0 and 
                candle['low'] > 0 and candle['close'] > 0):
                logger.info("✓ OHLC values are valid")
                return True
            else:
                logger.error("✗ OHLC values are invalid")
                return False
        else:
            logger.error("✗ No candle data created")
            return False
        
    except Exception as e:
        logger.error(f"✗ Candlestick display test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting Nifty-Only Chart Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Nifty-Only Configuration", test_nifty_only_configuration),
        ("Single Chart Display", test_single_chart_display),
        ("Candlestick Display", test_candlestick_display)
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
        logger.info("The chart now has:")
        logger.info("- Only Nifty 50 data subscription")
        logger.info("- Single chart display (no volume chart)")
        logger.info("- Proper candlestick visualization")
        logger.info("- Clean, focused interface")
        logger.info("")
        logger.info("Try running: python run_app.py")
    else:
        logger.error("✗ Some tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
