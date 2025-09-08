#!/usr/bin/env python3
"""
UpstoxOptionChain class for fetching option chain data from Upstox API.

This module provides functionality to fetch NIFTY option chain data
with filtering by expiry date and strike price.
"""

import logging
import upstox_client
from upstox_client.api import OptionsApi
from upstox_client.rest import ApiException
from typing import List, Dict, Optional, Any
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from trade_utils import Utils

logger = logging.getLogger("UpstoxOptionChain")

WEEKLY_EXPIRY_INDEX = 1

class UpstoxOptionChain:
    """
    Class to fetch option chain data from Upstox API for NIFTY options.
    
    Provides methods to fetch option chain data with filtering by
    expiry date and strike price.
    """
    
    # NIFTY instrument key
    NIFTY_INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"
    
    def __init__(self, access_token: str, underlying_instrument: str = "NIFTY"):
        """
        Initialize the UpstoxOptionChain.
        
        Args:
            access_token (str): Upstox API access token
            underlying_instrument (str): Underlying instrument (default: "NIFTY")
        """
        self.access_token = access_token
        self.underlying_instrument = underlying_instrument.upper()
        
        # Configure Upstox API client
        self.configuration = upstox_client.Configuration()
        self.configuration.access_token = self.access_token
        self.api_client = upstox_client.ApiClient(self.configuration)
        self.options_api = OptionsApi(self.api_client)
        
        # Cache for option chain data
        self._option_chain_cache = {}
        self._cache_timestamp = None
        self._cache_duration = 300  # 5 minutes cache
        
        logger.info(f"UpstoxOptionChain initialized for {self.underlying_instrument}")
    
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
                self.api_client.close()
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
    
    def fetch(self, expiry: Optional[str] = None, strike_price: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch option chain data for NIFTY.
        
        Args:
            expiry (str, optional): Expiry date in YYYY-MM-DD format. If None, uses next weekly expiry.
            strike_price (int, optional): Strike price to filter by
        
        Returns:
            List[Dict[str, Any]]: Option chain data
            
        Raises:
            Exception: If API call fails or data is invalid
        """
        try:
            # If no expiry is provided, use next weekly expiry
            if expiry is None:
                expiries = self.get_next_weekly_expiry(WEEKLY_EXPIRY_INDEX)
                if not expiries:
                    raise Exception("No expiry date available and unable to determine next weekly expiry")
                expiry = expiries[0]  # Use the first (next) expiry
            
            # Check cache first
            cache_key = f"{expiry}_{strike_price}"
            if self._is_cache_valid() and cache_key in self._option_chain_cache:
                logger.debug(f"Returning cached option chain data for {cache_key}")
                return self._option_chain_cache[cache_key]
            
            # Fetch fresh data from API
            logger.info(f"Fetching option chain data for {self.underlying_instrument}")
            logger.debug(f"Parameters - Expiry: {expiry}, Strike Price: {strike_price}")
            
            # Call Upstox API to get option chain
            api_response = self.options_api.get_put_call_option_chain(
                instrument_key=self.NIFTY_INSTRUMENT_KEY,
                expiry_date=expiry
            )
            
            if not api_response or not hasattr(api_response, 'data'):
                raise Exception("Invalid response from Upstox API")
            
            # Parse the response data
            option_chain_data = self._parse_option_chain_response(api_response.data)
            
            # Filter by strike price if provided
            if strike_price is not None:
                option_chain_data = self._filter_by_strike_price(option_chain_data, strike_price)
            
            # Cache the result
            self._option_chain_cache[cache_key] = option_chain_data
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Successfully fetched {len(option_chain_data)} option contracts")
            return option_chain_data
            
        except ApiException as e:
            logger.error(f"Upstox API error: {e}")
            raise Exception(f"Failed to fetch option chain data: {e}")
        except Exception as e:
            logger.error(f"Error fetching option chain data: {e}")
            raise
    
    def fetch_all_expiries(self, strike_price: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch option chain data for all available expiries.
        
        Args:
            strike_price (int, optional): Strike price to filter by
        
        Returns:
            List[Dict[str, Any]]: Combined option chain data from all expiries
            
        Raises:
            Exception: If API call fails or data is invalid
        """
        try:
            all_data = []
            expiries = self.get_available_expiries()
            
            logger.info(f"Fetching option chain data for {len(expiries)} expiries")
            
            for expiry in expiries:
                try:
                    expiry_data = self.fetch(expiry=expiry, strike_price=strike_price)
                    all_data.extend(expiry_data)
                    logger.debug(f"Fetched {len(expiry_data)} contracts for expiry {expiry}")
                except Exception as e:
                    logger.warning(f"Failed to fetch data for expiry {expiry}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(all_data)} total option contracts across all expiries")
            return all_data
            
        except Exception as e:
            logger.error(f"Error fetching all expiries data: {e}")
            raise
    
    def _parse_option_chain_response(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Parse the raw API response into a standardized format.
        
        The Upstox API returns data in the format:
            {
            "status": "success",
            "data": [
                {
                "expiry": "2025-02-13",
                "pcr": 7515.3,
                "strike_price": 21100,
                "underlying_key": "NSE_INDEX|Nifty 50",
                "underlying_spot_price": 22976.2,
                "call_options": {
                    "instrument_key": "NSE_FO|51059",
                    "market_data": {
                    "ltp": 2449.9,
                    "volume": 0,
                    "oi": 750,
                    "close_price": 2449.9,
                    "bid_price": 1856.65,
                    "bid_qty": 1125,
                    "ask_price": 1941.65,
                    "ask_qty": 1125,
                    "prev_oi": 1500
                    },
                    "option_greeks": {
                    "vega": 4.1731,
                    "theta": -472.8941,
                    "gamma": 0.0001,
                    "delta": 0.743,
                    "iv": 262.31,
                    "pop": 40.56
                    }
                },
                "put_options": {
                    "instrument_key": "NSE_FO|51060",
                    "market_data": {
                    "ltp": 0.3,
                    "volume": 22315725,
                    "oi": 5636475,
                    "close_price": 0.35,
                    "bid_price": 0.3,
                    "bid_qty": 1979400,
                    "ask_price": 0.35,
                    "ask_qty": 2152500,
                    "prev_oi": 5797500
                    },
                    "option_greeks": {
                    "vega": 0.0568,
                    "theta": -1.2461,
                    "gamma": 0,
                    "delta": -0.0013,
                    "iv": 50.78,
                    "pop": 0.15
                    }
                }
                }
            ]
            }        
        Args:
            raw_data: Raw response data from Upstox API
            
        Returns:
            List[Dict[str, Any]]: Parsed option chain data
        """
        try:
            parsed_data = []
            
            # Debug logging
            logger.debug(f"Raw data type: {type(raw_data)}")
            if raw_data is not None:
                logger.debug(f"Raw data length: {len(raw_data) if hasattr(raw_data, '__len__') else 'N/A'}")
            
            # Handle different response formats
            if isinstance(raw_data, list):
                data_list = raw_data
                logger.debug(f"Processing list with {len(data_list)} items")
            elif hasattr(raw_data, '__iter__'):
                data_list = list(raw_data)
                logger.debug(f"Processing iterable with {len(data_list)} items")
            else:
                logger.warning(f"Unexpected data format from API: {type(raw_data)}")
                return []
            
            if not data_list:
                logger.warning("Empty data list received from API")
                return []
            
            for i, item in enumerate(data_list):
                try:
                    logger.debug(f"Processing item {i}: {type(item)}")
                    
                    # Convert to dictionary if needed
                    if hasattr(item, '__dict__'):
                        item_dict = item.__dict__
                        logger.debug(f"Converted object to dict with keys: {list(item_dict.keys())}")
                    elif isinstance(item, dict):
                        item_dict = item
                        logger.debug(f"Item is dict with keys: {list(item_dict.keys())}")
                    else:
                        logger.warning(f"Skipping non-dict item: {type(item)}")
                        continue
                    
                    # Debug: Log all available keys in the item
                    logger.debug(f"Item {i} keys: {list(item_dict.keys())}")
                    
                    # Check if this is a direct option object (alternative format)
                    if item_dict.get('option_type') in ['CALL', 'PUT']:
                        logger.debug(f"Found direct option object: {item_dict.get('option_type')}")
                        parsed_option = self._parse_direct_option(item_dict)
                        if parsed_option:
                            parsed_data.append(parsed_option)
                            logger.debug(f"Added direct {parsed_option.get('option_type')} option for strike {parsed_option.get('strike_price')}")
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
                        logger.debug(f"Added call option for strike {call_option.get('strike_price')}")
                    else:
                        logger.debug(f"No call option found for item {i}")
                    
                    if put_option:
                        parsed_data.append(put_option)
                        logger.debug(f"Added put option for strike {put_option.get('strike_price')}")
                    else:
                        logger.debug(f"No put option found for item {i}")
                        
                except Exception as e:
                    logger.warning(f"Error parsing option data for item {i}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(parsed_data)} option contracts from {len(data_list)} items")
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
        Parse a single option contract from the API response.
        
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
            
            logger.debug(f"Parsing {option_type} option for strike {strike_price}, expiry {expiry}")
            logger.debug(f"Option key: {option_key}, data exists: {bool(option_data)}")
            
            if not option_data:
                logger.debug(f"No {option_type} option data found for strike {strike_price}")
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
                'implied_volatility': self._safe_float(
                    safe_get(option_greeks, 'iv', 'implied_volatility', 'impliedVolatility', 'volatility')
                ),
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
    
    def _filter_by_expiry(self, option_data: List[Dict[str, Any]], expiry: str) -> List[Dict[str, Any]]:
        """
        Filter option data by expiry date.
        
        Args:
            option_data (List[Dict[str, Any]]): Option chain data
            expiry (str): Expiry date in YYYY-MM-DD format
        
        Returns:
            List[Dict[str, Any]]: Filtered option data
        """
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
        """
        Filter option data by strike price.
        
        Args:
            option_data (List[Dict[str, Any]]): Option chain data
            strike_price (int): Strike price to filter by
        
        Returns:
            List[Dict[str, Any]]: Filtered option data
        """
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
        Get list of available expiry dates.
        
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
        """
        Get list of available strike prices.
        
        Args:
            expiry (str, optional): Filter by specific expiry
        
        Returns:
            List[int]: List of strike prices
        """
        try:
            # Fetch data with optional expiry filter
            data = self.fetch(expiry=expiry)
            
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
        """
        Get summary statistics for option chain.
        
        Args:
            expiry (str, optional): Filter by specific expiry
        
        Returns:
            Dict[str, Any]: Summary statistics
        """
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
        """
        Set cache duration in seconds.
        
        Args:
            duration_seconds (int): Cache duration in seconds
        """
        self._cache_duration = duration_seconds
        logger.debug(f"Cache duration set to {duration_seconds} seconds")


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    print("UpstoxOptionChain Example Usage")
    print("=" * 50)
    
    # Note: You need to provide a valid access token
    load_dotenv("keys.env")
    access_token = os.getenv("UPSTOX_ACCESS_TOKEN")
    
    try:
        # Initialize the option chain fetcher
        option_chain = UpstoxOptionChain(access_token)
        
        # Get next weekly expiry using Utils
        print("Fetching next weekly expiry...")
        expiries = Utils.get_next_weekly_expiry()
        print(f"Next weekly expiry: {expiries}")
        
        next_expiry = expiries[0]
        # Get strike prices for next expiry
        if next_expiry:
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
        
        # Get summary for next expiry
        print(f"\nOption chain summary for {next_expiry}:")
        summary = option_chain.get_option_summary(expiry=next_expiry)
        for key, value in summary.items():
            print(f"  {key}: {value}")
        
        # Demonstrate fetching all expiries
        print("\nFetching data for all expiries...")
        all_options = option_chain.fetch_all_expiries()
        print(f"Found {len(all_options)} total option contracts across all expiries")
            
    except Exception as e:
        print(f"Error: {e}")
        print("Note: Make sure to provide a valid Upstox access token")
