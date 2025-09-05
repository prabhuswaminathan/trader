# UpstoxOptionChain Class

A comprehensive Python class for fetching and managing NIFTY option chain data from the Upstox API.

## Features

### 🔗 **Option Chain Data Fetching**
- **Full Option Chain**: Fetch complete option chain data for NIFTY
- **Expiry Filtering**: Filter options by specific expiry dates
- **Strike Price Filtering**: Filter options by specific strike prices
- **Combined Filtering**: Filter by both expiry and strike price simultaneously

### 📊 **Data Management**
- **Caching**: Built-in caching system for improved performance
- **Data Parsing**: Automatic parsing and standardization of API responses
- **Error Handling**: Comprehensive error handling and logging
- **Data Validation**: Validates and cleans option data

### 📈 **Analytics & Utilities**
- **Summary Statistics**: Get comprehensive option chain summaries
- **Available Expiries**: List all available expiry dates
- **Available Strikes**: List all available strike prices
- **Option Greeks**: Access to delta, gamma, theta, vega, and implied volatility

## Quick Start

### 1. Installation

```bash
# Install required dependencies
pip install upstox-python
```

### 2. Basic Usage

```python
from upstox_option_chain import UpstoxOptionChain

# Initialize with your access token
option_chain = UpstoxOptionChain(access_token="your_access_token")

# Fetch all option data
all_options = option_chain.fetch()

# Fetch by expiry
expiry_options = option_chain.fetch(expiry="2025-09-09")

# Fetch by strike price
strike_options = option_chain.fetch(strike_price=25000)

# Fetch by both expiry and strike
specific_options = option_chain.fetch(expiry="2025-09-09", strike_price=25000)
```

### 3. Get Available Data

```python
# Get available expiries
expiries = option_chain.get_available_expiries()
print(f"Available expiries: {expiries}")

# Get available strike prices
strikes = option_chain.get_available_strike_prices()
print(f"Available strikes: {strikes}")

# Get strike prices for specific expiry
expiry_strikes = option_chain.get_available_strike_prices(expiry="2025-09-09")
print(f"Strikes for 2025-09-09: {expiry_strikes}")
```

### 4. Get Summary Statistics

```python
# Get overall summary
summary = option_chain.get_option_summary()
print(f"Total contracts: {summary['total_contracts']}")
print(f"Call contracts: {summary['call_contracts']}")
print(f"Put contracts: {summary['put_contracts']}")

# Get summary for specific expiry
expiry_summary = option_chain.get_option_summary(expiry="2025-09-09")
print(f"Contracts for 2025-09-09: {expiry_summary['total_contracts']}")
```

## API Reference

### Class: `UpstoxOptionChain`

#### Constructor

```python
UpstoxOptionChain(access_token: str, underlying_instrument: str = "NIFTY")
```

**Parameters:**
- `access_token` (str): Upstox API access token
- `underlying_instrument` (str): Underlying instrument (default: "NIFTY")

#### Methods

### `fetch(expiry: Optional[str] = None, strike_price: Optional[int] = None) -> List[Dict[str, Any]]`

Fetch option chain data with optional filtering.

**Parameters:**
- `expiry` (str, optional): Expiry date in YYYY-MM-DD format
- `strike_price` (int, optional): Strike price to filter by

**Returns:**
- `List[Dict[str, Any]]`: List of option contracts

**Example:**
```python
# Fetch all options
all_options = option_chain.fetch()

# Fetch specific expiry
expiry_options = option_chain.fetch(expiry="2025-09-09")

# Fetch specific strike
strike_options = option_chain.fetch(strike_price=25000)

# Fetch specific expiry and strike
specific_options = option_chain.fetch(expiry="2025-09-09", strike_price=25000)
```

### `get_available_expiries() -> List[str]`

Get list of available expiry dates.

**Returns:**
- `List[str]`: List of expiry dates in YYYY-MM-DD format

### `get_available_strike_prices(expiry: Optional[str] = None) -> List[int]`

Get list of available strike prices.

**Parameters:**
- `expiry` (str, optional): Filter by specific expiry

**Returns:**
- `List[int]`: List of strike prices

### `get_option_summary(expiry: Optional[str] = None) -> Dict[str, Any]`

Get comprehensive summary statistics.

**Parameters:**
- `expiry` (str, optional): Filter by specific expiry

**Returns:**
- `Dict[str, Any]`: Summary statistics including:
  - `total_contracts`: Total number of contracts
  - `call_contracts`: Number of call contracts
  - `put_contracts`: Number of put contracts
  - `expiries`: List of available expiries
  - `strike_range`: Min and max strike prices
  - `total_volume`: Total volume across all contracts
  - `total_open_interest`: Total open interest

### Cache Methods

### `clear_cache() -> None`

Clear the option chain cache.

### `set_cache_duration(duration_seconds: int) -> None`

Set cache duration in seconds.

**Parameters:**
- `duration_seconds` (int): Cache duration in seconds

## Data Structure

Each option contract contains the following fields:

```python
{
    'instrument_key': 'NSE_OPT|NIFTY|2025-09-09|25000|CE',
    'instrument_name': 'NIFTY 25000 CE',
    'strike_price': 25000,
    'expiry_date': '2025-09-09',
    'option_type': 'CALL',  # or 'PUT'
    'last_price': 100.50,
    'bid_price': 99.00,
    'ask_price': 101.00,
    'volume': 1500,
    'open_interest': 25000,
    'change': 5.50,
    'change_percent': 5.80,
    'implied_volatility': 0.25,
    'delta': 0.55,
    'gamma': 0.02,
    'theta': -1.50,
    'vega': 12.30,
    'raw_data': {}  # Original API response data
}
```

## Integration Examples

### 1. Basic Option Chain Analysis

```python
from upstox_option_chain import UpstoxOptionChain
from utils import Utils

# Initialize
option_chain = UpstoxOptionChain(access_token)

# Get next weekly expiry
next_expiry = Utils.get_next_weekly_expiry(0)

# Fetch options for next expiry
options = option_chain.fetch(expiry=next_expiry)

# Analyze call vs put distribution
calls = [opt for opt in options if opt['option_type'] == 'CALL']
puts = [opt for opt in options if opt['option_type'] == 'PUT']

print(f"Next expiry: {next_expiry}")
print(f"Call contracts: {len(calls)}")
print(f"Put contracts: {len(puts)}")
```

### 2. ATM (At-The-Money) Options

```python
# Get current price and nearest strikes
current_price = 25000
nearest_strikes = Utils.get_nearest_strikes(current_price, 5)

# Find ATM options
for strike in nearest_strikes:
    options = option_chain.fetch(expiry=next_expiry, strike_price=strike)
    if options:
        call = next((opt for opt in options if opt['option_type'] == 'CALL'), None)
        put = next((opt for opt in options if opt['option_type'] == 'PUT'), None)
        
        if call and put:
            print(f"Strike {strike}: Call {call['last_price']}, Put {put['last_price']}")
```

### 3. Iron Condor Setup

```python
# Define Iron Condor strikes
atm_strike = 25000
iron_condor_strikes = [atm_strike - 100, atm_strike, atm_strike + 100, atm_strike + 200]

print("Iron Condor Setup:")
for strike in iron_condor_strikes:
    options = option_chain.fetch(expiry=next_expiry, strike_price=strike)
    if options:
        call = next((opt for opt in options if opt['option_type'] == 'CALL'), None)
        put = next((opt for opt in options if opt['option_type'] == 'PUT'), None)
        
        if call and put:
            print(f"Strike {strike}: Call {call['last_price']}, Put {put['last_price']}")
```

### 4. Volume and Open Interest Analysis

```python
# Get summary statistics
summary = option_chain.get_option_summary()

print(f"Total volume: {summary['total_volume']:,}")
print(f"Total open interest: {summary['total_open_interest']:,}")

# Find high volume options
high_volume_options = [opt for opt in all_options if opt['volume'] > 1000]
print(f"High volume options: {len(high_volume_options)}")

# Find high OI options
high_oi_options = [opt for opt in all_options if opt['open_interest'] > 10000]
print(f"High OI options: {len(high_oi_options)}")
```

### 5. Greeks Analysis

```python
# Analyze option Greeks
for option in options[:5]:  # Show first 5 options
    print(f"{option['instrument_name']}:")
    print(f"  Delta: {option['delta']}")
    print(f"  Gamma: {option['gamma']}")
    print(f"  Theta: {option['theta']}")
    print(f"  Vega: {option['vega']}")
    print(f"  IV: {option['implied_volatility']}")
```

## Error Handling

The class includes comprehensive error handling:

```python
try:
    options = option_chain.fetch(expiry="2025-09-09")
except Exception as e:
    print(f"Error fetching options: {e}")
```

## Caching

The class includes built-in caching for improved performance:

```python
# Set cache duration (default: 5 minutes)
option_chain.set_cache_duration(300)

# Clear cache when needed
option_chain.clear_cache()
```

## Mock Version for Testing

For testing and development, use the mock version:

```python
from upstox_option_chain_mock import UpstoxOptionChainMock

# Initialize mock version
option_chain = UpstoxOptionChainMock("test_token")

# Same interface as real version
options = option_chain.fetch()
```

## Dependencies

- Python 3.7+
- upstox-python
- Standard library modules (datetime, logging, typing)

## File Structure

```
code/
├── upstox_option_chain.py          # Main UpstoxOptionChain class
├── upstox_option_chain_mock.py     # Mock version for testing
└── ...

test_upstox_option_chain.py         # Test script for real version
test_upstox_option_chain_mock.py    # Test script for mock version
upstox_option_chain_example.py      # Usage examples
```

## Testing

Run the test scripts to verify functionality:

```bash
# Test mock version (no API key required)
python3 test_upstox_option_chain_mock.py

# Test real version (requires valid access token)
python3 test_upstox_option_chain.py

# Run examples
python3 upstox_option_chain_example.py
```

## Performance

- **Caching**: Reduces API calls and improves response time
- **Efficient Filtering**: Fast filtering operations
- **Memory Management**: Optimized data structures
- **Error Recovery**: Graceful handling of API errors

## License

This code is part of the market trading application and follows the same license terms.

## Support

For issues and questions:
1. Check the test scripts for usage examples
2. Review the error logs for debugging information
3. Ensure you have a valid Upstox access token
4. Verify your API permissions for option chain data

