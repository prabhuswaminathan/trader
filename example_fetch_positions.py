#!/usr/bin/env python3
"""
Example script demonstrating how to fetch positions from Upstox API
"""

import sys
import os
import json
from datetime import datetime

# Add the code directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from upstox_agent import UpstoxAgent

def main():
    """Main function to demonstrate position fetching"""
    
    # Initialize the Upstox agent
    agent = UpstoxAgent()
    
    print("=" * 60)
    print("Upstox Positions Fetcher")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if access token is available
    if not agent.ACCESS_TOKEN:
        print("❌ Error: UPSTOX_ACCESS_TOKEN not found in environment variables")
        print("Please set your Upstox access token in the keys.env file")
        return
    
    try:
        # Method 1: Fetch raw positions data
        print("📊 Fetching raw positions data...")
        raw_positions = agent.fetch_positions()
        
        if raw_positions:
            print(f"✅ Successfully fetched {len(raw_positions)} positions")
            print("\nRaw positions data (first position):")
            print(json.dumps(raw_positions[0], indent=2))
        else:
            print("ℹ️  No positions found or error occurred")
        
        print("\n" + "-" * 60)
        
        # Method 2: Fetch formatted positions data
        print("📈 Fetching formatted positions data...")
        formatted_data = agent.get_formatted_positions()
        
        if formatted_data["status"] == "success":
            print(f"✅ Successfully formatted {formatted_data['total_positions']} positions")
            
            # Display summary
            summary = formatted_data["summary"]
            print(f"\n📋 Portfolio Summary:")
            print(f"   Total P&L: ₹{summary['total_pnl']:,.2f}")
            print(f"   Unrealised P&L: ₹{summary['total_unrealised']:,.2f}")
            print(f"   Realised P&L: ₹{summary['total_realised']:,.2f}")
            print(f"   Total Value: ₹{summary['total_value']:,.2f}")
            
            # Display individual positions
            if formatted_data["positions"]:
                print(f"\n📊 Individual Positions:")
                print("-" * 80)
                print(f"{'Symbol':<15} {'Exchange':<8} {'Qty':<8} {'Avg Price':<10} {'Last Price':<12} {'P&L':<12}")
                print("-" * 80)
                
                for pos in formatted_data["positions"]:
                    symbol = pos["trading_symbol"][:14]  # Truncate long symbols
                    exchange = pos["exchange"]
                    qty = pos["quantity"]
                    avg_price = pos["average_price"] or 0
                    last_price = pos["last_price"]
                    pnl = pos["pnl"]
                    
                    print(f"{symbol:<15} {exchange:<8} {qty:<8} {avg_price:<10.2f} {last_price:<12.2f} {pnl:<12.2f}")
            else:
                print("ℹ️  No positions to display")
        else:
            print(f"❌ Error fetching formatted positions: {formatted_data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
