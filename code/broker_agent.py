import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

class BrokerAgent(ABC):
    def __init__(self):
        self.broker = None
        # Live data streaming properties
        self.subscribed_instruments = set()
        self.live_data_callbacks = []
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def login(self):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def logout(self):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def place_order(self):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def fetch_orders(self):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def fetch_instruments(self):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def fetch_positions(self):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def fetch_quotes(self):
        raise NotImplementedError("Subclasses must implement this method")

    # Live data streaming methods
    @abstractmethod
    def connect_live_data(self):
        """Establish connection for live market data streaming"""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def subscribe_live_data(self, instrument_keys, mode="ltpc"):
        """Subscribe to live data for specific instruments"""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def unsubscribe_live_data(self, instrument_keys):
        """Unsubscribe from live data for specific instruments"""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def disconnect_live_data(self):
        """Disconnect from live data feed"""
        raise NotImplementedError("Subclasses must implement this method")

    def add_live_data_callback(self, callback):
        """
        Add a callback function to handle live data updates
        
        Args:
            callback (function): Function to call when live data is received
        """
        self.live_data_callbacks.append(callback)
        self.logger.info("Live data callback added")

    def remove_live_data_callback(self, callback):
        """
        Remove a callback function from live data updates
        
        Args:
            callback (function): Function to remove from callbacks
        """
        if callback in self.live_data_callbacks:
            self.live_data_callbacks.remove(callback)
            self.logger.info("Live data callback removed")

    def get_live_data_status(self):
        """Get the current status of live data connection"""
        return {
            "is_connected": self.is_connected,
            "subscribed_instruments": list(self.subscribed_instruments),
            "callback_count": len(self.live_data_callbacks),
            "reconnect_attempts": self.reconnect_attempts
        }

    # OHLC Data methods
    @abstractmethod
    def get_ohlc_intraday_data(self, instrument: str, interval: str = "1minute", 
                              start_time: Optional[datetime] = None, 
                              end_time: Optional[datetime] = None) -> List[Dict]:
        """
        Get intraday OHLC data from broker
        
        Args:
            instrument (str): Instrument identifier
            interval (str): Data interval (e.g., "1minute", "5minute")
            start_time (datetime, optional): Start time for data
            end_time (datetime, optional): End time for data
            
        Returns:
            List[Dict]: List of OHLC data dictionaries
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def get_ohlc_historical_data(self, instrument: str, interval: str = "day", 
                                start_time: Optional[datetime] = None, 
                                end_time: Optional[datetime] = None) -> List[Dict]:
        """
        Get historical OHLC data from broker
        
        Args:
            instrument (str): Instrument identifier
            interval (str): Data interval (e.g., "day", "week", "month")
            start_time (datetime, optional): Start time for data
            end_time (datetime, optional): End time for data
            
        Returns:
            List[Dict]: List of OHLC data dictionaries
        """
        raise NotImplementedError("Subclasses must implement this method")

    def consolidate_1min_to_5min(self, instrument: str, one_min_data: List[Dict]) -> List[Dict]:
        """
        Consolidate 1-minute OHLC data into 5-minute buckets
        
        Args:
            instrument (str): Instrument identifier
            one_min_data (List[Dict]): List of 1-minute OHLC data
            
        Returns:
            List[Dict]: Consolidated 5-minute OHLC data
        """
        from datawarehouse import datawarehouse
        return datawarehouse.consolidate_1min_to_5min(instrument, one_min_data)

    def store_ohlc_data(self, instrument: str, ohlc_data: List[Dict], 
                       data_type: str = "intraday", interval_minutes: int = 5):
        """
        Store OHLC data in the data warehouse
        
        Args:
            instrument (str): Instrument identifier
            ohlc_data (List[Dict]): List of OHLC data
            data_type (str): "intraday" or "historical"
            interval_minutes (int): Data interval in minutes
        """
        from datawarehouse import datawarehouse
        
        if data_type == "intraday":
            datawarehouse.store_intraday_data(instrument, ohlc_data, interval_minutes)
        elif data_type == "historical":
            # Historical data is no longer stored - it should be fetched fresh each time
            self.logger.info(f"Historical data not stored - will be fetched fresh when needed")
        else:
            self.logger.error(f"Invalid data_type: {data_type}. Must be 'intraday' or 'historical'")

    def get_stored_ohlc_data(self, instrument: str, data_type: str = "intraday",
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None,
                            limit: Optional[int] = None) -> pd.DataFrame:
        """
        Get stored OHLC data from the data warehouse
        
        Args:
            instrument (str): Instrument identifier
            data_type (str): "intraday" or "historical"
            start_time (datetime, optional): Start time filter
            end_time (datetime, optional): End time filter
            limit (int, optional): Maximum number of records
            
        Returns:
            pd.DataFrame: Stored OHLC data
        """
        from datawarehouse import datawarehouse
        
        if data_type == "intraday":
            return datawarehouse.get_intraday_data(instrument, start_time, end_time, limit)
        elif data_type == "historical":
            # Historical data is no longer stored - return empty DataFrame
            self.logger.info(f"Historical data not available from storage - must be fetched fresh")
            return pd.DataFrame()
        else:
            self.logger.error(f"Invalid data_type: {data_type}. Must be 'intraday' or 'historical'")
            return pd.DataFrame()

    def get_latest_price(self, instrument: str) -> Optional[float]:
        """
        Get the latest price for an instrument from stored data
        
        Args:
            instrument (str): Instrument identifier
            
        Returns:
            float: Latest close price, or None if not available
        """
        from datawarehouse import datawarehouse
        return datawarehouse.get_latest_price(instrument)

    def get_price_range(self, instrument: str, period_hours: int = 24) -> tuple:
        """
        Get price range (min, max) for an instrument over a specified period
        
        Args:
            instrument (str): Instrument identifier
            period_hours (int): Period in hours to look back
            
        Returns:
            Tuple[float, float]: (min_price, max_price) or (None, None) if no data
        """
        from datawarehouse import datawarehouse
        return datawarehouse.get_price_range(instrument, period_hours)

        
        
