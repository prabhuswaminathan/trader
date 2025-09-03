#!/usr/bin/env python3
"""
Debug script to diagnose live data connection issues
"""

import sys
import os
import logging
import time

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LiveDataDebug")

def check_environment():
    """Check if required environment variables are set"""
    logger.info("=== Environment Check ===")
    
    # Check if keys.env exists
    keys_file = "keys.env"
    if os.path.exists(keys_file):
        logger.info(f"✓ {keys_file} exists")
        
        # Read and check contents
        with open(keys_file, 'r') as f:
            content = f.read()
            if 'UPSTOX_API_KEY' in content:
                logger.info("✓ UPSTOX_API_KEY found in keys.env")
            else:
                logger.warning("✗ UPSTOX_API_KEY not found in keys.env")
                
            if 'UPSTOX_API_SECRET' in content:
                logger.info("✓ UPSTOX_API_SECRET found in keys.env")
            else:
                logger.warning("✗ UPSTOX_API_SECRET not found in keys.env")
                
            if 'UPSTOX_ACCESS_TOKEN' in content:
                logger.info("✓ UPSTOX_ACCESS_TOKEN found in keys.env")
            else:
                logger.warning("✗ UPSTOX_ACCESS_TOKEN not found in keys.env")
    else:
        logger.error(f"✗ {keys_file} not found")
        return False
    
    return True

def test_upstox_connection():
    """Test Upstox agent connection"""
    logger.info("=== Upstox Connection Test ===")
    
    try:
        # Mock external dependencies to avoid import errors
        import sys
        from unittest.mock import MagicMock
        
        # Mock upstox_client
        sys.modules['upstox_client'] = MagicMock()
        sys.modules['upstox_client.rest'] = MagicMock()
        
        from upstox_agent import UpstoxAgent
        
        # Create agent
        agent = UpstoxAgent()
        logger.info("✓ UpstoxAgent created successfully")
        
        # Check configuration
        if hasattr(agent, 'configuration') and agent.configuration:
            logger.info("✓ Configuration object exists")
        else:
            logger.warning("✗ Configuration object missing")
        
        # Check access token
        if hasattr(agent, 'ACCESS_TOKEN') and agent.ACCESS_TOKEN:
            logger.info("✓ Access token found")
        else:
            logger.warning("✗ Access token missing")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Upstox connection test failed: {e}")
        return False

def test_kite_connection():
    """Test Kite agent connection"""
    logger.info("=== Kite Connection Test ===")
    
    try:
        # Mock external dependencies
        import sys
        from unittest.mock import MagicMock
        
        sys.modules['kiteconnect'] = MagicMock()
        
        from kite_agent import KiteAgent
        
        # Create agent
        agent = KiteAgent()
        logger.info("✓ KiteAgent created successfully")
        
        # Check kite object
        if hasattr(agent, 'kite') and agent.kite:
            logger.info("✓ Kite object exists")
        else:
            logger.warning("✗ Kite object missing")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Kite connection test failed: {e}")
        return False

def test_chart_visualizer():
    """Test chart visualizer"""
    logger.info("=== Chart Visualizer Test ===")
    
    try:
        # Mock external dependencies
        import sys
        from unittest.mock import MagicMock
        
        mock_modules = [
            'matplotlib', 'matplotlib.pyplot', 'matplotlib.animation',
            'matplotlib.backends.backend_tkagg', 'tkinter', 'pandas', 'numpy'
        ]
        
        for module in mock_modules:
            sys.modules[module] = MagicMock()
        
        from chart_visualizer import LiveChartVisualizer
        
        # Create chart
        chart = LiveChartVisualizer(title="Test Chart")
        logger.info("✓ LiveChartVisualizer created successfully")
        
        # Add instrument
        chart.add_instrument("TEST_INSTRUMENT", "Test Instrument")
        logger.info("✓ Instrument added successfully")
        
        # Test data update
        test_data = {
            'instrument_token': 'TEST_INSTRUMENT',
            'last_price': 100.0,
            'volume': 1000
        }
        
        chart.update_data("TEST_INSTRUMENT", [test_data])
        logger.info("✓ Data update successful")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Chart visualizer test failed: {e}")
        return False

def create_sample_keys_file():
    """Create a sample keys.env file"""
    logger.info("=== Creating Sample keys.env ===")
    
    sample_content = """# Upstox API Credentials
UPSTOX_API_KEY=your_upstox_api_key_here
UPSTOX_API_SECRET=your_upstox_api_secret_here
UPSTOX_ACCESS_TOKEN=your_upstox_access_token_here

# Kite API Credentials (if needed)
KITE_API_KEY=your_kite_api_key_here
KITE_ACCESS_TOKEN=your_kite_access_token_here
"""
    
    try:
        with open("keys.env", "w") as f:
            f.write(sample_content)
        logger.info("✓ Sample keys.env created")
        logger.info("Please update the file with your actual API credentials")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create keys.env: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    logger.info("Starting Live Data Diagnostic")
    logger.info("=" * 50)
    
    tests = [
        ("Environment Check", check_environment),
        ("Upstox Connection", test_upstox_connection),
        ("Kite Connection", test_kite_connection),
        ("Chart Visualizer", test_chart_visualizer)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        logger.info("")
    
    logger.info("=" * 50)
    logger.info(f"Tests passed: {passed}/{total}")
    
    if passed < total:
        logger.info("\nIssues found:")
        logger.info("1. Check if keys.env file exists and has correct API credentials")
        logger.info("2. Verify API keys are valid and have live data permissions")
        logger.info("3. Check network connectivity to broker APIs")
        logger.info("4. Ensure all required packages are installed")
        
        # Create sample keys file if it doesn't exist
        if not os.path.exists("keys.env"):
            logger.info("\nCreating sample keys.env file...")
            create_sample_keys_file()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
