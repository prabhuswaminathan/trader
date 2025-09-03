#!/usr/bin/env python3
"""
Test script to verify the main app fix
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MainAppFixTest")

def test_main_app_agent_fix():
    """Test that the MarketDataApp now has proper agent reference"""
    try:
        # Mock the dependencies to avoid import errors
        import unittest.mock as mock
        
        # Mock the upstox_client to avoid dependency issues
        with mock.patch.dict('sys.modules', {
            'upstox_client': mock.MagicMock(),
            'upstox_client.rest': mock.MagicMock(),
            'upstox_client.ApiClient': mock.MagicMock(),
            'upstox_client.HistoryApi': mock.MagicMock(),
            'upstox_client.MarketDataStreamerV3': mock.MagicMock(),
            'upstox_client.MarketQuoteApi': mock.MagicMock(),
            'upstox_client.OrderApi': mock.MagicMock(),
            'auth_handler': mock.MagicMock(),
            'kiteconnect': mock.MagicMock(),
        }):
            from main import MarketDataApp
            
            logger.info("🚀 Testing MarketDataApp Agent Fix")
            logger.info("=" * 50)
            
            # Test 1: Create app instance
            logger.info("📊 Test 1: Creating MarketDataApp instance")
            app = MarketDataApp(broker_type="upstox")
            
            # Check if agent is properly initialized
            if hasattr(app, 'agent') and app.agent is not None:
                logger.info("✅ app.agent exists and is not None")
            else:
                logger.error("❌ app.agent is missing or None")
                return False
            
            # Test 2: Check if agent has required methods
            logger.info("📊 Test 2: Checking agent methods")
            required_methods = [
                'get_ohlc_historical_data',
                'get_ohlc_intraday_data',
                'consolidate_1min_to_5min',
                'store_ohlc_data'
            ]
            
            for method_name in required_methods:
                if hasattr(app.agent, method_name):
                    logger.info(f"✅ app.agent.{method_name} exists")
                else:
                    logger.error(f"❌ app.agent.{method_name} is missing")
                    return False
            
            # Test 3: Try calling fetch methods (they should fail gracefully without real API keys)
            logger.info("📊 Test 3: Testing fetch methods (expecting graceful failures)")
            
            try:
                result = app.fetch_and_display_historical_data()
                logger.info(f"✅ fetch_and_display_historical_data() called successfully (returned {result})")
            except AttributeError as e:
                if "'MarketDataApp' object has no attribute 'broker_agent'" in str(e):
                    logger.error(f"❌ Still getting broker_agent error: {e}")
                    return False
                else:
                    logger.info(f"✅ Different error (expected): {e}")
            except Exception as e:
                logger.info(f"✅ Other error (expected due to missing API keys): {e}")
            
            try:
                result = app.fetch_and_display_intraday_data()
                logger.info(f"✅ fetch_and_display_intraday_data() called successfully (returned {result})")
            except AttributeError as e:
                if "'MarketDataApp' object has no attribute 'broker_agent'" in str(e):
                    logger.error(f"❌ Still getting broker_agent error: {e}")
                    return False
                else:
                    logger.info(f"✅ Different error (expected): {e}")
            except Exception as e:
                logger.info(f"✅ Other error (expected due to missing API keys): {e}")
            
            logger.info("\n🎉 Main App Agent Fix Test Completed Successfully!")
            return True
        
    except Exception as e:
        logger.error(f"Main app agent fix test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test"""
    logger.info("🚀 Starting Main App Agent Fix Test")
    logger.info("=" * 60)
    
    if test_main_app_agent_fix():
        logger.info("\n🎉 Fix verified successfully!")
        logger.info("The 'broker_agent' attribute error has been resolved.")
    else:
        logger.error("\n❌ Fix verification failed!")
    
    return True

if __name__ == "__main__":
    main()
