import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Cursor
from matplotlib.dates import DateFormatter, HourLocator
import tkinter as tk
from tkinter import ttk
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import queue
import logging
from collections import deque
from trade_models import PositionType, OptionType

class LiveChartVisualizer:
    def __init__(self, title="Live Market Data", max_candles=100, candle_interval_minutes=5):
        self.title = title
        self.max_candles = max_candles
        self.candle_interval_minutes = candle_interval_minutes
        self.logger = logging.getLogger("ChartVisualizer")
        
        # Data storage
        self.data_queue = queue.Queue()
        self.candle_data = {}  # {instrument: deque of OHLCV data}
        self.current_prices = {}  # {instrument: current price}
        self.last_update_time = None  # Track last data update time
        self.historical_data = {}  # Store full historical data for scrolling
        self.current_view_start = 0  # Start index for current view
        self.view_size = 75  # Number of candles to display (one trading day)
        self.has_stored_data = {}  # Track if we have stored intraday data for each instrument
        
        # Tooltip functionality
        self.tooltip = None
        self.tooltip_annotation = None
        self.candlestick_patches = {}  # Store candlestick patches for hover detection
        
        # Crosshair functionality
        self.crosshair_vline = None  # Vertical crosshair line
        self.crosshair_hline = None  # Horizontal crosshair line
        
        # Hover labels functionality
        self.hover_labels = {}  # Store hover labels for OHLC data
        self.time_label = None  # Time label at bottom
        
        # Chart setup - Single chart for price only
        try:
            self.fig, self.price_ax = plt.subplots(1, 1, figsize=(12, 8))
            
            # Combined title with all information
            combined_title = f"{self.title} - Nifty 50 Intraday Candlestick Chart (5-Minute) - Price (₹) vs Time"
            self.fig.suptitle(combined_title, fontsize=10, fontweight='bold')
            
            # Remove individual titles to prevent overlap
            self.price_ax.set_title("")  # Empty title
            self.price_ax.set_ylabel("")  # Empty ylabel
            self.price_ax.set_xlabel("")  # Empty xlabel
            self.price_ax.grid(True, alpha=0.3)
            
            # No volume chart needed
            self.volume_ax = None
            
            # Tooltips will be setup after chart is ready
            
        except Exception as e:
            # Fallback for when matplotlib is mocked or not available
            self.logger.warning(f"Could not create matplotlib subplots: {e}")
            self.fig = None
            self.price_ax = None
            self.volume_ax = None
        
        # Chart elements
        self.candle_lines = {}
        self.volume_bars = {}
        self.price_lines = {}
        
        # Animation
        self.ani = None
        self.is_running = False
        
        # Threading
        self.update_thread = None
        self.stop_event = threading.Event()
        
        # Live data callback for payoff chart updates
        self.live_data_callback = None
        
        # Grid 2 update timer for live data
        self.last_grid2_update = 0  # Timestamp of last Grid 2 update
        self.grid2_update_interval = 5.0  # Update Grid 2 every 5 seconds
        self.pending_live_data = {}  # Store pending live data updates
        
        # Datawarehouse timer for fetching live data
        self.datawarehouse_timer = None  # Timer for fetching data from datawarehouse
        self.datawarehouse_update_interval = 5.0  # Fetch from datawarehouse every 5 seconds
        self.datawarehouse = None  # Reference to datawarehouse instance
        
    def add_instrument(self, instrument_key, instrument_name=None):
        """Add a new instrument to track"""
        if instrument_name is None:
            instrument_name = instrument_key
            
        self.candle_data[instrument_key] = deque(maxlen=self.max_candles)
        self.current_prices[instrument_key] = 0.0
        
        # Don't initialize with empty data - let the first tick create the first candle
        
        self.logger.info(f"Added instrument: {instrument_name} ({instrument_key})")
    
    def set_live_data_callback(self, callback):
        """Set callback for live data updates"""
        self.live_data_callback = callback
    
    def set_datawarehouse(self, datawarehouse):
        """Set reference to datawarehouse instance"""
        self.datawarehouse = datawarehouse
        self.logger.info("Datawarehouse reference set for chart visualizer")
    
    def start_datawarehouse_timer(self):
        """Start timer to fetch data from datawarehouse every 5 seconds"""
        try:
            if self.datawarehouse_timer:
                self.datawarehouse_timer.cancel()
            
            self.datawarehouse_timer = threading.Timer(self.datawarehouse_update_interval, self._fetch_from_datawarehouse)
            self.datawarehouse_timer.daemon = True
            self.datawarehouse_timer.start()
            
        except Exception as e:
            self.logger.error(f"Error starting datawarehouse timer: {e}")
    
    def stop_datawarehouse_timer(self):
        """Stop the datawarehouse timer"""
        try:
            if self.datawarehouse_timer:
                self.datawarehouse_timer.cancel()
                self.datawarehouse_timer = None
                self.logger.info("Stopped datawarehouse timer")
        except Exception as e:
            self.logger.error(f"Error stopping datawarehouse timer: {e}")
    
    def stop_all_timers(self):
        """Stop all timers in the chart visualizer"""
        try:
            self.logger.info("Stopping all chart visualizer timers...")
            
            # Stop datawarehouse timer (5-second updates)
            self.stop_datawarehouse_timer()
            
            # Stop any other timers that might exist
            if hasattr(self, 'chart_timer') and self.chart_timer:
                self.chart_timer.cancel()
                self.chart_timer = None
                self.logger.info("Stopped chart timer")
            
            self.logger.info("✅ All chart visualizer timers stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping all timers: {e}")
    
    def _fetch_from_datawarehouse(self):
        """Fetch latest data from datawarehouse and update only chart 2 (payoff chart)"""
        try:
            # Check if it's after market close (3:45 PM)
            from datetime import datetime, time as dt_time
            current_time = datetime.now().time()
            market_close_time = dt_time(15, 45)  # 3:45 PM
            
            if current_time >= market_close_time:
                self.logger.info(f"Market close detected at {current_time.strftime('%H:%M:%S')} - stopping datawarehouse timer")
                self.stop_datawarehouse_timer()
                return
            
            if not self.datawarehouse:
                self.logger.warning("No datawarehouse reference available")
                return
            
            # Get all instruments we're tracking
            for instrument_key in self.candle_data.keys():
                try:
                    # Get latest price from datawarehouse
                    latest_price = self.datawarehouse.get_latest_price(instrument_key)
                    if latest_price is not None:
                        # Update current price (for display purposes only)
                        self.current_prices[instrument_key] = latest_price
                        
                        # Only call live data callback for payoff chart updates (chart 2)
                        # Do NOT add to data_queue to avoid affecting chart 1
                        if self.live_data_callback:
                            self._call_live_data_callback_with_interval(instrument_key, latest_price, 0)
                        
                        self.logger.debug(f"Fetched from datawarehouse for chart 2: {instrument_key} = {latest_price}")
                    
                except Exception as e:
                    self.logger.error(f"Error fetching data for {instrument_key} from datawarehouse: {e}")
            
            # Schedule next fetch
            self.start_datawarehouse_timer()
            
        except Exception as e:
            self.logger.error(f"Error fetching from datawarehouse: {e}")
            # Still schedule next fetch even if this one failed
            self.start_datawarehouse_timer()
    
    def _call_live_data_callback_with_interval(self, instrument_key, price, volume):
        """Call live data callback with 5-second interval control"""
        try:
            import time
            current_time = time.time()
            
            # Store the latest live data
            self.pending_live_data[instrument_key] = {
                'price': price,
                'volume': volume,
                'timestamp': current_time
            }
            
            # Check if it's time to call the callback (every 5 seconds)
            if current_time - self.last_grid2_update >= self.grid2_update_interval:
                # Call the callback with the latest data
                if self.live_data_callback:
                    self.live_data_callback(instrument_key, price, volume)
                self.last_grid2_update = current_time
            else:
                # Log that we're storing data for later update
                remaining_time = self.grid2_update_interval - (current_time - self.last_grid2_update)
                self.logger.debug(f"Storing live data for {instrument_key}: {price} (Grid 2 update in {remaining_time:.1f}s)")
                
        except Exception as e:
            self.logger.error(f"Error calling live data callback with interval: {e}")
        
    def update_data(self, instrument_key, tick_data):
        """Update data for a specific instrument"""
        try:
            # Skip live data processing if we have stored intraday data
            if self.has_stored_data.get(instrument_key, False):
                self.logger.debug(f"Skipping live data update for {instrument_key} - using stored intraday data")
                return
            
            # Parse tick data based on broker type
            if isinstance(tick_data, list):
                # Kite format
                for tick in tick_data:
                    if tick['instrument_token'] == instrument_key:
                        self._process_kite_tick(instrument_key, tick)
            elif isinstance(tick_data, dict):
                # Upstox format or other
                self._process_upstox_tick(instrument_key, tick_data)
                
        except Exception as e:
            self.logger.error(f"Error updating data for {instrument_key}: {e}")
    
    def _process_kite_tick(self, instrument_key, tick):
        """Process Kite tick data"""
        # Skip live data processing if we have stored intraday data
        if self.has_stored_data.get(instrument_key, False):
            self.logger.debug(f"Skipping Kite tick processing for {instrument_key} - using stored intraday data")
            return
            
        current_price = tick.get('last_price', 0)
        volume = tick.get('volume', 0)
        timestamp = datetime.now()
        
        # Update current price
        self.current_prices[instrument_key] = current_price
        
        # Add to queue for processing
        self.data_queue.put({
            'instrument': instrument_key,
            'timestamp': timestamp,
            'price': current_price,
            'volume': volume,
            'tick': tick
        })
        
        # Call live data callback for payoff chart updates (with 5-second interval)
        if self.live_data_callback:
            self._call_live_data_callback_with_interval(instrument_key, current_price, volume)
    
    def _process_upstox_tick(self, instrument_key, tick_data):
        """Process Upstox tick data"""
        try:
            # Skip live data processing if we have stored intraday data
            if self.has_stored_data.get(instrument_key, False):
                self.logger.debug(f"Skipping Upstox tick processing for {instrument_key} - using stored intraday data")
                return
            
            # Check if this is complete OHLC data (from data warehouse)
            if isinstance(tick_data, dict) and all(key in tick_data for key in ['open', 'high', 'low', 'close']):
                # This is complete OHLC data - add it directly as a candle
                self._add_complete_candle(instrument_key, tick_data)
                return
            
            # Otherwise, process as individual tick data
            current_price = 0.0
            volume = 0
            
            # Check if tick_data already has extracted price information
            if isinstance(tick_data, dict) and 'price' in tick_data:
                current_price = tick_data.get('price', 0.0)
                volume = tick_data.get('volume', 0)
                self.logger.debug(f"Using pre-extracted price: {current_price}")
            else:
                # Try to extract price from different possible fields
                if isinstance(tick_data, dict):
                    # If it's a dictionary, try common price fields
                    # For OHLC data, use close price as current price
                    if 'close' in tick_data:
                        current_price = tick_data.get('close', 0.0)
                        self.logger.debug(f"Using close price from OHLC data: {current_price}")
                    else:
                        current_price = tick_data.get('ltp', tick_data.get('last_price', tick_data.get('price', 0)))
                    volume = tick_data.get('volume', 0)
                else:
                    # If it's a Protobuf message, try to extract price information
                    data_str = str(tick_data)
                    
                    # Try to find price patterns in the string representation
                    import re
                    price_patterns = [
                        r'ltp[:\s=]*(\d+\.?\d*)',
                        r'last_price[:\s=]*(\d+\.?\d*)',
                        r'price[:\s=]*(\d+\.?\d*)',
                        r'close[:\s=]*(\d+\.?\d*)',
                        r'open[:\s=]*(\d+\.?\d*)',
                        r'high[:\s=]*(\d+\.?\d*)',
                        r'low[:\s=]*(\d+\.?\d*)',
                        r'"last_price":\s*(\d+\.?\d*)',
                        r'last_price:\s*(\d+\.?\d*)',
                        r'ltp:\s*(\d+\.?\d*)',
                        r'(\d{4,6}\.?\d*)'
                    ]
                    
                    for pattern in price_patterns:
                        price_match = re.search(pattern, data_str, re.IGNORECASE)
                        if price_match:
                            try:
                                current_price = float(price_match.group(1))
                                break
                            except ValueError:
                                continue
                    
                    volume_patterns = [
                        r'volume[:\s=]*(\d+)',
                        r'vol[:\s=]*(\d+)',
                        r'"volume":\s*(\d+)'
                    ]
                    
                    for pattern in volume_patterns:
                        volume_match = re.search(pattern, data_str, re.IGNORECASE)
                        if volume_match:
                            try:
                                volume = int(volume_match.group(1))
                                break
                            except ValueError:
                                continue
            
            timestamp = datetime.now()
            
            # Update current price
            self.current_prices[instrument_key] = current_price
            
            # Add to queue for processing
            self.data_queue.put({
                'instrument': instrument_key,
                'timestamp': timestamp,
                'price': current_price,
                'volume': volume,
                'tick': tick_data
            })
            
            self.logger.debug(f"Processed Upstox tick for {instrument_key}: price={current_price}, volume={volume}")
            
            # Immediately update the chart if it's running
            if self.is_running:
                self._draw_charts()
            
            # Call live data callback for payoff chart updates (with 5-second interval)
            if self.live_data_callback:
                self._call_live_data_callback_with_interval(instrument_key, current_price, volume)
            
        except Exception as e:
            self.logger.error(f"Error processing Upstox tick: {e}")
            # Still add a basic entry to keep the chart alive
            self.data_queue.put({
                'instrument': instrument_key,
                'timestamp': datetime.now(),
                'price': 0.0,
                'volume': 0,
                'tick': tick_data
            })
    
    def _add_complete_candle(self, instrument_key, ohlc_data):
        """Add a complete OHLC candle directly to the chart"""
        try:
            if instrument_key not in self.candle_data:
                self.candle_data[instrument_key] = deque(maxlen=self.max_candles)
            
            # Convert timestamp to datetime if it's a string
            timestamp = ohlc_data.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif timestamp is None:
                timestamp = datetime.now()
            
            # Create complete candle data
            candle = {
                'timestamp': timestamp,
                'open': float(ohlc_data.get('open', 0)),
                'high': float(ohlc_data.get('high', 0)),
                'low': float(ohlc_data.get('low', 0)),
                'close': float(ohlc_data.get('close', 0)),
                'volume': float(ohlc_data.get('volume', 0))
            }
            
            # Add to candle data (deque will automatically limit size)
            self.candle_data[instrument_key].append(candle)
            
            # Update current price to close price
            self.current_prices[instrument_key] = candle['close']
            
            # Update last update time
            candle_time = candle['timestamp']
            if isinstance(candle_time, datetime):
                # Ensure timestamp is timezone-naive
                if candle_time.tzinfo is not None:
                    candle_time = candle_time.replace(tzinfo=None)
                self.last_update_time = candle_time
            else:
                self.last_update_time = datetime.fromtimestamp(candle_time)
            
            self.logger.debug(f"Added complete OHLC candle for {instrument_key}: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}, V={candle['volume']}")
            
            # Chart will be updated by animation loop, no need for immediate redraw
                
        except Exception as e:
            self.logger.error(f"Error adding complete candle: {e}")
    
    
    def _consolidate_candles(self, candles_data):
        """Consolidate 1-minute candles into 5-minute candles"""
        try:
            if not candles_data:
                return []
            
            # Group candles by 5-minute intervals
            consolidated = {}
            
            for candle in candles_data:
                # Convert timestamp to datetime if needed
                timestamp = candle.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif timestamp is None:
                    timestamp = datetime.now()
                
                # Round to 5-minute boundary
                minute = timestamp.minute
                rounded_minute = (minute // 5) * 5
                bucket_time = timestamp.replace(minute=rounded_minute, second=0, microsecond=0)
                
                if bucket_time not in consolidated:
                    consolidated[bucket_time] = []
                
                consolidated[bucket_time].append(candle)
            
            # Create consolidated candles
            result = []
            for bucket_time, candles in sorted(consolidated.items()):
                if not candles:
                    continue
                
                # Sort candles within the bucket by timestamp
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
                
                result.append(consolidated_candle)
            
            # Sort by timestamp
            result.sort(key=lambda x: x['timestamp'])
            
            self.logger.debug(f"Consolidated {len(candles_data)} 1-min candles into {len(result)} 5-min candles")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error consolidating candles: {e}")
            return []
    
    def _store_historical_data(self, instrument_key, historical_data):
        """Historical data storage disabled - only intraday data is displayed in grid 1"""
        self.logger.info(f"Historical data storage disabled - {len(historical_data)} historical candles not displayed in chart")
        # Historical data is stored in datawarehouse only, not displayed in chart

    def _store_intraday_data(self, instrument_key, intraday_data):
        """Store intraday data in the chart for display"""
        try:
            if not intraday_data:
                self.logger.warning(f"No intraday data to store for {instrument_key}")
                return
            
            # Initialize intraday data storage if not exists
            if instrument_key not in self.candle_data:
                self.candle_data[instrument_key] = deque(maxlen=self.max_candles)
            
            # Clear existing data before storing new data to prevent duplicates
            self.candle_data[instrument_key].clear()
            
            # Store intraday data
            for candle in intraday_data:
                self.candle_data[instrument_key].append(candle)
            
            # Mark that we have stored data for this instrument
            self.has_stored_data[instrument_key] = True
            
            # Update current price to the latest close price
            if intraday_data:
                latest_candle = intraday_data[-1]
                self.current_prices[instrument_key] = latest_candle.get('close', 0)
                
                # Update last update time
                latest_timestamp = latest_candle.get('timestamp')
                if isinstance(latest_timestamp, datetime):
                    # Ensure timestamp is timezone-naive
                    if latest_timestamp.tzinfo is not None:
                        latest_timestamp = latest_timestamp.replace(tzinfo=None)
                    self.last_update_time = latest_timestamp
                else:
                    self.last_update_time = datetime.fromtimestamp(latest_timestamp)
            
            self.logger.info(f"Stored {len(intraday_data)} intraday candles for {instrument_key}")
            
            # Force chart update to display the data
            if self.is_running:
                self.force_chart_update()
            
        except Exception as e:
            self.logger.error(f"Error storing intraday data for {instrument_key}: {e}")
    
    def _update_candle_data(self, instrument_key, price, volume, timestamp):
        """Update candle data with new tick"""
        if instrument_key not in self.candle_data:
            return
        
        # Skip live data processing if we have stored intraday data
        if self.has_stored_data.get(instrument_key, False):
            self.logger.debug(f"Skipping live data processing for {instrument_key} - using stored intraday data")
            return
            
        candle_data = self.candle_data[instrument_key]
        
        # Convert timestamp to datetime if it's a float
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        
        # Ensure timestamp is timezone-naive to avoid timezone issues
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        
        if not candle_data:
            # First data point
            candle_data.append({
                'timestamp': timestamp,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            })
            self.logger.debug(f"Created first candle for {instrument_key}: O={price}, H={price}, L={price}, C={price}, V={volume}")
            
            # Immediately update the chart if it's running
            if self.is_running:
                self._draw_charts()
        else:
            # Update last candle or create new one
            last_candle = candle_data[-1]
            current_time = timestamp
            
            # Check if we need a new candle (every N minutes as configured)
            last_timestamp = last_candle.get('timestamp')
            if last_timestamp is None:
                self.logger.warning("Last candle has no timestamp, creating new candle")
                time_diff = float('inf')  # Force new candle creation
            else:
                # Ensure both timestamps are timezone-naive for comparison
                if last_timestamp.tzinfo is not None:
                    last_timestamp = last_timestamp.replace(tzinfo=None)
                time_diff = (current_time - last_timestamp).total_seconds()
            
            if time_diff >= (self.candle_interval_minutes * 60):
                # Create new candle
                candle_data.append({
                    'timestamp': current_time,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                })
                self.logger.debug(f"Created new candle for {instrument_key}: O={price}, H={price}, L={price}, C={price}, V={volume}")
                
                # Immediately update the chart if it's running
                if self.is_running:
                    self._draw_charts()
            else:
                # Update current candle
                last_candle['high'] = max(last_candle['high'], price)
                last_candle['low'] = min(last_candle['low'], price)
                last_candle['close'] = price
                last_candle['volume'] += volume
                self.logger.debug(f"Updated candle for {instrument_key}: O={last_candle['open']}, H={last_candle['high']}, L={last_candle['low']}, C={last_candle['close']}, V={last_candle['volume']}")
                
                # Immediately update the chart if it's running
                if self.is_running:
                    self._draw_charts()
    
    def _animate(self, frame):
        """Animation function to update charts"""
        try:
            # Process queued data
            has_new_data = False
            while not self.data_queue.empty():
                try:
                    data = self.data_queue.get_nowait()
                    self._update_candle_data(
                        data['instrument'],
                        data['price'],
                        data['volume'],
                        data['timestamp']
                    )
                    has_new_data = True
                except queue.Empty:
                    break
            
            # Only update charts if there's new data
            if has_new_data:
                self._draw_charts()
            
        except Exception as e:
            self.logger.error(f"Error in animation: {e}")
    
    def _draw_charts(self):
        """Draw/update the candlestick chart"""
        try:
            # Check if axes are available
            if not self.price_ax:
                self.logger.warning("Chart axes not available, skipping chart update")
                return
            
            # Clear axes
            self.price_ax.clear()
            
            # Clear hover labels
            self.hover_labels.clear()
            self.time_label = None
            
            # Set up axes with combined title
            # Get last update time for title
            last_update_time = self._get_last_update_time()
            time_info = f" (Last Update: {last_update_time})" if last_update_time else ""
            
            # Update the combined title with current information
            combined_title = f"{self.title} - Nifty 50 Intraday Candlestick Chart (5-Minute) - Price (₹) vs Time{time_info}"
            self.fig.suptitle(combined_title, fontsize=10, fontweight='bold')
            
            # Remove individual titles to prevent overlap
            self.price_ax.set_title("")  # Empty title
            self.price_ax.set_ylabel("")  # Empty ylabel
            self.price_ax.set_xlabel("")  # Empty xlabel
            self.price_ax.grid(True, alpha=0.3)
            
            # Check if we have any data to display
            has_data = False
            
            # Plot candlesticks for each instrument
            for instrument_key, candle_data in self.candle_data.items():
                if not candle_data:
                    continue
                
                # Convert to DataFrame for easier handling
                df = pd.DataFrame(list(candle_data))
                if df.empty:
                    continue
                
                # Plot candlesticks
                self._plot_candlesticks(df, instrument_key)
                has_data = True
            
            # If no data, show a message
            if not has_data:
                self.price_ax.text(0.5, 0.5, 'No data available\nWaiting for market data...', 
                                 transform=self.price_ax.transAxes, ha='center', va='center',
                                 fontsize=14, color='gray', alpha=0.7)
                self.price_ax.set_ylim(0, 1)
                self.price_ax.set_xlim(0, 1)
            else:
                # Update Y-axis scale based on price range
                self._update_y_axis_scale()
            
            # Format x-axis with time display
            self._format_x_axis_time()
            
            # Adjust layout with proper spacing for rotated labels and combined title
            plt.tight_layout(pad=3.0)
            
            # Ensure subplot spacing accommodates rotated labels and combined title
            if hasattr(self, 'fig') and self.fig:
                self.fig.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.88)
            
            # Only redraw if chart is running to prevent flickering
            if self.is_running and hasattr(self, 'fig') and self.fig:
                self.fig.canvas.draw_idle()
            
        except Exception as e:
            self.logger.error(f"Error drawing charts: {e}")
    
    def _format_x_axis_time(self):
        """Format X-axis to display time with appropriate intervals"""
        try:
            if not self.candle_data:
                return
            
            # Collect all timestamps from all instruments
            all_timestamps = []
            for instrument_key, candle_data in self.candle_data.items():
                if not candle_data:
                    continue
                
                for candle in candle_data:
                    timestamp = candle['timestamp']
                    if isinstance(timestamp, datetime):
                        # Ensure timestamp is timezone-naive
                        if timestamp.tzinfo is not None:
                            timestamp = timestamp.replace(tzinfo=None)
                        all_timestamps.append(timestamp)
                    else:
                        # Convert timestamp to datetime if needed
                        dt = datetime.fromtimestamp(timestamp)
                        # Ensure it's timezone-naive
                        if dt.tzinfo is not None:
                            dt = dt.replace(tzinfo=None)
                        all_timestamps.append(dt)
            
            if not all_timestamps:
                return
            
            # Sort timestamps
            all_timestamps.sort()
            
            # Calculate time range
            min_time = all_timestamps[0]
            max_time = all_timestamps[-1]
            time_range = max_time - min_time
            
            # Debug logging
            self.logger.info(f"Time range: {min_time.strftime('%H:%M:%S')} to {max_time.strftime('%H:%M:%S')}")
            
            # Convert to matplotlib date format
            import matplotlib.dates as mdates
            min_time_mpl = mdates.date2num(min_time)
            max_time_mpl = mdates.date2num(max_time)
            
            # Custom formatter for time display
            def time_formatter(x, pos):
                # Convert matplotlib date number to datetime
                dt = mdates.num2date(x)
                # Display time as-is (assuming data is already in local timezone)
                return dt.strftime('%H:%M')
            
            # Set up time formatting based on data range
            if time_range.total_seconds() <= 3600:  # Less than 1 hour
                # Create custom 5-minute intervals starting from 9:21
                # Generate ticks every 5 minutes starting from 9:21
                start_tick = min_time.replace(hour=9, minute=21, second=0, microsecond=0)
                if min_time < start_tick:
                    start_tick = start_tick - timedelta(days=1) if min_time.hour < 9 else start_tick
                
                # Create custom tick positions
                ticks = []
                current_tick = start_tick
                while current_tick <= max_time + timedelta(minutes=5):
                    ticks.append(current_tick)
                    current_tick += timedelta(minutes=5)
                
                # Set custom ticks
                self.price_ax.set_xticks([mdates.date2num(t) for t in ticks])
            elif time_range.total_seconds() <= 14400:  # Less than 4 hours
                # Show 15-minute intervals
                minute_locator = mdates.MinuteLocator(interval=15)
                self.price_ax.xaxis.set_major_locator(minute_locator)
            else:
                # Show 1-hour intervals
                hour_locator = mdates.HourLocator(interval=1)
                self.price_ax.xaxis.set_major_locator(hour_locator)
            
            # Apply the time formatter
            self.price_ax.xaxis.set_major_formatter(plt.FuncFormatter(time_formatter))
            
            # Rotate x-axis labels for better readability
            self.price_ax.tick_params(axis='x', rotation=45)
            
            # Set x-axis limits based on data range
            # Ensure x-axis starts from 9:15 AM if data starts before that
            start_time = min_time
            if min_time.hour == 9 and min_time.minute < 15:
                # If data starts before 9:15, align to 9:15
                start_time = min_time.replace(hour=9, minute=15, second=0, microsecond=0)
            
            # Add padding on left to show first candle fully, and padding on right
            left_padding = timedelta(minutes=5)  # 5 minutes before first candle for better visibility
            right_padding = time_range * 0.05
            final_start = start_time - left_padding
            final_end = max_time + right_padding
            self.price_ax.set_xlim(final_start, final_end)
            
            # Debug logging
            self.logger.info(f"X-axis limits: {final_start.strftime('%H:%M:%S')} to {final_end.strftime('%H:%M:%S')}")
            
            # Adjust layout to prevent label cutoff
            self.price_ax.tick_params(axis='x', labelsize=8, pad=10)
            
            # Ensure there's enough space for rotated labels
            self.price_ax.margins(x=0.02, y=0.05)
            
            # Force matplotlib to update the axis
            if time_range.total_seconds() <= 3600:
                self.price_ax.xaxis.set_major_locator(minute_locator)
            elif time_range.total_seconds() <= 14400:
                self.price_ax.xaxis.set_major_locator(minute_locator)
            else:
                self.price_ax.xaxis.set_major_locator(hour_locator)
            
        except Exception as e:
            self.logger.error(f"Error formatting X-axis time: {e}")
            # Fallback to simple time display
            try:
                self.price_ax.tick_params(axis='x', rotation=45, labelsize=8, pad=10)
                # Set a simple time formatter
                import matplotlib.dates as mdates
                self.price_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                # Ensure proper spacing for rotated labels
                self.price_ax.margins(x=0.02, y=0.05)
            except Exception as fallback_error:
                self.logger.error(f"Error in fallback time formatting: {fallback_error}")
    
    def _update_y_axis_scale(self):
        """Update Y-axis scale based on current price range"""
        try:
            if not self.candle_data:
                return
            
            # Collect all price data from all instruments
            all_highs = []
            all_lows = []
            
            for instrument_key, candle_data in self.candle_data.items():
                if not candle_data:
                    continue
                
                # Convert to DataFrame for easier handling
                df = pd.DataFrame(list(candle_data))
                if df.empty:
                    continue
                
                # Add high and low prices
                all_highs.extend(df['high'].tolist())
                all_lows.extend(df['low'].tolist())
            
            if not all_highs or not all_lows:
                return
            
            # Calculate price range
            min_price = min(all_lows)
            max_price = max(all_highs)
            
            # Add some padding (5% on each side)
            price_range = max_price - min_price
            padding = price_range * 0.05
            
            y_min = min_price - padding
            y_max = max_price + padding
            
            # Set Y-axis limits
            self.price_ax.set_ylim(y_min, y_max)
            
            # Format Y-axis to show prices with appropriate precision
            self.price_ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.2f}'))
            
            self.logger.debug(f"Updated Y-axis scale: {y_min:.2f} to {y_max:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error updating Y-axis scale: {e}")
    
    def _plot_candlesticks(self, df, instrument_key):
        """Plot candlestick chart"""
        try:
            if df.empty:
                return
            
            # Ensure all timestamps are timezone-naive before sorting
            def normalize_timestamp(ts):
                if isinstance(ts, datetime):
                    if ts.tzinfo is not None:
                        return ts.replace(tzinfo=None)
                    return ts
                else:
                    return datetime.fromtimestamp(ts)
            
            df['timestamp'] = df['timestamp'].apply(normalize_timestamp)
            
            # Sort by timestamp to ensure proper order
            df = df.sort_values('timestamp')
            
            # Convert timestamps to matplotlib date format for proper plotting
            import matplotlib.dates as mdates
            df['timestamp_mpl'] = df['timestamp'].apply(lambda x: mdates.date2num(x))
            
            # Calculate candlestick width based on 5-minute interval
            # For 5-minute candles, use a fixed width of 4 minutes (0.8 * 5 minutes)
            candle_width = (5 * 60) * 0.8 / (24 * 3600)  # 5 minutes * 0.8 / seconds per day
            
            # Store candlestick patches for hover detection
            if instrument_key not in self.candlestick_patches:
                self.candlestick_patches[instrument_key] = []
            else:
                self.candlestick_patches[instrument_key].clear()
            
            for i, row in df.iterrows():
                timestamp_mpl = row['timestamp_mpl']
                timestamp = row['timestamp']
                open_price = row['open']
                high_price = row['high']
                low_price = row['low']
                close_price = row['close']
                
                # Skip invalid data
                if (open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0 or
                    not all(isinstance(x, (int, float)) and not np.isnan(x) for x in [open_price, high_price, low_price, close_price])):
                    self.logger.warning(f"Skipping invalid candle data: O={open_price}, H={high_price}, L={low_price}, C={close_price}")
                    continue
                
                # Determine candle color (green for up, red for down)
                candle_color = 'green' if close_price >= open_price else 'red'
                edge_color = 'darkgreen' if close_price >= open_price else 'darkred'
                
                # Draw the wick lines (upper and lower shadows)
                # Upper wick: from body top to high
                body_top = max(open_price, close_price)
                body_bottom = min(open_price, close_price)
                
                # Upper wick (if high > body top)
                upper_wick = None
                if high_price > body_top:
                    upper_wick = self.price_ax.plot([timestamp_mpl, timestamp_mpl], [body_top, high_price], 
                                     color='black', linewidth=1.5, alpha=0.8)
                
                # Lower wick (if low < body bottom)
                lower_wick = None
                if low_price < body_bottom:
                    lower_wick = self.price_ax.plot([timestamp_mpl, timestamp_mpl], [low_price, body_bottom], 
                                     color='black', linewidth=1.5, alpha=0.8)
                
                # Draw the open-close rectangle (body)
                body_patch = None
                if close_price >= open_price:
                    # Bullish candle (close >= open)
                    body_patch = self.price_ax.bar(timestamp_mpl, close_price - open_price, 
                                    bottom=open_price, width=candle_width,
                                    color=candle_color, edgecolor=edge_color, linewidth=1.5, alpha=0.8)
                else:
                    # Bearish candle (close < open)
                    body_patch = self.price_ax.bar(timestamp_mpl, open_price - close_price, 
                                    bottom=close_price, width=candle_width,
                                    color=candle_color, edgecolor=edge_color, linewidth=1.5, alpha=0.8)
                
                # Store patches for hover detection
                candle_patches = {
                    'body': body_patch[0] if body_patch else None,
                    'upper_wick': upper_wick[0] if upper_wick else None,
                    'lower_wick': lower_wick[0] if lower_wick else None,
                    'candle_data': {
                        'timestamp': timestamp,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': row.get('volume', 0)
                    }
                }
                self.candlestick_patches[instrument_key].append(candle_patches)
            
            # No line chart overlay - pure candlestick chart
            
        except Exception as e:
            self.logger.error(f"Error plotting candlesticks: {e}")
            # Fallback to simple line chart
            try:
                # Normalize timestamps before sorting
                def normalize_timestamp(ts):
                    if isinstance(ts, datetime):
                        if ts.tzinfo is not None:
                            return ts.replace(tzinfo=None)
                        return ts
                    else:
                        return datetime.fromtimestamp(ts)
                
                df['timestamp'] = df['timestamp'].apply(normalize_timestamp)
                df_sorted = df.sort_values('timestamp')
                
                # Convert timestamps for matplotlib
                import matplotlib.dates as mdates
                timestamps_mpl = df_sorted['timestamp'].apply(lambda x: mdates.date2num(x))
                self.price_ax.plot(timestamps_mpl, df_sorted['close'], 
                                 color='blue', linewidth=2, label=instrument_key, alpha=0.7)
            except Exception as fallback_error:
                self.logger.error(f"Error in fallback line chart: {fallback_error}")
    
    def start_chart(self):
        """Start the live chart"""
        if self.is_running:
            return
            
        self.is_running = True
        self.stop_event.clear()
        
        # Start animation with reduced frequency to prevent flickering
        self.ani = animation.FuncAnimation(
            self.fig, self._animate, interval=2000, blit=False, 
            cache_frame_data=False, save_count=100
        )
        
        # Start datawarehouse timer for fetching live data
        self.start_datawarehouse_timer()
        
        self.logger.info("Live chart started")
    
    def stop_chart(self):
        """Stop the live chart"""
        if not self.is_running:
            return
            
        self.is_running = False
        self.stop_event.set()
        
        if self.ani:
            self.ani.event_source.stop()
        
        # Stop datawarehouse timer
        self.stop_datawarehouse_timer()
        
        self.logger.info("Live chart stopped")
    
    def show_chart(self):
        """Display the chart window"""
        plt.show()
    
    def get_current_prices(self):
        """Get current prices for all instruments"""
        return self.current_prices.copy()
    
    def get_candle_data(self, instrument_key):
        """Get candle data for a specific instrument"""
        if instrument_key in self.candle_data:
            return list(self.candle_data[instrument_key])
        return []
    
    def set_historical_data(self, instrument_key, historical_data):
        """Historical data scrolling disabled - only intraday data is displayed in grid 1"""
        self.logger.info(f"Historical data scrolling disabled - {len(historical_data)} historical candles not stored for scrolling")
        # Historical data scrolling is disabled
    
    def set_status_callback(self, callback):
        """Set callback function for status updates"""
        self.status_callback = callback
    
    def scroll_left(self, instrument_key):
        """Historical data scrolling disabled - only intraday data is displayed in grid 1"""
        self.logger.debug("Historical data scrolling disabled")
        return False
    
    def scroll_right(self, instrument_key):
        """Historical data scrolling disabled - only intraday data is displayed in grid 1"""
        self.logger.debug("Historical data scrolling disabled")
        return False
    
    def _update_display_data(self, instrument_key):
        """Historical data display disabled - only intraday data is displayed in grid 1"""
        self.logger.debug("Historical data display disabled")
        # Historical data display is disabled
    
    def process_data_queue(self):
        """Manually process the data queue (useful for testing)"""
        try:
            while not self.data_queue.empty():
                try:
                    data = self.data_queue.get_nowait()
                    self._update_candle_data(
                        data['instrument'],
                        data['price'],
                        data['volume'],
                        data['timestamp']
                    )
                except queue.Empty:
                    break
        except Exception as e:
            self.logger.error(f"Error processing data queue: {e}")
    
    def force_chart_update(self):
        """Force an immediate chart update"""
        if self.price_ax:
            try:
                self._draw_charts()
                # Force matplotlib to redraw
                if hasattr(self, 'fig') and self.fig:
                    self.fig.canvas.draw_idle()
                    # Setup tooltips after chart is ready
                    if not hasattr(self, 'tooltip_annotation') or self.tooltip_annotation is None:
                        self._setup_tooltips()
            except Exception as e:
                self.logger.error(f"Error forcing chart update: {e}")
    
    def ensure_chart_running(self):
        """Ensure the chart is running and restart if needed"""
        try:
            if not self.is_running:
                self.logger.warning("Chart is not running, restarting...")
                self.start_chart()
                return True
            
            # Check if animation is still active
            if hasattr(self, 'ani') and self.ani and hasattr(self.ani, 'event_source'):
                # Check if the animation event source is still running
                # TimerTk doesn't have is_alive(), so we check if it's still active differently
                try:
                    if hasattr(self.ani.event_source, 'is_alive'):
                        if not self.ani.event_source.is_alive():
                            self.logger.warning("Chart animation stopped, restarting...")
                            self.start_chart()
                            return True
                    else:
                        # For TimerTk, check if the animation is still running by checking the interval
                        if not self.ani.event_source.interval:
                            self.logger.warning("Chart animation stopped, restarting...")
                            self.start_chart()
                            return True
                except Exception as e:
                    self.logger.warning(f"Error checking animation status: {e}, restarting...")
                    self.start_chart()
                    return True
            
            return True
        except Exception as e:
            self.logger.error(f"Error ensuring chart is running: {e}")
            return False
    
    def refresh_chart_data(self):
        """Refresh the chart with latest data - useful for periodic updates"""
        try:
            if self.is_running:
                self._draw_charts()
                # Force matplotlib to redraw
                if hasattr(self, 'fig') and self.fig:
                    self.fig.canvas.draw_idle()
                self.logger.debug("Chart data refreshed")
        except Exception as e:
            self.logger.error(f"Error refreshing chart data: {e}")
    
    def _setup_tooltips(self):
        """Setup tooltip functionality for candlesticks"""
        try:
            if not self.fig or not self.price_ax:
                self.logger.warning("Cannot setup tooltips: fig or price_ax not available")
                return
            
            # Check if tooltips are already set up
            if hasattr(self, 'tooltip_annotation') and self.tooltip_annotation is not None:
                self.logger.info("Tooltips already initialized")
                return
            
            # Connect mouse events
            self.fig.canvas.mpl_connect('motion_notify_event', self._on_hover)
            self.fig.canvas.mpl_connect('button_press_event', self._on_click)
            
            # Initialize tooltip annotation with error handling
            try:
                self.tooltip_annotation = self.price_ax.annotate('', xy=(0, 0), xytext=(20, 20),
                                                               textcoords="offset points",
                                                               bbox=dict(boxstyle="round,pad=0.5", 
                                                                       facecolor="white", 
                                                                       edgecolor="navy",
                                                                       linewidth=2,
                                                                       alpha=0.95),
                                                               arrowprops=dict(arrowstyle="->",
                                                                             connectionstyle="arc3,rad=0",
                                                                             color="navy",
                                                                             linewidth=2),
                                                               fontsize=11,
                                                               fontweight='bold',
                                                               color="navy",
                                                               visible=False)
            except Exception as e:
                self.logger.warning(f"Could not initialize tooltip annotation: {e}")
                self.tooltip_annotation = None
            
            self.logger.info("Tooltip functionality initialized (hover and click)")
            
        except Exception as e:
            self.logger.error(f"Error setting up tooltips: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_hover(self, event):
        """Handle mouse hover events for tooltips and crosshair"""
        try:
            if not self.tooltip_annotation or not self.price_ax:
                return
            
            # Check if mouse is over the chart
            if event.inaxes != self.price_ax:
                self.tooltip_annotation.set_visible(False)
                self._hide_crosshair()
                self._hide_hover_labels()
                self.fig.canvas.draw_idle()
                return
            
            # Update crosshair position
            self._update_crosshair(event.xdata, event.ydata)
            self.logger.debug(f"Crosshair updated at x={event.xdata}, y={event.ydata}")
            
            # Find the closest candlestick
            closest_candle = self._find_closest_candlestick(event.xdata, event.ydata)
            
            if closest_candle:
                # Show tooltip
                self._show_tooltip(event, closest_candle)
                self.logger.debug(f"Hover tooltip shown for {closest_candle['instrument']}")
            else:
                # Hide tooltip and labels
                if self.tooltip_annotation and hasattr(self.tooltip_annotation, 'set_visible'):
                    self.tooltip_annotation.set_visible(False)
                self._hide_hover_labels()
                self.fig.canvas.draw_idle()
                
        except Exception as e:
            self.logger.error(f"Error in hover event: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_click(self, event):
        """Handle mouse click events for tooltips"""
        try:
            if not self.tooltip_annotation or not self.price_ax:
                self.logger.debug("Click event: tooltip_annotation or price_ax not available")
                return
            
            # Check if mouse is over the chart
            if event.inaxes != self.price_ax:
                self.logger.debug("Click event: mouse not over chart")
                return
            
            # Only respond to left mouse button clicks
            if event.button != 1:
                self.logger.debug(f"Click event: not left button (button={event.button})")
                return
            
            self.logger.debug(f"Click event: x={event.xdata}, y={event.ydata}")
            
            # Find the closest candlestick
            closest_candle = self._find_closest_candlestick(event.xdata, event.ydata)
            
            if closest_candle:
                # Show tooltip on click
                self._show_tooltip(event, closest_candle)
                self.logger.info(f"Tooltip shown on click for {closest_candle['instrument']}")
            else:
                # Hide tooltip if no candle found
                if self.tooltip_annotation and hasattr(self.tooltip_annotation, 'set_visible'):
                    self.tooltip_annotation.set_visible(False)
                    self.fig.canvas.draw_idle()
                self.logger.debug("Click event: no closest candle found")
                
        except Exception as e:
            self.logger.error(f"Error in click event: {e}")
            import traceback
            traceback.print_exc()
    
    def _find_closest_candlestick(self, x, y):
        """Find the closest candlestick to the mouse position using stored patches"""
        try:
            if not self.candlestick_patches or x is None or y is None:
                return None
            
            closest_candle = None
            min_distance = float('inf')
            
            # Check all instruments
            for instrument_key, patches_list in self.candlestick_patches.items():
                if not patches_list:
                    continue
                
                # Check each candlestick patch
                for patch_data in patches_list:
                    candle_data = patch_data['candle_data']
                    candle_time = candle_data['timestamp']
                    
                    # Convert timestamp to matplotlib time format
                    if isinstance(candle_time, datetime):
                        candle_x = candle_time
                    else:
                        candle_x = datetime.fromtimestamp(candle_time)
                    
                    # Convert to matplotlib date format for comparison
                    import matplotlib.dates as mdates
                    candle_x_mpl = mdates.date2num(candle_x)
                    
                    # Calculate candlestick bounds
                    # For 5-minute candles, width is approximately 0.0035 days (5 minutes)
                    candle_width = 0.0035  # 5 minutes in days
                    candle_left = candle_x_mpl - candle_width/2
                    candle_right = candle_x_mpl + candle_width/2
                    
                    # Check if mouse is within candlestick time bounds
                    if candle_left <= x <= candle_right:
                        # Check if mouse is within candlestick price bounds
                        high_price = candle_data['high']
                        low_price = candle_data['low']
                        
                        if low_price <= y <= high_price:
                            # Mouse is within both time and price bounds of this candlestick
                            closest_candle = {
                                'instrument': instrument_key,
                                'candle': candle_data,
                                'x': candle_x,
                                'y': candle_data['close']
                            }
                            return closest_candle  # Return immediately for exact match
                    
                    # If not within bounds, calculate distance for fallback
                    time_diff = abs(x - candle_x_mpl)
                    price_diff = abs(y - candle_data['close'])
                    
                    # Use time difference as primary factor
                    time_weight = 1.0
                    price_weight = 0.001  # Very low weight for price
                    
                    distance = time_diff * time_weight + price_diff * price_weight
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_candle = {
                            'instrument': instrument_key,
                            'candle': candle_data,
                            'x': candle_x,
                            'y': candle_data['close']
                        }
            
            # Only return closest candle if it's very close (within 0.01 days = 14.4 minutes)
            # This ensures tooltip only shows when cursor is very close to a candlestick
            if min_distance < 0.01:  # Within 14.4 minutes
                return closest_candle
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding closest candlestick: {e}")
            return None
    
    def _show_tooltip(self, event, candle_info):
        """Show OHLC data as labels at top and time at bottom"""
        try:
            if not self.price_ax:
                return
            
            candle = candle_info['candle']
            instrument = candle_info['instrument']
            
            # Format timestamp
            timestamp = candle['timestamp']
            if isinstance(timestamp, datetime):
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate diff value (previous candle close - current candle close)
            diff_value = 0
            diff_symbol = "📊"
            
            try:
                # Get the current candle's index in the patches list
                current_instrument = candle_info['instrument']
                patches_list = self.candlestick_patches.get(current_instrument, [])
                
                # Find current candle index
                current_index = -1
                for i, patch_data in enumerate(patches_list):
                    if patch_data['candle_data'] == candle:
                        current_index = i
                        break
                
                # If we found the current candle and there's a previous one
                if current_index > 0:
                    previous_candle = patches_list[current_index - 1]['candle_data']
                    diff_value = candle['close'] - previous_candle['close']
                    diff_symbol = "📈" if diff_value >= 0 else "📉"
                else:
                    # No previous candle, show 0 diff
                    diff_value = 0
                    diff_symbol = "📊"
                    
            except Exception as e:
                # Fallback to close - open if there's an error
                diff_value = candle['close'] - candle['open']
                diff_symbol = "📈" if diff_value >= 0 else "📉"
            
            # Create/update OHLC labels at the top
            self._update_ohlc_labels(candle, diff_value, diff_symbol)
            
            # Create/update time label at the bottom
            self._update_time_label(time_str)
            
            # Force redraw
            if hasattr(self, 'fig') and self.fig:
                self.fig.canvas.draw_idle()
            
        except Exception as e:
            self.logger.error(f"Error showing tooltip: {e}")
    
    def _update_ohlc_labels(self, candle, diff_value, diff_symbol):
        """Update OHLC labels at the top of the chart"""
        try:
            if not self.price_ax:
                return
            
            # Get chart bounds
            xlim = self.price_ax.get_xlim()
            ylim = self.price_ax.get_ylim()
            
            # Clear existing OHLC labels
            for label in self.hover_labels.values():
                if hasattr(label, 'remove'):
                    label.remove()
            self.hover_labels.clear()
            
            # Create OHLC labels at the top
            top_y = ylim[1] - (ylim[1] - ylim[0]) * 0.05  # 5% from top
            
            # Open label
            self.hover_labels['open'] = self.price_ax.text(xlim[0] + (xlim[1] - xlim[0]) * 0.1, top_y, 
                                                          f"O: ₹{candle['open']:.2f}", 
                                                          fontsize=10, fontweight='bold', color='blue',
                                                          bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
            # High label
            self.hover_labels['high'] = self.price_ax.text(xlim[0] + (xlim[1] - xlim[0]) * 0.3, top_y, 
                                                          f"H: ₹{candle['high']:.2f}", 
                                                          fontsize=10, fontweight='bold', color='green',
                                                          bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
            # Low label
            self.hover_labels['low'] = self.price_ax.text(xlim[0] + (xlim[1] - xlim[0]) * 0.5, top_y, 
                                                         f"L: ₹{candle['low']:.2f}", 
                                                         fontsize=10, fontweight='bold', color='red',
                                                         bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
            # Close label
            self.hover_labels['close'] = self.price_ax.text(xlim[0] + (xlim[1] - xlim[0]) * 0.7, top_y, 
                                                           f"C: ₹{candle['close']:.2f}", 
                                                           fontsize=10, fontweight='bold', color='purple',
                                                           bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
            # Diff label
            diff_color = 'green' if diff_value >= 0 else 'red'
            self.hover_labels['diff'] = self.price_ax.text(xlim[0] + (xlim[1] - xlim[0]) * 0.9, top_y, 
                                                          f"{diff_symbol} {diff_value:+.2f}", 
                                                          fontsize=10, fontweight='bold', color=diff_color,
                                                          bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
        except Exception as e:
            self.logger.error(f"Error updating OHLC labels: {e}")
    
    def _update_time_label(self, time_str):
        """Update time label at the bottom of the chart"""
        try:
            if not self.price_ax:
                return
            
            # Get chart bounds
            xlim = self.price_ax.get_xlim()
            ylim = self.price_ax.get_ylim()
            
            # Remove existing time label
            if self.time_label and hasattr(self.time_label, 'remove'):
                self.time_label.remove()
            
            # Create time label at the bottom
            bottom_y = ylim[0] + (ylim[1] - ylim[0]) * 0.05  # 5% from bottom
            center_x = (xlim[0] + xlim[1]) / 2
            
            self.time_label = self.price_ax.text(center_x, bottom_y, time_str, 
                                               fontsize=12, fontweight='bold', color='black',
                                               ha='center', va='bottom',
                                               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.9))
            
        except Exception as e:
            self.logger.error(f"Error updating time label: {e}")
    
    def _hide_hover_labels(self):
        """Hide all hover labels"""
        try:
            # Hide OHLC labels
            for label in self.hover_labels.values():
                if hasattr(label, 'remove'):
                    label.remove()
            self.hover_labels.clear()
            
            # Hide time label
            if self.time_label and hasattr(self.time_label, 'remove'):
                self.time_label.remove()
            self.time_label = None
            
        except Exception as e:
            self.logger.error(f"Error hiding hover labels: {e}")
    
    def _adjust_tooltip_position(self, event):
        """Adjust tooltip position to prevent cutoff at chart edges"""
        try:
            if not self.tooltip_annotation or not self.price_ax:
                return
            
            # Get chart bounds
            xlim = self.price_ax.get_xlim()
            ylim = self.price_ax.get_ylim()
            
            # Get mouse position
            mouse_x = event.xdata
            mouse_y = event.ydata
            
            # Calculate chart dimensions
            chart_width = xlim[1] - xlim[0]
            chart_height = ylim[1] - ylim[0]
            
            # Calculate position as percentage of chart
            x_percent = (mouse_x - xlim[0]) / chart_width
            y_percent = (mouse_y - ylim[0]) / chart_height
            
            # Use larger offsets to ensure tooltip is fully visible
            base_offset = 80  # Increased from 20 to 80 pixels
            
            # Horizontal positioning with more aggressive edge detection
            if x_percent > 0.7:  # Right 30% of chart
                offset_x = -base_offset  # Position to the left
            elif x_percent < 0.3:  # Left 30% of chart
                offset_x = base_offset   # Position to the right
            else:  # Middle 40% of chart
                offset_x = base_offset   # Default to right
            
            # Vertical positioning with more aggressive edge detection
            if y_percent > 0.7:  # Top 30% of chart
                offset_y = -base_offset  # Position below
            elif y_percent < 0.3:  # Bottom 30% of chart
                offset_y = base_offset   # Position above
            else:  # Middle 40% of chart
                offset_y = base_offset   # Default to above
            
            # Update tooltip position
            self.tooltip_annotation.xy = (mouse_x, mouse_y)
            self.tooltip_annotation.xytext = (offset_x, offset_y)
            
        except Exception as e:
            self.logger.error(f"Error adjusting tooltip position: {e}")
    
    def _update_crosshair(self, x, y):
        """Update crosshair position at cursor location"""
        try:
            if not self.price_ax or x is None or y is None:
                return
            
            # Get chart bounds
            xlim = self.price_ax.get_xlim()
            ylim = self.price_ax.get_ylim()
            
            # Create or update vertical line using plot method for better visibility
            if self.crosshair_vline is None or not hasattr(self.crosshair_vline, 'set_xdata'):
                self.crosshair_vline, = self.price_ax.plot([x, x], [ylim[0], ylim[1]], color='darkgrey', linestyle='--', alpha=0.7, linewidth=1)
            else:
                self.crosshair_vline.set_xdata([x, x])
                self.crosshair_vline.set_ydata([ylim[0], ylim[1]])
                self.crosshair_vline.set_visible(True)
            
            # Create or update horizontal line using plot method for better visibility
            if self.crosshair_hline is None or not hasattr(self.crosshair_hline, 'set_ydata'):
                self.crosshair_hline, = self.price_ax.plot([xlim[0], xlim[1]], [y, y], color='darkgrey', linestyle='--', alpha=0.7, linewidth=1)
            else:
                self.crosshair_hline.set_xdata([xlim[0], xlim[1]])
                self.crosshair_hline.set_ydata([y, y])
                self.crosshair_hline.set_visible(True)
            
            # Force redraw to make crosshair visible
            if hasattr(self, 'fig') and self.fig:
                self.fig.canvas.draw_idle()
            
        except Exception as e:
            self.logger.error(f"Error updating crosshair: {e}")
    
    def _hide_crosshair(self):
        """Hide crosshair lines"""
        try:
            if self.crosshair_vline:
                self.crosshair_vline.set_visible(False)
            if self.crosshair_hline:
                self.crosshair_hline.set_visible(False)
        except Exception as e:
            self.logger.error(f"Error hiding crosshair: {e}")
    
    def test_crosshair(self):
        """Test method to create visible crosshair for debugging"""
        try:
            if not self.price_ax:
                self.logger.error("No price axis available for crosshair test")
                return
            
            # Get chart center
            xlim = self.price_ax.get_xlim()
            ylim = self.price_ax.get_ylim()
            center_x = (xlim[0] + xlim[1]) / 2
            center_y = (ylim[0] + ylim[1]) / 2
            
            # Create test crosshair
            self.crosshair_vline, = self.price_ax.plot([center_x, center_x], [ylim[0], ylim[1]], color='darkgrey', linestyle='--', alpha=0.7, linewidth=1)
            self.crosshair_hline, = self.price_ax.plot([xlim[0], xlim[1]], [center_y, center_y], color='darkgrey', linestyle='--', alpha=0.7, linewidth=1)
            
            # Force redraw
            if hasattr(self, 'fig') and self.fig:
                self.fig.canvas.draw_idle()
            
            self.logger.info("Test crosshair created at chart center")
            
        except Exception as e:
            self.logger.error(f"Error creating test crosshair: {e}")
    
    def _get_last_update_time(self):
        """Get the last update time from the tracked update time"""
        try:
            if self.last_update_time:
                # Format as HH:MM:SS
                return self.last_update_time.strftime("%H:%M:%S")
            
            # Fallback: find the most recent timestamp from candle data
            if not self.candle_data:
                return None
            
            latest_timestamp = None
            for instrument_key, candle_list in self.candle_data.items():
                if candle_list:
                    # Get the last candle (most recent)
                    last_candle = candle_list[-1]
                    candle_time = last_candle['timestamp']
                    
                    # Convert to datetime if needed
                    if isinstance(candle_time, datetime):
                        timestamp = candle_time
                    else:
                        timestamp = datetime.fromtimestamp(candle_time)
                    
                    # Ensure timestamp is timezone-naive
                    if timestamp.tzinfo is not None:
                        timestamp = timestamp.replace(tzinfo=None)
                    
                    if latest_timestamp is None or timestamp > latest_timestamp:
                        latest_timestamp = timestamp
            
            if latest_timestamp:
                # Format as HH:MM:SS
                return latest_timestamp.strftime("%H:%M:%S")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting last update time: {e}")
            return None


class TkinterChartApp:
    """Tkinter-based application for the live chart"""
    
    def __init__(self, chart_visualizer):
        self.chart = chart_visualizer
        self.logger = logging.getLogger("TkinterChartApp")
        
        # Chart 2 crosshair functionality
        self.grid2_crosshair_vline = None  # Vertical crosshair line for chart 2
        self.grid2_crosshair_hline = None  # Horizontal crosshair line for chart 2
        
        self.root = tk.Tk()
        self.root.title("Live Market Data Chart - 2x2 Grid Layout")
        
        # Enable standard window controls (minimize, maximize, close)
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        
        # Start in maximized mode
        try:
            # Method 1: Linux/Unix attributes
            self.root.attributes('-zoomed', True)
        except:
            pass
        
        try:
            # Method 2: Windows state (only on Windows)
            import platform
            if platform.system() == "Windows":
                self.root.state('zoomed')
        except:
            pass
        
        # Set up proper window close handling
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)
        
        self.setup_ui()
        
        # Set up keyboard bindings for scrolling
        self.root.bind('<Left>', lambda e: self.scroll_chart_left())
        self.root.bind('<Right>', lambda e: self.scroll_chart_right())
        self.root.bind('<a>', lambda e: self.scroll_chart_left())
        self.root.bind('<d>', lambda e: self.scroll_chart_right())
        
        # Focus the root window to receive key events
        self.root.focus_set()
        
        # Set up status callback for scrolling updates
        self.chart.set_status_callback(self.update_status)
        
        # Set up live data callback for payoff chart updates
        self.chart.set_live_data_callback(self._on_live_data_update)
        
        # Set up window resize handler for responsive grid
        self.root.bind('<Configure>', self._on_window_resize)
        
        # Maximize window after UI is set up
        self.root.after(100, self._maximize_window)
    
    def _maximize_window(self):
        """Maximize the window to current screen only (not spanning multiple monitors)"""
        try:
            # First try standard maximize methods
            try:
                # Method 1: Linux/Unix attributes
                self.root.attributes('-zoomed', True)
                self.logger.info("Window maximized using attributes method")
            except:
                pass
            
            try:
                # Method 2: Windows state (only on Windows)
                import platform
                if platform.system() == "Windows":
                    self.root.state('zoomed')
                    self.logger.info("Window maximized using state method")
            except:
                pass
            
            # Force update the layout
            self.root.update_idletasks()
            
            # Get the actual window size after maximization
            actual_width = self.root.winfo_width()
            actual_height = self.root.winfo_height()
            self.logger.info(f"Window maximized to: {actual_width}x{actual_height}")
            
        except Exception as e:
            self.logger.warning(f"Error maximizing window: {e}")
            # Fallback: try manual geometry setting
            try:
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                max_width = min(screen_width, 1920)
                max_height = min(screen_height, 1080)
                self.root.geometry(f"{max_width}x{max_height}")
                self.logger.info(f"Window set to fallback size: {max_width}x{max_height}")
            except:
                pass
        
        # Force update and raise window
        self.root.update_idletasks()
        self.root.lift()
        self.root.focus_force()
        
        # Trigger a resize event to update the grid layout
        self.root.after(300, self._trigger_resize_update)
    
    def _trigger_resize_update(self):
        """Trigger a resize update after window maximization"""
        try:
            # Force update the layout first
            self.root.update_idletasks()
            
            # Create a fake resize event to trigger the resize handler
            class FakeEvent:
                def __init__(self, widget):
                    self.widget = widget
            
            fake_event = FakeEvent(self.root)
            self._on_window_resize(fake_event)
            
            # Also manually update the grid layout
            self._update_grid_layout()
            
        except Exception as e:
            self.logger.warning(f"Error triggering resize update: {e}")
    
    def _update_grid_layout(self):
        """Manually update the grid layout to ensure proper sizing"""
        try:
            # Force update the layout
            self.root.update_idletasks()
            
            # Update matplotlib figure size to match the container
            if hasattr(self, 'canvas') and self.canvas and hasattr(self, 'grid1_frame'):
                grid1_width = self.grid1_frame.winfo_width()
                grid1_height = self.grid1_frame.winfo_height()
                
                if grid1_width > 50 and grid1_height > 50:
                    # Update the matplotlib figure size
                    dpi = self.chart.fig.get_dpi()
                    fig_width = max(grid1_width / dpi, 4.0)
                    fig_height = max(grid1_height / dpi, 3.0)
                    
                    # Set the figure size
                    self.chart.fig.set_size_inches(fig_width, fig_height)
                    
                    # Ensure proper spacing for rotated labels and combined title
                    if hasattr(self.chart, 'price_ax') and self.chart.price_ax:
                        self.chart.price_ax.margins(x=0.02, y=0.05)
                        self.chart.fig.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.88)
                    
                    # Force the canvas to resize
                    self.canvas.get_tk_widget().configure(width=grid1_width, height=grid1_height)
                    
                    # Redraw the canvas
                    self.canvas.draw_idle()
                    
                    self.logger.info(f"Grid layout updated: {fig_width:.1f}x{fig_height:.1f} inches ({grid1_width}x{grid1_height} pixels)")
            
        except Exception as e:
            self.logger.warning(f"Error updating grid layout: {e}")
    
    def _on_live_data_update(self, instrument_key, price, volume):
        """Handle live data updates for payoff chart refresh with 5-second interval"""
        try:
            import time
            current_time = time.time()
            
            # Get the latest price from datawarehouse to ensure consistency
            datawarehouse_price = None
            if hasattr(self, '_main_app') and self._main_app and hasattr(self._main_app, 'datawarehouse'):
                datawarehouse_price = self._main_app.datawarehouse.get_latest_price(instrument_key)
            
            # Use datawarehouse price if available, otherwise fall back to live feed price
            actual_price = datawarehouse_price if datawarehouse_price is not None else price
            
            # Store the latest live data in the chart's pending data
            if hasattr(self.chart, 'pending_live_data'):
                self.chart.pending_live_data[instrument_key] = {
                    'price': actual_price,
                    'volume': volume,
                    'timestamp': current_time
                }
            
            # Log price source for debugging
            if datawarehouse_price is not None and datawarehouse_price != price:
                self.logger.debug(f"Using datawarehouse price {actual_price} instead of live feed price {price}")
            else:
                self.logger.debug(f"Using live feed price {actual_price}")
            
            # Check if it's time to update Grid 2 (every 5 seconds)
            if hasattr(self.chart, 'last_grid2_update') and hasattr(self.chart, 'grid2_update_interval'):
                if current_time - self.chart.last_grid2_update >= self.chart.grid2_update_interval:
                    self._update_grid2_with_live_data()
                    self.chart.last_grid2_update = current_time
                    self.logger.info(f"Updated Grid 2 with live data: {actual_price}")
                else:
                    # Log that we're storing data for later update
                    remaining_time = self.chart.grid2_update_interval - (current_time - self.chart.last_grid2_update)
                    self.logger.debug(f"Storing live data for {instrument_key}: {actual_price} (Grid 2 update in {remaining_time:.1f}s)")
            else:
                # Fallback: update immediately if interval attributes don't exist
                self._update_grid2_with_live_data()
                self.logger.debug(f"Updated Grid 2 immediately (no interval): {actual_price}")
                
        except Exception as e:
            self.logger.error(f"Error handling live data update for payoff chart: {e}")
    
    def _update_grid2_with_live_data(self):
        """Update Grid 2 with the latest stored live data"""
        try:
            # Check if we have a payoff chart displayed in Grid 2
            if not (hasattr(self, '_current_payoff_data') and self._current_payoff_data):
                return
            
            # Get the latest live data from the chart's pending data
            if not hasattr(self.chart, 'pending_live_data') or not self.chart.pending_live_data:
                return
                
            # Find the most recent data (use the first available instrument)
            latest_data = None
            primary_instrument = list(self._main_app.instruments[self._main_app.broker_type].keys())[0]
            for instrument_key, data in self.chart.pending_live_data.items():
                if instrument_key == primary_instrument:
                    if latest_data is None or data['timestamp'] > latest_data['timestamp']:
                        latest_data = data
            
            if latest_data:
                # Update the payoff chart with new spot price
                self._update_payoff_chart_spot_price(latest_data['price'])
                self.logger.debug(f"Updated Grid 2 with live data: {latest_data['price']}")
                
        except Exception as e:
            self.logger.error(f"Error updating Grid 2 with live data: {e}")
    
    def _update_payoff_chart_spot_price(self, new_spot_price):
        """Update the payoff chart with new spot price"""
        try:
            if not hasattr(self, '_current_payoff_data') or not self._current_payoff_data:
                return
                
            # Check if Grid 2 has a matplotlib figure
            if not hasattr(self, 'grid2_fig') or not self.grid2_fig:
                return
                
            # Update the spot price line in the chart
            ax = self.grid2_fig.axes[0] if self.grid2_fig.axes else None
            if ax:
                # Remove any existing spot price lines and create a new one
                # Get current y-limits BEFORE removing any lines to preserve them
                original_ylim = ax.get_ylim()
                
                # Find and remove existing spot price lines and text
                lines_to_remove = []
                texts_to_remove = []
                
                # Find lines to remove (spot price lines)
                # Look for red dashed lines (our spot price lines)
                for line in ax.lines:
                    try:
                        # Check if this is a red dashed line (our spot price line)
                        # Either by label or by visual properties
                        line_label = getattr(line, '_label', '') or ''
                        is_spot_line_by_label = 'Current Spot' in str(line_label)
                        is_spot_line_by_props = (hasattr(line, 'get_color') and line.get_color() == 'red' and
                                               hasattr(line, 'get_linestyle') and line.get_linestyle() == '--' and
                                               hasattr(line, 'get_linewidth') and line.get_linewidth() == 2)
                        
                        if is_spot_line_by_label or is_spot_line_by_props:
                            lines_to_remove.append(line)
                    except Exception:
                        # Skip if we can't get line properties
                        pass
                
                # Remove the old spot price lines
                for line in lines_to_remove:
                    try:
                        line.remove()
                    except Exception:
                        # Ignore errors when removing lines
                        pass
                
                # Remove existing spot price text objects (to avoid duplicates)
                # Only remove text objects that look like spot price values (numeric) and are positioned near the spot price
                texts_to_remove = []
                for text in ax.texts[:]:  # Create a copy to avoid modification during iteration
                    try:
                        # Check if text object is still valid
                        if hasattr(text, 'get_text') and hasattr(text, 'remove'):
                            text_content = str(text.get_text())
                            # Check if this looks like a spot price (numeric value) and is positioned near the spot price line
                            if (text_content.replace('.', '').replace('-', '').isdigit() and 
                                hasattr(text, 'get_position')):
                                text_pos = text.get_position()
                                # Only remove if it's close to the spot price line (within 50 points)
                                if abs(text_pos[0] - new_spot_price) < 50:
                                    texts_to_remove.append(text)
                    except Exception:
                        # Skip if we can't get text content or text is invalid
                        pass
                
                for text in texts_to_remove:
                    try:
                        if hasattr(text, 'remove'):
                            text.remove()
                    except Exception:
                        # Ignore errors when removing text objects
                        pass
                
                # Create a new spot price line using the original y-limits
                ax.plot([new_spot_price, new_spot_price], [original_ylim[0], original_ylim[1]], 
                       color='red', linestyle='--', linewidth=2, label='Current Spot')
                
                # Add/update spot price text near x-axis
                try:
                    text_y_position = original_ylim[0] + (original_ylim[1] - original_ylim[0]) * 0.05
                    text_obj = ax.text(new_spot_price, text_y_position, f'{new_spot_price}', 
                                     ha='center', va='bottom', fontsize=10, fontweight='bold', 
                                     bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
                    
                    # Ensure the text object is properly associated with the figure
                    if hasattr(text_obj, 'set_figure'):
                        text_obj.set_figure(ax.get_figure())
                        
                except Exception as e:
                    self.logger.warning(f"Could not add spot price text: {e}")
                
                # Restore the original y-limits to prevent axis expansion
                ax.set_ylim(original_ylim)
                
                # Preserve X-axis ticks at strike prices
                if hasattr(self, 'current_trade') and self.current_trade:
                    strikes = [leg.strike_price for leg in self.current_trade.legs]
                    ax.set_xticks(strikes)
                    ax.set_xticklabels([f'{strike}' for strike in strikes], rotation=45, ha='right')
                
                # Force chart refresh
                self.grid2_fig.canvas.draw()
                self.grid2_fig.canvas.flush_events()
                
                # Update the current spot price
                self._current_spot_price = new_spot_price
                
                self.logger.debug(f"Updated payoff chart spot price to: {new_spot_price}")
                
        except Exception as e:
            self.logger.error(f"Error updating payoff chart spot price: {e}")
        
    def setup_ui(self):
        """Set up the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Toolbar frame
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Toolbar buttons
        self.settings_button = ttk.Button(toolbar_frame, text="Settings", 
                                        command=self._show_settings_window)
        self.settings_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.trade_book_button = ttk.Button(toolbar_frame, text="Trade Book", 
                                          command=self._show_trade_book_window)
        self.trade_book_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.check_positions_button = ttk.Button(toolbar_frame, text="Check Positions", 
                                               command=self._check_positions)
        self.check_positions_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.info_button = ttk.Button(toolbar_frame, text="Info", 
                                    command=self._show_info_window)
        self.info_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Control frame (minimal - only status label)
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status label only
        self.status_label = ttk.Label(control_frame, text="Status: Running", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Grid frame for 2x2 layout
        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for equal distribution
        grid_frame.grid_rowconfigure(0, weight=1, uniform="row")
        grid_frame.grid_rowconfigure(1, weight=1, uniform="row")
        grid_frame.grid_columnconfigure(0, weight=1, uniform="col")
        grid_frame.grid_columnconfigure(1, weight=1, uniform="col")
        
        # Grid 1 (Top-Left): Intraday Price Chart
        self.grid1_frame = ttk.LabelFrame(grid_frame, text="Intraday Price Chart", padding=5)
        self.grid1_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.grid1_frame.grid_rowconfigure(0, weight=1)
        self.grid1_frame.grid_columnconfigure(0, weight=1)
        
        # Embed matplotlib figure in grid 1
        self.canvas = FigureCanvasTkAgg(self.chart.fig, self.grid1_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        
        # Set up tooltips for candlestick hover
        self.chart._setup_tooltips()
        
        # Grid 2 (Top-Right): Strategy Display
        self.grid2_frame = ttk.LabelFrame(grid_frame, text="Strategy Display", padding=5)
        self.grid2_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.grid2_frame.grid_rowconfigure(0, weight=1)
        self.grid2_frame.grid_columnconfigure(0, weight=1)
        
        # Add initial content to grid 2
        self._initialize_grid2_content()
        
        # Grid 3 (Bottom-Left): Placeholder for future use
        self.grid3_frame = ttk.LabelFrame(grid_frame, text="Grid 3 - Available", padding=5)
        self.grid3_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.grid3_frame.grid_rowconfigure(0, weight=1)
        self.grid3_frame.grid_columnconfigure(0, weight=1)
        
        # Add placeholder content to grid 3
        placeholder3 = ttk.Label(self.grid3_frame, text="Available for future charts\nor data displays", 
                               justify="center", font=("Arial", 12))
        placeholder3.grid(row=0, column=0, sticky="nsew")
        
        # Grid 4 (Bottom-Right): Placeholder for future use
        self.grid4_frame = ttk.LabelFrame(grid_frame, text="Grid 4 - Available", padding=5)
        self.grid4_frame.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)
        self.grid4_frame.grid_rowconfigure(0, weight=1)
        self.grid4_frame.grid_columnconfigure(0, weight=1)
        
        # Add placeholder content to grid 4
        placeholder4 = ttk.Label(self.grid4_frame, text="Available for future charts\nor data displays", 
                               justify="center", font=("Arial", 12))
        placeholder4.grid(row=0, column=0, sticky="nsew")
    
    def _initialize_grid2_content(self):
        """Initialize Grid 2 with default content"""
        try:
            # Clear any existing content
            for widget in self.grid2_frame.winfo_children():
                widget.destroy()
            
            # Create a main container frame for all content
            main_container = ttk.Frame(self.grid2_frame)
            main_container.pack(fill=tk.BOTH, expand=True)
            
            # Header frame with title and Trade All button
            header_frame = ttk.Frame(main_container)
            header_frame.pack(fill=tk.X, pady=(10, 5))
            
            # Title
            title_label = ttk.Label(header_frame, text="Strategy Display", 
                                  font=("Arial", 14, "bold"))
            title_label.pack(side=tk.LEFT)
            
            # Trade All button (top right)
            self.trade_all_button = ttk.Button(header_frame, text="Trade All", 
                                             command=self._show_trade_all_window,
                                             state="disabled")  # Initially disabled
            self.trade_all_button.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Content frame for charts and messages
            self.content_frame = ttk.Frame(main_container)
            self.content_frame.pack(fill=tk.BOTH, expand=True)
            
            # Initial state message
            initial_label = ttk.Label(self.content_frame, 
                                    text="No active strategies\nUse 'Manage Strategies' to create or view strategies", 
                                    font=("Arial", 12),
                                    foreground="gray",
                                    justify="center")
            initial_label.pack(pady=20)
            
            # Last updated
            last_updated = datetime.now().strftime("%H:%M:%S")
            update_label = ttk.Label(self.content_frame, 
                                   text=f"Initialized: {last_updated}", 
                                   font=("Arial", 8), 
                                   foreground="gray")
            update_label.pack(pady=(10, 5))
            
        except Exception as e:
            print(f"Error initializing Grid 2 content: {e}")
    
    def display_trade_payoff_graph(self, trades, spot_price, strategy_manager=None):
        """Display trade payoff chart in Grid 2 for single or multiple trades"""
        try:
            # Handle both single trade and list of trades
            if not isinstance(trades, list):
                trades = [trades]
            
            # Store trade reference for later use in updates
            self.current_trades = trades
            
            # Clear any existing content
            for widget in self.grid2_frame.winfo_children():
                widget.destroy()
            
            # Calculate payoff data using strategy manager
            if strategy_manager is None:
                self.logger.error("Strategy manager not provided for payoff calculation")
                self.display_error_message("Strategy manager not available")
                return
            
            if len(trades) > 0:
                # Single trade - use existing method
                payoff_data = strategy_manager.calculate_trade_payoff(trades[0], spot_price)
            else:
                # Multiple trades - use combined method
                payoff_data = strategy_manager.calculate_combined_trades_payoff(trades, spot_price)
                # Check if any trades are open
            
            open_trades = [t for t in trades if t.status.value == "OPEN"]
            if open_trades:
                chart_title = f"Open Trades - {open_trades[0].trade_id}"
            else:
                chart_title = "Strategy To Trade"

            if not payoff_data:
                self.logger.error("Failed to calculate payoff data")
                self.display_error_message("Failed to calculate payoff data")
                return
            
            # Header frame with title and Trade All button
            header_frame = ttk.Frame(self.grid2_frame)
            header_frame.pack(fill=tk.X, pady=(10, 5))
            
            # Title (left aligned)
            title_label = ttk.Label(header_frame, text=chart_title, 
                                  font=("Arial", 14, "bold"))
            title_label.pack(side=tk.LEFT)
            
            # Positions button (small square with positions icon)
            positions_icon = "📊"  # Chart/positions emoji/unicode character
            self.positions_button = ttk.Button(header_frame, text=positions_icon, 
                                             command=self._show_positions_window,
                                             width=3)  # Small square button
            self.positions_button.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Chain button (small square with chain icon)
            chain_icon = "⛓"  # Chain emoji/unicode character
            self.chain_button = ttk.Button(header_frame, text=chain_icon, 
                                             command=self._show_chain_window,
                                             width=3)  # Small square button
            self.chain_button.pack(side=tk.RIGHT, padx=(5, 0))


            # Buttons (right aligned) - only show for single trade with no open trades
            if len(trades) == 0:                
                # Trade All button
                self.trade_all_button = ttk.Button(header_frame, text="Trade All", 
                                                 command=self._show_trade_all_window,
                                                 state="normal")  # Enabled when strategy is displayed
                self.trade_all_button.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Create matplotlib figure for Iron Condor
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import matplotlib.pyplot as plt
            
            # Create figure with responsive size based on grid2 frame
            try:
                grid2_width = self.grid2_frame.winfo_width()
                grid2_height = self.grid2_frame.winfo_height()
                
                if grid2_width > 50 and grid2_height > 50:
                    # Calculate figure size based on grid dimensions
                    dpi = 100  # Default DPI
                    fig_width = max(grid2_width / dpi, 8.0)  # Minimum 8 inches
                    fig_height = max(grid2_height / dpi, 6.0)  # Minimum 6 inches
                else:
                    # Fallback to larger default size
                    fig_width, fig_height = 10.0, 7.0
            except:
                # Fallback to larger default size
                fig_width, fig_height = 10.0, 7.0
            
            fig, ax = plt.subplots(figsize=(fig_width, fig_height))
            
            # Adjust subplot to ensure x-axis is visible with more bottom space
            plt.subplots_adjust(bottom=0.20, left=0.1, right=0.95, top=0.95)
            
            # Plot payoff curve
            ax.plot(payoff_data["price_range"], payoff_data["payoffs"], 
                   'b-', linewidth=2)
            
            # Mark current spot price (using plot for easier updates)
            ylim = ax.get_ylim()
            ax.plot([spot_price, spot_price], [ylim[0], ylim[1]], 
                   color='red', linestyle='--', linewidth=2, label='Current Spot')
            
            # Add spot price text near x-axis
            try:
                text_obj = ax.text(spot_price, ylim[0] + (ylim[1] - ylim[0]) * 0.05, f'{spot_price}', 
                                 ha='center', va='bottom', fontsize=10, fontweight='bold', 
                                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
                
                # Ensure the text object is properly associated with the figure
                if hasattr(text_obj, 'set_figure'):
                    text_obj.set_figure(ax.get_figure())
                    
            except Exception as e:
                self.logger.warning(f"Could not add initial spot price text: {e}")
            
            # Mark strikes - collect all strikes from all trades
            all_strikes = []
            for trade in trades:
                for leg in trade.legs:
                    all_strikes.append(leg.strike_price)
            
            # Remove duplicates and sort
            unique_strikes = sorted(list(set(all_strikes)))
            
            # Only show strikes if there are not too many (avoid clutter)
            if len(unique_strikes) <= 10:
                for strike in unique_strikes:
                    ax.axvline(x=strike, color='gray', linestyle=':', alpha=0.7)
                
                # Set X-axis ticks at strike prices
                ax.set_xticks(unique_strikes)
                ax.set_xticklabels([f'{strike}' for strike in unique_strikes], rotation=45, ha='right')
            else:
                # Too many strikes - just show a few key ones
                key_strikes = [unique_strikes[0], unique_strikes[len(unique_strikes)//2], unique_strikes[-1]]
                for strike in key_strikes:
                    ax.axvline(x=strike, color='gray', linestyle=':', alpha=0.7)
                ax.set_xticks(key_strikes)
                ax.set_xticklabels([f'{strike}' for strike in key_strikes], rotation=45, ha='right')
            
            # Breakeven points are now only shown in the strategy details text
            
            # Add horizontal line at zero profit/loss (without label)
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
            
            # Formatting
            ax.set_xlabel('NIFTY Price at Expiry')
            ax.set_ylabel('Profit/Loss (₹)')
            ax.grid(True, alpha=0.3)
            # Legend removed as requested
            
            # Add color filling for profit/loss zones (only in chart area)
            # Use the actual data range instead of full chart limits
            price_range = payoff_data["price_range"]
            payoffs = payoff_data["payoffs"]
            
            # Convert to numpy arrays for proper comparison
            import numpy as np
            price_range = np.array(price_range)
            payoffs = np.array(payoffs)
            
            # Fill area above zero with green (profit zone) - only where data exists
            ax.fill_between(price_range, 0, payoffs, where=(payoffs >= 0), 
                           color='green', alpha=0.1)
            
            # Fill area below zero with red (loss zone) - only where data exists
            ax.fill_between(price_range, payoffs, 0, where=(payoffs < 0), 
                           color='red', alpha=0.1)
            
            # Calculate risk reward ratio for initial display
            max_profit = payoff_data["max_profit"]
            max_loss = abs(payoff_data["max_loss"])
            risk_reward_ratio = max_loss / max_profit if max_profit > 0 else 0
            
            # Add strategy details text box (will be updated on hover)
            if len(trades) == 1:
                # Single trade details
                trade = trades[0]
                strikes = [leg.strike_price for leg in trade.legs]
                initial_strategy_text = f"""Strategy Details:
Trade: {trade.trade_id}
Strikes: {sorted(strikes)}
Max Profit: ₹{max_profit:.0f}
Max Loss: ₹{payoff_data["max_loss"]:.0f}
Risk:Reward Ratio: {risk_reward_ratio:.2f}
Current P&L: ₹{payoff_data["current_payoff"]:.0f}"""
            else:
                # Multiple trades details
                initial_strategy_text = f"""Portfolio Details:
Trades: {len(trades)}
Total Legs: {payoff_data.get("total_legs", 0)}
Max Profit: ₹{max_profit:.0f}
Max Loss: ₹{payoff_data["max_loss"]:.0f}
Risk:Reward Ratio: {risk_reward_ratio:.2f}
Current P&L: ₹{payoff_data["current_payoff"]:.0f}"""
            
            strategy_text_obj = ax.text(0.02, 0.98, initial_strategy_text, transform=ax.transAxes,
                   verticalalignment='top', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            
            # Add hover functionality to update existing strategy details
            if len(trades) == 1:
                self._add_hover_update(fig, ax, trades[0], payoff_data, spot_price, strategy_text_obj)
            else:
                # For multiple trades, use a simpler hover or skip it
                self.logger.info("Hover functionality not implemented for multiple trades yet")
            
            # Store data for live updates
            self._current_payoff_data = payoff_data
            self._current_spot_price = spot_price
            self.grid2_fig = fig
            
            # Embed in grid 2
            canvas = FigureCanvasTkAgg(fig, self.grid2_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Add trade info below chart
            info_frame = ttk.Frame(self.grid2_frame)
            info_frame.pack(fill=tk.X, pady=(5, 0))
            
            if len(trades) == 1:
                trade = trades[0]
                trade_info = ttk.Label(info_frame, 
                                     text=f"Trade: {trade.trade_id} | Status: {trade.status.value}",
                                     font=("Arial", 8))
                trade_info.pack()
                self.logger.info(f"Displayed strategy in Grid 2: {trade.trade_id}")
            else:
                # Show summary for multiple trades
                trade_ids = [trade.trade_id for trade in trades]
                trade_info = ttk.Label(info_frame, 
                                     text=f"Portfolio: {len(trades)} trades | IDs: {', '.join(trade_ids[:3])}{'...' if len(trade_ids) > 3 else ''}",
                                     font=("Arial", 8))
                trade_info.pack()
                self.logger.info(f"Displayed portfolio in Grid 2: {len(trades)} trades")
            
        except Exception as e:
            self.logger.error(f"Error displaying Iron Condor strategy: {e}")
            # Fallback to error message
            error_label = ttk.Label(self.grid2_frame, 
                                  text=f"Error displaying strategy: {e}",
                                  font=("Arial", 10),
                                  foreground="red")
            error_label.pack(pady=20)
    
    def clear_grid2(self):
        """Clear Grid 2 and reset to default content"""
        try:
            # Clear any existing content
            for widget in self.grid2_frame.winfo_children():
                widget.destroy()
            
            # Reset to default content
            self._initialize_grid2_content()
            
        except Exception as e:
            self.logger.error(f"Error clearing Grid 2: {e}")
        
    def display_error_message(self, error_message):
        """Display error message in Grid 2"""
        try:
            # Clear any existing content
            for widget in self.grid2_frame.winfo_children():
                widget.destroy()
            
            # Create error display
            error_frame = ttk.Frame(self.grid2_frame)
            error_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
            
            # Error icon (using text symbol)
            error_icon = ttk.Label(error_frame, text="⚠️", font=("Arial", 48))
            error_icon.pack(pady=(20, 10))
            
            # Error title
            error_title = ttk.Label(error_frame, text="Strategy Creation Failed", 
                                  font=("Arial", 16, "bold"), foreground="red")
            error_title.pack(pady=(0, 10))
            
            # Error message
            error_text = ttk.Label(error_frame, text=error_message, 
                                 font=("Arial", 10), foreground="darkred",
                                 wraplength=400, justify=tk.CENTER)
            error_text.pack(pady=(0, 20))
            
            # Instructions
            instructions = ttk.Label(error_frame, 
                                   text="Please check your connection and try again.",
                                   font=("Arial", 9), foreground="gray")
            instructions.pack()
            
            self.logger.info(f"Displayed error message in Grid 2: {error_message}")
            
        except Exception as e:
            self.logger.error(f"Error displaying error message: {e}")
    
    def _clear_grid2(self):
        """Clear Grid 2 content"""
        try:
            # Clear any existing content
            for widget in self.grid2_frame.winfo_children():
                widget.destroy()
        except Exception as e:
            self.logger.error(f"Error clearing Grid 2: {e}")
    
    def _clear_grid2_chart(self):
        """Clear Grid 2 chart content (for matplotlib plots)"""
        try:
            # Clear content frame if it exists
            if hasattr(self, 'content_frame'):
                try:
                    for widget in self.content_frame.winfo_children():
                        widget.destroy()
                except Exception as content_error:
                    self.logger.warning(f"Error clearing content frame: {content_error}")
            else:
                # Fallback: clear all widgets in grid2_frame
                try:
                    for widget in self.grid2_frame.winfo_children():
                        widget.destroy()
                except Exception as grid_error:
                    self.logger.warning(f"Error clearing grid2_frame: {grid_error}")
            
            # Reset canvas references
            if hasattr(self, 'grid2_canvas'):
                delattr(self, 'grid2_canvas')
            if hasattr(self, 'grid2_fig'):
                delattr(self, 'grid2_fig')
            if hasattr(self, 'grid2_ax'):
                delattr(self, 'grid2_ax')
            
            # Ensure grid2_frame is properly configured
            self.grid2_frame.grid_rowconfigure(0, weight=1)
            self.grid2_frame.grid_columnconfigure(0, weight=1)
                
            # Force update the frame to ensure it's visible
            self.grid2_frame.update_idletasks()
            
        except Exception as e:
            self.logger.error(f"Error clearing Grid 2 chart: {e}")
    
    def _initialize_grid2_axes(self):
        """Initialize Grid 2 matplotlib axes if they don't exist"""
        try:
            self.logger.info("_initialize_grid2_axes called")
            
            if not hasattr(self, 'grid2_ax') or self.grid2_ax is None:
                self.logger.info("Creating new matplotlib axes for Grid 2")
                
                # Create matplotlib figure and axes for Grid 2
                import matplotlib.pyplot as plt
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                
                # Create figure for Grid 2 with responsive size
                try:
                    grid2_width = self.grid2_frame.winfo_width()
                    grid2_height = self.grid2_frame.winfo_height()
                    
                    if grid2_width > 50 and grid2_height > 50:
                        # Calculate figure size based on grid dimensions
                        dpi = 100  # Default DPI
                        fig_width = max(grid2_width / dpi, 8.0)  # Minimum 8 inches
                        fig_height = max(grid2_height / dpi, 6.0)  # Minimum 6 inches
                    else:
                        # Fallback to larger default size
                        fig_width, fig_height = 10.0, 7.0
                except:
                    # Fallback to larger default size
                    fig_width, fig_height = 10.0, 7.0
                
                self.grid2_fig, self.grid2_ax = plt.subplots(figsize=(fig_width, fig_height))
                
                # Adjust subplot to ensure x-axis is visible with more bottom space
                plt.subplots_adjust(bottom=0.20, left=0.1, right=0.95, top=0.95)
                
                # Create canvas and add to content frame (or grid2_frame as fallback)
                target_frame = self.content_frame if hasattr(self, 'content_frame') else self.grid2_frame
                self.grid2_canvas = FigureCanvasTkAgg(self.grid2_fig, target_frame)
                canvas_widget = self.grid2_canvas.get_tk_widget()
                canvas_widget.pack(fill=tk.BOTH, expand=True)
                
                self.logger.info(f"Canvas widget packed in {target_frame}: {canvas_widget}")
                
                # Set initial properties
                self.grid2_ax.set_xlim(0, 1)
                self.grid2_ax.set_ylim(0, 1)
                self.grid2_ax.set_xticks([])
                self.grid2_ax.set_yticks([])
                self.grid2_ax.set_title("")
                
                # Force update to ensure visibility
                self.grid2_frame.update_idletasks()
                self.grid2_canvas.draw()
                
                self.logger.info("Successfully initialized Grid 2 matplotlib axes and canvas")
            else:
                self.logger.info("Grid 2 axes already exist, skipping initialization")
                
        except Exception as e:
            self.logger.error(f"Error initializing Grid 2 axes: {e}")
            import traceback
            traceback.print_exc()
    
    # def display_open_trades_payoff(self, open_trades, spot_price):
    #     """Display payoff charts for open trades"""
    #     try:
    #         from trade_models import PositionType, OptionType
    #         import numpy as np
            
    #         self.logger.info(f"display_open_trades_payoff called with {len(open_trades)} trades, spot_price: {spot_price}")
            
    #         # Clear Grid 2 chart
    #         self._clear_grid2_chart()
            
    #         # Ensure axes are initialized
    #         self._initialize_grid2_axes()
            
    #         if not open_trades:
    #             self.logger.warning("No open trades provided to display_open_trades_payoff")
    #             self.display_error_message("No open trades to display")
    #             return
            
    #         # Calculate combined payoff for all open trades
    #         price_range = np.linspace(spot_price * 0.8, spot_price * 1.2, 100)
    #         total_payoff = np.zeros_like(price_range)
            
    #         self.logger.info(f"Calculating payoff for price range: {price_range[0]:.0f} to {price_range[-1]:.0f}")
            
    #         trade_details = []
            
    #         for trade in open_trades:
    #             trade_payoff = np.zeros_like(price_range)
    #             trade_info = {
    #                 'trade_id': trade.trade_id,
    #                 'strategy': trade.strategy_name,
    #                 'legs': []
    #             }
                
    #             for leg in trade.legs:
    #                 if leg.entry_price is not None:
    #                     # Calculate payoff for this leg
    #                     if leg.position_type == PositionType.LONG:
    #                         if leg.option_type == OptionType.CALL:
    #                             # Long Call: max(0, S - K) - premium
    #                             leg_payoff = np.maximum(0, price_range - leg.strike_price) - leg.entry_price
    #                         else:  # PUT
    #                             # Long Put: max(0, K - S) - premium
    #                             leg_payoff = np.maximum(0, leg.strike_price - price_range) - leg.entry_price
    #                     else:  # SHORT
    #                         if leg.option_type == OptionType.CALL:
    #                             # Short Call: premium - max(0, S - K)
    #                             leg_payoff = leg.entry_price - np.maximum(0, price_range - leg.strike_price)
    #                         else:  # PUT
    #                             # Short Put: premium - max(0, K - S)
    #                             leg_payoff = leg.entry_price - np.maximum(0, leg.strike_price - price_range)
                        
    #                     # Multiply by quantity
    #                     leg_payoff *= leg.quantity
    #                     trade_payoff += leg_payoff
                        
    #                     trade_info['legs'].append({
    #                         'type': leg.option_type.value,
    #                         'position': leg.position_type.value,
    #                         'strike': leg.strike_price,
    #                         'quantity': leg.quantity,
    #                         'entry_price': leg.entry_price
    #                     })
                
    #             total_payoff += trade_payoff
    #             trade_details.append(trade_info)
            
    #         # Plot the combined payoff
    #         self.grid2_ax.plot(price_range, total_payoff, 'b-', linewidth=2, label='Total Payoff')
            
    #         # Add zero line
    #         self.grid2_ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
            
    #         # Add current spot price line
    #         self.grid2_ax.axvline(x=spot_price, color='red', linestyle=':', alpha=0.7, label=f'Current Spot: ₹{spot_price:.0f}')
            
    #         # Fill areas above and below zero
    #         self.grid2_ax.fill_between(price_range, total_payoff, 0, 
    #                                  where=(total_payoff >= 0), 
    #                                  color='green', alpha=0.3, label='Profit Zone')
    #         self.grid2_ax.fill_between(price_range, total_payoff, 0, 
    #                                  where=(total_payoff < 0), 
    #                                  color='red', alpha=0.3, label='Loss Zone')
            
    #         # Set labels and title
    #         self.grid2_ax.set_xlabel('Underlying Price (₹)', fontsize=12)
    #         self.grid2_ax.set_ylabel('Profit/Loss (₹)', fontsize=12)
    #         self.grid2_ax.set_title(f'Open Trades Payoff - {len(open_trades)} Trades', fontsize=14, fontweight='bold')
            
    #         # Add legend
    #         # self.grid2_ax.legend(loc='upper left')
            
    #         # Format axes
    #         # self.grid2_ax.grid(True, alpha=0.3)
            
    #         # Store trade details for hover functionality
    #         self._current_open_trades = trade_details
    #         self._current_spot_price = spot_price
            
    #         # Store data for live updates
    #         self._current_payoff_data = {
    #             "price_range": price_range,
    #             "payoffs": total_payoff
    #         }
    #         self.grid2_fig = self.grid2_ax.figure if hasattr(self, 'grid2_ax') else None
            
    #         # Add hover functionality
    #         self._add_open_trades_hover()
            
    #         # Refresh the chart
    #         self.logger.info("Refreshing chart display...")
    #         try:
    #             if hasattr(self, 'grid2_canvas') and self.grid2_canvas is not None:
    #                 self.logger.info("Using grid2_canvas for refresh")
    #                 self.grid2_canvas.draw()
    #                 # Force update the canvas
    #                 self.grid2_canvas.flush_events()
    #                 self.logger.info("Grid2 canvas refreshed and flushed")
    #             else:
    #                 self.logger.info("Using main canvas for refresh")
    #                 self.canvas.draw()
    #         except Exception as refresh_error:
    #             self.logger.error(f"Error refreshing canvas: {refresh_error}")
    #             # Try to reinitialize the canvas
    #             try:
    #                 self._initialize_grid2_axes()
    #                 if hasattr(self, 'grid2_canvas') and self.grid2_canvas is not None:
    #                     self.grid2_canvas.draw()
    #                     self.logger.info("Canvas reinitialized and refreshed")
    #             except Exception as reinit_error:
    #                 self.logger.error(f"Error reinitializing canvas: {reinit_error}")
            
    #         # Force update the frame
    #         self.grid2_frame.update_idletasks()
            
    #         # Additional debugging
    #         try:
    #             if hasattr(self, 'grid2_canvas') and self.grid2_canvas is not None:
    #                 canvas_widget = self.grid2_canvas.get_tk_widget()
    #                 self.logger.info(f"Canvas widget visible: {canvas_widget.winfo_viewable()}")
    #                 self.logger.info(f"Canvas widget size: {canvas_widget.winfo_width()}x{canvas_widget.winfo_height()}")
    #                 self.logger.info(f"Grid2 frame size: {self.grid2_frame.winfo_width()}x{self.grid2_frame.winfo_height()}")
    #         except Exception as debug_error:
    #             self.logger.warning(f"Error in debug logging: {debug_error}")
            
    #         self.logger.info(f"Successfully displayed open trades payoff for {len(open_trades)} trades")
            
    #     except Exception as e:
    #         self.logger.error(f"Error displaying open trades payoff: {e}")
    #         self.display_error_message(f"Failed to display open trades payoff: {e}")
    
    def _add_open_trades_hover(self):
        """Add hover functionality for open trades payoff chart"""
        try:
            if hasattr(self, '_open_trades_hover_connection'):
                self.canvas.mpl_disconnect(self._open_trades_hover_connection)
            
            def on_hover(event):
                if event.inaxes == self.grid2_ax:
                    if hasattr(self, '_current_open_trades') and self._current_open_trades:
                        # Get price at cursor
                        price = event.xdata
                        if price is not None:
                            # Calculate total payoff at this price
                            total_payoff = 0
                            trade_summary = []
                            
                            for trade in self._current_open_trades:
                                trade_payoff = 0
                                for leg in trade['legs']:
                                    if leg['position'] == 'LONG':
                                        if leg['type'] == 'CALL':
                                            leg_payoff = max(0, price - leg['strike']) - leg['entry_price']
                                        else:  # PUT
                                            leg_payoff = max(0, leg['strike'] - price) - leg['entry_price']
                                    else:  # SHORT
                                        if leg['type'] == 'CALL':
                                            leg_payoff = leg['entry_price'] - max(0, price - leg['strike'])
                                        else:  # PUT
                                            leg_payoff = leg['entry_price'] - max(0, leg['strike'] - price)
                                    
                                    leg_payoff *= leg['quantity']
                                    trade_payoff += leg_payoff
                                
                                total_payoff += trade_payoff
                                trade_summary.append(f"{trade['strategy']}: ₹{trade_payoff:.0f}")
                            
                            # Update tooltip
                            tooltip_text = f"Price: ₹{price:.0f}\nTotal P&L: ₹{total_payoff:.0f}\n\nTrades:\n" + "\n".join(trade_summary)
                            
                            # Remove existing tooltip
                            if hasattr(self, '_open_trades_tooltip'):
                                self._open_trades_tooltip.remove()
                            
                            # Add new tooltip
                            self._open_trades_tooltip = self.grid2_ax.text(0.02, 0.98, tooltip_text,
                                                                        transform=self.grid2_ax.transAxes,
                                                                        fontsize=9, verticalalignment='top',
                                                                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9))
                            if hasattr(self, 'grid2_canvas'):
                                self.grid2_canvas.draw_idle()
                            else:
                                self.canvas.draw_idle()
            
            canvas_to_use = self.grid2_canvas if hasattr(self, 'grid2_canvas') else self.canvas
            self._open_trades_hover_connection = canvas_to_use.mpl_connect('motion_notify_event', on_hover)
            
        except Exception as e:
            self.logger.error(f"Error adding open trades hover functionality: {e}")
    
    def _refresh_chart_display(self):
        self._main_app._display_appropriate_chart()
    
    def _add_hover_update(self, fig, ax, trade, payoff_data, spot_price, strategy_text_obj):
        """Add hover functionality to update existing strategy details text"""
        try:
            # Store trade data and text object for updates
            self._current_trade = trade
            self._current_payoff_data = payoff_data
            self._current_spot_price = spot_price
            self._strategy_text_obj = strategy_text_obj
            
            # Store original text for when mouse leaves chart
            self._original_strategy_text = strategy_text_obj.get_text()
            
            def hover(event):
                """Handle mouse hover events"""
                if event.inaxes != ax:
                    # Mouse left chart area, restore original text and hide crosshair
                    self._strategy_text_obj.set_text(self._original_strategy_text)
                    self._hide_grid2_crosshair()
                    fig.canvas.draw_idle()
                    return
                
                if event.xdata is None or event.ydata is None:
                    # Invalid data, restore original text and hide crosshair
                    self._strategy_text_obj.set_text(self._original_strategy_text)
                    self._hide_grid2_crosshair()
                    fig.canvas.draw_idle()
                    return
                
                # Get hover position
                hover_price = event.xdata
                hover_payoff = event.ydata
                
                # Update crosshair position
                self._update_grid2_crosshair(hover_price, hover_payoff, ax)
                
                # Find the closest point on the payoff curve
                price_range = payoff_data["price_range"]
                payoffs = payoff_data["payoffs"]
                
                # Find closest index
                closest_idx = min(range(len(price_range)), 
                                key=lambda i: abs(price_range[i] - hover_price))
                
                closest_price = price_range[closest_idx]
                closest_payoff = payoffs[closest_idx]
                
                # Get strategy details for this price
                strategy_details = self._get_strategy_details_at_price(closest_price, closest_payoff)
                
                # Update the existing text box
                self._strategy_text_obj.set_text(strategy_details)
                fig.canvas.draw_idle()
            
            # Connect hover event
            fig.canvas.mpl_connect("motion_notify_event", hover)
            
            self.logger.info("Added hover update functionality to Iron Condor chart")
            
        except Exception as e:
            self.logger.error(f"Error adding hover update: {e}")
    
    def _get_strategy_details_at_price(self, price, payoff):
        """Get detailed strategy information at a specific price"""
        try:
            if not hasattr(self, '_current_trade') or not self._current_trade:
                return "No strategy data available"
            
            trade = self._current_trade
            payoff_data = self._current_payoff_data
            
            # Calculate percentage changes for breakevens based on current spot price
            breakeven_texts = []
            spot_price = getattr(self, '_current_spot_price', price)  # Use spot price if available, fallback to hovered price
            for breakeven in payoff_data['breakevens']:
                if isinstance(breakeven, (list, tuple)):
                    breakeven = breakeven[0] if breakeven else 0
                percentage_change = ((breakeven - spot_price) / spot_price) * 100
                sign = "+" if percentage_change >= 0 else ""
                breakeven_texts.append(f"{breakeven:.0f} ({sign}{percentage_change:.1f}%)")
            
            # Calculate risk reward ratio
            max_profit = payoff_data['max_profit']
            max_loss = abs(payoff_data['max_loss'])  # Use absolute value for loss
            risk_reward_ratio = max_loss / max_profit if max_profit > 0 else 0
            
            # Create detailed strategy text for the text box
            strategy_text = f"""Strategy Details at NIFTY {price:.0f}:

Total P&L: ₹{payoff:.0f}

Max Profit: ₹{max_profit:.0f}
Max Loss: ₹{payoff_data['max_loss']:.0f}
Risk:Reward Ratio: {risk_reward_ratio:.2f}
Breakevens: {', '.join(breakeven_texts)}"""
            
            return strategy_text
            
        except Exception as e:
            self.logger.error(f"Error getting strategy details at price: {e}")
            return f"Error loading details: {e}"
    
    def update_status(self, message):
        """Update the status label with scrolling information"""
        try:
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"Status: {message}")
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
    
    def _update_grid2_crosshair(self, x, y, ax):
        """Update crosshair position for chart 2 (Iron Condor payoff chart)"""
        try:
            if not ax or x is None or y is None:
                return
            
            # Get chart bounds
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            
            # Create or update vertical line only
            if self.grid2_crosshair_vline is None or not hasattr(self.grid2_crosshair_vline, 'set_xdata'):
                self.grid2_crosshair_vline, = ax.plot([x, x], [ylim[0], ylim[1]], 
                                                    color='darkgrey', linestyle='--', alpha=0.7, linewidth=1)
            else:
                self.grid2_crosshair_vline.set_xdata([x, x])
                self.grid2_crosshair_vline.set_ydata([ylim[0], ylim[1]])
                self.grid2_crosshair_vline.set_visible(True)
            
        except Exception as e:
            self.logger.error(f"Error updating chart 2 crosshair: {e}")
    
    def _hide_grid2_crosshair(self):
        """Hide crosshair line for chart 2"""
        try:
            if self.grid2_crosshair_vline:
                self.grid2_crosshair_vline.set_visible(False)
        except Exception as e:
            self.logger.error(f"Error hiding chart 2 crosshair: {e}")
    
    
    def _on_window_resize(self, event):
        """Handle window resize events to make grid responsive"""
        try:
            # Only handle resize events for the main window (not child widgets)
            if event.widget == self.root:
                # Force update the layout first
                self.root.update_idletasks()
                
                # Update matplotlib figure size to match the container
                if hasattr(self, 'canvas') and self.canvas:
                    # Get the current size of the grid1_frame
                    if hasattr(self, 'grid1_frame'):
                        grid1_width = self.grid1_frame.winfo_width()
                        grid1_height = self.grid1_frame.winfo_height()
                        
                        # Only resize if we have valid dimensions
                        if grid1_width > 50 and grid1_height > 50:
                            # Update the matplotlib figure size
                            dpi = self.chart.fig.get_dpi()
                            fig_width = max(grid1_width / dpi, 4.0)  # Minimum 4 inches
                            fig_height = max(grid1_height / dpi, 3.0)  # Minimum 3 inches
                            
                            # Set the figure size
                            self.chart.fig.set_size_inches(fig_width, fig_height)
                            
                            # Ensure proper spacing for rotated labels and combined title after resize
                            if hasattr(self.chart, 'price_ax') and self.chart.price_ax:
                                self.chart.price_ax.margins(x=0.02, y=0.05)
                                self.chart.fig.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.88)
                            
                            # Force the canvas to resize
                            self.canvas.get_tk_widget().configure(width=grid1_width, height=grid1_height)
                            
                            # Redraw the canvas
                            self.canvas.draw_idle()
                            
                            self.logger.info(f"Resized chart to {fig_width:.1f}x{fig_height:.1f} inches ({grid1_width}x{grid1_height} pixels)")
                
                # Update Grid 2 figure if it exists
                if hasattr(self, 'grid2_fig') and self.grid2_fig:
                    if hasattr(self, 'grid2_frame'):
                        grid2_width = self.grid2_frame.winfo_width()
                        grid2_height = self.grid2_frame.winfo_height()
                        
                        if grid2_width > 50 and grid2_height > 50:
                            dpi = self.grid2_fig.get_dpi()
                            fig_width = max(grid2_width / dpi, 4.0)
                            # Ensure minimum height to prevent x-axis cutoff
                            fig_height = max(grid2_height / dpi, 4.0)  # Increased from 3.0 to 4.0
                            
                            self.grid2_fig.set_size_inches(fig_width, fig_height)
                            
                            # Reapply subplot adjustments after resize
                            import matplotlib.pyplot as plt
                            plt.subplots_adjust(bottom=0.20, left=0.1, right=0.95, top=0.95)
                            
                            # Debug logging for Chart 2 resize
                            self.logger.info(f"Chart 2 resized to {fig_width:.1f}x{fig_height:.1f} inches with 20% bottom margin")
                            
                            # Force the canvas to resize
                            if hasattr(self.grid2_fig, 'canvas') and self.grid2_fig.canvas:
                                self.grid2_fig.canvas.get_tk_widget().configure(width=grid2_width, height=grid2_height)
                            
                            self.grid2_fig.canvas.draw_idle()
                            
                            self.logger.info(f"Resized Grid 2 chart to {fig_width:.1f}x{fig_height:.1f} inches ({grid2_width}x{grid2_height} pixels)")
                            
        except Exception as e:
            self.logger.warning(f"Error handling window resize: {e}")
    
    def _handle_close(self):
        """Handle window close event - wrapper for on_closing"""
        self.on_closing()
    
    def on_closing(self):
        """Handle window close event"""
        try:
            # Stop the chart
            if hasattr(self, 'chart') and self.chart:
                self.chart.stop_chart()
            
            # Destroy the window
            self.root.destroy()
            
            # Force exit the application
            import os
            os._exit(0)
            
        except Exception as e:
            print(f"Error during window close: {e}")
            # Force exit even if there's an error
            import os
            os._exit(0)
    
    def _show_trade_all_window(self):
        """Show window with all trades that would be executed in Iron Condor strategy"""
        try:
            if not hasattr(self, '_current_trade') or not self._current_trade:
                self.logger.warning("No current trade available for Trade All window")
                return
            
            # Create new window
            trade_window = tk.Toplevel(self.root)
            trade_window.title("Iron Condor - Trade All")
            trade_window.geometry("820x620")
            trade_window.resizable(True, True)
            
            # Center the window
            trade_window.transient(self.root)
            trade_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(trade_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Title
            title_label = ttk.Label(main_frame, text="Iron Condor Strategy - All Trades", 
                                  font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 10))
            
            # Strategy summary
            summary_frame = ttk.LabelFrame(main_frame, text="Strategy Summary", padding=10)
            summary_frame.pack(fill=tk.X, pady=(0, 10))
            
            trade = self._current_trade
            summary_text = f"""Strategy: {trade.strategy_name}
Underlying: {trade.underlying_instrument}
Trade ID: {trade.trade_id}
Total Legs: {len(trade.legs)}"""
            
            summary_label = ttk.Label(summary_frame, text=summary_text, font=("Arial", 10))
            summary_label.pack(anchor=tk.W)
            
            # Trades list
            trades_frame = ttk.LabelFrame(main_frame, text="Individual Trades", padding=10)
            trades_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create treeview for trades
            columns = ("Leg", "Instrument", "Type", "Strike", "Position", "Quantity", "Entry Price")
            tree = ttk.Treeview(trades_frame, columns=columns, show="headings", height=15)
            
            # Configure columns
            tree.heading("Leg", text="Leg #")
            tree.heading("Instrument", text="Instrument")
            tree.heading("Type", text="Type")
            tree.heading("Strike", text="Strike Price")
            tree.heading("Position", text="Position")
            tree.heading("Quantity", text="Quantity")
            tree.heading("Entry Price", text="Entry Price")
            
            # Set column widths
            tree.column("Leg", width=50)
            tree.column("Instrument", width=200)
            tree.column("Type", width=80)
            tree.column("Strike", width=100)
            tree.column("Position", width=80)
            tree.column("Quantity", width=80)
            tree.column("Entry Price", width=100)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(trades_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Configure row colors
            tree.tag_configure("long_trade", background="#ccffcc")  # Light green for LONG trades
            tree.tag_configure("short_trade", background="#ffcccc")  # Light red for SHORT trades
            
            # Pack treeview and scrollbar
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Populate trades
            for i, leg in enumerate(trade.legs, 1):
                position_text = "LONG" if leg.position_type.value == "LONG" else "SHORT"
                option_type_text = "CALL" if leg.option_type.value == "CALL" else "PUT"
                
                # Determine row color based on position type (LONG/SHORT)
                row_tag = "long_trade" if leg.position_type.value == "LONG" else "short_trade"
                
                tree.insert("", "end", values=(
                    i,
                    leg.instrument_name,
                    option_type_text,
                    f"₹{leg.strike_price:,.0f}",
                    position_text,
                    leg.quantity,
                    f"₹{leg.entry_price:.2f}"
                ), tags=(row_tag,))
            
            # Footer with strategy metrics
            footer_frame = ttk.Frame(main_frame)
            footer_frame.pack(fill=tk.X, pady=(10, 0))
            
            # Get max profit and max loss from payoff data
            if hasattr(self, '_current_payoff_data') and self._current_payoff_data:
                max_profit = self._current_payoff_data.get('max_profit', 0)
                max_loss = self._current_payoff_data.get('max_loss', 0)
            else:
                # Calculate from trade data if payoff data not available
                total_premium_collected = sum(leg.entry_price * leg.quantity for leg in trade.legs 
                                            if leg.position_type.value == "SHORT")
                total_premium_paid = sum(leg.entry_price * leg.quantity for leg in trade.legs 
                                       if leg.position_type.value == "LONG")
                net_premium = total_premium_collected - total_premium_paid
                max_profit = net_premium
                max_loss = -net_premium
            
            metrics_text = f"""Max Profit: ₹{max_profit:,.0f}
Max Loss: ₹{max_loss:,.0f}"""
            
            metrics_label = ttk.Label(footer_frame, text=metrics_text, font=("Arial", 10, "bold"))
            metrics_label.pack(anchor=tk.W)
            
            # Buttons frame
            buttons_frame = ttk.Frame(footer_frame)
            buttons_frame.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Trade button
            trade_button = ttk.Button(buttons_frame, text="Trade", 
                                    command=lambda: self._place_iron_condor_orders(trade_window, trade))
            trade_button.pack(side=tk.RIGHT)
            
            # Focus on the window
            trade_window.focus_set()
            
            self.logger.info("Opened Trade All window with Iron Condor trades")
            
        except Exception as e:
            self.logger.error(f"Error showing trade all window: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open trade window: {e}")
    
    def _show_chain_window(self):
        """Show chain/option chain window with live data"""
        try:
            # Create new window
            chain_window = tk.Toplevel(self.root)
            chain_window.title("Option Chain")
            chain_window.geometry("1000x600")
            chain_window.resizable(True, True)
            
            # Center the window
            chain_window.transient(self.root)
            chain_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(chain_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Title and info frame
            header_frame = ttk.Frame(main_frame)
            header_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Title
            title_label = ttk.Label(header_frame, text="Option Chain", 
                                  font=("Arial", 16, "bold"))
            title_label.pack(side=tk.LEFT)
            
            # Refresh button
            refresh_button = ttk.Button(header_frame, text="Refresh", 
                                      command=lambda: self._refresh_option_chain(chain_window))
            refresh_button.pack(side=tk.RIGHT)
            
            # Info frame for expiry and spot price
            info_frame = ttk.LabelFrame(main_frame, text="Market Info", padding=5)
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            self.chain_info_label = ttk.Label(info_frame, text="Loading...", font=("Arial", 10))
            self.chain_info_label.pack()
            
            # Table frame
            table_frame = ttk.LabelFrame(main_frame, text="Option Chain Data", padding=5)
            table_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create custom style for treeview with larger font
            style = ttk.Style()
            style.configure("Custom.Treeview", font=("Arial", 14))  # Increased font size for taller rows
            style.configure("Custom.Treeview.Heading", font=("Arial", 14, "bold"))
            
            # Create treeview for option chain table
            columns = ("Put LTP", "Strike Price", "Call LTP")
            self.chain_tree = ttk.Treeview(table_frame, columns=columns, show="headings", 
                                         height=20, style="Custom.Treeview")
            
            # Try to increase row height using different methods
            try:
                # Method 1: Configure the treeview with a larger font that naturally increases row height
                # Note: ttk.Treeview doesn't support direct font configuration, so we rely on the style
                self.logger.debug("Applied larger font (14px) via style configuration")
            except Exception as e:
                self.logger.debug(f"Could not apply larger font: {e}")
            
            # Configure columns
            self.chain_tree.heading("Put LTP", text="Put LTP")
            self.chain_tree.heading("Strike Price", text="Strike Price")
            self.chain_tree.heading("Call LTP", text="Call LTP")
            
            # Configure column widths
            self.chain_tree.column("Put LTP", width=100, anchor="center")
            self.chain_tree.column("Strike Price", width=120, anchor="center")
            self.chain_tree.column("Call LTP", width=100, anchor="center")
            
            # Configure tags for alternating rows and highlighting
            self.chain_tree.tag_configure("even", background="white")  # White background for even rows
            self.chain_tree.tag_configure("odd", background="#F8F8F8")  # Very light gray for odd rows
            self.chain_tree.tag_configure("nearest", background="#FFE4B5")  # Light orange for nearest strike
            
            # Increase row height by adding padding to each row
            self._increase_treeview_row_height()
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.chain_tree.yview)
            self.chain_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack treeview and scrollbar
            self.chain_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Status frame
            status_frame = ttk.Frame(main_frame)
            status_frame.pack(fill=tk.X, pady=(10, 0))
            
            self.chain_status_label = ttk.Label(status_frame, text="Loading option chain data...", 
                                              font=("Arial", 9))
            self.chain_status_label.pack(side=tk.LEFT)
            
            # Close button
            close_button = ttk.Button(status_frame, text="Close", 
                                    command=chain_window.destroy)
            close_button.pack(side=tk.RIGHT)
            
            # Load option chain data
            self._load_option_chain_data(chain_window)
            
        except Exception as e:
            self.logger.error(f"Error showing chain window: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open chain window: {e}")
    
    def _load_option_chain_data(self, chain_window):
        """Load and display option chain data"""
        try:
            # Import required modules
            from datawarehouse import datawarehouse
            from trade_utils import Utils
            
            # Get current expiry date (next weekly expiry)
            expiry_dates = Utils.get_next_weekly_expiry()
            if not expiry_dates:
                self.chain_status_label.config(text="Error: Could not get expiry date")
                return
            
            expiry_date = expiry_dates[0]  # Use first expiry
            instrument_key = "NSE_INDEX|Nifty 50"
            
            # Update status
            self.chain_status_label.config(text=f"Fetching option chain data for {expiry_date}...")
            chain_window.update()
            
            # Fetch option chain data
            raw_data = datawarehouse.fetch_option_chain_data(
                instrument_key=instrument_key,
                expiry_date=expiry_date
            )
            
            if not raw_data:
                self.chain_status_label.config(text="Error: No option chain data received")
                return
            
            # Format the data
            formatted_data = Utils.format_option_chain_data(raw_data)
            
            if not formatted_data or not formatted_data.get("strike_prices"):
                self.chain_status_label.config(text="Error: No formatted option chain data")
                return
            
            # Update info label
            spot_price = formatted_data.get("underlying_spot_price", 0)
            pcr = formatted_data.get("pcr", 0)
            info_text = f"Expiry: {expiry_date} | Spot: ₹{spot_price:,.2f} | PCR: {pcr:.2f}"
            self.chain_info_label.config(text=info_text)
            
            # Clear existing data
            for item in self.chain_tree.get_children():
                self.chain_tree.delete(item)
            
            # Populate table with option chain data
            strike_prices = sorted(formatted_data["strike_prices"].keys(), key=lambda x: float(x))
            
            # Get current spot price for nearest strike calculation
            spot_price = formatted_data.get("underlying_spot_price", 0)
            nearest_strike = None
            
            if spot_price > 0:
                # Get nearest strikes using Utils
                from trade_utils import Utils
                nearest_strikes = Utils.get_nearest_strikes(spot_price, count=1)
                if nearest_strikes:
                    nearest_strike = float(nearest_strikes[0])
                    self.logger.debug(f"Calculated nearest strike: {nearest_strike} for spot price: {spot_price}")

            counter = 0
            should_start_counting = False

            for i, strike_price in enumerate(strike_prices):
                strike_data = formatted_data["strike_prices"][strike_price]
                
                # Get LTP values
                put_ltp = "N/A"
                call_ltp = "N/A"
                
                if strike_data.get("put_options"):
                    put_ltp = f"₹{strike_data['put_options'].market_data.ltp:.2f}"
                
                if strike_data.get("call_options"):
                    call_ltp = f"₹{strike_data['call_options'].market_data.ltp:.2f}"
                
                # Determine tags for this row (alternating colors)
                tags = ["even" if i % 2 == 0 else "odd"]  # Alternating row colors
                if nearest_strike and strike_price == nearest_strike:
                    tags = ["nearest"]  # Override with nearest tag for highlighting
                
                # Insert row with tags
                item_id = self.chain_tree.insert("", "end", values=(
                    put_ltp,
                    f"₹{strike_price}",
                    call_ltp
                ), tags=tags)
                
                # Highlight the nearest strike price row
                if nearest_strike and float(strike_price) == nearest_strike:
                    self.chain_tree.set(item_id, "Strike Price", f"₹{strike_price} ← NEAREST")
                    self.chain_tree.selection_set(item_id)
                    should_start_counting = True
                
                if should_start_counting:
                    counter += 1

                if counter == 10:
                    self.nearest_strike_item = item_id
                    should_start_counting = False
                    counter = 0


            # Auto-scroll to nearest strike price
            if hasattr(self, 'nearest_strike_item') and self.nearest_strike_item:
                try:
                    # Schedule the scroll after a short delay to ensure tree is fully rendered
                    chain_window.after(100, self._scroll_to_nearest_strike)
                except Exception as e:
                    self.logger.warning(f"Could not schedule scroll to nearest strike: {e}")
            
            # Update status
            total_strikes = len(strike_prices)
            from datetime import datetime
            status_text = f"Loaded {total_strikes} strike prices | Last updated: {datetime.now().strftime('%H:%M:%S')}"
            if nearest_strike:
                status_text += f" | Nearest strike: ₹{nearest_strike}"
            self.chain_status_label.config(text=status_text)
            
        except Exception as e:
            self.logger.error(f"Error loading option chain data: {e}")
            self.chain_status_label.config(text=f"Error: {e}")
    
    def _increase_treeview_row_height(self):
        """Increase the row height of the treeview by adding padding"""
        try:
            # The row height is primarily controlled by the font size in the style
            # We've already increased the font size to 14px in the style configuration
            # This should naturally increase the row height
            
            # Additional method: Try to configure padding in the style
            style = ttk.Style()
            try:
                # Configure padding for treeview items
                style.configure("Custom.Treeview.Item", padding=(0, 3, 0, 3))  # Top and bottom padding
                style.map("Custom.Treeview.Item", 
                         padding=[("selected", (0, 3, 0, 3)),
                                 ("active", (0, 3, 0, 3))])
            except Exception as e:
                self.logger.debug(f"Could not configure item padding: {e}")
                
            self.logger.debug("Applied row height increase via font size and padding")
            
        except Exception as e:
            self.logger.warning(f"Could not increase treeview row height: {e}")

    def _scroll_to_nearest_strike(self):
        """Scroll to the nearest strike price in the option chain tree"""
        try:
            if hasattr(self, 'nearest_strike_item') and self.nearest_strike_item:
                # Select and scroll to the nearest strike price row
                self.chain_tree.see(self.nearest_strike_item)
                self.chain_tree.focus(self.nearest_strike_item)
                self.logger.debug(f"Auto-scrolled to nearest strike item: {self.nearest_strike_item}")
        except Exception as e:
            self.logger.warning(f"Could not scroll to nearest strike: {e}")

    def _refresh_option_chain(self, chain_window):
        """Refresh option chain data"""
        try:
            # Clear existing data first
            for item in self.chain_tree.get_children():
                self.chain_tree.delete(item)
            
            # Reload data with proper styling
            self._load_option_chain_data(chain_window)
        except Exception as e:
            self.logger.error(f"Error refreshing option chain: {e}")
            self.chain_status_label.config(text=f"Refresh error: {e}")
    
    def _show_positions_window(self):
        """Show current positions window"""
        try:
            # Create new window
            positions_window = tk.Toplevel(self.root)
            positions_window.title("Current Positions")
            positions_window.geometry("1000x600")
            positions_window.resizable(True, True)
            
            # Center the window
            positions_window.transient(self.root)
            positions_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(positions_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Title
            title_label = ttk.Label(main_frame, text="Current Positions", 
                                  font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 10))
            
            # Control frame with refresh button
            control_frame = ttk.Frame(main_frame)
            control_frame.pack(fill=tk.X, pady=(0, 10))
            
            refresh_button = ttk.Button(control_frame, text="🔄 Refresh Positions", 
                                      command=lambda: self._refresh_positions_window(positions_window, tree, summary_label))
            refresh_button.pack(side=tk.LEFT)
            
            # Status label
            status_label = ttk.Label(control_frame, text="Loading positions...", 
                                   font=("Arial", 10), foreground="blue")
            status_label.pack(side=tk.RIGHT)
            
            # Positions summary frame
            summary_frame = ttk.LabelFrame(main_frame, text="Positions Summary", padding=10)
            summary_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Initialize summary label
            summary_label = ttk.Label(summary_frame, text="Loading...", font=("Arial", 10))
            summary_label.pack(anchor=tk.W)
            
            # Positions details frame
            details_frame = ttk.LabelFrame(main_frame, text="Position Details", padding=10)
            details_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create treeview for positions with new columns
            columns = ("Name", "Quantity", "Average Price", "Last Price", "Profit/Loss", "Action")
            tree = ttk.Treeview(details_frame, columns=columns, show="headings", height=15)
            
            # Configure columns
            tree.heading("Name", text="Name (Trading Symbol)")
            tree.heading("Quantity", text="Quantity")
            tree.heading("Average Price", text="Average Price")
            tree.heading("Last Price", text="Last Price")
            tree.heading("Profit/Loss", text="Profit/Loss")
            tree.heading("Action", text="Action")
            
            # Configure column widths and alignment
            tree.column("Name", width=200, anchor="center")
            tree.column("Quantity", width=100, anchor="center")
            tree.column("Average Price", width=120, anchor="center")
            tree.column("Last Price", width=120, anchor="center")
            tree.column("Profit/Loss", width=120, anchor="center")
            tree.column("Action", width=120, anchor="center")
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack treeview and scrollbar
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Bind click events to handle "Add Trade" button clicks
            tree.bind("<Button-1>", lambda event: self._on_add_trade_click(event, tree, positions_window))
            tree.bind("<Double-1>", lambda event: self._on_add_trade_click(event, tree, positions_window))
            
            # Bind hover events for visual feedback
            tree.bind("<Motion>", lambda event: self._on_tree_hover(event, tree))
            tree.bind("<Leave>", lambda event: self._on_tree_leave(event, tree))
            
            # Fetch and populate positions data
            self._refresh_positions_window(positions_window, tree, summary_label, status_label)
            
            # Close button
            close_button = ttk.Button(main_frame, text="Close", 
                                    command=positions_window.destroy)
            close_button.pack(pady=(10, 0))
            
        except Exception as e:
            self.logger.error(f"Error showing positions window: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open positions window: {e}")
    
    def _refresh_positions_window(self, positions_window, tree, summary_label, status_label=None):
        """Refresh positions data from Upstox API"""
        try:
            # Validate parameters
            if not tree:
                self.logger.error("Tree widget is None, cannot refresh")
                return
            
            # Update status
            if status_label:
                try:
                    status_label.config(text="Fetching positions from server...", foreground="blue")
                except Exception as e:
                    self.logger.warning(f"Could not update status label: {e}")
            
            # Clear existing data
            try:
                for item in tree.get_children():
                    tree.delete(item)
            except Exception as e:
                self.logger.warning(f"Could not clear tree data: {e}")
                return
            
            # Check if we have access to the agent
            if not hasattr(self, '_current_agent') or not self._current_agent:
                summary_text = "❌ No trading agent available"
                if status_label:
                    try:
                        status_label.config(text="Error: No agent available", foreground="red")
                    except Exception as e:
                        self.logger.warning(f"Could not update status label: {e}")
                if summary_label:
                    try:
                        summary_label.config(text=summary_text)
                    except Exception as e:
                        self.logger.warning(f"Could not update summary label: {e}")
                return
            
            # Check if agent has fetch_positions method
            if not hasattr(self._current_agent, 'fetch_positions'):
                summary_text = "❌ Agent does not support position fetching"
                if status_label:
                    try:
                        status_label.config(text="Error: Agent not supported", foreground="red")
                    except Exception as e:
                        self.logger.warning(f"Could not update status label: {e}")
                if summary_label:
                    try:
                        summary_label.config(text=summary_text)
                    except Exception as e:
                        self.logger.warning(f"Could not update summary label: {e}")
                return
            
            # Fetch positions from Upstox API
            try:
                positions_data = self._current_agent.fetch_positions()
                
                if not positions_data:
                    summary_text = "ℹ️ No positions found"
                    if status_label:
                        try:
                            status_label.config(text="No positions found", foreground="orange")
                        except Exception as e:
                            self.logger.warning(f"Could not update status label: {e}")
                    if summary_label:
                        try:
                            summary_label.config(text=summary_text)
                        except Exception as e:
                            self.logger.warning(f"Could not update summary label: {e}")
                    return
                
                # Debug: Log the structure of the first position
                if positions_data and len(positions_data) > 0:
                    first_pos = positions_data[0]
                    self.logger.info(f"Position data type: {type(first_pos)}")
                    if hasattr(first_pos, '__dict__'):
                        self.logger.info(f"Position attributes: {list(first_pos.__dict__.keys())}")
                        # Try to get some sample values
                        try:
                            sample_symbol = getattr(first_pos, 'trading_symbol', 'NOT_FOUND')
                            sample_quantity = getattr(first_pos, 'quantity', 'NOT_FOUND')
                            self.logger.info(f"Sample trading_symbol: {sample_symbol}")
                            self.logger.info(f"Sample quantity: {sample_quantity}")
                        except Exception as debug_error:
                            self.logger.error(f"Debug error: {debug_error}")
                    else:
                        self.logger.info(f"Position is not an object, treating as dict")
                
                # Calculate totals
                total_pnl = 0.0
                total_unrealised = 0.0
                total_realised = 0.0
                
                # Populate tree with position data
                for pos in positions_data:
                    try:
                        # Extract required fields - positions should now be dictionaries
                        trading_symbol = (pos.get('_trading_symbol') or 
                                        pos.get('_tradingsymbol') or 'N/A')
                        quantity = pos.get('_quantity', 0) or 0
                        average_price = pos.get('_average_price', 0) or 0
                        last_price = pos.get('_last_price', 0) or 0
                        pnl = pos.get('_pnl', 0) or 0
                        unrealised = pos.get('_unrealised', 0) or 0
                        realised = pos.get('_realised', 0)
                            
                    except Exception as attr_error:
                        self.logger.error(f"Error extracting position data: {attr_error}")
                        # Skip this position if we can't extract data
                        continue
                    
                    # Calculate total P&L (realised + unrealised)
                    total_pnl_value = realised + unrealised
                    
                    # Update totals
                    total_pnl += pnl
                    total_unrealised += unrealised
                    total_realised += realised
                    
                    # Format values for display
                    avg_price_str = f"₹{average_price:.2f}" if average_price else "N/A"
                    last_price_str = f"₹{last_price:.2f}" if last_price else "N/A"
                    pnl_str = f"₹{total_pnl_value:.2f}"
                    
                    # Color code P&L
                    if total_pnl_value > 0:
                        pnl_str = f"🟢 {pnl_str}"
                    elif total_pnl_value < 0:
                        pnl_str = f"🔴 {pnl_str}"
                    else:
                        pnl_str = f"⚪ {pnl_str}"
                    
                    # Check if position exists in trade legs
                    is_in_trade_legs = self._is_position_in_trade_legs(trading_symbol)
                    
                    # Create more button-like text
                    if not is_in_trade_legs:
                        action_text = "➕ Add Trade"
                        action_display = "➕ Add Trade"
                    else:
                        action_text = "✅ In Trade"
                        action_display = "✅ In Trade"
                    
                    # Insert into tree
                    item = tree.insert("", "end", values=(
                        trading_symbol,
                        quantity,
                        avg_price_str,
                        last_price_str,
                        pnl_str,
                        action_display
                    ))
                    
                    # Add tags for styling if needed
                    if not is_in_trade_legs:
                        tree.set(item, "Action", "➕ Add Trade")
                    else:
                        tree.set(item, "Action", "✅ In Trade")
                
                # Update summary
                summary_text = f"📊 Total Positions: {len(positions_data)}\n"
                summary_text += f"💰 Total P&L: ₹{total_pnl:.2f}\n"
                summary_text += f"📈 Unrealised: ₹{total_unrealised:.2f}\n"
                summary_text += f"✅ Realised: ₹{total_realised:.2f}\n"
                
                if summary_label:
                    try:
                        summary_label.config(text=summary_text)
                    except Exception as e:
                        self.logger.warning(f"Could not update summary label: {e}")
                
                if status_label:
                    try:
                        status_label.config(text=f"✅ Loaded {len(positions_data)} positions", foreground="green")
                    except Exception as e:
                        self.logger.warning(f"Could not update status label: {e}")
                
                self.logger.info(f"Successfully loaded {len(positions_data)} positions from Upstox API")
                
            except Exception as api_error:
                error_msg = f"❌ Error fetching positions: {str(api_error)}"
                summary_text = error_msg
                if status_label:
                    try:
                        status_label.config(text="Error fetching positions", foreground="red")
                    except Exception as e:
                        self.logger.warning(f"Could not update status label: {e}")
                if summary_label:
                    try:
                        summary_label.config(text=summary_text)
                    except Exception as e:
                        self.logger.warning(f"Could not update summary label: {e}")
                self.logger.error(f"Error fetching positions from Upstox API: {api_error}")
                
        except Exception as e:
            error_msg = f"❌ Unexpected error: {str(e)}"
            summary_text = error_msg
            if status_label:
                try:
                    status_label.config(text="Unexpected error", foreground="red")
                except Exception as e:
                    self.logger.warning(f"Could not update status label: {e}")
            if summary_label:
                try:
                    summary_label.config(text=summary_text)
                except Exception as e:
                    self.logger.warning(f"Could not update summary label: {e}")
            self.logger.error(f"Unexpected error in _refresh_positions_window: {e}")
    
    def _is_position_in_trade_legs(self, trading_symbol: str) -> bool:
        """Check if a position exists in any open trade legs"""
        try:
            # Get all open trades from strategy manager
            if hasattr(self, 'strategy_manager') and self.strategy_manager:
                open_trades = self.strategy_manager.get_open_positions()
                
                # Check each trade's legs
                for trade in open_trades:
                    for leg in trade.legs:
                        # Check if the instrument matches (exact match or contains)
                        if (leg.instrument == trading_symbol or 
                            leg.instrument_name == trading_symbol or
                            trading_symbol in leg.instrument or
                            leg.instrument in trading_symbol):
                            self.logger.info(f"Position '{trading_symbol}' found in trade leg: {leg.instrument}")
                            return True
                
            # Also check if we have access to the main app's strategy manager
            elif hasattr(self, '_main_app') and hasattr(self._main_app, 'strategy_manager'):
                open_trades = self._main_app.strategy_manager.get_open_positions()
                
                # Check each trade's legs
                for trade in open_trades:
                    for leg in trade.legs:
                        # Check if the instrument matches (exact match or contains)
                        if (leg.instrument == trading_symbol or 
                            leg.instrument_name == trading_symbol or
                            trading_symbol in leg.instrument or
                            leg.instrument in trading_symbol):
                            self.logger.info(f"Position '{trading_symbol}' found in trade leg: {leg.instrument}")
                            return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if position exists in trade legs: {e}")
            return False
    
    def _check_positions(self):
        """Check positions manually by calling the main app's position comparison method"""
        try:
            if hasattr(self, '_main_app') and self._main_app:
                self.logger.info("Manually checking positions...")
                self._main_app.compare_positions_with_database()
            else:
                self.logger.warning("Main app reference not available for position checking")
                # Fallback: show a simple message
                import tkinter.messagebox as messagebox
                messagebox.showinfo("Check Positions", "Position checking requires main app connection.")
        except Exception as e:
            self.logger.error(f"Error checking positions: {e}")
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error", f"Failed to check positions: {e}")

    def _on_add_trade_click(self, event, tree, positions_window):
        """Handle Add Trade button clicks in the positions window"""
        try:
            # Get the item that was clicked
            item = tree.identify_row(event.y)
            if not item:
                return
            
            # Select the item for visual feedback
            tree.selection_set(item)
            
            # Get the values of the clicked row
            values = tree.item(item, "values")
            if len(values) < 6:  # Should have 6 columns including Action
                return
            
            trading_symbol = values[0]  # Name column
            quantity = values[1]        # Quantity column
            average_price = values[2]   # Average Price column
            last_price = values[3]      # Last Price column
            action_text = values[5]     # Action column value
            
            # Check if clicked on Action column (last column)
            column = tree.identify_column(event.x)
            self.logger.info(f"Clicked on column: {column}, Action text: {action_text}")
            
            if column == "#6":  # Action column is the 6th column
                if "Add Trade" in action_text:
                    # Visual feedback - change cursor
                    tree.config(cursor="hand2")
                    positions_window.update()
                    
                    self.logger.info(f"Adding position as trade leg: {trading_symbol}")
                    # Add position directly as trade leg
                    self._add_position_as_trade_leg(positions_window, trading_symbol, quantity, average_price, last_price)
                    
                    # Reset cursor
                    tree.config(cursor="")
                else:
                    # Position is already in trade, show info message
                    import tkinter.messagebox as msgbox
                    msgbox.showinfo("Position in Trade", 
                                  f"Position '{trading_symbol}' is already part of an open trade.\n"
                                  f"Action: {action_text}")
            else:
                # If not clicked on Action column, just select the row
                # Reset cursor to default
                tree.config(cursor="")
                self.logger.info(f"Clicked on non-action column: {column}")
                
        except Exception as e:
            self.logger.error(f"Error handling add trade click: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to handle add trade click: {e}")
    
    def _on_tree_hover(self, event, tree):
        """Handle mouse hover over treeview for visual feedback"""
        try:
            # Get the item and column under the mouse
            item = tree.identify_row(event.y)
            column = tree.identify_column(event.x)
            
            if item and column == "#6":  # Action column
                # Get the action text
                values = tree.item(item, "values")
                if len(values) >= 6:
                    action_text = values[5]
                    if "Add Trade" in action_text:
                        # Change cursor to hand pointer for clickable items
                        tree.config(cursor="hand2")
                    else:
                        tree.config(cursor="")
                else:
                    tree.config(cursor="")
            else:
                tree.config(cursor="")
                
        except Exception as e:
            # Silently handle hover errors to avoid spam
            pass
    
    def _on_tree_leave(self, event, tree):
        """Handle mouse leave from treeview"""
        try:
            tree.config(cursor="")
        except Exception as e:
            # Silently handle leave errors
            pass
    
    def _add_position_as_trade_leg(self, parent_window, trading_symbol, quantity, average_price, last_price):
        """Add position directly as trade leg to current open trade or create new trade"""
        try:
            import tkinter.messagebox as msgbox
            from trade_models import Trade, TradeLeg, OptionType, PositionType
            from datetime import datetime
            
            # Get strategy manager
            strategy_manager = None
            if hasattr(self, 'strategy_manager') and self.strategy_manager:
                strategy_manager = self.strategy_manager
            elif hasattr(self, '_main_app') and hasattr(self._main_app, 'strategy_manager'):
                strategy_manager = self._main_app.strategy_manager
            
            if not strategy_manager:
                msgbox.showerror("Error", "Strategy manager not available")
                return
            
            # Get current open trades
            open_trades = strategy_manager.get_open_positions()
            
            # Find the most recent open trade or create a new one
            current_trade = None
            if open_trades:
                # Use the most recent open trade
                current_trade = open_trades[0]
                self.logger.info(f"Using existing trade: {current_trade.trade_id}")
            else:
                # Create a new trade
                trade_id = f"POSITION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                current_trade = Trade(
                    trade_id=trade_id,
                    strategy_name="Position Trade",
                    underlying_instrument=trading_symbol.split('_')[0] if '_' in trading_symbol else trading_symbol,
                    notes=f"Auto-created trade for position: {trading_symbol}"
                )
                self.logger.info(f"Created new trade: {trade_id}")
            
            # Parse trading symbol to determine option type and strike price
            option_type = OptionType.CALL  # Default
            strike_price = 0.0
            
            # Try to extract option details from trading symbol
            symbol_upper = trading_symbol.upper()
            if any(x in symbol_upper for x in ['CE', 'CALL', 'C']):
                option_type = OptionType.CALL
            elif any(x in symbol_upper for x in ['PE', 'PUT', 'P']):
                option_type = OptionType.PUT
            else:
                # Default to CALL if we can't determine
                option_type = OptionType.CALL
            
            # Try to extract strike price (look for numbers in the symbol)
            import re
            numbers = re.findall(r'\d+', trading_symbol)
            if numbers:
                strike_price = float(numbers[-1])  # Use the last number found
            
            # Parse quantity safely
            try:
                qty_value = int(quantity)
            except (ValueError, TypeError):
                qty_value = 1  # Default to 1 if parsing fails
            
            # Determine position type based on quantity
            position_type = PositionType.LONG if qty_value > 0 else PositionType.SHORT
            
            # Parse average price safely
            try:
                if average_price != 'N/A':
                    entry_price = float(average_price.replace('₹', '').replace(',', ''))
                else:
                    entry_price = 0.0
            except (ValueError, TypeError):
                entry_price = 0.0
            
            # Create trade leg
            trade_leg = TradeLeg(
                instrument=trading_symbol,
                instrument_name=trading_symbol,
                option_type=option_type,
                strike_price=strike_price,
                position_type=position_type,
                quantity=abs(qty_value),  # Use absolute value
                entry_timestamp=datetime.now(),
                entry_price=entry_price
            )
            
            # Add leg to trade
            current_trade.add_leg(trade_leg)
            
            # Save trade to database
            # Check if trade already exists in database
            existing_trade = strategy_manager.db.get_trade(current_trade.trade_id)
            
            if existing_trade is None:
                # New trade - save it
                success = strategy_manager.db.save_trade(current_trade)
                if success:
                    self.logger.info(f"New trade saved successfully: {current_trade.trade_id}")
                else:
                    self.logger.error("Failed to save new trade")
                    msgbox.showerror("Error", "Failed to save new trade")
                    return
            else:
                # Existing trade - update it
                success = strategy_manager.db.update_trade(current_trade)
                if success:
                    self.logger.info(f"Trade updated successfully: {current_trade.trade_id}")
                else:
                    self.logger.error("Failed to update trade")
                    msgbox.showerror("Error", "Failed to update trade")
                    return
            
            # Show success message
            msgbox.showinfo("Trade Leg Added", 
                          f"Position '{trading_symbol}' added as trade leg!\n"
                          f"Trade ID: {current_trade.trade_id}\n"
                          f"Quantity: {abs(qty_value)}\n"
                          f"Position Type: {position_type.value}\n"
                          f"Option Type: {option_type.value}\n"
                          f"Strike Price: ₹{strike_price:.2f}\n"
                          f"Entry Price: ₹{trade_leg.entry_price:.2f}")
            
            # Refresh chart 2 to recalculate payoff with new trade leg
            try:
                self.logger.info("Refreshing chart 2 after adding trade leg")
                self._refresh_chart_display()
            except Exception as refresh_error:
                self.logger.warning(f"Could not refresh chart 2: {refresh_error}")
            
            # Refresh the positions window to update the action column
            if parent_window and parent_window.winfo_exists():
                try:
                    # Find the tree widget in the parent window
                    tree_widget = None
                    for widget in parent_window.winfo_children():
                        if isinstance(widget, ttk.Frame):
                            for child in widget.winfo_children():
                                if isinstance(child, ttk.LabelFrame):
                                    for grandchild in child.winfo_children():
                                        if isinstance(grandchild, ttk.Treeview):
                                            tree_widget = grandchild
                                            break
                                    if tree_widget:
                                        break
                                if tree_widget:
                                    break
                            if tree_widget:
                                break
                    
                    if tree_widget:
                        # Found the tree, refresh the window
                        self._refresh_positions_window(parent_window, tree_widget, None, None)
                    else:
                        self.logger.warning("Could not find tree widget for refresh")
                except Exception as refresh_error:
                    self.logger.warning(f"Could not refresh positions window: {refresh_error}")
            else:
                self.logger.warning("Parent window not available for refresh")
            
        except Exception as e:
            self.logger.error(f"Error adding position as trade leg: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to add position as trade leg: {e}")
    
    def _show_add_trade_dialog(self, parent_window, trading_symbol, quantity, average_price, last_price):
        """Show dialog for adding a trade based on the selected position"""
        try:
            # Create a simple dialog window
            dialog = tk.Toplevel(parent_window)
            dialog.title(f"Add Trade - {trading_symbol}")
            dialog.geometry("400x300")
            dialog.resizable(False, False)
            
            # Ensure parent window is visible and mapped
            parent_window.update_idletasks()
            if parent_window.winfo_viewable():
                dialog.transient(parent_window)
                # Center the dialog relative to parent
                parent_x = parent_window.winfo_rootx()
                parent_y = parent_window.winfo_rooty()
                parent_width = parent_window.winfo_width()
                parent_height = parent_window.winfo_height()
                
                dialog_width = 400
                dialog_height = 300
                x = parent_x + (parent_width - dialog_width) // 2
                y = parent_y + (parent_height - dialog_height) // 2
                dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
            else:
                # Fallback: center on screen
                dialog.geometry("+%d+%d" % (200, 200))
            
            # Set grab after window is properly positioned
            dialog.update_idletasks()
            try:
                if dialog.winfo_viewable():
                    dialog.grab_set()
            except tk.TclError as grab_error:
                self.logger.warning(f"Could not set grab on dialog: {grab_error}")
                # Continue without grab - dialog will still work but not be modal
            
            # Main frame
            main_frame = ttk.Frame(dialog, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Title
            title_label = ttk.Label(main_frame, text=f"Add Trade for {trading_symbol}", 
                                  font=("Arial", 14, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Position info frame
            info_frame = ttk.LabelFrame(main_frame, text="Position Information", padding=10)
            info_frame.pack(fill=tk.X, pady=(0, 20))
            
            # Display current position info
            ttk.Label(info_frame, text=f"Trading Symbol: {trading_symbol}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"Current Quantity: {quantity}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"Average Price: {average_price}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"Last Price: {last_price}").pack(anchor=tk.W)
            
            # Trade details frame
            trade_frame = ttk.LabelFrame(main_frame, text="New Trade Details", padding=10)
            trade_frame.pack(fill=tk.X, pady=(0, 20))
            
            # Trade type selection
            ttk.Label(trade_frame, text="Trade Type:").pack(anchor=tk.W)
            trade_type_var = tk.StringVar(value="BUY")
            trade_type_frame = ttk.Frame(trade_frame)
            trade_type_frame.pack(fill=tk.X, pady=(5, 10))
            ttk.Radiobutton(trade_type_frame, text="BUY", variable=trade_type_var, value="BUY").pack(side=tk.LEFT, padx=(0, 20))
            ttk.Radiobutton(trade_type_frame, text="SELL", variable=trade_type_var, value="SELL").pack(side=tk.LEFT)
            
            # Quantity input
            ttk.Label(trade_frame, text="Quantity:").pack(anchor=tk.W)
            quantity_var = tk.StringVar(value="1")
            quantity_entry = ttk.Entry(trade_frame, textvariable=quantity_var, width=20)
            quantity_entry.pack(anchor=tk.W, pady=(5, 10))
            
            # Price input
            ttk.Label(trade_frame, text="Price:").pack(anchor=tk.W)
            price_var = tk.StringVar(value=last_price.replace("₹", "").replace(",", ""))
            price_entry = ttk.Entry(trade_frame, textvariable=price_var, width=20)
            price_entry.pack(anchor=tk.W, pady=(5, 10))
            
            # Buttons frame
            buttons_frame = ttk.Frame(main_frame)
            buttons_frame.pack(fill=tk.X, pady=(10, 0))
            
            def on_add_trade():
                try:
                    trade_type = trade_type_var.get()
                    trade_quantity = int(quantity_var.get())
                    trade_price = float(price_var.get())
                    
                    # Here you would typically call the trading API
                    # For now, just show a confirmation
                    import tkinter.messagebox as msgbox
                    msgbox.showinfo("Trade Added", 
                                  f"Trade added successfully!\n"
                                  f"Type: {trade_type}\n"
                                  f"Quantity: {trade_quantity}\n"
                                  f"Price: ₹{trade_price:.2f}")
                    
                    try:
                        dialog.destroy()
                    except tk.TclError:
                        # Dialog already destroyed
                        pass
                    
                except ValueError as e:
                    import tkinter.messagebox as msgbox
                    msgbox.showerror("Invalid Input", f"Please enter valid numbers: {e}")
                except Exception as e:
                    import tkinter.messagebox as msgbox
                    msgbox.showerror("Error", f"Failed to add trade: {e}")
            
            def on_cancel():
                try:
                    dialog.destroy()
                except tk.TclError:
                    # Dialog already destroyed
                    pass
            
            # Add Trade and Cancel buttons
            ttk.Button(buttons_frame, text="Add Trade", command=on_add_trade).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(buttons_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT)
            
            # Focus on quantity entry
            quantity_entry.focus()
            
            # Add window close handler
            def on_dialog_close():
                try:
                    dialog.destroy()
                except tk.TclError:
                    # Dialog already destroyed
                    pass
            
            dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
            
        except Exception as e:
            self.logger.error(f"Error showing add trade dialog: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to show add trade dialog: {e}")
    
    def _place_iron_condor_orders(self, trade_window, trade):
        """Place all Iron Condor orders using Upstox API"""
        try:
            import tkinter.messagebox as msgbox
            
            # Check if we have access to the agent
            if not hasattr(self, '_current_agent') or not self._current_agent:
                msgbox.showerror("Error", "No trading agent available. Please ensure you're connected to Upstox.")
                return
            
            # Check if agent supports place_order_v3
            if not hasattr(self._current_agent, 'place_order_v3'):
                msgbox.showerror("Error", "Trading agent does not support order placement.")
                return
            
            # Show progress window
            progress_window = tk.Toplevel(trade_window)
            progress_window.title("Placing Orders...")
            progress_window.geometry("400x200")
            progress_window.transient(trade_window)
            progress_window.grab_set()
            
            # Center the progress window
            progress_window.geometry("+%d+%d" % (
                trade_window.winfo_rootx() + 50,
                trade_window.winfo_rooty() + 50
            ))
            
            # Progress frame
            progress_frame = ttk.Frame(progress_window)
            progress_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Progress label
            progress_label = ttk.Label(progress_frame, text="Placing orders...", font=("Arial", 12))
            progress_label.pack(pady=(0, 10))
            
            # Progress bar
            progress_bar = ttk.Progressbar(progress_frame, mode='determinate', maximum=len(trade.legs))
            progress_bar.pack(fill=tk.X, pady=(0, 10))
            
            # Status text
            status_text = tk.Text(progress_frame, height=8, width=50)
            status_text.pack(fill=tk.BOTH, expand=True)
            
            # Place orders for each leg
            successful_orders = 0
            failed_orders = 0
            order_results = []
            
            for i, leg in enumerate(trade.legs, 1):
                try:
                    # Update progress
                    progress_label.config(text=f"Placing order {i}/{len(trade.legs)}: {leg.instrument_name}")
                    progress_bar['value'] = i
                    progress_window.update()
                    
                    # Prepare order details
                    order_details = {
                        'quantity': leg.quantity,
                        'product': 'D',  # Intraday product
                        'validity': 'DAY',
                        'price': leg.entry_price,
                        'instrument_token': leg.instrument,  # This should be the instrument token
                        'order_type': 'MARKET',
                        'transaction_type': 'BUY' if leg.position_type.value == 'LONG' else 'SELL',
                        'tag': f"IC_{trade.trade_id}_Leg{i}"
                    }
                    
                    # Place the order
                    response = self._current_agent.place_order_v3(order_details)
                    order_results.append({
                        'leg': i,
                        'instrument': leg.instrument_name,
                        'status': 'SUCCESS',
                        'response': response
                    })
                    successful_orders += 1
                    
                    # Update status
                    status_text.insert(tk.END, f"✅ Leg {i}: {leg.instrument_name} - Order placed successfully\n")
                    status_text.see(tk.END)
                    progress_window.update()
                    
                except Exception as e:
                    order_results.append({
                        'leg': i,
                        'instrument': leg.instrument_name,
                        'status': 'FAILED',
                        'error': str(e)
                    })
                    failed_orders += 1
                    
                    # Update status
                    status_text.insert(tk.END, f"❌ Leg {i}: {leg.instrument_name} - Failed: {str(e)}\n")
                    status_text.see(tk.END)
                    progress_window.update()
            
            # Final status
            progress_label.config(text="Order placement completed")
            status_text.insert(tk.END, f"\n--- Order Summary ---\n")
            status_text.insert(tk.END, f"Successful: {successful_orders}\n")
            status_text.insert(tk.END, f"Failed: {failed_orders}\n")
            status_text.see(tk.END)
            
            # Add close button
            close_btn = ttk.Button(progress_frame, text="Close", command=progress_window.destroy)
            close_btn.pack(pady=(10, 0))
            
            # Save trade to database if at least one order was successful
            if successful_orders > 0:
                try:
                    from trade_database import TradeDatabase
                    from trade_models import TradeStatus
                    from datetime import datetime
                    
                    # Initialize database
                    db = TradeDatabase("trades.db")
                    
                    # Create trade object for database
                    trade_for_db = trade
                    trade_for_db.status = TradeStatus.OPEN
                    trade_for_db.created_timestamp = datetime.now()
                    
                    # Save trade to database
                    if db.save_trade(trade_for_db):
                        self.logger.info(f"Trade {trade.trade_id} saved to database successfully")
                        status_text.insert(tk.END, f"\n💾 Trade saved to database: {trade.trade_id}\n")
                        status_text.see(tk.END)
                        
                        # Refresh Trade Book if it's open
                        self._refresh_trade_book_after_execution()
                        
                        # Refresh chart display to show new open trades
                        self._refresh_chart_display()
                    else:
                        self.logger.warning(f"Failed to save trade {trade.trade_id} to database")
                        status_text.insert(tk.END, f"\n⚠️ Warning: Failed to save trade to database\n")
                        status_text.see(tk.END)
                        
                except Exception as e:
                    self.logger.error(f"Error saving trade to database: {e}")
                    status_text.insert(tk.END, f"\n❌ Error saving trade to database: {e}\n")
                    status_text.see(tk.END)
            
            # Log results
            self.logger.info(f"Iron Condor order placement completed: {successful_orders} successful, {failed_orders} failed")
            
            # Show final message
            if failed_orders == 0:
                msgbox.showinfo("Success", f"All {successful_orders} orders placed successfully!\n\nTrade saved to database.")
            else:
                msgbox.showwarning("Partial Success", 
                                 f"Order placement completed:\n"
                                 f"✅ Successful: {successful_orders}\n"
                                 f"❌ Failed: {failed_orders}\n\n"
                                 f"Trade saved to database.\n\n"
                                 f"Check the progress window for details.")
            
        except Exception as e:
            self.logger.error(f"Error placing Iron Condor orders: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to place orders: {e}")
    
    def _show_settings_window(self):
        """Show Settings window"""
        try:
            # Create settings window
            settings_window = tk.Toplevel(self.root)
            settings_window.title("Settings")
            settings_window.geometry("800x600")
            settings_window.resizable(True, True)
            
            # Center the window
            settings_window.transient(self.root)
            settings_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(settings_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title_label = ttk.Label(main_frame, text="Settings", font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Settings sections
            # Chart Settings
            chart_frame = ttk.LabelFrame(main_frame, text="Chart Settings", padding=10)
            chart_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Load existing settings
            settings = self._load_settings()
            
            # Chart refresh interval
            ttk.Label(chart_frame, text="Chart Refresh Interval (seconds):").pack(anchor=tk.W)
            refresh_var = tk.StringVar(value=settings.get('refresh_interval', '1'))
            refresh_entry = ttk.Entry(chart_frame, textvariable=refresh_var, width=10)
            refresh_entry.pack(anchor=tk.W, pady=(0, 10))
            
            # Max candles
            ttk.Label(chart_frame, text="Maximum Candles:").pack(anchor=tk.W)
            candles_var = tk.StringVar(value=settings.get('max_candles', '500'))
            candles_entry = ttk.Entry(chart_frame, textvariable=candles_var, width=10)
            candles_entry.pack(anchor=tk.W, pady=(0, 10))
            
            # Trading Settings
            trading_frame = ttk.LabelFrame(main_frame, text="Trading Settings", padding=10)
            trading_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Lot size
            ttk.Label(trading_frame, text="Lot Size:").pack(anchor=tk.W)
            lot_size_var = tk.StringVar(value=settings.get('lot_size', '75'))
            lot_size_entry = ttk.Entry(trading_frame, textvariable=lot_size_var, width=10)
            lot_size_entry.pack(anchor=tk.W, pady=(0, 10))
            
            # Default order type
            ttk.Label(trading_frame, text="Default Order Type:").pack(anchor=tk.W)
            order_type_var = tk.StringVar(value=settings.get('order_type', 'MARKET'))
            order_type_combo = ttk.Combobox(trading_frame, textvariable=order_type_var, 
                                          values=["MARKET", "LIMIT"], state="readonly", width=15)
            order_type_combo.pack(anchor=tk.W, pady=(0, 10))
            
            # Buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(20, 0))
            
            # Save button
            save_button = ttk.Button(button_frame, text="Save Settings", 
                                   command=lambda: self._save_settings(settings_window, {
                                       'refresh_interval': refresh_var.get(),
                                       'max_candles': candles_var.get(),
                                       'lot_size': lot_size_var.get(),
                                       'order_type': order_type_var.get()
                                   }))
            save_button.pack(side=tk.LEFT, padx=(0, 10))
            
            # Cancel button
            cancel_button = ttk.Button(button_frame, text="Cancel", 
                                     command=settings_window.destroy)
            cancel_button.pack(side=tk.LEFT)
            
            # Focus on the window
            settings_window.focus_set()
            
            self.logger.info("Opened Settings window")
            
        except Exception as e:
            self.logger.error(f"Error showing settings window: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open settings window: {e}")
    
    def _show_trade_book_window(self):
        """Show Trade Book window with tabs"""
        try:
            # Create trade book window
            trade_book_window = tk.Toplevel(self.root)
            trade_book_window.title("Trade Book")
            trade_book_window.geometry("1200x700")
            trade_book_window.resizable(True, True)
            
            # Center the window
            trade_book_window.transient(self.root)
            trade_book_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(trade_book_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title_label = ttk.Label(main_frame, text="Trade Book", font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Create notebook for tabs
            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill=tk.BOTH, expand=True)
            
            # Open Trades Tab
            open_frame = ttk.Frame(notebook)
            notebook.add(open_frame, text="Open Trades")
            
            # Create treeview for open trades with tree structure
            open_columns = ("Trade ID", "Strategy", "Status", "Created", "P&L", "Notes")
            self.open_tree = ttk.Treeview(open_frame, columns=open_columns, show="tree headings", height=15)
            
            # Configure columns
            self.open_tree.heading("#0", text="Trade Details")
            self.open_tree.heading("Trade ID", text="Trade ID")
            self.open_tree.heading("Strategy", text="Strategy")
            self.open_tree.heading("Status", text="Status")
            self.open_tree.heading("Created", text="Created")
            self.open_tree.heading("P&L", text="P&L")
            self.open_tree.heading("Notes", text="Notes")
            
            # Set column widths
            self.open_tree.column("#0", width=200)
            self.open_tree.column("Trade ID", width=150)
            self.open_tree.column("Strategy", width=120)
            self.open_tree.column("Status", width=80)
            self.open_tree.column("Created", width=120)
            self.open_tree.column("P&L", width=100)
            self.open_tree.column("Notes", width=200)
            
            # Add scrollbar for open trades
            open_scrollbar = ttk.Scrollbar(open_frame, orient=tk.VERTICAL, command=self.open_tree.yview)
            self.open_tree.configure(yscrollcommand=open_scrollbar.set)
            
            # Pack open trades treeview and scrollbar
            self.open_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            open_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Closed Trades Tab
            closed_frame = ttk.Frame(notebook)
            notebook.add(closed_frame, text="Closed Trades")
            
            # Create treeview for closed trades with tree structure
            closed_columns = ("Trade ID", "Strategy", "Status", "Created", "Closed", "P&L", "Notes")
            self.closed_tree = ttk.Treeview(closed_frame, columns=closed_columns, show="tree headings", height=15)
            
            # Configure columns
            self.closed_tree.heading("#0", text="Trade Details")
            self.closed_tree.heading("Trade ID", text="Trade ID")
            self.closed_tree.heading("Strategy", text="Strategy")
            self.closed_tree.heading("Status", text="Status")
            self.closed_tree.heading("Created", text="Created")
            self.closed_tree.heading("Closed", text="Closed")
            self.closed_tree.heading("P&L", text="P&L")
            self.closed_tree.heading("Notes", text="Notes")
            
            # Set column widths
            self.closed_tree.column("#0", width=200)
            self.closed_tree.column("Trade ID", width=150)
            self.closed_tree.column("Strategy", width=120)
            self.closed_tree.column("Status", width=80)
            self.closed_tree.column("Created", width=120)
            self.closed_tree.column("Closed", width=120)
            self.closed_tree.column("P&L", width=100)
            self.closed_tree.column("Notes", width=200)
            
            # Add scrollbar for closed trades
            closed_scrollbar = ttk.Scrollbar(closed_frame, orient=tk.VERTICAL, command=self.closed_tree.yview)
            self.closed_tree.configure(yscrollcommand=closed_scrollbar.set)
            
            # Pack closed trades treeview and scrollbar
            self.closed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            closed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Bind double-click events to both trees
            self.open_tree.bind("<Double-1>", self._on_tree_double_click)
            self.closed_tree.bind("<Double-1>", self._on_tree_double_click)
            
            # Store references to trees for leg details
            self.open_tree.leg_tree_type = "open"
            self.closed_tree.leg_tree_type = "closed"
            
            # Add sample data
            self._populate_trade_book()
            
            # Footer with buttons
            footer_frame = ttk.Frame(main_frame)
            footer_frame.pack(fill=tk.X, pady=(20, 0))
            
            # Refresh button
            refresh_button = ttk.Button(footer_frame, text="Refresh", 
                                      command=self._refresh_trade_book_tabs)
            refresh_button.pack(side=tk.LEFT, padx=(0, 10))
            
            # Close button
            close_button = ttk.Button(footer_frame, text="Close", 
                                    command=trade_book_window.destroy)
            close_button.pack(side=tk.RIGHT)
            
            # Focus on the window
            trade_book_window.focus_set()
            
            self.logger.info("Opened Trade Book window with tabs")
            
        except Exception as e:
            self.logger.error(f"Error showing trade book window: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open trade book window: {e}")
    
    def _show_info_window(self):
        """Show Info window"""
        try:
            # Create info window
            info_window = tk.Toplevel(self.root)
            info_window.title("Application Information")
            info_window.geometry("800x600")
            info_window.resizable(True, True)
            
            # Center the window
            info_window.transient(self.root)
            info_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(info_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title_label = ttk.Label(main_frame, text="Application Information", font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Info sections
            # Application Info
            app_frame = ttk.LabelFrame(main_frame, text="Application", padding=10)
            app_frame.pack(fill=tk.X, pady=(0, 10))
            
            app_info = """Application: Live Market Data Chart
Version: 1.0.0
Description: Real-time market data visualization and options trading platform
Framework: Python Tkinter + Matplotlib
Broker Support: Upstox, Kite Connect"""
            
            ttk.Label(app_frame, text=app_info, font=("Arial", 10)).pack(anchor=tk.W)
            
            # Features Info
            features_frame = ttk.LabelFrame(main_frame, text="Features", padding=10)
            features_frame.pack(fill=tk.X, pady=(0, 10))
            
            features_info = """• Real-time market data streaming
• Interactive candlestick charts
• Iron Condor strategy builder
• Options chain data integration
• Live P&L calculations
• Order placement via Upstox API
• Historical data analysis
• Multiple broker support"""
            
            ttk.Label(features_frame, text=features_info, font=("Arial", 10)).pack(anchor=tk.W)
            
            # System Info
            system_frame = ttk.LabelFrame(main_frame, text="System Information", padding=10)
            system_frame.pack(fill=tk.X, pady=(0, 10))
            
            import platform
            import sys
            system_info = f"""Python Version: {sys.version.split()[0]}
Platform: {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Tkinter Version: {tk.TkVersion}"""
            
            ttk.Label(system_frame, text=system_info, font=("Arial", 10)).pack(anchor=tk.W)
            
            # Close button
            close_button = ttk.Button(main_frame, text="Close", 
                                    command=info_window.destroy)
            close_button.pack(pady=(20, 0))
            
            # Focus on the window
            info_window.focus_set()
            
            self.logger.info("Opened Info window")
            
        except Exception as e:
            self.logger.error(f"Error showing info window: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open info window: {e}")
    
    def _save_settings(self, window, settings):
        """Save settings and close window"""
        try:
            import json
            import os
            
            # Create config directory if it doesn't exist
            config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
            os.makedirs(config_dir, exist_ok=True)
            
            # Save settings to config file
            config_file = os.path.join(config_dir, 'settings.json')
            with open(config_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            self.logger.info(f"Settings saved to {config_file}: {settings}")
            import tkinter.messagebox as msgbox
            msgbox.showinfo("Success", "Settings saved successfully!")
            window.destroy()
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to save settings: {e}")
    
    def _load_settings(self):
        """Load settings from config file"""
        try:
            import json
            import os
            
            config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    settings = json.load(f)
                self.logger.info(f"Settings loaded from {config_file}: {settings}")
                return settings
            else:
                # Return default settings
                default_settings = {
                    'refresh_interval': '1',
                    'max_candles': '500',
                    'lot_size': '75',
                    'order_type': 'MARKET'
                }
                self.logger.info("No settings file found, using defaults")
                return default_settings
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            # Return default settings on error
            return {
                'refresh_interval': '1',
                'max_candles': '500',
                'lot_size': '75',
                'order_type': 'MARKET'
            }
    
    def _populate_trade_book(self):
        """Populate trade book with data from trades.db database"""
        try:
            from trade_database import TradeDatabase
            from trade_models import TradeStatus
            
            # Initialize database connection
            db = TradeDatabase("trades.db")
            
            # Get open trades from database
            open_trades = db.get_open_trades()
            
            # Populate open trades tree
            for trade in open_trades:
                # Calculate total P&L for the trade
                total_pnl = sum(leg.profit or 0 for leg in trade.legs)
                pnl_str = f"₹{total_pnl:,.0f}" if total_pnl != 0 else "₹0"
                
                # Insert main trade
                trade_item = self.open_tree.insert("", "end", 
                    text=f"{trade.strategy_name} - {trade.trade_id}",
                    values=(trade.trade_id, trade.strategy_name, trade.status.value, 
                           trade.created_timestamp.strftime("%Y-%m-%d %H:%M"), pnl_str, trade.notes or ""),
                    open=False)
                
                # Insert trade legs
                for i, leg in enumerate(trade.legs, 1):
                    leg_text = f"Leg {i}: {leg.position_type.value} {leg.option_type.value} {leg.strike_price:.0f}"
                    
                    # Format entry and exit prices
                    entry_price = f"₹{leg.entry_price:.2f}" if leg.entry_price else "₹0"
                    exit_price = f"₹{leg.exit_price:.2f}" if leg.exit_price else "₹0"
                    pnl = f"₹{leg.profit:.0f}" if leg.profit is not None else "₹0"
                    
                    leg_values = ("", "", "", "", "", f"Entry: {entry_price} | Exit: {exit_price} | P&L: {pnl} | Qty: {leg.quantity} | {leg.instrument}")
                    self.open_tree.insert(trade_item, "end", text=leg_text, values=leg_values)
            
            # Get closed trades from database
            closed_trades = [trade for trade in db.get_all_trades() if trade.status == TradeStatus.CLOSED]
            
            # Populate closed trades tree
            for trade in closed_trades:
                # Calculate total P&L for the trade
                total_pnl = sum(leg.profit or 0 for leg in trade.legs)
                pnl_str = f"₹{total_pnl:,.0f}" if total_pnl != 0 else "₹0"
                
                # Find the latest exit timestamp from legs
                latest_exit = None
                for leg in trade.legs:
                    if leg.exit_timestamp:
                        if latest_exit is None or leg.exit_timestamp > latest_exit:
                            latest_exit = leg.exit_timestamp
                
                closed_time = latest_exit.strftime("%Y-%m-%d %H:%M") if latest_exit else "Unknown"
                
                # Insert main trade
                trade_item = self.closed_tree.insert("", "end", 
                    text=f"{trade.strategy_name} - {trade.trade_id}",
                    values=(trade.trade_id, trade.strategy_name, trade.status.value, 
                           trade.created_timestamp.strftime("%Y-%m-%d %H:%M"), closed_time, pnl_str, trade.notes or ""),
                    open=False)
                
                # Insert trade legs
                for i, leg in enumerate(trade.legs, 1):
                    leg_text = f"Leg {i}: {leg.position_type.value} {leg.option_type.value} {leg.strike_price:.0f}"
                    
                    # Format entry and exit prices
                    entry_price = f"₹{leg.entry_price:.2f}" if leg.entry_price else "₹0"
                    exit_price = f"₹{leg.exit_price:.2f}" if leg.exit_price else "₹0"
                    pnl = f"₹{leg.profit:.0f}" if leg.profit is not None else "₹0"
                    
                    leg_values = ("", "", "", "", "", "", f"Entry: {entry_price} | Exit: {exit_price} | P&L: {pnl} | Qty: {leg.quantity} | {leg.instrument}")
                    self.closed_tree.insert(trade_item, "end", text=leg_text, values=leg_values)
            
            self.logger.info(f"Trade book populated with {len(open_trades)} open trades and {len(closed_trades)} closed trades from database")
            
        except Exception as e:
            self.logger.error(f"Error populating trade book from database: {e}")
            # Fallback to empty trees if database is not available
            self.logger.info("Using empty trade book as fallback")
    
    def _refresh_trade_book_tabs(self):
        """Refresh trade book data for both tabs from database"""
        try:
            # Clear existing data
            for item in self.open_tree.get_children():
                self.open_tree.delete(item)
            
            for item in self.closed_tree.get_children():
                self.closed_tree.delete(item)
            
            # Repopulate with fresh data from database
            self._populate_trade_book()
            
            self.logger.info("Trade book tabs refreshed from database")
        except Exception as e:
            self.logger.error(f"Error refreshing trade book tabs: {e}")
    
    def _refresh_trade_book_after_execution(self):
        """Refresh Trade Book after trade execution (if Trade Book window is open)"""
        try:
            # Check if Trade Book trees exist (indicating the window is open)
            if hasattr(self, 'open_tree') and hasattr(self, 'closed_tree'):
                self.logger.info("Refreshing Trade Book after trade execution")
                self._refresh_trade_book_tabs()
            else:
                self.logger.info("Trade Book window not open, skipping refresh")
        except Exception as e:
            self.logger.error(f"Error refreshing Trade Book after execution: {e}")
    
    def _on_tree_double_click(self, event):
        """Handle double-click on trade tree items"""
        try:
            # Get the clicked item
            item = event.widget.selection()[0] if event.widget.selection() else None
            if not item:
                return
            
            # Get the tree type (open or closed)
            tree_type = getattr(event.widget, 'leg_tree_type', 'unknown')
            
            # Check if it's a leg item (has a parent)
            parent = event.widget.parent(item)
            if parent:  # This is a leg item
                self._show_leg_details_window(item, parent, tree_type, event.widget)
            else:  # This is a trade item
                self.logger.info(f"Double-clicked on trade item: {event.widget.item(item, 'text')}")
                
        except Exception as e:
            self.logger.error(f"Error handling tree double-click: {e}")
    
    def _show_leg_details_window(self, leg_item, trade_item, tree_type, tree_widget):
        """Show detailed leg information window"""
        try:
            from trade_database import TradeDatabase
            from trade_models import TradeStatus
            from datetime import datetime
            
            # Get leg information from the tree
            leg_text = tree_widget.item(leg_item, 'text')
            leg_values = tree_widget.item(leg_item, 'values')
            
            # Get trade information
            trade_text = tree_widget.item(trade_item, 'text')
            trade_values = tree_widget.item(trade_item, 'values')
            trade_id = trade_values[0]  # Trade ID is first column
            
            # Create leg details window
            leg_window = tk.Toplevel(self.root)
            leg_window.title(f"Leg Details - {trade_id}")
            leg_window.geometry("650x650")
            leg_window.resizable(True, True)
            
            # Ensure window appears on top and is properly focused
            leg_window.lift()
            leg_window.attributes('-topmost', True)
            leg_window.focus_force()
            
            # Make window modal (with error handling)
            try:
                leg_window.transient(self.root)
                leg_window.grab_set()
            except tk.TclError:
                # If grab fails, just make it transient
                leg_window.transient(self.root)
            
            # Remove topmost after a short delay to allow proper modal behavior
            leg_window.after(100, lambda: leg_window.attributes('-topmost', False))
            
            # Main frame
            main_frame = ttk.Frame(leg_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title_label = ttk.Label(main_frame, text=f"Trade Leg Details", 
                                  font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Trade info frame
            trade_info_frame = ttk.LabelFrame(main_frame, text="Trade Information", padding=10)
            trade_info_frame.pack(fill=tk.X, pady=(0, 15))
            
            trade_info_text = f"Trade ID: {trade_id}\n"
            trade_info_text += f"Strategy: {trade_values[1]}\n"
            trade_info_text += f"Status: {trade_values[2]}\n"
            trade_info_text += f"Created: {trade_values[3]}"
            
            trade_info_label = ttk.Label(trade_info_frame, text=trade_info_text, 
                                       font=("Arial", 10))
            trade_info_label.pack(anchor=tk.W)
            
            # Leg details frame
            leg_details_frame = ttk.LabelFrame(main_frame, text="Leg Details", padding=10)
            leg_details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            # Parse leg information from the tree display
            leg_info_text = f"Leg: {leg_text}\n"
            leg_info_text += f"Details: {leg_values[5] if len(leg_values) > 5 else 'N/A'}\n"
            
            # Try to get more detailed information from database
            try:
                db = TradeDatabase("trades.db")
                trade = db.get_trade(trade_id)
                if trade and trade.legs:
                    # Find the matching leg
                    leg_index = None
                    for i, leg in enumerate(trade.legs):
                        if f"Leg {i+1}:" in leg_text:
                            leg_index = i
                            break
                    
                    if leg_index is not None:
                        leg = trade.legs[leg_index]
                        leg_info_text = f"Leg {leg_index + 1}: {leg.position_type.value} {leg.option_type.value} {leg.strike_price:.0f}\n"
                        leg_info_text += f"Instrument: {leg.instrument}\n"
                        leg_info_text += f"Instrument Name: {leg.instrument_name}\n"
                        leg_info_text += f"Position: {leg.position_type.value}\n"
                        leg_info_text += f"Option Type: {leg.option_type.value}\n"
                        leg_info_text += f"Strike Price: ₹{leg.strike_price:.0f}\n"
                        leg_info_text += f"Quantity: {leg.quantity}\n"
                        leg_info_text += f"Entry Price: ₹{leg.entry_price:.2f}\n"
                        leg_info_text += f"Entry Time: {leg.entry_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        
                        if leg.exit_price is not None:
                            leg_info_text += f"Exit Price: ₹{leg.exit_price:.2f}\n"
                            leg_info_text += f"Exit Time: {leg.exit_timestamp.strftime('%Y-%m-%d %H:%M:%S') if leg.exit_timestamp else 'N/A'}\n"
                        else:
                            leg_info_text += f"Exit Price: Not exited\n"
                            leg_info_text += f"Exit Time: Not exited\n"
                        
                        if leg.profit is not None:
                            leg_info_text += f"Profit/Loss: ₹{leg.profit:.2f}\n"
                        else:
                            leg_info_text += f"Profit/Loss: Not calculated\n"
                            
            except Exception as e:
                self.logger.error(f"Error fetching leg details from database: {e}")
                leg_info_text += f"Error fetching detailed information: {e}\n"
            
            # Create text widget for leg details
            leg_text_widget = tk.Text(leg_details_frame, height=12, width=70, 
                                    font=("Courier", 10), wrap=tk.WORD)
            leg_text_widget.pack(fill=tk.BOTH, expand=True)
            leg_text_widget.insert(tk.END, leg_info_text)
            leg_text_widget.config(state=tk.DISABLED)
            
            # Add scrollbar for text widget
            leg_scrollbar = ttk.Scrollbar(leg_details_frame, orient=tk.VERTICAL, 
                                        command=leg_text_widget.yview)
            leg_text_widget.configure(yscrollcommand=leg_scrollbar.set)
            leg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Exit trade section (only for open trades)
            if tree_type == "open":
                exit_frame = ttk.LabelFrame(main_frame, text="Exit Trade", padding=10)
                exit_frame.pack(fill=tk.X, pady=(0, 15))
                
                # Exit price input
                price_frame = ttk.Frame(exit_frame)
                price_frame.pack(fill=tk.X, pady=(0, 10))
                
                ttk.Label(price_frame, text="Exit Price (₹):").pack(side=tk.LEFT)
                exit_price_var = tk.StringVar()
                exit_price_entry = ttk.Entry(price_frame, textvariable=exit_price_var, width=15)
                exit_price_entry.pack(side=tk.LEFT, padx=(10, 0))
                
                # Exit button
                def exit_trade_leg():
                    try:
                        exit_price = float(exit_price_var.get())
                        if exit_price <= 0:
                            import tkinter.messagebox as msgbox
                            msgbox.showerror("Error", "Exit price must be greater than 0")
                            return
                        
                        # Update the leg in database
                        db = TradeDatabase("trades.db")
                        trade = db.get_trade(trade_id)
                        if trade and trade.legs:
                            # Find the matching leg
                            leg_index = None
                            for i, leg in enumerate(trade.legs):
                                if f"Leg {i+1}:" in leg_text:
                                    leg_index = i
                                    break
                            
                            if leg_index is not None:
                                leg = trade.legs[leg_index]
                                leg.exit_price = exit_price
                                leg.exit_timestamp = datetime.now()
                                
                                # Calculate profit/loss
                                if leg.position_type.value == 'LONG':
                                    leg.profit = (exit_price - leg.entry_price) * leg.quantity
                                else:  # SHORT
                                    leg.profit = (leg.entry_price - exit_price) * leg.quantity
                                
                                # Update trade in database
                                if db.update_trade(trade):
                                    import tkinter.messagebox as msgbox
                                    msgbox.showinfo("Success", f"Leg {leg_index + 1} exited successfully!\nExit Price: ₹{exit_price:.2f}\nP&L: ₹{leg.profit:.2f}")
                                    
                                    # Refresh trade book
                                    self._refresh_trade_book_tabs()
                                    
                                    # Refresh chart display to show updated open trades
                                    self._refresh_chart_display()
                                    
                                    # Close leg details window
                                    leg_window.destroy()
                                else:
                                    import tkinter.messagebox as msgbox
                                    msgbox.showerror("Error", "Failed to update trade in database")
                            else:
                                import tkinter.messagebox as msgbox
                                msgbox.showerror("Error", "Leg not found in trade")
                        else:
                            import tkinter.messagebox as msgbox
                            msgbox.showerror("Error", "Trade not found in database")
                            
                    except ValueError:
                        import tkinter.messagebox as msgbox
                        msgbox.showerror("Error", "Please enter a valid exit price")
                    except Exception as e:
                        self.logger.error(f"Error exiting trade leg: {e}")
                        import tkinter.messagebox as msgbox
                        msgbox.showerror("Error", f"Failed to exit trade leg: {e}")
                
                exit_button = ttk.Button(exit_frame, text="Exit Trade Leg", 
                                       command=exit_trade_leg)
                exit_button.pack(side=tk.LEFT, padx=(0, 10))
                
                # Help text
                help_label = ttk.Label(exit_frame, 
                                     text="Enter the exit price and click 'Exit Trade Leg' to close this position",
                                     font=("Arial", 9), foreground="gray")
                help_label.pack(side=tk.LEFT)
            else:
                # Show message for closed trades
                closed_info_frame = ttk.LabelFrame(main_frame, text="Trade Status", padding=10)
                closed_info_frame.pack(fill=tk.X, pady=(0, 15))
                
                closed_info_label = ttk.Label(closed_info_frame, 
                                           text="This is a closed trade leg. Exit functionality is not available.",
                                           font=("Arial", 10), foreground="gray")
                closed_info_label.pack()
            
            # Close button
            close_button = ttk.Button(main_frame, text="Close", 
                                    command=leg_window.destroy)
            close_button.pack(pady=(10, 0))
            
            # Focus on the window
            leg_window.focus_set()
            
            self.logger.info(f"Opened leg details window for {trade_id}")
            
        except Exception as e:
            self.logger.error(f"Error showing leg details window: {e}")
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Failed to open leg details window: {e}")
    
    def _refresh_trade_book(self, tree):
        """Refresh trade book data (legacy method for compatibility)"""
        try:
            # Clear existing data
            for item in tree.get_children():
                tree.delete(item)
            
            # Add refreshed data (in real implementation, this would fetch from database)
            sample_trades = [
                ("IC_20240116_120000", "Iron Condor", "Open", "2024-01-16 12:00", "₹0", "NIFTY 24000/24500/25000/25500"),
                ("IC_20240116_110000", "Iron Condor", "Closed", "2024-01-16 11:00", "₹1,250", "NIFTY 23900/24400/24900/25400"),
                ("ST_20240116_100000", "Straddle", "Open", "2024-01-16 10:00", "₹-150", "NIFTY 25000"),
            ]
            
            for trade in sample_trades:
                tree.insert("", "end", values=trade)
            
            self.logger.info("Trade book refreshed")
        except Exception as e:
            self.logger.error(f"Error refreshing trade book: {e}")
    
    def set_agent(self, agent):
        """Set the current trading agent for order placement"""
        self._current_agent = agent
        self.logger.info(f"Trading agent set: {type(agent).__name__}")
        
    def run(self):
        """Run the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self.on_closing()
