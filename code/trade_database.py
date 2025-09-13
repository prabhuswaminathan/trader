#!/usr/bin/env python3
"""
Trade Database module for storing and managing trades.

This module provides a SQLite-based database for persisting trades and trade legs,
with full CRUD operations and query capabilities.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import threading

from trade_models import Trade, TradeLeg, TradeStatus, OptionType, PositionType

logger = logging.getLogger("TradeDatabase")

class TradeDatabase:
    """
    SQLite-based database for storing and managing trades.
    
    Provides full CRUD operations for trades and trade legs,
    with support for complex queries and filtering.
    """
    
    def __init__(self, db_path: str = "trades.db"):
        """
        Initialize the trade database.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create trades table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id TEXT PRIMARY KEY,
                        strategy_name TEXT NOT NULL,
                        underlying_instrument TEXT NOT NULL,
                        created_timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        notes TEXT,
                        tags TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create trade_legs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trade_legs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trade_id TEXT NOT NULL,
                        instrument TEXT NOT NULL,
                        instrument_name TEXT NOT NULL,
                        option_type TEXT NOT NULL,
                        strike_price REAL NOT NULL,
                        position_type TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        entry_timestamp TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        exit_timestamp TEXT,
                        profit REAL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (trade_id) REFERENCES trades (trade_id) ON DELETE CASCADE
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_status 
                    ON trades (status)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trades_underlying 
                    ON trades (underlying_instrument)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trade_legs_trade_id 
                    ON trade_legs (trade_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_trade_legs_instrument 
                    ON trade_legs (instrument)
                """)
                
                # Create trigger to update updated_at timestamp
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS update_trades_timestamp 
                    AFTER UPDATE ON trades
                    BEGIN
                        UPDATE trades SET updated_at = CURRENT_TIMESTAMP WHERE trade_id = NEW.trade_id;
                    END
                """)
                
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS update_trade_legs_timestamp 
                    AFTER UPDATE ON trade_legs
                    BEGIN
                        UPDATE trade_legs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                    END
                """)
                
                conn.commit()
                logger.info(f"Database initialized successfully: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def save_trade(self, trade: Trade) -> bool:
        """
        Save a trade to the database.
        
        Args:
            trade (Trade): Trade object to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Check if trade already exists
                    cursor.execute("SELECT trade_id FROM trades WHERE trade_id = ?", (trade.trade_id,))
                    if cursor.fetchone():
                        logger.warning(f"Trade {trade.trade_id} already exists. Use update_trade() instead.")
                        return False
                    
                    # Insert trade
                    cursor.execute("""
                        INSERT INTO trades (trade_id, strategy_name, underlying_instrument, 
                                         created_timestamp, status, notes, tags)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade.trade_id,
                        trade.strategy_name,
                        trade.underlying_instrument,
                        trade.created_timestamp.isoformat(),
                        trade.status.value,
                        trade.notes,
                        json.dumps(trade.tags) if trade.tags else None
                    ))
                    
                    # Insert trade legs
                    for leg in trade.legs:
                        cursor.execute("""
                            INSERT INTO trade_legs (trade_id, instrument, instrument_name, 
                                                  option_type, strike_price, position_type, 
                                                  quantity, entry_timestamp, entry_price, 
                                                  exit_price, exit_timestamp, profit)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            trade.trade_id,
                            leg.instrument,
                            leg.instrument_name,
                            leg.option_type.value,
                            leg.strike_price,
                            leg.position_type.value,
                            leg.quantity,
                            leg.entry_timestamp.isoformat(),
                            leg.entry_price,
                            leg.exit_price,
                            leg.exit_timestamp.isoformat() if leg.exit_timestamp else None,
                            leg.profit
                        ))
                    
                    conn.commit()
                    logger.info(f"Trade {trade.trade_id} saved successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving trade {trade.trade_id}: {e}")
            return False
    
    def update_trade(self, trade: Trade) -> bool:
        """
        Update an existing trade in the database.
        
        Args:
            trade (Trade): Trade object with updated data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Check if trade exists
                    cursor.execute("SELECT trade_id FROM trades WHERE trade_id = ?", (trade.trade_id,))
                    if not cursor.fetchone():
                        logger.warning(f"Trade {trade.trade_id} not found. Use save_trade() instead.")
                        return False
                    
                    # Update trade
                    cursor.execute("""
                        UPDATE trades 
                        SET strategy_name = ?, underlying_instrument = ?, 
                            created_timestamp = ?, status = ?, notes = ?, tags = ?
                        WHERE trade_id = ?
                    """, (
                        trade.strategy_name,
                        trade.underlying_instrument,
                        trade.created_timestamp.isoformat(),
                        trade.status.value,
                        trade.notes,
                        json.dumps(trade.tags) if trade.tags else None,
                        trade.trade_id
                    ))
                    
                    # Delete existing legs
                    cursor.execute("DELETE FROM trade_legs WHERE trade_id = ?", (trade.trade_id,))
                    
                    # Insert updated legs
                    for leg in trade.legs:
                        cursor.execute("""
                            INSERT INTO trade_legs (trade_id, instrument, instrument_name, 
                                                  option_type, strike_price, position_type, 
                                                  quantity, entry_timestamp, entry_price, 
                                                  exit_price, exit_timestamp, profit)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            trade.trade_id,
                            leg.instrument,
                            leg.instrument_name,
                            leg.option_type.value,
                            leg.strike_price,
                            leg.position_type.value,
                            leg.quantity,
                            leg.entry_timestamp.isoformat(),
                            leg.entry_price,
                            leg.exit_price,
                            leg.exit_timestamp.isoformat() if leg.exit_timestamp else None,
                            leg.profit
                        ))
                    
                    conn.commit()
                    logger.info(f"Trade {trade.trade_id} updated successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Error updating trade {trade.trade_id}: {e}")
            return False
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """
        Get a specific trade by ID.
        
        Args:
            trade_id (str): Trade ID to retrieve
            
        Returns:
            Optional[Trade]: Trade object if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get trade data
                cursor.execute("""
                    SELECT trade_id, strategy_name, underlying_instrument, 
                           created_timestamp, status, notes, tags
                    FROM trades WHERE trade_id = ?
                """, (trade_id,))
                
                trade_row = cursor.fetchone()
                if not trade_row:
                    return None
                
                # Get trade legs
                cursor.execute("""
                    SELECT instrument, instrument_name, option_type, strike_price, 
                           position_type, quantity, entry_timestamp, entry_price, 
                           exit_price, exit_timestamp, profit
                    FROM trade_legs WHERE trade_id = ?
                    ORDER BY id
                """, (trade_id,))
                
                leg_rows = cursor.fetchall()
                
                # Reconstruct trade object
                trade = Trade(
                    trade_id=trade_row[0],
                    strategy_name=trade_row[1],
                    underlying_instrument=trade_row[2],
                    created_timestamp=datetime.fromisoformat(trade_row[3]),
                    status=TradeStatus(trade_row[4]),
                    notes=trade_row[5],
                    tags=json.loads(trade_row[6]) if trade_row[6] else []
                )
                
                # Reconstruct trade legs
                for leg_row in leg_rows:
                    leg = TradeLeg(
                        instrument=leg_row[0],
                        instrument_name=leg_row[1],
                        option_type=OptionType(leg_row[2]),
                        strike_price=leg_row[3],
                        position_type=PositionType(leg_row[4]),
                        quantity=leg_row[5],
                        entry_timestamp=datetime.fromisoformat(leg_row[6]),
                        entry_price=leg_row[7],
                        exit_price=leg_row[8],
                        exit_timestamp=datetime.fromisoformat(leg_row[9]) if leg_row[9] else None,
                        profit=leg_row[10]
                    )
                    trade.legs.append(leg)
                
                return trade
                
        except Exception as e:
            logger.error(f"Error getting trade {trade_id}: {e}")
            return None
    
    def get_all_trades(self) -> List[Trade]:
        """
        Get all trades from the database.
        
        Returns:
            List[Trade]: List of all trades
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all trade IDs
                cursor.execute("SELECT trade_id FROM trades ORDER BY created_timestamp DESC")
                trade_ids = [row[0] for row in cursor.fetchall()]
                
                # Get each trade
                trades = []
                for trade_id in trade_ids:
                    trade = self.get_trade(trade_id)
                    if trade:
                        trades.append(trade)
                
                return trades
                
        except Exception as e:
            logger.error(f"Error getting all trades: {e}")
            return []
    
    def get_open_trades(self) -> List[Trade]:
        """
        Get all currently open trades.
        
        Returns:
            List[Trade]: List of open trades
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get open trade IDs
                cursor.execute("""
                    SELECT trade_id FROM trades 
                    WHERE status = ? 
                    ORDER BY created_timestamp DESC
                """, (TradeStatus.OPEN.value,))
                
                trade_ids = [row[0] for row in cursor.fetchall()]
                
                # Get each trade
                trades = []
                for trade_id in trade_ids:
                    trade = self.get_trade(trade_id)
                    if trade:
                        trades.append(trade)
                
                return trades
                
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []
    
    def get_open_trade_legs(self) -> List[TradeLeg]:
        """
        Get all open trade legs from all open trades.
        
        Returns:
            List[TradeLeg]: List of all open trade legs
        """
        try:
            open_trades = self.get_open_trades()
            open_legs = []
            
            for trade in open_trades:
                for leg in trade.legs:
                    if leg.is_open():
                        open_legs.append(leg)
            
            logger.info(f"Found {len(open_legs)} open trade legs from {len(open_trades)} open trades")
            return open_legs
                
        except Exception as e:
            logger.error(f"Error getting open trade legs: {e}")
            return []
    
    def close_trade_leg(self, trade_id: str, leg_index: int, exit_price: float, exit_timestamp: datetime) -> bool:
        """
        Close a specific trade leg with exit price and timestamp.
        
        Args:
            trade_id (str): ID of the trade containing the leg
            leg_index (int): Index of the leg within the trade
            exit_price (float): Exit price for the leg
            exit_timestamp (datetime): Exit timestamp
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the trade
            trade = self.get_trade(trade_id)
            if not trade:
                logger.error(f"Trade {trade_id} not found")
                return False
            
            # Check if leg index is valid
            if leg_index < 0 or leg_index >= len(trade.legs):
                logger.error(f"Invalid leg index {leg_index} for trade {trade_id}")
                return False
            
            # Get the leg
            leg = trade.legs[leg_index]
            
            # Check if leg is already closed
            if leg.is_closed():
                logger.warning(f"Leg {leg_index} in trade {trade_id} is already closed")
                return False
            
            # Close the leg
            leg.exit_price = exit_price
            leg.exit_timestamp = exit_timestamp
            leg.calculate_profit()  # Recalculate profit
            
            # Update the trade in database
            success = self.update_trade(trade)
            
            if success:
                logger.info(f"Successfully closed leg {leg_index} in trade {trade_id} at price {exit_price}")
            else:
                logger.error(f"Failed to update trade {trade_id} after closing leg")
            
            return success
                
        except Exception as e:
            logger.error(f"Error closing trade leg: {e}")
            return False
    
    def get_trades_by_strategy(self, strategy_name: str) -> List[Trade]:
        """
        Get all trades for a specific strategy.
        
        Args:
            strategy_name (str): Strategy name to filter by
            
        Returns:
            List[Trade]: List of trades for the strategy
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get trade IDs for strategy
                cursor.execute("""
                    SELECT trade_id FROM trades 
                    WHERE strategy_name = ? 
                    ORDER BY created_timestamp DESC
                """, (strategy_name,))
                
                trade_ids = [row[0] for row in cursor.fetchall()]
                
                # Get each trade
                trades = []
                for trade_id in trade_ids:
                    trade = self.get_trade(trade_id)
                    if trade:
                        trades.append(trade)
                
                return trades
                
        except Exception as e:
            logger.error(f"Error getting trades by strategy {strategy_name}: {e}")
            return []
    
    def get_trades_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Trade]:
        """
        Get trades within a date range.
        
        Args:
            start_date (datetime): Start date (inclusive)
            end_date (datetime): End date (inclusive)
            
        Returns:
            List[Trade]: List of trades in the date range
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get trade IDs in date range
                cursor.execute("""
                    SELECT trade_id FROM trades 
                    WHERE created_timestamp >= ? AND created_timestamp <= ?
                    ORDER BY created_timestamp DESC
                """, (start_date.isoformat(), end_date.isoformat()))
                
                trade_ids = [row[0] for row in cursor.fetchall()]
                
                # Get each trade
                trades = []
                for trade_id in trade_ids:
                    trade = self.get_trade(trade_id)
                    if trade:
                        trades.append(trade)
                
                return trades
                
        except Exception as e:
            logger.error(f"Error getting trades by date range: {e}")
            return []
    
    def get_trades_by_underlying(self, underlying_instrument: str) -> List[Trade]:
        """
        Get all trades for a specific underlying instrument.
        
        Args:
            underlying_instrument (str): Underlying instrument to filter by
            
        Returns:
            List[Trade]: List of trades for the underlying
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get trade IDs for underlying
                cursor.execute("""
                    SELECT trade_id FROM trades 
                    WHERE underlying_instrument = ? 
                    ORDER BY created_timestamp DESC
                """, (underlying_instrument,))
                
                trade_ids = [row[0] for row in cursor.fetchall()]
                
                # Get each trade
                trades = []
                for trade_id in trade_ids:
                    trade = self.get_trade(trade_id)
                    if trade:
                        trades.append(trade)
                
                return trades
                
        except Exception as e:
            logger.error(f"Error getting trades by underlying {underlying_instrument}: {e}")
            return []
    
    def delete_trade(self, trade_id: str) -> bool:
        """
        Delete a trade from the database.
        
        Args:
            trade_id (str): Trade ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Check if trade exists
                    cursor.execute("SELECT trade_id FROM trades WHERE trade_id = ?", (trade_id,))
                    if not cursor.fetchone():
                        logger.warning(f"Trade {trade_id} not found")
                        return False
                    
                    # Delete trade (legs will be deleted by CASCADE)
                    cursor.execute("DELETE FROM trades WHERE trade_id = ?", (trade_id,))
                    conn.commit()
                    
                    logger.info(f"Trade {trade_id} deleted successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Error deleting trade {trade_id}: {e}")
            return False
    
    def get_trade_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive trade statistics.
        
        Returns:
            Dict[str, Any]: Trade statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total trades
                cursor.execute("SELECT COUNT(*) FROM trades")
                total_trades = cursor.fetchone()[0]
                
                # Open trades
                cursor.execute("SELECT COUNT(*) FROM trades WHERE status = ?", (TradeStatus.OPEN.value,))
                open_trades = cursor.fetchone()[0]
                
                # Closed trades
                cursor.execute("SELECT COUNT(*) FROM trades WHERE status = ?", (TradeStatus.CLOSED.value,))
                closed_trades = cursor.fetchone()[0]
                
                # Partially closed trades
                cursor.execute("SELECT COUNT(*) FROM trades WHERE status = ?", (TradeStatus.PARTIALLY_CLOSED.value,))
                partially_closed_trades = cursor.fetchone()[0]
                
                # Total profit from closed trades
                cursor.execute("""
                    SELECT SUM(profit) FROM trade_legs 
                    WHERE exit_timestamp IS NOT NULL AND profit IS NOT NULL
                """)
                total_profit = cursor.fetchone()[0] or 0.0
                
                # Strategy breakdown
                cursor.execute("""
                    SELECT strategy_name, COUNT(*) as count 
                    FROM trades 
                    GROUP BY strategy_name 
                    ORDER BY count DESC
                """)
                strategy_breakdown = dict(cursor.fetchall())
                
                # Underlying breakdown
                cursor.execute("""
                    SELECT underlying_instrument, COUNT(*) as count 
                    FROM trades 
                    GROUP BY underlying_instrument 
                    ORDER BY count DESC
                """)
                underlying_breakdown = dict(cursor.fetchall())
                
                return {
                    'total_trades': total_trades,
                    'open_trades': open_trades,
                    'closed_trades': closed_trades,
                    'partially_closed_trades': partially_closed_trades,
                    'total_profit': total_profit,
                    'strategy_breakdown': strategy_breakdown,
                    'underlying_breakdown': underlying_breakdown
                }
                
        except Exception as e:
            logger.error(f"Error getting trade statistics: {e}")
            return {}
    
    def close_database(self) -> None:
        """Close the database connection (if any)"""
        # SQLite connections are automatically closed when exiting context managers
        logger.info("Database connection closed")
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path (str): Path for the backup file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path (str): Path to the backup file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import shutil
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False


# Example usage and factory functions
def create_sample_trades(db: TradeDatabase) -> None:
    """Create some sample trades for testing"""
    from trade_models import create_iron_condor, create_straddle
    
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
    
    # Save trades
    db.save_trade(iron_condor)
    db.save_trade(straddle)
    
    print("Sample trades created and saved")


if __name__ == "__main__":
    # Example usage
    print("Testing Trade Database...")
    
    # Initialize database
    db = TradeDatabase("test_trades.db")
    
    # Create sample trades
    create_sample_trades(db)
    
    # Test operations
    print(f"\nAll trades: {len(db.get_all_trades())}")
    print(f"Open trades: {len(db.get_open_trades())}")
    print(f"Iron Condor trades: {len(db.get_trades_by_strategy('Iron Condor'))}")
    print(f"NIFTY trades: {len(db.get_trades_by_underlying('NIFTY'))}")
    
    # Show statistics
    stats = db.get_trade_statistics()
    print(f"\nStatistics: {stats}")
    
    # Test individual trade retrieval
    trade = db.get_trade("IC_001")
    if trade:
        print(f"\nRetrieved trade: {trade}")
        print(f"Trade summary: {trade.get_summary()}")
    
    print("\n✅ Database operations completed successfully!")

