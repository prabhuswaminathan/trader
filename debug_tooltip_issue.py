#!/usr/bin/env python3
"""
Debug script to identify why tooltips are not displaying
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("TooltipDebug")

def debug_tooltip_issue():
    """Debug why tooltips are not working"""
    try:
        logger.info("🔍 Debugging Tooltip Issue")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer, TkinterChartApp
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Tooltip Debug Chart")
        
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
            }
        ]
        
        for i, candle in enumerate(test_candles, 1):
            chart.update_data("NSE_INDEX|Nifty 50", candle)
            logger.info(f"✅ Added candle {i}: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}")
        
        # Debug tooltip setup
        logger.info("\n🔍 Debugging Tooltip Setup")
        
        # Check if tooltip annotation exists
        if hasattr(chart, 'tooltip_annotation'):
            if chart.tooltip_annotation is not None:
                logger.info("✅ Tooltip annotation exists")
                logger.info(f"   Type: {type(chart.tooltip_annotation)}")
                logger.info(f"   Visible: {chart.tooltip_annotation.get_visible()}")
            else:
                logger.error("❌ Tooltip annotation is None")
        else:
            logger.error("❌ Tooltip annotation attribute does not exist")
        
        # Check if figure and axes exist
        if hasattr(chart, 'fig') and chart.fig is not None:
            logger.info("✅ Figure exists")
        else:
            logger.error("❌ Figure does not exist")
        
        if hasattr(chart, 'price_ax') and chart.price_ax is not None:
            logger.info("✅ Price axis exists")
        else:
            logger.error("❌ Price axis does not exist")
        
        # Check candle data
        logger.info(f"\n📊 Candle Data: {len(chart.candle_data)} instruments")
        for instrument, candles in chart.candle_data.items():
            logger.info(f"   {instrument}: {len(candles)} candles")
            if candles:
                logger.info(f"   First candle: {candles[0]}")
        
        # Test closest candlestick finding manually
        logger.info("\n🔍 Testing Closest Candlestick Finding")
        
        # Test with coordinates near the first candle
        test_time = base_time.timestamp()
        test_price = 24005.0
        
        try:
            closest_candle = chart._find_closest_candlestick(test_time, test_price)
            if closest_candle:
                logger.info("✅ Closest candlestick found manually")
                logger.info(f"   Instrument: {closest_candle['instrument']}")
                logger.info(f"   OHLC: O={closest_candle['candle']['open']}, H={closest_candle['candle']['high']}, L={closest_candle['candle']['low']}, C={closest_candle['candle']['close']}")
            else:
                logger.warning("⚠ No closest candlestick found manually")
        except Exception as e:
            logger.error(f"❌ Error finding closest candlestick manually: {e}")
            import traceback
            traceback.print_exc()
        
        # Test tooltip display manually
        logger.info("\n🔍 Testing Tooltip Display")
        
        if closest_candle and chart.tooltip_annotation:
            try:
                # Create a mock event
                class MockEvent:
                    def __init__(self, xdata, ydata):
                        self.xdata = xdata
                        self.ydata = ydata
                
                mock_event = MockEvent(test_time, test_price)
                chart._show_tooltip(mock_event, closest_candle)
                
                logger.info("✅ Tooltip display test completed")
                logger.info(f"   Tooltip visible: {chart.tooltip_annotation.get_visible()}")
                logger.info(f"   Tooltip text: {chart.tooltip_annotation.get_text()}")
                
            except Exception as e:
                logger.error(f"❌ Error testing tooltip display: {e}")
                import traceback
                traceback.print_exc()
        
        # Create GUI app
        app = TkinterChartApp(chart)
        
        # Force chart update
        chart.force_chart_update()
        
        # Check visual elements
        if chart.price_ax:
            lines = chart.price_ax.get_lines()
            patches = chart.price_ax.patches
            
            logger.info(f"\n📊 Chart Visual Elements:")
            logger.info(f"   Lines: {len(lines)}")
            logger.info(f"   Patches: {len(patches)}")
            
            if len(lines) > 0 and len(patches) > 0:
                logger.info("✅ Chart has candlestick elements")
            else:
                logger.error("❌ Chart has no visual elements")
        
        logger.info("\n🔍 Debug Summary:")
        logger.info("   • Check if tooltip annotation exists and is properly initialized")
        logger.info("   • Check if candle data is properly stored")
        logger.info("   • Check if closest candlestick finding works")
        logger.info("   • Check if tooltip display works manually")
        logger.info("   • Check if chart visual elements are created")
        
        # Run GUI for a few seconds
        logger.info("\n📊 Running GUI for 3 seconds...")
        app.root.after(3000, app.root.quit)
        app.run()
        
        return True
        
    except Exception as e:
        logger.error(f"Tooltip debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the debug"""
    logger.info("🚀 Starting Tooltip Debug")
    logger.info("=" * 60)
    
    success = debug_tooltip_issue()
    
    if success:
        logger.info("\n🔍 Tooltip debug completed!")
        logger.info("Check the logs above for any issues with tooltip setup")
    else:
        logger.error("\n❌ Tooltip debug failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
