#!/usr/bin/env python3
"""
Test script for Trade and TradeLeg models.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from trade_models import (
    Trade, TradeLeg, OptionType, PositionType, TradeStatus,
    create_iron_condor, create_straddle
)
from datetime import datetime

def test_basic_trade_leg():
    """Test basic TradeLeg functionality"""
    print("=== Testing TradeLeg ===")
    
    # Create a simple call option leg
    leg = TradeLeg(
        instrument="NIFTY_CALL_25000",
        instrument_name="NIFTY Call 25000",
        option_type=OptionType.CALL,
        strike_price=25000.0,
        position_type=PositionType.LONG,
        quantity=1,
        entry_timestamp=datetime.now(),
        entry_price=100.0
    )
    
    print(f"Created leg: {leg}")
    print(f"Is open: {leg.is_open()}")
    print(f"Profit: {leg.profit}")
    
    # Close the position
    leg.exit_price = 150.0
    leg.exit_timestamp = datetime.now()
    leg.calculate_profit()
    
    print(f"After closing: {leg}")
    print(f"Is closed: {leg.is_closed()}")
    print(f"Profit: {leg.profit}")

def test_iron_condor():
    """Test Iron Condor creation and management"""
    print("\n=== Testing Iron Condor ===")
    
    # Create Iron Condor
    iron_condor = create_iron_condor(
        trade_id="IC_001",
        underlying="NIFTY",
        short_call_strike=25000,
        long_call_strike=25100,
        short_put_strike=24000,
        long_put_strike=23900,
        call_premium=50.0,
        put_premium=45.0,
        quantity=1
    )
    
    print(f"Created Iron Condor: {iron_condor}")
    print(f"Strategy: {iron_condor.strategy_name}")
    print(f"Total legs: {len(iron_condor.legs)}")
    print(f"Status: {iron_condor.status}")
    print(f"Is Iron Condor: {iron_condor.is_iron_condor()}")
    
    # Show all legs
    for i, leg in enumerate(iron_condor.legs):
        print(f"  Leg {i+1}: {leg.option_type.value} {leg.strike_price} {leg.position_type.value} @ {leg.entry_price}")
    
    # Show summary
    summary = iron_condor.get_summary()
    print(f"Summary: {summary}")

def test_straddle():
    """Test Straddle creation and management"""
    print("\n=== Testing Straddle ===")
    
    # Create Straddle
    straddle = create_straddle(
        trade_id="ST_001",
        underlying="NIFTY",
        strike_price=24500,
        call_premium=100.0,
        put_premium=95.0,
        quantity=1
    )
    
    print(f"Created Straddle: {straddle}")
    print(f"Strategy: {straddle.strategy_name}")
    print(f"Total legs: {len(straddle.legs)}")
    print(f"Status: {straddle.status}")
    print(f"Is Straddle: {straddle.is_straddle()}")
    
    # Show all legs
    for i, leg in enumerate(straddle.legs):
        print(f"  Leg {i+1}: {leg.option_type.value} {leg.strike_price} {leg.position_type.value} @ {leg.entry_price}")
    
    # Show summary
    summary = straddle.get_summary()
    print(f"Summary: {summary}")

def test_trade_operations():
    """Test trade operations like closing legs"""
    print("\n=== Testing Trade Operations ===")
    
    # Create a simple trade with one leg
    trade = Trade(
        trade_id="SIMPLE_001",
        strategy_name="Simple Call",
        underlying_instrument="NIFTY"
    )
    
    # Add a leg
    leg = TradeLeg(
        instrument="NIFTY_CALL_25000",
        instrument_name="NIFTY Call 25000",
        option_type=OptionType.CALL,
        strike_price=25000.0,
        position_type=PositionType.LONG,
        quantity=1,
        entry_timestamp=datetime.now(),
        entry_price=100.0
    )
    
    trade.add_leg(leg)
    print(f"Added leg to trade: {trade}")
    print(f"Status: {trade.status}")
    print(f"Total profit: {trade.get_total_profit()}")
    
    # Close the leg
    trade.close_leg(0, exit_price=150.0)
    print(f"After closing leg: {trade}")
    print(f"Status: {trade.status}")
    print(f"Total profit: {trade.get_total_profit()}")

def test_json_serialization():
    """Test JSON serialization and deserialization"""
    print("\n=== Testing JSON Serialization ===")
    
    # Create a simple trade
    trade = Trade(
        trade_id="JSON_TEST_001",
        strategy_name="Test Trade",
        underlying_instrument="NIFTY"
    )
    
    # Add a leg
    leg = TradeLeg(
        instrument="NIFTY_CALL_25000",
        instrument_name="NIFTY Call 25000",
        option_type=OptionType.CALL,
        strike_price=25000.0,
        position_type=PositionType.LONG,
        quantity=1,
        entry_timestamp=datetime.now(),
        entry_price=100.0
    )
    
    trade.add_leg(leg)
    
    # Convert to JSON
    json_str = trade.to_json()
    print(f"JSON: {json_str[:200]}...")
    
    # Convert back from JSON
    trade_from_json = Trade.from_json(json_str)
    print(f"Recreated trade: {trade_from_json}")
    print(f"Legs match: {len(trade.legs) == len(trade_from_json.legs)}")

if __name__ == "__main__":
    print("Testing Trade and TradeLeg models...\n")
    
    try:
        test_basic_trade_leg()
        test_iron_condor()
        test_straddle()
        test_trade_operations()
        test_json_serialization()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

