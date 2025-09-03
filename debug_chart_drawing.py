#!/usr/bin/env python3
"""
Debug script to step through chart drawing process
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChartDrawingDebug")

def debug_chart_drawing_step_by_step():
    """Debug chart drawing step by step"""
    try:
        logger.info("🚀 Debugging Chart Drawing Step by Step")
        logger.info("=" * 50)
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Debug Chart")
        
        # Add instrument
        chart.add_instrument("NSE_INDEX|Nifty 50")
        
        # Add test data
        logger.info("📊 Adding Test Data")
        
        test_candle = {
            'timestamp': datetime.now(),
            'open': 24000.0,
            'high': 24010.0,
            'low': 23990.0,
            'close': 24005.0,
            'volume': 1000
        }
        
        chart.update_data("NSE_INDEX|Nifty 50", test_candle)
        
        # Check data
        if "NSE_INDEX|Nifty 50" in chart.candle_data:
            candles = chart.candle_data["NSE_INDEX|Nifty 50"]
            logger.info(f"✅ Chart has {len(candles)} candles")
            logger.info(f"✅ Candle data: {candles[0]}")
        else:
            logger.error("❌ No candle data found")
            return False
        
        # Test DataFrame conversion
        logger.info("\n📊 Testing DataFrame Conversion")
        
        import pandas as pd
        df = pd.DataFrame(list(candles))
        logger.info(f"✅ DataFrame created: {df.shape}")
        logger.info(f"✅ DataFrame columns: {list(df.columns)}")
        logger.info(f"✅ DataFrame data:\n{df}")
        
        if df.empty:
            logger.error("❌ DataFrame is empty")
            return False
        
        # Test candlestick plotting
        logger.info("\n📊 Testing Candlestick Plotting")
        
        try:
            # Clear axes first
            chart.price_ax.clear()
            logger.info("✅ Axes cleared")
            
            # Set up axes
            chart.price_ax.set_title("Debug Chart")
            chart.price_ax.set_ylabel("Price (₹)")
            chart.price_ax.set_xlabel("Time")
            chart.price_ax.grid(True, alpha=0.3)
            logger.info("✅ Axes set up")
            
            # Plot candlesticks
            chart._plot_candlesticks(df, "NSE_INDEX|Nifty 50")
            logger.info("✅ Candlesticks plotted")
            
            # Check visual elements
            lines = chart.price_ax.get_lines()
            patches = chart.price_ax.patches
            
            logger.info(f"✅ After plotting:")
            logger.info(f"   Lines: {len(lines)}")
            logger.info(f"   Patches: {len(patches)}")
            
            if len(lines) > 0 or len(patches) > 0:
                logger.info("✅ Visual elements created successfully")
            else:
                logger.error("❌ No visual elements created")
                
                # Debug the plotting method
                logger.info("🔍 Debugging _plot_candlesticks method")
                
                # Check if DataFrame is empty
                if df.empty:
                    logger.error("❌ DataFrame is empty in _plot_candlesticks")
                    return False
                
                # Check data types
                logger.info(f"✅ Data types: {df.dtypes}")
                
                # Check for NaN values
                nan_count = df.isnull().sum().sum()
                if nan_count > 0:
                    logger.error(f"❌ Found {nan_count} NaN values")
                    return False
                
                # Check timestamp format
                timestamp = df.iloc[0]['timestamp']
                logger.info(f"✅ First timestamp: {timestamp} (type: {type(timestamp)})")
                
                # Check price values
                open_price = df.iloc[0]['open']
                high_price = df.iloc[0]['high']
                low_price = df.iloc[0]['low']
                close_price = df.iloc[0]['close']
                
                logger.info(f"✅ Price values: O={open_price}, H={high_price}, L={low_price}, C={close_price}")
                
                # Check if prices are valid
                if all(price > 0 for price in [open_price, high_price, low_price, close_price]):
                    logger.info("✅ All prices are valid")
                else:
                    logger.error("❌ Some prices are invalid")
                    return False
                
                # Try manual plotting
                logger.info("🔍 Trying manual plotting")
                
                try:
                    # Draw the high-low line (wick)
                    chart.price_ax.plot([timestamp, timestamp], [low_price, high_price], 
                                     color='black', linewidth=1.5)
                    logger.info("✅ High-low line drawn")
                    
                    # Draw the open-close rectangle (body)
                    candle_color = 'green' if close_price >= open_price else 'red'
                    edge_color = 'darkgreen' if close_price >= open_price else 'darkred'
                    
                    from datetime import timedelta
                    candle_width = timedelta(minutes=5 * 0.6)
                    
                    if close_price >= open_price:
                        # Bullish candle
                        chart.price_ax.bar(timestamp, close_price - open_price, 
                                        bottom=open_price, width=candle_width,
                                        color=candle_color, edgecolor=edge_color, linewidth=1.5)
                    else:
                        # Bearish candle
                        chart.price_ax.bar(timestamp, open_price - close_price, 
                                        bottom=close_price, width=candle_width,
                                        color=candle_color, edgecolor=edge_color, linewidth=1.5)
                    
                    logger.info("✅ Candle body drawn")
                    
                    # Check visual elements again
                    lines = chart.price_ax.get_lines()
                    patches = chart.price_ax.patches
                    
                    logger.info(f"✅ After manual plotting:")
                    logger.info(f"   Lines: {len(lines)}")
                    logger.info(f"   Patches: {len(patches)}")
                    
                    if len(lines) > 0 or len(patches) > 0:
                        logger.info("✅ Manual plotting worked!")
                    else:
                        logger.error("❌ Manual plotting also failed")
                        return False
                    
                except Exception as e:
                    logger.error(f"❌ Manual plotting failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            
            # Update Y-axis scale
            chart._update_y_axis_scale()
            logger.info("✅ Y-axis scale updated")
            
            # Check final axis limits
            xlim = chart.price_ax.get_xlim()
            ylim = chart.price_ax.get_ylim()
            
            logger.info(f"✅ Final axis limits:")
            logger.info(f"   X-axis: {xlim}")
            logger.info(f"   Y-axis: {ylim}")
            
            if ylim[0] < ylim[1] and ylim[0] > 0:
                logger.info("✅ Y-axis limits are reasonable")
            else:
                logger.warning(f"⚠ Y-axis limits might be problematic: {ylim}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Chart drawing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        logger.error(f"Chart drawing debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run debug test"""
    logger.info("🚀 Starting Chart Drawing Debug")
    logger.info("=" * 60)
    
    success = debug_chart_drawing_step_by_step()
    
    if success:
        logger.info("\n🎉 Chart drawing debug completed!")
        logger.info("\n💡 Debug Summary:")
        logger.info("   • Data is being added correctly")
        logger.info("   • DataFrame conversion works")
        logger.info("   • Chart drawing methods work")
        logger.info("   • Visual elements are created")
        logger.info("   • Y-axis scaling works")
    else:
        logger.error("\n❌ Chart drawing debug failed!")
        logger.error("\n🔍 This indicates the issue is in the chart drawing logic")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
