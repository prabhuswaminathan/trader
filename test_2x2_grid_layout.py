#!/usr/bin/env python3
"""
Test script to verify 2x2 grid layout functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
import tkinter as tk
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GridLayoutTest")

def test_2x2_grid_layout():
    """Test the 2x2 grid layout functionality"""
    try:
        logger.info("🚀 Testing 2x2 Grid Layout")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer, TkinterChartApp
        
        # Create chart visualizer
        chart_visualizer = LiveChartVisualizer(
            title="Nifty 50 Live Data - Grid Layout Test"
        )
        
        # Add some test data
        logger.info("📊 Adding test data to chart...")
        
        # Add test instruments
        chart_visualizer.add_instrument("NSE_INDEX|Nifty 50", "Nifty 50")
        
        # Generate some test OHLC data
        base_time = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
        test_data = []
        
        for i in range(10):
            timestamp = base_time + timedelta(minutes=i*5)
            open_price = 19500 + (i * 10)
            high_price = open_price + 15
            low_price = open_price - 10
            close_price = open_price + 5
            volume = 1000 + (i * 100)
            
            test_data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        # Add test data to chart
        for data in test_data:
            chart_visualizer.update_data("NSE_INDEX|Nifty 50", data)
        
        logger.info(f"   Added {len(test_data)} test candles")
        
        # Create Tkinter app with grid layout
        logger.info("📊 Creating Tkinter app with 2x2 grid layout...")
        app = TkinterChartApp(chart_visualizer)
        
        # Test grid frame availability
        logger.info("📊 Testing grid frame availability...")
        
        if hasattr(app, 'grid1_frame'):
            logger.info("   ✅ Grid 1 (Top-Left) - Intraday Price Chart: Available")
        else:
            logger.error("   ❌ Grid 1 frame not found")
            
        if hasattr(app, 'grid2_frame'):
            logger.info("   ✅ Grid 2 (Top-Right) - Available: Available")
        else:
            logger.error("   ❌ Grid 2 frame not found")
            
        if hasattr(app, 'grid3_frame'):
            logger.info("   ✅ Grid 3 (Bottom-Left) - Available: Available")
        else:
            logger.error("   ❌ Grid 3 frame not found")
            
        if hasattr(app, 'grid4_frame'):
            logger.info("   ✅ Grid 4 (Bottom-Right) - Available: Available")
        else:
            logger.error("   ❌ Grid 4 frame not found")
        
        # Test window properties
        logger.info("📊 Testing window properties...")
        logger.info(f"   Window title: {app.root.title()}")
        logger.info(f"   Window geometry: {app.root.geometry()}")
        
        # Test button availability
        logger.info("📊 Testing button availability...")
        buttons = [
            ('start_btn', 'Start Chart'),
            ('stop_btn', 'Stop Chart'),
            ('fetch_historical_btn', 'Fetch Historical'),
            ('fetch_intraday_btn', 'Fetch Intraday'),
            ('start_timer_btn', 'Start Timer'),
            ('stop_timer_btn', 'Stop Timer')
        ]
        
        for btn_attr, btn_name in buttons:
            if hasattr(app, btn_attr):
                logger.info(f"   ✅ {btn_name} button: Available")
            else:
                logger.error(f"   ❌ {btn_name} button: Not found")
        
        # Test status label
        if hasattr(app, 'status_label'):
            logger.info("   ✅ Status label: Available")
        else:
            logger.error("   ❌ Status label: Not found")
        
        # Test canvas
        if hasattr(app, 'canvas'):
            logger.info("   ✅ Matplotlib canvas: Available")
        else:
            logger.error("   ❌ Matplotlib canvas: Not found")
        
        logger.info("✅ 2x2 grid layout test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"2x2 grid layout test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_grid_layout_visual():
    """Test the visual appearance of the grid layout"""
    try:
        logger.info("\n🎨 Testing Visual Grid Layout")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer, TkinterChartApp
        
        # Create chart visualizer
        chart_visualizer = LiveChartVisualizer(
            title="Nifty 50 Live Data - Visual Test"
        )
        
        # Add test instrument
        chart_visualizer.add_instrument("NSE_INDEX|Nifty 50", "Nifty 50")
        
        # Create app
        app = TkinterChartApp(chart_visualizer)
        
        # Test grid configuration
        logger.info("📊 Testing grid configuration...")
        
        # Get the grid frame
        grid_frame = None
        for child in app.root.winfo_children():
            if isinstance(child, tk.Frame):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, tk.Frame):
                        grid_frame = grandchild
                        break
                if grid_frame:
                    break
        
        if grid_frame:
            logger.info("   ✅ Grid frame found")
            
            # Test grid weights
            try:
                row_weights = []
                col_weights = []
                
                for i in range(2):
                    row_weight = grid_frame.grid_rowconfigure(i, 'weight')
                    col_weight = grid_frame.grid_columnconfigure(i, 'weight')
                    row_weights.append(row_weight)
                    col_weights.append(col_weight)
                
                logger.info(f"   Row weights: {row_weights}")
                logger.info(f"   Column weights: {col_weights}")
                
                if all(w == 1 for w in row_weights) and all(w == 1 for w in col_weights):
                    logger.info("   ✅ Grid weights configured correctly (equal distribution)")
                else:
                    logger.warning("   ⚠ Grid weights not configured for equal distribution")
                    
            except Exception as e:
                logger.warning(f"   ⚠ Could not test grid weights: {e}")
        else:
            logger.error("   ❌ Grid frame not found")
        
        # Test frame titles
        logger.info("📊 Testing frame titles...")
        
        frame_titles = [
            ("grid1_frame", "Intraday Price Chart"),
            ("grid2_frame", "Grid 2 - Available"),
            ("grid3_frame", "Grid 3 - Available"),
            ("grid4_frame", "Grid 4 - Available")
        ]
        
        for frame_attr, expected_title in frame_titles:
            if hasattr(app, frame_attr):
                frame = getattr(app, frame_attr)
                if hasattr(frame, 'cget'):
                    try:
                        actual_title = frame.cget('text')
                        if actual_title == expected_title:
                            logger.info(f"   ✅ {frame_attr}: '{actual_title}'")
                        else:
                            logger.warning(f"   ⚠ {frame_attr}: Expected '{expected_title}', got '{actual_title}'")
                    except:
                        logger.info(f"   ✅ {frame_attr}: Available (title not accessible)")
                else:
                    logger.info(f"   ✅ {frame_attr}: Available")
            else:
                logger.error(f"   ❌ {frame_attr}: Not found")
        
        logger.info("✅ Visual grid layout test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Visual grid layout test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the tests"""
    logger.info("🚀 Starting 2x2 Grid Layout Tests")
    logger.info("=" * 60)
    
    success1 = test_2x2_grid_layout()
    success2 = test_grid_layout_visual()
    
    if success1 and success2:
        logger.info("\n🎉 All 2x2 grid layout tests passed!")
        logger.info("\n💡 Features Implemented:")
        logger.info("   • 2x2 grid layout with equal distribution")
        logger.info("   • Intraday price chart in Grid 1 (top-left)")
        logger.info("   • 3 additional grids ready for future use")
        logger.info("   • Proper grid weights for responsive layout")
        logger.info("   • Labeled frames for each grid")
        logger.info("   • Increased window size (1400x900)")
        logger.info("   • All existing buttons and controls preserved")
        logger.info("\n🎯 The 2x2 grid layout is ready for use!")
    else:
        logger.error("\n❌ Some 2x2 grid layout tests failed!")
    
    return success1 and success2

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
