#!/usr/bin/env python3
"""
Test script to verify candlestick plotting timezone fix
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from chart_visualizer import LiveChartVisualizer, TkinterChartApp
import tkinter as tk
from datetime import datetime, timezone
import pandas as pd
import numpy as np

def test_candlestick_timezone_fix():
    """Test that candlestick plotting works without timezone errors"""
    try:
        # Create a simple chart visualizer
        chart = LiveChartVisualizer(title="Test Chart")
        
        # Create the Tkinter app
        app = TkinterChartApp(chart)
        
        # Add an instrument
        chart.add_instrument("TEST_INSTRUMENT", "Test Instrument")
        
        # Create test data with mixed timezone timestamps (this used to cause errors)
        test_data = []
        base_time = datetime.now()
        
        # Mix of timezone-aware and timezone-naive timestamps
        for i in range(10):
            if i % 2 == 0:
                # Timezone-aware timestamp
                timestamp = datetime.now(timezone.utc)
            else:
                # Timezone-naive timestamp
                timestamp = datetime.now()
            
            test_data.append({
                'timestamp': timestamp,
                'open': 100 + i,
                'high': 105 + i,
                'low': 95 + i,
                'close': 102 + i,
                'volume': 1000 + i * 100
            })
        
        print(f"Created test data with {len(test_data)} mixed timezone timestamps")
        
        # Convert to DataFrame (this is what the chart visualizer does)
        df = pd.DataFrame(test_data)
        print("✓ DataFrame created successfully")
        
        # Test the candlestick plotting method directly
        chart._plot_candlesticks(df, "TEST_INSTRUMENT")
        print("✓ Candlestick plotting completed without timezone errors")
        
        # Test with more complex data
        complex_data = []
        for i in range(20):
            # Mix different timezone types
            if i % 3 == 0:
                timestamp = datetime.now(timezone.utc)
            elif i % 3 == 1:
                timestamp = datetime.now()
            else:
                timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            
            complex_data.append({
                'timestamp': timestamp,
                'open': 200 + i * 2,
                'high': 205 + i * 2,
                'low': 195 + i * 2,
                'close': 202 + i * 2,
                'volume': 2000 + i * 50
            })
        
        df_complex = pd.DataFrame(complex_data)
        chart._plot_candlesticks(df_complex, "TEST_INSTRUMENT")
        print("✓ Complex candlestick plotting completed without timezone errors")
        
        # Test the chart display
        chart.start_chart()
        print("✓ Chart started successfully")
        
        # Show the window briefly
        app.root.after(3000, app.root.destroy)  # Auto-close after 3 seconds
        app.run()
        
        print("✓ All candlestick timezone tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error testing candlestick timezone fix: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing candlestick plotting timezone fix...")
    success = test_candlestick_timezone_fix()
    if success:
        print("\n✓ Candlestick timezone fix test completed successfully!")
    else:
        print("\n✗ Candlestick timezone fix test failed!")
        sys.exit(1)
