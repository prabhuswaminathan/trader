#!/usr/bin/env python3
"""
Debug intraday chart issues
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from chart_visualizer import LiveChartVisualizer, TkinterChartApp
from datetime import datetime, timedelta
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_intraday_chart_debug():
    """Debug intraday chart issues"""
    print("Debugging intraday chart issues...")
    
    # Create chart visualizer
    chart = LiveChartVisualizer("Test Chart")
    chart.start_chart()
    print("✓ Chart created and started")
    
    # Add comprehensive test data
    intraday_data = []
    base_time = datetime.now() - timedelta(hours=2)
    
    print("\n1. Creating test data...")
    for i in range(20):  # Create 20 5-minute candles
        candle_time = base_time + timedelta(minutes=i*5)
        # Create realistic OHLC data with some variation
        base_price = 100.0 + i * 2.0
        open_price = base_price + (i % 3 - 1) * 0.5  # Some variation
        close_price = base_price + (i % 2) * 1.0     # Some variation
        high_price = max(open_price, close_price) + 0.5
        low_price = min(open_price, close_price) - 0.5
        
        intraday_data.append({
            'timestamp': candle_time,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': 1000 + i * 100
        })
    
    print(f"✓ Created {len(intraday_data)} test candles")
    print(f"  - First candle: {intraday_data[0]}")
    print(f"  - Last candle: {intraday_data[-1]}")
    
    # Store intraday data
    print("\n2. Storing intraday data...")
    chart._store_intraday_data("NIFTY", intraday_data)
    
    # Check stored data
    if "NIFTY" in chart.candle_data:
        stored_count = len(chart.candle_data["NIFTY"])
        print(f"✓ Stored {stored_count} candles in chart")
        
        # Check first and last stored candles
        first_candle = chart.candle_data["NIFTY"][0]
        last_candle = chart.candle_data["NIFTY"][-1]
        print(f"  - First stored: {first_candle}")
        print(f"  - Last stored: {last_candle}")
    else:
        print("✗ No data stored in chart")
        return False
    
    # Test chart rendering
    print("\n3. Testing chart rendering...")
    try:
        # Force chart update
        chart.force_chart_update()
        print("✓ Chart update forced")
        
        # Check if chart is running
        print(f"  - Chart running: {chart.is_running}")
        print(f"  - Chart axes available: {chart.price_ax is not None}")
        
        # Test manual chart drawing
        chart._draw_charts()
        print("✓ Manual chart drawing completed")
        
    except Exception as e:
        print(f"✗ Chart rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create Tkinter app
    print("\n4. Creating Tkinter app...")
    try:
        app = TkinterChartApp(chart)
        print("✓ Tkinter app created")
        
        # Check initial state
        print(f"  - Window size: {app.root.winfo_width()}x{app.root.winfo_height()}")
        print(f"  - Grid1 size: {app.grid1_frame.winfo_width()}x{app.grid1_frame.winfo_height()}")
        print(f"  - Canvas available: {app.canvas is not None}")
        
        # Wait for UI to settle
        time.sleep(1)
        
        # Check after UI settlement
        print(f"  - Window size after settle: {app.root.winfo_width()}x{app.root.winfo_height()}")
        print(f"  - Grid1 size after settle: {app.grid1_frame.winfo_width()}x{app.grid1_frame.winfo_height()}")
        
        # Test resize handler
        print("\n5. Testing resize handler...")
        try:
            class FakeEvent:
                def __init__(self, widget):
                    self.widget = widget
            
            fake_event = FakeEvent(app.root)
            app._on_window_resize(fake_event)
            print("✓ Resize handler executed")
            
        except Exception as e:
            print(f"✗ Resize handler failed: {e}")
        
        # Test manual grid layout update
        print("\n6. Testing manual grid layout update...")
        try:
            app._update_grid_layout()
            print("✓ Manual grid layout update completed")
            
        except Exception as e:
            print(f"✗ Manual grid layout update failed: {e}")
        
        # Check final chart state
        print("\n7. Checking final chart state...")
        print(f"  - Chart running: {chart.is_running}")
        print(f"  - Animation running: {chart.ani is not None}")
        print(f"  - Candle data count: {len(chart.candle_data.get('NIFTY', []))}")
        
        # Show window briefly
        print("\n8. Showing window briefly...")
        app.root.after(2000, app.root.destroy)  # Auto-close after 2 seconds
        
        try:
            app.root.mainloop()
            print("✓ Window displayed and closed")
        except Exception as e:
            print(f"✗ Window display failed: {e}")
        
    except Exception as e:
        print(f"✗ Tkinter app creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ Intraday chart debug completed!")
    return True

if __name__ == "__main__":
    print("🧪 Debugging Intraday Chart Issues\n")
    
    success = test_intraday_chart_debug()
    
    if success:
        print("\n🎉 Intraday chart debug completed successfully!")
        print("✅ Check the output above for any issues")
    else:
        print("\n❌ Intraday chart debug failed - check the issues above.")
