#!/usr/bin/env python3
"""
Strategy Manager for handling open positions and creating new strategies.
"""

import logging
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from trade_database import TradeDatabase
from trade_models import Trade, TradeLeg, TradeStatus, OptionType, PositionType
from upstox_option_chain import UpstoxOptionChain
from utils import Utils
from datawarehouse import datawarehouse
import math

logger = logging.getLogger("StrategyManager")

class StrategyManager:
    """Manages trading strategies and position tracking"""
    
    def __init__(self, agent=None, instruments=None, broker_type=None, db_path: str = "market_trades.db"):
        """Initialize the strategy manager"""
        self.db = TradeDatabase(db_path)
        self.option_chain = None
        self.agent = agent
        self.instruments = instruments
        self.broker_type = broker_type
    
    def set_agent(self, agent):
        """Set the agent after initialization"""
        self.agent = agent
        logger.info("Agent set for StrategyManager")
        
    def initialize_option_chain(self, access_token: str):
        """Initialize the option chain fetcher"""
        try:
            self.option_chain = UpstoxOptionChain(access_token)
            logger.info("Option chain initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize option chain: {e}")
            raise
    
    def get_open_positions(self) -> List[Trade]:
        """Get all open positions from the database"""
        try:
            open_trades = self.db.get_open_trades()
            logger.info(f"Found {len(open_trades)} open positions")
            return open_trades
        except Exception as e:
            logger.error(f"Error fetching open positions: {e}")
            return []
        
    def get_nearest_strike(self, spot_price: float, strike_interval: int = 50) -> int:
        """Get the nearest strike price to spot price"""
        return int(round(spot_price / strike_interval) * strike_interval)
    
    def get_primary_instrument(self) -> str:
        """Get the primary instrument key from the instruments configuration"""
        if self.instruments and self.broker_type and self.broker_type in self.instruments:
            # Get the first instrument from the broker's instruments
            broker_instruments = self.instruments[self.broker_type]
            if broker_instruments:
                return list(broker_instruments.keys())[0]
        
        # Fallback to NIFTY 50 if no instruments available
        logger.warning("No instruments available, using fallback NIFTY 50")
        return "NSE_INDEX|Nifty 50"
    
    def create_iron_condor_strategy(self, spot_price: float) -> Trade:
        """
        Create an Iron Condor strategy based on current spot price
        
        Args:
            spot_price: Current NIFTY spot price
            
        Returns:
            Trade: Iron Condor trade object
        """
        try:
            # Calculate strikes based on requirements
            current_strike = self.get_nearest_strike(spot_price)
            
            # Short positions: 400 points away from current strike
            short_call_strike = current_strike + 400
            short_put_strike = current_strike - 400
            
            # Long positions: 200 points away from short positions
            long_call_strike = short_call_strike + 200
            long_put_strike = short_put_strike - 200
            
            # Get next expiry - use a future date to avoid API issues
            from datetime import date, timedelta
            today = date.today()
            # Get next Tuesday (NIFTY weekly expiry)
            days_until_tuesday = (1 - today.weekday()) % 7
            if days_until_tuesday == 0:
                days_until_tuesday = 7
            next_expiry = (today + timedelta(days=days_until_tuesday)).strftime("%Y-%m-%d")
            
            # Get option data for these strikes
            options = self.option_chain.fetch(expiry=next_expiry)
            
            # Find the specific options we need
            trade_legs = []
            lot_size = 75  # NIFTY lot size
            
            # Create trade legs
            legs_config = [
                {
                    "strike": long_put_strike,
                    "option_type": OptionType.PUT,
                    "position_type": PositionType.LONG,
                    "description": "Long Put (Protection)"
                },
                {
                    "strike": short_put_strike,
                    "option_type": OptionType.PUT,
                    "position_type": PositionType.SHORT,
                    "description": "Short Put (Income)"
                },
                {
                    "strike": short_call_strike,
                    "option_type": OptionType.CALL,
                    "position_type": PositionType.SHORT,
                    "description": "Short Call (Income)"
                },
                {
                    "strike": long_call_strike,
                    "option_type": OptionType.CALL,
                    "position_type": PositionType.LONG,
                    "description": "Long Call (Protection)"
                }
            ]
            
            for leg_config in legs_config:
                option_data = self._find_option_data(options, leg_config["strike"], leg_config["option_type"])
                
                if option_data:
                    trade_leg = TradeLeg(
                        instrument=option_data.get('instrument_key', ''),
                        instrument_name=option_data.get('instrument_name', ''),
                        option_type=leg_config["option_type"],
                        strike_price=leg_config["strike"],
                        position_type=leg_config["position_type"],
                        quantity=lot_size,
                        entry_timestamp=datetime.now(),
                        entry_price=option_data.get('last_price', 0.0)
                    )
                    trade_legs.append(trade_leg)
                else:
                    logger.warning(f"Could not find option data for {leg_config['description']} at strike {leg_config['strike']}")
            
            if len(trade_legs) != 4:
                raise ValueError(f"Could only create {len(trade_legs)} out of 4 required legs")
            
            # Create the trade
            trade_id = f"IC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            trade = Trade(
                trade_id=trade_id,
                strategy_name="Iron Condor",
                underlying_instrument="NIFTY",
                status=TradeStatus.OPEN,
                legs=trade_legs,
                notes=f"Iron Condor: {long_put_strike}P/{short_put_strike}P/{short_call_strike}C/{long_call_strike}C",
                tags=["Iron Condor", "Options Strategy"]
            )
            
            # Note: Trade is not saved to database until broker execution
            # This is just a strategy calculation for display purposes
            logger.info(f"Created Iron Condor strategy for display: {trade_id}")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error creating Iron Condor strategy: {e}")
            raise
    
    
    def _find_option_data(self, options: List[Dict], strike: int, option_type: OptionType) -> Optional[Dict]:
        """Find option data for specific strike and type"""
        for option in options:
            if (option.get('strike_price') == strike and 
                option.get('option_type') == option_type.value):
                return option
        return None
    
    def calculate_iron_condor_payoff(self, trade: Trade, spot_price: float) -> Dict[str, Any]:
        """Calculate Iron Condor payoff analysis"""
        try:
            # Extract legs
            legs = trade.legs
            
            # Create payoff calculation data
            payoff_legs = []
            for leg in legs:
                payoff_legs.append({
                    "type": leg.option_type.value.lower(),
                    "position": leg.position_type.value.lower(),
                    "strike": leg.strike_price,
                    "premium": leg.entry_price
                })
            
            # Calculate payoff range
            min_strike = min(leg.strike_price for leg in legs)
            max_strike = max(leg.strike_price for leg in legs)
            
            # Create price range
            price_range = np.arange(
                min_strike - 500, 
                max_strike + 500, 
                10
            )
            
            # Calculate payoffs
            payoffs = []
            lot_size = 75  # NIFTY lot size
            for price in price_range:
                total_payoff = 0
                for leg in payoff_legs:
                    payoff = self._calculate_leg_payoff(price, leg)
                    total_payoff += payoff
                payoffs.append(total_payoff * lot_size)
            
            payoffs = np.array(payoffs)
            
            # Find max profit and loss
            max_profit = np.max(payoffs)
            max_loss = np.min(payoffs)
            
            # Find breakeven points
            breakevens = []
            for i in range(1, len(price_range)):
                if payoffs[i-1] * payoffs[i] < 0:
                    breakevens.append(round(price_range[i], 2))
            
            return {
                "price_range": price_range,
                "payoffs": payoffs,
                "max_profit": max_profit,
                "max_loss": max_loss,
                "breakevens": breakevens,
                "current_payoff": payoffs[np.argmin(np.abs(price_range - spot_price))]
            }
            
        except Exception as e:
            logger.error(f"Error calculating Iron Condor payoff: {e}")
            return {}
    
    def _calculate_leg_payoff(self, price: float, leg: Dict) -> float:
        """Calculate payoff for a single leg"""
        option_type = leg["type"]
        position = leg["position"]
        strike = leg["strike"]
        premium = leg["premium"]
        
        if option_type == "call":
            intrinsic_value = max(0, price - strike)
        else:  # put
            intrinsic_value = max(0, strike - price)
        
        if position == "long":
            return intrinsic_value - premium
        else:  # short
            return premium - intrinsic_value
    
    def plot_iron_condor(self, trade: Trade, spot_price: float, save_path: Optional[str] = None):
        """Plot Iron Condor payoff diagram"""
        try:
            payoff_data = self.calculate_iron_condor_payoff(trade, spot_price)
            
            if not payoff_data:
                logger.error("No payoff data available for plotting")
                return
            
            # Create the plot
            plt.figure(figsize=(12, 8))
            
            # Plot payoff curve
            plt.plot(payoff_data["price_range"], payoff_data["payoffs"], 
                    'b-', linewidth=2, label='Payoff at Expiry')
            
            # Mark current spot price
            plt.axvline(x=spot_price, color='red', linestyle='--', 
                       label=f'Current Spot: {spot_price}')
            
            # Mark strikes
            strikes = [leg.strike_price for leg in trade.legs]
            for strike in strikes:
                plt.axvline(x=strike, color='gray', linestyle=':', alpha=0.7)
            
            # Mark breakeven points
            for be in payoff_data["breakevens"]:
                plt.axvline(x=be, color='green', linestyle=':', alpha=0.7)
                plt.text(be, payoff_data["max_profit"] * 0.1, f'BE: {be}', 
                        rotation=90, ha='right', va='bottom')
            
            # Formatting
            plt.xlabel('NIFTY Price at Expiry')
            plt.ylabel('Profit/Loss (₹)')
            plt.title(f'Iron Condor Strategy - {trade.trade_id}\n'
                     f'Max Profit: ₹{payoff_data["max_profit"]:.0f} | '
                     f'Max Loss: ₹{payoff_data["max_loss"]:.0f}')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Add strategy details
            strategy_text = f"""Strategy Details:
Strikes: {sorted(strikes)}
Current P&L: ₹{payoff_data["current_payoff"]:.0f}
Breakevens: {payoff_data["breakevens"]}"""
            
            plt.text(0.02, 0.98, strategy_text, transform=plt.gca().transAxes,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Plot saved to {save_path}")
            
            # Don't call plt.show() - the chart will be displayed in Grid 2 by the main app
            # plt.show()  # Commented out to prevent new window
            
        except Exception as e:
            logger.error(f"Error plotting Iron Condor: {e}")
    
    def manage_positions(self, access_token: str) -> Dict[str, Any]:
        """Main method to manage positions and create strategies"""
        try:
            # Try to get real spot price, fallback to default if API fails
            spot_price = 250.0  # Default fallback
            try:
                # Initialize option chain
                self.initialize_option_chain(access_token)
                
                # Get spot price from agent
                if self.agent and hasattr(self.agent, 'get_latest_price'):
                    primary_instrument = self.get_primary_instrument()
                    spot_price = self.agent.get_latest_price(primary_instrument)
                    
                    if spot_price is None:
                        logger.warning(f"No spot price available from agent for {primary_instrument}")
                        spot_price = 250.0  # Use fallback price
                    else:
                        logger.info(f"Retrieved spot price from agent: {spot_price}")
                else:
                    logger.warning("No agent available or agent doesn't have get_latest_price method")
                    spot_price = 250.0  # Use fallback price
                    
            except Exception as api_error:
                logger.warning(f"Error getting spot price from agent, using fallback: {api_error}")
                spot_price = 250.0  # Use fallback price
            
            # Try to create Iron Condor strategy with real option data
            logger.info("Creating Iron Condor strategy for display...")
            
            try:
                trade = self.create_iron_condor_strategy(spot_price)
                
                result = {
                    "spot_price": spot_price,
                    "open_positions": 0,  # No positions stored in DB
                    "action_taken": "iron_condor_created",
                    "trade_created": trade.trade_id,
                    "strategy_details": {
                        "strikes": [leg.strike_price for leg in trade.legs],
                        "expiry": trade.legs[0].entry_timestamp.strftime("%Y-%m-%d") if trade.legs else "N/A",
                        "description": trade.notes
                    }
                }
                
                return result
                
            except Exception as strategy_error:
                logger.error(f"Failed to create Iron Condor strategy: {strategy_error}")
                return {
                    "spot_price": spot_price,
                    "open_positions": 0,
                    "action_taken": "error",
                    "error": f"Failed to create Iron Condor strategy: {strategy_error}",
                    "strategy_details": {
                        "error_message": f"Unable to fetch option chain data. Please check your connection and try again. Error: {strategy_error}"
                    }
                }
            
        except Exception as e:
            logger.error(f"Error in manage_positions: {e}")
            return {
                "error": str(e),
                "spot_price": 25000.0,
                "open_positions": 0,
                "action_taken": "error"
            }
