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


# ============================================================================
# Rate Limiting Configuration
# ============================================================================

class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    """Session class with caching and rate limiting capabilities."""
    pass


# Rate limit configuration based on Yahoo Finance API limits
# Reference: https://help.yahooinc.com/dsp-api/docs/rate-limits
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
    - Task-based stock data fetching for parallel processing
    - Additional ticker information retrieval
    - Watchlist management
    - Data fetching from multiple sources
    
    Attributes:
        _tickersInfoDict (dict): Cache for storing ticker information
    """
    
    _tickersInfoDict = {}
    
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
        Fetch stock price data from external sources.
        
        This is the main data fetching method that retrieves historical
        price data for one or more stocks.
        
        Args:
            stockCode: Single stock symbol or list of symbols
            period: Data period (e.g., "1d", "5d", "1mo", "1y")
            duration: Candle duration/interval (e.g., "1m", "5m", "1d")
            proxyServer: Optional proxy server URL
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
            
        Note:
            The actual yfinance-based fetching code is currently commented out.
            This method returns None until the data source is re-enabled.
        """
        # Note: yfinance integration is currently disabled
        # The commented code below shows the intended implementation
        data = None
        
        # Display progress if requested
        if printCounter and type(screenCounter) != int:
            self._printFetchProgress(stockCode, screenResultsCounter, screenCounter, totalSymbols)
        
        # Handle empty data case
        if (data is None or len(data) == 0) and printCounter:
            self._printFetchError()
            raise StockDataEmptyException
            
        if printCounter:
            self._printFetchSuccess()
            
        return data
    
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
            proxyServer: Optional proxy server URL
            
        Returns:
            pandas.DataFrame or None: Nifty 50 daily data
            
        Note:
            Currently returns None as yfinance integration is disabled.
        """
        return None
        # Disabled yfinance code:
        # data = yf.download(
        #     tickers="^NSEI",
        #     period="5d",
        #     interval="1d",
        #     proxy=proxyServer,
        #     progress=False,
        #     timeout=self.configManager.longTimeout,
        # )
        # return data
    
    def fetchFiveEmaData(self, proxyServer=None):
        """
        Fetch data required for the Five EMA strategy.
        
        This method fetches both Nifty 50 and Bank Nifty data at 
        different intervals for EMA-based analysis.
        
        Args:
            proxyServer: Optional proxy server URL
            
        Returns:
            tuple: (nifty_buy, banknifty_buy, nifty_sell, banknifty_sell)
            
        Note:
            Currently returns None as yfinance integration is disabled.
        """
        return None
        # Disabled yfinance code would fetch:
        # - Nifty/BankNifty sell signals (5m interval)
        # - Nifty/BankNifty buy signals (15m interval)
    
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
