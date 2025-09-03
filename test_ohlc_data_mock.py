#!/usr/bin/env python3
"""
Test script for OHLC data fetching with mock data (no external dependencies)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OHLCDataMockTest")

def test_datawarehouse_functionality():
    """Test the data warehouse functionality with mock data"""
    try:
        from datawarehouse import DataWarehouse
        
        logger.info("🚀 Testing DataWarehouse with Mock OHLC Data")
        logger.info("=" * 60)
        
        # Create data warehouse
        dw = DataWarehouse("test_data")
        
        # Create mock historical data
        logger.info("📊 Creating mock historical data...")
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        historical_data = []
        
        for i in range(30):  # 30 days of data
            date = base_date - timedelta(days=i)
            base_price = 24000 - (i * 10) + (i % 3) * 20  # Simulate price movement
            
            historical_data.append({
                'timestamp': date,
                'open': base_price,
                'high': base_price + 50,
                'low': base_price - 50,
                'close': base_price + 25,
                'volume': 10000 + i * 100
            })
        
        logger.info(f"✅ Created {len(historical_data)} historical candles")
        
        # Store historical data
        dw.store_historical_data("NSE_INDEX|Nifty 50", historical_data)
        logger.info("✅ Historical data stored in warehouse")
        
        # Create mock intraday data (1-minute)
        logger.info("📊 Creating mock intraday data...")
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        intraday_data = []
        
        for i in range(60):  # 60 minutes of data
            timestamp = base_time - timedelta(minutes=i)
            base_price = 24000 + (i % 10) * 5  # Simulate price movement
            
            intraday_data.append({
                'timestamp': timestamp,
                'open': base_price,
                'high': base_price + 2,
                'low': base_price - 2,
                'close': base_price + 1,
                'volume': 100 + i
            })
        
        logger.info(f"✅ Created {len(intraday_data)} 1-minute candles")
        
        # Test consolidation
        logger.info("🔄 Testing 1-minute to 5-minute consolidation...")
        consolidated_data = dw.consolidate_1min_to_5min("NSE_INDEX|Nifty 50", intraday_data)
        logger.info(f"✅ Consolidated to {len(consolidated_data)} 5-minute candles")
        
        # Store consolidated data
        dw.store_intraday_data("NSE_INDEX|Nifty 50", consolidated_data, 5)
        logger.info("✅ Consolidated data stored in warehouse")
        
        # Test data retrieval
        logger.info("📊 Testing data retrieval...")
        
        # Get historical data
        historical_df = dw.get_historical_data("NSE_INDEX|Nifty 50", limit=5)
        if not historical_df.empty:
            logger.info(f"✅ Retrieved {len(historical_df)} historical candles")
            logger.info(f"   Date range: {historical_df.index[0]} to {historical_df.index[-1]}")
            logger.info(f"   Price range: {historical_df['low'].min():.2f} - {historical_df['high'].max():.2f}")
        
        # Get intraday data
        intraday_df = dw.get_intraday_data("NSE_INDEX|Nifty 50", limit=5)
        if not intraday_df.empty:
            logger.info(f"✅ Retrieved {len(intraday_df)} intraday candles")
            logger.info(f"   Time range: {intraday_df.index[0]} to {intraday_df.index[-1]}")
            logger.info(f"   Price range: {intraday_df['low'].min():.2f} - {intraday_df['high'].max():.2f}")
        
        # Test price calculations
        logger.info("💰 Testing price calculations...")
        
        latest_price = dw.get_latest_price("NSE_INDEX|Nifty 50")
        if latest_price:
            logger.info(f"✅ Latest price: {latest_price:.2f}")
        
        min_price, max_price = dw.get_price_range("NSE_INDEX|Nifty 50", 24)
        if min_price and max_price:
            logger.info(f"✅ Price range (24h): {min_price:.2f} - {max_price:.2f}")
            logger.info(f"   Range width: {max_price - min_price:.2f} points")
        
        # Test data summary
        summary = dw.get_data_summary()
        logger.info(f"📊 Data summary: {summary}")
        
        # Clean up
        dw.clear_data("NSE_INDEX|Nifty 50")
        logger.info("✅ Test data cleaned up")
        
        logger.info("\n🎉 DataWarehouse functionality test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"DataWarehouse functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chart_visualizer_integration():
    """Test chart visualizer with mock data"""
    try:
        from chart_visualizer import LiveChartVisualizer
        
        logger.info("\n🎨 Testing Chart Visualizer Integration")
        logger.info("=" * 50)
        
        # Create chart visualizer
        chart = LiveChartVisualizer("Mock Data Test", max_candles=50, candle_interval_minutes=5)
        
        # Add instrument
        instrument = "NSE_INDEX|Nifty 50"
        chart.add_instrument(instrument, "Nifty 50")
        logger.info(f"✅ Added instrument: {instrument}")
        
        # Create mock candle data
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        mock_candles = []
        
        for i in range(20):  # 20 candles
            timestamp = base_time - timedelta(minutes=i*5)
            base_price = 24000 + (i % 5) * 10  # Simulate price movement
            
            candle_data = {
                'timestamp': timestamp,
                'open': base_price,
                'high': base_price + 5,
                'low': base_price - 5,
                'close': base_price + 2,
                'volume': 1000 + i * 50
            }
            mock_candles.append(candle_data)
        
        logger.info(f"✅ Created {len(mock_candles)} mock candles")
        
        # Add data to chart
        for candle in mock_candles:
            chart.update_data(instrument, candle)
        
        logger.info("✅ Added mock data to chart")
        
        # Test chart data retrieval
        chart_data = chart.get_candle_data(instrument)
        if chart_data:
            logger.info(f"✅ Chart contains {len(chart_data)} candles")
            
            # Show sample data
            if len(chart_data) >= 3:
                logger.info("📋 Sample chart data (last 3 candles):")
                for i, candle in enumerate(chart_data[-3:]):
                    logger.info(f"   Candle {i+1}: O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}")
        
        # Test current prices
        current_prices = chart.get_current_prices()
        if current_prices:
            logger.info(f"✅ Current prices: {current_prices}")
        
        logger.info("\n🎉 Chart visualizer integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Chart visualizer integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_broker_agent_interface():
    """Test the broker agent interface with mock implementation"""
    try:
        from broker_agent import BrokerAgent
        from datawarehouse import datawarehouse
        
        logger.info("\n🔧 Testing Broker Agent Interface")
        logger.info("=" * 50)
        
        # Create a mock broker agent
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
            
            def get_ohlc_intraday_data(self, instrument, interval="1minute", start_time=None, end_time=None):
                # Return mock intraday data
                base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
                data = []
                
                for i in range(10):  # 10 minutes
                    timestamp = base_time - timedelta(minutes=i)
                    price = 24000 + i * 2
                    
                    data.append({
                        'timestamp': timestamp,
                        'open': price,
                        'high': price + 1,
                        'low': price - 1,
                        'close': price + 0.5,
                        'volume': 100 + i * 10
                    })
                
                return data
            
            def get_ohlc_historical_data(self, instrument, interval="day", start_time=None, end_time=None):
                # Return mock historical data
                base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                data = []
                
                for i in range(5):  # 5 days
                    date = base_date - timedelta(days=i)
                    price = 24000 - i * 10
                    
                    data.append({
                        'timestamp': date,
                        'open': price,
                        'high': price + 20,
                        'low': price - 20,
                        'close': price + 10,
                        'volume': 10000 + i * 1000
                    })
                
                return data
        
        # Test the mock agent
        agent = MockBrokerAgent()
        instrument = "NSE_INDEX|Nifty 50"
        
        # Test intraday data
        logger.info("📊 Testing get_ohlc_intraday_data()...")
        intraday_data = agent.get_ohlc_intraday_data(instrument)
        if intraday_data:
            logger.info(f"✅ Intraday data method returned {len(intraday_data)} records")
        
        # Test historical data
        logger.info("📊 Testing get_ohlc_historical_data()...")
        historical_data = agent.get_ohlc_historical_data(instrument)
        if historical_data:
            logger.info(f"✅ Historical data method returned {len(historical_data)} records")
        
        # Test data consolidation
        logger.info("🔄 Testing data consolidation...")
        if intraday_data:
            consolidated = agent.consolidate_1min_to_5min(instrument, intraday_data)
            logger.info(f"✅ Consolidation: {len(intraday_data)} 1-min → {len(consolidated)} 5-min candles")
        
        # Test data storage
        logger.info("💾 Testing data storage...")
        if historical_data:
            agent.store_ohlc_data(instrument, historical_data, "historical")
            logger.info("✅ Historical data stored")
        
        if intraday_data:
            agent.store_ohlc_data(instrument, intraday_data, "intraday", 1)
            logger.info("✅ Intraday data stored")
        
        # Test data retrieval
        logger.info("📊 Testing data retrieval...")
        stored_historical = agent.get_stored_ohlc_data(instrument, "historical")
        if not stored_historical.empty:
            logger.info(f"✅ Retrieved {len(stored_historical)} historical records")
        
        stored_intraday = agent.get_stored_ohlc_data(instrument, "intraday")
        if not stored_intraday.empty:
            logger.info(f"✅ Retrieved {len(stored_intraday)} intraday records")
        
        # Test price calculations
        latest_price = agent.get_latest_price(instrument)
        if latest_price:
            logger.info(f"✅ Latest price: {latest_price:.2f}")
        
        min_price, max_price = agent.get_price_range(instrument)
        if min_price and max_price:
            logger.info(f"✅ Price range: {min_price:.2f} - {max_price:.2f}")
        
        # Clean up
        datawarehouse.clear_data(instrument)
        logger.info("✅ Test data cleaned up")
        
        logger.info("\n🎉 Broker agent interface test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Broker agent interface test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting OHLC Data Mock Tests")
    logger.info("=" * 60)
    
    success = True
    
    # Test 1: DataWarehouse functionality
    if not test_datawarehouse_functionality():
        success = False
    
    # Test 2: Chart visualizer integration
    if not test_chart_visualizer_integration():
        success = False
    
    # Test 3: Broker agent interface
    if not test_broker_agent_interface():
        success = False
    
    if success:
        logger.info("\n🎉 All mock tests passed!")
        logger.info("\n💡 Key Features Demonstrated:")
        logger.info("   • DataWarehouse data storage and retrieval")
        logger.info("   • 1-minute to 5-minute data consolidation")
        logger.info("   • Chart visualizer integration")
        logger.info("   • Broker agent interface implementation")
        logger.info("   • Price range calculations")
        logger.info("   • Dynamic Y-axis scaling preparation")
    else:
        logger.error("\n❌ Some mock tests failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
