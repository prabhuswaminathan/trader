# Utils Module

A comprehensive utility module for trading operations, providing date/time calculations, expiry date management, and market-related functions.

## Features

### 📅 **Expiry Date Calculations**
- **Weekly Expiry**: Calculate NIFTY weekly option expiry dates (Thursdays)
- **Tuesday Expiry**: Calculate Tuesday expiry dates (as originally requested)
- **Monthly Expiry**: Calculate monthly option expiry dates (last Thursday of month)
- **Expiry Series**: Get multiple expiry dates at once

### ⏰ **Market Hours & Trading**
- **Market Status**: Check if market is currently open
- **Next Market Open**: Get next trading session time
- **Holiday Handling**: Automatically skip market holidays

### 💰 **Strike Price Management**
- **Strike Formatting**: Round prices to nearest strike step (50 for NIFTY)
- **Nearest Strikes**: Get strike prices around current price
- **Strike Series**: Generate multiple strike prices

### 📊 **Expiry Analysis**
- **Days to Expiry**: Calculate remaining days until expiry
- **Expiry Info**: Comprehensive information about expiry dates
- **Expiry Status**: Check if expiry is today, past, or future

## Quick Start

### Basic Usage

```python
from utils import Utils

# Get next weekly expiry (0 = next, 1 = following, etc.)
next_expiry = Utils.get_next_weekly_expiry(0)  # "2025-09-11"
next_week_expiry = Utils.get_next_weekly_expiry(1)  # "2025-09-18"

# Get Tuesday expiry (as originally requested)
tuesday_expiry = Utils.get_next_tuesday_expiry(0)  # "2025-09-09"

# Get monthly expiry
monthly_expiry = Utils.get_monthly_expiry(2025, 9)  # "2025-09-25"
```

### Expiry Series

```python
# Get next 4 weekly expiries
weekly_series = Utils.get_expiry_series("weekly", 4)
# ['2025-09-11', '2025-09-18', '2025-09-25', '2025-10-02']

# Get next 4 Tuesday expiries
tuesday_series = Utils.get_expiry_series("tuesday", 4)
# ['2025-09-09', '2025-09-16', '2025-09-23', '2025-09-30']
```

### Market Status

```python
# Check if market is open
is_open = Utils.is_market_open()  # True/False

# Get next market open time
next_open = Utils.get_next_market_open()  # datetime object
```

### Strike Price Calculations

```python
# Format strike price to nearest 50
formatted = Utils.format_strike_price(24567.89)  # 24550.0

# Get nearest strikes around current price
strikes = Utils.get_nearest_strikes(24500.0, 5)
# [24450.0, 24500.0, 24550.0, 24600.0, 24650.0]
```

### Expiry Analysis

```python
# Get comprehensive expiry information
expiry_info = Utils.get_expiry_info("2025-09-11")
# {
#     'expiry_date': '2025-09-11',
#     'days_to_expiry': 7,
#     'is_today': False,
#     'is_past': False,
#     'is_future': True,
#     'weekday': 'Thursday',
#     'is_weekend': False,
#     'is_holiday': False
# }

# Calculate days to expiry
days = Utils.calculate_days_to_expiry("2025-09-11")  # 7

# Check if expiry is today
is_today = Utils.is_expiry_today("2025-09-11")  # False
```

## API Reference

### Expiry Functions

#### `get_next_weekly_expiry(weeks_ahead: int = 0) -> str`
Get the next weekly expiry date for NIFTY options (Thursdays).

**Parameters:**
- `weeks_ahead` (int): Number of weeks ahead (0 = next, 1 = following, etc.)

**Returns:**
- `str`: Expiry date in YYYY-MM-DD format

**Example:**
```python
Utils.get_next_weekly_expiry(0)  # "2025-09-11"
Utils.get_next_weekly_expiry(1)  # "2025-09-18"
```

#### `get_next_tuesday_expiry(weeks_ahead: int = 0) -> str`
Get the next Tuesday expiry date (as originally requested).

**Parameters:**
- `weeks_ahead` (int): Number of weeks ahead (0 = next, 1 = following, etc.)

**Returns:**
- `str`: Expiry date in YYYY-MM-DD format

#### `get_monthly_expiry(year: int, month: int) -> str`
Get the monthly expiry date (last Thursday of the month).

**Parameters:**
- `year` (int): Year
- `month` (int): Month (1-12)

**Returns:**
- `str`: Monthly expiry date in YYYY-MM-DD format

#### `get_expiry_series(expiry_type: str, count: int) -> List[str]`
Get a series of expiry dates.

**Parameters:**
- `expiry_type` (str): "weekly", "tuesday", or "monthly"
- `count` (int): Number of expiry dates to return

**Returns:**
- `List[str]`: List of expiry dates

### Market Functions

#### `is_market_open(dt: Optional[datetime] = None) -> bool`
Check if the market is open at the given time.

**Parameters:**
- `dt` (datetime, optional): Time to check (defaults to now)

**Returns:**
- `bool`: True if market is open

#### `get_next_market_open() -> datetime`
Get the next market open time.

**Returns:**
- `datetime`: Next market open time

### Strike Price Functions

#### `format_strike_price(price: float, step: float = 50.0) -> float`
Format strike price to the nearest step.

**Parameters:**
- `price` (float): Current price
- `step` (float): Strike price step (default 50 for NIFTY)

**Returns:**
- `float`: Formatted strike price

#### `get_nearest_strikes(price: float, count: int = 5, step: float = 50.0) -> List[float]`
Get nearest strike prices around the current price.

**Parameters:**
- `price` (float): Current price
- `count` (int): Number of strikes to return
- `step` (float): Strike price step

**Returns:**
- `List[float]`: List of strike prices

### Expiry Analysis Functions

#### `calculate_days_to_expiry(expiry_date: str) -> int`
Calculate days remaining until expiry.

**Parameters:**
- `expiry_date` (str): Expiry date in YYYY-MM-DD format

**Returns:**
- `int`: Number of days until expiry

#### `is_expiry_today(expiry_date: str) -> bool`
Check if the given date is today's expiry.

**Parameters:**
- `expiry_date` (str): Expiry date in YYYY-MM-DD format

**Returns:**
- `bool`: True if expiry is today

#### `get_expiry_info(expiry_date: str) -> Dict[str, Any]`
Get comprehensive information about an expiry date.

**Parameters:**
- `expiry_date` (str): Expiry date in YYYY-MM-DD format

**Returns:**
- `Dict[str, Any]`: Expiry information dictionary

## Error Handling

All functions include comprehensive error handling:

- **ValueError**: Raised for invalid parameters (negative weeks_ahead, invalid expiry_type)
- **Date Format Errors**: Handled gracefully with informative error messages
- **Logging**: All errors are logged for debugging

## Market Holidays

The module includes a `MARKET_HOLIDAYS` list that can be updated with specific market holidays. Currently includes common Indian market holidays (commented out for reference).

## Thread Safety

All functions are static methods and thread-safe for concurrent use.

## Dependencies

- Python 3.7+
- Standard library only (datetime, calendar, logging)

## Testing

Run the test suite to verify functionality:

```bash
python3 test_utils.py
```

## Examples

See the example files for practical usage:

- `utils_example.py` - Comprehensive usage examples
- `demo_weekly_expiry.py` - Specific demonstration of weekly expiry function
- `test_utils.py` - Complete test suite

## Integration

The Utils class integrates seamlessly with your existing trading application:

```python
# In your trading application
from utils import Utils

# Get expiry for option chain
expiry = Utils.get_next_weekly_expiry(1)

# Get strikes for current price
strikes = Utils.get_nearest_strikes(current_price, 10)

# Check if market is open
if Utils.is_market_open():
    # Place trades
    pass
```

## License

This code is part of the market trading application and follows the same license terms.

