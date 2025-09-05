#!/usr/bin/env python3
"""
Trade and TradeLeg data models for complex trading strategies.

This module provides data classes for managing trades with multiple legs,
such as Iron Condors, Straddles, Strangles, etc.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import logging

logger = logging.getLogger("TradeModels")

class OptionType(Enum):
    """Enumeration for option types"""
    CALL = "CALL"
    PUT = "PUT"

class PositionType(Enum):
    """Enumeration for position types"""
    LONG = "LONG"
    SHORT = "SHORT"

class TradeStatus(Enum):
    """Enumeration for trade status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"

@dataclass
class TradeLeg:
    """
    Represents a single leg of a trade (e.g., one option contract).
    
    Each trade leg contains all the information needed to track
    a single position within a complex trade strategy.
    """
    # Basic instrument information
    instrument: str
    instrument_name: str
    option_type: OptionType
    strike_price: float
    
    # Position details
    position_type: PositionType  # LONG or SHORT
    quantity: int
    
    # Entry information
    entry_timestamp: datetime
    entry_price: float
    
    # Exit information (optional for open positions)
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    
    # Calculated fields
    profit: Optional[float] = None
    
    def __post_init__(self):
        """Calculate profit after initialization"""
        self.calculate_profit()
    
    def calculate_profit(self) -> float:
        """
        Calculate profit/loss for this trade leg.
        
        Returns:
            float: Profit (positive) or loss (negative)
        """
        if self.exit_price is None:
            # Position is still open, profit is unrealized
            self.profit = None
            return 0.0
        
        # Calculate profit based on position type
        if self.position_type == PositionType.LONG:
            # Long position: profit = (exit_price - entry_price) * quantity
            self.profit = (self.exit_price - self.entry_price) * self.quantity
        else:  # SHORT
            # Short position: profit = (entry_price - exit_price) * quantity
            self.profit = (self.entry_price - self.exit_price) * self.quantity
        
        return self.profit
    
    def is_closed(self) -> bool:
        """Check if this trade leg is closed"""
        return self.exit_price is not None and self.exit_timestamp is not None
    
    def is_open(self) -> bool:
        """Check if this trade leg is open"""
        return not self.is_closed()
    
    def get_unrealized_pnl(self, current_price: float) -> float:
        """
        Calculate unrealized P&L for open positions.
        
        Args:
            current_price (float): Current market price of the instrument
            
        Returns:
            float: Unrealized profit/loss
        """
        if self.is_closed():
            return 0.0
        
        if self.position_type == PositionType.LONG:
            return (current_price - self.entry_price) * self.quantity
        else:  # SHORT
            return (self.entry_price - current_price) * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TradeLeg to dictionary for JSON serialization"""
        return {
            'instrument': self.instrument,
            'instrument_name': self.instrument_name,
            'option_type': self.option_type.value,
            'strike_price': self.strike_price,
            'position_type': self.position_type.value,
            'quantity': self.quantity,
            'entry_timestamp': self.entry_timestamp.isoformat(),
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'exit_timestamp': self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            'profit': self.profit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeLeg':
        """Create TradeLeg from dictionary"""
        return cls(
            instrument=data['instrument'],
            instrument_name=data['instrument_name'],
            option_type=OptionType(data['option_type']),
            strike_price=data['strike_price'],
            position_type=PositionType(data['position_type']),
            quantity=data['quantity'],
            entry_timestamp=datetime.fromisoformat(data['entry_timestamp']),
            entry_price=data['entry_price'],
            exit_price=data.get('exit_price'),
            exit_timestamp=datetime.fromisoformat(data['exit_timestamp']) if data.get('exit_timestamp') else None,
            profit=data.get('profit')
        )

@dataclass
class Trade:
    """
    Represents a complete trade that can have multiple legs.
    
    Examples:
    - Iron Condor: 4 legs (2 short calls, 2 long calls)
    - Straddle: 2 legs (1 long call, 1 long put)
    - Simple option: 1 leg
    """
    # Basic trade information
    trade_id: str
    strategy_name: str
    underlying_instrument: str
    
    # Trade legs
    legs: List[TradeLeg] = field(default_factory=list)
    
    # Trade metadata
    created_timestamp: datetime = field(default_factory=datetime.now)
    status: TradeStatus = TradeStatus.OPEN
    
    # Additional information
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def add_leg(self, leg: TradeLeg) -> None:
        """Add a trade leg to this trade"""
        self.legs.append(leg)
        self._update_status()
    
    def remove_leg(self, leg_index: int) -> TradeLeg:
        """Remove a trade leg by index"""
        if 0 <= leg_index < len(self.legs):
            removed_leg = self.legs.pop(leg_index)
            self._update_status()
            return removed_leg
        raise IndexError(f"Leg index {leg_index} out of range")
    
    def close_leg(self, leg_index: int, exit_price: float, exit_timestamp: Optional[datetime] = None) -> None:
        """
        Close a specific trade leg.
        
        Args:
            leg_index (int): Index of the leg to close
            exit_price (float): Exit price for the leg
            exit_timestamp (datetime, optional): Exit timestamp (defaults to now)
        """
        if 0 <= leg_index < len(self.legs):
            leg = self.legs[leg_index]
            leg.exit_price = exit_price
            leg.exit_timestamp = exit_timestamp or datetime.now()
            leg.calculate_profit()
            self._update_status()
        else:
            raise IndexError(f"Leg index {leg_index} out of range")
    
    def close_all_legs(self, exit_prices: List[float], exit_timestamp: Optional[datetime] = None) -> None:
        """
        Close all trade legs at once.
        
        Args:
            exit_prices (List[float]): Exit prices for each leg (in order)
            exit_timestamp (datetime, optional): Exit timestamp (defaults to now)
        """
        if len(exit_prices) != len(self.legs):
            raise ValueError(f"Expected {len(self.legs)} exit prices, got {len(exit_prices)}")
        
        exit_time = exit_timestamp or datetime.now()
        for i, (leg, exit_price) in enumerate(zip(self.legs, exit_prices)):
            leg.exit_price = exit_price
            leg.exit_timestamp = exit_time
            leg.calculate_profit()
        
        self._update_status()
    
    def _update_status(self) -> None:
        """Update trade status based on leg statuses"""
        if not self.legs:
            self.status = TradeStatus.OPEN
            return
        
        closed_legs = sum(1 for leg in self.legs if leg.is_closed())
        total_legs = len(self.legs)
        
        if closed_legs == 0:
            self.status = TradeStatus.OPEN
        elif closed_legs == total_legs:
            self.status = TradeStatus.CLOSED
        else:
            self.status = TradeStatus.PARTIALLY_CLOSED
    
    def get_total_profit(self) -> float:
        """
        Calculate total profit/loss for all closed legs.
        
        Returns:
            float: Total realized profit/loss
        """
        total_profit = 0.0
        for leg in self.legs:
            if leg.is_closed() and leg.profit is not None:
                total_profit += leg.profit
        return total_profit
    
    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate unrealized P&L for all open legs.
        
        Args:
            current_prices (Dict[str, float]): Current prices for each instrument
            
        Returns:
            float: Total unrealized profit/loss
        """
        total_unrealized = 0.0
        for leg in self.legs:
            if leg.is_open() and leg.instrument in current_prices:
                total_unrealized += leg.get_unrealized_pnl(current_prices[leg.instrument])
        return total_unrealized
    
    def get_open_legs(self) -> List[TradeLeg]:
        """Get all open trade legs"""
        return [leg for leg in self.legs if leg.is_open()]
    
    def get_closed_legs(self) -> List[TradeLeg]:
        """Get all closed trade legs"""
        return [leg for leg in self.legs if leg.is_closed()]
    
    def get_legs_by_option_type(self, option_type: OptionType) -> List[TradeLeg]:
        """Get all legs of a specific option type"""
        return [leg for leg in self.legs if leg.option_type == option_type]
    
    def get_legs_by_position_type(self, position_type: PositionType) -> List[TradeLeg]:
        """Get all legs of a specific position type"""
        return [leg for leg in self.legs if leg.position_type == position_type]
    
    def is_iron_condor(self) -> bool:
        """Check if this trade is an Iron Condor (4 legs: 2 short calls, 2 long calls)"""
        if len(self.legs) != 4:
            return False
        
        call_legs = self.get_legs_by_option_type(OptionType.CALL)
        put_legs = self.get_legs_by_option_type(OptionType.PUT)
        short_legs = self.get_legs_by_position_type(PositionType.SHORT)
        long_legs = self.get_legs_by_position_type(PositionType.LONG)
        
        return len(call_legs) == 2 and len(put_legs) == 2 and len(short_legs) == 2 and len(long_legs) == 2
    
    def is_straddle(self) -> bool:
        """Check if this trade is a Straddle (2 legs: 1 long call, 1 long put)"""
        if len(self.legs) != 2:
            return False
        
        call_legs = self.get_legs_by_option_type(OptionType.CALL)
        put_legs = self.get_legs_by_option_type(OptionType.PUT)
        long_legs = self.get_legs_by_position_type(PositionType.LONG)
        
        return len(call_legs) == 1 and len(put_legs) == 1 and len(long_legs) == 2
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the trade"""
        return {
            'trade_id': self.trade_id,
            'strategy_name': self.strategy_name,
            'underlying_instrument': self.underlying_instrument,
            'status': self.status.value,
            'total_legs': len(self.legs),
            'open_legs': len(self.get_open_legs()),
            'closed_legs': len(self.get_closed_legs()),
            'total_profit': self.get_total_profit(),
            'created_timestamp': self.created_timestamp.isoformat(),
            'is_iron_condor': self.is_iron_condor(),
            'is_straddle': self.is_straddle()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Trade to dictionary for JSON serialization"""
        return {
            'trade_id': self.trade_id,
            'strategy_name': self.strategy_name,
            'underlying_instrument': self.underlying_instrument,
            'legs': [leg.to_dict() for leg in self.legs],
            'created_timestamp': self.created_timestamp.isoformat(),
            'status': self.status.value,
            'notes': self.notes,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """Create Trade from dictionary"""
        legs = [TradeLeg.from_dict(leg_data) for leg_data in data.get('legs', [])]
        
        return cls(
            trade_id=data['trade_id'],
            strategy_name=data['strategy_name'],
            underlying_instrument=data['underlying_instrument'],
            legs=legs,
            created_timestamp=datetime.fromisoformat(data['created_timestamp']),
            status=TradeStatus(data['status']),
            notes=data.get('notes'),
            tags=data.get('tags', [])
        )
    
    def to_json(self) -> str:
        """Convert Trade to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Trade':
        """Create Trade from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation of the trade"""
        return f"Trade({self.trade_id}, {self.strategy_name}, {len(self.legs)} legs, {self.status.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the trade"""
        return f"Trade(trade_id='{self.trade_id}', strategy_name='{self.strategy_name}', legs={len(self.legs)}, status='{self.status.value}')"


# Example usage and factory functions
def create_iron_condor(trade_id: str, underlying: str, 
                      short_call_strike: float, long_call_strike: float,
                      short_put_strike: float, long_put_strike: float,
                      call_premium: float, put_premium: float,
                      quantity: int = 1) -> Trade:
    """
    Create an Iron Condor trade.
    
    Args:
        trade_id (str): Unique trade identifier
        underlying (str): Underlying instrument
        short_call_strike (float): Strike price for short call
        long_call_strike (float): Strike price for long call
        short_put_strike (float): Strike price for short put
        long_put_strike (float): Strike price for long put
        call_premium (float): Premium received for calls
        put_premium (float): Premium received for puts
        quantity (int): Number of contracts
        
    Returns:
        Trade: Iron Condor trade with 4 legs
    """
    trade = Trade(
        trade_id=trade_id,
        strategy_name="Iron Condor",
        underlying_instrument=underlying
    )
    
    # Short call leg
    trade.add_leg(TradeLeg(
        instrument=f"{underlying}_CALL_{short_call_strike}",
        instrument_name=f"{underlying} Call {short_call_strike}",
        option_type=OptionType.CALL,
        strike_price=short_call_strike,
        position_type=PositionType.SHORT,
        quantity=quantity,
        entry_timestamp=datetime.now(),
        entry_price=call_premium
    ))
    
    # Long call leg
    trade.add_leg(TradeLeg(
        instrument=f"{underlying}_CALL_{long_call_strike}",
        instrument_name=f"{underlying} Call {long_call_strike}",
        option_type=OptionType.CALL,
        strike_price=long_call_strike,
        position_type=PositionType.LONG,
        quantity=quantity,
        entry_timestamp=datetime.now(),
        entry_price=call_premium * 0.1  # Assume long call costs 10% of short call
    ))
    
    # Short put leg
    trade.add_leg(TradeLeg(
        instrument=f"{underlying}_PUT_{short_put_strike}",
        instrument_name=f"{underlying} Put {short_put_strike}",
        option_type=OptionType.PUT,
        strike_price=short_put_strike,
        position_type=PositionType.SHORT,
        quantity=quantity,
        entry_timestamp=datetime.now(),
        entry_price=put_premium
    ))
    
    # Long put leg
    trade.add_leg(TradeLeg(
        instrument=f"{underlying}_PUT_{long_put_strike}",
        instrument_name=f"{underlying} Put {long_put_strike}",
        option_type=OptionType.PUT,
        strike_price=long_put_strike,
        position_type=PositionType.LONG,
        quantity=quantity,
        entry_timestamp=datetime.now(),
        entry_price=put_premium * 0.1  # Assume long put costs 10% of short put
    ))
    
    return trade


def create_straddle(trade_id: str, underlying: str, strike_price: float,
                   call_premium: float, put_premium: float,
                   quantity: int = 1) -> Trade:
    """
    Create a Straddle trade.
    
    Args:
        trade_id (str): Unique trade identifier
        underlying (str): Underlying instrument
        strike_price (float): Strike price for both options
        call_premium (float): Premium paid for call
        put_premium (float): Premium paid for put
        quantity (int): Number of contracts
        
    Returns:
        Trade: Straddle trade with 2 legs
    """
    trade = Trade(
        trade_id=trade_id,
        strategy_name="Straddle",
        underlying_instrument=underlying
    )
    
    # Long call leg
    trade.add_leg(TradeLeg(
        instrument=f"{underlying}_CALL_{strike_price}",
        instrument_name=f"{underlying} Call {strike_price}",
        option_type=OptionType.CALL,
        strike_price=strike_price,
        position_type=PositionType.LONG,
        quantity=quantity,
        entry_timestamp=datetime.now(),
        entry_price=call_premium
    ))
    
    # Long put leg
    trade.add_leg(TradeLeg(
        instrument=f"{underlying}_PUT_{strike_price}",
        instrument_name=f"{underlying} Put {strike_price}",
        option_type=OptionType.PUT,
        strike_price=strike_price,
        position_type=PositionType.LONG,
        quantity=quantity,
        entry_timestamp=datetime.now(),
        entry_price=put_premium
    ))
    
    return trade


if __name__ == "__main__":
    # Example usage
    print("Creating example trades...")
    
    # Create an Iron Condor
    iron_condor = create_iron_condor(
        trade_id="IC_001",
        underlying="NIFTY",
        short_call_strike=25000,
        long_call_strike=25100,
        short_put_strike=24000,
        long_put_strike=23900,
        call_premium=50.0,
        put_premium=45.0,
        quantity=1
    )
    
    print(f"Iron Condor: {iron_condor}")
    print(f"Is Iron Condor: {iron_condor.is_iron_condor()}")
    print(f"Total legs: {len(iron_condor.legs)}")
    print(f"Open legs: {len(iron_condor.get_open_legs())}")
    
    # Create a Straddle
    straddle = create_straddle(
        trade_id="ST_001",
        underlying="NIFTY",
        strike_price=24500,
        call_premium=100.0,
        put_premium=95.0,
        quantity=1
    )
    
    print(f"\nStraddle: {straddle}")
    print(f"Is Straddle: {straddle.is_straddle()}")
    print(f"Total legs: {len(straddle.legs)}")
    
    # Show trade summary
    print(f"\nIron Condor Summary: {iron_condor.get_summary()}")
    print(f"Straddle Summary: {straddle.get_summary()}")
