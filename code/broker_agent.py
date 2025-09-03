import logging
import threading
from abc import ABC, abstractmethod

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

        
        
