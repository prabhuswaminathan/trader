#!/usr/bin/env python3
"""
Example usage of the refactored market data application.
This demonstrates how to switch between different broker agents and use live data visualization.
"""

import logging
import time
from main import MarketDataApp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Example")

def example_upstox_usage():
    """Example of using Upstox agent"""
    logger.info("=== Upstox Agent Example ===")
    
    # Create app with Upstox agent
    app = MarketDataApp(broker_type="upstox")
    
    # Get status
    status = app.get_status()
    logger.info(f"App status: {status}")
    
    # Start live data (this would normally be done through the GUI)
    try:
        app.start_live_data()
        logger.info("Live data started successfully")
        
        # Keep running for a few seconds to see data
        time.sleep(5)
        
        # Stop live data
        app.stop_live_data()
        logger.info("Live data stopped")
        
    except Exception as e:
        logger.error(f"Error with Upstox agent: {e}")

def example_kite_usage():
    """Example of using Kite agent"""
    logger.info("=== Kite Agent Example ===")
    
    # Create app with Kite agent
    app = MarketDataApp(broker_type="kite")
    
    # Get status
    status = app.get_status()
    logger.info(f"App status: {status}")
    
    # Start live data
    try:
        app.start_live_data()
        logger.info("Live data started successfully")
        
        # Keep running for a few seconds to see data
        time.sleep(5)
        
        # Stop live data
        app.stop_live_data()
        logger.info("Live data stopped")
        
    except Exception as e:
        logger.error(f"Error with Kite agent: {e}")

def example_broker_switching():
    """Example of switching between brokers"""
    logger.info("=== Broker Switching Example ===")
    
    # Start with Upstox
    app = MarketDataApp(broker_type="upstox")
    logger.info(f"Started with: {app.broker_type}")
    
    # Switch to Kite
    app.switch_broker("kite")
    logger.info(f"Switched to: {app.broker_type}")
    
    # Switch back to Upstox
    app.switch_broker("upstox")
    logger.info(f"Switched back to: {app.broker_type}")

def example_chart_only():
    """Example of using just the chart visualizer"""
    logger.info("=== Chart Only Example ===")
    
    from chart_visualizer import LiveChartVisualizer, TkinterChartApp
    
    # Create chart visualizer
    chart = LiveChartVisualizer(title="Test Chart")
    
    # Add some test instruments
    chart.add_instrument("TEST_INSTRUMENT_1", "Test Instrument 1")
    chart.add_instrument("TEST_INSTRUMENT_2", "Test Instrument 2")
    
    # Simulate some data updates
    import random
    from datetime import datetime
    
    for i in range(10):
        # Simulate tick data
        tick_data = {
            'instrument_token': 'TEST_INSTRUMENT_1',
            'last_price': 100 + random.uniform(-5, 5),
            'volume': random.randint(100, 1000)
        }
        
        chart.update_data("TEST_INSTRUMENT_1", [tick_data])
        time.sleep(0.5)
    
    logger.info("Chart test completed")

def main():
    """Run all examples"""
    logger.info("Starting Market Data Application Examples")
    
    try:
        # Example 1: Upstox usage
        example_upstox_usage()
        
        # Example 2: Kite usage
        example_kite_usage()
        
        # Example 3: Broker switching
        example_broker_switching()
        
        # Example 4: Chart only
        example_chart_only()
        
        logger.info("All examples completed successfully")
        
    except Exception as e:
        logger.error(f"Example error: {e}")

if __name__ == "__main__":
    main()
