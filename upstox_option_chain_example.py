#!/usr/bin/env python3
"""
Example usage of UpstoxOptionChain class.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from upstox_option_chain_mock import UpstoxOptionChainMock
from utils import Utils
import json

def main():
    """Main example function"""
    print("UpstoxOptionChain Usage Example")
    print("=" * 50)
    
    # Initialize the option chain fetcher
    # Note: In real usage, you would use UpstoxOptionChain with a valid access token
    # For this example, we'll use the mock version
    option_chain = UpstoxOptionChainMock("your_access_token_here")
    print("✅ Option chain fetcher initialized")
    
    # Example 1: Get next weekly expiry using Utils
    print("\n1. Next Weekly Expiry")
    print("-" * 30)
    next_expiry = option_chain.get_next_weekly_expiry()
    print(f"Next weekly expiry: {next_expiry}")
    
    # Also show current week expiry for comparison
    all_expiries = Utils.get_next_weekly_expiry()
    current_expiry = all_expiries[0] if all_expiries else "N/A"
    print(f"Current week expiry (from Utils): {current_expiry}")
    print(f"All available expiries: {all_expiries}")
    
    # Example 2: Get all available strike prices
    print("\n2. Available Strike Prices")
    print("-" * 30)
    strikes = option_chain.get_available_strike_prices()
    print(f"Available strikes: {strikes[:10]}...")  # Show first 10
    
    # Example 3: Fetch all option data
    print("\n3. Fetch All Option Data")
    print("-" * 30)
    all_options = option_chain.fetch()
    print(f"Total option contracts: {len(all_options)}")
    
    # Show sample data
    if all_options:
        sample = all_options[0]
        print("\nSample option contract:")
        for key, value in sample.items():
            if key != 'raw_data':  # Skip raw data for display
                print(f"  {key}: {value}")
    
    # Example 4: Fetch by expiry
    print("\n4. Fetch by Expiry")
    print("-" * 30)
    if next_expiry:
        expiry_options = option_chain.fetch(expiry=next_expiry)
        print(f"Options for expiry {next_expiry}: {len(expiry_options)}")
        
        # Show breakdown by option type
        calls = [opt for opt in expiry_options if opt['option_type'] == 'CALL']
        puts = [opt for opt in expiry_options if opt['option_type'] == 'PUT']
        print(f"  Calls: {len(calls)}, Puts: {len(puts)}")
    
    # Example 5: Fetch by strike price
    print("\n5. Fetch by Strike Price")
    print("-" * 30)
    if strikes:
        target_strike = strikes[0]
        strike_options = option_chain.fetch(strike_price=target_strike)
        print(f"Options for strike {target_strike}: {len(strike_options)}")
        
        # Show all expiries for this strike
        strike_expiries = list(set(opt['expiry_date'] for opt in strike_options))
        print(f"  Available expiries: {strike_expiries}")
    
    # Example 6: Fetch by both expiry and strike
    print("\n6. Fetch by Expiry and Strike")
    print("-" * 30)
    if next_expiry and strikes:
        target_strike = strikes[0]
        specific_options = option_chain.fetch(expiry=next_expiry, strike_price=target_strike)
        print(f"Options for {next_expiry} strike {target_strike}: {len(specific_options)}")
        
        # Show the specific options
        for option in specific_options:
            print(f"  {option['option_type']} - Last: {option['last_price']}, "
                  f"Bid: {option['bid_price']}, Ask: {option['ask_price']}")
    
    # Example 7: Get option chain summary
    print("\n7. Option Chain Summary")
    print("-" * 30)
    summary = option_chain.get_option_summary()
    print(f"Total contracts: {summary['total_contracts']}")
    print(f"Call contracts: {summary['call_contracts']}")
    print(f"Put contracts: {summary['put_contracts']}")
    print(f"Available expiries: {len(summary['expiries'])}")
    print(f"Strike range: {summary['strike_range']['min']} - {summary['strike_range']['max']}")
    print(f"Total volume: {summary['total_volume']:,}")
    print(f"Total open interest: {summary['total_open_interest']:,}")
    
    # Example 8: Get summary for specific expiry
    print("\n8. Summary for Specific Expiry")
    print("-" * 30)
    if next_expiry:
        expiry_summary = option_chain.get_option_summary(expiry=next_expiry)
        print(f"Summary for {next_expiry}:")
        print(f"  Contracts: {expiry_summary['total_contracts']}")
        print(f"  Calls: {expiry_summary['call_contracts']}")
        print(f"  Puts: {expiry_summary['put_contracts']}")
        print(f"  Strike range: {expiry_summary['strike_range']['min']} - {expiry_summary['strike_range']['max']}")
    
    # Example 9: Find ATM (At-The-Money) options
    print("\n9. Find ATM Options")
    print("-" * 30)
    current_price = 25000  # Simulated current NIFTY price
    atm_strikes = Utils.get_nearest_strikes(current_price, 3)  # Get 3 nearest strikes
    print(f"Current price: {current_price}")
    print(f"Nearest strikes: {atm_strikes}")
    
    if next_expiry:
        for strike in atm_strikes:
            atm_options = option_chain.fetch(expiry=next_expiry, strike_price=strike)
            if atm_options:
                call_option = next((opt for opt in atm_options if opt['option_type'] == 'CALL'), None)
                put_option = next((opt for opt in atm_options if opt['option_type'] == 'PUT'), None)
                
                if call_option and put_option:
                    print(f"  Strike {strike}:")
                    print(f"    Call: {call_option['last_price']} (IV: {call_option['implied_volatility']})")
                    print(f"    Put:  {put_option['last_price']} (IV: {put_option['implied_volatility']})")
    
    # Example 10: Cache functionality
    print("\n10. Cache Functionality")
    print("-" * 30)
    print("Testing cache performance...")
    
    # First fetch (populates cache)
    import time
    start_time = time.time()
    data1 = option_chain.fetch()
    first_fetch_time = time.time() - start_time
    
    # Second fetch (uses cache)
    start_time = time.time()
    data2 = option_chain.fetch()
    second_fetch_time = time.time() - start_time
    
    print(f"First fetch: {len(data1)} contracts in {first_fetch_time:.4f} seconds")
    print(f"Second fetch (cached): {len(data2)} contracts in {second_fetch_time:.4f} seconds")
    print(f"Cache speedup: {first_fetch_time / second_fetch_time:.1f}x faster")
    
    # Clear cache
    option_chain.clear_cache()
    print("✅ Cache cleared")
    
    # Example 11: Integration with trading strategies
    print("\n11. Integration with Trading Strategies")
    print("-" * 30)
    print("Example: Iron Condor setup")
    
    if next_expiry and len(strikes) >= 4:
        atm_strike = 25000
        
        # Find strikes for Iron Condor
        iron_condor_strikes = [atm_strike - 100, atm_strike, atm_strike + 100, atm_strike + 200]
        
        print(f"Setting up Iron Condor for {next_expiry}:")
        print(f"Strikes: {iron_condor_strikes}")
        
        for strike in iron_condor_strikes:
            options = option_chain.fetch(expiry=next_expiry, strike_price=strike)
            if options:
                call_option = next((opt for opt in options if opt['option_type'] == 'CALL'), None)
                put_option = next((opt for opt in options if opt['option_type'] == 'PUT'), None)
                
                if call_option and put_option:
                    print(f"  Strike {strike}:")
                    print(f"    Call: {call_option['last_price']} (OI: {call_option['open_interest']:,})")
                    print(f"    Put:  {put_option['last_price']} (OI: {put_option['open_interest']:,})")
    
    print("\n✅ All examples completed successfully!")
    print("\nNote: This example uses mock data. In production, use UpstoxOptionChain with a valid access token.")

if __name__ == "__main__":
    main()
