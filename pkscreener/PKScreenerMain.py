#!/usr/bin/python3
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
import random
import warnings
warnings.simplefilter("ignore", UserWarning, append=True)
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import logging
import multiprocessing
import sys
import time
import urllib
import warnings
from datetime import datetime, UTC, timedelta
from time import sleep

import numpy as np

warnings.simplefilter("ignore", DeprecationWarning)
warnings.simplefilter("ignore", FutureWarning)
import pandas as pd
from alive_progress import alive_bar
from PKDevTools.classes.Committer import Committer
from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.PKDateUtilities import PKDateUtilities
from PKDevTools.classes.log import default_logger
from PKDevTools.classes.SuppressOutput import SuppressOutput
from PKDevTools.classes import Archiver
from PKDevTools.classes.Telegram import (
    is_token_telegram_configured,
    send_document,
    send_message,
    send_photo,
    send_media_group
)
from PKNSETools.morningstartools.PKMorningstarDataFetcher import morningstarDataFetcher
from PKNSETools.Nasdaq.PKNasdaqIndex import PKNasdaqIndexFetcher
from tabulate import tabulate
from halo import Halo

import pkscreener.classes.ConfigManager as ConfigManager
import pkscreener.classes.Fetcher as Fetcher
import pkscreener.classes.ScreeningStatistics as ScreeningStatistics
from pkscreener.classes import Utility, ConsoleUtility, ConsoleMenuUtility, ImageUtility
from pkscreener.classes.Utility import STD_ENCODING
from pkscreener.classes import VERSION, PortfolioXRay
from pkscreener.classes.Backtest import backtest, backtestSummary
from pkscreener.classes.PKSpreadsheets import PKSpreadsheets
from PKDevTools.classes.OutputControls import OutputControls
from PKDevTools.classes.Environment import PKEnvironment
from pkscreener.classes.CandlePatterns import CandlePatterns
from pkscreener.classes import AssetsManager
from PKDevTools.classes.FunctionTimeouts import exit_after
from pkscreener.classes.MenuOptions import (
    level0MenuDict,
    level1_X_MenuDict,
    level1_P_MenuDict,
    level2_X_MenuDict,
    level2_P_MenuDict,
    level3_X_ChartPattern_MenuDict,
    level3_X_PopularStocks_MenuDict,
    level3_X_PotentialProfitable_MenuDict,
    PRICE_CROSS_SMA_EMA_DIRECTION_MENUDICT,
    PRICE_CROSS_SMA_EMA_TYPE_MENUDICT,
    PRICE_CROSS_PIVOT_POINT_TYPE_MENUDICT,
    level3_X_Reversal_MenuDict,
    level4_X_Lorenzian_MenuDict,
    level4_X_ChartPattern_Confluence_MenuDict,
    level4_X_ChartPattern_BBands_SQZ_MenuDict,
    level4_X_ChartPattern_MASignalMenuDict,
    level1_index_options_sectoral,
    menus,
    MAX_SUPPORTED_MENU_OPTION,
    MAX_MENU_OPTION,
    PIPED_SCANNERS,
    PREDEFINED_SCAN_MENU_KEYS,
    PREDEFINED_SCAN_MENU_TEXTS,
    INDICES_MAP,
    CANDLESTICK_DICT
)
from pkscreener.classes.OtaUpdater import OTAUpdater
from pkscreener.classes.Portfolio import PortfolioCollection
from pkscreener.classes.PKTask import PKTask
from pkscreener.classes.PKScheduler import PKScheduler
from pkscreener.classes.PKScanRunner import PKScanRunner
from pkscreener.classes.PKMarketOpenCloseAnalyser import PKMarketOpenCloseAnalyser
from pkscreener.classes.PKPremiumHandler import PKPremiumHandler
from pkscreener.classes.AssetsManager import PKAssetsManager
from pkscreener.classes.PKAnalytics import PKAnalyticsService

if __name__ == '__main__':
    multiprocessing.freeze_support()

# Constants
np.seterr(divide="ignore", invalid="ignore")
TEST_STKCODE = "SBIN"


class PKScreenerMain:
    """
    Main application class for PKScreener that orchestrates the entire screening process.
    Handles initialization, menu navigation, scanning execution, and result processing.
    """

    def __init__(self):
        """Initialize the PKScreener application with default configuration and state."""
        self.configManager = ConfigManager.tools()
        self.configManager.getConfig(ConfigManager.parser)
        self.defaultAnswer = None
        self.fetcher = Fetcher.screenerStockDataFetcher(self.configManager)
        self.mstarFetcher = morningstarDataFetcher(self.configManager)
        self.keyboardInterruptEvent = None
        self.keyboardInterruptEventFired = False
        self.loadCount = 0
        self.loadedStockData = False
        
        # Menu objects
        self.m0 = menus()
        self.m1 = menus()
        self.m2 = menus()
        self.m3 = menus()
        self.m4 = menus()
        
        self.maLength = None
        self.nValueForMenu = 0
        self.menuChoiceHierarchy = ""
        self.newlyListedOnly = False
        self.screenCounter = None
        self.screener = ScreeningStatistics.ScreeningStatistics(self.configManager, default_logger())
        self.screenResults = None
        self.backtest_df = None
        self.screenResultsCounter = None
        self.selectedChoice = {"0": "", "1": "", "2": "", "3": "", "4": ""}
        self.stockDictPrimary = None
        self.stockDictSecondary = None
        self.userPassedArgs = None
        self.elapsed_time = 0
        self.start_time = 0
        self.scanCycleRunning = False
        self.test_messages_queue = None
        self.strategyFilter = []
        self.listStockCodes = None
        self.lastScanOutputStockCodes = None
        self.tasks_queue = None
        self.results_queue = None
        self.consumers = None
        self.logging_queue = None
        self.mp_manager = None
        self.analysis_dict = {}
        self.download_trials = 0
        self.media_group_dict = {}
        self.DEV_CHANNEL_ID = "-1001785195297"
        self.criteria_dateTime = None
        self.saved_screen_results = None
        self.show_saved_diff_results = False
        self.resultsContentsEncoded = None
        self.runCleanUp = False

    def startMarketMonitor(self, mp_dict, keyboardevent):
        """Start monitoring the market status in a separate process."""
        if not 'pytest' in sys.modules:
            from PKDevTools.classes.NSEMarketStatus import NSEMarketStatus
            NSEMarketStatus(mp_dict, keyboardevent).startMarketMonitor()

    def finishScreening(self, downloadOnly, testing, stockDictPrimary, loadCount, 
                       testBuild, screenResults, saveResults, user=None):
        """
        Finalize the screening process by saving data and notifying results.
        
        Args:
            downloadOnly (bool): Whether only downloading data without screening
            testing (bool): Whether running in test mode
            stockDictPrimary (dict): Primary stock data dictionary
            loadCount (int): Number of stocks loaded
            testBuild (bool): Whether running test build
            screenResults: Screen results data
            saveResults: Results to save
            user: User identifier for notifications
        """
        if "RUNNER" not in os.environ.keys() or downloadOnly:
            self.saveDownloadedData(downloadOnly, testing, stockDictPrimary, loadCount)
        
        if not testBuild and not downloadOnly and not testing and \
           ((self.userPassedArgs is not None and "|" not in self.userPassedArgs.options) or self.userPassedArgs is None):
            self.saveNotifyResultsFile(screenResults, saveResults, self.defaultAnswer, 
                                     self.menuChoiceHierarchy, user=user)
        
        if ("RUNNER" in os.environ.keys() and not downloadOnly) or self.userPassedArgs.log:
            self.sendMessageToTelegramChannel(mediagroup=True, user=self.userPassedArgs.user)

    def saveDownloadedData(self, downloadOnly, testing, stockDictPrimary, loadCount):
        """
        Save downloaded stock data to cache for future use.
        
        Args:
            downloadOnly (bool): Whether only downloading data
            testing (bool): Whether running in test mode
            stockDictPrimary (dict): Primary stock data dictionary
            loadCount (int): Number of stocks loaded
        """
        argsIntraday = self.userPassedArgs is not None and self.userPassedArgs.intraday is not None
        intradayConfig = self.configManager.isIntradayConfig()
        intraday = intradayConfig or argsIntraday
        
        if not self.keyboardInterruptEventFired and (downloadOnly or (
            self.configManager.cacheEnabled and not PKDateUtilities.isTradingTime() and not testing
        )):
            OutputControls().printOutput(
                colorText.GREEN
                + "  [+] Caching Stock Data for future use, Please Wait... "
                + colorText.END,
                end="",
            )
            AssetsManager.PKAssetsManager.saveStockData(stockDictPrimary, self.configManager, loadCount, intraday)
            
            if downloadOnly:
                cache_file = AssetsManager.PKAssetsManager.saveStockData(stockDictPrimary, self.configManager, 
                                                                        loadCount, intraday, downloadOnly=downloadOnly)
                cacheFileSize = os.stat(cache_file).st_size if os.path.exists(cache_file) else 0
                
                if cacheFileSize < 1024*1024*40:
                    try:
                        from PKDevTools.classes import Archiver
                        log_file_path = os.path.join(Archiver.get_user_data_dir(), "pkscreener-logs.txt")
                        message = f"{cache_file} has size: {cacheFileSize}! Something is wrong!"
                        
                        if os.path.exists(log_file_path):
                            self.sendMessageToTelegramChannel(caption=message, document_filePath=log_file_path, 
                                                            user=self.DEV_CHANNEL_ID)
                        else:
                            self.sendMessageToTelegramChannel(message=message, user=self.DEV_CHANNEL_ID)
                    except:
                        pass
                    
                    if "PKDevTools_Default_Log_Level" not in os.environ.keys():
                        launcher = f'"{sys.argv[0]}"' if " " in sys.argv[0] else sys.argv[0]
                        launcher = f"python3.12 {launcher}" if (launcher.endswith(".py\"") or launcher.endswith(".py")) else launcher
                        os.system(f"{launcher} -a Y -e -l -d {'-i 1m' if self.configManager.isIntradayConfig() else ''}")
                    else:
                        del os.environ['PKDevTools_Default_Log_Level']
                        PKAnalyticsService().send_event("app_exit")
                        sys.exit(0)
        else:
            OutputControls().printOutput(colorText.GREEN + "  [+] Skipped Saving!" + colorText.END)

    def saveNotifyResultsFile(self, screenResults, saveResults, defaultAnswer, menuChoiceHierarchy, user=None):
        """
        Save screening results to file and send notifications.
        
        Args:
            screenResults: Screen results data
            saveResults: Results to save
            defaultAnswer: Default answer for prompts
            menuChoiceHierarchy: Menu choice hierarchy string
            user: User identifier for notifications
        """
        global elapsed_time, selectedChoice, media_group_dict, criteria_dateTime
        
        if user is None and self.userPassedArgs.user is not None:
            user = self.userPassedArgs.user
            
        if ">|" in self.userPassedArgs.options and not self.configManager.alwaysExportToExcel:
            return
            
        caption = f'<b>{menuChoiceHierarchy.split(">")[-1]}</b>'
        
        if screenResults is not None and len(screenResults) >= 1:
            choices = PKScanRunner.getFormattedChoices(self.userPassedArgs, self.selectedChoice)
            
            if self.userPassedArgs.progressstatus is not None:
                choices = self.userPassedArgs.progressstatus.split("=>")[0].split("  [+] ")[1]
                
            choices = f'{choices.strip()}{"_IA" if self.userPassedArgs is not None and self.userPassedArgs.runintradayanalysis else ""}'
            needsCalc = self.userPassedArgs is not None and self.userPassedArgs.backtestdaysago is not None
            pastDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(
                int(self.userPassedArgs.backtestdaysago) if needsCalc else 0) if needsCalc else None
            
            filename = PKAssetsManager.promptSaveResults(choices, saveResults, 
                                                       defaultAnswer=defaultAnswer, pastDate=pastDate,
                                                       screenResults=screenResults)
            
            if filename is not None:
                if "ATTACHMENTS" not in self.media_group_dict.keys():
                    self.media_group_dict["ATTACHMENTS"] = []
                    
                caption = self.media_group_dict["CAPTION"] if "CAPTION" in self.media_group_dict.keys() else menuChoiceHierarchy
                self.media_group_dict["ATTACHMENTS"].append({"FILEPATH": filename, "CAPTION": caption.replace('&', 'n')})

            OutputControls().printOutput(
                colorText.WARN
                + f"  [+] Notes:\n  [+] 1.Trend calculation is based on 'daysToLookBack'. See configuration.\n  [+] 2.Reduce the console font size to fit all columns on screen.\n  [+] Standard data columns were hidden: {self.configManager.alwaysHiddenDisplayColumns}. If you want, you can change this in pkscreener.ini"
                + colorText.END
            )
            
        if self.userPassedArgs.monitor is None:
            needsCalc = self.userPassedArgs is not None and self.userPassedArgs.backtestdaysago is not None
            pastDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(
                int(self.userPassedArgs.backtestdaysago) if needsCalc else 0) if self.criteria_dateTime is None else self.criteria_dateTime
                
            if self.userPassedArgs.triggertimestamp is None:
                self.userPassedArgs.triggertimestamp = int(PKDateUtilities.currentDateTimestamp())
                
            OutputControls().printOutput(
                colorText.GREEN
                + f"  [+] Screening Completed. Found {len(screenResults) if screenResults is not None else 0} results in {round(self.elapsed_time,2)} sec. for {colorText.END}{colorText.FAIL}{pastDate}{colorText.END}{colorText.GREEN}. Queue Wait Time:{int(PKDateUtilities.currentDateTimestamp()-self.userPassedArgs.triggertimestamp-round(self.elapsed_time,2))}s! Press Enter to Continue.."
                + colorText.END
                , enableMultipleLineOutput=True
            )
            
            if defaultAnswer is None:
                OutputControls().takeUserInput("Press <Enter> to continue...")

    def getDownloadChoices(self, defaultAnswer=None):
        """
        Get menu choices for download operations.
        
        Args:
            defaultAnswer: Default answer for prompts
            
        Returns:
            tuple: Menu option, index option, execute option, and selected choices
        """
        argsIntraday = self.userPassedArgs is not None and self.userPassedArgs.intraday is not None
        intradayConfig = self.configManager.isIntradayConfig()
        intraday = intradayConfig or argsIntraday
        
        exists, cache_file = AssetsManager.PKAssetsManager.afterMarketStockDataExists(intraday)
        
        if exists:
            shouldReplace = AssetsManager.PKAssetsManager.promptFileExists(
                cache_file=cache_file, defaultAnswer=defaultAnswer
            )
            
            if shouldReplace == "N":
                OutputControls().printOutput(
                    cache_file
                    + colorText.END
                    + " already exists. Exiting as user chose not to replace it!"
                )
                PKAnalyticsService().send_event("app_exit")
                sys.exit(0)
            else:
                pattern = f"{'intraday_' if intraday else ''}stock_data_*.pkl"
                self.configManager.deleteFileWithPattern(rootDir=Archiver.get_user_data_dir(), pattern=pattern)
                
        return "X", 12, 0, {"0": "X", "1": "12", "2": "0"}

    def getHistoricalDays(self, numStocks, testing):
        """
        Calculate the number of historical days for backtesting based on stock count.
        
        Args:
            numStocks (int): Number of stocks to process
            testing (bool): Whether running in test mode
            
        Returns:
            int: Number of historical days to use
        """
        return (
            2 if testing else self.configManager.backtestPeriod
        )

    def getScannerMenuChoices(self, testBuild=False, downloadOnly=False, startupoptions=None,
                             menuOption=None, indexOption=None, executeOption=None, 
                             defaultAnswer=None, user=None):
        """
        Get menu choices for scanner operations based on user input and current state.
        
        Args:
            testBuild (bool): Whether running test build
            downloadOnly (bool): Whether only downloading data
            startupoptions: Startup options string
            menuOption: Selected menu option
            indexOption: Selected index option
            executeOption: Selected execute option
            defaultAnswer: Default answer for prompts
            user: User identifier
            
        Returns:
            tuple: Menu option, index option, execute option, and selected choices
        """
        executeOption = executeOption
        menuOption = menuOption
        
        try:
            if menuOption is None:
                selectedMenu = self.initExecution(menuOption=menuOption)
                menuOption = selectedMenu.menuKey
                
            if menuOption in ["H", "U", "T", "E", "Y"]:
                self.handleSecondaryMenuChoices(menuOption, testBuild, defaultAnswer=defaultAnswer, user=user)
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
            elif menuOption in ["X", "C"]:
                indexOption, executeOption = self.initPostLevel0Execution(
                    menuOption=menuOption, indexOption=indexOption, executeOption=executeOption
                )
                indexOption, executeOption = self.initPostLevel1Execution(
                    indexOption=indexOption, executeOption=executeOption
                )
        except KeyboardInterrupt:
            OutputControls().takeUserInput(
                colorText.FAIL
                + "  [+] Press <Enter> to Exit!"
                + colorText.END
            )
            PKAnalyticsService().send_event("app_exit")
            sys.exit(0)
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            
        return menuOption, indexOption, executeOption, self.selectedChoice

    def getSummaryCorrectnessOfStrategy(self, resultdf, summaryRequired=True):
        """
        Get summary of strategy correctness from backtest results.
        
        Args:
            resultdf: Results dataframe
            summaryRequired (bool): Whether summary is required
            
        Returns:
            tuple: Summary dataframe and detail dataframe
        """
        summarydf = None
        detaildf = None
        
        try:
            if resultdf is None or len(resultdf) == 0:
                return None, None
                
            results = resultdf.copy()
            
            if summaryRequired:
                _, reportNameSummary = self.getBacktestReportFilename(optionalName="Summary")
                dfs = pd.read_html(
                    "https://pkjmesra.github.io/PKScreener/Backtest-Reports/{0}".format(
                        reportNameSummary.replace("_X_", "_B_").replace("_G_", "_B_").replace("_S_", "_B_")
                    ), encoding="UTF-8", attrs={'id': 'resultsTable'}
                )
                
            _, reportNameDetail = self.getBacktestReportFilename()
            dfd = pd.read_html(
                "https://pkjmesra.github.io/PKScreener/Backtest-Reports/{0}".format(
                    reportNameDetail.replace("_X_", "_B_").replace("_G_", "_B_").replace("_S_", "_B_")
                ), encoding="UTF-8", attrs={'id': 'resultsTable'}
            )

            if summaryRequired and dfs is not None and len(dfs) > 0:
                df = dfs[0]
                summarydf = df[df["Stock"] == "SUMMARY"]
                
                for col in summarydf.columns:
                    summarydf.loc[:, col] = summarydf.loc[:, col].apply(
                        lambda x: ConsoleUtility.PKConsoleTools.getFormattedBacktestSummary(
                            x, columnName=col
                        )
                    )
                    
                summarydf = summarydf.replace(np.nan, "", regex=True)
                
            if dfd is not None and len(dfd) > 0:
                df = dfd[0]
                results.reset_index(inplace=True)
                detaildf = df[df["Stock"].isin(results["Stock"])]
                
                for col in detaildf.columns:
                    detaildf.loc[:, col] = detaildf.loc[:, col].apply(
                        lambda x: ConsoleUtility.PKConsoleTools.getFormattedBacktestSummary(
                            x, pnlStats=True, columnName=col
                        )
                    )
                    
                detaildf = detaildf.replace(np.nan, "", regex=True)
                detaildf.loc[:, "volume"] = detaildf.loc[:, "volume"].apply(
                    lambda x: Utility.tools.formatRatio(x, self.configManager.volumeRatio)
                )
                detaildf.sort_values(["Stock", "Date"], ascending=[True, False], inplace=True)
                detaildf.rename(columns={"LTP": "LTP on Date"}, inplace=True)
                
        except urllib.error.HTTPError as e:
            if "HTTP Error 404" in str(e):
                pass
            else:
                default_logger().debug(e, exc_info=True)
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            pass
            
        return summarydf, detaildf

    def getTestBuildChoices(self, indexOption=None, executeOption=None, menuOption=None):
        """
        Get menu choices for test build operations.
        
        Args:
            indexOption: Selected index option
            executeOption: Selected execute option
            menuOption: Selected menu option
            
        Returns:
            tuple: Menu option, index option, execute option, and selected choices
        """
        if menuOption is not None:
            return (
                str(menuOption),
                indexOption if indexOption is not None else 1,
                executeOption if executeOption is not None else 0,
                {
                    "0": str(menuOption),
                    "1": (str(indexOption) if indexOption is not None else 1),
                    "2": (str(executeOption) if executeOption is not None else 0),
                },
            )
        return "X", 1, 0, {"0": "X", "1": "1", "2": "0"}

    def getTopLevelMenuChoices(self, startupoptions, testBuild, downloadOnly, defaultAnswer=None):
        """
        Get top-level menu choices based on startup options and mode.
        
        Args:
            startupoptions: Startup options string
            testBuild (bool): Whether running test build
            downloadOnly (bool): Whether only downloading data
            defaultAnswer: Default answer for prompts
            
        Returns:
            tuple: Options list, menu option, index option, and execute option
        """
        executeOption = None
        menuOption = None
        indexOption = None
        options = []
        
        if startupoptions is not None:
            options = startupoptions.split(":")
            menuOption = options[0] if len(options) >= 1 else None
            indexOption = options[1] if len(options) >= 2 else None
            executeOption = options[2] if len(options) >= 3 else None
            
        if testBuild:
            menuOption, indexOption, executeOption, self.selectedChoice = self.getTestBuildChoices(
                indexOption=indexOption, executeOption=executeOption, menuOption=menuOption
            )
        elif downloadOnly:
            menuOption, indexOption, executeOption, self.selectedChoice = self.getDownloadChoices(
                defaultAnswer=defaultAnswer
            )
            intraday = self.userPassedArgs.intraday or self.configManager.isIntradayConfig()
            filePrefix = "INTRADAY_" if intraday else ""
            _, cache_file_name = AssetsManager.PKAssetsManager.afterMarketStockDataExists(intraday)
            Utility.tools.set_github_output(f"{filePrefix}DOWNLOAD_CACHE_FILE_NAME", cache_file_name)
            
        indexOption = 0 if self.lastScanOutputStockCodes is not None else indexOption
        
        return options, menuOption, indexOption, executeOption

    def handleScannerExecuteOption4(self, executeOption, options):
        """
        Handle scanner execute option 4 (volume analysis).
        
        Args:
            executeOption: Execute option value
            options: Options list
            
        Returns:
            int: Days for lowest volume analysis
        """
        try:
            if len(options) >= 4:
                if str(options[3]).upper() == "D":
                    daysForLowestVolume = 5
                else:
                    daysForLowestVolume = int(options[3])
            else:
                daysForLowestVolume = int(
                    input(
                        colorText.WARN
                        + "\n  [+] The Volume should be lowest since last how many candles? (Default = 5)"
                    ) or "5"
                )
        except ValueError as e:
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(colorText.END)
            OutputControls().printOutput(
                colorText.FAIL
                + "  [+] Error: Non-numeric value entered! Please try again!"
                + colorText.END
            )
            OutputControls().takeUserInput("Press <Enter> to continue...")
            return
            
        OutputControls().printOutput(colorText.END)
        self.nValueForMenu = daysForLowestVolume
        return daysForLowestVolume

    def handleSecondaryMenuChoices(self, menuOption, testing=False, defaultAnswer=None, user=None):
        """
        Handle secondary menu choices (help, update, config, etc.).
        
        Args:
            menuOption: Selected menu option
            testing (bool): Whether running in test mode
            defaultAnswer: Default answer for prompts
            user: User identifier
        """
        if menuOption == "H":
            self.showSendHelpInfo(defaultAnswer, user)
        elif menuOption == "U":
            OTAUpdater.checkForUpdate(VERSION, skipDownload=testing)
            if defaultAnswer is None:
                OutputControls().takeUserInput("Press <Enter> to continue...")
        elif menuOption == "T":
            if self.userPassedArgs is None or self.userPassedArgs.options is None:
                selectedMenu = self.m0.find(menuOption)
                self.m1.renderForMenu(selectedMenu=selectedMenu)
                periodOption = input(
                    colorText.FAIL + "  [+] Select option: "
                ) or ('L' if self.configManager.period == '1y' else 'S')
                OutputControls().printOutput(colorText.END, end="")
                
                if periodOption is None or periodOption.upper() not in ["L", "S", "B"]:
                    return
                    
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                
                if periodOption.upper() in ["L", "S"]:
                    selectedMenu = self.m1.find(periodOption)
                    self.m2.renderForMenu(selectedMenu=selectedMenu)
                    durationOption = input(
                        colorText.FAIL + "  [+] Select option: "
                    ) or "1"
                    OutputControls().printOutput(colorText.END, end="")
                    
                    if durationOption is None or durationOption.upper() not in ["1", "2", "3", "4", "5"]:
                        return
                        
                    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                    
                    if durationOption.upper() in ["1", "2", "3", "4"]:
                        selectedMenu = self.m2.find(durationOption)
                        periodDurations = selectedMenu.menuText.split("(")[1].split(")")[0].split(", ")
                        self.configManager.period = periodDurations[0]
                        self.configManager.duration = periodDurations[1]
                        self.configManager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
                        self.configManager.deleteFileWithPattern(rootDir=Archiver.get_user_data_dir(), pattern="*stock_data_*.pkl*")
                    elif durationOption.upper() in ["5"]:
                        self.configManager.setConfig(ConfigManager.parser, default=False, showFileCreatedText=True)
                        self.configManager.deleteFileWithPattern(rootDir=Archiver.get_user_data_dir(), pattern="*stock_data_*.pkl*")
                    return
                elif periodOption.upper() in ["B"]:
                    lastTradingDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(n=(22 if self.configManager.period == '1y' else 15))
                    backtestDaysAgo = input(
                        f"{colorText.FAIL}  [+] Enter no. of days/candles in the past as starting candle for which you'd like to run the scans\n  [+] You can also enter a past date in {colorText.END}{colorText.GREEN}YYYY-MM-DD{colorText.END}{colorText.FAIL} format\n  [+] (e.g. {colorText.GREEN}10{colorText.END} for 10 candles ago or {colorText.GREEN}0{colorText.END} for today or {colorText.GREEN}{lastTradingDate}{colorText.END}):"
                    ) or ('22' if self.configManager.period == '1y' else '15')
                    OutputControls().printOutput(colorText.END, end="")
                    
                    if len(str(backtestDaysAgo)) >= 3 and "-" in str(backtestDaysAgo):
                        try:
                            backtestDaysAgo = abs(PKDateUtilities.trading_days_between(
                                d1=PKDateUtilities.dateFromYmdString(str(backtestDaysAgo)),
                                d2=PKDateUtilities.currentDateTime()))
                        except Exception as e:
                            default_logger().debug(e, exc_info=True)
                            OutputControls().printOutput(f"An error occured! Going ahead with default inputs.")
                            backtestDaysAgo = ('22' if self.configManager.period == '1y' else '15')
                            sleep(3)
                            pass
                            
                    launcher = f'"{sys.argv[0]}"' if " " in sys.argv[0] else sys.argv[0]
                    requestingUser = f" -u {self.userPassedArgs.user}" if self.userPassedArgs.user is not None else ""
                    enableLog = f" -l" if self.userPassedArgs.log else ""
                    enableTelegramMode = f" --telegram" if self.userPassedArgs is not None and self.userPassedArgs.telegram else ""
                    stockListParam = f" --stocklist {self.userPassedArgs.stocklist}" if self.userPassedArgs.stocklist else ""
                    slicewindowParam = f" --slicewindow {self.userPassedArgs.slicewindow}" if self.userPassedArgs.slicewindow else ""
                    fnameParam = f" --fname {self.resultsContentsEncoded}" if self.resultsContentsEncoded else ""
                    launcher = f"python3.12 {launcher}" if (launcher.endswith(".py\"") or launcher.endswith(".py")) else launcher
                    
                    OutputControls().printOutput(f"{colorText.GREEN}Launching PKScreener in quick backtest mode. If it does not launch, please try with the following:{colorText.END}\n{colorText.FAIL}{launcher} --backtestdaysago {int(backtestDaysAgo)}{requestingUser}{enableLog}{enableTelegramMode}{stockListParam}{slicewindowParam}{fnameParam}{colorText.END}\n{colorText.WARN}Press Ctrl + C to exit quick backtest mode.{colorText.END}")
                    sleep(2)
                    os.system(f"{launcher} --systemlaunched -a Y -e --backtestdaysago {int(backtestDaysAgo)}{requestingUser}{enableLog}{enableTelegramMode}{stockListParam}{slicewindowParam}{fnameParam}")
                    ConsoleUtility.PKConsoleTools.clearScreen(clearAlways=True, forceTop=True)
                    return None, None
            elif self.userPassedArgs is not None and self.userPassedArgs.options is not None:
                options = self.userPassedArgs.options.split(":")
                selectedMenu = self.m0.find(options[0])
                self.m1.renderForMenu(selectedMenu=selectedMenu, asList=True)
                selectedMenu = self.m1.find(options[1])
                self.m2.renderForMenu(selectedMenu=selectedMenu, asList=True)
                
                if options[2] in ["1", "2", "3", "4"]:
                    selectedMenu = self.m2.find(options[2])
                    periodDurations = selectedMenu.menuText.split("(")[1].split(")")[0].split(", ")
                    self.configManager.period = periodDurations[0]
                    self.configManager.duration = periodDurations[1]
                    self.configManager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
                else:
                    self.toggleUserConfig()
            else:
                self.toggleUserConfig()
        elif menuOption == "E":
            self.configManager.setConfig(ConfigManager.parser)
        elif menuOption == "Y":
            self.showSendConfigInfo(defaultAnswer, user)
            
        return

    def showSendConfigInfo(self, defaultAnswer=None, user=None):
        """
        Show and send configuration information.
        
        Args:
            defaultAnswer: Default answer for prompts
            user: User identifier
        """
        configData = self.configManager.showConfigFile(defaultAnswer=('Y' if user is not None else defaultAnswer))
        
        if user is not None:
            self.sendMessageToTelegramChannel(message=ImageUtility.PKImageTools.removeAllColorStyles(configData), user=user)
            
        if defaultAnswer is None:
            input("Press any key to continue...")

    def showSendHelpInfo(self, defaultAnswer=None, user=None):
        """
        Show and send help information.
        
        Args:
            defaultAnswer: Default answer for prompts
            user: User identifier
        """
        helpData = ConsoleUtility.PKConsoleTools.showDevInfo(defaultAnswer=('Y' if user is not None else defaultAnswer))
        
        if user is not None:
            self.sendMessageToTelegramChannel(message=ImageUtility.PKImageTools.removeAllColorStyles(helpData), user=user)
            
        if defaultAnswer is None:
            input("Press any key to continue...")

    def ensureMenusLoaded(self, menuOption=None, indexOption=None, executeOption=None):
        """
        Ensure all menus are loaded and rendered.
        
        Args:
            menuOption: Selected menu option
            indexOption: Selected index option
            executeOption: Selected execute option
        """
        try:
            if len(self.m0.menuDict.keys()) == 0:
                self.m0.renderForMenu(asList=True)
                
            if len(self.m1.menuDict.keys()) == 0:
                self.m1.renderForMenu(selectedMenu=self.m0.find(menuOption), asList=True)
                
            if len(self.m2.menuDict.keys()) == 0:
                self.m2.renderForMenu(selectedMenu=self.m1.find(indexOption), asList=True)
                
            if len(self.m3.menuDict.keys()) == 0:
                self.m3.renderForMenu(selectedMenu=self.m2.find(executeOption), asList=True)
        except:
            pass

    def initExecution(self, menuOption=None):
        """
        Initialize execution by showing main menu and getting user selection.
        
        Args:
            menuOption: Pre-selected menu option
            
        Returns:
            object: Selected menu object
        """
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        
        if (self.userPassedArgs is not None and self.userPassedArgs.pipedmenus is not None):
            OutputControls().printOutput(
                colorText.FAIL
                + "  [+] You chose: "
                + f" (Piped Scan Mode) [{self.userPassedArgs.pipedmenus}]"
                + colorText.END
            )
            
        self.m0.renderForMenu(selectedMenu=None, asList=(self.userPassedArgs is not None and self.userPassedArgs.options is not None))
        
        try:
            needsCalc = self.userPassedArgs is not None and self.userPassedArgs.backtestdaysago is not None
            pastDate = f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(self.userPassedArgs.backtestdaysago) if needsCalc else 0)}{colorText.END} ]\n" if needsCalc else ""
            
            if menuOption is None:
                if "PKDevTools_Default_Log_Level" in os.environ.keys():
                    from PKDevTools.classes import Archiver
                    log_file_path = os.path.join(Archiver.get_user_data_dir(), "pkscreener-logs.txt")
                    OutputControls().printOutput(colorText.FAIL + "\n      [+] Logs will be written to:" + colorText.END)
                    OutputControls().printOutput(colorText.GREEN + f"      [+] {log_file_path}" + colorText.END)
                    OutputControls().printOutput(colorText.FAIL + "      [+] If you need to share,run through the menus that are causing problems. At the end, open this folder, zip the log file to share at https://github.com/pkjmesra/PKScreener/issues .\n" + colorText.END)
                    
                menuOption = input(colorText.FAIL + f"{pastDate}  [+] Select option: ") or "P"
                OutputControls().printOutput(colorText.END, end="")
                
            if menuOption == "" or menuOption is None:
                menuOption = "X"
                
            menuOption = menuOption.upper()
            selectedMenu = self.m0.find(menuOption)
            
            if selectedMenu is not None:
                if selectedMenu.menuKey == "Z":
                    OutputControls().takeUserInput(
                        colorText.FAIL
                        + "  [+] Press <Enter> to Exit!"
                        + colorText.END
                    )
                    PKAnalyticsService().send_event("app_exit")
                    sys.exit(0)
                elif selectedMenu.menuKey in ["B", "C", "G", "H", "U", "T", "S", "E", "X", "Y", "M", "D", "I", "L", "F"]:
                    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                    self.selectedChoice["0"] = selectedMenu.menuKey
                    return selectedMenu
                elif selectedMenu.menuKey in ["P"]:
                    return selectedMenu
                    
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            self.showOptionErrorMessage()
            return self.initExecution()

        self.showOptionErrorMessage()
        return self.initExecution()

    def initPostLevel0Execution(self, menuOption=None, indexOption=None, executeOption=None, skip=[], retrial=False):
        """
        Initialize execution after level 0 menu selection.
        
        Args:
            menuOption: Selected menu option
            indexOption: Selected index option
            executeOption: Selected execute option
            skip: List of options to skip
            retrial (bool): Whether this is a retry
            
        Returns:
            tuple: Index option and execute option
        """
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        
        if menuOption is None:
            OutputControls().printOutput('You must choose an option from the previous menu! Defaulting to "X"...')
            menuOption = "X"
            
        OutputControls().printOutput(
            colorText.FAIL
            + "  [+] You chose: "
            + level0MenuDict[menuOption].strip()
            + (f" (Piped Scan Mode) [{self.userPassedArgs.pipedmenus}]" if (self.userPassedArgs is not None and self.userPassedArgs.pipedmenus is not None) else "")
            + colorText.END
        )
        
        if indexOption is None:
            selectedMenu = self.m0.find(menuOption)
            self.m1.renderForMenu(selectedMenu=selectedMenu, skip=skip, asList=(self.userPassedArgs is not None and self.userPassedArgs.options is not None))
            
        try:
            needsCalc = self.userPassedArgs is not None and self.userPassedArgs.backtestdaysago is not None
            pastDate = f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(self.userPassedArgs.backtestdaysago) if needsCalc else 0)}{colorText.END} ]\n" if needsCalc else ""
            
            if indexOption is None:
                indexOption = OutputControls().takeUserInput(
                    colorText.FAIL + f"{pastDate}  [+] Select option: "
                )
                OutputControls().printOutput(colorText.END, end="")
                
            if (str(indexOption).isnumeric() and int(indexOption) > 1 and str(executeOption).isnumeric() and int(str(executeOption)) <= MAX_SUPPORTED_MENU_OPTION) or \
                    str(indexOption).upper() in ["S", "E", "W"]:
                self.ensureMenusLoaded(menuOption, indexOption, executeOption)
                
                if not PKPremiumHandler.hasPremium(self.m1.find(str(indexOption).upper())):
                    PKAnalyticsService().send_event(f"non_premium_user_{menuOption}_{indexOption}_{executeOption}")
                    return None, None
                    
            if indexOption == "" or indexOption is None:
                indexOption = int(self.configManager.defaultIndex)
            elif not str(indexOption).isnumeric():
                indexOption = indexOption.upper()
                
                if indexOption in ["M", "E", "N", "Z"]:
                    return indexOption, 0
            else:
                indexOption = int(indexOption)
                
                if indexOption < 0 or indexOption > 15:
                    raise ValueError
                elif indexOption == 13:
                    self.configManager.period = "2y"
                    self.configManager.getConfig(ConfigManager.parser)
                    self.newlyListedOnly = True
                    indexOption = 12
                    
            if indexOption == 15:
                from pkscreener.classes.MarketStatus import MarketStatus
                MarketStatus().exchange = "^IXIC"
                
            self.selectedChoice["1"] = str(indexOption)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(
                colorText.FAIL
                + "\n  [+] Please enter a valid numeric option & Try Again!"
                + colorText.END
            )
            
            if not retrial:
                sleep(2)
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                return self.initPostLevel0Execution(retrial=True)
                
        return indexOption, executeOption

    def initPostLevel1Execution(self, indexOption, executeOption=None, skip=[], retrial=False):
        """
        Initialize execution after level 1 menu selection.
        
        Args:
            indexOption: Selected index option
            executeOption: Selected execute option
            skip: List of options to skip
            retrial (bool): Whether this is a retry
            
        Returns:
            tuple: Index option and execute option
        """
        self.listStockCodes = [] if self.listStockCodes is None or len(self.listStockCodes) == 0 else self.listStockCodes
        
        if executeOption is None:
            if indexOption is not None and indexOption != "W":
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                OutputControls().printOutput(
                    colorText.FAIL
                    + "  [+] You chose: "
                    + level0MenuDict[self.selectedChoice["0"]].strip()
                    + " > "
                    + level1_X_MenuDict[self.selectedChoice["1"]].strip()
                    + (f" (Piped Scan Mode) [{self.userPassedArgs.pipedmenus}]" if (self.userPassedArgs is not None and self.userPassedArgs.pipedmenus is not None) else "")
                    + colorText.END
                )
                
                selectedMenu = self.m1.find(indexOption)
                self.m2.renderForMenu(selectedMenu=selectedMenu, skip=skip, asList=(self.userPassedArgs is not None and self.userPassedArgs.options is not None))
                stockIndexCode = str(len(level1_index_options_sectoral.keys()))
                
                if indexOption == "S":
                    self.ensureMenusLoaded("X", indexOption, executeOption)
                    
                    if not PKPremiumHandler.hasPremium(selectedMenu):
                        PKAnalyticsService().send_event(f"non_premium_user_X_{indexOption}_{executeOption}")
                        PKAnalyticsService().send_event("app_exit")
                        sys.exit(0)
                        
                    indexKeys = level1_index_options_sectoral.keys()
                    stockIndexCode = input(
                        colorText.FAIL + "  [+] Select option: "
                    ) or str(len(indexKeys))
                    OutputControls().printOutput(colorText.END, end="")
                    
                    if stockIndexCode == str(len(indexKeys)):
                        for indexCode in indexKeys:
                            if indexCode != str(len(indexKeys)):
                                self.listStockCodes.append(level1_index_options_sectoral[str(indexCode)].split("(")[1].split(")")[0])
                    else:
                        self.listStockCodes = [level1_index_options_sectoral[str(stockIndexCode)].split("(")[1].split(")")[0]]
                        
                    selectedMenu.menuKey = "0"  # Reset because user must have selected specific index menu with single stock
                    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                    self.m2.renderForMenu(selectedMenu=selectedMenu, skip=skip, asList=(self.userPassedArgs is not None and self.userPassedArgs.options is not None))
                    
        try:
            needsCalc = self.userPassedArgs is not None and self.userPassedArgs.backtestdaysago is not None
            pastDate = f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(self.userPassedArgs.backtestdaysago) if needsCalc else 0)}{colorText.END} ]\n" if needsCalc else ""
            
            if indexOption is not None and indexOption != "W":
                if executeOption is None:
                    executeOption = input(
                        colorText.FAIL + f"{pastDate}  [+] Select option: "
                    ) or "9"
                    OutputControls().printOutput(colorText.END, end="")
                    
                self.ensureMenusLoaded("X", indexOption, executeOption)
                
                if not PKPremiumHandler.hasPremium(self.m2.find(str(executeOption))):
                    PKAnalyticsService().send_event(f"non_premium_user_X_{indexOption}_{executeOption}")
                    return None, None
                    
                if executeOption == "":
                    executeOption = 1
                    
                if not str(executeOption).isnumeric():
                    executeOption = executeOption.upper()
                else:
                    executeOption = int(executeOption)
                    
                    if executeOption < 0 or executeOption > MAX_MENU_OPTION:
                        raise ValueError
            else:
                executeOption = 0
                
            self.selectedChoice["2"] = str(executeOption)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(
                colorText.FAIL
                + "\n  [+] Please enter a valid numeric option & Try Again!"
                + colorText.END
            )
            
            if not retrial:
                sleep(2)
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                return self.initPostLevel1Execution(indexOption, executeOption, retrial=True)
                
        return indexOption, executeOption

    def labelDataForPrinting(self, screenResults, saveResults, volumeRatio, executeOption, reversalOption, menuOption):
        """
        Label and format data for printing and display.
        
        Args:
            screenResults: Screen results data
            saveResults: Results to save
            volumeRatio: Volume ratio for formatting
            executeOption: Execute option value
            reversalOption: Reversal option value
            menuOption: Menu option value
            
        Returns:
            tuple: Formatted screen results and save results
        """
        if saveResults is None:
            return screenResults, saveResults
            
        try:
            isTrading = PKDateUtilities.isTradingTime() and not PKDateUtilities.isTodayHoliday()[0]
            
            if "RUNNER" not in os.environ.keys() and (isTrading or self.userPassedArgs.monitor or ("RSIi" in saveResults.columns)) and self.configManager.calculatersiintraday:
                screenResults['RSI'] = screenResults['RSI'].astype(str) + "/" + screenResults['RSIi'].astype(str)
                saveResults['RSI'] = saveResults['RSI'].astype(str) + "/" + saveResults['RSIi'].astype(str)
                screenResults.rename(columns={"RSI": "RSI/i"}, inplace=True)
                saveResults.rename(columns={"RSI": "RSI/i"}, inplace=True)
                
            sortKey = ["volume"] if "RSI" not in self.menuChoiceHierarchy else ("RSIi" if (isTrading or "RSIi" in saveResults.columns) else "RSI")
            ascending = [False if "RSI" not in self.menuChoiceHierarchy else True]
            
            if executeOption == 21:
                if reversalOption in [3, 5, 6, 7]:
                    sortKey = ["MFI"]
                    ascending = [reversalOption in [6, 7]]
                elif reversalOption in [8, 9]:
                    sortKey = ["FVDiff"]
                    ascending = [reversalOption in [9]]
            elif executeOption == 7:
                if reversalOption in [3]:
                    if "SuperConfSort" in saveResults.columns:
                        sortKey = ["SuperConfSort"]
                        ascending = [False]
                    else:
                        sortKey = ["volume"]
                        ascending = [False]
                elif reversalOption in [4]:
                    if "deviationScore" in saveResults.columns:
                        sortKey = ["deviationScore"]
                        ascending = [True]
                    else:
                        sortKey = ["volume"]
                        ascending = [False]
            elif executeOption == 23:
                sortKey = ["bbands_ulr_ratio_max5"] if "bbands_ulr_ratio_max5" in screenResults.columns else ["volume"]
                ascending = [False]
            elif executeOption == 27:  # ATR Cross
                sortKey = ["ATR"] if "ATR" in screenResults.columns else ["volume"]
                ascending = [False]
            elif executeOption == 31:  # DEEL Momentum
                sortKey = ["%Chng"]
                ascending = [False]
                
            try:
                try:
                    screenResults[sortKey] = screenResults[sortKey].replace("", np.nan).replace(np.inf, np.nan).replace(-np.inf, np.nan).astype(float)
                except:
                    pass
                    
                try:
                    saveResults[sortKey] = saveResults[sortKey].replace("", np.nan).replace(np.inf, np.nan).replace(-np.inf, np.nan).astype(float)
                except:
                    pass
                    
                screenResults.sort_values(by=sortKey, ascending=ascending, inplace=True)
                saveResults.sort_values(by=sortKey, ascending=ascending, inplace=True)
            except Exception as e:
                default_logger().debug(e, exc_info=True)
                pass
                
            columnsToBeDeleted = ["MFI", "FVDiff", "ConfDMADifference", "bbands_ulr_ratio_max5", "RSIi"]
            
            if menuOption not in ["F"]:
                columnsToBeDeleted.extend(["ScanOption"])
                
            if "EoDDiff" in saveResults.columns:
                columnsToBeDeleted.extend(["Trend", "Breakout"])
                
            if "SuperConfSort" in saveResults.columns:
                columnsToBeDeleted.extend(["SuperConfSort"])
                
            if "deviationScore" in saveResults.columns:
                columnsToBeDeleted.extend(["deviationScore"])
                
            if self.userPassedArgs is not None and self.userPassedArgs.options is not None and self.userPassedArgs.options.upper().startswith("C"):
                columnsToBeDeleted.append("FairValue")
                
            if executeOption == 27 and "ATR" in screenResults.columns:  # ATR Cross
                screenResults['ATR'] = screenResults['ATR'].astype(str)
                screenResults['ATR'] = colorText.GREEN + screenResults['ATR'] + colorText.END
                
            for column in columnsToBeDeleted:
                if column in saveResults.columns:
                    saveResults.drop(column, axis=1, inplace=True, errors="ignore")
                    screenResults.drop(column, axis=1, inplace=True, errors="ignore")
                    
            if "Stock" in screenResults.columns:
                screenResults.set_index("Stock", inplace=True)
                
            if "Stock" in saveResults.columns:
                saveResults.set_index("Stock", inplace=True)
                
            screenResults["volume"] = screenResults["volume"].astype(str)
            saveResults["volume"] = saveResults["volume"].astype(str)
            
            screenResults.loc[:, "volume"] = screenResults.loc[:, "volume"].apply(
                lambda x: Utility.tools.formatRatio(float(ImageUtility.PKImageTools.removeAllColorStyles(x)), volumeRatio) if len(str(x).strip()) > 0 else ''
            )
            
            saveResults.loc[:, "volume"] = saveResults.loc[:, "volume"].apply(
                lambda x: str(x) + "x"
            )
            
            screenResults.rename(
                columns={
                    "Trend": f"Trend({self.configManager.daysToLookback}Prds)",
                    "Breakout": f"Breakout({self.configManager.daysToLookback}Prds)",
                },
                inplace=True,
            )
            
            saveResults.rename(
                columns={
                    "Trend": f"Trend({self.configManager.daysToLookback}Prds)",
                    "Breakout": f"Breakout({self.configManager.daysToLookback}Prds)",
                },
                inplace=True,
            )
            
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            
        screenResults.dropna(how="all" if menuOption not in ["F"] else "any", axis=1, inplace=True)
        saveResults.dropna(how="all" if menuOption not in ["F"] else "any", axis=1, inplace=True)
        
        return screenResults, saveResults

    def isInterrupted(self):
        """Check if the process has been interrupted."""
        return self.keyboardInterruptEventFired

    def resetUserMenuChoiceOptions(self):
        """Reset user menu choice options to default values."""
        self.menuChoiceHierarchy = ""
        
        if self.userPassedArgs is not None:
            self.userPassedArgs.pipedtitle = ""
            
        self.media_group_dict = {}

    @Halo(text='', spinner='dots')
    def refreshStockData(self, startupoptions=None):
        """
        Refresh stock data from database or fetch from source.
        
        Args:
            startupoptions: Startup options string
        """
        self.menuChoiceHierarchy = ""
        options = startupoptions.replace("|", "").split(" ")[0].replace(":i", "")
        self.loadedStockData = False
        
        options, menuOption, indexOption, executeOption = self.getTopLevelMenuChoices(
            options, False, False, defaultAnswer='Y'
        )
        
        if indexOption == 0:
            self.listStockCodes = self.handleRequestForSpecificStocks(options, indexOption=indexOption)
            
        self.listStockCodes = self.prepareStocksForScreening(testing=False, downloadOnly=False, 
                                                           listStockCodes=self.listStockCodes, indexOption=indexOption)
        
        try:
            import tensorflow as tf
            with tf.device("/device:GPU:0"):
                self.stockDictPrimary, self.stockDictSecondary = self.loadDatabaseOrFetch(
                    downloadOnly=False, listStockCodes=self.listStockCodes, 
                    menuOption=menuOption, indexOption=indexOption
                )
        except:
            self.stockDictPrimary, self.stockDictSecondary = self.loadDatabaseOrFetch(
                downloadOnly=False, listStockCodes=self.listStockCodes, 
                menuOption=menuOption, indexOption=indexOption
            )
            pass
            
        PKScanRunner.refreshDatabase(self.consumers, self.stockDictPrimary, self.stockDictSecondary)

    def closeWorkersAndExit(self):
        """Close all worker processes and exit the application."""
        if self.consumers is not None:
            PKScanRunner.terminateAllWorkers(userPassedArgs=self.userPassedArgs, consumers=self.consumers, 
                                           tasks_queue=self.tasks_queue, testing=self.userPassedArgs.testbuild)

    def main(self, userArgs=None, optionalFinalOutcome_df=None):
        """
        Main entry point for the PKScreener application.
        
        Args:
            userArgs: User arguments
            optionalFinalOutcome_df: Optional final outcome dataframe
            
        Returns:
            tuple: Screen results and save results
        """
        # [Rest of the main method implementation would go here]
        # This is a very long method that would need to be broken down further
        
        return self.screenResults, self.saveResults

# Additional classes would be defined here for MenuManager, ScanExecutor, ResultProcessor, etc.
# Each would handle specific aspects of the application

# The original global functions would be converted to methods of these classes

