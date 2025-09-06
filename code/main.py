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
from upstox_agent import UpstoxAgent
from kite_agent import KiteAgent
from chart_visualizer import LiveChartVisualizer, TkinterChartApp
from broker_agent import BrokerAgent
from datawarehouse import datawarehouse
from strategy_manager import StrategyManager

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
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
        
        # Strategy management
        self.strategy_manager = StrategyManager()
        
        # Configuration - Only Nifty 50
        self.instruments = {
            "upstox": {
                "NSE_INDEX|Nifty 50": "Nifty 50"
            },
            "kite": {
                256265: "Nifty 50"  # NSE:NIFTY 50
            }
        }
        
        # Initialize components
        self._initialize_agent()
        self._initialize_chart()
        
        # Initialize timer tracking
        self._last_strike_update = None
        
        # Live feed debug logging flag
        self._live_feed_debug = False
    
    def _safe_datetime_diff(self, dt1, dt2, default_seconds=0):
        """Safely calculate datetime difference, handling None values"""
        try:
            if dt1 is None or dt2 is None:
                return default_seconds
            return (dt1 - dt2).total_seconds()
        except Exception as e:
            logger.warning(f"Error calculating datetime difference: {e}")
            return default_seconds
    
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
                title=f"Nifty 50 Live Data - {self.broker_type.upper()}",
                max_candles=500  # Increased to handle full intraday dataset (288+ candles)
            )
            
            # Load historical data for context
            self._load_historical_data()
            
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
            
            # Process data based on broker type
            if self.broker_type == "upstox":
                self._process_upstox_data(data)
            elif self.broker_type == "kite":
                self._process_kite_data(data)
            else:
                logger.warning(f"Unknown broker type: {self.broker_type}")
            
        except Exception as e:
            logger.error(f"Error processing live data: {e}")
            logger.error(f"Data type: {type(data)}, Data: {data}")
    
    def _load_historical_data(self):
        """Load historical data for context and better Y-axis scaling"""
        try:
            # Get the primary instrument (Nifty 50)
            primary_instrument = list(self.instruments[self.broker_type].keys())[0]
            
            # Try to get stored historical data first
            historical_df = datawarehouse.get_historical_data(primary_instrument, limit=50)
            
            if historical_df.empty:
                # If no stored data, try to fetch from broker
                logger.info(f"No stored historical data found for {primary_instrument}, fetching from broker...")
                historical_data = self.agent.get_ohlc_historical_data(
                    primary_instrument,     
                    interval="day",
                    start_time=None,  # Will use default (last year)
                    end_time=None
                )
                
                if historical_data:
                    # Store the fetched data
                    self.agent.store_ohlc_data(primary_instrument, historical_data, "historical")
                    historical_df = datawarehouse.get_historical_data(primary_instrument, limit=50)
            
            if not historical_df.empty:
                # Convert to the format expected by chart visualizer
                for _, row in historical_df.iterrows():
                    candle_data = {
                        'timestamp': row.name,
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row.get('volume', 0))
                    }
                    self.chart_visualizer.update_data(primary_instrument, candle_data)
                
                logger.info(f"Loaded {len(historical_df)} historical candles for context")
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
    
    def fetch_and_display_historical_data(self):
        """Fetch historical data from broker and display in chart"""
        try:
            # Get the primary instrument (Nifty 50)
            primary_instrument = list(self.instruments[self.broker_type].keys())[0]
            
            logger.info(f"Fetching historical data for {primary_instrument}...")
            
            # Fetch historical data from broker
            historical_data = self.agent.get_ohlc_historical_data(
                primary_instrument, 
                interval="day",
                start_time=None,  # Will use default (last year)
                end_time=None
            )
            
            if historical_data:
                logger.info(f"Fetched {len(historical_data)} historical candles from broker")
                
                # Store the fetched data
                self.agent.store_ohlc_data(primary_instrument, historical_data, "historical")
                
                # Display in chart (limit to last 50 candles for performance)
                display_data = historical_data[-50:] if len(historical_data) > 50 else historical_data
                
                for candle in display_data:
                    self.chart_visualizer.update_data(primary_instrument, candle)
                
                logger.info(f"Displayed {len(display_data)} historical candles in chart")
                
                # Chart will be updated by animation loop, no need for force update
                
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
            # Get the primary instrument (Nifty 50)
            primary_instrument = list(self.instruments[self.broker_type].keys())[0]
            
            logger.info(f"Fetching intraday data for {primary_instrument}...")
            logger.info(f"Agent type: {type(self.agent)}, Agent connected: {self.agent.is_connected if self.agent else 'No agent'}")
            
            # Test agent connection first
            if not self.agent:
                logger.error("No agent available for data fetching")
                return False
            
            # Fetch 1-minute intraday data from broker
            logger.info(f"Calling get_ohlc_intraday_data with instrument: {primary_instrument}")
            intraday_data = self.agent.get_ohlc_intraday_data(
                primary_instrument, 
                interval="1minute",
                start_time=None,  # Will use default (last 24 hours)
                end_time=None
            )
            logger.info(f"get_ohlc_intraday_data returned: {len(intraday_data) if intraday_data else 0} candles")
            
            if intraday_data:
                logger.info(f"Fetched {len(intraday_data)} 1-minute candles from broker")
                
                # Store the latest price from the most recent candle for P&L calculations
                if intraday_data:
                    latest_candle = intraday_data[-1]  # Get the most recent candle
                    latest_price = latest_candle.get('close', latest_candle.get('price', 0))
                    latest_volume = latest_candle.get('volume', 0)
                    
                    # Store latest price in datawarehouse for P&L calculations
                    datawarehouse.store_latest_price(primary_instrument, latest_price, latest_volume)
                    logger.info(f"Stored latest price for P&L: {primary_instrument} = {latest_price}")
                
                # Store the raw intraday data (without consolidation)
                self.agent.store_ohlc_data(primary_instrument, intraday_data, "intraday", 1)
                logger.info(f"Stored {len(intraday_data)} 1-minute candles for P&L calculations")
                
                # Display all the data in the chart (no artificial limit)
                display_data = intraday_data
                
                # Use the new consolidation method to properly display 5-minute candles
                # Clear existing data and add fresh data
                self.chart_visualizer.add_multiple_candles(primary_instrument, display_data, clear_existing=True)
                
                logger.info(f"Displayed all {len(display_data)} intraday candles in chart (consolidated to 5-minute)")
                
                # Chart will be updated by animation loop, no need for force update
                
                return True
            else:
                logger.warning("No intraday data received from broker")
                return False
                
        except Exception as e:
            logger.error(f"Error fetching intraday data: {e}")
            return False
    
    def _process_upstox_data(self, data):
        """Process Upstox live data - simplified to store only latest price for P&L calculations"""
        try:
            # Log the received data for debugging
            self._log_live_feed(f"Processing Upstox data: {type(data)} - {str(data)[:100]}...")
            
            # Check if data is valid
            if data is None:
                logger.warning("Received None data from Upstox")
                return
            
            # Upstox data comes as Protobuf messages, extract price information
            data_str = str(data)
            
            # Try to extract price information from the data using multiple patterns
            import re
            price = None
            volume = 0
            
            # Try different price patterns
            price_patterns = [
                r'ltp[:\s=]*(\d+\.?\d*)',
                r'last_price[:\s=]*(\d+\.?\d*)',
                r'price[:\s=]*(\d+\.?\d*)',
                r'close[:\s=]*(\d+\.?\d*)',
                r'"last_price":\s*(\d+\.?\d*)',  # JSON format
                r'last_price:\s*(\d+\.?\d*)',    # Protobuf format
                r'ltp:\s*(\d+\.?\d*)',           # LTP format
                r'(\d{4,6}\.?\d*)'  # Generic 4-6 digit number (for Nifty prices)
            ]
            
            for pattern in price_patterns:
                price_match = re.search(pattern, data_str, re.IGNORECASE)
                if price_match:
                    try:
                        price = float(price_match.group(1))
                        self._log_live_feed(f"Extracted price: {price} using pattern: {pattern}")
                        break
                    except ValueError:
                        continue
            
            # Try to extract volume
            volume_patterns = [
                r'volume[:\s=]*(\d+)',
                r'vol[:\s=]*(\d+)',
                r'"volume":\s*(\d+)'  # JSON format
            ]
            
            for pattern in volume_patterns:
                volume_match = re.search(pattern, data_str, re.IGNORECASE)
                if volume_match:
                    try:
                        volume = int(volume_match.group(1))
                        break
                    except ValueError:
                        continue
            
            if price is not None:
                # Try to find the instrument key in the data
                instrument_key = None
                for key in self.instruments[self.broker_type].keys():
                    if key in data_str:
                        instrument_key = key
                        break
                
                # If no specific instrument found, use the first one (NIFTY)
                if instrument_key is None:
                    instrument_key = list(self.instruments[self.broker_type].keys())[0]
                    self._log_live_feed(f"No specific instrument found, using default: {instrument_key}")
                
                # Store only the latest price in datawarehouse for P&L calculations
                datawarehouse.store_latest_price(instrument_key, price, volume)
                self._log_live_feed(f"✓ Updated latest price for {instrument_key}: {price} (Volume: {volume})")
                
                
            else:
                logger.warning(f"Could not extract price from data: {data_str[:100]}...")
                    
        except Exception as e:
            logger.error(f"Error processing Upstox data: {e}")
            logger.error(f"Data type: {type(data)}, Data: {str(data)[:200]}...")
    
    def _process_kite_data(self, data):
        """Process Kite live data - simplified to store only latest price for P&L calculations"""
        try:
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
                            datawarehouse.store_latest_price(str(instrument_token), price, volume)
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
    
    def _timer_loop(self):
        """Main timer loop that runs from 9:15 AM to 3:30 PM"""
        try:
            logger.info("Timer loop started - will fetch intraday data every 5 minutes + 10 seconds during market hours")
            
            while self.timer_running:
                current_time = datetime.now().time()
                
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
            
            # Override the button commands to integrate live data streaming
            def integrated_start():
                logger.info("Starting chart and live data...")
                # Start the chart animation
                self.chart_app.chart.start_chart()
                # Update GUI status
                self.chart_app.status_label.config(text="Status: Running")
                self.chart_app.start_btn.config(state=tk.DISABLED)
                self.chart_app.stop_btn.config(state=tk.NORMAL)
                # Start live data streaming
                self.start_live_data()
            
            def integrated_stop():
                logger.info("Stopping chart and live data...")
                # Stop live data streaming
                self.stop_live_data()
            
            def fetch_historical():
                logger.info("Fetching historical data...")
                self.chart_app.status_label.config(text="Status: Fetching Historical Data...")
                if self.fetch_and_display_historical_data():
                    self.chart_app.status_label.config(text="Status: Historical Data Loaded")
                else:
                    self.chart_app.status_label.config(text="Status: Failed to Load Historical Data")
            
            def fetch_intraday():
                logger.info("Fetching intraday data...")
                self.chart_app.status_label.config(text="Status: Fetching Intraday Data...")
                if self.fetch_and_display_intraday_data():
                    self.chart_app.status_label.config(text="Status: Intraday Data Loaded")
                else:
                    self.chart_app.status_label.config(text="Status: Failed to Load Intraday Data")
            
            def integrated_stop():
                logger.info("Stopping chart and live data...")
                # Stop live data streaming
                self.stop_live_data()
                # Stop the chart animation
                self.chart_app.chart.stop_chart()
                # Update GUI status
                self.chart_app.status_label.config(text="Status: Stopped")
                self.chart_app.start_btn.config(state=tk.NORMAL)
                self.chart_app.stop_btn.config(state=tk.DISABLED)
            
            def start_timer():
                logger.info("Starting trading timer...")
                self.start_timer()
                self.chart_app.status_label.config(text="Status: Timer Running (9:15 AM - 3:30 PM)")
            
            def stop_timer():
                logger.info("Stopping trading timer...")
                self.stop_timer()
                self.chart_app.status_label.config(text="Status: Timer Stopped")
            
            
            # Update button commands to use integrated functions
            self.chart_app.start_btn.config(command=integrated_start)
            self.chart_app.stop_btn.config(command=integrated_stop)
            self.chart_app.fetch_historical_btn.config(command=fetch_historical)
            self.chart_app.fetch_intraday_btn.config(command=fetch_intraday)
            self.chart_app.start_timer_btn.config(command=start_timer)
            self.chart_app.stop_timer_btn.config(command=stop_timer)
            self.chart_app.manage_strategies_btn.config(command=self.manage_strategies)
            
            logger.info("Starting chart application...")
            
            # Auto-start the chart and timer
            logger.info("Auto-starting chart and timer...")
            self.chart_app.chart.start_chart()
            self.chart_app.status_label.config(text="Status: Running - Chart initialized with intraday data")
            self.chart_app.start_btn.config(state=tk.DISABLED)
            self.chart_app.stop_btn.config(state=tk.NORMAL)
            
            # Start live data streaming
            self.start_live_data()
            
            # Start the timer for automatic data fetching
            self.start_timer()
            self.chart_app.status_label.config(text="Status: Running - Timer active (5min + 10s intervals)")
            
            # Auto-display strategy in Grid 2 on startup
            try:
                logger.info("Auto-displaying strategy in Grid 2...")
                self.manage_strategies()
            except Exception as e:
                logger.error(f"Error in auto strategy display: {e}")
            
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
                    # Force exit
                    import os
                    os._exit(0)
            
            # Set the cleanup function as the window close handler
            self.chart_app.root.protocol("WM_DELETE_WINDOW", cleanup_and_close)
            
            self.chart_app.run()
            
        except Exception as e:
            logger.error(f"Error running chart app: {e}")
            raise
    
    def manage_strategies(self, access_token: str = None) -> Dict[str, Any]:
        """
        Manage trading strategies - check for open positions and create Iron Condor if needed
        
        Args:
            access_token: Upstox access token
            
        Returns:
            Dict containing strategy management results
        """
        try:
            logger.info("Starting strategy management...")
            
            # Get access token from agent if not provided
            if access_token is None and self.agent and hasattr(self.agent, 'ACCESS_TOKEN'):
                access_token = self.agent.ACCESS_TOKEN
                logger.info("Using access token from agent")
            elif access_token is None:
                logger.error("No access token available for strategy management")
                return {
                    "error": "No access token available",
                    "action_taken": "error"
                }
            
            result = self.strategy_manager.manage_positions(access_token)
            
            # Log results
            logger.info(f"Strategy management result: {result}")
            
            if result.get("action_taken") == "iron_condor_created":
                logger.info(f"Created Iron Condor strategy: {result.get('trade_created')}")
                
                # Display Iron Condor strategy in Grid 2
                if self.chart_app and hasattr(self.chart_app, 'display_iron_condor_strategy'):
                    try:
                        # Get the created trade from the strategy manager (not database)
                        trade_id = result.get('trade_created')
                        if trade_id:
                            # Get the trade object directly from strategy manager
                            # Since we're not storing in DB, we need to recreate it
                            spot_price = result.get('spot_price', 25000)
                            trade = self.strategy_manager.create_iron_condor_strategy_fallback(spot_price)
                            
                            # Calculate payoff data
                            payoff_data = self.strategy_manager.calculate_iron_condor_payoff(trade, spot_price)
                            
                            # Display in Grid 2
                            self.chart_app.display_iron_condor_strategy(trade, spot_price, payoff_data)
                            logger.info(f"Displayed Iron Condor strategy in Grid 2")
                    except Exception as e:
                        logger.error(f"Error displaying Iron Condor strategy: {e}")
                        
            elif result.get("action_taken") == "error":
                logger.error(f"Strategy management error: {result.get('error')}")
                
            else:
                logger.warning(f"Unknown action taken: {result.get('action_taken')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in strategy management: {e}")
            return {
                "error": str(e),
                "action_taken": "error"
            }
    
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
        
        # Fetch and display historical data for context
        logger.info("Fetching historical data for context...")
        if app.fetch_and_display_historical_data():
            logger.info("✓ Historical data loaded successfully")
        else:
            logger.warning("⚠ Failed to load historical data")
        
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
