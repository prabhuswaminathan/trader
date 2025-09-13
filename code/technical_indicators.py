#!/usr/bin/env python3
"""
Technical Indicators module for calculating various technical analysis indicators.
"""

import numpy as np
import pandas as pd
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("TechnicalIndicators")

class TechnicalIndicators:
    """Class for calculating technical indicators"""
    
    @staticmethod
    def moving_average(data: List[float], period: int) -> List[Optional[float]]:
        """
        Calculate Simple Moving Average (SMA)
        
        Args:
            data: List of price values
            period: Period for moving average
            
        Returns:
            List of moving average values (None for insufficient data)
        """
        try:
            if len(data) < period:
                return [None] * len(data)
            
            ma_values = []
            for i in range(len(data)):
                if i < period - 1:
                    ma_values.append(None)
                else:
                    ma_values.append(sum(data[i - period + 1:i + 1]) / period)
            
            return ma_values
            
        except Exception as e:
            logger.error(f"Error calculating moving average: {e}")
            return [None] * len(data)
    
    @staticmethod
    def exponential_moving_average(data: List[float], period: int) -> List[Optional[float]]:
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            data: List of price values
            period: Period for EMA
            
        Returns:
            List of EMA values (None for insufficient data)
        """
        try:
            if len(data) < period:
                return [None] * len(data)
            
            ema_values = [None] * len(data)
            multiplier = 2 / (period + 1)
            
            # First EMA value is SMA
            sma = sum(data[:period]) / period
            ema_values[period - 1] = sma
            
            # Calculate subsequent EMA values
            for i in range(period, len(data)):
                ema_values[i] = (data[i] * multiplier) + (ema_values[i - 1] * (1 - multiplier))
            
            return ema_values
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return [None] * len(data)
    
    @staticmethod
    def rsi(data: List[float], period: int = 14) -> List[Optional[float]]:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            data: List of price values
            period: Period for RSI calculation (default 14)
            
        Returns:
            List of RSI values (None for insufficient data)
        """
        try:
            if len(data) < period + 1:
                return [None] * len(data)
            
            rsi_values = [None] * len(data)
            
            # Calculate price changes
            price_changes = []
            for i in range(1, len(data)):
                price_changes.append(data[i] - data[i - 1])
            
            # Calculate gains and losses
            gains = [max(change, 0) for change in price_changes]
            losses = [abs(min(change, 0)) for change in price_changes]
            
            # Calculate initial average gain and loss
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            # Calculate RSI for first valid period
            if avg_loss == 0:
                rsi_values[period] = 100
            else:
                rs = avg_gain / avg_loss
                rsi_values[period] = 100 - (100 / (1 + rs))
            
            # Calculate subsequent RSI values using Wilder's smoothing
            for i in range(period + 1, len(data)):
                avg_gain = ((avg_gain * (period - 1)) + gains[i - 1]) / period
                avg_loss = ((avg_loss * (period - 1)) + losses[i - 1]) / period
                
                if avg_loss == 0:
                    rsi_values[i] = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi_values[i] = 100 - (100 / (1 + rs))
            
            return rsi_values
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return [None] * len(data)
    
    @staticmethod
    def macd(data: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, List[Optional[float]]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            data: List of price values
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
            
        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' lists
        """
        try:
            if len(data) < slow_period:
                return {
                    'macd': [None] * len(data),
                    'signal': [None] * len(data),
                    'histogram': [None] * len(data)
                }
            
            # Calculate EMAs
            fast_ema = TechnicalIndicators.exponential_moving_average(data, fast_period)
            slow_ema = TechnicalIndicators.exponential_moving_average(data, slow_period)
            
            # Calculate MACD line
            macd_line = []
            for i in range(len(data)):
                if fast_ema[i] is not None and slow_ema[i] is not None:
                    macd_line.append(fast_ema[i] - slow_ema[i])
                else:
                    macd_line.append(None)
            
            # Calculate signal line (EMA of MACD)
            signal_line = TechnicalIndicators.exponential_moving_average(
                [x for x in macd_line if x is not None], signal_period
            )
            
            # Pad signal line with None values
            signal_padded = [None] * (len(data) - len(signal_line)) + signal_line
            
            # Calculate histogram
            histogram = []
            for i in range(len(data)):
                if macd_line[i] is not None and signal_padded[i] is not None:
                    histogram.append(macd_line[i] - signal_padded[i])
                else:
                    histogram.append(None)
            
            return {
                'macd': macd_line,
                'signal': signal_padded,
                'histogram': histogram
            }
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {
                'macd': [None] * len(data),
                'signal': [None] * len(data),
                'histogram': [None] * len(data)
            }
    
    @staticmethod
    def super_trend(high: List[float], low: List[float], close: List[float], period: int = 10, multiplier: float = 3.0) -> Dict[str, List[Optional[float]]]:
        """
        Calculate Super Trend indicator
        
        Args:
            high: List of high prices
            low: List of low prices
            close: List of close prices
            period: Period for ATR calculation (default 10)
            multiplier: Multiplier for Super Trend (default 3.0)
            
        Returns:
            Dictionary with 'super_trend', 'direction', and 'atr' lists
        """
        try:
            if len(high) != len(low) or len(high) != len(close) or len(high) < period + 1:
                return {
                    'super_trend': [None] * len(high),
                    'direction': [None] * len(high),
                    'atr': [None] * len(high)
                }
            
            # Calculate True Range (TR)
            tr_values = []
            for i in range(len(high)):
                if i == 0:
                    tr_values.append(high[i] - low[i])
                else:
                    tr1 = high[i] - low[i]
                    tr2 = abs(high[i] - close[i - 1])
                    tr3 = abs(low[i] - close[i - 1])
                    tr_values.append(max(tr1, tr2, tr3))
            
            # Calculate ATR (Average True Range)
            atr_values = [None] * len(high)
            atr_values[period - 1] = sum(tr_values[:period]) / period
            
            for i in range(period, len(high)):
                atr_values[i] = ((atr_values[i - 1] * (period - 1)) + tr_values[i]) / period
            
            # Calculate Super Trend
            super_trend_values = [None] * len(high)
            direction_values = [None] * len(high)
            
            for i in range(period - 1, len(high)):
                if atr_values[i] is None:
                    continue
                
                hl2 = (high[i] + low[i]) / 2
                upper_band = hl2 + (multiplier * atr_values[i])
                lower_band = hl2 - (multiplier * atr_values[i])
                
                if i == period - 1:
                    # First value
                    super_trend_values[i] = lower_band
                    direction_values[i] = 1  # 1 for uptrend, -1 for downtrend
                else:
                    # Previous values
                    prev_super_trend = super_trend_values[i - 1]
                    prev_direction = direction_values[i - 1]
                    
                    if prev_direction == 1:
                        # Previous was uptrend
                        if lower_band > prev_super_trend:
                            super_trend_values[i] = lower_band
                            direction_values[i] = 1
                        else:
                            super_trend_values[i] = prev_super_trend
                            direction_values[i] = 1
                    else:
                        # Previous was downtrend
                        if upper_band < prev_super_trend:
                            super_trend_values[i] = upper_band
                            direction_values[i] = -1
                        else:
                            super_trend_values[i] = prev_super_trend
                            direction_values[i] = -1
                    
                    # Check for trend change
                    if (prev_direction == 1 and close[i] < super_trend_values[i]) or \
                       (prev_direction == -1 and close[i] > super_trend_values[i]):
                        direction_values[i] = -prev_direction
                        if direction_values[i] == 1:
                            super_trend_values[i] = lower_band
                        else:
                            super_trend_values[i] = upper_band
            
            return {
                'super_trend': super_trend_values,
                'direction': direction_values,
                'atr': atr_values
            }
            
        except Exception as e:
            logger.error(f"Error calculating Super Trend: {e}")
            return {
                'super_trend': [None] * len(high),
                'direction': [None] * len(high),
                'atr': [None] * len(high)
            }
    
    @staticmethod
    def calculate_all_indicators(ohlc_data: List[Dict]) -> Dict[str, List[Optional[float]]]:
        """
        Calculate all technical indicators for given OHLC data
        
        Args:
            ohlc_data: List of OHLC dictionaries with 'open', 'high', 'low', 'close' keys
                      Data should be sorted with most recent first (index 0)
            
        Returns:
            Dictionary with all calculated indicators
        """
        try:
            if not ohlc_data:
                return {}
            
            # Reverse the data to get chronological order (oldest first) for calculations
            # Historical data comes with most recent first, but indicators need oldest first
            reversed_data = list(reversed(ohlc_data))
            
            # Extract price data in chronological order (oldest first)
            close_prices = [candle['close'] for candle in reversed_data]
            high_prices = [candle['high'] for candle in reversed_data]
            low_prices = [candle['low'] for candle in reversed_data]
            
            # Calculate indicators on chronologically ordered data
            indicators = {}
            
            # Moving Averages
            indicators['ma_20'] = TechnicalIndicators.moving_average(close_prices, 20)
            indicators['ma_50'] = TechnicalIndicators.moving_average(close_prices, 50)
            indicators['ma_100'] = TechnicalIndicators.moving_average(close_prices, 100)
            indicators['ma_200'] = TechnicalIndicators.moving_average(close_prices, 200)
            
            # RSI
            indicators['rsi'] = TechnicalIndicators.rsi(close_prices, 14)
            
            # MACD
            macd_data = TechnicalIndicators.macd(close_prices)
            indicators['macd'] = macd_data['macd']
            indicators['macd_signal'] = macd_data['signal']
            indicators['macd_histogram'] = macd_data['histogram']
            
            # Super Trend
            super_trend_data = TechnicalIndicators.super_trend(high_prices, low_prices, close_prices)
            indicators['super_trend'] = super_trend_data['super_trend']
            indicators['super_trend_direction'] = super_trend_data['direction']
            indicators['atr'] = super_trend_data['atr']
            
            # Reverse all indicators back to match original data order (most recent first)
            for key in indicators:
                if isinstance(indicators[key], list):
                    indicators[key] = list(reversed(indicators[key]))
            
            logger.info(f"Calculated technical indicators for {len(ohlc_data)} data points")
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating all indicators: {e}")
            return {}
