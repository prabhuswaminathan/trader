#!/usr/bin/env python3
"""
Test script to verify the fixed chart display
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FixedChartDisplayTest")

def test_fixed_chart_display():
    """Test the fixed chart display"""
    try:
        logger.info("🚀 Testing Fixed Chart Display")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer, TkinterChartApp
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Fixed Chart")
        
        # Add instrument
        chart.add_instrument("NSE_INDEX|Nifty 50")
        
        # Add test data
        logger.info("📊 Adding Test Data")
        
        test_candles = [
            {
                'timestamp': datetime.now() - timedelta(minutes=20),
                'open': 24000.0,
                'high': 24010.0,
                'low': 23990.0,
                'close': 24005.0,
                'volume': 1000
            },
            {
                'timestamp': datetime.now() - timedelta(minutes=15),
                'open': 24005.0,
                'high': 24015.0,
                'low': 23995.0,
                'close': 24010.0,
                'volume': 1200
            },
            {
                'timestamp': datetime.now() - timedelta(minutes=10),
                'open': 24010.0,
                'high': 24020.0,
                'low': 24000.0,
                'close': 24015.0,
                'volume': 1500
            }
        ]
        
        for i, candle in enumerate(test_candles, 1):
            chart.update_data("NSE_INDEX|Nifty 50", candle)
            logger.info(f"✅ Added candle {i}: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}")
        
        # Check data
        if "NSE_INDEX|Nifty 50" in chart.candle_data:
            candles = chart.candle_data["NSE_INDEX|Nifty 50"]
            logger.info(f"✅ Chart has {len(candles)} candles")
        else:
            logger.error("❌ No candle data found")
            return False
        
        # Test force_chart_update (should work even when not running)
        logger.info("\n📊 Testing force_chart_update")
        chart.force_chart_update()
        
        # Check visual elements
        if chart.price_ax:
            lines = chart.price_ax.get_lines()
            patches = chart.price_ax.patches
            
            logger.info(f"✅ After force_chart_update:")
            logger.info(f"   Lines: {len(lines)}")
            logger.info(f"   Patches: {len(patches)}")
            
            if len(lines) > 0 or len(patches) > 0:
                logger.info("✅ Visual elements created successfully")
            else:
                logger.error("❌ No visual elements created")
                return False
        
        # Create GUI app
        logger.info("\n📊 Creating GUI App")
        app = TkinterChartApp(chart)
        
        # Check if canvas is properly embedded
        if hasattr(app, 'canvas') and app.canvas is not None:
            logger.info("✅ Canvas is embedded in GUI")
        else:
            logger.error("❌ Canvas is not embedded in GUI")
            return False
        
        # Start the chart
        logger.info("\n📊 Starting Chart")
        chart.start_chart()
        
        # Check if chart is running
        if chart.is_running:
            logger.info("✅ Chart is running")
        else:
            logger.error("❌ Chart is not running")
            return False
        
        # Add more data while chart is running
        logger.info("\n📊 Adding More Data While Chart is Running")
        
        new_candle = {
            'timestamp': datetime.now() - timedelta(minutes=5),
            'open': 24015.0,
            'high': 24025.0,
            'low': 24005.0,
            'close': 24020.0,
            'volume': 1800
        }
        
        chart.update_data("NSE_INDEX|Nifty 50", new_candle)
        logger.info(f"✅ Added new candle: O={new_candle['open']}, H={new_candle['high']}, L={new_candle['low']}, C={new_candle['close']}")
        
        # Check visual elements again
        if chart.price_ax:
            lines = chart.price_ax.get_lines()
            patches = chart.price_ax.patches
            
            logger.info(f"✅ After adding data while running:")
            logger.info(f"   Lines: {len(lines)}")
            logger.info(f"   Patches: {len(patches)}")
            
            if len(lines) > 0 or len(patches) > 0:
                logger.info("✅ Visual elements still present")
            else:
                logger.error("❌ Visual elements disappeared")
                return False
        
        # Update canvas
        app.canvas.draw()
        
        logger.info("✅ Chart setup complete")
        logger.info("📊 Chart should now be visible in the GUI window")
        
        # Run the GUI for a few seconds
        logger.info("📊 Running GUI for 3 seconds...")
        app.root.after(3000, app.root.quit)  # Quit after 3 seconds
        app.run()
        
        # Stop the chart
        chart.stop_chart()
        logger.info("✅ Chart stopped")
        
        logger.info("✅ Fixed chart display test completed")
        return True
        
    except Exception as e:
        logger.error(f"Fixed chart display test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run test"""
    logger.info("🚀 Starting Fixed Chart Display Test")
    logger.info("=" * 60)
    
    success = test_fixed_chart_display()
    
    if success:
        logger.info("\n🎉 Fixed chart display test passed!")
        logger.info("\n💡 Fix Summary:")
        logger.info("   • force_chart_update now works even when chart is not running")
        logger.info("   • OHLC data triggers immediate chart updates when chart is running")
        logger.info("   • Chart displays visual elements correctly")
        logger.info("   • GUI integration works properly")
        logger.info("   • Chart can be started and stopped correctly")
        logger.info("\n🎯 The chart should now display properly in the main application!")
    else:
        logger.error("\n❌ Fixed chart display test failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
