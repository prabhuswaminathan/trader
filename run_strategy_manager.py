#!/usr/bin/env python3
"""
Main script to run the strategy manager and handle positions.
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
logger = logging.getLogger("StrategyManagerApp")

def main():
    """Main function to run the strategy manager"""
    try:
        # Load environment variables
        load_dotenv("keys.env")
        access_token = os.getenv("UPSTOX_ACCESS_TOKEN")
        
        if not access_token:
            logger.error("UPSTOX_ACCESS_TOKEN not found in keys.env")
            return
        
        print("=" * 60)
        print("STRATEGY MANAGER - POSITION CHECK & IRON CONDOR CREATION")
        print("=" * 60)
        
        # Initialize strategy manager
        strategy_manager = StrategyManager()
        
        # Run position management
        result = strategy_manager.manage_positions(access_token)
        
        # Display results
        print(f"\nCurrent NIFTY Spot Price: ₹{result.get('spot_price', 'N/A'):,.2f}")
        print(f"Open Positions Found: {result.get('open_positions', 0)}")
        
        if result.get("action_taken") == "existing_positions_found":
            print("\n✅ EXISTING POSITIONS FOUND")
            print("No new strategy needed. Current open trades:")
            for trade_id in result.get("open_trades", []):
                print(f"  - {trade_id}")
                
        elif result.get("action_taken") == "iron_condor_created":
            print("\n🎯 IRON CONDOR STRATEGY CREATED")
            print(f"Trade ID: {result.get('trade_created')}")
            
            strategy_details = result.get("strategy_details", {})
            print(f"Strikes: {strategy_details.get('strikes', [])}")
            print(f"Expiry: {strategy_details.get('expiry', 'N/A')}")
            print(f"Description: {strategy_details.get('description', 'N/A')}")
            
            plot_path = result.get("plot_path")
            if plot_path:
                print(f"\n📊 Payoff diagram saved to: {plot_path}")
                print("The diagram shows:")
                print("  - Max Profit and Max Loss")
                print("  - Breakeven points")
                print("  - Current spot price")
                print("  - All strike prices")
                
        elif result.get("action_taken") == "error":
            print(f"\n❌ ERROR: {result.get('error', 'Unknown error')}")
            
        print("\n" + "=" * 60)
        print("Strategy management completed!")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()

