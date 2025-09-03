#!/usr/bin/env python3
"""
Simple test to verify main app works with actual Upstox agent
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
logger = logging.getLogger("MainAppTest")

def test_main_app_creation():
    """Test if main app can be created without errors"""
    logger.info("=== Testing Main App Creation ===")
    
    try:
        from main import MarketDataApp
        
        # Create application
        app = MarketDataApp(broker_type="upstox")
        logger.info("✓ MarketDataApp created successfully")
        
        # Check components
        if app.agent:
            logger.info("✓ Agent initialized")
        else:
            logger.error("✗ Agent not initialized")
            return False
        
        if app.chart_visualizer:
            logger.info("✓ Chart visualizer initialized")
        else:
            logger.error("✗ Chart visualizer not initialized")
            return False
        
        # Check instruments
        instruments = app.instruments[app.broker_type]
        logger.info(f"✓ Instruments configured: {list(instruments.keys())}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Main app creation failed: {e}")
        return False

def test_data_processing():
    """Test data processing methods"""
    logger.info("=== Testing Data Processing ===")
    
    try:
        from main import MarketDataApp
        
        app = MarketDataApp(broker_type="upstox")
        
        # Test with mock data
        mock_data = "ltp: 19500.5, volume: 1000, instrument: NSE_INDEX|Nifty 50"
        
        # Test Upstox data processing
        app._process_upstox_data(mock_data)
        logger.info("✓ Upstox data processing completed")
        
        # Test Kite data processing
        mock_kite_data = [{'instrument_token': 256265, 'last_price': 19500.5, 'volume': 1000}]
        app._process_kite_data(mock_kite_data)
        logger.info("✓ Kite data processing completed")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Data processing test failed: {e}")
        return False

def main():
    """Run tests"""
    logger.info("Starting Main App Tests")
    logger.info("=" * 40)
    
    tests = [
        ("Main App Creation", test_main_app_creation),
        ("Data Processing", test_data_processing)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        logger.info("")
    
    logger.info("=" * 40)
    logger.info(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        logger.info("✓ All tests passed!")
        logger.info("\nThe main application should now work correctly.")
        logger.info("To run with live data:")
        logger.info("1. Make sure keys.env has valid Upstox credentials")
        logger.info("2. Run: python run_app.py")
        logger.info("3. Click 'Start Chart' in the GUI")
    else:
        logger.error("✗ Some tests failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
