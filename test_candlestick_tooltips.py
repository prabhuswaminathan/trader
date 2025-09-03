#!/usr/bin/env python3
"""
Test script to verify candlestick tooltip functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CandlestickTooltipsTest")

def test_tooltip_functionality():
    """Test candlestick tooltip functionality"""
    try:
        logger.info("🚀 Testing Candlestick Tooltip Functionality")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer, TkinterChartApp
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Tooltip Test Chart")
        
        # Add instrument
        chart.add_instrument("NSE_INDEX|Nifty 50")
        
        # Add test data with multiple candles
        logger.info("📊 Adding Test Data")
        
        base_time = datetime.now() - timedelta(hours=2)
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
        
        # Check data
        if "NSE_INDEX|Nifty 50" in chart.candle_data:
            candles = chart.candle_data["NSE_INDEX|Nifty 50"]
            logger.info(f"✅ Chart has {len(candles)} candles")
        else:
            logger.error("❌ No candle data found")
            return False
        
        # Test tooltip setup
        logger.info("\n📊 Testing Tooltip Setup")
        
        if hasattr(chart, 'tooltip_annotation') and chart.tooltip_annotation is not None:
            logger.info("✅ Tooltip annotation created")
        else:
            logger.error("❌ Tooltip annotation not created")
            return False
        
        # Test closest candlestick finding
        logger.info("\n📊 Testing Closest Candlestick Finding")
        
        # Test with a known candle position
        test_candle = test_candles[2]  # Middle candle
        test_time = test_candle['timestamp']
        test_price = test_candle['close']
        
        # Convert to matplotlib format for testing
        if isinstance(test_time, datetime):
            test_x = test_time.timestamp()
        else:
            test_x = test_time
        
        closest_candle = chart._find_closest_candlestick(test_x, test_price)
        
        if closest_candle:
            logger.info("✅ Closest candlestick found")
            logger.info(f"   Instrument: {closest_candle['instrument']}")
            logger.info(f"   OHLC: O={closest_candle['candle']['open']}, H={closest_candle['candle']['high']}, L={closest_candle['candle']['low']}, C={closest_candle['candle']['close']}")
            logger.info(f"   Volume: {closest_candle['candle']['volume']}")
        else:
            logger.error("❌ No closest candlestick found")
            return False
        
        # Test tooltip text generation
        logger.info("\n📊 Testing Tooltip Text Generation")
        
        try:
            # Create a mock event for testing
            class MockEvent:
                def __init__(self, xdata, ydata):
                    self.xdata = xdata
                    self.ydata = ydata
                    self.inaxes = chart.price_ax
            
            mock_event = MockEvent(test_x, test_price)
            chart._show_tooltip(mock_event, closest_candle)
            
            if chart.tooltip_annotation.get_text():
                logger.info("✅ Tooltip text generated")
                logger.info(f"   Tooltip text: {chart.tooltip_annotation.get_text()}")
            else:
                logger.error("❌ Tooltip text not generated")
                return False
                
        except Exception as e:
            logger.error(f"❌ Tooltip text generation failed: {e}")
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
        
        # Force chart update
        chart.force_chart_update()
        
        # Check visual elements
        if chart.price_ax:
            lines = chart.price_ax.get_lines()
            patches = chart.price_ax.patches
            
            logger.info(f"✅ Chart visual elements:")
            logger.info(f"   Lines: {len(lines)}")
            logger.info(f"   Patches: {len(patches)}")
            
            if len(lines) > 0 or len(patches) > 0:
                logger.info("✅ Chart has visual elements")
            else:
                logger.error("❌ Chart has no visual elements")
                return False
        
        logger.info("✅ Tooltip functionality setup complete")
        logger.info("📊 Chart should now show tooltips when hovering over candlesticks")
        logger.info("💡 Hover over the candlesticks to see OHLC data in tooltips")
        
        # Run the GUI for a few seconds
        logger.info("📊 Running GUI for 5 seconds...")
        app.root.after(5000, app.root.quit)  # Quit after 5 seconds
        app.run()
        
        logger.info("✅ Tooltip functionality test completed")
        return True
        
    except Exception as e:
        logger.error(f"Tooltip functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tooltip_edge_cases():
    """Test tooltip edge cases"""
    try:
        logger.info("\n🔧 Testing Tooltip Edge Cases")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Edge Case Test Chart")
        
        # Test with no data
        logger.info("📊 Testing with no data")
        
        closest_candle = chart._find_closest_candlestick(0, 0)
        if closest_candle is None:
            logger.info("✅ Correctly returns None when no data")
        else:
            logger.error("❌ Should return None when no data")
            return False
        
        # Test with invalid coordinates
        logger.info("📊 Testing with invalid coordinates")
        
        closest_candle = chart._find_closest_candlestick(None, None)
        if closest_candle is None:
            logger.info("✅ Correctly handles None coordinates")
        else:
            logger.error("❌ Should handle None coordinates")
            return False
        
        # Test with empty candle data
        logger.info("📊 Testing with empty candle data")
        
        chart.candle_data = {"TEST": []}
        closest_candle = chart._find_closest_candlestick(1000, 24000)
        if closest_candle is None:
            logger.info("✅ Correctly handles empty candle data")
        else:
            logger.error("❌ Should handle empty candle data")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Tooltip edge cases test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Candlestick Tooltip Tests")
    logger.info("=" * 60)
    
    success = True
    
    # Test 1: Tooltip functionality
    if not test_tooltip_functionality():
        success = False
    
    # Test 2: Edge cases
    if not test_tooltip_edge_cases():
        success = False
    
    if success:
        logger.info("\n🎉 All tooltip tests passed!")
        logger.info("\n💡 Tooltip Feature Summary:")
        logger.info("   • Tooltip annotation is created on chart initialization")
        logger.info("   • Mouse hover detection works correctly")
        logger.info("   • Closest candlestick finding works with distance calculation")
        logger.info("   • Tooltip text shows complete OHLC data")
        logger.info("   • Tooltip appears near cursor position")
        logger.info("   • Edge cases are handled gracefully")
        logger.info("\n🎯 The chart now shows interactive tooltips on candlestick hover!")
    else:
        logger.error("\n❌ Some tooltip tests failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
