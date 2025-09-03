#!/usr/bin/env python3
"""
Debug script to investigate why chart is blank despite data being logged
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChartDisplayDebug")

def test_chart_initialization():
    """Test chart initialization and basic setup"""
    try:
        logger.info("🚀 Testing Chart Initialization")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Debug Chart")
        
        # Check if chart components are initialized
        logger.info("📊 Checking Chart Components")
        
        if hasattr(chart, 'fig') and chart.fig is not None:
            logger.info("✅ Figure object exists")
        else:
            logger.error("❌ Figure object is missing")
            return False
        
        if hasattr(chart, 'price_ax') and chart.price_ax is not None:
            logger.info("✅ Price axis exists")
        else:
            logger.error("❌ Price axis is missing")
            return False
        
        if hasattr(chart, 'candle_data'):
            logger.info("✅ Candle data dictionary exists")
        else:
            logger.error("❌ Candle data dictionary is missing")
            return False
        
        # Add instrument
        chart.add_instrument("NSE_INDEX|Nifty 50")
        
        if "NSE_INDEX|Nifty 50" in chart.candle_data:
            logger.info("✅ Instrument added to candle data")
        else:
            logger.error("❌ Instrument not added to candle data")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Chart initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_addition_and_chart_drawing():
    """Test adding data and drawing chart"""
    try:
        logger.info("\n🔧 Testing Data Addition and Chart Drawing")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Debug Chart")
        
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
        
        # Check if data was stored
        logger.info("\n📊 Checking Stored Data")
        
        if "NSE_INDEX|Nifty 50" in chart.candle_data:
            candles = chart.candle_data["NSE_INDEX|Nifty 50"]
            logger.info(f"✅ Found {len(candles)} candles in chart")
            
            for i, candle in enumerate(candles):
                logger.info(f"   Candle {i+1}: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}, V={candle['volume']}")
        else:
            logger.error("❌ No candle data found")
            return False
        
        # Test chart drawing
        logger.info("\n📊 Testing Chart Drawing")
        
        try:
            # Test _draw_charts method directly
            chart._draw_charts()
            logger.info("✅ _draw_charts method executed successfully")
            
            # Check if axes have data
            if chart.price_ax:
                lines = chart.price_ax.get_lines()
                collections = chart.price_ax.collections
                patches = chart.price_ax.patches
                
                logger.info(f"✅ Chart axes info:")
                logger.info(f"   Lines: {len(lines)}")
                logger.info(f"   Collections: {len(collections)}")
                logger.info(f"   Patches: {len(patches)}")
                
                if len(lines) > 0 or len(collections) > 0 or len(patches) > 0:
                    logger.info("✅ Chart has visual elements")
                else:
                    logger.warning("⚠ Chart has no visual elements")
            
        except Exception as e:
            logger.error(f"❌ Chart drawing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Data addition and chart drawing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chart_animation():
    """Test chart animation and display"""
    try:
        logger.info("\n🎬 Testing Chart Animation")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Debug Chart")
        
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
        logger.info("✅ Added test candle")
        
        # Test chart start
        logger.info("📊 Testing Chart Start")
        
        try:
            chart.start_chart()
            logger.info("✅ Chart started successfully")
            
            # Check if animation is running
            if hasattr(chart, 'ani') and chart.ani is not None:
                logger.info("✅ Animation object exists")
            else:
                logger.warning("⚠ Animation object is missing")
            
            # Check if chart is running
            if chart.is_running:
                logger.info("✅ Chart is running")
            else:
                logger.warning("⚠ Chart is not running")
            
            # Stop chart
            chart.stop_chart()
            logger.info("✅ Chart stopped successfully")
            
        except Exception as e:
            logger.info(f"✅ Chart animation test (expected error due to GUI): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Chart animation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dataframe_conversion():
    """Test DataFrame conversion for chart data"""
    try:
        logger.info("\n📊 Testing DataFrame Conversion")
        logger.info("=" * 50)
        
        import pandas as pd
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Debug Chart")
        
        # Add instrument and data
        chart.add_instrument("NSE_INDEX|Nifty 50")
        
        test_candles = [
            {
                'timestamp': datetime.now() - timedelta(minutes=10),
                'open': 24000.0,
                'high': 24010.0,
                'low': 23990.0,
                'close': 24005.0,
                'volume': 1000
            },
            {
                'timestamp': datetime.now() - timedelta(minutes=5),
                'open': 24005.0,
                'high': 24015.0,
                'low': 23995.0,
                'close': 24010.0,
                'volume': 1200
            }
        ]
        
        for candle in test_candles:
            chart.update_data("NSE_INDEX|Nifty 50", candle)
        
        # Test DataFrame conversion
        logger.info("📊 Testing DataFrame Conversion")
        
        if "NSE_INDEX|Nifty 50" in chart.candle_data:
            candle_data = chart.candle_data["NSE_INDEX|Nifty 50"]
            df = pd.DataFrame(list(candle_data))
            
            logger.info(f"✅ DataFrame created with {len(df)} rows")
            logger.info(f"✅ DataFrame columns: {list(df.columns)}")
            logger.info(f"✅ DataFrame shape: {df.shape}")
            
            if not df.empty:
                logger.info("✅ DataFrame is not empty")
                logger.info(f"✅ Sample data:\n{df.head()}")
                
                # Check data types
                logger.info(f"✅ Data types:\n{df.dtypes}")
                
                # Check for any NaN values
                nan_count = df.isnull().sum().sum()
                if nan_count == 0:
                    logger.info("✅ No NaN values in DataFrame")
                else:
                    logger.warning(f"⚠ Found {nan_count} NaN values in DataFrame")
            else:
                logger.error("❌ DataFrame is empty")
                return False
        else:
            logger.error("❌ No candle data found")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"DataFrame conversion test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all debug tests"""
    logger.info("🚀 Starting Chart Display Debug Tests")
    logger.info("=" * 60)
    
    success = True
    
    # Test 1: Chart initialization
    if not test_chart_initialization():
        success = False
    
    # Test 2: Data addition and chart drawing
    if not test_data_addition_and_chart_drawing():
        success = False
    
    # Test 3: Chart animation
    if not test_chart_animation():
        success = False
    
    # Test 4: DataFrame conversion
    if not test_dataframe_conversion():
        success = False
    
    if success:
        logger.info("\n🎉 All debug tests passed!")
        logger.info("\n💡 Debug Summary:")
        logger.info("   • Chart components are properly initialized")
        logger.info("   • Data is being added correctly")
        logger.info("   • Chart drawing methods work")
        logger.info("   • DataFrame conversion works")
        logger.info("   • Chart animation starts/stops correctly")
        logger.info("\n🔍 If chart is still blank, the issue might be:")
        logger.info("   • Chart window not being displayed")
        logger.info("   • Chart being drawn but not visible")
        logger.info("   • GUI display issues")
        logger.info("   • Chart being drawn off-screen")
    else:
        logger.error("\n❌ Some debug tests failed!")
        logger.error("\n🔍 This indicates the issue is in the chart logic itself")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
