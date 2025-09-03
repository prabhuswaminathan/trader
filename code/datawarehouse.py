import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
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
        
        # In-memory storage for active data
        self.intraday_data: Dict[str, pd.DataFrame] = {}
        self.historical_data: Dict[str, pd.DataFrame] = {}
        
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
    
    def consolidate_1min_to_5min(self, instrument: str, one_min_data: List[Dict]) -> List[Dict]:
        """
        Consolidate 1-minute OHLC data into 5-minute buckets
        
        Args:
            instrument (str): Instrument identifier
            one_min_data (List[Dict]): List of 1-minute OHLC data
            
        Returns:
            List[Dict]: Consolidated 5-minute OHLC data
        """
        if not one_min_data:
            return []
        
        # Group data by 5-minute intervals
        buckets = {}
        
        for candle in one_min_data:
            # Parse timestamp
            if isinstance(candle.get('timestamp'), str):
                timestamp = pd.to_datetime(candle['timestamp'])
            else:
                timestamp = candle.get('timestamp', datetime.now())
            
            # Round to 5-minute boundary
            bucket_time = self._round_to_interval(timestamp, 5)
            
            if bucket_time not in buckets:
                buckets[bucket_time] = []
            
            buckets[bucket_time].append(candle)
        
        # Consolidate each bucket
        consolidated_data = []
        
        for bucket_time, candles in buckets.items():
            if not candles:
                continue
            
            # Sort candles by timestamp within the bucket
            candles.sort(key=lambda x: x.get('timestamp', datetime.now()))
            
            # Extract OHLCV values
            opens = [float(c.get('open', 0)) for c in candles if c.get('open') is not None]
            highs = [float(c.get('high', 0)) for c in candles if c.get('high') is not None]
            lows = [float(c.get('low', 0)) for c in candles if c.get('low') is not None]
            closes = [float(c.get('close', 0)) for c in candles if c.get('close') is not None]
            volumes = [float(c.get('volume', 0)) for c in candles if c.get('volume') is not None]
            
            if not opens or not highs or not lows or not closes:
                continue
            
            # Create consolidated candle
            consolidated_candle = {
                'timestamp': bucket_time,
                'open': opens[0],  # First open in the bucket
                'high': max(highs),  # Highest high in the bucket
                'low': min(lows),    # Lowest low in the bucket
                'close': closes[-1], # Last close in the bucket
                'volume': sum(volumes) if volumes else 0  # Sum of volumes
            }
            
            consolidated_data.append(consolidated_candle)
        
        # Sort by timestamp
        consolidated_data.sort(key=lambda x: x['timestamp'])
        
        self.logger.debug(f"Consolidated {len(one_min_data)} 1-min candles into {len(consolidated_data)} 5-min candles for {instrument}")
        
        return consolidated_data
    
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
                
                # Load existing data
                existing_df = self._load_data_from_file(instrument, 'intraday')
                
                if not existing_df.empty:
                    # Combine with existing data
                    combined_df = pd.concat([existing_df, df])
                    # Remove duplicates and sort
                    combined_df = combined_df[~combined_df.index.duplicated(keep='last')].sort_index()
                else:
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
                
                # Load existing data
                existing_df = self._load_data_from_file(instrument, 'historical')
                
                if not existing_df.empty:
                    # Combine with existing data
                    combined_df = pd.concat([existing_df, df])
                    # Remove duplicates and sort
                    combined_df = combined_df[~combined_df.index.duplicated(keep='last')].sort_index()
                else:
                    combined_df = df
                
                # Store in memory and file
                self.historical_data[instrument] = combined_df
                self._save_data_to_file(instrument, 'historical', combined_df)
                
                self.logger.info(f"Stored {len(df)} historical candles for {instrument}")
                
            except Exception as e:
                self.logger.error(f"Error storing historical data for {instrument}: {e}")
    
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
    
    def get_latest_price(self, instrument: str) -> Optional[float]:
        """
        Get the latest price for an instrument
        
        Args:
            instrument (str): Instrument identifier
            
        Returns:
            float: Latest close price, or None if not available
        """
        try:
            # Try intraday data first
            intraday_df = self.get_intraday_data(instrument, limit=1)
            if not intraday_df.empty:
                return float(intraday_df['close'].iloc[-1])
            
            # Fallback to historical data
            historical_df = self.get_historical_data(instrument, limit=1)
            if not historical_df.empty:
                return float(historical_df['close'].iloc[-1])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting latest price for {instrument}: {e}")
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
            data_type (str, optional): 'intraday', 'historical', or None for both.
        """
        with self.lock:
            try:
                if instrument is None:
                    # Clear all data
                    self.intraday_data.clear()
                    self.historical_data.clear()
                    self.logger.info("Cleared all data")
                else:
                    # Clear specific instrument
                    if data_type is None or data_type == 'intraday':
                        if instrument in self.intraday_data:
                            del self.intraday_data[instrument]
                        file_path = self._get_data_file_path(instrument, 'intraday')
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    if data_type is None or data_type == 'historical':
                        if instrument in self.historical_data:
                            del self.historical_data[instrument]
                        file_path = self._get_data_file_path(instrument, 'historical')
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
            'intraday_instruments': list(self.intraday_data.keys()),
            'historical_instruments': list(self.historical_data.keys()),
            'total_intraday_candles': sum(len(df) for df in self.intraday_data.values()),
            'total_historical_candles': sum(len(df) for df in self.historical_data.values())
        }
        
        return summary


# Global data warehouse instance
datawarehouse = DataWarehouse()
