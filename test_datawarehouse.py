#!/usr/bin/env python3
"""
Test script for the DataWarehouse functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataWarehouseTest")

def test_datawarehouse():
    """Test the DataWarehouse functionality"""
    try:
        from datawarehouse import DataWarehouse
        
        # Create a test data warehouse
        dw = DataWarehouse("test_data")
        
        # Test data consolidation
        logger.info("Testing 1-minute to 5-minute data consolidation...")
        
        # Create sample 1-minute data
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        one_min_data = []
        
        for i in range(10):  # 10 minutes of data
            timestamp = base_time + timedelta(minutes=i)
            price = 24000 + (i * 10) + (i % 3) * 5  # Simulate price movement
            
            one_min_data.append({
                'timestamp': timestamp,
                'open': price,
                'high': price + 5,
                'low': price - 5,
                'close': price + 2,
                'volume': 1000 + i * 100
            })
        
        logger.info(f"Created {len(one_min_data)} 1-minute candles")
        
        # Consolidate to 5-minute data
        consolidated_data = dw.consolidate_1min_to_5min("NSE_INDEX|Nifty 50", one_min_data)
        logger.info(f"Consolidated to {len(consolidated_data)} 5-minute candles")
        
        # Display consolidated data
        for candle in consolidated_data:
            logger.info(f"5-min candle: {candle['timestamp']} - O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}")
        
        # Test data storage
        logger.info("Testing data storage...")
        dw.store_intraday_data("NSE_INDEX|Nifty 50", consolidated_data, 5)
        
        # Test data retrieval
        logger.info("Testing data retrieval...")
        retrieved_data = dw.get_intraday_data("NSE_INDEX|Nifty 50", limit=5)
        logger.info(f"Retrieved {len(retrieved_data)} candles from storage")
        
        if not retrieved_data.empty:
            logger.info("Sample retrieved data:")
            logger.info(retrieved_data.head())
        
        # Test price range calculation
        logger.info("Testing price range calculation...")
        min_price, max_price = dw.get_price_range("NSE_INDEX|Nifty 50", 24)
        if min_price and max_price:
            logger.info(f"Price range (24h): {min_price:.2f} - {max_price:.2f}")
        
        # Test latest price
        logger.info("Testing latest price...")
        latest_price = dw.get_latest_price("NSE_INDEX|Nifty 50")
        if latest_price:
            logger.info(f"Latest price: {latest_price:.2f}")
        
        # Test data summary
        logger.info("Testing data summary...")
        summary = dw.get_data_summary()
        logger.info(f"Data summary: {summary}")
        
        # Clean up test data
        dw.clear_data("NSE_INDEX|Nifty 50")
        logger.info("Cleaned up test data")
        
        logger.info("✓ DataWarehouse test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"DataWarehouse test failed: {e}")
        return False

def test_broker_agent_integration():
    """Test broker agent integration with data warehouse"""
    try:
        from broker_agent import BrokerAgent
        from datawarehouse import datawarehouse
        
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
                # Return mock data
                base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
                return [{
                    'timestamp': base_time,
                    'open': 24000.0,
                    'high': 24050.0,
                    'low': 23950.0,
                    'close': 24025.0,
                    'volume': 1000
                }]
            
            def get_ohlc_historical_data(self, instrument, interval="day", start_time=None, end_time=None):
                # Return mock data
                base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                return [{
                    'timestamp': base_time,
                    'open': 24000.0,
                    'high': 24100.0,
                    'low': 23900.0,
                    'close': 24050.0,
                    'volume': 5000
                }]
        
        logger.info("Testing broker agent integration...")
        
        # Create mock agent
        agent = MockBrokerAgent()
        
        # Test data consolidation
        one_min_data = agent.get_ohlc_intraday_data("NSE_INDEX|Nifty 50")
        consolidated = agent.consolidate_1min_to_5min("NSE_INDEX|Nifty 50", one_min_data)
        logger.info(f"Consolidated {len(one_min_data)} 1-min candles to {len(consolidated)} 5-min candles")
        
        # Test data storage
        agent.store_ohlc_data("NSE_INDEX|Nifty 50", consolidated, "intraday", 5)
        logger.info("Stored consolidated data")
        
        # Test data retrieval
        stored_data = agent.get_stored_ohlc_data("NSE_INDEX|Nifty 50", "intraday")
        logger.info(f"Retrieved {len(stored_data)} candles from storage")
        
        # Test price range
        min_price, max_price = agent.get_price_range("NSE_INDEX|Nifty 50")
        if min_price and max_price:
            logger.info(f"Price range: {min_price:.2f} - {max_price:.2f}")
        
        logger.info("✓ Broker agent integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Broker agent integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting DataWarehouse tests...")
    
    success = True
    
    # Test 1: DataWarehouse functionality
    if not test_datawarehouse():
        success = False
    
    # Test 2: Broker agent integration
    if not test_broker_agent_integration():
        success = False
    
    if success:
        logger.info("🎉 All tests passed!")
    else:
        logger.error("❌ Some tests failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
