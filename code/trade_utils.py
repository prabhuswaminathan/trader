#!/usr/bin/env python3
"""
Utility functions for trading operations.

This module provides various utility functions for date/time operations,
expiry calculations, and other trading-related utilities.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
import calendar

logger = logging.getLogger("Utils")

class Utils:
    """
    Utility class containing various helper functions for trading operations.
    """
    
    # Market holidays (can be expanded)
    MARKET_HOLIDAYS = [
        # Add specific holidays as needed
        # Example: date(2024, 1, 26),  # Republic Day
        # Example: date(2024, 3, 8),   # Holi
        # Example: date(2024, 4, 11),  # Eid
        # Example: date(2024, 4, 17),  # Ram Navami
        # Example: date(2024, 5, 1),   # Labour Day
        # Example: date(2024, 8, 15),  # Independence Day
        # Example: date(2024, 10, 2),  # Gandhi Jayanti
        # Example: date(2024, 11, 1),  # Diwali
        # Example: date(2024, 12, 25), # Christmas
    ]
    
    @staticmethod
    def get_next_weekly_expiry() -> List[str]:
        """
        Get the list of next 5 weekly expiry dates for NIFTY options.
        
        NIFTY weekly options expire every Tuesday. The function returns the list of expiry dates in YYYY-MM-DD format.
        
        Returns:
            List[str]: List of expiry dates in YYYY-MM-DD format
            
        Raises:
            ValueError: If list of expiry dates is empty
        """
        try:
            # Get current date
            today = date.today()
            
            # Find the next Tuesday (NIFTY weekly expiry day)
            # Monday = 0, Tuesday = 1, Wednesday = 2, Thursday = 3, Friday = 4, Saturday = 5, Sunday = 6
            days_until_tuesday = (1 - today.weekday()) % 7
            if days_until_tuesday == 0:  # If today is Tuesday
                days_until_tuesday = 7  # Get next Tuesday

            expiry_dates = []            
            for weeks_ahead in range(5):
                # Calculate the target expiry date
                target_date = today + timedelta(days=days_until_tuesday + (weeks_ahead * 7))
                
                # Check if the target date falls on a market holiday
                # If it does, move to the previous working day
                while target_date in Utils.MARKET_HOLIDAYS or Utils.isWeekend(datetime.combine(target_date, datetime.min.time())):  # Skip weekends and holidays
                    target_date -= timedelta(days=1)
                
                # Format as YYYY-MM-DD
                expiry_dates.append(target_date.strftime("%Y-%m-%d"))
                
            return expiry_dates
            
        except Exception as e:
            logger.error(f"Error calculating weekly expiry: {e}")
            raise
    
    @staticmethod
    def get_next_tuesday_expiry(weeks_ahead: int = 0) -> str:
        """
        Get the next Tuesday expiry date (as originally requested).
        
        This function calculates expiry dates for Tuesday expiries.
        
        Args:
            weeks_ahead (int): Number of weeks ahead to look for expiry
                             0 = next expiry, 1 = following expiry, etc.
        
        Returns:
            str: Expiry date in YYYY-MM-DD format
            
        Raises:
            ValueError: If weeks_ahead is negative
        """
        if weeks_ahead < 0:
            raise ValueError("weeks_ahead must be non-negative")
        
        try:
            # Get current date
            today = date.today()
            
            # Find the next Tuesday
            # Monday = 0, Tuesday = 1, Wednesday = 2, Thursday = 3, Friday = 4, Saturday = 5, Sunday = 6
            days_until_tuesday = (1 - today.weekday()) % 7
            if days_until_tuesday == 0:  # If today is Tuesday
                days_until_tuesday = 7  # Get next Tuesday
            
            # Calculate the target expiry date
            target_date = today + timedelta(days=days_until_tuesday + (weeks_ahead * 7))
            
            # Check if the target date falls on a market holiday
            # If it does, move to the previous working day
            while target_date in Utils.MARKET_HOLIDAYS or Utils.isWeekend(datetime.combine(target_date, datetime.min.time())):  # Skip weekends and holidays
                target_date -= timedelta(days=1)
            
            # Format as YYYY-MM-DD
            expiry_date = target_date.strftime("%Y-%m-%d")
            
            logger.debug(f"Calculated Tuesday expiry for weeks_ahead={weeks_ahead}: {expiry_date}")
            return expiry_date
            
        except Exception as e:
            logger.error(f"Error calculating Tuesday expiry: {e}")
            raise
    
    @staticmethod
    def get_monthly_expiry(year: int, month: int) -> str:
        """
        Get the monthly expiry date for NIFTY options.
        
        Monthly expiry is typically the last Tuesday of the month.
        
        Args:
            year (int): Year
            month (int): Month (1-12)
        
        Returns:
            str: Monthly expiry date in YYYY-MM-DD format
        """
        try:
            # Get the last day of the month
            last_day = calendar.monthrange(year, month)[1]
            last_date = date(year, month, last_day)
            
            # Find the last Tuesday of the month
            # Go back from the last day to find the last Tuesday
            days_back = (last_date.weekday() - 1) % 7  # Tuesday = 1
            if days_back == 0 and last_date.weekday() != 1:  # If last day is not Tuesday
                days_back = 7
            
            monthly_expiry = last_date - timedelta(days=days_back)
            
            # Check if it's a holiday and adjust if needed
            while monthly_expiry in Utils.MARKET_HOLIDAYS or Utils.isWeekend(datetime.combine(monthly_expiry, datetime.min.time())):
                monthly_expiry -= timedelta(days=1)
            
            return monthly_expiry.strftime("%Y-%m-%d")
            
        except Exception as e:
            logger.error(f"Error calculating monthly expiry for {year}-{month:02d}: {e}")
            raise
    
    @staticmethod
    def get_expiry_series(expiry_type: str = "weekly", count: int = 4) -> List[str]:
        """
        Get a series of expiry dates.
        
        Args:
            expiry_type (str): Type of expiry ("weekly", "tuesday", "monthly")
            count (int): Number of expiry dates to return
        
        Returns:
            List[str]: List of expiry dates in YYYY-MM-DD format
        """
        try:
            expiry_dates = []
            
            if expiry_type.lower() == "weekly":
                for i in range(count):
                    expiry_dates.append(Utils.get_next_weekly_expiry(i))
            elif expiry_type.lower() == "tuesday":
                for i in range(count):
                    expiry_dates.append(Utils.get_next_tuesday_expiry(i))
            elif expiry_type.lower() == "monthly":
                # Get monthly expiries for the next few months
                current_date = date.today()
                for i in range(count):
                    target_date = current_date + timedelta(days=30 * i)
                    expiry_dates.append(Utils.get_monthly_expiry(target_date.year, target_date.month))
            else:
                raise ValueError(f"Invalid expiry_type: {expiry_type}")
            
            return expiry_dates
            
        except Exception as e:
            logger.error(f"Error getting expiry series: {e}")
            raise
    
    @staticmethod
    def isWeekend(dt: Optional[datetime] = None) -> bool:
        """
        Check if the given date/time is a weekend (Saturday or Sunday).
        
        Args:
            dt (datetime, optional): DateTime to check. If None, uses current time.
        
        Returns:
            bool: True if it's a weekend, False otherwise
        """
        if dt is None:
            dt = datetime.now()
        
        # Check if it's a weekend (Saturday = 5, Sunday = 6)
        return dt.weekday() >= 5
    
    @staticmethod
    def getPreviousFriday(dt: Optional[datetime] = None) -> datetime:
        """
        Get the previous Friday from the given date/time.
        
        Args:
            dt (datetime, optional): DateTime to check from. If None, uses current time.
        
        Returns:
            datetime: Previous Friday datetime
        """
        if dt is None:
            dt = datetime.now()
        
        # Get the date part
        current_date = dt.date()
        
        # Calculate days to go back to previous Friday
        # Friday = 4, so we need to go back (current_weekday - 4) % 7 days
        # If today is Friday, we want the previous Friday (7 days ago)
        days_back = (current_date.weekday() - 4) % 7
        if days_back == 0:  # If today is Friday
            days_back = 7  # Get previous Friday
        
        previous_friday = current_date - timedelta(days=days_back)
        
        # Convert back to datetime with the same time as input
        return datetime.combine(previous_friday, dt.time())
    
    @staticmethod
    def is_market_open(dt: Optional[datetime] = None) -> bool:
        """
        Check if the market is open at the given time.
        
        Args:
            dt (datetime, optional): DateTime to check. If None, uses current time.
        
        Returns:
            bool: True if market is open, False otherwise
        """
        if dt is None:
            dt = datetime.now()
        
        # Check if it's a weekend
        if Utils.isWeekend(dt):
            return False
        
        # Check if it's a holiday
        if dt.date() in Utils.MARKET_HOLIDAYS:
            return False
        
        # Check market hours (9:15 AM to 3:30 PM IST)
        market_open = dt.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = dt.replace(hour=15, minute=30, second=0, microsecond=0)
        
        return market_open <= dt <= market_close
    
    @staticmethod
    def get_next_market_open() -> datetime:
        """
        Get the next market open time.
        
        Returns:
            datetime: Next market open time
        """
        now = datetime.now()
        
        # If market is currently open, return current time
        if Utils.is_market_open(now):
            return now
        
        # Find next market open
        next_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
        
        # If it's past market hours today, move to next day
        if now.time() > next_open.time():
            next_open += timedelta(days=1)
        
        # Skip weekends and holidays
        while Utils.isWeekend(next_open) or next_open.date() in Utils.MARKET_HOLIDAYS:
            next_open += timedelta(days=1)
            next_open = next_open.replace(hour=9, minute=15, second=0, microsecond=0)
        
        return next_open
    
    @staticmethod
    def format_strike_price(price: float, step: float = 50.0) -> float:
        """
        Format strike price to the nearest step.
        
        Args:
            price (float): Current price
            step (float): Strike price step (default 50 for NIFTY)
        
        Returns:
            float: Formatted strike price
        """
        return round(price / step) * step
    
    @staticmethod
    def get_nearest_strikes(price: float, count: int = 5, step: float = 50.0) -> List[float]:
        """
        Get nearest strike prices around the current price.
        
        Args:
            price (float): Current price
            count (int): Number of strikes to return (total, including above and below)
            step (float): Strike price step
        
        Returns:
            List[float]: List of strike prices
        """
        # Round to nearest step
        rounded_price = Utils.format_strike_price(price, step)
        
        # Calculate strikes
        strikes = []
        half_count = count // 2
        
        for i in range(-half_count, half_count + 1):
            strike = rounded_price + (i * step)
            strikes.append(strike)
        
        return sorted(strikes)
    
    @staticmethod
    def calculate_days_to_expiry(expiry_date: str) -> int:
        """
        Calculate days remaining until expiry.
        
        Args:
            expiry_date (str): Expiry date in YYYY-MM-DD format
        
        Returns:
            int: Number of days until expiry
        """
        try:
            expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            today = date.today()
            return (expiry - today).days
        except Exception as e:
            logger.error(f"Error calculating days to expiry: {e}")
            raise
    
    @staticmethod
    def is_expiry_today(expiry_date: str) -> bool:
        """
        Check if the given date is today's expiry.
        
        Args:
            expiry_date (str): Expiry date in YYYY-MM-DD format
        
        Returns:
            bool: True if expiry is today
        """
        try:
            expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            return expiry == date.today()
        except Exception as e:
            logger.error(f"Error checking if expiry is today: {e}")
            return False
    
    @staticmethod
    def get_expiry_info(expiry_date: str) -> Dict[str, Any]:
        """
        Get comprehensive information about an expiry date.
        
        Args:
            expiry_date (str): Expiry date in YYYY-MM-DD format
        
        Returns:
            Dict[str, Any]: Expiry information
        """
        try:
            expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            today = date.today()
            days_to_expiry = (expiry - today).days
            
            return {
                'expiry_date': expiry_date,
                'days_to_expiry': days_to_expiry,
                'is_today': days_to_expiry == 0,
                'is_past': days_to_expiry < 0,
                'is_future': days_to_expiry > 0,
                'weekday': expiry.strftime('%A'),
                'is_weekend': expiry.weekday() >= 5,
                'is_holiday': expiry in Utils.MARKET_HOLIDAYS
            }
        except Exception as e:
            logger.error(f"Error getting expiry info: {e}")
            return {}


# Example usage and testing
if __name__ == "__main__":
    print("Testing Utils class...")
    
    # Test weekly expiry calculation
    print("\n=== Weekly Expiry Tests ===")
    expiry = Utils.get_next_weekly_expiry()
    print(f"Next 4 weekly expiries: {expiry}")

    # Test Tuesday expiry calculation
    print("\n=== Tuesday Expiry Tests ===")
    for i in range(5):
        expiry = Utils.get_next_tuesday_expiry(i)
        print(f"Next {i} weeks (Tuesday): {expiry}")
    
    # Test monthly expiry
    print("\n=== Monthly Expiry Tests ===")
    current_date = date.today()
    for i in range(3):
        target_date = current_date + timedelta(days=30 * i)
        expiry = Utils.get_monthly_expiry(target_date.year, target_date.month)
        print(f"Monthly expiry {target_date.year}-{target_date.month:02d}: {expiry}")
    
    # Test expiry series
    print("\n=== Expiry Series Tests ===")
    weekly_series = Utils.get_expiry_series("weekly", 4)
    print(f"Weekly series: {weekly_series}")
    
    tuesday_series = Utils.get_expiry_series("tuesday", 4)
    print(f"Tuesday series: {tuesday_series}")
    
    # Test weekend check
    print("\n=== Weekend Check Tests ===")
    print(f"Is today a weekend: {Utils.isWeekend()}")
    
    # Test specific dates
    from datetime import datetime
    saturday = datetime(2024, 1, 6)  # Saturday
    sunday = datetime(2024, 1, 7)    # Sunday
    monday = datetime(2024, 1, 8)    # Monday
    
    print(f"Is Saturday a weekend: {Utils.isWeekend(saturday)}")
    print(f"Is Sunday a weekend: {Utils.isWeekend(sunday)}")
    print(f"Is Monday a weekend: {Utils.isWeekend(monday)}")
    
    # Test previous Friday
    print("\n=== Previous Friday Tests ===")
    print(f"Previous Friday from today: {Utils.getPreviousFriday().strftime('%Y-%m-%d %A')}")
    
    # Test specific dates
    test_dates = [
        datetime(2024, 1, 8),   # Monday
        datetime(2024, 1, 9),   # Tuesday
        datetime(2024, 1, 10),  # Wednesday
        datetime(2024, 1, 11),  # Thursday
        datetime(2024, 1, 12),  # Friday
        datetime(2024, 1, 13),  # Saturday
        datetime(2024, 1, 14),  # Sunday
    ]
    
    for test_date in test_dates:
        prev_friday = Utils.getPreviousFriday(test_date)
        print(f"Previous Friday from {test_date.strftime('%Y-%m-%d %A')}: {prev_friday.strftime('%Y-%m-%d %A')}")
    
    # Test market hours
    print("\n=== Market Hours Tests ===")
    print(f"Market open now: {Utils.is_market_open()}")
    print(f"Next market open: {Utils.get_next_market_open()}")
    
    # Test strike price formatting
    print("\n=== Strike Price Tests ===")
    price = 24567.89
    formatted = Utils.format_strike_price(price)
    print(f"Price {price} -> Strike {formatted}")
    
    strikes = Utils.get_nearest_strikes(price, 5)
    print(f"Nearest strikes: {strikes}")
    
    # Test expiry info
    print("\n=== Expiry Info Tests ===")
    next_expiry = Utils.get_next_weekly_expiry(0)
    info = Utils.get_expiry_info(next_expiry)
    print(f"Expiry info for {next_expiry}: {info}")
    
    print("\n✅ All tests completed successfully!")
