#!/usr/bin/env python3
"""
Debug script to understand Upstox data format and fix parsing
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
import re
import unittest.mock as mock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UpstoxDataDebug")

def test_price_extraction_patterns():
    """Test different price extraction patterns"""
    logger.info("🔍 Testing Price Extraction Patterns")
    logger.info("=" * 50)
    
    # Sample Upstox data strings (these are examples of what we might receive)
    test_data_samples = [
        # Example 1: LTP data
        "LtpData(instrument_token='256265', last_price=24050.5, volume=1000)",
        
        # Example 2: OHLC data
        "OhlcData(instrument_token='256265', open=24000.0, high=24060.0, low=23980.0, close=24050.5, volume=1500)",
        
        # Example 3: Quote data
        "QuoteData(instrument_token='256265', last_price=24050.5, volume=1000, bid=24049.0, ask=24051.0)",
        
        # Example 4: Generic protobuf string
        "instrument_token: '256265' last_price: 24050.5 volume: 1000",
        
        # Example 5: JSON-like string
        '{"instrument_token": "256265", "last_price": 24050.5, "volume": 1000}',
        
        # Example 6: Simple string
        "NSE_INDEX|Nifty 50: 24050.5",
        
        # Example 7: Complex protobuf
        "MarketDataFeed(instrument_token='256265', ltp=24050.5, volume=1000, timestamp=1640995200)",
    ]
    
    # Current patterns from main.py
    current_patterns = [
        r'ltp[:\s]*(\d+\.?\d*)',
        r'last_price[:\s]*(\d+\.?\d*)',
        r'price[:\s]*(\d+\.?\d*)',
        r'close[:\s]*(\d+\.?\d*)',
        r'(\d{4,6}\.?\d*)'  # Generic 4-6 digit number
    ]
    
    # Improved patterns
    improved_patterns = [
        r'ltp[:\s]*(\d+\.?\d*)',
        r'last_price[:\s]*(\d+\.?\d*)',
        r'price[:\s]*(\d+\.?\d*)',
        r'close[:\s]*(\d+\.?\d*)',
        r'open[:\s]*(\d+\.?\d*)',
        r'high[:\s]*(\d+\.?\d*)',
        r'low[:\s]*(\d+\.?\d*)',
        r'(\d{4,6}\.?\d*)',  # Generic 4-6 digit number
        r'"last_price":\s*(\d+\.?\d*)',  # JSON format
        r'last_price:\s*(\d+\.?\d*)',    # Protobuf format
        r'ltp:\s*(\d+\.?\d*)',           # LTP format
    ]
    
    logger.info("📊 Testing Current Patterns:")
    for i, data_sample in enumerate(test_data_samples, 1):
        logger.info(f"\n--- Sample {i}: {data_sample} ---")
        
        for pattern in current_patterns:
            match = re.search(pattern, data_sample, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    logger.info(f"✅ Pattern '{pattern}' → Price: {price}")
                    break
                except ValueError:
                    logger.info(f"❌ Pattern '{pattern}' → Invalid number: {match.group(1)}")
            else:
                logger.info(f"❌ Pattern '{pattern}' → No match")
    
    logger.info("\n📊 Testing Improved Patterns:")
    for i, data_sample in enumerate(test_data_samples, 1):
        logger.info(f"\n--- Sample {i}: {data_sample} ---")
        
        for pattern in improved_patterns:
            match = re.search(pattern, data_sample, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    logger.info(f"✅ Pattern '{pattern}' → Price: {price}")
                    break
                except ValueError:
                    logger.info(f"❌ Pattern '{pattern}' → Invalid number: {match.group(1)}")
            else:
                logger.info(f"❌ Pattern '{pattern}' → No match")

def test_volume_extraction():
    """Test volume extraction patterns"""
    logger.info("\n🔍 Testing Volume Extraction Patterns")
    logger.info("=" * 50)
    
    test_data_samples = [
        "LtpData(instrument_token='256265', last_price=24050.5, volume=1000)",
        "volume: 1500",
        '"volume": 2000',
        "vol: 500",
        "volume=3000",
    ]
    
    volume_patterns = [
        r'volume[:\s=]*(\d+)',
        r'vol[:\s=]*(\d+)',
        r'"volume":\s*(\d+)',
    ]
    
    for i, data_sample in enumerate(test_data_samples, 1):
        logger.info(f"\n--- Sample {i}: {data_sample} ---")
        
        for pattern in volume_patterns:
            match = re.search(pattern, data_sample, re.IGNORECASE)
            if match:
                try:
                    volume = int(match.group(1))
                    logger.info(f"✅ Pattern '{pattern}' → Volume: {volume}")
                    break
                except ValueError:
                    logger.info(f"❌ Pattern '{pattern}' → Invalid number: {match.group(1)}")
            else:
                logger.info(f"❌ Pattern '{pattern}' → No match")

def create_improved_parsing_function():
    """Create an improved data parsing function"""
    logger.info("\n🔧 Creating Improved Parsing Function")
    logger.info("=" * 50)
    
    def parse_upstox_data(data):
        """Improved Upstox data parsing function"""
        try:
            data_str = str(data)
            logger.info(f"Parsing data: {data_str[:200]}...")
            
            # Improved price patterns
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
                r'(\d{4,6}\.?\d*)',  # Generic 4-6 digit number (for Nifty prices)
            ]
            
            price = None
            for pattern in price_patterns:
                match = re.search(pattern, data_str, re.IGNORECASE)
                if match:
                    try:
                        price = float(match.group(1))
                        logger.debug(f"✅ Extracted price: {price} using pattern: {pattern}")
                        break
                    except ValueError:
                        continue
            
            # Improved volume patterns
            volume_patterns = [
                r'volume[:\s=]*(\d+)',
                r'vol[:\s=]*(\d+)',
                r'"volume":\s*(\d+)',
            ]
            
            volume = 0
            for pattern in volume_patterns:
                match = re.search(pattern, data_str, re.IGNORECASE)
                if match:
                    try:
                        volume = int(match.group(1))
                        logger.info(f"✅ Extracted volume: {volume} using pattern: {pattern}")
                        break
                    except ValueError:
                        continue
            
            return price, volume
            
        except Exception as e:
            logger.error(f"Error parsing data: {e}")
            return None, 0
    
    # Test the improved function
    test_samples = [
        "LtpData(instrument_token='256265', last_price=24050.5, volume=1000)",
        "OhlcData(instrument_token='256265', open=24000.0, high=24060.0, low=23980.0, close=24050.5, volume=1500)",
        '{"instrument_token": "256265", "last_price": 24050.5, "volume": 1000}',
        "NSE_INDEX|Nifty 50: 24050.5",
    ]
    
    for i, sample in enumerate(test_samples, 1):
        logger.info(f"\n--- Testing Sample {i} ---")
        price, volume = parse_upstox_data(sample)
        logger.info(f"Result: price={price}, volume={volume}")
    
    return parse_upstox_data

def main():
    """Run all debugging tests"""
    logger.info("🚀 Starting Upstox Data Parsing Debug")
    logger.info("=" * 60)
    
    # Test 1: Price extraction patterns
    test_price_extraction_patterns()
    
    # Test 2: Volume extraction patterns
    test_volume_extraction()
    
    # Test 3: Improved parsing function
    improved_parser = create_improved_parsing_function()
    
    logger.info("\n🎉 Debugging Complete!")
    logger.info("\n💡 Recommendations:")
    logger.info("   1. Update price patterns to include more formats")
    logger.info("   2. Add better error handling for invalid numbers")
    logger.info("   3. Test with actual Upstox data format")
    logger.info("   4. Consider using protobuf parsing if available")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
