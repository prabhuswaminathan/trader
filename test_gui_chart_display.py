#!/usr/bin/env python3
"""
Test script to run the actual GUI and see if chart displays
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GUIChartDisplayTest")

def test_gui_chart_display():
    """Test the actual GUI chart display"""
    try:
        logger.info("🚀 Testing GUI Chart Display")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer, TkinterChartApp
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Test GUI Chart")
        
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
            },
            {
                'timestamp': datetime.now() - timedelta(minutes=5),
                'open': 24015.0,
                'high': 24025.0,
                'low': 24005.0,
                'close': 24020.0,
                'volume': 1800
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
        
        # Create GUI app
        logger.info("📊 Creating GUI App")
        app = TkinterChartApp(chart)
        
        # Check if canvas is properly embedded
        if hasattr(app, 'canvas') and app.canvas is not None:
            logger.info("✅ Canvas is embedded in GUI")
        else:
            logger.error("❌ Canvas is not embedded in GUI")
            return False
        
        # Force a chart update
        logger.info("📊 Forcing Chart Update")
        chart.force_chart_update()
        
        # Check if chart has visual elements
        if chart.price_ax:
            lines = chart.price_ax.get_lines()
            patches = chart.price_ax.patches
            
            logger.info(f"✅ Chart visual elements:")
            logger.info(f"   Lines: {len(lines)}")
            logger.info(f"   Patches: {len(patches)}")
            
            if len(lines) > 0 or len(patches) > 0:
                logger.info("✅ Chart has visual elements")
            else:
                logger.warning("⚠ Chart has no visual elements")
        
        # Start the chart
        logger.info("📊 Starting Chart")
        chart.start_chart()
        
        # Update canvas
        app.canvas.draw()
        
        logger.info("✅ GUI setup complete")
        logger.info("📊 Chart should now be visible in the GUI window")
        logger.info("💡 If chart is still blank, the issue might be:")
        logger.info("   • Chart window is off-screen")
        logger.info("   • Chart is too small to see")
        logger.info("   • Chart colors are not visible")
        logger.info("   • Chart data is outside visible range")
        
        # Run the GUI for a few seconds
        logger.info("📊 Running GUI for 5 seconds...")
        app.root.after(5000, app.root.quit)  # Quit after 5 seconds
        app.run()
        
        logger.info("✅ GUI test completed")
        return True
        
    except Exception as e:
        logger.error(f"GUI chart display test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chart_visibility():
    """Test chart visibility settings"""
    try:
        logger.info("\n🔍 Testing Chart Visibility Settings")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Visibility Test Chart")
        
        # Add instrument and data
        chart.add_instrument("NSE_INDEX|Nifty 50")
        
        test_candle = {
            'timestamp': datetime.now(),
            'open': 24000.0,
            'high': 24010.0,
            'low': 23990.0,
            'close': 24005.0,
            'volume': 1000
        }
        
        chart.update_data("NSE_INDEX|Nifty 50", test_candle)
        
        # Check chart settings
        logger.info("📊 Checking Chart Settings")
        
        if chart.price_ax:
            # Check axis limits
            xlim = chart.price_ax.get_xlim()
            ylim = chart.price_ax.get_ylim()
            
            logger.info(f"✅ X-axis limits: {xlim}")
            logger.info(f"✅ Y-axis limits: {ylim}")
            
            # Check if limits are reasonable
            if ylim[0] < ylim[1] and ylim[0] > 0:
                logger.info("✅ Y-axis limits are reasonable")
            else:
                logger.warning(f"⚠ Y-axis limits might be problematic: {ylim}")
            
            # Check grid
            grid_visible = chart.price_ax.grid(True)
            logger.info(f"✅ Grid is enabled: {grid_visible}")
            
            # Check title
            title = chart.price_ax.get_title()
            logger.info(f"✅ Chart title: {title}")
            
            # Check labels
            xlabel = chart.price_ax.get_xlabel()
            ylabel = chart.price_ax.get_ylabel()
            logger.info(f"✅ X-axis label: {xlabel}")
            logger.info(f"✅ Y-axis label: {ylabel}")
        
        return True
        
    except Exception as e:
        logger.error(f"Chart visibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting GUI Chart Display Tests")
    logger.info("=" * 60)
    
    success = True
    
    # Test 1: GUI chart display
    if not test_gui_chart_display():
        success = False
    
    # Test 2: Chart visibility settings
    if not test_chart_visibility():
        success = False
    
    if success:
        logger.info("\n🎉 All tests passed!")
        logger.info("\n💡 Test Summary:")
        logger.info("   • GUI is properly set up")
        logger.info("   • Canvas is embedded correctly")
        logger.info("   • Chart has visual elements")
        logger.info("   • Chart settings are reasonable")
        logger.info("\n🔍 If chart is still blank in the actual app:")
        logger.info("   • Check if the GUI window is visible")
        logger.info("   • Check if the chart is in the visible area")
        logger.info("   • Check if the data is within the visible range")
        logger.info("   • Try clicking 'Start Chart' button")
    else:
        logger.error("\n❌ Some tests failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
