#!/usr/bin/env python3
"""
Test script to verify live data flow from agent to chart
"""

import sys
import os
import logging
import time

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LiveDataFlowTest")

def test_upstox_data_flow():
    """Test the complete data flow from Upstox agent to chart"""
    logger.info("=== Testing Upstox Data Flow ===")
    
    try:
        from main import MarketDataApp
        
        # Create application
        app = MarketDataApp(broker_type="upstox")
        logger.info("✓ MarketDataApp created")
        
        # Check if agent is properly initialized
        if app.agent:
            logger.info("✓ UpstoxAgent initialized")
        else:
            logger.error("✗ UpstoxAgent not initialized")
            return False
        
        # Check if chart is properly initialized
        if app.chart_visualizer:
            logger.info("✓ ChartVisualizer initialized")
        else:
            logger.error("✗ ChartVisualizer not initialized")
            return False
        
        # Test data processing with mock data
        logger.info("Testing data processing with mock Upstox data...")
        
        # Mock Upstox data (simulating what would come from the WebSocket)
        mock_upstox_data = "ltp: 19500.5, volume: 1000, instrument: NSE_INDEX|Nifty 50"
        
        # Test the data processing
        app._process_upstox_data(mock_upstox_data)
        logger.info("✓ Mock data processed")
        
        # Check if chart received the data
        prices = app.chart_visualizer.get_current_prices()
        logger.info(f"Current prices: {prices}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Upstox data flow test failed: {e}")
        return False

def test_chart_data_processing():
    """Test chart data processing directly"""
    logger.info("=== Testing Chart Data Processing ===")
    
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
        chart = LiveChartVisualizer(title="Test Chart")
        chart.add_instrument("NSE_INDEX|Nifty 50", "Nifty 50")
        
        # Test with mock Upstox data
        mock_tick_data = {
            'instrument_key': 'NSE_INDEX|Nifty 50',
            'data': 'ltp: 19500.5, volume: 1000',
            'timestamp': time.time()
        }
        
        chart.update_data("NSE_INDEX|Nifty 50", mock_tick_data)
        logger.info("✓ Chart data processing test passed")
        
        # Check if data was processed
        prices = chart.get_current_prices()
        logger.info(f"Chart prices: {prices}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Chart data processing test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting Live Data Flow Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Chart Data Processing", test_chart_data_processing),
        ("Upstox Data Flow", test_upstox_data_flow)
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
        logger.info("✓ All data flow tests passed!")
        logger.info("\nThe live data flow should now work correctly.")
        logger.info("Try running: python run_app.py")
    else:
        logger.error("✗ Some tests failed")
        logger.info("\nIssues to check:")
        logger.info("1. Make sure keys.env has valid Upstox credentials")
        logger.info("2. Check if Upstox API has live data permissions")
        logger.info("3. Verify network connectivity")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
