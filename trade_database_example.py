#!/usr/bin/env python3
"""
Example integration of Trade Database with the market application.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from trade_database import TradeDatabase
from trade_models import (
    Trade, TradeLeg, OptionType, PositionType, TradeStatus,
    create_iron_condor, create_straddle
)
from datetime import datetime, timedelta

def main():
    """Main example function"""
    print("Trade Database Integration Example")
    print("=" * 50)
    
    # Initialize database
    db = TradeDatabase("trades.db")
    print("✅ Database initialized")
    
    # Example 1: Create and save an Iron Condor trade
    print("\n1. Creating Iron Condor Trade...")
    iron_condor = create_iron_condor(
        trade_id="IC_NIFTY_001",
        underlying="NIFTY",
        short_call_strike=25000,
        long_call_strike=25100,
        short_put_strike=24000,
        long_put_strike=23900,
        call_premium=50.0,
        put_premium=45.0,
        quantity=1
    )
    
    # Add some metadata
    iron_condor.notes = "Iron Condor on NIFTY for earnings play"
    iron_condor.tags = ["earnings", "iron-condor", "nifty"]
    
    # Save to database
    success = db.save_trade(iron_condor)
    print(f"   Iron Condor saved: {success}")
    
    # Example 2: Create and save a Straddle trade
    print("\n2. Creating Straddle Trade...")
    straddle = create_straddle(
        trade_id="ST_NIFTY_001",
        underlying="NIFTY",
        strike_price=24500,
        call_premium=100.0,
        put_premium=95.0,
        quantity=1
    )
    
    # Add some metadata
    straddle.notes = "Straddle on NIFTY for volatility play"
    straddle.tags = ["volatility", "straddle", "nifty"]
    
    # Save to database
    success = db.save_trade(straddle)
    print(f"   Straddle saved: {success}")
    
    # Example 3: Create a simple call option trade
    print("\n3. Creating Simple Call Trade...")
    call_trade = Trade(
        trade_id="CALL_NIFTY_001",
        strategy_name="Long Call",
        underlying_instrument="NIFTY",
        notes="Simple long call on NIFTY",
        tags=["call", "nifty", "directional"]
    )
    
    # Add a leg
    call_leg = TradeLeg(
        instrument="NIFTY_CALL_25000",
        instrument_name="NIFTY Call 25000",
        option_type=OptionType.CALL,
        strike_price=25000.0,
        position_type=PositionType.LONG,
        quantity=2,
        entry_timestamp=datetime.now(),
        entry_price=120.0
    )
    
    call_trade.add_leg(call_leg)
    
    # Save to database
    success = db.save_trade(call_trade)
    print(f"   Call trade saved: {success}")
    
    # Example 4: Query operations
    print("\n4. Query Operations...")
    
    # Get all trades
    all_trades = db.get_all_trades()
    print(f"   Total trades: {len(all_trades)}")
    
    # Get open trades
    open_trades = db.get_open_trades()
    print(f"   Open trades: {len(open_trades)}")
    
    # Get trades by strategy
    iron_condor_trades = db.get_trades_by_strategy("Iron Condor")
    print(f"   Iron Condor trades: {len(iron_condor_trades)}")
    
    # Get trades by underlying
    nifty_trades = db.get_trades_by_underlying("NIFTY")
    print(f"   NIFTY trades: {len(nifty_trades)}")
    
    # Example 5: Update a trade (close a position)
    print("\n5. Updating Trade (Closing Position)...")
    
    # Get the call trade
    call_trade = db.get_trade("CALL_NIFTY_001")
    if call_trade:
        print(f"   Before closing: {call_trade.status}")
        
        # Close the position
        call_trade.close_leg(0, exit_price=150.0)
        call_trade.notes = "Closed call position with profit"
        
        # Update in database
        success = db.update_trade(call_trade)
        print(f"   Trade updated: {success}")
        print(f"   After closing: {call_trade.status}")
        print(f"   Profit: {call_trade.get_total_profit()}")
    
    # Example 6: Get trade statistics
    print("\n6. Trade Statistics...")
    stats = db.get_trade_statistics()
    print(f"   Total trades: {stats['total_trades']}")
    print(f"   Open trades: {stats['open_trades']}")
    print(f"   Closed trades: {stats['closed_trades']}")
    print(f"   Total profit: {stats['total_profit']}")
    print(f"   Strategy breakdown: {stats['strategy_breakdown']}")
    print(f"   Underlying breakdown: {stats['underlying_breakdown']}")
    
    # Example 7: Display trade details
    print("\n7. Trade Details...")
    for trade in all_trades:
        print(f"\n   Trade ID: {trade.trade_id}")
        print(f"   Strategy: {trade.strategy_name}")
        print(f"   Underlying: {trade.underlying_instrument}")
        print(f"   Status: {trade.status.value}")
        print(f"   Legs: {len(trade.legs)}")
        print(f"   Notes: {trade.notes}")
        print(f"   Tags: {trade.tags}")
        
        if trade.legs:
            print("   Legs:")
            for i, leg in enumerate(trade.legs):
                print(f"     {i+1}. {leg.option_type.value} {leg.strike_price} {leg.position_type.value} @ {leg.entry_price}")
                if leg.is_closed():
                    print(f"        Closed @ {leg.exit_price} (P&L: {leg.profit})")
    
    # Example 8: Backup database
    print("\n8. Database Backup...")
    backup_path = f"market_trades_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    success = db.backup_database(backup_path)
    print(f"   Backup created: {success}")
    if success:
        print(f"   Backup file: {backup_path}")
    
    print("\n✅ Example completed successfully!")
    print(f"Database file: trades.db")
    print(f"Backup file: {backup_path}")

if __name__ == "__main__":
    main()

