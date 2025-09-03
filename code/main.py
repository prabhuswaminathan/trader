#!/usr/bin/env python3
"""
Main application for live market data visualization with flexible broker agent switching.
"""

import logging
import time
import threading
import tkinter as tk
from typing import Optional, Dict, Any
from upstox_agent import UpstoxAgent
from kite_agent import KiteAgent
from chart_visualizer import LiveChartVisualizer, TkinterChartApp
from broker_agent import BrokerAgent

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
        
        # Configuration
        self.instruments = {
            "upstox": {
                "NSE_INDEX|Nifty 50": "Nifty 50",
                "NSE_INDEX|Nifty Bank": "Nifty Bank"
            },
            "kite": {
                256265: "Nifty 50",  # NSE:NIFTY 50
                260105: "Nifty Bank"  # NSE:NIFTY BANK
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
                title=f"Live Market Data - {self.broker_type.upper()}"
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
    
    def _process_upstox_data(self, data):
        """Process Upstox live data"""
        try:
            # Log the received data for debugging
            logger.info(f"Processing Upstox data: {type(data)} - {str(data)[:100]}...")
            
            # Upstox data comes as Protobuf messages, we need to extract the relevant information
            # The data structure depends on the message type (ltp, ohlc, etc.)
            
            # For now, let's handle it as a generic message and try to extract instrument info
            data_str = str(data)
            
            # Check if any of our subscribed instruments are in the data
            for instrument_key in self.instruments[self.broker_type].keys():
                if instrument_key in data_str:
                    # Create a simplified tick data structure for the chart
                    tick_data = {
                        'instrument_key': instrument_key,
                        'data': data,
                        'timestamp': time.time()
                    }
                    
                    # Update the chart with this data
                    self.chart_visualizer.update_data(instrument_key, tick_data)
                    logger.info(f"✓ Updated chart for {instrument_key}")
                    return  # Process only the first matching instrument
            
            # If no specific instrument found, try to process as generic data
            # This helps when the data format doesn't contain the exact instrument key
            logger.info("No specific instrument found in data, processing as generic data")
            
            # Try to extract price information from the data
            import re
            price_match = re.search(r'ltp[:\s]*(\d+\.?\d*)', data_str, re.IGNORECASE)
            if price_match:
                price = float(price_match.group(1))
                # Use the first instrument as default
                first_instrument = list(self.instruments[self.broker_type].keys())[0]
                
                tick_data = {
                    'instrument_key': first_instrument,
                    'data': data,
                    'timestamp': time.time(),
                    'price': price
                }
                
                self.chart_visualizer.update_data(first_instrument, tick_data)
                logger.info(f"✓ Updated chart for {first_instrument} with price {price}")
                    
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
                # Stop the chart animation
                self.chart_app.chart.stop_chart()
                # Update GUI status
                self.chart_app.status_label.config(text="Status: Stopped")
                self.chart_app.start_btn.config(state=tk.NORMAL)
                self.chart_app.stop_btn.config(state=tk.DISABLED)
            
            # Update button commands to use integrated functions
            self.chart_app.start_btn.config(command=integrated_start)
            self.chart_app.stop_btn.config(command=integrated_stop)
            
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
        except:
            pass


if __name__ == "__main__":
    main()
