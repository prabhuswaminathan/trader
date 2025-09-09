#!/usr/bin/env python3
"""
Test script to verify datawarehouse timer is working and updating chart 2
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from chart_visualizer import TkinterChartApp, LiveChartVisualizer
from datawarehouse import DataWarehouse
from trade_models import Trade, TradeStatus, PositionType, OptionType, TradeLeg
from datetime import datetime
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_iron_condor():
    """Create a test Iron Condor trade"""
    # Create test legs
    legs = [
        TradeLeg(instrument="NIFTY25000CE", instrument_name="NIFTY 25000 CE", option_type=OptionType.CALL, position_type=PositionType.SHORT, strike_price=25000, quantity=1, entry_timestamp=datetime.now(), entry_price=50.0),
        TradeLeg(instrument="NIFTY25100CE", instrument_name="NIFTY 25100 CE", option_type=OptionType.CALL, position_type=PositionType.LONG, strike_price=25100, quantity=1, entry_timestamp=datetime.now(), entry_price=30.0),
        TradeLeg(instrument="NIFTY24900PE", instrument_name="NIFTY 24900 PE", option_type=OptionType.PUT, position_type=PositionType.LONG, strike_price=24900, quantity=1, entry_timestamp=datetime.now(), entry_price=40.0),
        TradeLeg(instrument="NIFTY24800PE", instrument_name="NIFTY 24800 PE", option_type=OptionType.PUT, position_type=PositionType.SHORT, strike_price=24800, quantity=1, entry_timestamp=datetime.now(), entry_price=60.0)
    ]
    
    # Create trade
    trade = Trade(
        trade_id="TEST_IC_001",
        strategy_name="Iron Condor",
        underlying_instrument="NIFTY",
        legs=legs,
        status=TradeStatus.OPEN
    )
    
    return trade

def create_test_payoff_data():
    """Create test payoff data"""
    # Price range from 24500 to 25500
    price_range = list(range(24500, 25501, 50))
    payoffs = []
    
    for price in price_range:
        # Simple Iron Condor payoff calculation
        if price <= 24800:
            payoff = -2000  # Max loss
        elif price <= 24900:
            payoff = -2000 + (price - 24800) * 1  # Loss zone
        elif price <= 25000:
            payoff = -1000  # Profit zone
        elif price <= 25100:
            payoff = -1000 - (price - 25000) * 1  # Loss zone
        else:
            payoff = -2000  # Max loss
        
        payoffs.append(payoff)
    
    return {
        "price_range": price_range,
        "payoffs": payoffs,
        "max_profit": 1000,
        "max_loss": -2000,
        "breakevens": [24800, 25200],
        "current_payoff": -500
    }

def test_datawarehouse_timer():
    """Test datawarehouse timer functionality"""
    try:
        logger.info("Creating datawarehouse...")
        datawarehouse = DataWarehouse()
        
        logger.info("Creating chart visualizer...")
        chart_visualizer = LiveChartVisualizer()
        
        # Add an instrument
        chart_visualizer.add_instrument("NSE_INDEX|Nifty 50", "NIFTY 50")
        
        # Set up datawarehouse reference
        chart_visualizer.set_datawarehouse(datawarehouse)
        
        logger.info("Creating Tkinter app...")
        app = TkinterChartApp(chart_visualizer)
        
        # Create test data
        trade = create_test_iron_condor()
        payoff_data = create_test_payoff_data()
        initial_spot_price = 24950
        
        logger.info("Displaying Iron Condor strategy...")
        app.display_trade_payoff_graph(trade, initial_spot_price, payoff_data)
        
        # Start the datawarehouse timer
        logger.info("Starting datawarehouse timer...")
        chart_visualizer.start_datawarehouse_timer()
        
        # Store different spot prices in datawarehouse over time
        test_prices = [25000, 25050, 25100, 25075, 25025, 25090, 25010]
        
        logger.info("Storing test prices in datawarehouse...")
        for i, price in enumerate(test_prices):
            logger.info(f"Storing price {price} in datawarehouse...")
            datawarehouse.store_latest_price("NSE_INDEX|Nifty 50", price, 1000, 'live_feed')
            time.sleep(6)  # Wait 6 seconds between updates (timer runs every 5 seconds)
        
        logger.info("Chart 2 with datawarehouse timer updates should now be displayed!")
        logger.info("The red dashed line should have moved to show different spot prices every 5 seconds.")
        logger.info("Close the window to exit.")
        
        # Start the GUI
        app.root.mainloop()
        
    except Exception as e:
        logger.error(f"Error testing datawarehouse timer: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_datawarehouse_timer()
