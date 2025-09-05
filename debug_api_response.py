#!/usr/bin/env python3
"""
Debug script to help identify the actual API response format.
Use this script to debug the real Upstox API response.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

# Set up detailed logging
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def debug_api_response():
    """Debug the actual API response format"""
    print("=== Debugging Real Upstox API Response ===")
    print("This script will help you debug the actual API response format.")
    print("Make sure you have a valid access token in keys.env")
    
    try:
        # Try to import the real UpstoxOptionChain
        from upstox_option_chain import UpstoxOptionChain
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv("keys.env")
        access_token = os.getenv("UPSTOX_ACCESS_TOKEN")
        
        if not access_token:
            print("❌ No UPSTOX_ACCESS_TOKEN found in keys.env")
            print("Please add your access token to keys.env file")
            return
        
        print(f"✅ Access token found: {access_token[:10]}...")
        
        # Initialize the option chain
        print("\nInitializing UpstoxOptionChain...")
        option_chain = UpstoxOptionChain(access_token)
        
        # Get next expiry
        print("\nGetting next expiry...")
        next_expiry = option_chain.get_next_weekly_expiry()
        print(f"Next expiry: {next_expiry}")
        
        # Try to fetch data
        print(f"\nFetching option chain data for expiry: {next_expiry}")
        try:
            data = option_chain.fetch(expiry=next_expiry)
            print(f"✅ Successfully fetched {len(data)} option contracts")
            
            if data:
                print("\nSample option contract:")
                sample = data[0]
                for key, value in sample.items():
                    if key != 'raw_data':
                        print(f"  {key}: {value}")
            else:
                print("❌ No option contracts found!")
                print("This suggests the API response format might be different from expected.")
                print("Check the logs above for debugging information.")
        
        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            print("Check the logs above for debugging information.")
        
        # Clean up
        option_chain.close()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure upstox_client is installed: pip install upstox-python-sdk")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_api_response()
