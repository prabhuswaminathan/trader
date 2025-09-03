import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
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
    def __init__(self, title="Live Market Data", max_candles=100):
        self.title = title
        self.max_candles = max_candles
        self.logger = logging.getLogger("ChartVisualizer")
        
        # Data storage
        self.data_queue = queue.Queue()
        self.candle_data = {}  # {instrument: deque of OHLCV data}
        self.current_prices = {}  # {instrument: current price}
        
        # Chart setup
        try:
            self.fig, self.axes = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
            self.fig.suptitle(self.title, fontsize=16)
            
            # Main price chart
            self.price_ax = self.axes[0]
            self.price_ax.set_title("Price Chart")
            self.price_ax.set_ylabel("Price")
            self.price_ax.grid(True, alpha=0.3)
            
            # Volume chart
            self.volume_ax = self.axes[1]
            self.volume_ax.set_title("Volume")
            self.volume_ax.set_ylabel("Volume")
            self.volume_ax.set_xlabel("Time")
            self.volume_ax.grid(True, alpha=0.3)
        except Exception as e:
            # Fallback for when matplotlib is mocked or not available
            self.logger.warning(f"Could not create matplotlib subplots: {e}")
            self.fig = None
            self.axes = [None, None]
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
        
        # Initialize empty data
        self.candle_data[instrument_key].append({
            'timestamp': datetime.now(),
            'open': 0.0,
            'high': 0.0,
        'low': 0.0,
            'close': 0.0,
            'volume': 0
        })
        
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
            # Upstox data comes as Protobuf messages, we need to extract price information
            # The exact structure depends on the message type
            
            current_price = 0.0
            volume = 0
            
            # Try to extract price from different possible fields
            if isinstance(tick_data, dict):
                # If it's a dictionary, try common price fields
                current_price = tick_data.get('ltp', tick_data.get('last_price', tick_data.get('price', 0)))
                volume = tick_data.get('volume', 0)
            else:
                # If it's a Protobuf message, try to extract price information
                # This is a simplified approach - in reality, you'd need to parse the Protobuf properly
                data_str = str(tick_data)
                
                # Try to find price patterns in the string representation
                import re
                price_match = re.search(r'ltp[:\s]*(\d+\.?\d*)', data_str, re.IGNORECASE)
                if price_match:
                    current_price = float(price_match.group(1))
                
                volume_match = re.search(r'volume[:\s]*(\d+)', data_str, re.IGNORECASE)
                if volume_match:
                    volume = int(volume_match.group(1))
            
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
    
    def _update_candle_data(self, instrument_key, price, volume, timestamp):
        """Update candle data with new tick"""
        if instrument_key not in self.candle_data:
            return
            
        candle_data = self.candle_data[instrument_key]
        
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
        else:
            # Update last candle or create new one
            last_candle = candle_data[-1]
            current_time = timestamp
            
            # Check if we need a new candle (every minute for simplicity)
            if (current_time - last_candle['timestamp']).seconds >= 60:
                # Create new candle
                candle_data.append({
                    'timestamp': current_time,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                })
            else:
                # Update current candle
                last_candle['high'] = max(last_candle['high'], price)
                last_candle['low'] = min(last_candle['low'], price)
                last_candle['close'] = price
                last_candle['volume'] += volume
    
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
        """Draw/update the candlestick and volume charts"""
        try:
            # Check if axes are available
            if not self.price_ax or not self.volume_ax:
                self.logger.warning("Chart axes not available, skipping chart update")
                return
            
            # Clear axes
            self.price_ax.clear()
            self.volume_ax.clear()
            
            # Set up axes
            self.price_ax.set_title("Price Chart")
            self.price_ax.set_ylabel("Price")
            self.price_ax.grid(True, alpha=0.3)
            
            self.volume_ax.set_title("Volume")
            self.volume_ax.set_ylabel("Volume")
            self.volume_ax.set_xlabel("Time")
            self.volume_ax.grid(True, alpha=0.3)
            
            colors = ['blue', 'red', 'green', 'orange', 'purple']
            
            for i, (instrument_key, candle_data) in enumerate(self.candle_data.items()):
                if not candle_data:
                    continue
                    
                color = colors[i % len(colors)]
                
                # Convert to DataFrame for easier handling
                df = pd.DataFrame(list(candle_data))
                if df.empty:
                    continue
                
                # Plot candlesticks (simplified as line chart for now)
                self.price_ax.plot(df['timestamp'], df['close'], 
                                 color=color, linewidth=2, label=instrument_key)
                
                # Plot volume
                self.volume_ax.bar(df['timestamp'], df['volume'], 
                                 color=color, alpha=0.7, width=timedelta(minutes=0.5))
            
            # Add legend
            self.price_ax.legend()
            
            # Format x-axis
            self.price_ax.tick_params(axis='x', rotation=45)
            self.volume_ax.tick_params(axis='x', rotation=45)
            
            # Adjust layout
            plt.tight_layout()
            
        except Exception as e:
            self.logger.error(f"Error drawing charts: {e}")
    
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
        
        # Price display frame
        price_frame = ttk.LabelFrame(main_frame, text="Current Prices")
        price_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.price_labels = {}
        self.update_price_display()
        
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
        
    def update_price_display(self):
        """Update the price display"""
        # Clear existing labels
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.LabelFrame):
                        for price_widget in child.winfo_children():
                            if hasattr(price_widget, 'destroy'):
                                price_widget.destroy()
        
        # Add new price labels
        prices = self.chart.get_current_prices()
        for instrument, price in prices.items():
            label = ttk.Label(self.root, text=f"{instrument}: {price:.2f}")
            label.pack()
        
        # Schedule next update
        self.root.after(1000, self.update_price_display)
        
    def run(self):
        """Run the application"""
        self.root.mainloop()
