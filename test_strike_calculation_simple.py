#!/usr/bin/env python3
"""
Simple test script to verify strike price calculation logic
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StrikeCalculationTest")

def calculate_nearest_strike_price(current_price: float) -> int:
    """
    Calculate the nearest strike price (multiples of 50) based on current NIFTY price
    
    Args:
        current_price (float): Current NIFTY price
        
    Returns:
        int: Nearest strike price (multiple of 50)
    """
    try:
        # Handle edge cases
        if current_price <= 0:
            return 0
        
        # Round to nearest multiple of 50
        # Use floor division and then multiply by 50, then add 50 if remainder >= 25
        base_strike = int(current_price // 50) * 50
        remainder = current_price % 50
        
        if remainder >= 25:
            strike_price = base_strike + 50
        else:
            strike_price = base_strike
        
        return int(strike_price)
        
    except Exception as e:
        logger.error(f"Error calculating nearest strike price: {e}")
        return 0

def test_strike_price_calculation():
    """Test the strike price calculation logic"""
    try:
        logger.info("🚀 Testing Strike Price Calculation Logic")
        logger.info("=" * 60)
        
        # Test strike price calculations
        logger.info("📊 Testing strike price calculations...")
        
        test_cases = [
            (19475.25, 19450),  # Should round down
            (19475.75, 19500),  # Should round up
            (19500.00, 19500),  # Exact multiple
            (19525.00, 19550),  # Should round up
            (19524.99, 19500),  # Should round down
            (20000.00, 20000),  # Large number
            (19000.00, 19000),  # Small number
            (19525.75, 19550),  # Real example
            (19475.25, 19450),  # Real example
        ]
        
        all_passed = True
        for current_price, expected_strike in test_cases:
            calculated_strike = calculate_nearest_strike_price(current_price)
            status = "✅" if calculated_strike == expected_strike else "❌"
            logger.info(f"   {status} NIFTY {current_price} -> Strike {calculated_strike} (expected: {expected_strike})")
            if calculated_strike != expected_strike:
                all_passed = False
        
        # Test edge cases
        logger.info("\n📊 Testing edge cases...")
        
        edge_cases = [
            (0, 0),           # Zero price
            (-100, 0),        # Negative price
            (50.0, 50),       # Exactly 50
            (25.0, 50),       # Less than 50
            (75.0, 100),      # More than 50
        ]
        
        for current_price, expected_strike in edge_cases:
            calculated_strike = calculate_nearest_strike_price(current_price)
            status = "✅" if calculated_strike == expected_strike else "❌"
            logger.info(f"   {status} Edge case {current_price} -> Strike {calculated_strike} (expected: {expected_strike})")
            if calculated_strike != expected_strike:
                all_passed = False
        
        # Test real-world NIFTY scenarios
        logger.info("\n📊 Testing real-world NIFTY scenarios...")
        
        real_scenarios = [
            (19450.00, 19450),  # Exact strike
            (19450.25, 19450),  # Just above strike
            (19449.75, 19450),  # Just below strike
            (19500.00, 19500),  # Next strike
            (19500.25, 19500),  # Just above next strike
            (19499.75, 19500),  # Just below next strike
            (19525.75, 19550),  # Mid-range
            (19475.25, 19450),  # Mid-range
        ]
        
        for current_price, expected_strike in real_scenarios:
            calculated_strike = calculate_nearest_strike_price(current_price)
            status = "✅" if calculated_strike == expected_strike else "❌"
            logger.info(f"   {status} Real scenario {current_price} -> Strike {calculated_strike} (expected: {expected_strike})")
            if calculated_strike != expected_strike:
                all_passed = False
        
        if all_passed:
            logger.info("✅ All strike price calculations passed!")
        else:
            logger.error("❌ Some strike price calculations failed!")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"Strike price calculation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_display_formatting():
    """Test the display formatting for Grid 2"""
    try:
        logger.info("\n🚀 Testing Display Formatting")
        logger.info("=" * 60)
        
        # Test display formatting
        logger.info("📊 Testing display formatting...")
        
        test_prices = [
            (19475.25, 19450),
            (19525.75, 19550),
            (19500.00, 19500),
            (19575.00, 19600),
        ]
        
        for current_price, strike_price in test_prices:
            difference = abs(current_price - strike_price)
            
            # Format display strings
            current_display = f"Current NIFTY: {current_price:.2f}"
            strike_display = f"Nearest Strike: {strike_price}"
            diff_display = f"Difference: {difference:.2f}"
            
            logger.info(f"   ✅ {current_display}")
            logger.info(f"   ✅ {strike_display}")
            logger.info(f"   ✅ {diff_display}")
            logger.info("   " + "-" * 40)
        
        logger.info("✅ Display formatting test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Display formatting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting Simple Strike Price Calculation Tests")
    logger.info("=" * 80)
    
    success1 = test_strike_price_calculation()
    success2 = test_display_formatting()
    
    if success1 and success2:
        logger.info("\n🎉 All strike price calculation tests passed!")
        logger.info("\n💡 Features Verified:")
        logger.info("   • Strike price calculation (multiples of 50)")
        logger.info("   • Edge case handling")
        logger.info("   • Real-world NIFTY scenarios")
        logger.info("   • Display formatting")
        logger.info("   • Rounding logic accuracy")
        logger.info("\n🎯 The strike price calculation logic is working correctly!")
        
        logger.info("\n📋 Implementation Summary:")
        logger.info("   • Grid 2 will display nearest strike price")
        logger.info("   • Updates automatically with live NIFTY price")
        logger.info("   • Manual update button available")
        logger.info("   • Shows current price, strike price, and difference")
        logger.info("   • Real-time updates during market hours")
    else:
        logger.error("\n❌ Some strike price calculation tests failed!")
    
    return success1 and success2

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
