import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import threading
import json
import os

class DataWarehouse:
    """
    Data warehouse class to manage OHLC data storage for both historical and intraday data.
    Maintains 5-minute OHLC data buckets and provides consolidation from 1-minute data.
    """
    
    def __init__(self, data_directory: str = "data"):
        self.data_directory = data_directory
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_directory, exist_ok=True)
        
        # Thread lock for data operations
        self.lock = threading.Lock()
        
        # In-memory storage for different data sources
        self.historical_data: Dict[str, pd.DataFrame] = {}  # Historical API data
        self.intraday_data: Dict[str, pd.DataFrame] = {}    # Intraday API data
        self.live_feed_data: Dict[str, pd.DataFrame] = {}   # Live feed data
        
        # Latest price storage for P&L calculations (from all sources)
        self.latest_prices: Dict[str, Dict] = {}  # {instrument: {price, timestamp, volume, source}}
        
        # Technical indicators storage
        self.technical_indicators: Dict[str, Dict] = {}  # {instrument: {indicator_name: values}}
        
        # Configuration
        self.default_interval_minutes = 5
        self.max_candles_in_memory = 1000  # Keep last 1000 candles in memory
        
        self.logger.info(f"DataWarehouse initialized with data directory: {self.data_directory}")
    
    def _get_data_file_path(self, instrument: str, data_type: str) -> str:
        """Get file path for storing data"""
        safe_instrument = instrument.replace("|", "_").replace(" ", "_").replace(":", "_")
        return os.path.join(self.data_directory, f"{safe_instrument}_{data_type}.csv")
    
    def _load_data_from_file(self, instrument: str, data_type: str) -> pd.DataFrame:
        """Load data from CSV file"""
        file_path = self._get_data_file_path(instrument, data_type)
        
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                self.logger.debug(f"Loaded {len(df)} records for {instrument} {data_type}")
                return df
            except Exception as e:
                self.logger.error(f"Error loading data from {file_path}: {e}")
                return pd.DataFrame()
        else:
            self.logger.debug(f"No data file found for {instrument} {data_type}")
            return pd.DataFrame()
    
    def _save_data_to_file(self, instrument: str, data_type: str, df: pd.DataFrame):
        """Save data to CSV file"""
        file_path = self._get_data_file_path(instrument, data_type)
        
        try:
            df.to_csv(file_path)
            self.logger.debug(f"Saved {len(df)} records for {instrument} {data_type}")
        except Exception as e:
            self.logger.error(f"Error saving data to {file_path}: {e}")
    
    def _round_to_interval(self, timestamp: datetime, interval_minutes: int) -> datetime:
        """Round timestamp to the nearest interval boundary"""
        # Round down to the nearest interval
        minutes = (timestamp.minute // interval_minutes) * interval_minutes
        return timestamp.replace(minute=minutes, second=0, microsecond=0)
    
    def store_historical_data(self, instrument: str, ohlc_data: List[Dict]):
        """
        Store historical OHLC data
        
        Args:
            instrument (str): Instrument identifier
            ohlc_data (List[Dict]): List of OHLC data
        """
        with self.lock:
            try:
                # Convert to DataFrame
                df = pd.DataFrame(ohlc_data)
                if df.empty:
                    return
                
                # Set timestamp as index
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Store historical data separately (don't combine with existing)
                combined_df = df
                
                # Keep only recent data in memory
                if len(combined_df) > self.max_candles_in_memory:
                    combined_df = combined_df.tail(self.max_candles_in_memory)
                
                # Store in memory and file
                self.historical_data[instrument] = combined_df
                self._save_data_to_file(instrument, 'historical', combined_df)
                
                self.logger.info(f"Stored {len(df)} historical candles for {instrument}")
                
            except Exception as e:
                self.logger.error(f"Error storing historical data for {instrument}: {e}")

    def store_intraday_data(self, instrument: str, ohlc_data: List[Dict], interval_minutes: int = 5):
        """
        Store intraday OHLC data
        
        Args:
            instrument (str): Instrument identifier
            ohlc_data (List[Dict]): List of OHLC data
            interval_minutes (int): Data interval in minutes
        """
        with self.lock:
            try:
                # Convert to DataFrame
                df = pd.DataFrame(ohlc_data)
                if df.empty:
                    return
                
                # Set timestamp as index
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Store intraday data separately (don't combine with existing)
                combined_df = df
                
                # Keep only recent data in memory
                if len(combined_df) > self.max_candles_in_memory:
                    combined_df = combined_df.tail(self.max_candles_in_memory)
                
                # Store in memory and file
                self.intraday_data[instrument] = combined_df
                self._save_data_to_file(instrument, 'intraday', combined_df)
                
                self.logger.info(f"Stored {len(df)} intraday candles for {instrument}")
                
            except Exception as e:
                self.logger.error(f"Error storing intraday data for {instrument}: {e}")

    def store_live_feed_data(self, instrument: str, ohlc_data: List[Dict]):
        """
        Store live feed OHLC data
        
        Args:
            instrument (str): Instrument identifier
            ohlc_data (List[Dict]): List of OHLC data
        """
        with self.lock:
            try:
                # Convert to DataFrame
                df = pd.DataFrame(ohlc_data)
                if df.empty:
                    return
                
                # Set timestamp as index
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Store live feed data separately (don't combine with existing)
                combined_df = df
                
                # Keep only recent data in memory
                if len(combined_df) > self.max_candles_in_memory:
                    combined_df = combined_df.tail(self.max_candles_in_memory)
                
                # Store in memory and file
                self.live_feed_data[instrument] = combined_df
                self._save_data_to_file(instrument, 'live_feed', combined_df)
                
                self.logger.info(f"Stored {len(df)} live feed candles for {instrument}")
                
            except Exception as e:
                self.logger.error(f"Error storing live feed data for {instrument}: {e}")
    
    
    def get_intraday_data(self, instrument: str, start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get intraday OHLC data
        
        Args:
            instrument (str): Instrument identifier
            start_time (datetime, optional): Start time filter
            end_time (datetime, optional): End time filter
            limit (int, optional): Maximum number of records to return
            
        Returns:
            pd.DataFrame: Intraday OHLC data
        """
        with self.lock:
            try:
                # Load from memory first, then file if needed
                if instrument in self.intraday_data:
                    df = self.intraday_data[instrument].copy()
                else:
                    df = self._load_data_from_file(instrument, 'intraday')
                    if not df.empty:
                        self.intraday_data[instrument] = df
                
                if df.empty:
                    return df
                
                # Apply filters
                if start_time:
                    df = df[df.index >= start_time]
                if end_time:
                    df = df[df.index <= end_time]
                
                # Apply limit
                if limit:
                    df = df.tail(limit)
                
                return df
                
            except Exception as e:
                self.logger.error(f"Error getting intraday data for {instrument}: {e}")
                return pd.DataFrame()

    def get_historical_data(self, instrument: str, start_time: Optional[datetime] = None, 
                           end_time: Optional[datetime] = None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get historical OHLC data
        
        Args:
            instrument (str): Instrument identifier
            start_time (datetime, optional): Start time filter
            end_time (datetime, optional): End time filter
            limit (int, optional): Maximum number of records to return
            
        Returns:
            pd.DataFrame: Historical OHLC data
        """
        with self.lock:
            try:
                # Load from memory first, then file if needed
                if instrument in self.historical_data:
                    df = self.historical_data[instrument].copy()
                else:
                    df = self._load_data_from_file(instrument, 'historical')
                    if not df.empty:
                        self.historical_data[instrument] = df
                
                if df.empty:
                    return df
                
                # Apply filters
                if start_time:
                    df = df[df.index >= start_time]
                if end_time:
                    df = df[df.index <= end_time]
                
                # Apply limit
                if limit:
                    df = df.tail(limit)
                
                return df
                
            except Exception as e:
                self.logger.error(f"Error getting historical data for {instrument}: {e}")
                return pd.DataFrame()

    def get_live_feed_data(self, instrument: str, start_time: Optional[datetime] = None, 
                          end_time: Optional[datetime] = None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get live feed OHLC data
        
        Args:
            instrument (str): Instrument identifier
            start_time (datetime, optional): Start time filter
            end_time (datetime, optional): End time filter
            limit (int, optional): Maximum number of records to return
            
        Returns:
            pd.DataFrame: Live feed OHLC data
        """
        with self.lock:
            try:
                # Load from memory first, then file if needed
                if instrument in self.live_feed_data:
                    df = self.live_feed_data[instrument].copy()
                else:
                    df = self._load_data_from_file(instrument, 'live_feed')
                    if not df.empty:
                        self.live_feed_data[instrument] = df
                
                if df.empty:
                    return df
                
                # Apply filters
                if start_time:
                    df = df[df.index >= start_time]
                if end_time:
                    df = df[df.index <= end_time]
                
                # Apply limit
                if limit:
                    df = df.tail(limit)
                
                return df
                
            except Exception as e:
                self.logger.error(f"Error getting live feed data for {instrument}: {e}")
                return pd.DataFrame()
    
    
    def get_latest_price(self, instrument: str) -> Optional[float]:
        """
        Get the latest price for an instrument with priority order:
        1. Live Feed data
        2. Intraday data  
        3. Historical data
        
        Args:
            instrument (str): Instrument identifier
            
        Returns:
            float: Latest close price, or None if not available
        """
        try:
            # Define priority order (lower number = higher priority)
            priority_order = {
                'live_feed': 1,
                'intraday': 2, 
                'historical': 3,
                'unknown': 4
            }
            
            # Collect all available prices with their sources
            available_prices = []
            
            # Check latest_prices (most recent data from any source)
            if instrument in self.latest_prices:
                price_data = self.latest_prices[instrument]
                source = price_data.get('source', 'unknown')
                price = float(price_data['price'])
                available_prices.append((price, source, 'latest_prices'))
            
            # Check live feed data
            if instrument in self.live_feed_data and not self.live_feed_data[instrument].empty:
                latest_candle = self.live_feed_data[instrument].iloc[0]
                price = float(latest_candle['close'])
                available_prices.append((price, 'live_feed', 'live_feed_data'))
            
            # Check intraday data
            if instrument in self.intraday_data and not self.intraday_data[instrument].empty:
                latest_candle = self.intraday_data[instrument].iloc[0]
                price = float(latest_candle['close'])
                available_prices.append((price, 'intraday', 'intraday_data'))
            
            # Check historical data
            if instrument in self.historical_data and not self.historical_data[instrument].empty:
                latest_candle = self.historical_data[instrument].iloc[0]
                price = float(latest_candle['close'])
                available_prices.append((price, 'historical', 'historical_data'))
            
            if not available_prices:
                self.logger.warning(f"No price available for {instrument} from any source")
                return None
            
            # Sort by priority (lower priority number = higher priority)
            available_prices.sort(key=lambda x: priority_order.get(x[1], 999))
            
            # Return the highest priority price
            selected_price, selected_source, selected_location = available_prices[0]
            self.logger.debug(f"Selected price {selected_price} from {selected_source} ({selected_location})")
            
            return selected_price
            
        except Exception as e:
            self.logger.error(f"Error getting latest price for {instrument}: {e}")
            return None
    
    def store_latest_price(self, instrument: str, price: float, volume: float = 0.0, source: str = 'unknown') -> None:
        """
        Store the latest price for an instrument (for P&L calculations)
        Only stores if the new source has higher or equal priority than existing data
        
        Args:
            instrument (str): Instrument identifier
            price (float): Latest price
            volume (float): Latest volume (optional)
            source (str): Data source ('historical', 'intraday', 'live_feed')
        """
        try:
            with self.lock:
                # Define priority order (lower number = higher priority)
                priority_order = {
                    'live_feed': 1,
                    'intraday': 2, 
                    'historical': 3,
                    'unknown': 4
                }
                
                # Check if we should store this price based on priority
                should_store = True
                if instrument in self.latest_prices:
                    existing_source = self.latest_prices[instrument].get('source', 'unknown')
                    existing_priority = priority_order.get(existing_source, 999)
                    new_priority = priority_order.get(source, 999)
                    
                    if new_priority > existing_priority:
                        # New source has lower priority, don't overwrite
                        should_store = False
                        self.logger.debug(f"Skipping {source} price {price} for {instrument} - existing {existing_source} has higher priority")
                    elif new_priority == existing_priority:
                        # Same priority, update with newer data
                        should_store = True
                        self.logger.debug(f"Updating {source} price for {instrument} from {self.latest_prices[instrument]['price']} to {price}")
                    else:
                        # New source has higher priority, overwrite
                        should_store = True
                        self.logger.debug(f"Overwriting {existing_source} price with higher priority {source} price for {instrument}")
                
                if should_store:
                    self.latest_prices[instrument] = {
                        'price': price,
                        'volume': volume,
                        'timestamp': datetime.now(),
                        'source': source
                    }
                    self.logger.debug(f"Stored latest price for {instrument}: {price} (source: {source})")
                
        except Exception as e:
            self.logger.error(f"Error storing latest price for {instrument}: {e}")
    
    def store_latest_close_price(self, instrument: str, close_price: float) -> None:
        """
        Store the latest close price from daily historical data
        
        Args:
            instrument (str): Instrument identifier
            close_price (float): Latest close price from daily data
        """
        try:
            with self.lock:
                if not hasattr(self, 'latest_close_prices'):
                    self.latest_close_prices = {}
                
                self.latest_close_prices[instrument] = {
                    'close_price': close_price,
                    'timestamp': datetime.now()
                }
                self.logger.debug(f"Stored latest close price for {instrument}: {close_price}")
                
        except Exception as e:
            self.logger.error(f"Error storing latest close price for {instrument}: {e}")
    
    def get_latest_close_price(self, instrument: str) -> Optional[float]:
        """
        Get the latest close price from daily historical data
        
        Args:
            instrument (str): Instrument identifier
            
        Returns:
            float: Latest close price, or None if not available
        """
        try:
            with self.lock:
                if hasattr(self, 'latest_close_prices') and instrument in self.latest_close_prices:
                    return self.latest_close_prices[instrument]['close_price']
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting latest close price for {instrument}: {e}")
            return None
    
    def store_technical_indicators(self, instrument: str, indicators: Dict[str, List[Optional[float]]]) -> None:
        """
        Store technical indicators for an instrument
        
        Args:
            instrument (str): Instrument identifier
            indicators (Dict): Dictionary of indicator names and their values
        """
        try:
            with self.lock:
                self.technical_indicators[instrument] = indicators
                self.logger.info(f"Stored technical indicators for {instrument}: {list(indicators.keys())}")
                
        except Exception as e:
            self.logger.error(f"Error storing technical indicators for {instrument}: {e}")
    
    def get_technical_indicators(self, instrument: str) -> Dict[str, List[Optional[float]]]:
        """
        Get technical indicators for an instrument
        
        Args:
            instrument (str): Instrument identifier
            
        Returns:
            Dict: Dictionary of indicator names and their values
        """
        try:
            with self.lock:
                return self.technical_indicators.get(instrument, {})
                
        except Exception as e:
            self.logger.error(f"Error getting technical indicators for {instrument}: {e}")
            return {}
    
    def get_latest_price_data(self, instrument: str) -> Optional[Dict]:
        """
        Get the latest price data for an instrument
        
        Args:
            instrument (str): Instrument identifier
            
        Returns:
            Dict: {price, volume, timestamp} or None if not available
        """
        try:
            with self.lock:
                return self.latest_prices.get(instrument)
                
        except Exception as e:
            self.logger.error(f"Error getting latest price data for {instrument}: {e}")
            return None
    
    def get_price_range(self, instrument: str, period_hours: int = 24) -> Tuple[Optional[float], Optional[float]]:
        """
        Get price range (min, max) for an instrument over a specified period
        
        Args:
            instrument (str): Instrument identifier
            period_hours (int): Period in hours to look back
            
        Returns:
            Tuple[float, float]: (min_price, max_price) or (None, None) if no data
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=period_hours)
            
            # Get data for the period
            df = self.get_intraday_data(instrument, start_time, end_time)
            
            if df.empty:
                return None, None
            
            min_price = float(df['low'].min())
            max_price = float(df['high'].max())
            
            return min_price, max_price
            
        except Exception as e:
            self.logger.error(f"Error getting price range for {instrument}: {e}")
            return None, None
    
    def clear_data(self, instrument: str = None, data_type: str = None):
        """
        Clear data for an instrument or all data
        
        Args:
            instrument (str, optional): Instrument to clear. If None, clears all.
            data_type (str, optional): 'intraday', 'historical', 'live_feed', or None for all.
        """
        with self.lock:
            try:
                if instrument is None:
                    # Clear all data
                    self.historical_data.clear()
                    self.intraday_data.clear()
                    self.live_feed_data.clear()
                    self.latest_prices.clear()
                    self.logger.info("Cleared all data")
                else:
                    # Clear specific instrument
                    if data_type is None or data_type == 'intraday':
                        if instrument in self.intraday_data:
                            del self.intraday_data[instrument]
                        file_path = self._get_data_file_path(instrument, 'intraday')
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    self.logger.info(f"Cleared {data_type or 'all'} data for {instrument}")
                    
            except Exception as e:
                self.logger.error(f"Error clearing data: {e}")
    
    def get_data_summary(self) -> Dict:
        """
        Get summary of stored data
        
        Returns:
            Dict: Summary of data warehouse contents
        """
        summary = {
            'historical_instruments': list(self.historical_data.keys()),
            'total_historical_candles': sum(len(df) for df in self.historical_data.values()),
            'intraday_instruments': list(self.intraday_data.keys()),
            'total_intraday_candles': sum(len(df) for df in self.intraday_data.values()),
            'live_feed_instruments': list(self.live_feed_data.keys()),
            'total_live_feed_candles': sum(len(df) for df in self.live_feed_data.values()),
            'latest_prices': len(self.latest_prices)
        }
        
        return summary
    
    def fetch_option_chain_data(self, instrument_key: str, expiry_date: str, access_token: str = None) -> Dict[str, Any]:
        # Import here to avoid circular imports
        from upstox_option_chain import UpstoxOptionChain
        
        # Get access token from environment if not provided
        if access_token is None:
            from dotenv import load_dotenv
            load_dotenv()
            access_token = os.getenv('UPSTOX_ACCESS_TOKEN')
            
        if not access_token:
            return None
        # Create option chain instance
        option_chain = UpstoxOptionChain(access_token=access_token)
        
        # Fetch option chain data
        self.logger.info(f"Fetching option chain data for {instrument_key} with expiry {expiry_date}")
        option_data = option_chain.fetch(expiry=expiry_date)
        return option_data
            



# Global data warehouse instance
datawarehouse = DataWarehouse()
