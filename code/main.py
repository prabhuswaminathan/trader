#!/usr/bin/env python3
"""
Main application for live market data visualization with flexible broker agent switching.
"""
import logging
import time
import threading
import tkinter as tk
from datetime import datetime, time as dt_time, timedelta
from typing import Optional, Dict, Any
from upstox_agent import UpstoxAgent, TradingHolidayException
from kite_agent import KiteAgent
from chart_visualizer import LiveChartVisualizer, TkinterChartApp
from broker_agent import BrokerAgent
from datawarehouse import datawarehouse
from strategy_manager import StrategyManager
from trade_utils import Utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MainApp")

class MarketDataApp:
    """Main application class for market data visualization"""
    
    def __init__(self, broker_type: str = "upstox"):
        """
        Initialize the market data application
        
        Args:
            broker_type (str): Type of broker to use ("upstox" or "kite")
        """
        self.broker_type = broker_type.lower()
        self.agent: Optional[BrokerAgent] = None
        self.chart_visualizer: Optional[LiveChartVisualizer] = None
        self.chart_app: Optional[TkinterChartApp] = None
        
        # Timer configuration
        self.timer_thread: Optional[threading.Thread] = None
        self.timer_running = False
        self.timer_interval = 300  # 5 minutes in seconds
        self.market_start_time = dt_time(9, 15)  # 9:15 AM
        self.market_end_time = dt_time(15, 30)   # 3:30 PM
        
        # Configuration - Nifty 50 and India VIX
        self.instruments = {
            "upstox": {
                "NSE_INDEX|Nifty 50": "Nifty 50",
                "NSE_INDEX|India VIX": "India VIX"
            },
            "kite": {
                256265: "Nifty 50",  # NSE:NIFTY 50
                260105: "India VIX"  # NSE:INDIA VIX
            }
        }
        
        # Strategy management
        self.strategy_manager = StrategyManager(agent=self.agent, instruments=self.instruments, broker_type=self.broker_type)
        
        # Initialize components
        self._initialize_agent()
        # Set the agent in strategy manager after it's initialized
        if self.agent:
            self.strategy_manager.set_agent(self.agent)
        self._initialize_chart()
        
        # Initialize timer tracking
        self._last_strike_update = None
        
        # Live feed debug logging flag
        self._live_feed_debug = False
        
        # Trading holiday flag
        self._is_trading_holiday = False
    
    
    def enable_live_feed_debug(self, enable=True):
        """Enable or disable debug logging for live feed data"""
        self._live_feed_debug = enable
        logger.info(f"Live feed debug logging {'enabled' if enable else 'disabled'}")
    
    def _log_live_feed(self, message, level="debug"):
        """Log live feed message based on debug setting"""
        if self._live_feed_debug:
            if level == "debug":
                logger.debug(message)
            elif level == "info":
                logger.info(message)
            elif level == "warning":
                logger.warning(message)
            elif level == "error":
                logger.error(message)
        
    def _initialize_agent(self):
        """Initialize the broker agent based on type"""
        try:
            if self.broker_type == "upstox":
                self.agent = UpstoxAgent()
                logger.info("Initialized Upstox agent")
            elif self.broker_type == "kite":
                self.agent = KiteAgent()
                logger.info("Initialized Kite agent")
            else:
                raise ValueError(f"Unsupported broker type: {self.broker_type}")
                
        except Exception as e:
            logger.error(f"Failed to initialize {self.broker_type} agent: {e}")
            raise
    
    def _initialize_chart(self):
        """Initialize the chart visualizer"""
        try:
            self.chart_visualizer = LiveChartVisualizer(
                title=f"Live Market Data - {self.broker_type.upper()}",
                max_candles=500  # Increased to handle full intraday dataset (288+ candles)
            )
                        
            # Add instruments to chart
            for instrument_key, instrument_name in self.instruments[self.broker_type].items():
                self.chart_visualizer.add_instrument(instrument_key, instrument_name)
            
            logger.info("Initialized chart visualizer")
            
        except Exception as e:
            logger.error(f"Failed to initialize chart visualizer: {e}")
            raise
    
    def switch_broker(self, new_broker_type: str):
        """
        Switch to a different broker agent
        
        Args:
            new_broker_type (str): New broker type ("upstox" or "kite")
        """
        try:
            logger.info(f"Switching from {self.broker_type} to {new_broker_type}")
            
            # Disconnect current agent
            if self.agent and self.agent.is_connected:
                self.agent.disconnect_live_data()
            
            # Update broker type
            self.broker_type = new_broker_type.lower()
            
            # Initialize new agent
            self._initialize_agent()
            
            # Update strategy manager with new agent
            if self.agent:
                self.strategy_manager.set_agent(self.agent)
            
            # Reinitialize chart with new instruments
            self._initialize_chart()
            
            # Reconnect if chart was running
            if self.chart_app and self.chart_visualizer.is_running:
                self.start_live_data()
            
            logger.info(f"Successfully switched to {self.broker_type} agent")
            
        except Exception as e:
            logger.error(f"Failed to switch broker: {e}")
            raise
    
    def start_live_data(self):
        """Start live data streaming and chart visualization"""
        try:
            if not self.agent:
                raise RuntimeError("No agent initialized")
            
            # Connect to live data
            if not self.agent.connect_live_data():
                raise RuntimeError("Failed to connect to live data feed")
            
            # Add chart callback
            self.agent.add_live_data_callback(self._on_live_data)
            
            # Subscribe to instruments
            instrument_keys = list(self.instruments[self.broker_type].keys())
            if not self.agent.subscribe_live_data(instrument_keys):
                raise RuntimeError("Failed to subscribe to live data")
            
            # Set datawarehouse reference in chart visualizer
            self.chart_visualizer.set_datawarehouse(datawarehouse)
            
            # Start chart
            self.chart_visualizer.start_chart()
            
            logger.info(f"Started live data streaming for {self.broker_type}")
            
        except Exception as e:
            logger.error(f"Failed to start live data: {e}")
            raise
    
    def stop_live_data(self):
        """Stop live data streaming and chart visualization"""
        try:
            if self.agent:
                self.agent.disconnect_live_data()
            
            if self.chart_visualizer:
                self.chart_visualizer.stop_chart()
            
            logger.info("Stopped live data streaming")
            
        except Exception as e:
            logger.error(f"Error stopping live data: {e}")
    
    def _on_live_data(self, data):
        """Callback function to handle live data updates"""
        try:
            self._log_live_feed(f"Received live data: {type(data)} - {str(data)[:200]}...")
            
            # Process data based on broker type (only updates datawarehouse)
            if self.broker_type == "upstox":
                self._process_upstox_data(data)
            elif self.broker_type == "kite":
                self._process_kite_data(data)
            else:
                logger.warning(f"Unknown broker type: {self.broker_type}")
            
            # Chart will fetch data from datawarehouse via its own timer
            
        except Exception as e:
            logger.error(f"Error processing live data: {e}")
            logger.error(f"Data type: {type(data)}, Data: {data}")
    
    def _load_historical_data(self, start_date: str, end_date: str):
        """Load historical data for context and better Y-axis scaling"""
        try:
            # Get the primary instrument (first in the list)
            primary_instrument = list(self.instruments[self.broker_type].keys())[0]
            
            # Fetch fresh historical data from broker (no caching)
            logger.info(f"Fetching fresh historical data for {primary_instrument}...")
            historical_data = self.agent.get_ohlc_historical_data(
                primary_instrument,     
                unit="minutes",
                interval=5,
                from_date=start_date,
                end_date=end_date
            )
            
            # Update datawarehouse with latest price from historical data
            if historical_data and len(historical_data) > 0:
                latest_candle = historical_data[0]  # Historical data is sorted with most recent first
                latest_price = latest_candle.get('close', latest_candle.get('price', 0))
                latest_volume = latest_candle.get('volume', 0)
                
                # Store historical data in datawarehouse
                datawarehouse.store_historical_data(primary_instrument, historical_data)
                
                # Store latest price in datawarehouse for P&L calculations
                datawarehouse.store_latest_price(primary_instrument, latest_price, latest_volume, 'historical')
                logger.info(f"Updated datawarehouse with latest price from historical data: {primary_instrument} = {latest_price}")
            
            return historical_data
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
    
    def fetch_and_display_historical_data(self):
        """Fetch historical data from broker and display in chart"""
        try:
            # Get the primary instrument (first in the list)
            primary_instrument = list(self.instruments[self.broker_type].keys())[0]
            
            logger.info(f"Fetching historical data for {primary_instrument}...")
            
            # Fetch historical data from broker
            historical_data = self._load_historical_data()
            
            if historical_data and len(historical_data) > 0:
                logger.info(f"Fetched {len(historical_data)} historical candles from broker")
                
                # Store the latest price from the most recent historical candle
                latest_candle = historical_data[0]  # Historical data is sorted with most recent first
                latest_price = latest_candle.get('close', latest_candle.get('price', 0))
                latest_volume = latest_candle.get('volume', 0)
                
                # Store historical data in datawarehouse
                datawarehouse.store_historical_data(primary_instrument, historical_data)
                
                # Store latest price in datawarehouse for P&L calculations
                datawarehouse.store_latest_price(primary_instrument, latest_price, latest_volume, 'historical')
                logger.info(f"Stored latest price from historical data: {primary_instrument} = {latest_price}")
                
                # Historical data is stored in datawarehouse only, not displayed in chart
                logger.info(f"Stored {len(historical_data)} historical candles in datawarehouse (not displayed in chart)")
                
                return True
            else:
                logger.warning("No historical data received from broker")
                return False
                
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return False
        
    def fetch_and_display_intraday_data(self):
        """Fetch intraday data from broker and display in chart"""
        try:
            # Get the primary instrument (first in the list)
            primary_instrument = list(self.instruments[self.broker_type].keys())[0]
            
            logger.info(f"Fetching intraday data for {primary_instrument}...")
            logger.info(f"Agent type: {type(self.agent)}, Agent connected: {self.agent.is_connected if self.agent else 'No agent'}")
            
            # Test agent connection first
            if not self.agent:
                logger.error("No agent available for data fetching")
                return False
            

            data_fetched = False
            intraday_data = None
            
            if not Utils.isWeekend():
                # Fetch 1-minute intraday data from broker
                logger.info(f"Calling get_ohlc_intraday_data with instrument: {primary_instrument}")
                try:
                    intraday_data = self.agent.get_ohlc_intraday_data(
                        primary_instrument, 
                        interval="5"
                    )
                    logger.info(f"get_ohlc_intraday_data returned: {len(intraday_data) if intraday_data else 0} candles")
                    data_fetched = len(intraday_data) > 0                    
                except TradingHolidayException as e:
                    logger.warning(f"Trading holiday detected: {e}")
                    data_fetched = False
            
            # If intraday data failed or it's weekend, try historical data as fallback
            if not data_fetched:
                logger.info("Intraday data not available - fetching historical data as fallback")
                if Utils.isWeekend():
                    start_date = Utils.getPreviousFriday().strftime("%Y-%m-%d")
                else:
                    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                
                intraday_data = self._load_historical_data(start_date, start_date)
                data_fetched = len(intraday_data) > 0
            
            if intraday_data and len(intraday_data) > 0:
                logger.info(f"Fetched {len(intraday_data)} candles from broker")
                
                # Store the latest price from the most recent candle for P&L calculations
                latest_candle = intraday_data[0]  # Get the most recent candle
                latest_price = latest_candle.get('close', latest_candle.get('price', 0))
                latest_volume = latest_candle.get('volume', 0)
                
                # Store intraday data in datawarehouse
                datawarehouse.store_intraday_data(primary_instrument, intraday_data)
                
                # Store latest price in datawarehouse for P&L calculations
                datawarehouse.store_latest_price(primary_instrument, latest_price, latest_volume, 'intraday')
                logger.info(f"Stored latest price for P&L: {primary_instrument} = {latest_price}")
                
                # Store intraday data in chart for display
                if self.chart_visualizer:
                    self.chart_visualizer._store_intraday_data(primary_instrument, intraday_data)
                    logger.info(f"Stored {len(intraday_data)} intraday candles in chart for display")
                
                return True
            else:
                # No intraday data available - fetch historical data
                logger.warning("No intraday data received from broker - fetching historical data")
                self._is_trading_holiday = True  # Set flag to disable timer
                
                return True
                
        except Exception as e:
            logger.error(f"Error fetching intraday data: {e}")
            return False
    
    def _process_upstox_data(self, data):
        """Process Upstox live data - handle new response format with feeds object"""
        try:
            # Check if it's after market close (3:45 PM)
            current_time = datetime.now().time()
            if self._is_after_market_close(current_time):
                self._log_live_feed(f"Market close detected at {current_time.strftime('%H:%M:%S')} - stopping live feed processing")
                # Disconnect from live feed
                if hasattr(self, 'broker_agent') and self.broker_agent:
                    self.broker_agent.disconnect_live_feed()
                return
            
            # Log the received data for debugging
            self._log_live_feed(f"Processing Upstox data: {type(data)} - {str(data)[:100]}...")
            
            # Check if data is valid
            if data is None:
                logger.warning("Received None data from Upstox")
                return
            
            # Check if data contains "feeds" object
            if not isinstance(data, dict) or 'feeds' not in data:
                self._log_live_feed("No 'feeds' object found in response, skipping processing")
                return
            
            feeds = data.get('feeds', {})
            if not feeds:
                self._log_live_feed("Empty 'feeds' object, skipping processing")
                return
            
            self._log_live_feed(f"Processing {len(feeds)} feed entries")
            
            # Process each feed entry
            for instrument_name, feed_data in feeds.items():
                try:
                    # Extract ltpc data
                    ltpc = feed_data.get('ltpc', {})
                    if not ltpc:
                        self._log_live_feed(f"No 'ltpc' data for {instrument_name}, skipping")
                        continue
                    
                    # Extract price and change
                    ltp = ltpc.get('ltp')
                    cp = ltpc.get('cp')  # Change percentage
                    ltt = ltpc.get('ltt')  # Last trade time
                    
                    if ltp is None:
                        self._log_live_feed(f"No 'ltp' data for {instrument_name}, skipping")
                        continue
                    
                    # Convert to float
                    try:
                        price = float(ltp)
                        volume = 0  # Volume not available in this format
                        
                        self._log_live_feed(f"Extracted from {instrument_name}: LTP={price}, CP={cp}, LTT={ltt}")
                        
                        # Map instrument name to our instrument key
                        instrument_key = None
                        
                        # Try to match with existing instruments
                        for key in self.instruments[self.broker_type].keys():
                            if key.upper() in instrument_name.upper():
                                instrument_key = key
                                break
                        
                        # If no specific instrument found, use the first one (NIFTY)
                        if instrument_key is None:
                            instrument_key = list(self.instruments[self.broker_type].keys())[0]
                            self._log_live_feed(f"No specific instrument found for {instrument_name}, using default: {instrument_key}")
                        
                        # Store the latest price in datawarehouse for P&L calculations
                        datawarehouse.store_latest_price(instrument_key, price, volume, 'live_feed')
                        self._log_live_feed(f"✓ Updated latest price for {instrument_key}: {price} (from {instrument_name})")
                        
                    except (ValueError, TypeError) as e:
                        self._log_live_feed(f"Error converting price for {instrument_name}: {e}")
                        continue
                        
                except Exception as e:
                    self._log_live_feed(f"Error processing feed for {instrument_name}: {e}")
                    continue
                                
        except Exception as e:
            logger.error(f"Error processing Upstox data: {e}")
            logger.error(f"Data type: {type(data)}, Data: {str(data)[:200]}...")
    
    def _process_kite_data(self, data):
        """Process Kite live data - simplified to store only latest price for P&L calculations"""
        try:
            # Check if it's after market close (3:45 PM)
            current_time = datetime.now().time()
            if self._is_after_market_close(current_time):
                self._log_live_feed(f"Market close detected at {current_time.strftime('%H:%M:%S')} - stopping live feed processing")
                # Disconnect from live feed
                if hasattr(self, 'broker_agent') and self.broker_agent:
                    self.broker_agent.disconnect_live_feed()
                return
            
            # Check if data is valid
            if data is None:
                logger.warning("Received None data from Kite")
                return
                
            if isinstance(data, list):
                for tick in data:
                    instrument_token = tick.get('instrument_token')
                    if instrument_token in self.instruments[self.broker_type]:
                        # Extract price and volume from Kite tick data
                        price = tick.get('last_price')
                        volume = tick.get('volume', 0)
                        
                        if price is not None:
                            # Store only the latest price in datawarehouse for P&L calculations
                            datawarehouse.store_latest_price(str(instrument_token), price, volume, 'live_feed')
                            self._log_live_feed(f"✓ Updated latest price for {instrument_token}: {price} (Volume: {volume})")
                            
        except Exception as e:
            logger.error(f"Error processing Kite data: {e}")
    
    def start_timer(self):
        """Start the trading timer for automatic data fetching"""
        try:
            if self.timer_running:
                logger.info("Timer is already running")
                return
            
            self.timer_running = True
            self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
            self.timer_thread.start()
            logger.info("Trading timer started (9:15 AM - 3:30 PM, every 5 minutes + 10 seconds)")
            
        except Exception as e:
            logger.error(f"Failed to start timer: {e}")
            self.timer_running = False
    
    def stop_timer(self):
        """Stop the trading timer"""
        try:
            self.timer_running = False
            if self.timer_thread and self.timer_thread.is_alive():
                self.timer_thread.join(timeout=5)
            logger.info("Trading timer stopped")
            
        except Exception as e:
            logger.error(f"Error stopping timer: {e}")
    
    def _stop_all_timers_and_feeds(self):
        """Stop all timers and live feed after market close (3:45 PM)"""
        try:
            logger.info("Stopping all timers and live feed after market close...")
            
            # Stop the main trading timer
            self.stop_timer()
            
            # Stop the datawarehouse timer (5-second updates for chart 2)
            if self.chart_visualizer:
                self.chart_visualizer.stop_datawarehouse_timer()
                logger.info("Stopped datawarehouse timer (5-second chart 2 updates)")
            
            # Disconnect from live feed
            if hasattr(self, 'broker_agent') and self.broker_agent:
                try:
                    self.broker_agent.disconnect_live_feed()
                    logger.info("Disconnected from live feed")
                except Exception as e:
                    logger.warning(f"Error disconnecting live feed: {e}")
            
            # Stop any other timers
            if hasattr(self, 'chart_visualizer') and self.chart_visualizer:
                # Stop any other chart timers
                if hasattr(self.chart_visualizer, 'stop_all_timers'):
                    self.chart_visualizer.stop_all_timers()
            
            logger.info("✅ All timers and live feed stopped after market close")
            
        except Exception as e:
            logger.error(f"Error stopping timers and feeds: {e}")
    
    def _timer_loop(self):
        """Main timer loop that runs from 9:15 AM to 3:30 PM"""
        try:
            logger.info("Timer loop started - will fetch intraday data every 5 minutes + 10 seconds during market hours")
            
            while self.timer_running:
                current_time = datetime.now().time()
                
                # Check if it's after market close (3:45 PM)
                if self._is_after_market_close(current_time):
                    logger.info(f"Market close detected at {current_time.strftime('%H:%M:%S')} - stopping all timers and live feed")
                    
                    # Stop all timers and live feed
                    self._stop_all_timers_and_feeds()
                    
                    # Exit the timer loop
                    break
                
                # Check if it's a weekend or trading holiday
                if Utils.isWeekend() or self._is_trading_holiday:
                    if Utils.isWeekend():
                        logger.info("Weekend detected - timer will not fetch data")
                    else:
                        logger.info("Trading holiday detected - timer will not fetch data")
                    time.sleep(300)  # Wait 5 minutes before checking again
                    continue
                
                # Check if we're within market hours
                if self._is_market_hours(current_time):
                    logger.info(f"Market hours detected: {current_time.strftime('%H:%M:%S')}")
                    
                    # Ensure chart is still running
                    if self.chart_visualizer:
                        self.chart_visualizer.ensure_chart_running()
                    
                    # Fetch intraday data
                    self._fetch_intraday_data_timer()
                    
                    # Wait for the next interval
                    self._wait_for_next_interval()
                else:
                    # Outside market hours, wait 1 minute and check again
                    logger.debug(f"Outside market hours: {current_time.strftime('%H:%M:%S')}")
                    time.sleep(60)  # Wait 1 minute
                    
        except Exception as e:
            logger.error(f"Error in timer loop: {e}")
        finally:
            logger.info("Timer loop ended")
    
    def _is_market_hours(self, current_time: dt_time) -> bool:
        """Check if current time is within market hours (9:15 AM - 3:30 PM)"""
        return self.market_start_time <= current_time <= self.market_end_time
    
    def _is_after_market_close(self, current_time: dt_time) -> bool:
        """Check if current time is after market close (3:45 PM)"""
        market_close_time = dt_time(15, 45)  # 3:45 PM
        return current_time >= market_close_time
    
    def _wait_for_next_interval(self):
        """Wait for the next 5-minute interval + 10 seconds"""
        try:
            current_time = datetime.now()
            
            # Calculate next 5-minute mark
            minutes_since_hour = current_time.minute
            next_interval_minutes = ((minutes_since_hour // 5) + 1) * 5
            
            if next_interval_minutes >= 60:
                # Next hour
                next_time = current_time.replace(minute=0, second=10, microsecond=0) + timedelta(hours=1)
            else:
                # Same hour, add 10 seconds to the 5-minute mark
                next_time = current_time.replace(minute=next_interval_minutes, second=10, microsecond=0)
            
            # Calculate sleep duration
            sleep_duration = (next_time - current_time).total_seconds()
            
            if sleep_duration > 0:
                logger.info(f"Waiting {sleep_duration:.0f} seconds until next 5-minute interval + 10s: {next_time.strftime('%H:%M:%S')}")
                time.sleep(sleep_duration)
            
        except Exception as e:
            logger.error(f"Error calculating next interval: {e}")
            # Fallback to fixed interval + 10 seconds
            time.sleep(self.timer_interval + 10)
    
    def _fetch_intraday_data_timer(self):
        """Fetch intraday data as part of the timer and display in chart"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            logger.info(f"Timer [{current_time}]: Fetching latest intraday data...")
            
            # Fetch intraday data (this will update the datawarehouse and display in chart)
            success = self.fetch_and_display_intraday_data()
            
            if success:
                
                # Ensure chart is running and force refresh to display new data
                if self.chart_visualizer:
                    self.chart_visualizer.ensure_chart_running()
                    self.chart_visualizer.force_chart_update()
                
                logger.info(f"Timer [{current_time}]: ✓ Intraday data fetched and candlestick chart updated")
                
                # Compare positions with database after successful data fetch
                try:
                    logger.info(f"Timer [{current_time}]: Checking position consistency...")
                    self.compare_positions_with_database()
                except Exception as e:
                    logger.error(f"Timer [{current_time}]: Error in position comparison: {e}")
            else:
                logger.warning(f"Timer [{current_time}]: ⚠ Failed to fetch intraday data")
            
        except Exception as e:
            logger.error(f"Error fetching intraday data in timer: {e}")
    
    
    
    
    
    def _initialize_chart_with_data(self):
        """Initialize the chart with fetched data to ensure it's properly displayed"""
        try:
            if self.chart_visualizer:
                # Ensure chart is running and force update to display data
                self.chart_visualizer.ensure_chart_running()
                self.chart_visualizer.force_chart_update()
                
                
                logger.info("Chart initialized with fetched data")
            else:
                logger.warning("Chart visualizer not available for initialization")
        except Exception as e:
            logger.error(f"Error initializing chart with data: {e}")
    
    def run_chart_app(self):
        """Run the chart application with GUI"""
        try:
            self.chart_app = TkinterChartApp(self.chart_visualizer)
            
            # Set the current agent for order placement
            if self.agent:
                self.chart_app.set_agent(self.agent)
                logger.info(f"Trading agent set in chart app: {type(self.agent).__name__}")
            
            # Set the main app reference in chart app for chart refresh
            self.chart_app._main_app = self
            
            logger.info("Starting chart application...")
            
            # Auto-start the chart and timer
            logger.info("Auto-starting chart and timer...")
            self.chart_app.chart.start_chart()
            self.chart_app.status_label.config(text="Status: Running - Chart initialized with intraday data")
            
            # Check if it's weekend or trading holiday
            is_weekend = Utils.isWeekend()
            should_start_live_data = not self._is_trading_holiday and not is_weekend
            
            if should_start_live_data:
                # Start live data streaming
                self.start_live_data()
            else:
                if is_weekend:
                    logger.info("Weekend detected - skipping live data subscription")
                if self._is_trading_holiday:
                    logger.info("Trading holiday detected - skipping live data subscription")
            
            # Start the timer for automatic data fetching (only if not trading holiday or weekend)
            if should_start_live_data:
                self.start_timer()
                self.chart_app.status_label.config(text="Status: Running - Timer active (5min + 10s intervals)")
            else:
                if is_weekend:
                    self.chart_app.status_label.config(text="Status: Weekend Mode - Historical data only")
                else:
                    self.chart_app.status_label.config(text="Status: Historical Data Mode - No refresh needed")
            
            # Auto-display strategy in Grid 2 on startup
            try:
                logger.info("Auto-displaying strategy in Grid 2...")
                self.strategy_manager.initialize_option_chain(self.agent.ACCESS_TOKEN)
                self._display_appropriate_chart()
            except Exception as e:
                logger.error(f"Error in auto strategy display: {e}")
                # Fallback: try to display appropriate chart
                try:
                    self._display_appropriate_chart()
                except Exception as fallback_error:
                    logger.error(f"Error in fallback chart display: {fallback_error}")
            
            # Override the window close handler to include cleanup
            def cleanup_and_close():
                logger.info("Application closing - cleaning up...")
                try:
                    # Stop timer
                    self.stop_timer()
                    # Stop live data
                    self.stop_live_data()
                    # Stop chart
                    if self.chart_visualizer:
                        self.chart_visualizer.stop_chart()
                    logger.info("Cleanup completed")
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
                finally:
                    # Call the chart app's close handler for proper cleanup
                    if hasattr(self.chart_app, 'on_closing'):
                        self.chart_app.on_closing()
                    else:
                        # Fallback: destroy the window and exit
                        self.chart_app.root.destroy()
                        import os
                        os._exit(0)
            
            # Set the cleanup function as the window close handler
            self.chart_app.root.protocol("WM_DELETE_WINDOW", cleanup_and_close)
            
            self.chart_app.run()
            
        except Exception as e:
            logger.error(f"Error running chart app: {e}")
            raise
    
    def get_open_trades(self):
        """Get open trades from the database"""
        from trade_database import TradeDatabase
        db = TradeDatabase("trades.db")
        open_trades = db.get_open_trades()
        if open_trades:
            return open_trades
        else:
            primary_instrument = list(self.instruments[self.broker_type].keys())[0]
            spot_price = datawarehouse.get_latest_price(primary_instrument)
            return self.strategy_manager.create_iron_condor_strategy(spot_price)

    def _display_appropriate_chart(self):
        """Display appropriate chart based on open trades availability"""
        open_trades = self.get_open_trades()
        primary_instrument = list(self.instruments[self.broker_type].keys())[0]
        spot_price = datawarehouse.get_latest_price(primary_instrument)
        self._display_trade_payoff_graph(open_trades, spot_price)
    
    
    def _display_trade_payoff_graph(self, open_trades, spot_price):
        """Display Iron Condor strategy when no open trades"""
        try:
            if not self.chart_app or not hasattr(self.chart_app, 'display_trade_payoff_graph'):
                logger.warning("Chart app not available or missing display_trade_payoff_graph method")
                return
            
            self.chart_app.display_trade_payoff_graph(open_trades, spot_price, self.strategy_manager)
            logger.info(f"Displayed Iron Condor strategy in Grid 2 with spot price: {spot_price}")
            
        except Exception as e:
            logger.error(f"Error displaying Iron Condor strategy: {e}")
            # Display error message in chart
            if self.chart_app and hasattr(self.chart_app, 'display_error_message'):
                self.chart_app.display_error_message(f"Failed to create Iron Condor strategy: {e}")
            else:
                logger.error("Cannot display error message - chart app not available or missing display_error_message method")
    
    def cleanup(self):
        """Clean up all resources and stop all processes"""
        try:
            logger.info("Starting application cleanup...")
            
            # Stop timer
            if hasattr(self, 'timer_running') and self.timer_running:
                self.stop_timer()
                logger.info("Timer stopped")
            
            # Stop live data
            if hasattr(self, 'agent') and self.agent:
                self.stop_live_data()
                logger.info("Live data stopped")
            
            # Stop chart
            if hasattr(self, 'chart_visualizer') and self.chart_visualizer:
                self.chart_visualizer.stop_chart()
                logger.info("Chart stopped")
            
            logger.info("Application cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def compare_positions_with_database(self):
        """
        Compare open trade legs in database with server positions and show alert if mismatch.
        """
        try:
            if not self.agent:
                logger.warning("No agent available for position comparison")
                return
            
            # Get open trade legs from database
            from trade_database import TradeDatabase
            db = TradeDatabase("trades.db")
            open_legs = db.get_open_trade_legs()
            
            if not open_legs:
                logger.info("No open trade legs found in database")
                return
            
            # Fetch positions from server
            server_positions = self.agent.fetch_positions()
            if not server_positions:
                logger.warning("No positions received from server")
                return
            
            # Create a set of server position trading symbols for quick lookup
            server_symbols = set()
            for pos in server_positions:
                trading_symbol = pos.get('trading_symbol', '')
                if trading_symbol:
                    server_symbols.add(trading_symbol)
            
            # Check for missing positions
            missing_positions = []
            for leg in open_legs:
                # Try different matching strategies
                leg_found = False
                
                # Direct match
                if leg.instrument in server_symbols:
                    leg_found = True
                elif leg.instrument_name in server_symbols:
                    leg_found = True
                else:
                    # Partial match - check if any server position contains the leg instrument
                    for server_symbol in server_symbols:
                        if (leg.instrument in server_symbol or 
                            server_symbol in leg.instrument or
                            leg.instrument_name in server_symbol or
                            server_symbol in leg.instrument_name):
                            leg_found = True
                            break
                
                if not leg_found:
                    missing_positions.append({
                        'instrument': leg.instrument,
                        'instrument_name': leg.instrument_name,
                        'option_type': leg.option_type.value,
                        'strike_price': leg.strike_price,
                        'position_type': leg.position_type.value,
                        'quantity': leg.quantity
                    })
            
            # Show alert if there are missing positions
            if missing_positions:
                self._show_position_mismatch_alert(missing_positions, len(server_positions))
            else:
                logger.info(f"✓ All {len(open_legs)} open trade legs found in server positions")
                
        except Exception as e:
            logger.error(f"Error comparing positions with database: {e}")
    
    def _show_position_mismatch_alert(self, missing_positions, server_position_count):
        """
        Show alert dialog for missing positions.
        
        Args:
            missing_positions: List of missing position details
            server_position_count: Total number of server positions
        """
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # Create alert message
            message = f"Position Mismatch Alert!\n\n"
            message += f"Found {len(missing_positions)} open trade legs in database that are NOT present in server positions.\n"
            message += f"Server has {server_position_count} positions.\n\n"
            message += "Missing positions:\n"
            
            for i, pos in enumerate(missing_positions, 1):
                message += f"{i}. {pos['instrument_name']} ({pos['option_type']} {pos['strike_price']}) - {pos['position_type']} {pos['quantity']}\n"
            
            message += "\nThis could indicate:\n"
            message += "• Positions were closed outside the application\n"
            message += "• Database is out of sync with server\n"
            message += "• Network/API issues\n\n"
            message += "Please verify your positions manually."
            
            # Show alert
            if self.chart_app and hasattr(self.chart_app, 'root'):
                # Show in the main window
                messagebox.showwarning("Position Mismatch", message, parent=self.chart_app.root)
            else:
                # Fallback: print to console
                logger.warning(f"POSITION MISMATCH ALERT: {message}")
                print(f"\n{'='*60}")
                print("POSITION MISMATCH ALERT")
                print(f"{'='*60}")
                print(message)
                print(f"{'='*60}\n")
                
        except Exception as e:
            logger.error(f"Error showing position mismatch alert: {e}")
            # Fallback: just log the issue
            logger.warning(f"POSITION MISMATCH: {len(missing_positions)} positions missing from server")

    def get_status(self) -> Dict[str, Any]:
        """Get current application status"""
        status = {
            "broker_type": self.broker_type,
            "agent_connected": self.agent.is_connected if self.agent else False,
            "chart_running": self.chart_visualizer.is_running if self.chart_visualizer else False,
            "subscribed_instruments": list(self.instruments[self.broker_type].keys())
        }
        
        if self.agent:
            status.update(self.agent.get_live_data_status())
        
        return status


def main():
    """Main function to run the application"""
    try:
        # Create application with Upstox agent by default
        app = MarketDataApp(broker_type="upstox")
        app.enable_live_feed_debug(False)
        logger.info("Market Data Application initialized")
        logger.info("Available broker types: upstox, kite")
        
        # Historical data is now fetched fresh during chart initialization
        logger.info("Historical data will be fetched fresh during chart initialization...")
        
        # Fetch and display intraday data for candlestick chart
        logger.info("Fetching intraday data for candlestick chart...")
        logger.info(f"Agent status: {app.get_status()}")
        if app.fetch_and_display_intraday_data():
            logger.info("✓ Intraday data loaded successfully - candlestick chart ready")
        else:
            logger.warning("⚠ Failed to load intraday data - chart may be empty")
        
        logger.info("Starting chart application...")
        
        # Ensure chart is properly initialized with data
        app._initialize_chart_with_data()
        
        # Run the chart application
        app.run_chart_app()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
    finally:
        # Cleanup
        try:
            if 'app' in locals():
                app.cleanup()
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")
            # Force exit
            import os
            os._exit(0)


if __name__ == "__main__":
    main()
