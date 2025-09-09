#!/usr/bin/env python3
"""
Script to create an Iron Condor strategy in the database
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

import logging
from datetime import datetime
from trade_models import Trade, TradeLeg, OptionType, PositionType, TradeStatus
from trade_database import TradeDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def create_iron_condor_strategy(spot_price=25000):
    """Create an Iron Condor strategy with the given spot price"""
    try:
        logger.info("=" * 80)
        logger.info("CREATING IRON CONDOR STRATEGY")
        logger.info("=" * 80)
        logger.info(f"Spot Price: {spot_price}")
        
        # Calculate strikes around the spot price
        # Iron Condor: Sell Put Spread + Sell Call Spread
        # Put spread: Sell higher put, Buy lower put
        # Call spread: Sell lower call, Buy higher call
        
        put_strike_short = spot_price - 200  # Sell put at 24800
        put_strike_long = spot_price - 400   # Buy put at 24600
        call_strike_short = spot_price + 200 # Sell call at 25200
        call_strike_long = spot_price + 400  # Buy call at 25400
        
        # Premiums (example values - in real scenario these would come from market data)
        put_premium_short = 45.0  # Premium received for selling put
        put_premium_long = 25.0   # Premium paid for buying put
        call_premium_short = 50.0 # Premium received for selling call
        call_premium_long = 30.0  # Premium paid for buying call
        
        logger.info(f"Put Spread: Sell {put_strike_short} @ {put_premium_short}, Buy {put_strike_long} @ {put_premium_long}")
        logger.info(f"Call Spread: Sell {call_strike_short} @ {call_premium_short}, Buy {call_strike_long} @ {call_premium_long}")
        
        # Create trade legs
        legs = [
            # Put spread - Sell higher put, Buy lower put
            TradeLeg(
                instrument="NSE_INDEX|Nifty 50",
                instrument_name="NIFTY 50",
                option_type=OptionType.PUT,
                strike_price=put_strike_short,
                position_type=PositionType.SHORT,  # Sell
                quantity=1,
                entry_timestamp=datetime.now(),
                entry_price=put_premium_short
            ),
            TradeLeg(
                instrument="NSE_INDEX|Nifty 50",
                instrument_name="NIFTY 50",
                option_type=OptionType.PUT,
                strike_price=put_strike_long,
                position_type=PositionType.LONG,  # Buy
                quantity=1,
                entry_timestamp=datetime.now(),
                entry_price=put_premium_long
            ),
            # Call spread - Sell lower call, Buy higher call
            TradeLeg(
                instrument="NSE_INDEX|Nifty 50",
                instrument_name="NIFTY 50",
                option_type=OptionType.CALL,
                strike_price=call_strike_short,
                position_type=PositionType.SHORT,  # Sell
                quantity=1,
                entry_timestamp=datetime.now(),
                entry_price=call_premium_short
            ),
            TradeLeg(
                instrument="NSE_INDEX|Nifty 50",
                instrument_name="NIFTY 50",
                option_type=OptionType.CALL,
                strike_price=call_strike_long,
                position_type=PositionType.LONG,  # Buy
                quantity=1,
                entry_timestamp=datetime.now(),
                entry_price=call_premium_long
            )
        ]
        
        # Calculate net premium received
        net_premium = (put_premium_short + call_premium_short) - (put_premium_long + call_premium_long)
        logger.info(f"Net Premium Received: {net_premium}")
        
        # Create trade
        trade = Trade(
            trade_id=f"IC_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            strategy_name="Iron Condor",
            underlying_instrument="NSE_INDEX|Nifty 50",
            status=TradeStatus.OPEN,
            created_timestamp=datetime.now(),
            legs=legs
        )
        
        logger.info(f"Created trade: {trade.trade_id}")
        logger.info(f"Strategy: {trade.strategy_name}")
        logger.info(f"Status: {trade.status.value}")
        logger.info(f"Number of legs: {len(trade.legs)}")
        
        # Save to database
        db = TradeDatabase("trades.db")
        db.save_trade(trade)
        
        logger.info("✅ Iron Condor strategy successfully saved to database")
        
        # Display trade details
        logger.info("\n" + "=" * 80)
        logger.info("TRADE DETAILS")
        logger.info("=" * 80)
        logger.info(f"Trade ID: {trade.trade_id}")
        logger.info(f"Strategy: {trade.strategy_name}")
        logger.info(f"Underlying: {trade.underlying_instrument}")
        logger.info(f"Status: {trade.status.value}")
        logger.info(f"Created: {trade.created_timestamp}")
        logger.info(f"Net Premium: ₹{net_premium}")
        
        logger.info("\nLegs:")
        for i, leg in enumerate(trade.legs, 1):
            logger.info(f"  {i}. {leg.position_type.value} {leg.option_type.value} {leg.strike_price} @ ₹{leg.entry_price}")
        
        # Calculate and display payoff analysis
        logger.info("\n" + "=" * 80)
        logger.info("PAYOFF ANALYSIS")
        logger.info("=" * 80)
        
        # Max profit = Net premium received
        max_profit = net_premium * 75  # Lot size
        logger.info(f"Max Profit: ₹{max_profit}")
        
        # Max loss = (Strike difference - Net premium) * Lot size
        put_spread_width = put_strike_short - put_strike_long  # 200
        call_spread_width = call_strike_long - call_strike_short  # 200
        max_loss_per_spread = max(put_spread_width, call_spread_width) - net_premium
        max_loss = max_loss_per_spread * 75  # Lot size
        logger.info(f"Max Loss: ₹{max_loss}")
        
        # Breakeven points
        put_breakeven = put_strike_short - net_premium
        call_breakeven = call_strike_short + net_premium
        logger.info(f"Put Breakeven: {put_breakeven}")
        logger.info(f"Call Breakeven: {call_breakeven}")
        
        # Profit range
        profit_range_start = put_breakeven
        profit_range_end = call_breakeven
        logger.info(f"Profit Range: {profit_range_start} - {profit_range_end}")
        
        logger.info("\n" + "=" * 80)
        logger.info("IRON CONDOR STRATEGY CREATION COMPLETED")
        logger.info("=" * 80)
        
        return trade
        
    except Exception as e:
        logger.error(f"Error creating Iron Condor strategy: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function"""
    try:
        # Create Iron Condor with spot price 25000
        trade = create_iron_condor_strategy(25000)
        
        if trade:
            print(f"\n✅ Successfully created Iron Condor strategy: {trade.trade_id}")
            print("The strategy has been saved to the database and can be viewed in the application.")
        else:
            print("\n❌ Failed to create Iron Condor strategy")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
