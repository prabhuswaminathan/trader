#!/usr/bin/env python3
"""
Launcher script for the Market Data Application.
This script can be run directly without package import issues.
"""

import sys
import os
import logging

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MarketDataApp")

def main():
    """Main function to run the application"""
    try:
        # Import the main application
        from main import MarketDataApp
        
        logger.info("Market Data Application starting...")
        logger.info("Available broker types: upstox, kite")
        
        # Create application with Upstox agent by default
        app = MarketDataApp(broker_type="upstox")
        
        logger.info("Market Data Application initialized")
        logger.info("Starting chart application...")
        
        # Run the chart application
        app.run_chart_app()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except ImportError as e:
        logger.error(f"Import error - missing dependencies: {e}")
        logger.info("Please install required packages: pip install -r requirements.txt")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        # Cleanup
        try:
            if 'app' in locals():
                app.stop_live_data()
        except:
            pass

if __name__ == "__main__":
    main()
