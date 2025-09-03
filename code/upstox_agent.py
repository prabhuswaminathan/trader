from math import log
import os
import json
import logging
import requests
import threading
import time
import uuid
import upstox_client
from dotenv import load_dotenv
from broker_agent import BrokerAgent
from auth_handler import AuthHandler
from upstox_client.rest import ApiException

auth_event = threading.Event()
logging.basicConfig(level= logging.DEBUG)
logger = logging.getLogger("UpstoxAgent")

api_version = "2.0"

class UpstoxAgent(BrokerAgent):
    CLIENT_ID = "6RBXY3"
    REDIRECT_URI = "http://localhost:3030/callback"

    API_KEY = None
    API_SECRET = None

    ACCESS_TOKEN = None

    def __init__(self):
        super().__init__()
        self.broker = None
        load_dotenv("keys.env")
        self.API_KEY = os.getenv("UPSTOX_API_KEY")
        self.API_SECRET = os.getenv("UPSTOX_API_SECRET")
        self.ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN")
        self.configuration = upstox_client.Configuration()
        self.configuration.access_token = self.ACCESS_TOKEN
        
        # Live data streaming properties
        self.streamer = None
        self.subscribed_instruments = set()
        self.live_data_callbacks = []
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds

    def get_access_token(self, code):
        try:
            self.auth_code = code
            logger.debug("#################get_token called########################")
            url = 'https://api.upstox.com/v2/login/authorization/token'
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            }

            data = {
                'code': self.auth_code,
                'client_id': self.API_KEY,
                'client_secret': self.API_SECRET,
                'redirect_uri': self.REDIRECT_URI,
                'grant_type': 'authorization_code',
            }

            response = requests.post(url, headers=headers, data=data)

            logger.info(response.status_code)
            user_info = response.json()
            self.ACCESS_TOKEN = user_info['access_token']
            logger.debug(f"##############################{self.ACCESS_TOKEN}")  
            self.get_order_details()
        except Exception as e:
            logger.error(e)

    def fetch_orders(self):
        logger.debug("==================get order details================")
        try:
            # Get order book
            api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration=self.configuration))
            api_version = api_version # str | API Version Header
            api_response = self.api_instance.get_order_book(self.api_version)
            logger.info(api_response)
        except ApiException as e:
            print("Exception when calling OrderApi->get_order_book: %s\n" % e)        

    def login(self):
        logger.debug(f"==========================>Initiating Login")
        url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={self.API_KEY}&redirect_uri={self.REDIRECT_URI}"
        auth_handler = AuthHandler()
        auth_handler.get_auth_code(url, self.get_access_token)


    def logout(self):
        self.broker.logout()

    def place_order(self):
        self.broker.place_order()

    def fetch_instruments(self):
        self.broker.fetch_instruments()

    def fetch_positions(self):
        self.broker.fetch_positions()

    def fetch_quotes(self, symbol = "NSE_INDEX|Nifty 50", interval = "I1"):
        try:
            # Market quotes and instruments - OHLC quotes
            api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration=self.configuration))
            api_response = api_instance.get_market_quote_ohlc(symbol, interval, api_version)
            logger.info(api_response)
        except ApiException as e:
            print("Exception when calling MarketQuoteApi->get_market_quote_ohlc: %s\n" % e)

    def connect_live_data(self):
        """Establish WebSocket connection for live market data streaming"""
        try:
            # Create API client
            api_client = upstox_client.ApiClient(configuration=self.configuration)
            
            # Initialize the MarketDataStreamerV3 with empty instrument list initially
            self.streamer = upstox_client.MarketDataStreamerV3(
                api_client,
                instrumentKeys=[],  # Start with empty list, will subscribe later
                mode="ltpc"
            )
            
            # Set up message handler
            self.streamer.on("message", self._on_streamer_message)
            
            # Connect to the WebSocket
            self.streamer.connect()
            
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("Connected to Upstox Market Data Streamer V3")
            
            return True
                
        except Exception as e:
            logger.error(f"Error connecting to live data feed: {e}")
            return False

    def _on_streamer_message(self, message):
        """Handle incoming messages from MarketDataStreamerV3"""
        try:
            # Log the received message
            logger.debug(f"Received live data message: {message}")
            
            # Call registered callbacks
            for callback in self.live_data_callbacks:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in live data callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing live data message: {e}")

    def subscribe_live_data(self, instrument_keys, mode="ltpc"):
        """
        Subscribe to live data for specific instruments
        
        Args:
            instrument_keys (list): List of instrument keys (e.g., ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"])
            mode (str): Data mode - "ltpc", "option_greeks", "full", or "full_d30"
        """
        if not self.is_connected:
            logger.warning("Streamer not connected. Attempting to connect...")
            if not self.connect_live_data():
                logger.error("Failed to establish streamer connection")
                return False

        try:
            # Add to subscribed instruments
            self.subscribed_instruments.update(instrument_keys)
            
            # Create new streamer with updated instrument list
            api_client = upstox_client.ApiClient(configuration=self.configuration)
            self.streamer = upstox_client.MarketDataStreamerV3(
                api_client,
                instrumentKeys=list(self.subscribed_instruments),
                mode=mode
            )
            
            # Set up message handler
            self.streamer.on("message", self._on_streamer_message)
            
            # Connect to the WebSocket
            self.streamer.connect()
            
            logger.info(f"Subscribed to live data for: {instrument_keys} in mode: {mode}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to live data: {e}")
            return False

    def unsubscribe_live_data(self, instrument_keys):
        """
        Unsubscribe from live data for specific instruments
        
        Args:
            instrument_keys (list): List of instrument keys to unsubscribe from
        """
        if not self.is_connected:
            logger.warning("Streamer not connected")
            return False

        try:
            # Remove from subscribed instruments
            self.subscribed_instruments.difference_update(instrument_keys)
            
            if self.subscribed_instruments:
                # Create new streamer with updated instrument list
                api_client = upstox_client.ApiClient(configuration=self.configuration)
                self.streamer = upstox_client.MarketDataStreamerV3(
                    api_client,
                    instrumentKeys=list(self.subscribed_instruments),
                    mode="ltpc"  # Default mode
                )
                
                # Set up message handler
                self.streamer.on("message", self._on_streamer_message)
                
                # Connect to the WebSocket
                self.streamer.connect()
            else:
                # No instruments left, disconnect
                self.disconnect_live_data()
            
            logger.info(f"Unsubscribed from live data for: {instrument_keys}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing from live data: {e}")
            return False

    def _resubscribe_instruments(self):
        """Resubscribe to all previously subscribed instruments after reconnection"""
        if self.subscribed_instruments:
            logger.info("Resubscribing to previously subscribed instruments...")
            self.subscribe_live_data(list(self.subscribed_instruments))

    def add_live_data_callback(self, callback):
        """
        Add a callback function to handle live data updates
        
        Args:
            callback (function): Function to call when live data is received
        """
        self.live_data_callbacks.append(callback)
        logger.info("Live data callback added")

    def remove_live_data_callback(self, callback):
        """
        Remove a callback function from live data updates
        
        Args:
            callback (function): Function to remove from callbacks
        """
        if callback in self.live_data_callbacks:
            self.live_data_callbacks.remove(callback)
            logger.info("Live data callback removed")

    def disconnect_live_data(self):
        """Disconnect from live data feed"""
        if hasattr(self, 'streamer') and self.streamer:
            try:
                self.streamer.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting streamer: {e}")
        self.is_connected = False
        logger.info("Disconnected from live data feed")

    def get_live_data_status(self):
        """Get the current status of live data connection"""
        return {
            "is_connected": self.is_connected,
            "subscribed_instruments": list(self.subscribed_instruments),
            "callback_count": len(self.live_data_callbacks),
            "reconnect_attempts": self.reconnect_attempts
        }


if __name__ == "__main__":    
    agent = UpstoxAgent()
    
    # Example callback function to handle live data
    def handle_live_data(message):
        print(f"Live data received: {message}")
        # Here you would parse the Protobuf message and extract relevant data
    
    # Add the callback
    agent.add_live_data_callback(handle_live_data)
    
    # Connect to live data feed
    if agent.connect_live_data():
        print("Connected to live data feed")
        
        # Subscribe to Nifty 50 and Nifty Bank live data
        instruments = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"]
        if agent.subscribe_live_data(instruments, mode="ltpc"):
            print(f"Subscribed to live data for: {instruments}")
            
            # Keep the program running to receive live data
            try:
                while True:
                    time.sleep(1)
                    status = agent.get_live_data_status()
                    print(f"Connection status: {status}")
            except KeyboardInterrupt:
                print("Disconnecting from live data feed...")
                agent.disconnect_live_data()
        else:
            print("Failed to subscribe to live data")
    else:
        print("Failed to connect to live data feed")
    
    # Uncomment to test other functionality
    # agent.login()
    # agent.fetch_orders()
    # agent.fetch_quotes("NSE_INDEX|Nifty 50")