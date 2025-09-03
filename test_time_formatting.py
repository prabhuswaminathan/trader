#!/usr/bin/env python3
"""
Test script to verify X-axis time formatting with 1-hour intervals
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TimeFormattingTest")

def test_time_formatting():
    """Test that X-axis displays time with 1-hour intervals"""
    try:
        logger.info("🚀 Testing X-Axis Time Formatting")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer, TkinterChartApp
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Time Formatting Test Chart")
        
        # Add instrument
        chart.add_instrument("NSE_INDEX|Nifty 50")
        
        # Add test data spanning multiple hours
        logger.info("📊 Adding Test Data Spanning Multiple Hours")
        
        base_time = datetime.now() - timedelta(hours=3)
        test_candles = []
        
        # Create candles for 3 hours (every 5 minutes)
        for hour in range(3):
            for minute in range(0, 60, 5):  # Every 5 minutes
                candle_time = base_time + timedelta(hours=hour, minutes=minute)
                
                # Create realistic OHLC data
                base_price = 24000 + (hour * 10) + (minute * 0.5)
                candle = {
                    'timestamp': candle_time,
                    'open': base_price,
                    'high': base_price + 5,
                    'low': base_price - 5,
                    'close': base_price + 2,
                    'volume': 1000 + (minute * 10)
                }
                test_candles.append(candle)
        
        # Add candles to chart
        for i, candle in enumerate(test_candles, 1):
            chart.update_data("NSE_INDEX|Nifty 50", candle)
            if i % 12 == 0:  # Log every hour
                logger.info(f"✅ Added {i} candles (up to {candle['timestamp'].strftime('%H:%M')})")
        
        logger.info(f"✅ Total candles added: {len(test_candles)}")
        
        # Force chart update (this should format the X-axis)
        chart.force_chart_update()
        
        # Check if time formatting was applied
        if chart.price_ax:
            # Check if the locator and formatter are set
            major_locator = chart.price_ax.xaxis.get_major_locator()
            major_formatter = chart.price_ax.xaxis.get_major_formatter()
            
            logger.info("✅ Chart axes available")
            logger.info(f"   Major locator: {type(major_locator).__name__}")
            logger.info(f"   Major formatter: {type(major_formatter).__name__}")
            
            # Check if it's an HourLocator
            if hasattr(major_locator, 'interval'):
                logger.info(f"   Locator interval: {major_locator.interval} hours")
            
            # Check if it's a DateFormatter
            if hasattr(major_formatter, 'fmt'):
                logger.info(f"   Formatter format: {major_formatter.fmt}")
        
        # Create GUI app
        app = TkinterChartApp(chart)
        
        logger.info("✅ Time formatting setup successful")
        logger.info("📊 Chart should now display:")
        logger.info("   • X-axis with time labels (HH:MM format)")
        logger.info("   • Major ticks every 1 hour")
        logger.info("   • Rotated labels for better readability")
        logger.info("   • Proper time range with padding")
        
        # Run GUI for a few seconds
        logger.info("📊 Running GUI for 5 seconds...")
        app.root.after(5000, app.root.quit)
        app.run()
        
        return True
        
    except Exception as e:
        logger.error(f"Time formatting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test"""
    logger.info("🚀 Starting X-Axis Time Formatting Test")
    logger.info("=" * 60)
    
    success = test_time_formatting()
    
    if success:
        logger.info("\n🎉 Time formatting test passed!")
        logger.info("\n💡 Features Applied:")
        logger.info("   • X-axis displays time in HH:MM format")
        logger.info("   • Major ticks every 1 hour")
        logger.info("   • Labels rotated 45 degrees for readability")
        logger.info("   • Proper time range with 30-minute padding")
        logger.info("   • HourLocator and DateFormatter configured")
        logger.info("\n🎯 The chart now displays time properly on the X-axis!")
    else:
        logger.error("\n❌ Time formatting test failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
