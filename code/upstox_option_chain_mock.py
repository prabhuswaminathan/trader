#!/usr/bin/env python3
"""
Mock version of UpstoxOptionChain for testing without upstox_client dependency.

This module provides the same interface as UpstoxOptionChain but uses mock data
for testing and development purposes.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
import random
from unittest.mock import Mock
from utils import Utils

logger = logging.getLogger("UpstoxOptionChainMock")

class UpstoxOptionChainMock:
    """
    Mock version of UpstoxOptionChain for testing.
    
    Provides the same interface as UpstoxOptionChain but uses mock data
    instead of making actual API calls.
    """
    
    # NIFTY instrument key
    NIFTY_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
    
    def __init__(self, access_token: str, underlying_instrument: str = "NIFTY"):
        """
        Initialize the UpstoxOptionChainMock.
        
        Args:
            access_token (str): Upstox API access token (ignored in mock)
            underlying_instrument (str): Underlying instrument (default: "NIFTY")
        """
        self.access_token = access_token
        self.underlying_instrument = underlying_instrument.upper()
        
        # Cache for option chain data
        self._option_chain_cache = {}
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutes cache
        
        # Generate mock data
        self._mock_data = self._generate_mock_data()
        
        # Mock API object for testing
        self.options_api = Mock()
        
        logger.info(f"UpstoxOptionChainMock initialized for {self.underlying_instrument}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        self.close()
    
    def close(self):
        """Close the API client and clean up resources."""
        try:
            if hasattr(self, 'api_client') and self.api_client:
                # self.api_client.close()
                self.api_client = None
            # Use a try-except to handle logger cleanup issues
            try:
                logger.debug("API client closed successfully")
            except:
                pass  # Ignore logger errors during cleanup
        except Exception as e:
            # Use a try-except to handle logger cleanup issues
            try:
                logger.warning(f"Error during API client cleanup: {e}")
            except:
                pass  # Ignore logger errors during cleanup
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except:
            pass  # Ignore any errors during destruction
    
    def _generate_mock_data(self) -> List[Dict[str, Any]]:
        """Generate mock option chain data."""
        mock_data = []
        
        # Generate expiries (next 4 Tuesdays)
        base_date = datetime.now()
        expiries = []
        for i in range(4):
            # Find next Tuesday
            days_until_tuesday = (1 - base_date.weekday()) % 7
            if days_until_tuesday == 0:
                days_until_tuesday = 7
            expiry_date = base_date + timedelta(days=days_until_tuesday + (i * 7))
            expiries.append(expiry_date.strftime("%Y-%m-%d"))
        
        # Generate strike prices around 25000
        base_strike = 25000
        strikes = [base_strike + (i - 10) * 50 for i in range(21)]  # 20 strikes around 25000
        
        # Generate option data
        for expiry in expiries:
            for strike in strikes:
                # Call option
                call_option = {
                    'instrument_key': f'NSE_OPT|NIFTY|{expiry}|{strike}|CE',
                    'instrument_name': f'NIFTY {strike} CE',
                    'strike_price': strike,
                    'expiry_date': expiry,
                    'option_type': 'CALL',
                    'last_price': round(random.uniform(10, 200), 2),
                    'bid_price': round(random.uniform(10, 200), 2),
                    'ask_price': round(random.uniform(10, 200), 2),
                    'volume': random.randint(100, 5000),
                    'open_interest': random.randint(1000, 50000),
                    'change': round(random.uniform(-20, 20), 2),
                    'change_percent': round(random.uniform(-10, 10), 2),
                    'implied_volatility': round(random.uniform(0.1, 0.5), 3),
                    'delta': round(random.uniform(0.1, 0.9), 3),
                    'gamma': round(random.uniform(0.001, 0.05), 4),
                    'theta': round(random.uniform(-5, -0.1), 3),
                    'vega': round(random.uniform(1, 30), 2),
                    'raw_data': {}
                }
                mock_data.append(call_option)
                
                # Put option
                put_option = {
                    'instrument_key': f'NSE_OPT|NIFTY|{expiry}|{strike}|PE',
                    'instrument_name': f'NIFTY {strike} PE',
                    'strike_price': strike,
                    'expiry_date': expiry,
                    'option_type': 'PUT',
                    'last_price': round(random.uniform(10, 200), 2),
                    'bid_price': round(random.uniform(10, 200), 2),
                    'ask_price': round(random.uniform(10, 200), 2),
                    'volume': random.randint(100, 5000),
                    'open_interest': random.randint(1000, 50000),
                    'change': round(random.uniform(-20, 20), 2),
                    'change_percent': round(random.uniform(-10, 10), 2),
                    'implied_volatility': round(random.uniform(0.1, 0.5), 3),
                    'delta': round(random.uniform(-0.9, -0.1), 3),
                    'gamma': round(random.uniform(0.001, 0.05), 4),
                    'theta': round(random.uniform(-5, -0.1), 3),
                    'vega': round(random.uniform(1, 30), 2),
                    'raw_data': {}
                }
                mock_data.append(put_option)
        
        return mock_data
    
    def fetch(self, expiry: Optional[str] = None, strike_price: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch option chain data for NIFTY (mock implementation).
        
        Args:
            expiry (str, optional): Expiry date in YYYY-MM-DD format. If None, uses next weekly expiry.
            strike_price (int, optional): Strike price to filter by
        
        Returns:
            List[Dict[str, Any]]: Option chain data
        """
        try:
            # If no expiry is provided, use next weekly expiry
            if expiry is None:
                expiry = self.get_next_weekly_expiry()
                if not expiry:
                    raise Exception("No expiry date available and unable to determine next weekly expiry")
            
            # Check cache first
            cache_key = f"{expiry}_{strike_price}"
            if self._is_cache_valid() and cache_key in self._option_chain_cache:
                logger.debug(f"Returning cached option chain data for {cache_key}")
                return self._option_chain_cache[cache_key]
            
            # Start with all mock data
            option_chain_data = self._mock_data.copy()
            
            # Filter by expiry if provided
            if expiry:
                option_chain_data = self._filter_by_expiry(option_chain_data, expiry)
            
            # Filter by strike price if provided
            if strike_price is not None:
                option_chain_data = self._filter_by_strike_price(option_chain_data, strike_price)
            
            # Cache the result
            self._option_chain_cache[cache_key] = option_chain_data
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Successfully fetched {len(option_chain_data)} option contracts (mock data)")
            return option_chain_data
            
        except Exception as e:
            logger.error(f"Error fetching option chain data: {e}")
            raise
    
    def fetch_all_expiries(self, strike_price: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch option chain data for all available expiries (mock implementation).
        
        Args:
            strike_price (int, optional): Strike price to filter by
        
        Returns:
            List[Dict[str, Any]]: Combined option chain data from all expiries
        """
        try:
            all_data = []
            expiries = self.get_available_expiries()
            
            logger.info(f"Fetching option chain data for {len(expiries)} expiries (mock data)")
            
            for expiry in expiries:
                try:
                    expiry_data = self.fetch(expiry=expiry, strike_price=strike_price)
                    all_data.extend(expiry_data)
                    logger.debug(f"Fetched {len(expiry_data)} contracts for expiry {expiry}")
                except Exception as e:
                    logger.warning(f"Failed to fetch data for expiry {expiry}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(all_data)} total option contracts across all expiries (mock data)")
            return all_data
            
        except Exception as e:
            logger.error(f"Error fetching all expiries data: {e}")
            raise
    
    def _filter_by_expiry(self, option_data: List[Dict[str, Any]], expiry: str) -> List[Dict[str, Any]]:
        """Filter option data by expiry date."""
        try:
            filtered_data = []
            for option in option_data:
                if option.get('expiry_date') == expiry:
                    filtered_data.append(option)
            
            logger.debug(f"Filtered by expiry {expiry}: {len(filtered_data)} contracts")
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error filtering by expiry: {e}")
            return option_data
    
    def _filter_by_strike_price(self, option_data: List[Dict[str, Any]], strike_price: int) -> List[Dict[str, Any]]:
        """Filter option data by strike price."""
        try:
            filtered_data = []
            for option in option_data:
                if option.get('strike_price') == strike_price:
                    filtered_data.append(option)
            
            logger.debug(f"Filtered by strike price {strike_price}: {len(filtered_data)} contracts")
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error filtering by strike price: {e}")
            return option_data
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache_timestamp is None:
            return False
        
        time_diff = (datetime.now() - self._cache_timestamp).total_seconds()
        return time_diff < self._cache_duration
    
    def get_next_weekly_expiry(self) -> str:
        """
        Get the next weekly expiry date using Utils function.
        
        Returns:
            str: Next weekly expiry date in YYYY-MM-DD format
        """
        try:
            # Use Utils function to get next weekly expiry list and return the first one
            expiries = Utils.get_next_weekly_expiry()
            return expiries[0] if expiries else ""
        except Exception as e:
            logger.error(f"Error getting next weekly expiry: {e}")
            return ""
    
    def get_available_expiries(self) -> List[str]:
        """
        Get list of available expiry dates (mock implementation).
        
        Returns:
            List[str]: List of expiry dates in YYYY-MM-DD format
        """
        try:
            # Use Utils function to get next 5 weekly expiries
            expiries = Utils.get_next_weekly_expiry()
            logger.info(f"Generated {len(expiries)} available expiries: {expiries}")
            return expiries
            
        except Exception as e:
            logger.error(f"Error getting available expiries: {e}")
            return []
    
    def get_available_strike_prices(self, expiry: Optional[str] = None) -> List[int]:
        """Get list of available strike prices."""
        try:
            data = self._mock_data
            if expiry:
                data = self._filter_by_expiry(data, expiry)
            
            strikes = set()
            for option in data:
                strike = option.get('strike_price')
                if strike is not None:
                    strikes.add(int(strike))
            
            return sorted(list(strikes))
            
        except Exception as e:
            logger.error(f"Error getting available strike prices: {e}")
            return []
    
    def get_option_summary(self, expiry: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for option chain."""
        try:
            data = self.fetch(expiry=expiry)
            
            if not data:
                return {
                    'total_contracts': 0,
                    'call_contracts': 0,
                    'put_contracts': 0,
                    'expiries': [],
                    'strike_range': {'min': None, 'max': None},
                    'total_volume': 0,
                    'total_open_interest': 0
                }
            
            call_contracts = [opt for opt in data if opt.get('option_type') == 'CALL']
            put_contracts = [opt for opt in data if opt.get('option_type') == 'PUT']
            
            strikes = [opt.get('strike_price') for opt in data if opt.get('strike_price') is not None]
            expiries = list(set(opt.get('expiry_date') for opt in data if opt.get('expiry_date')))
            
            total_volume = sum(opt.get('volume', 0) or 0 for opt in data)
            total_oi = sum(opt.get('open_interest', 0) or 0 for opt in data)
            
            return {
                'total_contracts': len(data),
                'call_contracts': len(call_contracts),
                'put_contracts': len(put_contracts),
                'expiries': sorted(expiries),
                'strike_range': {
                    'min': min(strikes) if strikes else None,
                    'max': max(strikes) if strikes else None
                },
                'total_volume': total_volume,
                'total_open_interest': total_oi
            }
            
        except Exception as e:
            logger.error(f"Error getting option summary: {e}")
            return {}
    
    def clear_cache(self) -> None:
        """Clear the option chain cache."""
        self._option_chain_cache.clear()
        self._cache_timestamp = None
        logger.debug("Option chain cache cleared")
    
    def set_cache_duration(self, duration_seconds: int) -> None:
        """Set cache duration in seconds."""
        self._cache_duration = duration_seconds
        logger.debug(f"Cache duration set to {duration_seconds} seconds")
    
    def _parse_option_chain_response(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Parse the raw API response into a standardized format (mock implementation).
        
        Args:
            raw_data: Raw response data from Upstox API
            
        Returns:
            List[Dict[str, Any]]: Parsed option chain data
        """
        try:
            parsed_data = []
            
            # Handle different response formats
            if isinstance(raw_data, list):
                data_list = raw_data
            elif hasattr(raw_data, '__iter__'):
                data_list = list(raw_data)
            else:
                logger.warning("Unexpected data format from API")
                return []
            
            for i, item in enumerate(data_list):
                try:
                    # Convert to dictionary if needed
                    if hasattr(item, '__dict__'):
                        item_dict = item.__dict__
                    elif isinstance(item, dict):
                        item_dict = item
                    else:
                        continue
                    
                    # Debug: Log all available keys in the item
                    logger.debug(f"Item {i} keys: {list(item_dict.keys())}")
                    
                    # Check if this is a direct option object (alternative format)
                    if item_dict.get('option_type') in ['CALL', 'PUT']:
                        parsed_option = self._parse_direct_option(item_dict)
                        if parsed_option:
                            parsed_data.append(parsed_option)
                        continue
                    
                    # Check for different possible field names for strike price and expiry
                    def safe_get(data, *keys):
                        """Safely get value from dict or object with multiple possible keys"""
                        for key in keys:
                            if isinstance(data, dict):
                                if key in data:
                                    return data[key]
                            else:
                                if hasattr(data, key):
                                    return getattr(data, key)
                        return None
                    
                    strike_price = safe_get(item_dict, 'strike_price', '_strike_price', 'strike', 'strikePrice', 'strikePriceValue')
                    
                    expiry = safe_get(item_dict, 'expiry', '_expiry', 'expiry_date', 'expiryDate', 'expiryDateValue')
                    
                    logger.debug(f"Item {i} - strike_price: {strike_price}, expiry: {expiry}")
                    
                    # Check if item has required fields for grouped format
                    if not strike_price or not expiry:
                        logger.warning(f"Item {i} missing required fields (strike_price: {strike_price}, expiry: {expiry})")
                        logger.warning(f"Available fields: {list(item_dict.keys())}")
                        continue
                    
                    # Parse both call and put options from the item (grouped format)
                    call_option = self._parse_single_option(item_dict, 'CALL')
                    put_option = self._parse_single_option(item_dict, 'PUT')
                    
                    if call_option:
                        parsed_data.append(call_option)
                    if put_option:
                        parsed_data.append(put_option)
                        
                except Exception as e:
                    logger.warning(f"Error parsing option data for item {i}: {e}")
                    continue
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing option chain response: {e}")
            return []
    
    def _parse_direct_option(self, item_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a direct option object (alternative format).
        
        Args:
            item_dict (Dict[str, Any]): Direct option data
            
        Returns:
            Optional[Dict[str, Any]]: Parsed option data or None if invalid
        """
        try:
            # Extract fields directly from the option object
            parsed_option = {
                'instrument_key': item_dict.get('instrument_key', ''),
                'instrument_name': item_dict.get('instrument_name', ''),
                'strike_price': self._safe_float(item_dict.get('strike_price')),
                'expiry_date': item_dict.get('expiry_date', ''),
                'option_type': item_dict.get('option_type', '').upper(),
                'last_price': self._safe_float(item_dict.get('last_price')),
                'bid_price': self._safe_float(item_dict.get('bid_price')),
                'ask_price': self._safe_float(item_dict.get('ask_price')),
                'volume': self._safe_int(item_dict.get('volume')),
                'open_interest': self._safe_int(item_dict.get('open_interest')),
                'close_price': self._safe_float(item_dict.get('close_price')),
                'change': self._safe_float(item_dict.get('change')),
                'change_percent': self._safe_float(item_dict.get('change_percent')),
                'implied_volatility': self._safe_float(item_dict.get('implied_volatility')),
                'delta': self._safe_float(item_dict.get('delta')),
                'gamma': self._safe_float(item_dict.get('gamma')),
                'theta': self._safe_float(item_dict.get('theta')),
                'vega': self._safe_float(item_dict.get('vega')),
                'pop': self._safe_float(item_dict.get('pop')),
                'underlying_key': item_dict.get('underlying_key', ''),
                'underlying_spot_price': self._safe_float(item_dict.get('underlying_spot_price')),
                'pcr': self._safe_float(item_dict.get('pcr')),
                'raw_data': item_dict
            }
            
            # Calculate change and change_percent if we have close_price and last_price
            if parsed_option['close_price'] and parsed_option['last_price']:
                change = parsed_option['last_price'] - parsed_option['close_price']
                parsed_option['change'] = change
                if parsed_option['close_price'] != 0:
                    parsed_option['change_percent'] = (change / parsed_option['close_price']) * 100
                else:
                    parsed_option['change_percent'] = 0
            
            # Validate required fields
            if not parsed_option['strike_price'] or not parsed_option['expiry_date']:
                return None
            
            return parsed_option
            
        except Exception as e:
            logger.warning(f"Error parsing direct option: {e}")
            return None
    
    def _parse_single_option(self, item_dict: Dict[str, Any], option_type: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single option contract from the API response (mock implementation).
        
        Args:
            item_dict (Dict[str, Any]): Raw option data containing both call and put options
            option_type (str): 'CALL' or 'PUT' to specify which option to parse
            
        Returns:
            Optional[Dict[str, Any]]: Parsed option data or None if invalid
        """
        try:
            # Extract common fields from the main item with multiple possible field names
            # Handle both dictionary and object responses
            def safe_get(data, *keys):
                """Safely get value from dict or object with multiple possible keys"""
                for key in keys:
                    if isinstance(data, dict):
                        if key in data:
                            return data[key]
                    else:
                        if hasattr(data, key):
                            return getattr(data, key)
                return None
            
            expiry = (safe_get(item_dict, 'expiry', '_expiry', 'expiry_date', 'expiryDate', 'expiryDateValue') or '')
            
            strike_price = self._safe_float(
                safe_get(item_dict, 'strike_price', '_strike_price', 'strike', 'strikePrice', 'strikePriceValue')
            )
            
            underlying_key = (safe_get(item_dict, 'underlying_key', '_underlying_key', 'underlyingKey', 'underlying') or '')
            
            underlying_spot_price = self._safe_float(
                safe_get(item_dict, 'underlying_spot_price', '_underlying_spot_price', 'underlyingSpotPrice', 'spot_price', 'spotPrice')
            )
            
            pcr = self._safe_float(
                safe_get(item_dict, 'pcr', '_pcr', 'putCallRatio', 'put_call_ratio')
            )  # Put-Call Ratio
            
            # Get the specific option data (call or put) with multiple possible field names
            option_key = f'{option_type.lower()}_options'
            option_data = safe_get(item_dict, option_key, f'_{option_type.lower()}_options', f'{option_type.lower()}Options', f'{option_type.lower()}_option', f'{option_type.lower()}Option') or {}
            
            if not option_data:
                return None
            
            # Extract market data with multiple possible field names
            market_data = safe_get(option_data, 'market_data', 'marketData', 'market', 'price_data', 'priceData') or {}
            
            option_greeks = safe_get(option_data, 'option_greeks', 'optionGreeks', 'greeks', 'Greeks') or {}
            
            # Build the parsed option data
            parsed_option = {
                'instrument_key': safe_get(option_data, 'instrument_key', 'instrumentKey', 'instrument') or '',
                'instrument_name': f'NIFTY {int(strike_price)} {option_type}' if strike_price else '',
                'strike_price': strike_price,
                'expiry_date': expiry,
                'option_type': option_type,
                'last_price': self._safe_float(
                    safe_get(market_data, 'ltp', 'last_price', 'lastPrice', 'price', 'current_price', 'currentPrice')
                ),
                'bid_price': self._safe_float(
                    safe_get(market_data, 'bid_price', 'bidPrice', 'bid', 'best_bid', 'bestBid')
                ),
                'ask_price': self._safe_float(
                    safe_get(market_data, 'ask_price', 'askPrice', 'ask', 'best_ask', 'bestAsk')
                ),
                'volume': self._safe_int(
                    safe_get(market_data, 'volume', 'vol', 'traded_volume', 'tradedVolume')
                ),
                'open_interest': self._safe_int(
                    safe_get(market_data, 'oi', 'open_interest', 'openInterest', 'openInt')
                ),
                'close_price': self._safe_float(
                    safe_get(market_data, 'close_price', 'closePrice', 'close', 'previous_close', 'previousClose')
                ),
                'bid_qty': self._safe_int(
                    safe_get(market_data, 'bid_qty', 'bidQty', 'bid_quantity', 'bidQuantity')
                ),
                'ask_qty': self._safe_int(
                    safe_get(market_data, 'ask_qty', 'askQty', 'ask_quantity', 'askQuantity')
                ),
                'prev_oi': self._safe_int(
                    safe_get(market_data, 'prev_oi', 'prevOi', 'previous_oi', 'previousOi')
                ),
                'implied_volatility': self._safe_float(safe_get(option_greeks, 'iv', 'implied_volatility', 'impliedVolatility', 'volatility')),
                'delta': self._safe_float(safe_get(option_greeks, 'delta')),
                'gamma': self._safe_float(safe_get(option_greeks, 'gamma')),
                'theta': self._safe_float(safe_get(option_greeks, 'theta')),
                'vega': self._safe_float(safe_get(option_greeks, 'vega')),
                'pop': self._safe_float(safe_get(option_greeks, 'pop')),  # Probability of Profit
                'underlying_key': underlying_key,
                'underlying_spot_price': underlying_spot_price,
                'pcr': pcr,  # Put-Call Ratio for this strike
                'raw_data': item_dict  # Keep original data for debugging
            }
            
            # Calculate change and change_percent if we have close_price and last_price
            if parsed_option['close_price'] and parsed_option['last_price']:
                change = parsed_option['last_price'] - parsed_option['close_price']
                parsed_option['change'] = change
                if parsed_option['close_price'] != 0:
                    parsed_option['change_percent'] = (change / parsed_option['close_price']) * 100
                else:
                    parsed_option['change_percent'] = 0
            else:
                parsed_option['change'] = None
                parsed_option['change_percent'] = None
            
            # Validate required fields
            if not parsed_option['strike_price'] or not parsed_option['expiry_date']:
                return None
            
            return parsed_option
            
        except Exception as e:
            logger.warning(f"Error parsing single option: {e}")
            return None
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        try:
            if value is None or value == '':
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int."""
        try:
            if value is None or value == '':
                return None
            return int(value)
        except (ValueError, TypeError):
            return None


# Example usage
if __name__ == "__main__":
    print("UpstoxOptionChainMock Example Usage")
    print("=" * 50)
    
    try:
        # Initialize the mock option chain fetcher
        option_chain = UpstoxOptionChainMock("test_token")
        
        # Get next weekly expiry using Utils
        print("Fetching next weekly expiry...")
        next_expiry = option_chain.get_next_weekly_expiry()
        print(f"Next weekly expiry: {next_expiry}")
        
        # Get strike prices for next expiry
        if next_expiry:
            print(f"\nFetching strike prices for {next_expiry}...")
            strikes = option_chain.get_available_strike_prices(next_expiry)
            print(f"Available strikes: {strikes[:10]}...")  # Show first 10
            
            # Fetch specific option data
            print(f"\nFetching option data for {next_expiry}...")
            options = option_chain.fetch(expiry=next_expiry)
            print(f"Found {len(options)} option contracts")
            
            # Show sample data
            if options:
                print("\nSample option data:")
                sample = options[0]
                for key, value in sample.items():
                    if key != 'raw_data':  # Skip raw data for display
                        print(f"  {key}: {value}")
        
        # Get summary
        print("\nOption chain summary:")
        summary = option_chain.get_option_summary()
        for key, value in summary.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
