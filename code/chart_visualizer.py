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
        
        # Tooltip functionality
        self.tooltip = None
        self.tooltip_annotation = None
        self.candlestick_patches = {}  # Store candlestick patches for hover detection
        
        # Chart setup - Single chart for price only
        try:
            self.fig, self.price_ax = plt.subplots(1, 1, figsize=(12, 8))
            self.fig.suptitle(self.title, fontsize=16)
            
            # Main price chart
            self.price_ax.set_title("Nifty 50 - Intraday Candlestick Chart (5-Minute)")
            self.price_ax.set_ylabel("Price (₹)")
            self.price_ax.set_xlabel("Time")
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
        
    def add_instrument(self, instrument_key, instrument_name=None):
        """Add a new instrument to track"""
        if instrument_name is None:
            instrument_name = instrument_key
            
        self.candle_data[instrument_key] = deque(maxlen=self.max_candles)
        self.current_prices[instrument_key] = 0.0
        
        # Don't initialize with empty data - let the first tick create the first candle
        
        self.logger.info(f"Added instrument: {instrument_name} ({instrument_key})")
        
    def update_data(self, instrument_key, tick_data):
        """Update data for a specific instrument"""
        try:
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
    
    def _process_upstox_tick(self, instrument_key, tick_data):
        """Process Upstox tick data"""
        try:
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
        """Store historical data in the chart for display"""
        try:
            if not historical_data:
                self.logger.warning(f"No historical data to store for {instrument_key}")
                return
            
            # Clear existing data for this instrument
            if instrument_key in self.candle_data:
                self.candle_data[instrument_key].clear()
            else:
                self.candle_data[instrument_key] = deque(maxlen=self.max_candles)
            
            # Store historical data
            for candle in historical_data:
                self.candle_data[instrument_key].append(candle)
            
            # Update current price to the latest close price
            if historical_data:
                latest_candle = historical_data[-1]
                self.current_prices[instrument_key] = latest_candle.get('close', 0)
                
                # Update last update time
                latest_timestamp = latest_candle.get('timestamp')
                if isinstance(latest_timestamp, datetime):
                    self.last_update_time = latest_timestamp
                else:
                    self.last_update_time = datetime.fromtimestamp(latest_timestamp)
            
            self.logger.info(f"Stored {len(historical_data)} historical candles for {instrument_key}")
            
            # Force chart update to display the data
            if self.is_running:
                self.force_chart_update()
            
        except Exception as e:
            self.logger.error(f"Error storing historical data for {instrument_key}: {e}")
    
    def _update_candle_data(self, instrument_key, price, volume, timestamp):
        """Update candle data with new tick"""
        if instrument_key not in self.candle_data:
            return
            
        candle_data = self.candle_data[instrument_key]
        
        # Convert timestamp to datetime if it's a float
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        
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
                
                # Chart will be updated by animation loop
            else:
                # Update current candle
                last_candle['high'] = max(last_candle['high'], price)
                last_candle['low'] = min(last_candle['low'], price)
                last_candle['close'] = price
                last_candle['volume'] += volume
                self.logger.debug(f"Updated candle for {instrument_key}: O={last_candle['open']}, H={last_candle['high']}, L={last_candle['low']}, C={last_candle['close']}, V={last_candle['volume']}")
                
                # Chart will be updated by animation loop
    
    def _animate(self, frame):
        """Animation function to update charts"""
        try:
            # Process queued data
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
            
            # Update charts
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
            
            # Set up axes
            self.price_ax.set_title("Nifty 50 - Intraday Candlestick Chart (5-Minute)")
            self.price_ax.set_ylabel("Price (₹)")
            
            # Get last update time for x-axis label
            last_update_time = self._get_last_update_time()
            xlabel_text = f"Time ({last_update_time})" if last_update_time else "Time"
            self.price_ax.set_xlabel(xlabel_text)
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
            
            # Adjust layout
            plt.tight_layout()
            
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
                        all_timestamps.append(timestamp)
                    else:
                        # Convert timestamp to datetime if needed
                        all_timestamps.append(datetime.fromtimestamp(timestamp))
            
            if not all_timestamps:
                return
            
            # Sort timestamps
            all_timestamps.sort()
            
            # Calculate time range
            min_time = all_timestamps[0]
            max_time = all_timestamps[-1]
            time_range = max_time - min_time
            
            # Convert to matplotlib date format
            import matplotlib.dates as mdates
            min_time_mpl = mdates.date2num(min_time)
            max_time_mpl = mdates.date2num(max_time)
            
            # Custom formatter to convert UTC to IST for display
            def ist_formatter(x, pos):
                from datetime import timedelta
                # Convert matplotlib date number to datetime
                dt = mdates.num2date(x)
                # Add 5 hours 30 minutes to convert UTC to IST
                ist_dt = dt + timedelta(hours=5, minutes=30)
                return ist_dt.strftime('%H:%M')
            
            # Set up time formatting based on data range
            if time_range.total_seconds() <= 3600:  # Less than 1 hour
                # Show 5-minute intervals
                minute_locator = mdates.MinuteLocator(interval=5)
                self.price_ax.xaxis.set_major_locator(minute_locator)
            elif time_range.total_seconds() <= 14400:  # Less than 4 hours
                # Show 15-minute intervals
                minute_locator = mdates.MinuteLocator(interval=15)
                self.price_ax.xaxis.set_major_locator(minute_locator)
            else:
                # Show 1-hour intervals
                hour_locator = mdates.HourLocator(interval=1)
                self.price_ax.xaxis.set_major_locator(hour_locator)
            
            # Apply the IST formatter
            self.price_ax.xaxis.set_major_formatter(plt.FuncFormatter(ist_formatter))
            
            # Rotate x-axis labels for better readability
            self.price_ax.tick_params(axis='x', rotation=45)
            
            # Set x-axis limits based on data range
            # Add some padding (5% on each side)
            padding = time_range * 0.05
            self.price_ax.set_xlim(min_time - padding, max_time + padding)
            
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
                self.price_ax.tick_params(axis='x', rotation=45)
                # Set a simple time formatter
                import matplotlib.dates as mdates
                self.price_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
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
            
            # Sort by timestamp to ensure proper order
            df = df.sort_values('timestamp')
            
            # Convert timestamps to matplotlib date format for proper plotting
            import matplotlib.dates as mdates
            df['timestamp_mpl'] = df['timestamp'].apply(lambda x: mdates.date2num(x) if isinstance(x, datetime) else mdates.date2num(datetime.fromtimestamp(x)))
            
            # Calculate candlestick width based on data frequency
            if len(df) > 1:
                time_diff = (df['timestamp'].iloc[1] - df['timestamp'].iloc[0]).total_seconds()
                candle_width = time_diff * 0.8 / (24 * 3600)  # Convert to days for matplotlib
            else:
                candle_width = (self.candle_interval_minutes * 60) * 0.8 / (24 * 3600)  # Convert to days
            
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
                if high_price > body_top:
                    self.price_ax.plot([timestamp_mpl, timestamp_mpl], [body_top, high_price], 
                                     color='black', linewidth=1.5, alpha=0.8)
                
                # Lower wick (if low < body bottom)
                if low_price < body_bottom:
                    self.price_ax.plot([timestamp_mpl, timestamp_mpl], [low_price, body_bottom], 
                                     color='black', linewidth=1.5, alpha=0.8)
                
                # Draw the open-close rectangle (body)
                if close_price >= open_price:
                    # Bullish candle (close >= open)
                    self.price_ax.bar(timestamp_mpl, close_price - open_price, 
                                    bottom=open_price, width=candle_width,
                                    color=candle_color, edgecolor=edge_color, linewidth=1.5, alpha=0.8)
                else:
                    # Bearish candle (close < open)
                    self.price_ax.bar(timestamp_mpl, open_price - close_price, 
                                    bottom=close_price, width=candle_width,
                                    color=candle_color, edgecolor=edge_color, linewidth=1.5, alpha=0.8)
            
            # No line chart overlay - pure candlestick chart
            
        except Exception as e:
            self.logger.error(f"Error plotting candlesticks: {e}")
            # Fallback to simple line chart
            try:
                df_sorted = df.sort_values('timestamp')
                # Convert timestamps for matplotlib
                import matplotlib.dates as mdates
                timestamps_mpl = df_sorted['timestamp'].apply(lambda x: mdates.date2num(x) if isinstance(x, datetime) else mdates.date2num(datetime.fromtimestamp(x)))
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
        
        self.logger.info("Live chart started")
    
    def stop_chart(self):
        """Stop the live chart"""
        if not self.is_running:
            return
            
        self.is_running = False
        self.stop_event.set()
        
        if self.ani:
            self.ani.event_source.stop()
        
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
        """Set full historical data for scrolling functionality"""
        self.historical_data[instrument_key] = historical_data
        self.current_view_start = max(0, len(historical_data) - self.view_size)
        self.logger.info(f"Stored {len(historical_data)} historical candles for {instrument_key}")
    
    def set_status_callback(self, callback):
        """Set callback function for status updates"""
        self.status_callback = callback
    
    def scroll_left(self, instrument_key):
        """Scroll to show earlier data"""
        if instrument_key not in self.historical_data:
            return False
        
        historical_data = self.historical_data[instrument_key]
        if self.current_view_start > 0:
            self.current_view_start = max(0, self.current_view_start - self.view_size)
            self._update_display_data(instrument_key)
            return True
        return False
    
    def scroll_right(self, instrument_key):
        """Scroll to show later data"""
        if instrument_key not in self.historical_data:
            return False
        
        historical_data = self.historical_data[instrument_key]
        max_start = max(0, len(historical_data) - self.view_size)
        if self.current_view_start < max_start:
            self.current_view_start = min(max_start, self.current_view_start + self.view_size)
            self._update_display_data(instrument_key)
            return True
        return False
    
    def _update_display_data(self, instrument_key):
        """Update the displayed data based on current view position"""
        if instrument_key not in self.historical_data:
            return
        
        historical_data = self.historical_data[instrument_key]
        end_index = min(self.current_view_start + self.view_size, len(historical_data))
        view_data = historical_data[self.current_view_start:end_index]
        
        # Clear and update display data
        if instrument_key in self.candle_data:
            self.candle_data[instrument_key].clear()
        
        for candle in view_data:
            if instrument_key not in self.candle_data:
                self.candle_data[instrument_key] = deque(maxlen=self.max_candles)
            self.candle_data[instrument_key].append(candle)
            self.current_prices[instrument_key] = candle['close']
        
        self.logger.info(f"Updated view: showing candles {self.current_view_start}-{end_index} of {len(historical_data)}")
        
        # Update status if we have a status callback
        if hasattr(self, 'status_callback'):
            self.status_callback(f"View: {self.current_view_start}-{end_index} of {len(historical_data)} candles")
    
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
                if not self.ani.event_source.is_alive():
                    self.logger.warning("Chart animation stopped, restarting...")
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
            
            # Initialize tooltip annotation
            self.tooltip_annotation = self.price_ax.annotate('', xy=(0, 0), xytext=(20, 20),
                                                           textcoords="offset points",
                                                           bbox=dict(boxstyle="round,pad=0.3", 
                                                                   facecolor="lightblue", 
                                                                   edgecolor="black",
                                                                   alpha=0.8),
                                                           arrowprops=dict(arrowstyle="->",
                                                                         connectionstyle="arc3,rad=0"),
                                                           fontsize=10,
                                                           visible=False)
            
            self.logger.info("Tooltip functionality initialized (hover and click)")
            
        except Exception as e:
            self.logger.error(f"Error setting up tooltips: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_hover(self, event):
        """Handle mouse hover events for tooltips"""
        try:
            if not self.tooltip_annotation or not self.price_ax:
                return
            
            # Check if mouse is over the chart
            if event.inaxes != self.price_ax:
                self.tooltip_annotation.set_visible(False)
                self.fig.canvas.draw_idle()
                return
            
            # Find the closest candlestick
            closest_candle = self._find_closest_candlestick(event.xdata, event.ydata)
            
            if closest_candle:
                # Show tooltip
                self._show_tooltip(event, closest_candle)
                self.logger.debug(f"Hover tooltip shown for {closest_candle['instrument']}")
            else:
                # Hide tooltip
                self.tooltip_annotation.set_visible(False)
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
                self.tooltip_annotation.set_visible(False)
                self.fig.canvas.draw_idle()
                self.logger.debug("Click event: no closest candle found")
                
        except Exception as e:
            self.logger.error(f"Error in click event: {e}")
            import traceback
            traceback.print_exc()
    
    def _find_closest_candlestick(self, x, y):
        """Find the closest candlestick to the mouse position"""
        try:
            if not self.candle_data or x is None or y is None:
                return None
            
            closest_candle = None
            min_distance = float('inf')
            
            # Check all instruments
            for instrument_key, candle_list in self.candle_data.items():
                if not candle_list:
                    continue
                
                # Check each candle
                for candle in candle_list:
                    candle_time = candle['timestamp']
                    
                    # Convert timestamp to matplotlib time format
                    if isinstance(candle_time, datetime):
                        candle_x = candle_time
                    else:
                        candle_x = datetime.fromtimestamp(candle_time)
                    
                    # Calculate distance (considering both time and price)
                    # Convert both to timestamps to avoid timezone issues
                    candle_timestamp = candle_x.timestamp()
                    if hasattr(x, '__float__'):
                        mouse_timestamp = x
                    else:
                        mouse_timestamp = x.timestamp() if hasattr(x, 'timestamp') else x
                    
                    time_diff = abs(candle_timestamp - mouse_timestamp)
                    price_diff = abs(y - candle['close'])
                    
                    # Very lenient distance calculation - focus on time proximity only
                    # Use time difference as primary factor, ignore price for click detection
                    time_weight = 1.0
                    price_weight = 0.01  # Very low weight for price
                    
                    distance = time_diff * time_weight + price_diff * price_weight
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_candle = {
                            'instrument': instrument_key,
                            'candle': candle,
                            'x': candle_x,
                            'y': candle['close']
                        }
            
            # Very lenient threshold for better click detection
            # Allow clicks within 8 hours (28800 seconds) - very generous
            if min_distance < 28800:  # Within 8 hours
                return closest_candle
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding closest candlestick: {e}")
            return None
    
    def _show_tooltip(self, event, candle_info):
        """Show tooltip with OHLC data"""
        try:
            if not self.tooltip_annotation:
                return
            
            candle = candle_info['candle']
            instrument = candle_info['instrument']
            
            # Format timestamp
            timestamp = candle['timestamp']
            if isinstance(timestamp, datetime):
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            
            # Create tooltip text
            tooltip_text = f"{instrument}\n"
            tooltip_text += f"Time: {time_str}\n"
            tooltip_text += f"Open: ₹{candle['open']:.2f}\n"
            tooltip_text += f"High: ₹{candle['high']:.2f}\n"
            tooltip_text += f"Low: ₹{candle['low']:.2f}\n"
            tooltip_text += f"Close: ₹{candle['close']:.2f}\n"
            tooltip_text += f"Volume: {candle['volume']:,.0f}"
            
            # Update tooltip
            self.tooltip_annotation.set_text(tooltip_text)
            self.tooltip_annotation.xy = (event.xdata, event.ydata)
            self.tooltip_annotation.set_visible(True)
            
            # Force redraw
            self.fig.canvas.draw_idle()
            
        except Exception as e:
            self.logger.error(f"Error showing tooltip: {e}")
    
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
        self.root = tk.Tk()
        self.root.title("Live Market Data Chart - 2x2 Grid Layout")
        self.root.geometry("1400x900")
        
        # Set up proper window close handling
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
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
        
        # Maximize window after UI is set up
        self.root.after(100, self._maximize_window)
    
    def _maximize_window(self):
        """Maximize the window using multiple methods"""
        try:
            # Method 1: Linux/Unix attributes
            self.root.attributes('-zoomed', True)
        except:
            pass
        
        try:
            # Method 2: Windows state
            self.root.state('zoomed')
        except:
            pass
        
        try:
            # Method 3: Use geometry to fill screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        except:
            pass
        
        try:
            # Method 4: Use wm_attributes
            self.root.wm_attributes('-zoomed', True)
        except:
            pass
        
        # Force update and raise window
        self.root.update_idletasks()
        self.root.lift()
        self.root.focus_force()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Buttons
        self.start_btn = ttk.Button(control_frame, text="Start Chart", 
                                   command=self.start_chart)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Chart", 
                                  command=self.stop_chart)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Data fetch buttons
        self.fetch_historical_btn = ttk.Button(control_frame, text="Fetch Historical", 
                                              command=self.fetch_historical)
        self.fetch_historical_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.fetch_intraday_btn = ttk.Button(control_frame, text="Fetch Intraday", 
                                            command=self.fetch_intraday)
        self.fetch_intraday_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Timer buttons
        self.start_timer_btn = ttk.Button(control_frame, text="Start Timer", 
                                         command=self.start_timer)
        self.start_timer_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_timer_btn = ttk.Button(control_frame, text="Stop Timer", 
                                        command=self.stop_timer)
        self.stop_timer_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        
        # Strategy management button
        self.manage_strategies_btn = ttk.Button(control_frame, text="Manage Strategies", 
                                               command=self.manage_strategies)
        self.manage_strategies_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Chart scrolling controls
        self.scroll_left_btn = ttk.Button(control_frame, text="← Earlier", 
                                        command=self.scroll_chart_left)
        self.scroll_left_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.scroll_right_btn = ttk.Button(control_frame, text="Later →", 
                                         command=self.scroll_chart_right)
        self.scroll_right_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Status: Stopped")
        self.status_label.pack(side=tk.LEFT, padx=(20, 0))
        
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
            
            # Title
            title_label = ttk.Label(self.grid2_frame, text="Strategy Display", 
                                  font=("Arial", 14, "bold"))
            title_label.pack(pady=(10, 5))
            
            # Initial state message
            initial_label = ttk.Label(self.grid2_frame, 
                                    text="No active strategies\nUse 'Manage Strategies' to create or view strategies", 
                                    font=("Arial", 12),
                                    foreground="gray",
                                    justify="center")
            initial_label.pack(pady=20)
            
            # Last updated
            last_updated = datetime.now().strftime("%H:%M:%S")
            update_label = ttk.Label(self.grid2_frame, 
                                   text=f"Initialized: {last_updated}", 
                                   font=("Arial", 8), 
                                   foreground="gray")
            update_label.pack(pady=(10, 5))
            
        except Exception as e:
            print(f"Error initializing Grid 2 content: {e}")
    
    def display_iron_condor_strategy(self, trade, spot_price, payoff_data):
        """Display Iron Condor strategy chart in Grid 2"""
        try:
            # Clear any existing content
            for widget in self.grid2_frame.winfo_children():
                widget.destroy()
            
            # Update title
            title_label = ttk.Label(self.grid2_frame, text="Iron Condor Strategy", 
                                  font=("Arial", 14, "bold"))
            title_label.pack(pady=(10, 5))
            
            # Create matplotlib figure for Iron Condor
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(6, 4))
            
            # Plot payoff curve
            ax.plot(payoff_data["price_range"], payoff_data["payoffs"], 
                   'b-', linewidth=2, label='Payoff at Expiry')
            
            # Mark current spot price
            ax.axvline(x=spot_price, color='red', linestyle='--', 
                      label=f'Current Spot: {spot_price}')
            
            # Mark strikes
            strikes = [leg.strike_price for leg in trade.legs]
            for strike in strikes:
                ax.axvline(x=strike, color='gray', linestyle=':', alpha=0.7)
            
            # Mark breakeven points
            for be in payoff_data["breakevens"]:
                ax.axvline(x=be, color='green', linestyle=':', alpha=0.7)
                ax.text(be, payoff_data["max_profit"] * 0.1, f'BE: {be}', 
                       rotation=90, ha='right', va='bottom', fontsize=8)
            
            # Formatting
            ax.set_xlabel('NIFTY Price at Expiry')
            ax.set_ylabel('Profit/Loss (₹)')
            ax.set_title(f'Iron Condor - {trade.trade_id}')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
            
            # Add strategy details
            strategy_text = f"""Strategy Details:
Strikes: {sorted(strikes)}
Max Profit: ₹{payoff_data["max_profit"]:.0f}
Max Loss: ₹{payoff_data["max_loss"]:.0f}
Current P&L: ₹{payoff_data["current_payoff"]:.0f}"""
            
            ax.text(0.02, 0.98, strategy_text, transform=ax.transAxes,
                   verticalalignment='top', fontsize=8,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            
            # Embed in grid 2
            canvas = FigureCanvasTkAgg(fig, self.grid2_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Add trade info below chart
            info_frame = ttk.Frame(self.grid2_frame)
            info_frame.pack(fill=tk.X, pady=(5, 0))
            
            trade_info = ttk.Label(info_frame, 
                                 text=f"Trade: {trade.trade_id} | Status: {trade.status.value}",
                                 font=("Arial", 8))
            trade_info.pack()
            
            self.logger.info(f"Displayed Iron Condor strategy in Grid 2: {trade.trade_id}")
            
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
        
    def start_chart(self):
        """Start the chart"""
        self.chart.start_chart()
        self.status_label.config(text="Status: Running")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
    def stop_chart(self):
        """Stop the chart"""
        self.chart.stop_chart()
        self.status_label.config(text="Status: Stopped")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def fetch_historical(self):
        """Placeholder for fetch historical data - will be overridden by main app"""
        self.status_label.config(text="Status: Fetch Historical button clicked")
    
    def fetch_intraday(self):
        """Placeholder for fetch intraday data - will be overridden by main app"""
        self.status_label.config(text="Status: Fetch Intraday button clicked")
    
    def manage_strategies(self):
        """Placeholder for manage strategies - will be overridden by main app"""
        self.status_label.config(text="Status: Manage Strategies button clicked")
    
    def scroll_chart_left(self):
        """Scroll chart to show earlier data"""
        try:
            # Get the primary instrument (assuming Nifty 50)
            primary_instrument = "NSE_INDEX|Nifty 50"
            if self.chart.scroll_left(primary_instrument):
                self.chart.force_chart_update()
                self.logger.info("Scrolled chart left to show earlier data")
            else:
                self.logger.info("Already at the beginning of historical data")
        except Exception as e:
            self.logger.error(f"Error scrolling chart left: {e}")
    
    def scroll_chart_right(self):
        """Scroll chart to show later data"""
        try:
            # Get the primary instrument (assuming Nifty 50)
            primary_instrument = "NSE_INDEX|Nifty 50"
            if self.chart.scroll_right(primary_instrument):
                self.chart.force_chart_update()
                self.logger.info("Scrolled chart right to show later data")
            else:
                self.logger.info("Already at the end of historical data")
        except Exception as e:
            self.logger.error(f"Error scrolling chart right: {e}")
    
    def update_status(self, message):
        """Update the status label with scrolling information"""
        try:
            if hasattr(self, 'status_label'):
                self.status_label.config(text=f"Status: {message}")
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
    
    def start_timer(self):
        """Placeholder for start timer - will be overridden by main app"""
        self.status_label.config(text="Status: Start Timer button clicked")
    
    def stop_timer(self):
        """Placeholder for stop timer - will be overridden by main app"""
        self.status_label.config(text="Status: Stop Timer button clicked")
    
    
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
        
    def run(self):
        """Run the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self.on_closing()
