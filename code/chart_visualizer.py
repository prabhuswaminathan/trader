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
            
            self.logger.info(f"Processed Upstox tick for {instrument_key}: price={current_price}, volume={volume}")
            
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
                self.candle_data[instrument_key] = []
            
            # Convert timestamp to datetime if it's a string
            timestamp = ohlc_data.get('timestamp')
            if isinstance(timestamp, str):
                from datetime import datetime
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
            
            # Add to candle data
            self.candle_data[instrument_key].append(candle)
            
            # Update current price to close price
            self.current_prices[instrument_key] = candle['close']
            
            # Limit number of candles to keep chart responsive
            max_candles = self.max_candles
            if len(self.candle_data[instrument_key]) > max_candles:
                self.candle_data[instrument_key] = self.candle_data[instrument_key][-max_candles:]
            
            self.logger.info(f"Added complete OHLC candle for {instrument_key}: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}, V={candle['volume']}")
            
            # Immediately update the chart if it's running
            if self.is_running:
                self._draw_charts()
                # Force matplotlib to redraw
                if hasattr(self, 'fig') and self.fig:
                    self.fig.canvas.draw_idle()
                
        except Exception as e:
            self.logger.error(f"Error adding complete candle: {e}")
    
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
            self.logger.info(f"Created first candle for {instrument_key}: O={price}, H={price}, L={price}, C={price}, V={volume}")
            
            # Immediately update the chart if it's running
            if self.is_running:
                self._draw_charts()
        else:
            # Update last candle or create new one
            last_candle = candle_data[-1]
            current_time = timestamp
            
            # Check if we need a new candle (every N minutes as configured)
            time_diff = (current_time - last_candle['timestamp']).total_seconds()
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
                self.logger.info(f"Created new candle for {instrument_key}: O={price}, H={price}, L={price}, C={price}, V={volume}")
                
                # Immediately update the chart if it's running
                if self.is_running:
                    self._draw_charts()
            else:
                # Update current candle
                last_candle['high'] = max(last_candle['high'], price)
                last_candle['low'] = min(last_candle['low'], price)
                last_candle['close'] = price
                last_candle['volume'] += volume
                self.logger.info(f"Updated candle for {instrument_key}: O={last_candle['open']}, H={last_candle['high']}, L={last_candle['low']}, C={last_candle['close']}, V={last_candle['volume']}")
                
                # Immediately update the chart if it's running
                if self.is_running:
                    self._draw_charts()
    
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
            self.price_ax.set_xlabel("Time")
            self.price_ax.grid(True, alpha=0.3)
            
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
            
            # Update Y-axis scale based on price range
            self._update_y_axis_scale()
            
            # Format x-axis with time display
            self._format_x_axis_time()
            
            # Adjust layout
            plt.tight_layout()
            
        except Exception as e:
            self.logger.error(f"Error drawing charts: {e}")
    
    def _format_x_axis_time(self):
        """Format X-axis to display time with 1-hour intervals"""
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
            
            # Set up time formatting
            # Major ticks every 1 hour
            hour_locator = HourLocator(interval=1)
            self.price_ax.xaxis.set_major_locator(hour_locator)
            
            # Format time display as HH:MM
            time_formatter = DateFormatter('%H:%M')
            self.price_ax.xaxis.set_major_formatter(time_formatter)
            
            # Rotate x-axis labels for better readability
            self.price_ax.tick_params(axis='x', rotation=45)
            
            # Set x-axis limits based on data range
            min_time = min(all_timestamps)
            max_time = max(all_timestamps)
            
            # Add some padding (30 minutes on each side)
            padding = timedelta(minutes=30)
            self.price_ax.set_xlim(min_time - padding, max_time + padding)
            
        except Exception as e:
            self.logger.error(f"Error formatting X-axis time: {e}")
    
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
            
            # Calculate candlestick width
            candle_width = timedelta(minutes=self.candle_interval_minutes * 0.6)
            
            for i, row in df.iterrows():
                timestamp = row['timestamp']
                open_price = row['open']
                high_price = row['high']
                low_price = row['low']
                close_price = row['close']
                
                # Determine candle color (green for up, red for down)
                candle_color = 'green' if close_price >= open_price else 'red'
                edge_color = 'darkgreen' if close_price >= open_price else 'darkred'
                
                # Draw the wick lines (upper and lower shadows)
                # Upper wick: from body top to high
                body_top = max(open_price, close_price)
                body_bottom = min(open_price, close_price)
                
                # Upper wick (if high > body top)
                if high_price > body_top:
                    self.price_ax.plot([timestamp, timestamp], [body_top, high_price], 
                                     color='black', linewidth=1.5)
                
                # Lower wick (if low < body bottom)
                if low_price < body_bottom:
                    self.price_ax.plot([timestamp, timestamp], [low_price, body_bottom], 
                                     color='black', linewidth=1.5)
                
                # Draw the open-close rectangle (body)
                if close_price >= open_price:
                    # Bullish candle (close >= open)
                    self.price_ax.bar(timestamp, close_price - open_price, 
                                    bottom=open_price, width=candle_width,
                                    color=candle_color, edgecolor=edge_color, linewidth=1.5)
                else:
                    # Bearish candle (close < open)
                    self.price_ax.bar(timestamp, open_price - close_price, 
                                    bottom=close_price, width=candle_width,
                                    color=candle_color, edgecolor=edge_color, linewidth=1.5)
            
            # No line chart overlay - pure candlestick chart
            
        except Exception as e:
            self.logger.error(f"Error plotting candlesticks: {e}")
            # Fallback to simple line chart
            self.price_ax.plot(df['timestamp'], df['close'], 
                             color='blue', linewidth=2, label=instrument_key)
    
    def start_chart(self):
        """Start the live chart"""
        if self.is_running:
            return
            
        self.is_running = True
        self.stop_event.clear()
        
        # Start animation
        self.ani = animation.FuncAnimation(
            self.fig, self._animate, interval=1000, blit=False
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


class TkinterChartApp:
    """Tkinter-based application for the live chart"""
    
    def __init__(self, chart_visualizer):
        self.chart = chart_visualizer
        self.root = tk.Tk()
        self.root.title("Live Market Data Chart")
        self.root.geometry("1200x800")
        
        self.setup_ui()
        
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
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Status: Stopped")
        self.status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Chart frame
        chart_frame = ttk.Frame(main_frame)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # Embed matplotlib figure
        self.canvas = FigureCanvasTkAgg(self.chart.fig, chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
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
    
    def start_timer(self):
        """Placeholder for start timer - will be overridden by main app"""
        self.status_label.config(text="Status: Start Timer button clicked")
    
    def stop_timer(self):
        """Placeholder for stop timer - will be overridden by main app"""
        self.status_label.config(text="Status: Stop Timer button clicked")

        
    def run(self):
        """Run the application"""
        self.root.mainloop()
