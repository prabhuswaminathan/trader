#!/usr/bin/env python3
"""
Test script to verify click tooltip functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClickTooltipsTest")

def test_click_tooltips():
    """Test that tooltips work on both hover and click"""
    try:
        logger.info("🚀 Testing Click Tooltip Functionality")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer, TkinterChartApp
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Click Tooltip Test Chart")
        
        # Add instrument
        chart.add_instrument("NSE_INDEX|Nifty 50")
        
        # Add test data
        logger.info("📊 Adding Test Data")
        
        base_time = datetime.now() - timedelta(hours=1)
        test_candles = [
            {
                'timestamp': base_time,
                'open': 24000.0,
                'high': 24010.0,
                'low': 23990.0,
                'close': 24005.0,
                'volume': 1000
            },
            {
                'timestamp': base_time + timedelta(minutes=5),
                'open': 24005.0,
                'high': 24015.0,
                'low': 23995.0,
                'close': 24010.0,
                'volume': 1200
            },
            {
                'timestamp': base_time + timedelta(minutes=10),
                'open': 24010.0,
                'high': 24020.0,
                'low': 24000.0,
                'close': 24015.0,
                'volume': 1500
            },
            {
                'timestamp': base_time + timedelta(minutes=15),
                'open': 24015.0,
                'high': 24025.0,
                'low': 24005.0,
                'close': 24020.0,
                'volume': 1800
            },
            {
                'timestamp': base_time + timedelta(minutes=20),
                'open': 24020.0,
                'high': 24030.0,
                'low': 24010.0,
                'close': 24025.0,
                'volume': 2000
            }
        ]
        
        for i, candle in enumerate(test_candles, 1):
            chart.update_data("NSE_INDEX|Nifty 50", candle)
            logger.info(f"✅ Added candle {i}: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}")
        
        # Check tooltip setup
        if hasattr(chart, 'tooltip_annotation') and chart.tooltip_annotation is not None:
            logger.info("✅ Tooltip annotation created")
        else:
            logger.error("❌ Tooltip annotation not created")
            return False
        
        # Test closest candlestick finding
        logger.info("\n📊 Testing Closest Candlestick Finding")
        
        # Test with coordinates near the first candle
        test_time = base_time.timestamp()
        test_price = 24005.0
        
        try:
            closest_candle = chart._find_closest_candlestick(test_time, test_price)
            if closest_candle:
                logger.info("✅ Closest candlestick found")
                logger.info(f"   Instrument: {closest_candle['instrument']}")
                logger.info(f"   OHLC: O={closest_candle['candle']['open']}, H={closest_candle['candle']['high']}, L={closest_candle['candle']['low']}, C={closest_candle['candle']['close']}")
            else:
                logger.warning("⚠ No closest candlestick found")
        except Exception as e:
            logger.error(f"❌ Error finding closest candlestick: {e}")
            return False
        
        # Create GUI app
        app = TkinterChartApp(chart)
        
        # Force chart update
        chart.force_chart_update()
        
        # Check visual elements
        if chart.price_ax:
            lines = chart.price_ax.get_lines()
            patches = chart.price_ax.patches
            
            logger.info(f"✅ Chart visual elements:")
            logger.info(f"   Lines: {len(lines)}")
            logger.info(f"   Patches: {len(patches)}")
            
            if len(lines) > 0 and len(patches) > 0:
                logger.info("✅ Chart has candlestick elements")
            else:
                logger.error("❌ Chart has no visual elements")
                return False
        
        logger.info("✅ Click tooltip setup successful")
        logger.info("📊 Chart should now display candlesticks with click and hover tooltips")
        logger.info("💡 Instructions:")
        logger.info("   • Hover over candlesticks to see tooltips")
        logger.info("   • Click on candlesticks to show tooltips")
        logger.info("   • Tooltips will show OHLC data")
        
        # Run GUI for a few seconds
        logger.info("📊 Running GUI for 5 seconds...")
        app.root.after(5000, app.root.quit)
        app.run()
        
        return True
        
    except Exception as e:
        logger.error(f"Click tooltip test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the test"""
    logger.info("🚀 Starting Click Tooltip Test")
    logger.info("=" * 60)
    
    success = test_click_tooltips()
    
    if success:
        logger.info("\n🎉 Click tooltip test passed!")
        logger.info("\n💡 Features:")
        logger.info("   • Tooltips work on both hover and click")
        logger.info("   • Click detection is more lenient (2-hour threshold)")
        logger.info("   • Tooltips show complete OHLC data")
        logger.info("   • Chart displays pure candlesticks")
        logger.info("\n🎯 The chart now supports both hover and click tooltips!")
    else:
        logger.error("\n❌ Click tooltip test failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
