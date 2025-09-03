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
                title=f"Nifty 50 Live Data - {self.broker_type.upper()}"
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
            logger.info(f"Received live data: {type(data)} - {str(data)[:200]}...")
            
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
                
                # Force chart update
                self.chart_visualizer.force_chart_update()
                
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
            
            # Fetch 1-minute intraday data from broker
            intraday_data = self.agent.get_ohlc_intraday_data(
                primary_instrument, 
                interval="1minute",
                start_time=None,  # Will use default (last 24 hours)
                end_time=None
            )
            
            if intraday_data:
                logger.info(f"Fetched {len(intraday_data)} 1-minute candles from broker")
                
                # Consolidate 1-minute data to 5-minute data
                consolidated_data = self.agent.consolidate_1min_to_5min(primary_instrument, intraday_data)
                logger.info(f"Consolidated to {len(consolidated_data)} 5-minute candles")
                
                # Store the consolidated data
                self.agent.store_ohlc_data(primary_instrument, consolidated_data, "intraday", 5)
                
                # Display in chart (limit to last 100 candles for performance)
                display_data = consolidated_data[-100:] if len(consolidated_data) > 100 else consolidated_data
                
                for candle in display_data:
                    self.chart_visualizer.update_data(primary_instrument, candle)
                
                logger.info(f"Displayed {len(display_data)} intraday candles in chart")
                
                # Force chart update
                self.chart_visualizer.force_chart_update()
                
                return True
            else:
                logger.warning("No intraday data received from broker")
                return False
                
        except Exception as e:
            logger.error(f"Error fetching intraday data: {e}")
            return False
    
    def _process_upstox_data(self, data):
        """Process Upstox live data"""
        try:
            # Log the received data for debugging
            logger.info(f"Processing Upstox data: {type(data)} - {str(data)[:200]}...")
            
            # Additional debug logging for data structure
            if hasattr(data, '__dict__'):
                logger.info(f"Data attributes: {list(data.__dict__.keys())}")
            if hasattr(data, 'last_price'):
                logger.info(f"Direct last_price access: {data.last_price}")
            if hasattr(data, 'ltp'):
                logger.info(f"Direct ltp access: {data.ltp}")
            
            # Upstox data comes as Protobuf messages, we need to extract the relevant information
            # The data structure depends on the message type (ltp, ohlc, etc.)
            
            data_str = str(data)
            
            # Try to extract price information from the data using multiple patterns
            import re
            price = None
            volume = 0
            
            # Try different price patterns (improved to handle = sign)
            price_patterns = [
                r'ltp[:\s=]*(\d+\.?\d*)',
                r'last_price[:\s=]*(\d+\.?\d*)',
                r'price[:\s=]*(\d+\.?\d*)',
                r'close[:\s=]*(\d+\.?\d*)',
                r'open[:\s=]*(\d+\.?\d*)',
                r'high[:\s=]*(\d+\.?\d*)',
                r'low[:\s=]*(\d+\.?\d*)',
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
                        logger.info(f"Extracted price: {price} using pattern: {pattern}")
                        break
                    except ValueError:
                        continue
            
            # Try to extract volume (improved to handle = sign)
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
                
                # If no specific instrument found, use the first one
                if instrument_key is None:
                    instrument_key = list(self.instruments[self.broker_type].keys())[0]
                    logger.info(f"No specific instrument found, using default: {instrument_key}")
                
                # Create tick data structure
                tick_data = {
                    'instrument_key': instrument_key,
                    'data': data,
                    'timestamp': time.time(),
                    'price': price,
                    'volume': volume
                }
                
                # Update the chart with this data
                self.chart_visualizer.update_data(instrument_key, tick_data)
                logger.info(f"✓ Updated chart for {instrument_key} with price {price}, volume {volume}")
                
                # Store the processed data in the warehouse
                tick_data = {
                    'timestamp': datetime.now(),
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                }
                # Store as intraday data (will be consolidated to 5-minute buckets)
                self.agent.store_ohlc_data(instrument_key, [tick_data], "intraday", 1)
                
                # Force immediate chart update
                self.chart_visualizer.force_chart_update()
            else:
                logger.warning(f"Could not extract price from data: {data_str[:100]}...")
                    
        except Exception as e:
            logger.error(f"Error processing Upstox data: {e}")
            logger.error(f"Data type: {type(data)}, Data: {str(data)[:200]}...")
    
    def _process_kite_data(self, data):
        """Process Kite live data"""
        try:
            if isinstance(data, list):
                for tick in data:
                    instrument_token = tick.get('instrument_token')
                    if instrument_token in self.instruments[self.broker_type]:
                        self.chart_visualizer.update_data(instrument_token, data)
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
            logger.info("Trading timer started (9:15 AM - 3:30 PM, every 5 minutes)")
            
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
            logger.info("Timer loop started")
            
            while self.timer_running:
                current_time = datetime.now().time()
                
                # Check if we're within market hours
                if self._is_market_hours(current_time):
                    logger.info(f"Market hours detected: {current_time.strftime('%H:%M:%S')}")
                    
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
        """Wait for the next 5-minute interval"""
        try:
            current_time = datetime.now()
            
            # Calculate next 5-minute mark
            minutes_since_hour = current_time.minute
            next_interval_minutes = ((minutes_since_hour // 5) + 1) * 5
            
            if next_interval_minutes >= 60:
                # Next hour
                next_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                # Same hour
                next_time = current_time.replace(minute=next_interval_minutes, second=0, microsecond=0)
            
            # Calculate sleep duration
            sleep_duration = (next_time - current_time).total_seconds()
            
            if sleep_duration > 0:
                logger.info(f"Waiting {sleep_duration:.0f} seconds until next 5-minute interval: {next_time.strftime('%H:%M:%S')}")
                time.sleep(sleep_duration)
            
        except Exception as e:
            logger.error(f"Error calculating next interval: {e}")
            # Fallback to fixed interval
            time.sleep(self.timer_interval)
    
    def _fetch_intraday_data_timer(self):
        """Fetch intraday data as part of the timer"""
        try:
            logger.info("Timer: Fetching intraday data...")
            
            # Fetch intraday data
            self.fetch_and_display_intraday_data()
            
            # Force chart update
            if self.chart_visualizer:
                self.chart_visualizer.force_chart_update()
                logger.info("Timer: Chart updated with new intraday data")
            
        except Exception as e:
            logger.error(f"Error fetching intraday data in timer: {e}")
    
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
            
            logger.info("Starting chart application...")
            self.chart_app.run()
            
        except Exception as e:
            logger.error(f"Error running chart app: {e}")
            raise
    
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
        
        logger.info("Market Data Application initialized")
        logger.info("Available broker types: upstox, kite")
        
        # Fetch and display historical data
        logger.info("Fetching historical data...")
        if app.fetch_and_display_historical_data():
            logger.info("✓ Historical data loaded successfully")
        else:
            logger.warning("⚠ Failed to load historical data")
        
        # Fetch and display intraday data
        logger.info("Fetching intraday data...")
        if app.fetch_and_display_intraday_data():
            logger.info("✓ Intraday data loaded successfully")
        else:
            logger.warning("⚠ Failed to load intraday data")
        
        logger.info("Starting chart application...")
        
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
                app.stop_live_data()
                app.stop_timer()
        except:
            pass


if __name__ == "__main__":
    main()
