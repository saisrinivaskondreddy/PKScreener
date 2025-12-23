"""
    The MIT License (MIT)

    Copyright (c) 2023 pkjmesra

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

"""
import os
import sys
import warnings
import logging
from time import sleep

warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("ignore", FutureWarning)

import pandas as pd
from PKDevTools.classes.Utils import USER_AGENTS
import random
from concurrent.futures import ThreadPoolExecutor

from PKDevTools.classes.PKDateUtilities import PKDateUtilities
from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.Fetcher import StockDataEmptyException
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.SuppressOutput import SuppressOutput
from PKNSETools.PKNSEStockDataFetcher import nseStockDataFetcher
from pkscreener.classes.PKTask import PKTask
from PKDevTools.classes.OutputControls import OutputControls
from PKDevTools.classes import Archiver

from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter

# Import high-performance data provider (replaces Yahoo Finance)
try:
    from PKDevTools.classes.PKDataProvider import get_data_provider, PKDataProvider
    _HP_DATA_AVAILABLE = True
except ImportError:
    _HP_DATA_AVAILABLE = False

# Keep yfinance as optional fallback (deprecated)
try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False


# ============================================================================
# Rate Limiting Configuration (for fallback sources)
# ============================================================================

class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    """Session class with caching and rate limiting capabilities."""
    pass


# Rate limit configuration for fallback data sources
# Note: Primary data source (PKBrokers candle store) has no rate limits
TRY_FACTOR = 1
yf_limiter = Limiter(
    RequestRate(60 * TRY_FACTOR, Duration.MINUTE),    # Max 60 requests per minute
    RequestRate(360 * TRY_FACTOR, Duration.HOUR),     # Max 360 requests per hour
    RequestRate(8000 * TRY_FACTOR, Duration.DAY)      # Max 8000 requests per day
)


# ============================================================================
# Stock Data Fetcher Class
# ============================================================================

class screenerStockDataFetcher(nseStockDataFetcher):
    """
    Enhanced stock data fetcher with additional functionality for the PKScreener.
    
    This class extends nseStockDataFetcher to provide:
    - High-performance data access via PKBrokers candle store
    - Task-based stock data fetching for parallel processing
    - Additional ticker information retrieval
    - Watchlist management
    - Data fetching from multiple sources (real-time, pickle, remote)
    
    Data Source Priority:
        1. In-memory candle store (PKBrokers) - Real-time during market hours
        2. Local pickle files - Cached historical data
        3. Remote GitHub pickle files - Fallback for historical data
    
    Attributes:
        _tickersInfoDict (dict): Cache for storing ticker information
        _hp_provider: High-performance data provider instance
    """
    
    _tickersInfoDict = {}
    
    def __init__(self, configManager=None):
        """Initialize the screener stock data fetcher."""
        super().__init__(configManager)
        self._hp_provider = None
        if _HP_DATA_AVAILABLE:
            try:
                self._hp_provider = get_data_provider()
            except Exception:
                pass
    
    # ========================================================================
    # Task-Based Data Fetching
    # ========================================================================
    
    def fetchStockDataWithArgs(self, *args):
        """
        Fetch stock data using either a PKTask object or individual arguments.
        
        This method supports two calling conventions:
        1. With a PKTask object containing all necessary parameters
        2. With individual positional arguments
        
        Args:
            *args: Either (PKTask,) or (stockCode, period, duration, exchangeSuffix)
            
        Returns:
            The fetched stock data (typically a DataFrame)
        """
        task = None
        
        # Parse arguments - supports both PKTask and direct arguments
        if isinstance(args[0], PKTask):
            task = args[0]
            stockCode, period, duration, exchangeSuffix = task.long_running_fn_args
        else:
            stockCode, period, duration, exchangeSuffix = args[0], args[1], args[2], args[3]
        
        # Fetch the data
        result = self.fetchStockData(
            stockCode, period, duration, None, 0, 0, 0,
            exchangeSuffix=exchangeSuffix,
            printCounter=False
        )
        
        # Update task progress if this is a task-based call
        if task is not None:
            self._updateTaskProgress(task, result)
            
        return result
    
    def _updateTaskProgress(self, task, result):
        """
        Update task progress tracking dictionaries.
        
        Args:
            task: The PKTask object to update
            result: The result to store in the task
        """
        if task.taskId >= 0:
            task.progressStatusDict[task.taskId] = {'progress': 0, 'total': 1}
            task.resultsDict[task.taskId] = result
            task.progressStatusDict[task.taskId] = {'progress': 1, 'total': 1}
        task.result = result
    
    # ========================================================================
    # Ticker Information Methods
    # ========================================================================
    
    def get_stats(self, ticker):
        """
        Fetch and cache basic statistics for a single ticker.
        
        Note: Currently returns placeholder data as yfinance integration 
        is commented out.
        
        Args:
            ticker: The ticker symbol to fetch stats for
        """
        info = None  # Placeholder: yf.Tickers(ticker).tickers[ticker].fast_info
        screenerStockDataFetcher._tickersInfoDict[ticker] = {
            "marketCap": info.market_cap if info is not None else 0
        }
    
    def fetchAdditionalTickerInfo(self, ticker_list, exchangeSuffix=".NS"):
        """
        Fetch additional information for multiple tickers in parallel.
        
        Args:
            ticker_list: List of ticker symbols
            exchangeSuffix: Exchange suffix to append (default: ".NS" for NSE)
            
        Returns:
            dict: Dictionary mapping tickers to their info
            
        Raises:
            TypeError: If ticker_list is not a list
        """
        if not isinstance(ticker_list, list):
            raise TypeError("ticker_list must be a list")
        
        # Append exchange suffix to tickers if needed
        if len(exchangeSuffix) > 0:
            ticker_list = [
                (f"{x}{exchangeSuffix}" if not x.endswith(exchangeSuffix) else x)
                for x in ticker_list
            ]
        
        # Fetch stats in parallel
        screenerStockDataFetcher._tickersInfoDict = {}
        with ThreadPoolExecutor() as executor:
            executor.map(self.get_stats, ticker_list)
            
        return screenerStockDataFetcher._tickersInfoDict
    
    # ========================================================================
    # Core Data Fetching Methods
    # ========================================================================
    
    def fetchStockData(
        self,
        stockCode,
        period,
        duration,
        proxyServer=None,
        screenResultsCounter=0,
        screenCounter=0,
        totalSymbols=0,
        printCounter=False,
        start=None,
        end=None,
        exchangeSuffix=".NS",
        attempt=0
    ):
        """
        Fetch stock price data using high-performance data provider.
        
        This is the main data fetching method that retrieves historical
        price data for one or more stocks. Uses the following priority:
        1. In-memory candle store (real-time, during market hours)
        2. Local pickle files
        3. Remote GitHub pickle files
        
        Args:
            stockCode: Single stock symbol or list of symbols
            period: Data period (e.g., "1d", "5d", "1mo", "1y")
            duration: Candle duration/interval (e.g., "1m", "5m", "1d")
            proxyServer: Optional proxy server URL (deprecated, unused)
            screenResultsCounter: Counter for screening results (for display)
            screenCounter: Current screen position counter
            totalSymbols: Total number of symbols being processed
            printCounter: Whether to print progress to console
            start: Optional start date for data range
            end: Optional end date for data range
            exchangeSuffix: Exchange suffix (default: ".NS" for NSE)
            attempt: Current retry attempt number
            
        Returns:
            pandas.DataFrame or None: The fetched stock data
            
        Raises:
            StockDataEmptyException: If no data is fetched and printCounter is True
        """
        data = None
        
        # Display progress if requested
        if printCounter and type(screenCounter) != int:
            self._printFetchProgress(stockCode, screenResultsCounter, screenCounter, totalSymbols)
        
        # Normalize symbol
        symbol = stockCode.replace(exchangeSuffix, "").upper() if exchangeSuffix else stockCode.upper()
        
        # Map period to count
        count = self._period_to_count(period, duration)
        
        # Map interval format
        normalized_interval = self._normalize_interval(duration)
        
        # Try high-performance data provider first
        if self._hp_provider is not None:
            try:
                data = self._hp_provider.get_stock_data(
                    symbol,
                    interval=normalized_interval,
                    count=count,
                    start=start,
                    end=end,
                )
            except Exception as e:
                default_logger().debug(f"HP provider failed for {symbol}: {e}")
        
        # If HP provider didn't return data, try parent class method
        if data is None or (hasattr(data, 'empty') and data.empty):
            try:
                data = super().fetchStockData(
                    stockCode,
                    period=period,
                    interval=duration,
                    start=start,
                    end=end,
                    exchangeSuffix=exchangeSuffix,
                )
            except Exception as e:
                default_logger().debug(f"Parent fetchStockData failed for {symbol}: {e}")
        
        # Handle empty data case
        if (data is None or (hasattr(data, '__len__') and len(data) == 0)) and printCounter:
            self._printFetchError()
            raise StockDataEmptyException
            
        if printCounter and data is not None:
            self._printFetchSuccess()
            
        return data
    
    def _period_to_count(self, period: str, interval: str) -> int:
        """Convert period string to candle count."""
        period_days = {
            "1d": 1,
            "5d": 5,
            "1wk": 7,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
            "10y": 3650,
            "max": 5000,
        }
        
        interval_minutes = {
            "1m": 1,
            "2m": 2,
            "3m": 3,
            "4m": 4,
            "5m": 5,
            "10m": 10,
            "15m": 15,
            "30m": 30,
            "60m": 60,
            "1h": 60,
            "1d": 1440,
            "day": 1440,
        }
        
        days = period_days.get(period, 365)
        interval_mins = interval_minutes.get(interval, 1440)
        
        if interval_mins >= 1440:
            return days
        else:
            # Intraday: market hours are ~6.25 hours = 375 minutes
            trading_minutes_per_day = 375
            return min(int((days * trading_minutes_per_day) / interval_mins), 5000)
    
    def _normalize_interval(self, interval: str) -> str:
        """Normalize interval string to standard format."""
        interval_map = {
            "1m": "1m",
            "2m": "2m",
            "3m": "3m",
            "4m": "4m",
            "5m": "5m",
            "10m": "10m",
            "15m": "15m",
            "30m": "30m",
            "60m": "60m",
            "1h": "60m",
            "1d": "day",
            "day": "day",
            "1wk": "day",
            "1mo": "day",
        }
        return interval_map.get(interval, "day")
    
    def getLatestPrice(self, symbol: str, exchangeSuffix: str = ".NS") -> float:
        """Get the latest price for a stock."""
        clean_symbol = symbol.replace(exchangeSuffix, "").upper()
        
        if self._hp_provider is not None:
            try:
                price = self._hp_provider.get_latest_price(clean_symbol)
                if price is not None:
                    return price
            except Exception:
                pass
        return 0.0
    
    def getRealtimeOHLCV(self, symbol: str, exchangeSuffix: str = ".NS") -> dict:
        """Get real-time OHLCV for a stock."""
        clean_symbol = symbol.replace(exchangeSuffix, "").upper()
        
        if self._hp_provider is not None:
            try:
                ohlcv = self._hp_provider.get_realtime_ohlcv(clean_symbol)
                if ohlcv is not None:
                    return ohlcv
            except Exception:
                pass
        return {}
    
    def isRealtimeDataAvailable(self) -> bool:
        """Check if real-time data is available."""
        if self._hp_provider is not None:
            try:
                return self._hp_provider.is_realtime_available()
            except Exception:
                pass
        return False
    
    def getAllRealtimeData(self) -> dict:
        """Get real-time OHLCV for all available stocks."""
        if self._hp_provider is not None:
            try:
                return self._hp_provider.get_all_realtime_data()
            except Exception:
                pass
        return {}
    
    def _printFetchProgress(self, stockCode, screenResultsCounter, screenCounter, totalSymbols):
        """Print the current fetch progress to console."""
        sys.stdout.write("\r\033[K")
        try:
            OutputControls().printOutput(
                colorText.GREEN +
                "[%d%%] Screened %d, Found %d. Fetching data & Analyzing %s..." % (
                    int((screenCounter.value / totalSymbols) * 100),
                    screenCounter.value,
                    screenResultsCounter.value,
                    stockCode,
                ) +
                colorText.END,
                end="",
            )
        except ZeroDivisionError as e:
            default_logger().debug(e, exc_info=True)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            default_logger().debug(e, exc_info=True)
    
    def _printFetchError(self):
        """Print fetch error message to console."""
        OutputControls().printOutput(
            colorText.FAIL + "=> Failed to fetch!" + colorText.END,
            end="\r",
            flush=True,
        )
    
    def _printFetchSuccess(self):
        """Print fetch success message to console."""
        OutputControls().printOutput(
            colorText.GREEN + "=> Done!" + colorText.END,
            end="\r",
            flush=True,
        )
    
    # ========================================================================
    # Index Data Methods
    # ========================================================================
    
    def fetchLatestNiftyDaily(self, proxyServer=None):
        """
        Fetch daily Nifty 50 index data.
        
        Args:
            proxyServer: Optional proxy server URL (deprecated, unused)
            
        Returns:
            pandas.DataFrame or None: Nifty 50 daily data
        """
        # Try high-performance provider first
        if self._hp_provider is not None:
            try:
                # NIFTY 50 is typically tracked as "NIFTY" or index
                data = self._hp_provider.get_stock_data("NIFTY 50", interval="day", count=5)
                if data is not None and not data.empty:
                    return data
            except Exception as e:
                default_logger().debug(f"HP provider failed for NIFTY: {e}")
        
        return None
    
    def fetchFiveEmaData(self, proxyServer=None):
        """
        Fetch data required for the Five EMA strategy.
        
        This method fetches both Nifty 50 and Bank Nifty data at 
        different intervals for EMA-based analysis.
        
        Args:
            proxyServer: Optional proxy server URL (deprecated, unused)
            
        Returns:
            tuple: (nifty_buy, banknifty_buy, nifty_sell, banknifty_sell) or None
        """
        if self._hp_provider is None:
            return None
        
        try:
            # Fetch Nifty data for buy signals (15m interval)
            nifty_buy = self._hp_provider.get_stock_data("NIFTY 50", interval="15m", count=50)
            
            # Fetch Bank Nifty data for buy signals (15m interval)
            banknifty_buy = self._hp_provider.get_stock_data("NIFTY BANK", interval="15m", count=50)
            
            # Fetch Nifty data for sell signals (5m interval)
            nifty_sell = self._hp_provider.get_stock_data("NIFTY 50", interval="5m", count=50)
            
            # Fetch Bank Nifty data for sell signals (5m interval)
            banknifty_sell = self._hp_provider.get_stock_data("NIFTY BANK", interval="5m", count=50)
            
            # Check if we got valid data for all
            all_valid = all([
                nifty_buy is not None and not nifty_buy.empty,
                banknifty_buy is not None and not banknifty_buy.empty,
                nifty_sell is not None and not nifty_sell.empty,
                banknifty_sell is not None and not banknifty_sell.empty,
            ])
            
            if all_valid:
                return (nifty_buy, banknifty_buy, nifty_sell, banknifty_sell)
            
        except Exception as e:
            default_logger().debug(f"Error fetching Five EMA data: {e}")
        
        return None
    
    # ========================================================================
    # Watchlist Methods
    # ========================================================================
    
    def fetchWatchlist(self):
        """
        Load stock codes from the user's watchlist.xlsx file.
        
        The watchlist file should have a column named "Stock Code" containing
        the stock symbols to watch.
        
        Returns:
            list or None: List of stock codes, or None if file not found/invalid
            
        Side Effects:
            - Creates a template file (watchlist_template.xlsx) if the watchlist
              is not found or has invalid format
        """
        createTemplate = False
        data = pd.DataFrame()
        
        # Try to load the watchlist file
        try:
            data = pd.read_excel("watchlist.xlsx")
        except FileNotFoundError as e:
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(
                colorText.FAIL +
                f"  [+] watchlist.xlsx not found in {os.getcwd()}" +
                colorText.END
            )
            createTemplate = True
        
        # Try to extract stock codes
        try:
            if not createTemplate:
                data = data["Stock Code"].values.tolist()
        except KeyError as e:
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(
                colorText.FAIL +
                '  [+] Bad Watchlist Format: First Column (A1) should have '
                'Header named "Stock Code"' +
                colorText.END
            )
            createTemplate = True
        
        # Create template if needed
        if createTemplate:
            self._createWatchlistTemplate()
            return None
            
        return data
    
    def _createWatchlistTemplate(self):
        """Create a sample watchlist template file for user reference."""
        sample = {"Stock Code": ["SBIN", "INFY", "TATAMOTORS", "ITC"]}
        sample_data = pd.DataFrame(sample, columns=["Stock Code"])
        sample_data.to_excel("watchlist_template.xlsx", index=False, header=True)
        OutputControls().printOutput(
            colorText.BLUE +
            f"  [+] watchlist_template.xlsx created in {os.getcwd()} as a reference template." +
            colorText.END
        )
