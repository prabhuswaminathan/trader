import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class NiftyAnalyzer:
    def __init__(self, csv_file_path):
        """
        Initialize the Nifty Analyzer with the CSV file path
        """
        self.csv_file_path = csv_file_path
        self.df = None
        self.trades = None
        self.vix_df = None
        
    def load_data(self):
        """
        Load the NIFTY data file into a pandas DataFrame
        """
        try:
            self.df = pd.read_csv(self.csv_file_path)
            print(f"Data loaded successfully. Shape: {self.df.shape}")
            print(f"Columns: {self.df.columns.tolist()}")
            
            # Clean column names (remove extra spaces)
            self.df.columns = self.df.columns.str.strip()
            
            # Check if we have the expected columns
            if 'Date' not in self.df.columns:
                print("Error: 'Date' column not found in the data")
                return False
            
            # Convert Date to datetime to check range
            self.df['Date'] = pd.to_datetime(self.df['Date'], format='%d-%b-%Y', errors='coerce')
            valid_dates = self.df['Date'].dropna()
            if len(valid_dates) > 0:
                print(f"Date range: {valid_dates.min()} to {valid_dates.max()}")
            else:
                print("Warning: No valid dates found")
            
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def preprocess_data(self, year_filter=None):
        """
        Preprocess the data - convert dates, handle missing values
        """
        if self.df is None:
            print("Please load data first")
            return False
        
        # Convert Date column to datetime (already done in load_data, but ensure it's done)
        self.df['Date'] = pd.to_datetime(self.df['Date'], format='%d-%b-%Y', errors='coerce')
        
        # Remove rows with invalid dates
        self.df = self.df.dropna(subset=['Date'])
        
        # Clean column names (remove extra spaces)
        self.df.columns = self.df.columns.str.strip()
        
        # The 2024 data format has: Date, Open, High, Low, Close, Shares Traded, Turnover
        # We already have the correct columns: Date, Open, High, Low, Close
        
        # Clean numeric columns (remove commas and convert to float)
        numeric_columns = ['Open', 'High', 'Low', 'Close']
        for col in numeric_columns:
            if col in self.df.columns:
                # Convert to float (no commas in this data)
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Filter by year if specified
        if year_filter is not None:
            self.df = self.df[self.df['Date'].dt.year == year_filter].copy()
            print(f"Filtered data for year {year_filter}. Shape: {self.df.shape}")
            if len(self.df) == 0:
                print(f"No data found for year {year_filter}")
                return False
        
        # Sort by date
        self.df = self.df.sort_values('Date').reset_index(drop=True)
        
        # Add day of week
        self.df['DayOfWeek'] = self.df['Date'].dt.day_name()
        self.df['Weekday'] = self.df['Date'].dt.weekday  # 0=Monday, 6=Sunday
        
        # Handle missing values in OHLC data
        # For Open, High, Low, Close - forward fill then backward fill
        ohlc_columns = ['Open', 'High', 'Low', 'Close']
        for col in ohlc_columns:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna(method='ffill').fillna(method='bfill')
        
        print("Data preprocessing completed")
        return True
    
    def load_vix_data(self, vix_file_paths):
        """
        Load and combine VIX data from provided CSV file paths
        """
        combined = []
        for path in vix_file_paths:
            try:
                temp = pd.read_csv(path)
                # Clean column names
                temp.columns = temp.columns.str.strip()
                # Parse date like 01-JAN-2024
                temp['Date'] = pd.to_datetime(temp['Date'], format='%d-%b-%Y', errors='coerce')
                # Keep only needed columns
                keep_cols = [c for c in ['Date', 'Open', 'High', 'Low', 'Close', 'Prev. Close', 'Change', '% Change'] if c in temp.columns]
                temp = temp[keep_cols]
                combined.append(temp)
            except Exception as e:
                print(f"Error loading VIX file {path}: {e}")
        if not combined:
            print("No VIX data loaded")
            return False
        self.vix_df = pd.concat(combined, ignore_index=True)
        self.vix_df = self.vix_df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
        # Ensure numeric
        for col in ['Open', 'High', 'Low', 'Close', 'Prev. Close', 'Change']:
            if col in self.vix_df.columns:
                self.vix_df[col] = pd.to_numeric(self.vix_df[col], errors='coerce')
        if '% Change' in self.vix_df.columns:
            # Remove % sign if present
            self.vix_df['% Change'] = (
                self.vix_df['% Change']
                .astype(str)
                .str.replace('%', '', regex=False)
            )
            self.vix_df['% Change'] = pd.to_numeric(self.vix_df['% Change'], errors='coerce')
        print(f"VIX data loaded. Shape: {self.vix_df.shape}")
        if not self.vix_df.empty:
            print(f"VIX Date range: {self.vix_df['Date'].min()} to {self.vix_df['Date'].max()}")
        return True


    

    
    def analyze_performance(self):
        """
        Analyze the market data performance
        """
        if self.df is None or self.df.empty:
            print("No data to analyze")
            return
        
        print("\n" + "="*50)
        print("MARKET DATA ANALYSIS")
        print("="*50)
        
        # Basic statistics
        total_days = len(self.df)
        print(f"Total Trading Days: {total_days}")
        print(f"Date Range: {self.df['Date'].min()} to {self.df['Date'].max()}")
        
        # Price Statistics
        if 'Close' in self.df.columns:
            initial_price = self.df['Close'].iloc[0]
            final_price = self.df['Close'].iloc[-1]
            total_return = ((final_price - initial_price) / initial_price) * 100
            max_price = self.df['Close'].max()
            min_price = self.df['Close'].min()
            
            print(f"\nPrice Statistics:")
            print(f"Initial Price: {initial_price:.2f}")
            print(f"Final Price: {final_price:.2f}")
            print(f"Total Return: {total_return:.2f}%")
            print(f"Maximum Price: {max_price:.2f}")
            print(f"Minimum Price: {min_price:.2f}")
        
        # Daily returns
        if 'Close' in self.df.columns:
            self.df['Daily_Return'] = self.df['Close'].pct_change() * 100
            daily_returns = self.df['Daily_Return'].dropna()
            
            avg_daily_return = daily_returns.mean()
            std_daily_return = daily_returns.std()
            max_daily_return = daily_returns.max()
            min_daily_return = daily_returns.min()
            
            print(f"\nDaily Return Statistics:")
            print(f"Average Daily Return: {avg_daily_return:.2f}%")
            print(f"Standard Deviation: {std_daily_return:.2f}%")
            print(f"Maximum Daily Return: {max_daily_return:.2f}%")
            print(f"Minimum Daily Return: {min_daily_return:.2f}%")
        
        # Calculate weekly returns based on trade periods
        self.calculate_weekly_returns()
        
        return self.df
    
    def calculate_weekly_returns(self):
        """
        Calculate weekly returns based on trade start and end dates
        """
        if self.df is None or self.df.empty:
            print("No data to calculate weekly returns")
            return
        
        # Get all unique weeks (starting from Monday)
        start_date = self.df['Date'].min()
        end_date = self.df['Date'].max()
        
        weekly_returns = []
        current_date = start_date
        
        while current_date <= end_date:
            # Find Monday of the week (trade start)
            monday = current_date - timedelta(days=current_date.weekday())
            
            # Find Thursday of the week (trade end)
            thursday = monday + timedelta(days=3)
            
            # Get Monday opening price (trade start)
            monday_data = self.df[self.df['Date'] == monday]
            if monday_data.empty:
                # If Monday not found, look for the next available day
                monday_data = self.df[self.df['Date'] >= monday].head(1)
            
            # Get Thursday closing price (trade end)
            thursday_data = self.df[self.df['Date'] == thursday]
            if thursday_data.empty:
                # If Thursday not found, look for the previous available day
                thursday_data = self.df[self.df['Date'] <= thursday].tail(1)
            
            if not monday_data.empty and not thursday_data.empty:
                monday_open = monday_data.iloc[0]['Open']
                thursday_close = thursday_data.iloc[0]['Close']
                
                if monday_open > 0:
                    weekly_return = ((thursday_close - monday_open) / monday_open) * 100
                    # Compute VIX standard deviation within the trade window if available
                    vix_std = np.nan
                    vix_start = np.nan
                    nifty_std_from_vix = np.nan
                    if self.vix_df is not None and not self.vix_df.empty:
                        vix_window = self.vix_df[(self.vix_df['Date'] >= monday) & (self.vix_df['Date'] <= thursday)]
                        if not vix_window.empty and 'Close' in vix_window.columns:
                            vix_std = float(vix_window['Close'].std())
                        # Use VIX Close of the previous Friday (before Monday trade start)
                        friday = monday - timedelta(days=3)
                        vix_start_row = self.vix_df[self.vix_df['Date'] == friday].tail(1)
                        if not vix_start_row.empty and 'Close' in vix_start_row.columns:
                            vix_start = float(vix_start_row.iloc[0]['Close'])
                            # Number of nifty trading days in window
                            trade_days = len(self.df[(self.df['Date'] >= monday) & (self.df['Date'] <= thursday)])
                            if trade_days > 0:
                                # Convert annualized VIX (%) to price std over trade window
                                horizon = trade_days / 252.0
                                nifty_std_from_vix = monday_open * (vix_start / 100.0) * np.sqrt(horizon)
                    
                    weekly_returns.append({
                        'Week_Start': monday,
                        'Week_End': thursday,
                        'Start_Price': monday_open,
                        'End_Price': thursday_close,
                        'Weekly_Return': weekly_return,
                        'P&L': thursday_close - monday_open,
                        'VIX_Std': vix_std,
                        'VIX_Start': vix_start,
                        'Nifty_Std_From_VIX': nifty_std_from_vix
                    })
            
            # Move to next week
            current_date += timedelta(days=7)
        
        # Store weekly returns as DataFrame
        self.weekly_returns = pd.DataFrame(weekly_returns)
        
        if len(self.weekly_returns) > 0:
            print(f"\nWeekly Returns Analysis:")
            print(f"Total Weekly Periods: {len(self.weekly_returns)}")
            
            avg_weekly_return = self.weekly_returns['Weekly_Return'].mean()
            std_weekly_return = self.weekly_returns['Weekly_Return'].std()
            max_weekly_return = self.weekly_returns['Weekly_Return'].max()
            min_weekly_return = self.weekly_returns['Weekly_Return'].min()
            
            print(f"Average Weekly Return: {avg_weekly_return:.2f}%")
            print(f"Standard Deviation: {std_weekly_return:.2f}%")
            print(f"Maximum Weekly Return: {max_weekly_return:.2f}%")
            print(f"Minimum Weekly Return: {min_weekly_return:.2f}%")
            
            # Win/Loss statistics
            winning_weeks = len(self.weekly_returns[self.weekly_returns['Weekly_Return'] > 0])
            losing_weeks = len(self.weekly_returns[self.weekly_returns['Weekly_Return'] < 0])
            total_weeks = len(self.weekly_returns)
            
            print(f"Winning Weeks: {winning_weeks} ({winning_weeks/total_weeks*100:.1f}%)")
            print(f"Losing Weeks: {losing_weeks} ({losing_weeks/total_weeks*100:.1f}%)")
        else:
            print("No weekly returns calculated")
    
    def save_results(self, filename='nifty_market_data.csv'):
        """
        Save the market data and weekly returns to CSV files
        """
        if self.df is None or self.df.empty:
            print("No data to save")
            return False
        
        try:
            # Save market data
            self.df.to_csv(filename, index=False)
            print(f"Market data saved to {filename}")
            
            # Save weekly returns if available
            if hasattr(self, 'weekly_returns') and not self.weekly_returns.empty:
                weekly_filename = filename.replace('.csv', '_weekly_returns.csv')
                self.weekly_returns.to_csv(weekly_filename, index=False)
                print(f"Weekly returns saved to {weekly_filename}")
            
            return True
        except Exception as e:
            print(f"Error saving results: {e}")
            return False
    
    def plot_performance(self):
        """
        Plot the market data performance
        """
        if self.df is None or self.df.empty:
            print("No data to plot")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # Plot 1: Price over time
        ax1.plot(self.df['Date'], self.df['Close'])
        ax1.set_title('Nifty Price Over Time')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Price')
        ax1.grid(True)
        
        # Plot 2: Weekly Returns Bar Graph with VIX Std overlay (if available)
        if hasattr(self, 'weekly_returns') and not self.weekly_returns.empty:
            weekly_returns = self.weekly_returns['Weekly_Return'].reset_index(drop=True)
            weeks = range(1, len(weekly_returns) + 1)
            colors = ['green' if x >= 0 else 'red' for x in weekly_returns]
            
            bars = ax2.bar(weeks, weekly_returns, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)
            ax2.set_title('Weekly Returns % (bars) with VIX Std (line)')
            ax2.set_xlabel('Week Number')
            ax2.set_ylabel('Return (%)')
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
            
            # Add value labels on bars
            for bar, value in zip(bars, weekly_returns):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.2),
                        f'{value:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', 
                        fontsize=8, rotation=90)
            
            # Overlay VIX standard deviation on secondary axis if exists
            # Overlay VIX derived Nifty price std at trade start (secondary axis) as bars
            overlay_done = False
            if 'Nifty_Std_From_VIX' in self.weekly_returns.columns:
                derived_std = self.weekly_returns['Nifty_Std_From_VIX'].reset_index(drop=True)
                if derived_std.notna().any():
                    ax2b = ax2.twinx()
                    ax2b.bar(weeks, derived_std, color='purple', alpha=0.35, label='Nifty Std from VIX')
                    ax2b.set_ylabel('Price Std (derived from VIX)')
                    ax2b.legend(loc='upper right')
                    overlay_done = True
            if not overlay_done and 'VIX_Std' in self.weekly_returns.columns:
                vix_std_series = self.weekly_returns['VIX_Std'].reset_index(drop=True)
                if vix_std_series.notna().any():
                    ax2b = ax2.twinx()
                    ax2b.bar(weeks, vix_std_series, color='blue', alpha=0.35, label='VIX Std')
                    ax2b.set_ylabel('VIX Std (Close)')
                    ax2b.legend(loc='upper right')
        else:
            # Fallback to daily returns
            if 'Daily_Return' in self.df.columns:
                ax2.plot(self.df['Date'], self.df['Daily_Return'])
                ax2.set_title('Daily Returns (%)')
                ax2.set_xlabel('Date')
                ax2.set_ylabel('Return (%)')
                ax2.grid(True)
                ax2.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        plt.show()
    

    def plot_bell_curve(self):
        """
        Plot a bell curve showing the distribution of weekly returns
        """
        if not hasattr(self, 'weekly_returns') or self.weekly_returns.empty:
            print("No weekly returns calculated. Run analyze_performance first.")
            return
        
        # Get the weekly returns
        returns = self.weekly_returns['Weekly_Return'].dropna()
        
        if len(returns) == 0:
            print("No valid weekly returns to plot")
            return
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Plot 1: Histogram with normal distribution overlay
        ax1.hist(returns, bins=20, density=True, alpha=0.7, color='skyblue', edgecolor='black', label='Actual Returns')
        
        # Calculate normal distribution parameters
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Generate normal distribution curve
        x = np.linspace(returns.min(), returns.max(), 100)
        normal_curve = (1 / (std_return * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean_return) / std_return) ** 2)
        
        # Plot normal distribution curve
        ax1.plot(x, normal_curve, 'r-', linewidth=2, label=f'Normal Distribution\n(μ={mean_return:.2f}%, σ={std_return:.2f}%)')
        
        ax1.set_xlabel('Return (%)')
        ax1.set_ylabel('Density')
        ax1.set_title('Distribution of Weekly Returns\n(Histogram vs Normal Distribution)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.axvline(mean_return, color='red', linestyle='--', alpha=0.7, label=f'Mean: {mean_return:.2f}%')
        
        # Plot 2: Q-Q plot to check normality
        
        # Calculate theoretical quantiles
        theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, len(returns)))
        sample_quantiles = np.sort(returns)
        
        ax2.scatter(theoretical_quantiles, sample_quantiles, alpha=0.6, color='blue')
        
        # Add reference line (perfect normal distribution)
        min_val = min(theoretical_quantiles.min(), sample_quantiles.min())
        max_val = max(theoretical_quantiles.max(), sample_quantiles.max())
        ax2.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Perfect Normal')
        
        ax2.set_xlabel('Theoretical Quantiles')
        ax2.set_ylabel('Sample Quantiles')
        ax2.set_title('Q-Q Plot: Checking Normality of Returns')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Add statistics text
        stats_text = f'Statistics:\n'
        stats_text += f'Mean: {mean_return:.2f}%\n'
        stats_text += f'Std Dev: {std_return:.2f}%\n'
        stats_text += f'Skewness: {stats.skew(returns):.2f}\n'
        stats_text += f'Kurtosis: {stats.kurtosis(returns):.2f}\n'
        stats_text += f'Shapiro-Wilk p-value: {stats.shapiro(returns)[1]:.4f}'
        
        ax2.text(0.05, 0.95, stats_text, transform=ax2.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        plt.show()
        
        # Print additional statistics
        print("\n" + "="*50)
        print("RETURN DISTRIBUTION ANALYSIS")
        print("="*50)
        print(f"Mean Return: {mean_return:.2f}%")
        print(f"Standard Deviation: {std_return:.2f}%")
        print(f"Skewness: {stats.skew(returns):.2f}")
        print(f"Kurtosis: {stats.kurtosis(returns):.2f}")
        print(f"Shapiro-Wilk Test p-value: {stats.shapiro(returns)[1]:.4f}")
        
        if stats.shapiro(returns)[1] > 0.05:
            print("✓ Returns appear to be normally distributed (p > 0.05)")
        else:
            print("✗ Returns do not appear to be normally distributed (p ≤ 0.05)")
    
    def run_analysis(self, year_filter=None):
        """
        Run the complete analysis
        """
        if year_filter:
            print(f"Starting Nifty OHLC Analysis for {year_filter}...")
        else:
            print("Starting Nifty OHLC Analysis...")
        
        # Load data
        if not self.load_data():
            return False
        
        # Preprocess data
        if not self.preprocess_data(year_filter):
            return False
        
        # Load VIX data (if present)
        self.load_vix_data([
            '/home/prabhu/Desktop/code/market/vix 2024.csv',
            '/home/prabhu/Desktop/code/market/vix 2025.csv',
        ])

        # Merge VIX Close onto main df by Date
        if self.vix_df is not None and not self.vix_df.empty:
            vix_to_merge = self.vix_df[['Date', 'Close']].rename(columns={'Close': 'VIX_Close'})
            self.df = self.df.merge(vix_to_merge, on='Date', how='left')
            # Forward/backward fill VIX if needed within same year data
            self.df['VIX_Close'] = self.df['VIX_Close'].fillna(method='ffill').fillna(method='bfill')

        # Analyze performance
        self.analyze_performance()
        
        # Save results to CSV
        filename = f'nifty_trade_results_{year_filter}.csv' if year_filter else 'nifty_trade_results.csv'
        self.save_results(filename)
        
        # Plot performance
        self.plot_performance()
        
        # Removed bell curve plot per request
        
        return True

def main():
    """
    Main function to run the analysis
    """
    # Initialize analyzer with the 2024 data file
    analyzer = NiftyAnalyzer('/home/prabhu/Desktop/code/market/NIFTY 2024.csv')
    
    # Run analysis for 2024 data
    analyzer.run_analysis()
    
    # Display sample data
    if analyzer.df is not None:
        print("\n" + "="*50)
        print("SAMPLE MARKET DATA (First 10 rows)")
        print("="*50)
        print(analyzer.df.head(10).to_string(index=False))
        
        print("\n" + "="*50)
        print("SAMPLE MARKET DATA (Last 10 rows)")
        print("="*50)
        print(analyzer.df.tail(10).to_string(index=False))
    
    # Display weekly returns data
    if hasattr(analyzer, 'weekly_returns') and not analyzer.weekly_returns.empty:
        print("\n" + "="*50)
        print("SAMPLE WEEKLY RETURNS (First 10 rows)")
        print("="*50)
        print(analyzer.weekly_returns.head(10).to_string(index=False))
        
        print("\n" + "="*50)
        print("SAMPLE WEEKLY RETURNS (Last 10 rows)")
        print("="*50)
        print(analyzer.weekly_returns.tail(10).to_string(index=False))

if __name__ == "__main__":
    main()
