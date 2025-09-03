#!/usr/bin/env python3
"""
Demonstration script showing the dynamic Y-axis scaling functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("YAxisScalingDemo")

def demo_y_axis_scaling():
    """Demonstrate the Y-axis scaling functionality"""
    try:
        from datawarehouse import datawarehouse
        
        logger.info("🎯 Demonstrating Dynamic Y-Axis Scaling")
        logger.info("=" * 50)
        
        # Create sample data with different price ranges
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        # Scenario 1: Normal price range (Nifty around 24,000)
        logger.info("📊 Scenario 1: Normal Nifty Price Range (24,000 - 24,100)")
        normal_data = []
        for i in range(5):
            timestamp = base_time + timedelta(minutes=i*5)
            base_price = 24000 + i * 20
            normal_data.append({
                'timestamp': timestamp,
                'open': base_price,
                'high': base_price + 10,
                'low': base_price - 10,
                'close': base_price + 5,
                'volume': 1000
            })
        
        datawarehouse.store_intraday_data("NSE_INDEX|Nifty 50", normal_data, 5)
        min_price, max_price = datawarehouse.get_price_range("NSE_INDEX|Nifty 50", 24)
        logger.info(f"   Price Range: {min_price:.2f} - {max_price:.2f}")
        logger.info(f"   Range Width: {max_price - min_price:.2f} points")
        
        # Scenario 2: Wide price range (market volatility)
        logger.info("\n📊 Scenario 2: Wide Price Range (23,500 - 24,500)")
        wide_data = []
        for i in range(5):
            timestamp = base_time + timedelta(minutes=(i+5)*5)
            base_price = 23500 + i * 250  # Much wider range
            wide_data.append({
                'timestamp': timestamp,
                'open': base_price,
                'high': base_price + 50,
                'low': base_price - 50,
                'close': base_price + 25,
                'volume': 2000
            })
        
        datawarehouse.store_intraday_data("NSE_INDEX|Nifty 50", wide_data, 5)
        min_price, max_price = datawarehouse.get_price_range("NSE_INDEX|Nifty 50", 24)
        logger.info(f"   Price Range: {min_price:.2f} - {max_price:.2f}")
        logger.info(f"   Range Width: {max_price - min_price:.2f} points")
        
        # Scenario 3: Narrow price range (low volatility)
        logger.info("\n📊 Scenario 3: Narrow Price Range (24,000 - 24,020)")
        narrow_data = []
        for i in range(5):
            timestamp = base_time + timedelta(minutes=(i+10)*5)
            base_price = 24000 + i * 4  # Very narrow range
            narrow_data.append({
                'timestamp': timestamp,
                'open': base_price,
                'high': base_price + 2,
                'low': base_price - 2,
                'close': base_price + 1,
                'volume': 500
            })
        
        datawarehouse.store_intraday_data("NSE_INDEX|Nifty 50", narrow_data, 5)
        min_price, max_price = datawarehouse.get_price_range("NSE_INDEX|Nifty 50", 24)
        logger.info(f"   Price Range: {min_price:.2f} - {max_price:.2f}")
        logger.info(f"   Range Width: {max_price - min_price:.2f} points")
        
        # Show how Y-axis scaling would work
        logger.info("\n🎨 Y-Axis Scaling Behavior:")
        logger.info("   • Chart automatically adjusts Y-axis limits based on price range")
        logger.info("   • Adds 5% padding above and below the range for better visualization")
        logger.info("   • Updates in real-time as new data arrives")
        logger.info("   • Ensures all price movements are visible without manual adjustment")
        
        # Demonstrate padding calculation
        final_min, final_max = datawarehouse.get_price_range("NSE_INDEX|Nifty 50", 24)
        if final_min and final_max:
            price_range = final_max - final_min
            padding = price_range * 0.05
            y_min = final_min - padding
            y_max = final_max + padding
            
            logger.info(f"\n📐 Final Y-Axis Calculation:")
            logger.info(f"   Data Range: {final_min:.2f} - {final_max:.2f}")
            logger.info(f"   Range Width: {price_range:.2f}")
            logger.info(f"   5% Padding: {padding:.2f}")
            logger.info(f"   Y-Axis Limits: {y_min:.2f} - {y_max:.2f}")
        
        # Clean up
        datawarehouse.clear_data("NSE_INDEX|Nifty 50")
        
        logger.info("\n✅ Y-axis scaling demonstration completed!")
        return True
        
    except Exception as e:
        logger.error(f"Y-axis scaling demonstration failed: {e}")
        return False

def demo_data_consolidation():
    """Demonstrate the 1-minute to 5-minute data consolidation"""
    try:
        from datawarehouse import datawarehouse
        
        logger.info("\n🔄 Demonstrating 1-Minute to 5-Minute Data Consolidation")
        logger.info("=" * 60)
        
        # Create 1-minute data
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        one_min_data = []
        
        logger.info("📊 Creating 1-minute data (10 minutes):")
        for i in range(10):
            timestamp = base_time + timedelta(minutes=i)
            price = 24000 + (i * 5) + (i % 2) * 3  # Simulate price movement
            one_min_data.append({
                'timestamp': timestamp,
                'open': price,
                'high': price + 2,
                'low': price - 2,
                'close': price + 1,
                'volume': 100 + i * 10
            })
            logger.info(f"   {timestamp.strftime('%H:%M')} - Price: {price:.2f}, Volume: {100 + i * 10}")
        
        # Consolidate to 5-minute data
        logger.info("\n🔄 Consolidating to 5-minute candles:")
        consolidated = datawarehouse.consolidate_1min_to_5min("NSE_INDEX|Nifty 50", one_min_data)
        
        for candle in consolidated:
            logger.info(f"   {candle['timestamp'].strftime('%H:%M')} - O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}")
        
        logger.info(f"\n📈 Consolidation Summary:")
        logger.info(f"   Input: {len(one_min_data)} 1-minute candles")
        logger.info(f"   Output: {len(consolidated)} 5-minute candles")
        logger.info(f"   Compression Ratio: {len(one_min_data)/len(consolidated):.1f}:1")
        
        return True
        
    except Exception as e:
        logger.error(f"Data consolidation demonstration failed: {e}")
        return False

def main():
    """Run all demonstrations"""
    logger.info("🚀 Starting DataWarehouse Demonstrations")
    logger.info("=" * 60)
    
    success = True
    
    # Demo 1: Y-axis scaling
    if not demo_y_axis_scaling():
        success = False
    
    # Demo 2: Data consolidation
    if not demo_data_consolidation():
        success = False
    
    if success:
        logger.info("\n🎉 All demonstrations completed successfully!")
        logger.info("\n💡 Key Benefits:")
        logger.info("   • Dynamic Y-axis scaling adapts to any price range")
        logger.info("   • 1-minute data automatically consolidated to 5-minute candles")
        logger.info("   • Real-time updates with proper price scaling")
        logger.info("   • No manual chart adjustment needed")
    else:
        logger.error("\n❌ Some demonstrations failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
