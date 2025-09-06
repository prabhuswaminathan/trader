#!/usr/bin/env python3
"""
Demo script to show Iron Condor strategy creation with mock data.
"""

import sys
import os
import logging
from datetime import datetime, date, timedelta
import numpy as np
import matplotlib.pyplot as plt

# Add the code directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from strategy_manager import StrategyManager
from trade_models import Trade, TradeLeg, TradeStatus, OptionType, PositionType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DemoIronCondor")

def create_mock_iron_condor(spot_price: float = 25000):
    """Create a mock Iron Condor strategy for demonstration"""
    
    print("=" * 60)
    print("IRON CONDOR STRATEGY DEMONSTRATION")
    print("=" * 60)
    
    # Calculate strikes based on requirements
    current_strike = int(round(spot_price / 50) * 50)  # Round to nearest 50
    
    # Short positions: 400 points away from current strike
    short_call_strike = current_strike + 400
    short_put_strike = current_strike - 400
    
    # Long positions: 200 points away from short positions
    long_call_strike = short_call_strike + 200
    long_put_strike = short_put_strike - 200
    
    print(f"Current NIFTY Spot Price: ₹{spot_price:,.2f}")
    print(f"Current Strike: {current_strike}")
    print(f"\nIron Condor Strikes:")
    print(f"  Long Put:  {long_put_strike} (Protection)")
    print(f"  Short Put: {short_put_strike} (Income)")
    print(f"  Short Call: {short_call_strike} (Income)")
    print(f"  Long Call:  {long_call_strike} (Protection)")
    
    # Create mock option data
    lot_size = 50
    next_expiry = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Mock option prices (these would come from the API in real usage)
    mock_prices = {
        long_put_strike: {"call": 0, "put": 15.50},
        short_put_strike: {"call": 0, "put": 45.75},
        short_call_strike: {"call": 42.25, "put": 0},
        long_call_strike: {"call": 8.50, "put": 0}
    }
    
    # Create trade legs
    trade_legs = []
    legs_config = [
        {
            "strike": long_put_strike,
            "option_type": OptionType.PUT,
            "position_type": PositionType.LONG,
            "description": "Long Put (Protection)",
            "price": mock_prices[long_put_strike]["put"]
        },
        {
            "strike": short_put_strike,
            "option_type": OptionType.PUT,
            "position_type": PositionType.SHORT,
            "description": "Short Put (Income)",
            "price": mock_prices[short_put_strike]["put"]
        },
        {
            "strike": short_call_strike,
            "option_type": OptionType.CALL,
            "position_type": PositionType.SHORT,
            "description": "Short Call (Income)",
            "price": mock_prices[short_call_strike]["call"]
        },
        {
            "strike": long_call_strike,
            "option_type": OptionType.CALL,
            "position_type": PositionType.LONG,
            "description": "Long Call (Protection)",
            "price": mock_prices[long_call_strike]["call"]
        }
    ]
    
    print(f"\nOption Prices (Mock Data):")
    for leg_config in legs_config:
        trade_leg = TradeLeg(
            instrument=f"NSE_OPT|NIFTY|{next_expiry}|{leg_config['strike']}|{leg_config['option_type'].value[0]}E",
            instrument_name=f"NIFTY {leg_config['strike']} {leg_config['option_type'].value}",
            option_type=leg_config["option_type"],
            strike_price=leg_config["strike"],
            position_type=leg_config["position_type"],
            quantity=lot_size,
            entry_timestamp=datetime.now(),
            entry_price=leg_config["price"]
        )
        trade_legs.append(trade_leg)
        print(f"  {leg_config['description']}: ₹{leg_config['price']:.2f}")
    
    # Create the trade
    trade_id = f"IC_DEMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    trade = Trade(
        trade_id=trade_id,
        strategy_name="Iron Condor",
        underlying_instrument="NIFTY",
        status=TradeStatus.OPEN,
        legs=trade_legs,
        notes=f"Iron Condor: {long_put_strike}P/{short_put_strike}P/{short_call_strike}C/{long_call_strike}C",
        tags=["Iron Condor", "Options Strategy", "Demo"]
    )
    
    print(f"\nTrade Created: {trade_id}")
    
    # Calculate and display payoff analysis
    print(f"\n" + "=" * 40)
    print("PAYOFF ANALYSIS")
    print("=" * 40)
    
    # Calculate net premium received
    net_premium = 0
    for leg in trade_legs:
        if leg.position_type == PositionType.SHORT:
            net_premium += leg.entry_price * leg.quantity
        else:
            net_premium -= leg.entry_price * leg.quantity
    
    print(f"Net Premium Received: ₹{net_premium:,.2f}")
    
    # Calculate max profit and loss
    max_profit = net_premium
    max_loss = (long_call_strike - short_call_strike) * lot_size - net_premium
    
    print(f"Max Profit: ₹{max_profit:,.2f}")
    print(f"Max Loss: ₹{max_loss:,.2f}")
    
    # Calculate breakeven points
    put_breakeven = short_put_strike - (net_premium / lot_size)
    call_breakeven = short_call_strike + (net_premium / lot_size)
    
    print(f"Put Breakeven: {put_breakeven:.2f}")
    print(f"Call Breakeven: {call_breakeven:.2f}")
    
    # Create payoff diagram
    create_payoff_diagram(trade, spot_price, trade_id)
    
    return trade

def create_payoff_diagram(trade: Trade, spot_price: float, trade_id: str):
    """Create a payoff diagram for the Iron Condor"""
    
    # Extract strikes
    strikes = [leg.strike_price for leg in trade.legs]
    min_strike = min(strikes)
    max_strike = max(strikes)
    
    # Create price range
    price_range = np.arange(min_strike - 500, max_strike + 500, 10)
    
    # Calculate payoffs
    payoffs = []
    for price in price_range:
        total_payoff = 0
        for leg in trade.legs:
            if leg.option_type == OptionType.CALL:
                intrinsic_value = max(0, price - leg.strike_price)
            else:  # PUT
                intrinsic_value = max(0, leg.strike_price - price)
            
            if leg.position_type == PositionType.LONG:
                payoff = intrinsic_value - leg.entry_price
            else:  # SHORT
                payoff = leg.entry_price - intrinsic_value
            
            total_payoff += payoff * leg.quantity
        payoffs.append(total_payoff)
    
    payoffs = np.array(payoffs)
    
    # Find max profit and loss
    max_profit = np.max(payoffs)
    max_loss = np.min(payoffs)
    
    # Find breakeven points
    breakevens = []
    for i in range(1, len(price_range)):
        if payoffs[i-1] * payoffs[i] < 0:
            breakevens.append(round(price_range[i], 2))
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Plot payoff curve
    plt.plot(price_range, payoffs, 'b-', linewidth=2, label='Payoff at Expiry')
    
    # Mark current spot price
    plt.axvline(x=spot_price, color='red', linestyle='--', 
               label=f'Current Spot: {spot_price}')
    
    # Mark strikes
    for strike in strikes:
        plt.axvline(x=strike, color='gray', linestyle=':', alpha=0.7)
    
    # Mark breakeven points
    for be in breakevens:
        plt.axvline(x=be, color='green', linestyle=':', alpha=0.7)
        plt.text(be, max_profit * 0.1, f'BE: {be}', 
                rotation=90, ha='right', va='bottom')
    
    # Formatting
    plt.xlabel('NIFTY Price at Expiry')
    plt.ylabel('Profit/Loss (₹)')
    plt.title(f'Iron Condor Strategy - {trade_id}\n'
             f'Max Profit: ₹{max_profit:.0f} | Max Loss: ₹{max_loss:.0f}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Add strategy details
    strategy_text = f"""Strategy Details:
Strikes: {sorted(strikes)}
Current P&L: ₹{payoffs[np.argmin(np.abs(price_range - spot_price))]:.0f}
Breakevens: {breakevens}
Net Premium: ₹{max_profit:.0f}"""
    
    plt.text(0.02, 0.98, strategy_text, transform=plt.gca().transAxes,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    # Save the plot
    plot_path = f"iron_condor_demo_{trade_id}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"\n📊 Payoff diagram saved to: {plot_path}")
    
    plt.show()

def main():
    """Main function"""
    try:
        # Create mock Iron Condor
        trade = create_mock_iron_condor(25000)
        
        print(f"\n" + "=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Trade ID: {trade.trade_id}")
        print(f"Strategy: {trade.strategy_name}")
        print(f"Strikes: {[leg.strike_price for leg in trade.legs]}")
        print(f"Status: {trade.status.value}")
        
    except Exception as e:
        logger.error(f"Error in demo: {e}")
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()

