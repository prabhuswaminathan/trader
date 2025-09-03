# Market Data Live Visualization System

A flexible Python application for real-time market data visualization with support for multiple broker APIs (Upstox and Kite) and live candlestick charting.

## Features

- **Flexible Broker Support**: Switch between Upstox and Kite brokers seamlessly
- **Live Data Streaming**: Real-time market data feed with WebSocket connections
- **Interactive Charts**: Live candlestick charts with volume indicators
- **Modular Architecture**: Clean separation of concerns with abstract base classes
- **Easy Switching**: Runtime broker switching without restarting the application

## Architecture

### Core Components

1. **BrokerAgent** (Abstract Base Class): Defines the interface for all broker implementations
2. **UpstoxAgent**: Implementation for Upstox broker API
3. **KiteAgent**: Implementation for Kite broker API
4. **LiveChartVisualizer**: Real-time chart visualization with matplotlib
5. **MarketDataApp**: Main application orchestrating all components

### Class Hierarchy

```
BrokerAgent (Abstract)
├── UpstoxAgent
└── KiteAgent

LiveChartVisualizer
└── TkinterChartApp

MarketDataApp (Main orchestrator)
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd market
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys**:
   - Create a `keys.env` file in the project root
   - Add your broker API credentials:
     ```
     UPSTOX_API_KEY=your_upstox_api_key
     UPSTOX_API_SECRET=your_upstox_api_secret
     ```

## Usage

### Basic Usage

Run the main application with default Upstox agent:

```bash
python code/main.py
```

This will:
1. Initialize the Upstox agent
2. Open a GUI window with live charts
3. Connect to live data feed
4. Display real-time candlestick charts

### Switching Brokers

The application supports runtime broker switching:

```python
from main import MarketDataApp

# Start with Upstox
app = MarketDataApp(broker_type="upstox")

# Switch to Kite
app.switch_broker("kite")

# Switch back to Upstox
app.switch_broker("upstox")
```

### Programmatic Usage

```python
from main import MarketDataApp

# Create application
app = MarketDataApp(broker_type="upstox")

# Start live data streaming
app.start_live_data()

# Get current status
status = app.get_status()
print(f"Connected: {status['agent_connected']}")
print(f"Chart running: {status['chart_running']}")

# Stop live data
app.stop_live_data()
```

### Chart-Only Usage

Use the chart visualizer independently:

```python
from chart_visualizer import LiveChartVisualizer, TkinterChartApp

# Create chart
chart = LiveChartVisualizer(title="My Chart")

# Add instruments
chart.add_instrument("NSE_INDEX|Nifty 50", "Nifty 50")

# Update with data
chart.update_data("NSE_INDEX|Nifty 50", tick_data)

# Run GUI
app = TkinterChartApp(chart)
app.run()
```

## Configuration

### Supported Instruments

**Upstox**:
- `NSE_INDEX|Nifty 50`
- `NSE_INDEX|Nifty Bank`

**Kite**:
- `256265` (NSE:NIFTY 50)
- `260105` (NSE:NIFTY BANK)

### Adding New Instruments

To add new instruments, modify the `instruments` dictionary in `MarketDataApp.__init__()`:

```python
self.instruments = {
    "upstox": {
        "NSE_INDEX|Nifty 50": "Nifty 50",
        "NSE_INDEX|Nifty Bank": "Nifty Bank",
        "NSE_INDEX|Nifty IT": "Nifty IT"  # Add new instrument
    },
    "kite": {
        256265: "Nifty 50",
        260105: "Nifty Bank",
        256265: "Nifty IT"  # Add new instrument
    }
}
```

## API Reference

### MarketDataApp

Main application class for orchestrating market data visualization.

#### Methods

- `__init__(broker_type: str)`: Initialize with specified broker type
- `switch_broker(new_broker_type: str)`: Switch to different broker
- `start_live_data()`: Start live data streaming and chart updates
- `stop_live_data()`: Stop live data streaming
- `run_chart_app()`: Run the GUI chart application
- `get_status() -> Dict[str, Any]`: Get current application status

### BrokerAgent

Abstract base class for all broker implementations.

#### Abstract Methods

- `connect_live_data()`: Establish live data connection
- `subscribe_live_data(instrument_keys, mode)`: Subscribe to instruments
- `unsubscribe_live_data(instrument_keys)`: Unsubscribe from instruments
- `disconnect_live_data()`: Disconnect from live data feed

### LiveChartVisualizer

Real-time chart visualization component.

#### Methods

- `add_instrument(instrument_key, instrument_name)`: Add instrument to track
- `update_data(instrument_key, tick_data)`: Update chart with new data
- `start_chart()`: Start chart animation
- `stop_chart()`: Stop chart animation
- `get_current_prices()`: Get current prices for all instruments

## Examples

See `code/example_usage.py` for comprehensive usage examples including:
- Basic Upstox usage
- Basic Kite usage
- Broker switching
- Chart-only usage

## Troubleshooting

### Common Issues

1. **Connection Errors**: Ensure API keys are correctly configured in `keys.env`
2. **Import Errors**: Make sure all dependencies are installed via `pip install -r requirements.txt`
3. **Chart Not Updating**: Check if live data connection is established and instruments are subscribed
4. **GUI Not Showing**: Ensure tkinter is available (usually comes with Python)

### Logging

The application uses Python's logging module. To enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the examples in `code/example_usage.py`
3. Create an issue in the repository
