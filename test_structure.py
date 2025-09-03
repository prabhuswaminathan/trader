#!/usr/bin/env python3
"""
Simple test script to verify the basic structure without external dependencies
"""

import sys
import os

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

def test_broker_agent():
    """Test BrokerAgent base class"""
    try:
        from broker_agent import BrokerAgent
        print("✓ BrokerAgent import successful")
        
        # Test that it's abstract
        try:
            agent = BrokerAgent()
            print("✗ BrokerAgent should be abstract")
            return False
        except TypeError:
            print("✓ BrokerAgent is properly abstract")
            return True
            
    except ImportError as e:
        print(f"✗ BrokerAgent import failed: {e}")
        return False

def test_chart_visualizer():
    """Test chart visualizer (without matplotlib)"""
    try:
        # Mock matplotlib to avoid import issues
        import sys
        from unittest.mock import MagicMock
        
        sys.modules['matplotlib'] = MagicMock()
        sys.modules['matplotlib.pyplot'] = MagicMock()
        sys.modules['matplotlib.animation'] = MagicMock()
        sys.modules['matplotlib.backends.backend_tkagg'] = MagicMock()
        sys.modules['tkinter'] = MagicMock()
        sys.modules['pandas'] = MagicMock()
        sys.modules['numpy'] = MagicMock()
        
        from chart_visualizer import LiveChartVisualizer
        print("✓ LiveChartVisualizer import successful")
        return True
        
    except ImportError as e:
        print(f"✗ LiveChartVisualizer import failed: {e}")
        return False

def test_main_structure():
    """Test main.py structure (without external dependencies)"""
    try:
        # Mock external dependencies
        import sys
        from unittest.mock import MagicMock
        
        sys.modules['upstox_client'] = MagicMock()
        sys.modules['kiteconnect'] = MagicMock()
        sys.modules['matplotlib'] = MagicMock()
        sys.modules['matplotlib.pyplot'] = MagicMock()
        sys.modules['matplotlib.animation'] = MagicMock()
        sys.modules['matplotlib.backends.backend_tkagg'] = MagicMock()
        sys.modules['tkinter'] = MagicMock()
        sys.modules['pandas'] = MagicMock()
        sys.modules['numpy'] = MagicMock()
        
        from main import MarketDataApp
        print("✓ MarketDataApp import successful")
        
        # Test that we can create the class (it will fail on agent creation, but that's expected)
        try:
            app = MarketDataApp(broker_type="upstox")
            print("✗ MarketDataApp creation should fail without proper setup")
            return False
        except Exception as e:
            print(f"✓ MarketDataApp properly handles missing dependencies: {type(e).__name__}")
            return True
            
    except ImportError as e:
        print(f"✗ MarketDataApp import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing Market Data Application Structure")
    print("=" * 50)
    
    tests = [
        test_broker_agent,
        test_chart_visualizer,
        test_main_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All structure tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
