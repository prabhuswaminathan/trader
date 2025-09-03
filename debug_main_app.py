#!/usr/bin/env python3
"""
Debug script to help identify why live data isn't showing in main.py
"""

import sys
import os
import logging

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MainAppDebug")

def main():
    """Main debug function"""
    logger.info("=== Main App Live Data Debug ===")
    
    logger.info("This script will help you debug why live data isn't showing in main.py")
    logger.info("")
    
    logger.info("Steps to debug:")
    logger.info("1. Make sure you have valid Upstox credentials in keys.env")
    logger.info("2. Run: python run_app.py")
    logger.info("3. Click 'Start Chart' in the GUI")
    logger.info("4. Check the console output for these messages:")
    logger.info("   - 'Connected to Upstox Market Data Streamer V3'")
    logger.info("   - 'Subscribed to live data for: [instruments]'")
    logger.info("   - 'Received live data: [data]'")
    logger.info("   - 'Processing Upstox data: [data]'")
    logger.info("   - 'Updated chart for [instrument]'")
    logger.info("")
    
    logger.info("If you see 'Received live data' but not 'Updated chart for [instrument]':")
    logger.info("- The data is being received but not processed correctly")
    logger.info("- Check if the instrument keys match between subscription and processing")
    logger.info("")
    
    logger.info("If you don't see 'Received live data' at all:")
    logger.info("- The WebSocket connection might not be established")
    logger.info("- Check your API credentials and permissions")
    logger.info("- Verify network connectivity")
    logger.info("")
    
    logger.info("Current instrument configuration:")
    try:
        from main import MarketDataApp
        app = MarketDataApp(broker_type="upstox")
        instruments = app.instruments[app.broker_type]
        for key, name in instruments.items():
            logger.info(f"  - {key}: {name}")
    except Exception as e:
        logger.error(f"Could not load instrument configuration: {e}")
    
    logger.info("")
    logger.info("To run the application:")
    logger.info("  python run_app.py")
    logger.info("")
    logger.info("To run just the Upstox agent (for comparison):")
    logger.info("  python code/upstox_agent.py")

if __name__ == "__main__":
    main()
