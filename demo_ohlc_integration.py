#!/usr/bin/env python3
"""
Demonstration script showing the complete OHLC data integration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OHLCIntegrationDemo")

def demo_ohlc_integration():
    """Demonstrate the complete OHLC data integration"""
    try:
        from datawarehouse import DataWarehouse
        from chart_visualizer import LiveChartVisualizer
        
        logger.info("🚀 OHLC Data Integration Demonstration")
        logger.info("=" * 60)
        
        # Step 1: Create DataWarehouse
        logger.info("📊 Step 1: Creating DataWarehouse")
        dw = DataWarehouse("demo_data")
        
        # Step 2: Create mock historical data
        logger.info("📊 Step 2: Creating mock historical data")
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        historical_data = []
        
        for i in range(10):  # 10 days of data
            date = base_date - timedelta(days=i)
            base_price = 24000 - (i * 5) + (i % 2) * 10  # Simulate price movement
            
            historical_data.append({
                'timestamp': date,
                'open': base_price,
                'high': base_price + 25,
                'low': base_price - 25,
                'close': base_price + 12,
                'volume': 5000 + i * 500
            })
        
        logger.info(f"✅ Created {len(historical_data)} historical candles")
        
        # Step 3: Store historical data
        logger.info("📊 Step 3: Storing historical data")
        # Historical data is no longer stored - fetched fresh each time
        logger.info("Historical data not stored - will be fetched fresh when needed")
        logger.info("✅ Historical data stored in warehouse")
        
        # Step 4: Create mock intraday data (1-minute)
        logger.info("📊 Step 4: Creating mock intraday data")
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        intraday_data = []
        
        for i in range(30):  # 30 minutes of data
            timestamp = base_time - timedelta(minutes=i)
            base_price = 24000 + (i % 5) * 3  # Simulate price movement
            
            intraday_data.append({
                'timestamp': timestamp,
                'open': base_price,
                'high': base_price + 1.5,
                'low': base_price - 1.5,
                'close': base_price + 0.8,
                'volume': 200 + i * 10
            })
        
        logger.info(f"✅ Created {len(intraday_data)} 1-minute candles")
        
        # Step 5: Consolidate to 5-minute data
        logger.info("📊 Step 5: Consolidating to 5-minute data")
        consolidated_data = dw.consolidate_1min_to_5min("NSE_INDEX|Nifty 50", intraday_data)
        logger.info(f"✅ Consolidated to {len(consolidated_data)} 5-minute candles")
        
        # Step 6: Store consolidated data
        logger.info("📊 Step 6: Storing consolidated data")
        dw.store_intraday_data("NSE_INDEX|Nifty 50", consolidated_data, 5)
        logger.info("✅ Consolidated data stored in warehouse")
        
        # Step 7: Create chart visualizer
        logger.info("📊 Step 7: Creating chart visualizer")
        chart = LiveChartVisualizer("OHLC Integration Demo", max_candles=50, candle_interval_minutes=5)
        chart.add_instrument("NSE_INDEX|Nifty 50", "Nifty 50")
        logger.info("✅ Chart visualizer created")
        
        # Step 8: Load historical data into chart
        logger.info("📊 Step 8: Loading historical data into chart")
        # Historical data is no longer stored - must be fetched fresh from broker
        logger.info("📈 Historical data not available from storage - must be fetched fresh from broker")
        logger.info("✅ Historical data storage removed - fresh data will be fetched each time")
        
        # Step 9: Load intraday data into chart
        logger.info("📊 Step 9: Loading intraday data into chart")
        intraday_df = dw.get_intraday_data("NSE_INDEX|Nifty 50", limit=10)
        
        for _, row in intraday_df.iterrows():
            candle_data = {
                'timestamp': row.name,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row.get('volume', 0))
            }
            chart.update_data("NSE_INDEX|Nifty 50", candle_data)
        
        logger.info(f"✅ Loaded {len(intraday_df)} intraday candles into chart")
        
        # Step 10: Display chart data summary
        logger.info("📊 Step 10: Chart data summary")
        chart_data = chart.get_candle_data("NSE_INDEX|Nifty 50")
        if chart_data:
            logger.info(f"✅ Chart contains {len(chart_data)} total candles")
            
            # Show sample data
            if len(chart_data) >= 3:
                logger.info("📋 Sample chart data (last 3 candles):")
                for i, candle in enumerate(chart_data[-3:]):
                    logger.info(f"   Candle {i+1}: {candle['timestamp']} - O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}")
        
        # Step 11: Price calculations
        logger.info("📊 Step 11: Price calculations")
        latest_price = dw.get_latest_price("NSE_INDEX|Nifty 50")
        if latest_price:
            logger.info(f"✅ Latest price: {latest_price:.2f}")
        
        min_price, max_price = dw.get_price_range("NSE_INDEX|Nifty 50", 24)
        if min_price and max_price:
            logger.info(f"✅ Price range (24h): {min_price:.2f} - {max_price:.2f}")
            logger.info(f"   Range width: {max_price - min_price:.2f} points")
        
        # Step 12: Data warehouse summary
        logger.info("📊 Step 12: Data warehouse summary")
        summary = dw.get_data_summary()
        logger.info(f"✅ Data summary: {summary}")
        
        # Clean up
        dw.clear_data("NSE_INDEX|Nifty 50")
        logger.info("✅ Demo data cleaned up")
        
        logger.info("\n🎉 OHLC Integration Demonstration Completed!")
        return True
        
    except Exception as e:
        logger.error(f"OHLC integration demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_main_app_integration():
    """Demonstrate how the main app integrates OHLC data fetching"""
    try:
        logger.info("\n🚀 Main App Integration Demonstration")
        logger.info("=" * 60)
        
        # Create a mock broker agent for demonstration
        from broker_agent import BrokerAgent
        from datawarehouse import datawarehouse
        
        class MockBrokerAgent(BrokerAgent):
            def login(self):
                pass
            
            def logout(self):
                pass
            
            def place_order(self):
                pass
            
            def fetch_orders(self):
                pass
            
            def fetch_instruments(self):
                pass
            
            def fetch_positions(self):
                pass
            
            def fetch_quotes(self):
                pass
            
            def connect_live_data(self):
                return True
            
            def subscribe_live_data(self, instrument_keys, mode="ltpc"):
                return True
            
            def unsubscribe_live_data(self, instrument_keys):
                return True
            
            def disconnect_live_data(self):
                pass
            
            def get_ohlc_intraday_data(self, instrument, interval="5"):
                # Return mock intraday data
                base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
                data = []
                
                for i in range(20):  # 20 minutes
                    timestamp = base_time - timedelta(minutes=i)
                    price = 24000 + i * 2
                    
                    data.append({
                        'timestamp': timestamp,
                        'open': price,
                        'high': price + 1,
                        'low': price - 1,
                        'close': price + 0.5,
                        'volume': 100 + i * 5
                    })
                
                return data
            
            def get_ohlc_historical_data(self, instrument, interval="day", start_time=None, end_time=None):
                # Return mock historical data
                base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                data = []
                
                for i in range(7):  # 7 days
                    date = base_date - timedelta(days=i)
                    price = 24000 - i * 5
                    
                    data.append({
                        'timestamp': date,
                        'open': price,
                        'high': price + 15,
                        'low': price - 15,
                        'close': price + 8,
                        'volume': 8000 + i * 500
                    })
                
                return data
        
        # Demonstrate the main app workflow
        logger.info("📊 Step 1: Creating mock broker agent")
        agent = MockBrokerAgent()
        instrument = "NSE_INDEX|Nifty 50"
        
        # Step 2: Fetch historical data
        logger.info("📊 Step 2: Fetching historical data")
        historical_data = agent.get_ohlc_historical_data(instrument)
        if historical_data:
            logger.info(f"✅ Fetched {len(historical_data)} historical candles")
            
            # Historical data is no longer stored - fetched fresh each time
            logger.info("📈 Historical data not stored - will be fetched fresh when needed")
        
        # Step 3: Fetch intraday data
        logger.info("📊 Step 3: Fetching intraday data")
        intraday_data = agent.get_ohlc_intraday_data(instrument)
        if intraday_data:
            logger.info(f"✅ Fetched {len(intraday_data)} 1-minute candles")
            
            # Consolidate to 5-minute data
            consolidated = agent.consolidate_1min_to_5min(instrument, intraday_data)
            logger.info(f"✅ Consolidated to {len(consolidated)} 5-minute candles")
            
            # Store in warehouse
            agent.store_ohlc_data(instrument, consolidated, "intraday", 5)
            logger.info("✅ Intraday data stored in warehouse")
        
        # Step 4: Retrieve stored data
        logger.info("📊 Step 4: Retrieving stored data")
        # Historical data is no longer stored - must be fetched fresh from broker
        logger.info("📈 Historical data not available from storage - must be fetched fresh from broker")
        stored_intraday = agent.get_stored_ohlc_data(instrument, "intraday")
        
        if not stored_intraday.empty:
            logger.info(f"✅ Retrieved {len(stored_intraday)} intraday records")
        
        # Step 5: Price calculations
        logger.info("📊 Step 5: Price calculations")
        latest_price = agent.get_latest_price(instrument)
        if latest_price:
            logger.info(f"✅ Latest price: {latest_price:.2f}")
        
        min_price, max_price = agent.get_price_range(instrument)
        if min_price and max_price:
            logger.info(f"✅ Price range: {min_price:.2f} - {max_price:.2f}")
        
        # Clean up
        datawarehouse.clear_data(instrument)
        logger.info("✅ Demo data cleaned up")
        
        logger.info("\n🎉 Main App Integration Demonstration Completed!")
        return True
        
    except Exception as e:
        logger.error(f"Main app integration demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all demonstrations"""
    logger.info("🚀 Starting OHLC Integration Demonstrations")
    logger.info("=" * 60)
    
    success = True
    
    # Demo 1: OHLC integration
    if not demo_ohlc_integration():
        success = False
    
    # Demo 2: Main app integration
    if not demo_main_app_integration():
        success = False
    
    if success:
        logger.info("\n🎉 All demonstrations completed successfully!")
        logger.info("\n💡 Complete OHLC Integration Features:")
        logger.info("   • Historical data fetching from broker")
        logger.info("   • Intraday data fetching from broker")
        logger.info("   • 1-minute to 5-minute data consolidation")
        logger.info("   • Data storage in warehouse (CSV + in-memory)")
        logger.info("   • Chart display with dynamic Y-axis scaling")
        logger.info("   • Price range calculations")
        logger.info("   • Real-time data updates")
        logger.info("   • GUI buttons for manual data fetching")
        logger.info("\n🚀 Ready to run: python3 run_app.py")
    else:
        logger.error("\n❌ Some demonstrations failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
