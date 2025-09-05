#!/usr/bin/env python3
"""
Test script for Trade Database operations.
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
import tempfile
import shutil

def test_basic_operations():
    """Test basic database operations"""
    print("=== Testing Basic Database Operations ===")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Initialize database
        db = TradeDatabase(db_path)
        print(f"Database created: {db_path}")
        
        # Create a simple trade
        trade = Trade(
            trade_id="TEST_001",
            strategy_name="Test Strategy",
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
        
        # Test save
        print("Testing save_trade...")
        success = db.save_trade(trade)
        print(f"Save result: {success}")
        
        # Test get
        print("Testing get_trade...")
        retrieved_trade = db.get_trade("TEST_001")
        print(f"Retrieved trade: {retrieved_trade}")
        print(f"Trade matches: {retrieved_trade.trade_id == trade.trade_id}")
        
        # Test update
        print("Testing update_trade...")
        trade.notes = "Updated trade"
        trade.tags = ["test", "updated"]
        success = db.update_trade(trade)
        print(f"Update result: {success}")
        
        # Verify update
        updated_trade = db.get_trade("TEST_001")
        print(f"Updated notes: {updated_trade.notes}")
        print(f"Updated tags: {updated_trade.tags}")
        
        # Test get all trades
        print("Testing get_all_trades...")
        all_trades = db.get_all_trades()
        print(f"Total trades: {len(all_trades)}")
        
        # Test get open trades
        print("Testing get_open_trades...")
        open_trades = db.get_open_trades()
        print(f"Open trades: {len(open_trades)}")
        
        # Test delete
        print("Testing delete_trade...")
        success = db.delete_trade("TEST_001")
        print(f"Delete result: {success}")
        
        # Verify deletion
        deleted_trade = db.get_trade("TEST_001")
        print(f"Trade after deletion: {deleted_trade}")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)
        print("Temporary database cleaned up")

def test_complex_trades():
    """Test with complex trades like Iron Condors and Straddles"""
    print("\n=== Testing Complex Trades ===")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Initialize database
        db = TradeDatabase(db_path)
        
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
        
        # Create Straddle
        straddle = create_straddle(
            trade_id="ST_001",
            underlying="NIFTY",
            strike_price=24500,
            call_premium=100.0,
            put_premium=95.0,
            quantity=1
        )
        
        # Save both trades
        print("Saving Iron Condor...")
        db.save_trade(iron_condor)
        
        print("Saving Straddle...")
        db.save_trade(straddle)
        
        # Test retrieval
        print("Testing trade retrieval...")
        ic_trade = db.get_trade("IC_001")
        st_trade = db.get_trade("ST_001")
        
        print(f"Iron Condor: {ic_trade}")
        print(f"Straddle: {st_trade}")
        print(f"Iron Condor legs: {len(ic_trade.legs)}")
        print(f"Straddle legs: {len(st_trade.legs)}")
        
        # Test strategy filtering
        print("Testing strategy filtering...")
        ic_trades = db.get_trades_by_strategy("Iron Condor")
        st_trades = db.get_trades_by_strategy("Straddle")
        
        print(f"Iron Condor trades: {len(ic_trades)}")
        print(f"Straddle trades: {len(st_trades)}")
        
        # Test underlying filtering
        print("Testing underlying filtering...")
        nifty_trades = db.get_trades_by_underlying("NIFTY")
        print(f"NIFTY trades: {len(nifty_trades)}")
        
        # Test closing a trade
        print("Testing trade closure...")
        ic_trade.close_all_legs([60.0, 5.0, 55.0, 4.5])  # Close all legs
        db.update_trade(ic_trade)
        
        # Check status
        updated_ic = db.get_trade("IC_001")
        print(f"Updated Iron Condor status: {updated_ic.status}")
        print(f"Total profit: {updated_ic.get_total_profit()}")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)
        print("Temporary database cleaned up")

def test_query_operations():
    """Test various query operations"""
    print("\n=== Testing Query Operations ===")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Initialize database
        db = TradeDatabase(db_path)
        
        # Create multiple trades with different dates
        base_date = datetime.now() - timedelta(days=10)
        
        for i in range(5):
            trade = Trade(
                trade_id=f"TRADE_{i:03d}",
                strategy_name="Test Strategy",
                underlying_instrument="NIFTY" if i % 2 == 0 else "BANKNIFTY"
            )
            
            # Add a leg
            leg = TradeLeg(
                instrument=f"NIFTY_CALL_{25000 + i*100}",
                instrument_name=f"NIFTY Call {25000 + i*100}",
                option_type=OptionType.CALL,
                strike_price=25000 + i*100,
                position_type=PositionType.LONG,
                quantity=1,
                entry_timestamp=base_date + timedelta(days=i),
                entry_price=100.0 + i*10
            )
            
            trade.add_leg(leg)
            
            # Close some trades
            if i % 2 == 0:
                trade.close_all_legs([120.0 + i*10])
            
            db.save_trade(trade)
        
        # Test date range queries
        print("Testing date range queries...")
        start_date = base_date
        end_date = base_date + timedelta(days=3)
        
        date_trades = db.get_trades_by_date_range(start_date, end_date)
        print(f"Trades in date range: {len(date_trades)}")
        
        # Test underlying queries
        print("Testing underlying queries...")
        nifty_trades = db.get_trades_by_underlying("NIFTY")
        banknifty_trades = db.get_trades_by_underlying("BANKNIFTY")
        
        print(f"NIFTY trades: {len(nifty_trades)}")
        print(f"BANKNIFTY trades: {len(banknifty_trades)}")
        
        # Test status queries
        print("Testing status queries...")
        all_trades = db.get_all_trades()
        open_trades = db.get_open_trades()
        
        print(f"All trades: {len(all_trades)}")
        print(f"Open trades: {len(open_trades)}")
        
        # Test statistics
        print("Testing statistics...")
        stats = db.get_trade_statistics()
        print(f"Statistics: {stats}")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)
        print("Temporary database cleaned up")

def test_backup_restore():
    """Test backup and restore functionality"""
    print("\n=== Testing Backup and Restore ===")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Initialize database
        db = TradeDatabase(db_path)
        
        # Create some trades
        trade = Trade(
            trade_id="BACKUP_TEST",
            strategy_name="Backup Test",
            underlying_instrument="NIFTY"
        )
        
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
        db.save_trade(trade)
        
        # Create backup
        backup_path = db_path + ".backup"
        success = db.backup_database(backup_path)
        print(f"Backup created: {success}")
        
        # Verify backup
        if os.path.exists(backup_path):
            print(f"Backup file exists: {os.path.getsize(backup_path)} bytes")
        
        # Test restore
        new_db_path = db_path + ".restored"
        shutil.copy2(backup_path, new_db_path)
        
        # Test restored database
        restored_db = TradeDatabase(new_db_path)
        restored_trade = restored_db.get_trade("BACKUP_TEST")
        print(f"Restored trade: {restored_trade}")
        print(f"Restore successful: {restored_trade is not None}")
        
    finally:
        # Clean up
        for path in [db_path, db_path + ".backup", db_path + ".restored"]:
            if os.path.exists(path):
                os.unlink(path)
        print("Temporary files cleaned up")

if __name__ == "__main__":
    print("Testing Trade Database Operations...\n")
    
    try:
        test_basic_operations()
        test_complex_trades()
        test_query_operations()
        test_backup_restore()
        
        print("\n✅ All database tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

