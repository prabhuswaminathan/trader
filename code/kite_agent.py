import logging
import threading
import time
from kiteconnect import KiteConnect, KiteTicker
from broker_agent import BrokerAgent

logging.basicConfig(level=logging.DEBUG)

class KiteAgent(BrokerAgent):
    def __init__(self):
        super().__init__()
        self.kite = KiteConnect(api_key="z102ygbcfqtv6jfw")
        self.kite.set_access_token("Kq07pZrV277nXC7JrfDe2j60eyAlZ4sN")
        self.kws = None


    def login(self):
        url = self.kite.login_url()
        print(url)
        # Redirect the user to the login url obtained
        # from kite.login_url(), and receive the request_token
        # from the registered redirect url after the login flow.
        # Once you have the request_token, obtain the access_token
        # as follows.

        data = self.kite.generate_session("FtfiSYOv8b1ICJrEcX0Ura5B7UdFBt3L", api_secret="cib9xpae769cbip683e7bmcs4t5sn12k")
        self.kite.set_access_token(data["access_token"])
        print(data["access_token"])

    def place_order(self):
        # Place an order
        try:
            order_id = self.kite.place_order(tradingsymbol="INFY",
                                        exchange=self.kite.EXCHANGE_NSE,
                                        transaction_type=self.kite.TRANSACTION_TYPE_BUY,
                                        quantity=1,
                                        variety=self.kite.VARIETY_AMO,
                                        order_type=self.kite.ORDER_TYPE_MARKET,
                                        product=self.kite.PRODUCT_CNC,
                                        validity=self.kite.VALIDITY_DAY)

            logging.info("Order placed. ID is: {}".format(order_id))
        except Exception as e:
            logging.info("Order placement failed: {}".format(e.message))


    def fetch_orders(self):
        # Fetch all orders
        orders = self.kite.orders()
        return orders

    def fetch_instruments(self):
        # Get instruments
        instruments = self.kite.instruments()
        return instruments

    def fetch_positions(self):
        # Get positions
        positions = self.kite.positions()
        return positions

    def fetch_quotes(self, symbol="NSE:NIFTY 50"):
        # Get quotes
        quotes = self.kite.quote([symbol])
        return quotes

    def logout(self):
        if self.kws:
            self.kws.close()
        self.is_connected = False

    # Live data streaming methods
    def connect_live_data(self):
        """Establish WebSocket connection for live market data streaming"""
        try:
            self.kws = KiteTicker("z102ygbcfqtv6jfw", "Kq07pZrV277nXC7JrfDe2j60eyAlZ4sN")
            
            # Set up event handlers
            self.kws.on_ticks = self._on_ticks
            self.kws.on_connect = self._on_connect
            self.kws.on_close = self._on_close
            self.kws.on_error = self._on_error
            
            # Connect to the WebSocket
            self.kws.connect(threaded=True)
            
            self.is_connected = True
            self.reconnect_attempts = 0
            self.logger.info("Connected to Kite WebSocket")
            
            return True
                
        except Exception as e:
            self.logger.error(f"Error connecting to live data feed: {e}")
            return False

    def _on_ticks(self, ws, ticks):
        """Handle incoming ticks from KiteTicker"""
        try:
            # Log the received ticks
            self.logger.debug(f"Received live data ticks: {ticks}")
            
            # Call registered callbacks
            for callback in self.live_data_callbacks:
                try:
                    callback(ticks)
                except Exception as e:
                    self.logger.error(f"Error in live data callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error processing live data ticks: {e}")

    def _on_connect(self, ws, response):
        """Handle WebSocket connection"""
        self.logger.info("Kite WebSocket connected")
        self.is_connected = True

    def _on_close(self, ws, code, reason):
        """Handle WebSocket disconnection"""
        self.logger.info(f"Kite WebSocket closed: {code} - {reason}")
        self.is_connected = False

    def _on_error(self, ws, code, reason):
        """Handle WebSocket errors"""
        self.logger.error(f"Kite WebSocket error: {code} - {reason}")
        self.is_connected = False

    def subscribe_live_data(self, instrument_keys, mode="ltpc"):
        """
        Subscribe to live data for specific instruments
        
        Args:
            instrument_keys (list): List of instrument tokens (e.g., [256265, 260105])
            mode (str): Data mode - not used in KiteTicker but kept for compatibility
        """
        if not self.is_connected:
            self.logger.warning("WebSocket not connected. Attempting to connect...")
            if not self.connect_live_data():
                self.logger.error("Failed to establish WebSocket connection")
                return False

        try:
            # Add to subscribed instruments
            self.subscribed_instruments.update(instrument_keys)
            
            # Subscribe to the instruments
            self.kws.subscribe(instrument_keys)
            
            self.logger.info(f"Subscribed to live data for: {instrument_keys}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error subscribing to live data: {e}")
            return False

    def unsubscribe_live_data(self, instrument_keys):
        """
        Unsubscribe from live data for specific instruments
        
        Args:
            instrument_keys (list): List of instrument tokens to unsubscribe from
        """
        if not self.is_connected:
            self.logger.warning("WebSocket not connected")
            return False

        try:
            # Remove from subscribed instruments
            self.subscribed_instruments.difference_update(instrument_keys)
            
            # Unsubscribe from the instruments
            self.kws.unsubscribe(instrument_keys)
            
            self.logger.info(f"Unsubscribed from live data for: {instrument_keys}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unsubscribing from live data: {e}")
            return False

    def disconnect_live_data(self):
        """Disconnect from live data feed"""
        if self.kws:
            try:
                self.kws.close()
            except Exception as e:
                self.logger.error(f"Error disconnecting WebSocket: {e}")
        self.is_connected = False
        self.logger.info("Disconnected from live data feed")
