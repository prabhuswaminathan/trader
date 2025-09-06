#!/usr/bin/env python3
"""
Test script for the strategy manager functionality.
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Add the code directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from strategy_manager import StrategyManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestStrategyManager")

def test_strategy_manager():
    """Test the strategy manager functionality"""
    try:
        # Load environment variables
        load_dotenv("keys.env")
        access_token = os.getenv("UPSTOX_ACCESS_TOKEN")
        
        if not access_token:
            logger.error("UPSTOX_ACCESS_TOKEN not found in keys.env")
            return
        
        print("=" * 60)
        print("TESTING STRATEGY MANAGER")
        print("=" * 60)
        
        # Initialize strategy manager
        strategy_manager = StrategyManager()
        
        # Test 1: Check open positions
        print("\n1. Checking for open positions...")
        open_positions = strategy_manager.get_open_positions()
        print(f"   Found {len(open_positions)} open positions")
        
        # Test 2: Get current spot price
        print("\n2. Getting current spot price...")
        try:
            strategy_manager.initialize_option_chain(access_token)
            spot_price = strategy_manager.get_current_spot_price()
            print(f"   Current NIFTY spot price: ₹{spot_price:,.2f}")
        except Exception as e:
            print(f"   Error getting spot price: {e}")
            spot_price = 25000  # Fallback
        
        # Test 3: Calculate strikes for Iron Condor
        print("\n3. Calculating Iron Condor strikes...")
        current_strike = strategy_manager.get_nearest_strike(spot_price)
        short_call_strike = current_strike + 400
        short_put_strike = current_strike - 400
        long_call_strike = short_call_strike + 200
        long_put_strike = short_put_strike - 200
        
        print(f"   Current Strike: {current_strike}")
        print(f"   Short Call Strike: {short_call_strike}")
        print(f"   Short Put Strike: {short_put_strike}")
        print(f"   Long Call Strike: {long_call_strike}")
        print(f"   Long Put Strike: {long_put_strike}")
        
        # Test 4: Run full strategy management
        print("\n4. Running full strategy management...")
        result = strategy_manager.manage_positions(access_token)
        
        print(f"\n   Result: {result.get('action_taken')}")
        if result.get('trade_created'):
            print(f"   Trade Created: {result.get('trade_created')}")
        if result.get('plot_path'):
            print(f"   Plot Saved: {result.get('plot_path')}")
        
        print("\n" + "=" * 60)
        print("Strategy manager test completed!")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    test_strategy_manager()

