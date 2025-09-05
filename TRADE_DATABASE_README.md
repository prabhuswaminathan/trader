# Trade Database System

A comprehensive SQLite-based database system for storing and managing complex trading strategies with multiple legs.

## Features

### 🗄️ **Database Operations**
- **Save Trades**: Store complete trades with all legs
- **Update Trades**: Modify existing trades and their legs
- **Delete Trades**: Remove trades from the database
- **Get Trades**: Retrieve individual or multiple trades

### 🔍 **Query Capabilities**
- **Get All Trades**: Retrieve all trades in the database
- **Get Open Trades**: Find all currently open positions
- **Get by Strategy**: Filter trades by strategy type (Iron Condor, Straddle, etc.)
- **Get by Underlying**: Filter trades by underlying instrument (NIFTY, BANKNIFTY, etc.)
- **Get by Date Range**: Find trades within specific time periods

### 📊 **Statistics & Analytics**
- **Trade Statistics**: Comprehensive statistics about all trades
- **Profit Tracking**: Total realized and unrealized P&L
- **Strategy Breakdown**: Count of trades by strategy type
- **Underlying Breakdown**: Count of trades by underlying instrument

### 💾 **Data Management**
- **Backup & Restore**: Create and restore database backups
- **Thread Safety**: Thread-safe operations for concurrent access
- **Automatic Timestamps**: Track creation and update times
- **JSON Serialization**: Full support for JSON import/export

## Quick Start

### 1. Initialize Database

```python
from trade_database import TradeDatabase

# Create database
db = TradeDatabase("my_trades.db")
```

### 2. Create and Save a Trade

```python
from trade_models import Trade, TradeLeg, OptionType, PositionType

# Create a simple trade
trade = Trade(
    trade_id="TRADE_001",
    strategy_name="Long Call",
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

# Save to database
db.save_trade(trade)
```

### 3. Query Trades

```python
# Get all trades
all_trades = db.get_all_trades()

# Get open trades
open_trades = db.get_open_trades()

# Get trades by strategy
iron_condors = db.get_trades_by_strategy("Iron Condor")

# Get trades by underlying
nifty_trades = db.get_trades_by_underlying("NIFTY")
```

### 4. Update Trades

```python
# Get a trade
trade = db.get_trade("TRADE_001")

# Close a position
trade.close_leg(0, exit_price=150.0)

# Update in database
db.update_trade(trade)
```

## Database Schema

### Trades Table
- `trade_id` (TEXT, PRIMARY KEY)
- `strategy_name` (TEXT)
- `underlying_instrument` (TEXT)
- `created_timestamp` (TEXT)
- `status` (TEXT)
- `notes` (TEXT)
- `tags` (TEXT, JSON)
- `created_at` (TEXT)
- `updated_at` (TEXT)

### Trade Legs Table
- `id` (INTEGER, PRIMARY KEY)
- `trade_id` (TEXT, FOREIGN KEY)
- `instrument` (TEXT)
- `instrument_name` (TEXT)
- `option_type` (TEXT)
- `strike_price` (REAL)
- `position_type` (TEXT)
- `quantity` (INTEGER)
- `entry_timestamp` (TEXT)
- `entry_price` (REAL)
- `exit_price` (REAL)
- `exit_timestamp` (TEXT)
- `profit` (REAL)
- `created_at` (TEXT)
- `updated_at` (TEXT)

## Supported Trade Types

### Simple Trades
- **Long Call**: Single long call option
- **Long Put**: Single long put option
- **Short Call**: Single short call option
- **Short Put**: Single short put option

### Complex Strategies
- **Iron Condor**: 4 legs (2 short calls, 2 long calls)
- **Straddle**: 2 legs (1 long call, 1 long put, same strike)
- **Strangle**: 2 legs (1 long call, 1 long put, different strikes)
- **Butterfly**: 3 legs (1 long, 2 short, 1 long)
- **Custom Strategies**: Any combination of legs

## Example Usage

### Creating an Iron Condor

```python
from trade_models import create_iron_condor

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

# Save to database
db.save_trade(iron_condor)
```

### Creating a Straddle

```python
from trade_models import create_straddle

# Create Straddle
straddle = create_straddle(
    trade_id="ST_001",
    underlying="NIFTY",
    strike_price=24500,
    call_premium=100.0,
    put_premium=95.0,
    quantity=1
)

# Save to database
db.save_trade(straddle)
```

### Getting Trade Statistics

```python
# Get comprehensive statistics
stats = db.get_trade_statistics()

print(f"Total trades: {stats['total_trades']}")
print(f"Open trades: {stats['open_trades']}")
print(f"Closed trades: {stats['closed_trades']}")
print(f"Total profit: {stats['total_profit']}")
print(f"Strategy breakdown: {stats['strategy_breakdown']}")
print(f"Underlying breakdown: {stats['underlying_breakdown']}")
```

## File Structure

```
code/
├── trade_models.py          # Trade and TradeLeg data classes
├── trade_database.py        # Database operations
└── ...

test_trade_models.py         # Test script for trade models
test_trade_database.py       # Test script for database operations
trade_database_example.py    # Integration example
```

## Testing

Run the test scripts to verify functionality:

```bash
# Test trade models
python3 test_trade_models.py

# Test database operations
python3 test_trade_database.py

# Run integration example
python3 trade_database_example.py
```

## Thread Safety

The database operations are thread-safe and can be used in multi-threaded applications. All database operations use a lock to ensure data consistency.

## Backup and Restore

```python
# Create backup
db.backup_database("backup.db")

# Restore from backup
db.restore_database("backup.db")
```

## Error Handling

All database operations include comprehensive error handling and logging. Check the logs for detailed error information if operations fail.

## Performance

- **Indexes**: Database includes indexes on commonly queried fields
- **Efficient Queries**: Optimized SQL queries for fast retrieval
- **Connection Management**: Automatic connection management with context managers
- **Memory Efficient**: Streams large result sets to avoid memory issues

## Dependencies

- Python 3.7+
- SQLite3 (included with Python)
- No external dependencies required

## License

This code is part of the market trading application and follows the same license terms.

