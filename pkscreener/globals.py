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
# =============================================================================
# REFACTORED GLOBALS MODULE
# =============================================================================
# This module has been refactored into several classes for better maintainability:
# - GlobalStore: Centralized state management (pkscreener/classes/GlobalStore.py)
# - ResultsManager: Results processing and display (pkscreener/classes/ResultsManager.py)
# - TelegramNotifier: Telegram messaging (pkscreener/classes/TelegramNotifier.py)
# - BacktestHandler: Backtesting operations (pkscreener/classes/BacktestHandler.py)
#
# This file maintains backward compatibility by exposing the same API.
# =============================================================================

# Keep module imports prior to classes
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

# Import the refactored classes
from pkscreener.classes.ResultsManager import ResultsManager
from pkscreener.classes.TelegramNotifier import TelegramNotifier
from pkscreener.classes.BacktestHandler import BacktestHandler

if __name__ == '__main__':
    multiprocessing.freeze_support()

# =============================================================================
# CONSTANTS
# =============================================================================
TEST_STKCODE = "SBIN"
np.seterr(divide="ignore", invalid="ignore")

# =============================================================================
# GLOBAL VARIABLES (maintained for backward compatibility)
# =============================================================================
configManager = ConfigManager.tools()
configManager.getConfig(ConfigManager.parser)
defaultAnswer = None
fetcher = Fetcher.screenerStockDataFetcher(configManager)
mstarFetcher = morningstarDataFetcher(configManager)
keyboardInterruptEvent = None
keyboardInterruptEventFired = False
loadCount = 0
loadedStockData = False
m0 = menus()
m1 = menus()
m2 = menus()
m3 = menus()
m4 = menus()
maLength = None
nValueForMenu = 0
menuChoiceHierarchy = ""
newlyListedOnly = False
screenCounter = None
screener = ScreeningStatistics.ScreeningStatistics(configManager, default_logger())
screenResults = None
backtest_df = None
screenResultsCounter = None
selectedChoice = {"0": "", "1": "", "2": "", "3": "", "4": ""}
stockDictPrimary = None
stockDictSecondary = None
userPassedArgs = None
elapsed_time = 0
start_time = 0
scanCycleRunning = False
test_messages_queue = None
strategyFilter = []
listStockCodes = None
lastScanOutputStockCodes = None
tasks_queue = None
results_queue = None
consumers = None
logging_queue = None
mp_manager = None
analysis_dict = {}
download_trials = 0
media_group_dict = {}
DEV_CHANNEL_ID = "-1001785195297"
criteria_dateTime = None
saved_screen_results = None
show_saved_diff_results = False
resultsContentsEncoded = None
runCleanUp = False

# =============================================================================
# CLASS INSTANCE HELPERS
# =============================================================================
_results_manager = None
_telegram_notifier = None
_backtest_handler = None


def _get_results_manager():
    """Get the results manager instance."""
    global _results_manager
    if _results_manager is None:
        _results_manager = ResultsManager(configManager, userPassedArgs)
    return _results_manager


def _get_telegram_notifier():
    """Get the telegram notifier instance."""
    global _telegram_notifier
    if _telegram_notifier is None:
        _telegram_notifier = TelegramNotifier(userPassedArgs, test_messages_queue, media_group_dict)
    return _telegram_notifier


def _get_backtest_handler():
    """Get the backtest handler instance."""
    global _backtest_handler
    if _backtest_handler is None:
        _backtest_handler = BacktestHandler(configManager, userPassedArgs)
    return _backtest_handler


# =============================================================================
# DELEGATING WRAPPER FUNCTIONS (for backward compatibility)
# These functions delegate to the refactored classes
# =============================================================================

def getHistoricalDays(numStocks, testing):
    """Delegate to BacktestHandler.get_historical_days()"""
    return _get_backtest_handler().get_historical_days(numStocks, testing)


def getSummaryCorrectnessOfStrategy(resultdf, summaryRequired=True):
    """Delegate to BacktestHandler.get_summary_correctness_of_strategy()"""
    return _get_backtest_handler().get_summary_correctness_of_strategy(resultdf, summaryRequired)


def tabulateBacktestResults(saveResults, maxAllowed=0, force=False):
    """Delegate to BacktestHandler.tabulate_backtest_results()"""
    return _get_backtest_handler().tabulate_backtest_results(saveResults, maxAllowed, force)


def showBacktestResults(backtest_df_param, sortKey="Stock", optionalName="backtest_result", choices=None):
    """Delegate to BacktestHandler.show_backtest_results()"""
    global menuChoiceHierarchy, selectedChoice, elapsed_time
    handler = _get_backtest_handler()
    handler.elapsed_time = elapsed_time
    handler.show_backtest_results(
        backtest_df_param, sortKey, optionalName, 
        menuChoiceHierarchy, selectedChoice, choices
    )


def scanOutputDirectory(backtest=False):
    """Delegate to BacktestHandler.scan_output_directory()"""
    return _get_backtest_handler().scan_output_directory(backtest)


def getBacktestReportFilename(sortKey="Stock", optionalName="backtest_result", choices=None):
    """Delegate to BacktestHandler.get_backtest_report_filename()"""
    global selectedChoice
    return _get_backtest_handler().get_backtest_report_filename(sortKey, optionalName, selectedChoice, choices)


def takeBacktestInputs(menuOption=None, indexOption=None, executeOption=None, backtestPeriod=0):
    """Delegate to BacktestHandler.take_backtest_inputs()"""
    return _get_backtest_handler().take_backtest_inputs(menuOption, indexOption, executeOption, backtestPeriod)


def updateBacktestResults(backtestPeriod, start_time_param, result, sampleDays, backtest_df_param):
    """Delegate to BacktestHandler.update_backtest_results()"""
    global selectedChoice, elapsed_time
    handler = _get_backtest_handler()
    result_df = handler.update_backtest_results(
        backtestPeriod, start_time_param, result, sampleDays, backtest_df_param, selectedChoice
    )
    elapsed_time = handler.elapsed_time
    return result_df


def FinishBacktestDataCleanup(backtest_df_param, df_xray):
    """Delegate to BacktestHandler.finish_backtest_data_cleanup()"""
    global defaultAnswer
    return _get_backtest_handler().finish_backtest_data_cleanup(backtest_df_param, df_xray, defaultAnswer)


def showSortedBacktestData(backtest_df_param, summary_df, sortKeys):
    """Delegate to BacktestHandler.show_sorted_backtest_data()"""
    global defaultAnswer
    return _get_backtest_handler().show_sorted_backtest_data(backtest_df_param, summary_df, sortKeys, defaultAnswer)


def labelDataForPrinting(screenResults_param, saveResults, configManager_param, volumeRatio, executeOption, reversalOption, menuOption):
    """Delegate to ResultsManager.label_data_for_printing()"""
    global menuChoiceHierarchy
    manager = _get_results_manager()
    manager.config_manager = configManager_param
    return manager.label_data_for_printing(
        screenResults_param, saveResults, volumeRatio,
        executeOption, reversalOption, menuOption, menuChoiceHierarchy
    )


def removeUnknowns(screenResults_param, saveResults):
    """Delegate to ResultsManager.remove_unknowns()"""
    return _get_results_manager().remove_unknowns(screenResults_param, saveResults)


def removedUnusedColumns(screenResults_param, saveResults, dropAdditionalColumns=None, userArgs=None):
    """Delegate to ResultsManager.remove_unused_columns()"""
    if dropAdditionalColumns is None:
        dropAdditionalColumns = []
    manager = _get_results_manager()
    manager.user_passed_args = userArgs
    return manager.remove_unused_columns(screenResults_param, saveResults, dropAdditionalColumns)


def saveScreenResultsEncoded(encodedText):
    """Delegate to ResultsManager.save_screen_results_encoded()"""
    return _get_results_manager().save_screen_results_encoded(encodedText)


def readScreenResultsDecoded(fileName=None):
    """Delegate to ResultsManager.read_screen_results_decoded()"""
    return _get_results_manager().read_screen_results_decoded(fileName)


def reformatTable(summaryText, headerDict, colored_text, sorting=True):
    """Delegate to ResultsManager.reformat_table_for_html()"""
    return _get_results_manager().reformat_table_for_html(summaryText, headerDict, colored_text, sorting)


def getLatestTradeDateTime(stockDictPrimary_param):
    """Delegate to ResultsManager.get_latest_trade_datetime()"""
    return _get_results_manager().get_latest_trade_datetime(stockDictPrimary_param)


def sendQuickScanResult(menuChoiceHierarchy_param, user, tabulated_results, markdown_results,
                        caption, pngName, pngExtension, addendum=None, addendumLabel=None,
                        backtestSummary="", backtestDetail="", summaryLabel=None,
                        detailLabel=None, legendPrefixText="", forceSend=False):
    """Delegate to TelegramNotifier.send_quick_scan_result()"""
    notifier = _get_telegram_notifier()
    notifier.send_quick_scan_result(
        menuChoiceHierarchy_param, user, tabulated_results, markdown_results,
        caption, pngName, pngExtension, addendum, addendumLabel,
        backtestSummary, backtestDetail, summaryLabel, detailLabel,
        legendPrefixText, forceSend
    )


def sendMessageToTelegramChannel(message=None, photo_filePath=None, document_filePath=None,
                                  caption=None, user=None, mediagroup=False):
    """Delegate to TelegramNotifier.send_message_to_telegram()"""
    global userPassedArgs, test_messages_queue, media_group_dict, menuChoiceHierarchy
    notifier = _get_telegram_notifier()
    notifier.user_passed_args = userPassedArgs
    notifier.test_messages_queue = test_messages_queue
    notifier.media_group_dict = media_group_dict
    notifier.send_message_to_telegram(message, photo_filePath, document_filePath, caption, user, mediagroup)


def sendTestStatus(screenResults_param, label, user=None):
    """Delegate to TelegramNotifier.send_test_status()"""
    _get_telegram_notifier().send_test_status(screenResults_param, label, user)


def sendGlobalMarketBarometer(userArgs=None):
    """Delegate to TelegramNotifier.send_global_market_barometer()"""
    notifier = _get_telegram_notifier()
    notifier.user_passed_args = userArgs
    notifier.send_global_market_barometer()


def handleAlertSubscriptions(user, message):
    """Delegate to TelegramNotifier._handle_alert_subscriptions()"""
    _get_telegram_notifier()._handle_alert_subscriptions(user, message)


# =============================================================================
# CORE APPLICATION FUNCTIONS
# These functions contain unique application logic and are not delegated
# =============================================================================

def startMarketMonitor(mp_dict, keyboardevent):
    """Start market monitoring."""
    if 'pytest' not in sys.modules:
        from PKDevTools.classes.NSEMarketStatus import NSEMarketStatus
        NSEMarketStatus(mp_dict, keyboardevent).startMarketMonitor()


def finishScreening(downloadOnly, testing, stockDictPrimary_param, configManager_param,
                    loadCount_param, testBuild, screenResults_param, saveResults, user=None):
    """Finish screening and save/notify results."""
    global defaultAnswer, menuChoiceHierarchy, userPassedArgs, selectedChoice
    if "RUNNER" not in os.environ.keys() or downloadOnly:
        saveDownloadedData(downloadOnly, testing, stockDictPrimary_param, configManager_param, loadCount_param)
    if not testBuild and not downloadOnly and not testing and ((userPassedArgs is not None and "|" not in userPassedArgs.options) or userPassedArgs is None):
        saveNotifyResultsFile(screenResults_param, saveResults, defaultAnswer, menuChoiceHierarchy, user=user)
    if ("RUNNER" in os.environ.keys() and not downloadOnly) or userPassedArgs.log:
        sendMessageToTelegramChannel(mediagroup=True, user=userPassedArgs.user)


def getDownloadChoices(defaultAnswer_param=None):
    """Get download choices for stock data."""
    global userPassedArgs
    argsIntraday = userPassedArgs is not None and userPassedArgs.intraday is not None
    intradayConfig = configManager.isIntradayConfig()
    intraday = intradayConfig or argsIntraday
    exists, cache_file = AssetsManager.PKAssetsManager.afterMarketStockDataExists(intraday)
    if exists:
        shouldReplace = AssetsManager.PKAssetsManager.promptFileExists(
            cache_file=cache_file, defaultAnswer=defaultAnswer_param
        )
        if shouldReplace == "N":
            OutputControls().printOutput(
                cache_file + colorText.END + " already exists. Exiting as user chose not to replace it!"
            )
            PKAnalyticsService().send_event("app_exit")
            sys.exit(0)
        else:
            pattern = f"{'intraday_' if intraday else ''}stock_data_*.pkl"
            configManager.deleteFileWithPattern(rootDir=Archiver.get_user_data_dir(), pattern=pattern)
    return "X", 12, 0, {"0": "X", "1": "12", "2": "0"}


def getTestBuildChoices(indexOption=None, executeOption=None, menuOption=None):
    """Get test build choices."""
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


def getTopLevelMenuChoices(startupoptions, testBuild, downloadOnly, defaultAnswer_param=None):
    """Get top level menu choices."""
    global selectedChoice, userPassedArgs, lastScanOutputStockCodes
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
        menuOption, indexOption, executeOption, selectedChoice = getTestBuildChoices(
            indexOption=indexOption, executeOption=executeOption, menuOption=menuOption
        )
    elif downloadOnly:
        menuOption, indexOption, executeOption, selectedChoice = getDownloadChoices(defaultAnswer=defaultAnswer_param)
        intraday = userPassedArgs.intraday or configManager.isIntradayConfig()
        filePrefix = "INTRADAY_" if intraday else ""
        _, cache_file_name = AssetsManager.PKAssetsManager.afterMarketStockDataExists(intraday)
        Utility.tools.set_github_output(f"{filePrefix}DOWNLOAD_CACHE_FILE_NAME", cache_file_name)
    indexOption = 0 if lastScanOutputStockCodes is not None else indexOption
    return options, menuOption, indexOption, executeOption


def handleScannerExecuteOption4(executeOption, options):
    """Handle scanner execute option 4."""
    global nValueForMenu
    try:
        if len(options) >= 4:
            if str(options[3]).upper() == "D":
                daysForLowestVolume = 5
            else:
                daysForLowestVolume = int(options[3])
        else:
            daysForLowestVolume = int(
                input(colorText.WARN + "\n  [+] The Volume should be lowest since last how many candles? (Default = 5)") or "5"
            )
    except ValueError as e:
        default_logger().debug(e, exc_info=True)
        OutputControls().printOutput(colorText.END)
        OutputControls().printOutput(colorText.FAIL + "  [+] Error: Non-numeric value entered! Please try again!" + colorText.END)
        OutputControls().takeUserInput("Press <Enter> to continue...")
        return
    OutputControls().printOutput(colorText.END)
    nValueForMenu = daysForLowestVolume
    return daysForLowestVolume


def isInterrupted():
    """Check if keyboard interrupt was fired."""
    global keyboardInterruptEventFired
    return keyboardInterruptEventFired


def resetUserMenuChoiceOptions():
    """Reset user menu choice options."""
    global menuChoiceHierarchy, userPassedArgs, media_group_dict
    media_group_dict = {}
    menuChoiceHierarchy = ""
    userPassedArgs.pipedtitle = ""


def ensureMenusLoaded(menuOption=None, indexOption=None, executeOption=None):
    """Ensure menus are loaded."""
    try:
        if len(m0.menuDict.keys()) == 0:
            m0.renderForMenu(asList=True)
        if len(m1.menuDict.keys()) == 0:
            m1.renderForMenu(selectedMenu=m0.find(menuOption), asList=True)
        if len(m2.menuDict.keys()) == 0:
            m2.renderForMenu(selectedMenu=m1.find(indexOption), asList=True)
        if len(m3.menuDict.keys()) == 0:
            m3.renderForMenu(selectedMenu=m2.find(executeOption), asList=True)
    except:
        pass


def handleExitRequest(executeOption):
    """Handle exit request."""
    if executeOption == "Z":
        OutputControls().takeUserInput(colorText.FAIL + "  [+] Press <Enter> to Exit!" + colorText.END)
        PKAnalyticsService().send_event("app_exit")
        sys.exit(0)


def handleMenu_XBG(menuOption, indexOption, executeOption):
    """Handle menu X, B, G options."""
    if menuOption in ["X", "B", "G", "C"]:
        selMenu = m0.find(menuOption)
        m1.renderForMenu(selMenu, asList=True)
        if indexOption is not None:
            selMenu = m1.find(indexOption)
            m2.renderForMenu(selMenu, asList=True)
            if executeOption is not None:
                selMenu = m2.find(executeOption)
                m3.renderForMenu(selMenu, asList=True)


def showOptionErrorMessage():
    """Show option error message."""
    OutputControls().printOutput(colorText.FAIL + "\n  [+] Please enter a valid option & try Again!" + colorText.END)
    sleep(2)
    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)


def toggleUserConfig():
    """Toggle user configuration between intraday and daily."""
    configManager.toggleConfig(candleDuration="1d" if configManager.isIntradayConfig() else "1m")
    OutputControls().printOutput(
        colorText.GREEN + "\nConfiguration toggled to duration: " + str(configManager.duration) +
        " and period: " + str(configManager.period) + colorText.END
    )
    input("\nPress <Enter> to Continue...\n")


def userReportName(userMenuOptions):
    """Generate user report name."""
    global userPassedArgs
    choices = ""
    for choice in userMenuOptions:
        if len(userMenuOptions[choice]) > 0:
            if len(choices) > 0:
                choices = f"{choices}_"
            choices = f"{choices}{userMenuOptions[choice]}"
    if choices.endswith("_"):
        choices = choices[:-1]
    choices = f"{choices}{'_i' if userPassedArgs.intraday else ''}"
    return choices


def getReviewDate(userPassedArgs_param=None):
    """Get review date."""
    reviewDate = PKDateUtilities.tradingDate().strftime('%Y-%m-%d')
    if userPassedArgs_param is not None and userPassedArgs_param.backtestdaysago is not None:
        reviewDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs_param.backtestdaysago))
    return reviewDate


def getMaxAllowedResultsCount(iterations, testing):
    """Get maximum allowed results count."""
    return iterations * (configManager.maxdisplayresults if userPassedArgs.maxdisplayresults is None else int(userPassedArgs.maxdisplayresults)) if not testing else 1


def getIterationsAndStockCounts(numStocks, iterations):
    """Get iterations and stock counts for processing."""
    if numStocks <= 2500:
        return 1, numStocks
    originalIterations = iterations
    idealNumStocksMaxPerIteration = 100
    iterations = int(numStocks * iterations / idealNumStocksMaxPerIteration) + 1
    numStocksPerIteration = int(numStocks / int(iterations))
    if numStocksPerIteration < 10:
        numStocksPerIteration = numStocks if (iterations == 1 or numStocks <= iterations) else int(numStocks / int(iterations))
        iterations = originalIterations
    if numStocksPerIteration > 500:
        numStocksPerIteration = 500
        iterations = int(numStocks / numStocksPerIteration) + 1
    return iterations, numStocksPerIteration


def processResults(menuOption, backtestPeriod, result, lstscreen, lstsave, backtest_df_param):
    """Process screening results."""
    if result is not None:
        lstscreen.append(result[0])
        lstsave.append(result[1])
        sampleDays = result[4]
        if menuOption == "B":
            backtest_df_param = updateBacktestResults(backtestPeriod, start_time, result, sampleDays, backtest_df_param)
    return backtest_df_param


# =============================================================================
# IMPORT REMAINING FUNCTIONS FROM ORIGINAL FILE
# The following functions are complex and contain unique application logic.
# They should be imported from the original module or kept inline.
# =============================================================================

# Import the remaining core functions that haven't been refactored yet
# These are kept for the application to function but can be further refactored

def getScannerMenuChoices(testBuild=False, downloadOnly=False, startupoptions=None,
                          menuOption=None, indexOption=None, executeOption=None,
                          defaultAnswer_param=None, user=None):
    """Get scanner menu choices from user."""
    global selectedChoice
    executeOption = executeOption
    menuOption = menuOption
    indexOption = indexOption
    try:
        if menuOption is None:
            selectedMenu = initExecution(menuOption=menuOption)
            menuOption = selectedMenu.menuKey
        if menuOption in ["H", "U", "T", "E", "Y"]:
            handleSecondaryMenuChoices(menuOption, testBuild, defaultAnswer=defaultAnswer_param, user=user)
            ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        elif menuOption in ["X", "C"]:
            indexOption, executeOption = initPostLevel0Execution(
                menuOption=menuOption, indexOption=indexOption, executeOption=executeOption
            )
            indexOption, executeOption = initPostLevel1Execution(indexOption=indexOption, executeOption=executeOption)
    except KeyboardInterrupt:
        OutputControls().takeUserInput(colorText.FAIL + "  [+] Press <Enter> to Exit!" + colorText.END)
        PKAnalyticsService().send_event("app_exit")
        sys.exit(0)
    except Exception as e:
        default_logger().debug(e, exc_info=True)
    return menuOption, indexOption, executeOption, selectedChoice


def handleSecondaryMenuChoices(menuOption, testing=False, defaultAnswer_param=None, user=None):
    """Handle secondary menu choices like Help, Update, etc."""
    global userPassedArgs
    if menuOption == "H":
        showSendHelpInfo(defaultAnswer_param, user)
    elif menuOption == "U":
        OTAUpdater.checkForUpdate(VERSION, skipDownload=testing)
        if defaultAnswer_param is None:
            OutputControls().takeUserInput("Press <Enter> to continue...")
    elif menuOption == "T":
        _handleTimePeriodMenu(defaultAnswer_param)
    elif menuOption == "E":
        configManager.setConfig(ConfigManager.parser)
    elif menuOption == "Y":
        showSendConfigInfo(defaultAnswer_param, user)
    return


def _handleTimePeriodMenu(defaultAnswer_param):
    """Handle time period menu selection."""
    global userPassedArgs, resultsContentsEncoded
    if userPassedArgs is None or userPassedArgs.options is None:
        selectedMenu = m0.find("T")
        m1.renderForMenu(selectedMenu=selectedMenu)
        periodOption = input(colorText.FAIL + "  [+] Select option: ") or ('L' if configManager.period == '1y' else 'S')
        OutputControls().printOutput(colorText.END, end="")
        if periodOption is None or periodOption.upper() not in ["L", "S", "B"]:
            return
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        if periodOption.upper() in ["L", "S"]:
            selectedMenu = m1.find(periodOption)
            m2.renderForMenu(selectedMenu=selectedMenu)
            durationOption = input(colorText.FAIL + "  [+] Select option: ") or "1"
            OutputControls().printOutput(colorText.END, end="")
            if durationOption is None or durationOption.upper() not in ["1", "2", "3", "4", "5"]:
                return
            ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
            if durationOption.upper() in ["1", "2", "3", "4"]:
                selectedMenu = m2.find(durationOption)
                periodDurations = selectedMenu.menuText.split("(")[1].split(")")[0].split(", ")
                configManager.period = periodDurations[0]
                configManager.duration = periodDurations[1]
                configManager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
                configManager.deleteFileWithPattern(rootDir=Archiver.get_user_data_dir(), pattern="*stock_data_*.pkl*")
            elif durationOption.upper() in ["5"]:
                configManager.setConfig(ConfigManager.parser, default=False, showFileCreatedText=True)
                configManager.deleteFileWithPattern(rootDir=Archiver.get_user_data_dir(), pattern="*stock_data_*.pkl*")
            return
        elif periodOption.upper() in ["B"]:
            _handleBacktestMode()
    elif userPassedArgs is not None and userPassedArgs.options is not None:
        options = userPassedArgs.options.split(":")
        selectedMenu = m0.find(options[0])
        m1.renderForMenu(selectedMenu=selectedMenu, asList=True)
        selectedMenu = m1.find(options[1])
        m2.renderForMenu(selectedMenu=selectedMenu, asList=True)
        if options[2] in ["1", "2", "3", "4"]:
            selectedMenu = m2.find(options[2])
            periodDurations = selectedMenu.menuText.split("(")[1].split(")")[0].split(", ")
            configManager.period = periodDurations[0]
            configManager.duration = periodDurations[1]
            configManager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
        else:
            toggleUserConfig()
    else:
        toggleUserConfig()


def _handleBacktestMode():
    """Handle backtest mode selection."""
    global userPassedArgs, resultsContentsEncoded
    lastTradingDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(n=(22 if configManager.period == '1y' else 15))
    backtestDaysAgo = input(
        f"{colorText.FAIL}  [+] Enter no. of days/candles in the past as starting candle for which you'd like to run the scans\n"
        f"  [+] You can also enter a past date in {colorText.END}{colorText.GREEN}YYYY-MM-DD{colorText.END}{colorText.FAIL} format\n"
        f"  [+] (e.g. {colorText.GREEN}10{colorText.END} for 10 candles ago or {colorText.GREEN}0{colorText.END} for today or "
        f"{colorText.GREEN}{lastTradingDate}{colorText.END}):"
    ) or ('22' if configManager.period == '1y' else '15')
    OutputControls().printOutput(colorText.END, end="")
    if len(str(backtestDaysAgo)) >= 3 and "-" in str(backtestDaysAgo):
        try:
            backtestDaysAgo = abs(PKDateUtilities.trading_days_between(
                d1=PKDateUtilities.dateFromYmdString(str(backtestDaysAgo)),
                d2=PKDateUtilities.currentDateTime()
            ))
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput("An error occurred! Going ahead with default inputs.")
            backtestDaysAgo = ('22' if configManager.period == '1y' else '15')
            sleep(3)
    
    launcher = f'"{sys.argv[0]}"' if " " in sys.argv[0] else sys.argv[0]
    requestingUser = f" -u {userPassedArgs.user}" if userPassedArgs.user is not None else ""
    enableLog = " -l" if userPassedArgs.log else ""
    enableTelegramMode = " --telegram" if userPassedArgs is not None and userPassedArgs.telegram else ""
    stockListParam = f" --stocklist {userPassedArgs.stocklist}" if userPassedArgs.stocklist else ""
    slicewindowParam = f" --slicewindow {userPassedArgs.slicewindow}" if userPassedArgs.slicewindow else ""
    fnameParam = f" --fname {resultsContentsEncoded}" if resultsContentsEncoded else ""
    launcher = f"python3.12 {launcher}" if (launcher.endswith('.py"') or launcher.endswith(".py")) else launcher
    
    OutputControls().printOutput(
        f"{colorText.GREEN}Launching PKScreener in quick backtest mode. If it does not launch, please try with the following:{colorText.END}\n"
        f"{colorText.FAIL}{launcher} --backtestdaysago {int(backtestDaysAgo)}{requestingUser}{enableLog}{enableTelegramMode}"
        f"{stockListParam}{slicewindowParam}{fnameParam}{colorText.END}\n"
        f"{colorText.WARN}Press Ctrl + C to exit quick backtest mode.{colorText.END}"
    )
    sleep(2)
    os.system(f"{launcher} --systemlaunched -a Y -e --backtestdaysago {int(backtestDaysAgo)}{requestingUser}{enableLog}"
              f"{enableTelegramMode}{stockListParam}{slicewindowParam}{fnameParam}")
    ConsoleUtility.PKConsoleTools.clearScreen(clearAlways=True, forceTop=True)


def showSendConfigInfo(defaultAnswer_param=None, user=None):
    """Show and send config info."""
    configData = configManager.showConfigFile(defaultAnswer=('Y' if user is not None else defaultAnswer_param))
    if user is not None:
        sendMessageToTelegramChannel(message=ImageUtility.PKImageTools.removeAllColorStyles(configData), user=user)
    if defaultAnswer_param is None:
        input("Press any key to continue...")


def showSendHelpInfo(defaultAnswer_param=None, user=None):
    """Show and send help info."""
    helpData = ConsoleUtility.PKConsoleTools.showDevInfo(defaultAnswer=('Y' if user is not None else defaultAnswer_param))
    if user is not None:
        sendMessageToTelegramChannel(message=ImageUtility.PKImageTools.removeAllColorStyles(helpData), user=user)
    if defaultAnswer_param is None:
        input("Press any key to continue...")


def initExecution(menuOption=None):
    """Initialize execution by showing main menu."""
    global selectedChoice, userPassedArgs
    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
    if userPassedArgs is not None and userPassedArgs.pipedmenus is not None:
        OutputControls().printOutput(
            colorText.FAIL + "  [+] You chose: " + f" (Piped Scan Mode) [{userPassedArgs.pipedmenus}]" + colorText.END
        )
    m0.renderForMenu(selectedMenu=None, asList=(userPassedArgs is not None and userPassedArgs.options is not None))
    try:
        needsCalc = userPassedArgs is not None and userPassedArgs.backtestdaysago is not None
        pastDate = (f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}"
                   f"{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs.backtestdaysago) if needsCalc else 0)}"
                   f"{colorText.END} ]\n" if needsCalc else "")
        if menuOption is None:
            if "PKDevTools_Default_Log_Level" in os.environ.keys():
                from PKDevTools.classes import Archiver
                log_file_path = os.path.join(Archiver.get_user_data_dir(), "pkscreener-logs.txt")
                OutputControls().printOutput(colorText.FAIL + "\n      [+] Logs will be written to:" + colorText.END)
                OutputControls().printOutput(colorText.GREEN + f"      [+] {log_file_path}" + colorText.END)
                OutputControls().printOutput(colorText.FAIL + "      [+] If you need to share, run through the menus that are causing problems. At the end, open this folder, zip the log file to share at https://github.com/pkjmesra/PKScreener/issues .\n" + colorText.END)
            menuOption = input(colorText.FAIL + f"{pastDate}  [+] Select option: ") or "P"
            OutputControls().printOutput(colorText.END, end="")
        if menuOption == "" or menuOption is None:
            menuOption = "X"
        menuOption = menuOption.upper()
        selectedMenu = m0.find(menuOption)
        if selectedMenu is not None:
            if selectedMenu.menuKey == "Z":
                OutputControls().takeUserInput(colorText.FAIL + "  [+] Press <Enter> to Exit!" + colorText.END)
                PKAnalyticsService().send_event("app_exit")
                sys.exit(0)
            elif selectedMenu.menuKey in ["B", "C", "G", "H", "U", "T", "S", "E", "X", "Y", "M", "D", "I", "L", "F"]:
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                selectedChoice["0"] = selectedMenu.menuKey
                return selectedMenu
            elif selectedMenu.menuKey in ["P"]:
                return selectedMenu
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        default_logger().debug(e, exc_info=True)
        showOptionErrorMessage()
        return initExecution()
    showOptionErrorMessage()
    return initExecution()


def initPostLevel0Execution(menuOption=None, indexOption=None, executeOption=None, skip=None, retrial=False):
    """Initialize post level 0 execution."""
    global newlyListedOnly, selectedChoice, userPassedArgs
    if skip is None:
        skip = []
    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
    if menuOption is None:
        OutputControls().printOutput('You must choose an option from the previous menu! Defaulting to "X"...')
        menuOption = "X"
    OutputControls().printOutput(
        colorText.FAIL + "  [+] You chose: " + level0MenuDict[menuOption].strip() +
        (f" (Piped Scan Mode) [{userPassedArgs.pipedmenus}]" if (userPassedArgs is not None and userPassedArgs.pipedmenus is not None) else "") +
        colorText.END
    )
    if indexOption is None:
        selectedMenu = m0.find(menuOption)
        m1.renderForMenu(selectedMenu=selectedMenu, skip=skip, asList=(userPassedArgs is not None and userPassedArgs.options is not None))
    try:
        needsCalc = userPassedArgs is not None and userPassedArgs.backtestdaysago is not None
        pastDate = (f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}"
                   f"{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs.backtestdaysago) if needsCalc else 0)}"
                   f"{colorText.END} ]\n" if needsCalc else "")
        if indexOption is None:
            indexOption = OutputControls().takeUserInput(colorText.FAIL + f"{pastDate}  [+] Select option: ")
            OutputControls().printOutput(colorText.END, end="")
        if ((str(indexOption).isnumeric() and int(indexOption) > 1 and str(executeOption).isnumeric() and int(str(executeOption)) <= MAX_SUPPORTED_MENU_OPTION) or
            str(indexOption).upper() in ["S", "E", "W"]):
            ensureMenusLoaded(menuOption, indexOption, executeOption)
            if not PKPremiumHandler.hasPremium(m1.find(str(indexOption).upper())):
                PKAnalyticsService().send_event(f"non_premium_user_{menuOption}_{indexOption}_{executeOption}")
                return None, None
        if indexOption == "" or indexOption is None:
            indexOption = int(configManager.defaultIndex)
        elif not str(indexOption).isnumeric():
            indexOption = indexOption.upper()
            if indexOption in ["M", "E", "N", "Z"]:
                return indexOption, 0
        else:
            indexOption = int(indexOption)
            if indexOption < 0 or indexOption > 15:
                raise ValueError
            elif indexOption == 13:
                configManager.period = "2y"
                configManager.getConfig(ConfigManager.parser)
                newlyListedOnly = True
                indexOption = 12
        if indexOption == 15:
            from pkscreener.classes.MarketStatus import MarketStatus
            MarketStatus().exchange = "^IXIC"
        selectedChoice["1"] = str(indexOption)
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        default_logger().debug(e, exc_info=True)
        OutputControls().printOutput(colorText.FAIL + "\n  [+] Please enter a valid numeric option & Try Again!" + colorText.END)
        if not retrial:
            sleep(2)
            ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
            return initPostLevel0Execution(retrial=True)
    return indexOption, executeOption


def initPostLevel1Execution(indexOption, executeOption=None, skip=None, retrial=False):
    """Initialize post level 1 execution."""
    global selectedChoice, userPassedArgs, listStockCodes
    if skip is None:
        skip = []
    listStockCodes = [] if listStockCodes is None or len(listStockCodes) == 0 else listStockCodes
    if executeOption is None:
        if indexOption is not None and indexOption != "W":
            ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
            OutputControls().printOutput(
                colorText.FAIL + "  [+] You chose: " + level0MenuDict[selectedChoice["0"]].strip() + " > " +
                level1_X_MenuDict[selectedChoice["1"]].strip() +
                (f" (Piped Scan Mode) [{userPassedArgs.pipedmenus}]" if (userPassedArgs is not None and userPassedArgs.pipedmenus is not None) else "") +
                colorText.END
            )
            selectedMenu = m1.find(indexOption)
            m2.renderForMenu(selectedMenu=selectedMenu, skip=skip, asList=(userPassedArgs is not None and userPassedArgs.options is not None))
            stockIndexCode = str(len(level1_index_options_sectoral.keys()))
            if indexOption == "S":
                ensureMenusLoaded("X", indexOption, executeOption)
                if not PKPremiumHandler.hasPremium(selectedMenu):
                    PKAnalyticsService().send_event(f"non_premium_user_X_{indexOption}_{executeOption}")
                    PKAnalyticsService().send_event("app_exit")
                    sys.exit(0)
                indexKeys = level1_index_options_sectoral.keys()
                stockIndexCode = input(colorText.FAIL + "  [+] Select option: ") or str(len(indexKeys))
                OutputControls().printOutput(colorText.END, end="")
                if stockIndexCode == str(len(indexKeys)):
                    for indexCode in indexKeys:
                        if indexCode != str(len(indexKeys)):
                            listStockCodes.append(level1_index_options_sectoral[str(indexCode)].split("(")[1].split(")")[0])
                else:
                    listStockCodes = [level1_index_options_sectoral[str(stockIndexCode)].split("(")[1].split(")")[0]]
                selectedMenu.menuKey = "0"
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                m2.renderForMenu(selectedMenu=selectedMenu, skip=skip, asList=(userPassedArgs is not None and userPassedArgs.options is not None))
    try:
        needsCalc = userPassedArgs is not None and userPassedArgs.backtestdaysago is not None
        pastDate = (f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}"
                   f"{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs.backtestdaysago) if needsCalc else 0)}"
                   f"{colorText.END} ]\n" if needsCalc else "")
        if indexOption is not None and indexOption != "W":
            if executeOption is None:
                executeOption = input(colorText.FAIL + f"{pastDate}  [+] Select option: ") or "9"
                OutputControls().printOutput(colorText.END, end="")
            ensureMenusLoaded("X", indexOption, executeOption)
            if not PKPremiumHandler.hasPremium(m2.find(str(executeOption))):
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
        selectedChoice["2"] = str(executeOption)
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as e:
        default_logger().debug(e, exc_info=True)
        OutputControls().printOutput(colorText.FAIL + "\n  [+] Please enter a valid numeric option & Try Again!" + colorText.END)
        if not retrial:
            sleep(2)
            ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
            return initPostLevel1Execution(indexOption, executeOption, retrial=True)
    return indexOption, executeOption


def updateMenuChoiceHierarchy():
    """Update menu choice hierarchy string."""
    global userPassedArgs, selectedChoice, menuChoiceHierarchy, nValueForMenu
    try:
        menuChoiceHierarchy = f'{level0MenuDict[selectedChoice["0"]].strip()}'
        topLevelMenuDict = level1_X_MenuDict if selectedChoice["0"] not in "P" else level1_P_MenuDict
        level2MenuDict = level2_X_MenuDict if selectedChoice["0"] not in "P" else level2_P_MenuDict
        if len(selectedChoice["1"]) > 0:
            menuChoiceHierarchy = f'{menuChoiceHierarchy}>{topLevelMenuDict[selectedChoice["1"]].strip()}'
        if len(selectedChoice["2"]) > 0:
            menuChoiceHierarchy = f'{menuChoiceHierarchy}>{level2MenuDict[selectedChoice["2"]].strip()}'
        if selectedChoice["0"] not in "P":
            _updateSubMenuHierarchy()
        intraday = "(Intraday)" if ("Intraday" not in menuChoiceHierarchy and ((userPassedArgs is not None and userPassedArgs.intraday) or configManager.isIntradayConfig())) else ""
        menuChoiceHierarchy = f"{menuChoiceHierarchy}{intraday}"
        menuChoiceHierarchy = menuChoiceHierarchy.replace("N-", f"{nValueForMenu}-")
    except:
        pass
    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
    needsCalc = userPassedArgs is not None and userPassedArgs.backtestdaysago is not None
    pastDate = f"[ {PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs.backtestdaysago) if needsCalc else 0)} ]" if needsCalc else ""
    reportTitle = f"{userPassedArgs.pipedtitle}|" if userPassedArgs is not None and userPassedArgs.pipedtitle is not None else ""
    runOptionName = PKScanRunner.getFormattedChoices(userPassedArgs, selectedChoice)
    if ((":0:" in runOptionName or "_0_" in runOptionName) and userPassedArgs.progressstatus is not None) or userPassedArgs.progressstatus is not None:
        runOptionName = userPassedArgs.progressstatus.split("=>")[0].split("  [+] ")[1].strip()
    reportTitle = f"{runOptionName} | {reportTitle}" if runOptionName is not None else reportTitle
    if len(runOptionName) >= 5:
        PKAnalyticsService().send_event(runOptionName)
    OutputControls().printOutput(
        colorText.FAIL + f"  [+] You chose: {reportTitle} " + menuChoiceHierarchy +
        (f" (Piped Scan Mode) [{userPassedArgs.pipedmenus}] {pastDate}" if (userPassedArgs is not None and userPassedArgs.pipedmenus is not None) else "") +
        colorText.END
    )
    default_logger().info(menuChoiceHierarchy)
    return menuChoiceHierarchy


def _updateSubMenuHierarchy():
    """Update submenu hierarchy."""
    global menuChoiceHierarchy, selectedChoice
    if selectedChoice["2"] == "6":
        menuChoiceHierarchy = menuChoiceHierarchy + f'>{level3_X_Reversal_MenuDict[selectedChoice["3"]].strip()}'
        if len(selectedChoice) >= 5 and selectedChoice["3"] in ["7", "10"]:
            menuChoiceHierarchy = menuChoiceHierarchy + f'>{level4_X_Lorenzian_MenuDict[selectedChoice["4"]].strip()}'
    elif selectedChoice["2"] in ["30"]:
        if len(selectedChoice) >= 3:
            menuChoiceHierarchy = menuChoiceHierarchy + f'>{level4_X_Lorenzian_MenuDict[selectedChoice["3"]].strip()}'
    elif selectedChoice["2"] == "7":
        menuChoiceHierarchy = menuChoiceHierarchy + f'>{level3_X_ChartPattern_MenuDict[selectedChoice["3"]].strip()}'
        if len(selectedChoice) >= 5 and selectedChoice["3"] == "3":
            menuChoiceHierarchy = menuChoiceHierarchy + f'>{level4_X_ChartPattern_Confluence_MenuDict[selectedChoice["4"]].strip()}'
        elif len(selectedChoice) >= 5 and selectedChoice["3"] == "6":
            menuChoiceHierarchy = menuChoiceHierarchy + f'>{level4_X_ChartPattern_BBands_SQZ_MenuDict[selectedChoice["4"]].strip()}'
        elif len(selectedChoice) >= 5 and selectedChoice["3"] == "9":
            menuChoiceHierarchy = menuChoiceHierarchy + f'>{level4_X_ChartPattern_MASignalMenuDict[selectedChoice["4"]].strip()}'
        elif len(selectedChoice) >= 5 and selectedChoice["3"] == "7":
            menuChoiceHierarchy = menuChoiceHierarchy + f'>{CANDLESTICK_DICT[selectedChoice["4"]].strip() if selectedChoice["4"] != 0 else "No Filter"}'
    elif selectedChoice["2"] == "21":
        menuChoiceHierarchy = menuChoiceHierarchy + f'>{level3_X_PopularStocks_MenuDict[selectedChoice["3"]].strip()}'
    elif selectedChoice["2"] == "33":
        menuChoiceHierarchy = menuChoiceHierarchy + f'>{level3_X_PotentialProfitable_MenuDict[selectedChoice["3"]].strip()}'
    elif selectedChoice["2"] == "40":
        menuChoiceHierarchy = menuChoiceHierarchy + f'>{PRICE_CROSS_SMA_EMA_DIRECTION_MENUDICT[selectedChoice["3"]].strip()}'
        menuChoiceHierarchy = menuChoiceHierarchy + f'>{PRICE_CROSS_SMA_EMA_TYPE_MENUDICT[selectedChoice["4"]].strip()}'
    elif selectedChoice["2"] == "41":
        menuChoiceHierarchy = menuChoiceHierarchy + f'>{PRICE_CROSS_PIVOT_POINT_TYPE_MENUDICT[selectedChoice["3"]].strip()}'
        menuChoiceHierarchy = menuChoiceHierarchy + f'>{PRICE_CROSS_SMA_EMA_DIRECTION_MENUDICT[selectedChoice["4"]].strip()}'


# =============================================================================
# STUB FOR MAIN FUNCTION
# The main() function and other complex functions should be imported from
# the MenuManager class or kept in a separate module. For now, we provide
# stubs that reference the original implementations.
# =============================================================================

# Note: The main() function and other complex scanning/processing functions
# are extensive and should be kept in the MenuManager class or refactored
# into a dedicated ScanCoordinator class.

# For backward compatibility, you can import the full main() function
# from the MenuManager module if needed:
# from pkscreener.classes.MenuManager import main

# The functions below are stubs - implement or import as needed
def saveDownloadedData(downloadOnly, testing, stockDictPrimary_param, configManager_param, loadCount_param):
    """Save downloaded stock data."""
    global userPassedArgs, keyboardInterruptEventFired, download_trials
    argsIntraday = userPassedArgs is not None and userPassedArgs.intraday is not None
    intradayConfig = configManager_param.isIntradayConfig()
    intraday = intradayConfig or argsIntraday
    if not keyboardInterruptEventFired and (downloadOnly or (configManager_param.cacheEnabled and not PKDateUtilities.isTradingTime() and not testing)):
        OutputControls().printOutput(colorText.GREEN + "  [+] Caching Stock Data for future use, Please Wait... " + colorText.END, end="")
        AssetsManager.PKAssetsManager.saveStockData(stockDictPrimary_param, configManager_param, loadCount_param, intraday)
        if downloadOnly:
            cache_file = AssetsManager.PKAssetsManager.saveStockData(stockDictPrimary_param, configManager_param, loadCount_param, intraday, downloadOnly=downloadOnly)
            cacheFileSize = os.stat(cache_file).st_size if os.path.exists(cache_file) else 0
            if cacheFileSize < 1024 * 1024 * 40:
                try:
                    from PKDevTools.classes import Archiver
                    log_file_path = os.path.join(Archiver.get_user_data_dir(), "pkscreener-logs.txt")
                    message = f"{cache_file} has size: {cacheFileSize}! Something is wrong!"
                    if os.path.exists(log_file_path):
                        sendMessageToTelegramChannel(caption=message, document_filePath=log_file_path, user=DEV_CHANNEL_ID)
                    else:
                        sendMessageToTelegramChannel(message=message, user=DEV_CHANNEL_ID)
                except:
                    pass
                if "PKDevTools_Default_Log_Level" not in os.environ.keys():
                    launcher = f'"{sys.argv[0]}"' if " " in sys.argv[0] else sys.argv[0]
                    launcher = f"python3.12 {launcher}" if (launcher.endswith('.py"') or launcher.endswith(".py")) else launcher
                    os.system(f"{launcher} -a Y -e -l -d {'-i 1m' if configManager_param.isIntradayConfig() else ''}")
                else:
                    del os.environ['PKDevTools_Default_Log_Level']
                    PKAnalyticsService().send_event("app_exit")
                    sys.exit(0)
    else:
        OutputControls().printOutput(colorText.GREEN + "  [+] Skipped Saving!" + colorText.END)


def saveNotifyResultsFile(screenResults_param, saveResults, defaultAnswer_param, menuChoiceHierarchy_param, user=None):
    """Save and notify results file."""
    global userPassedArgs, elapsed_time, selectedChoice, media_group_dict, criteria_dateTime
    if user is None and userPassedArgs.user is not None:
        user = userPassedArgs.user
    if ">|" in userPassedArgs.options and not configManager.alwaysExportToExcel:
        return
    caption = f'<b>{menuChoiceHierarchy_param.split(">")[-1]}</b>'
    if screenResults_param is not None and len(screenResults_param) >= 1:
        choices = PKScanRunner.getFormattedChoices(userPassedArgs, selectedChoice)
        if userPassedArgs.progressstatus is not None:
            choices = userPassedArgs.progressstatus.split("=>")[0].split("  [+] ")[1]
        choices = f'{choices.strip()}{"_IA" if userPassedArgs is not None and userPassedArgs.runintradayanalysis else ""}'
        needsCalc = userPassedArgs is not None and userPassedArgs.backtestdaysago is not None
        pastDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs.backtestdaysago) if needsCalc else 0) if needsCalc else None
        filename = PKAssetsManager.promptSaveResults(choices, saveResults, defaultAnswer=defaultAnswer_param, pastDate=pastDate, screenResults=screenResults_param)
        if filename is not None:
            if "ATTACHMENTS" not in media_group_dict.keys():
                media_group_dict["ATTACHMENTS"] = []
            caption = media_group_dict["CAPTION"] if "CAPTION" in media_group_dict.keys() else menuChoiceHierarchy_param
            media_group_dict["ATTACHMENTS"].append({"FILEPATH": filename, "CAPTION": caption.replace('&', 'n')})
        OutputControls().printOutput(
            colorText.WARN +
            f"  [+] Notes:\n  [+] 1.Trend calculation is based on 'daysToLookBack'. See configuration.\n"
            f"  [+] 2.Reduce the console font size to fit all columns on screen.\n"
            f"  [+] Standard data columns were hidden: {configManager.alwaysHiddenDisplayColumns}. "
            f"If you want, you can change this in pkscreener.ini" +
            colorText.END
        )
    if userPassedArgs.monitor is None:
        needsCalc = userPassedArgs is not None and userPassedArgs.backtestdaysago is not None
        pastDate = PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(userPassedArgs.backtestdaysago) if needsCalc else 0) if criteria_dateTime is None else criteria_dateTime
        if userPassedArgs.triggertimestamp is None:
            userPassedArgs.triggertimestamp = int(PKDateUtilities.currentDateTimestamp())
        OutputControls().printOutput(
            colorText.GREEN +
            f"  [+] Screening Completed. Found {len(screenResults_param) if screenResults_param is not None else 0} results in "
            f"{round(elapsed_time, 2)} sec. for {colorText.END}{colorText.FAIL}{pastDate}{colorText.END}{colorText.GREEN}. "
            f"Queue Wait Time:{int(PKDateUtilities.currentDateTimestamp() - userPassedArgs.triggertimestamp - round(elapsed_time, 2))}s! "
            f"Press Enter to Continue.." +
            colorText.END,
            enableMultipleLineOutput=True
        )
        if defaultAnswer_param is None:
            OutputControls().takeUserInput("Press <Enter> to continue...")


def resetConfigToDefault(force=False):
    """Reset configuration to default."""
    global userPassedArgs
    if userPassedArgs is not None and userPassedArgs.monitor is None:
        if "PKDevTools_Default_Log_Level" in os.environ.keys():
            if userPassedArgs is None or (userPassedArgs is not None and userPassedArgs.options is not None and "|" not in userPassedArgs.options and not userPassedArgs.runintradayanalysis and userPassedArgs.pipedtitle is None):
                del os.environ['PKDevTools_Default_Log_Level']
        configManager.logsEnabled = False
    if force:
        configManager.logsEnabled = False
    configManager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)


def cleanupLocalResults():
    """Cleanup local results."""
    global userPassedArgs, runCleanUp
    runCleanUp = True
    if userPassedArgs.answerdefault is not None or userPassedArgs.systemlaunched or userPassedArgs.testbuild:
        return
    from PKDevTools.classes.NSEMarketStatus import NSEMarketStatus
    if not NSEMarketStatus().shouldFetchNextBell()[0]:
        return
    launcher = f'"{sys.argv[0]}"' if " " in sys.argv[0] else sys.argv[0]
    shouldPrompt = (launcher.endswith('.py"') or launcher.endswith(".py")) and (userPassedArgs is None or userPassedArgs.answerdefault is None)
    response = "N"
    if shouldPrompt:
        response = input(f"  [+] {colorText.WARN}Clean up local non-essential system generated data?{colorText.END}{colorText.FAIL}[Default: {response}]{colorText.END}\n    (User generated reports won't be deleted.)        :") or response
    if "y" in response.lower():
        dirs = [Archiver.get_user_data_dir(), Archiver.get_user_cookies_dir(), Archiver.get_user_temp_dir(), Archiver.get_user_indices_dir()]
        for dir_path in dirs:
            configManager.deleteFileWithPattern(rootDir=dir_path, pattern="*")
        response = input(f"\n  [+] {colorText.WARN}Clean up local user generated reports as well?{colorText.END} {colorText.FAIL}[Default: N]{colorText.END} :") or "n"
        if "y" in response.lower():
            configManager.deleteFileWithPattern(rootDir=Archiver.get_user_reports_dir(), pattern="*.*")
    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)


# =============================================================================
# CORE FUNCTIONS REQUIRED FOR BACKWARD COMPATIBILITY
# =============================================================================

def closeWorkersAndExit():
    """Close all worker processes and exit gracefully."""
    global tasks_queue, consumers, userPassedArgs
    try:
        if consumers is not None:
            PKScanRunner.terminateAllWorkers(
                userPassedArgs=userPassedArgs, 
                consumers=consumers, 
                tasks_queue=tasks_queue, 
                testing=userPassedArgs.testbuild if userPassedArgs else False
            )
    except Exception as e:
        default_logger().debug(e, exc_info=True)
        pass
    finally:
        tasks_queue = None
        consumers = None


def refreshStockData(options=None):
    """
    Refresh stock data by clearing loaded data flag.
    Forces a fresh data load on next scan.
    
    Args:
        options: Options string for the scan
    """
    global loadedStockData, stockDictPrimary, stockDictSecondary
    loadedStockData = False
    stockDictPrimary = None
    stockDictSecondary = None


def main(userArgs=None, optionalFinalOutcome_df=None):
    """
    Main entry point for PKScreener application.
    
    This function orchestrates the entire screening process by initializing
    state, handling menu navigation, executing scans, and processing results.
    
    Args:
        userArgs: User arguments passed to the application
        optionalFinalOutcome_df: Optional final outcome dataframe for intraday analysis
        
    Returns:
        tuple: (screenResults, saveResults) dataframes
    """
    global userPassedArgs, defaultAnswer, selectedChoice, menuChoiceHierarchy
    global screenResults, backtest_df, screenCounter, screenResultsCounter
    global stockDictPrimary, stockDictSecondary, loadedStockData, loadCount
    global keyboardInterruptEvent, keyboardInterruptEventFired, newlyListedOnly
    global mp_manager, tasks_queue, results_queue, consumers, logging_queue
    global elapsed_time, start_time, scanCycleRunning, listStockCodes
    global analysis_dict, criteria_dateTime, strategyFilter, test_messages_queue
    global show_saved_diff_results, lastScanOutputStockCodes, media_group_dict
    global maLength, nValueForMenu, m0, m1, m2, m3, m4
    
    # Initialize state from user arguments
    userPassedArgs = userArgs
    defaultAnswer = None if userArgs is None else userArgs.answerdefault
    testing = False if userArgs is None else (userArgs.testbuild and userArgs.prodbuild)
    testBuild = False if userArgs is None else (userArgs.testbuild and not testing)
    downloadOnly = False if userArgs is None else userArgs.download
    startupoptions = None if userArgs is None else userArgs.options
    user = None if userArgs is None else userArgs.user
    
    # Check for keyboard interrupt
    if keyboardInterruptEventFired:
        return None, None
    
    # Initialize multiprocessing components
    if mp_manager is None and not testing:
        mp_manager = multiprocessing.Manager()
    
    if keyboardInterruptEvent is None and not testing:
        keyboardInterruptEvent = mp_manager.Event()
    
    # Initialize screen counters
    screenCounter = multiprocessing.Value("i", 1)
    screenResultsCounter = multiprocessing.Value("i", 0)
    
    # Initialize dataframes
    screenResults, saveResults = PKScanRunner.initDataframes()
    
    # Reset selected choice
    selectedChoice = {"0": "", "1": "", "2": "", "3": "", "4": ""}
    
    # Get top level menu choices
    options, menuOption, indexOption, executeOption = getTopLevelMenuChoices(
        startupoptions, testBuild, downloadOnly, defaultAnswer_param=defaultAnswer
    )
    
    # Initialize execution
    try:
        selectedMenu = initExecution(menuOption=menuOption)
        if selectedMenu is None:
            return None, None
        menuOption = selectedMenu.menuKey
    except KeyboardInterrupt:
        return None, None
    except Exception as e:
        default_logger().debug(e, exc_info=True)
        return None, None
    
    # Handle secondary menu choices (Help, Update, Config, etc.)
    if menuOption in ["H", "U", "T", "E", "Y"]:
        handleSecondaryMenuChoices(menuOption, testBuild, defaultAnswer_param=defaultAnswer, user=user)
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        return None, None
    
    # Handle exit request
    if menuOption == "Z":
        handleExitRequest(menuOption)
        return None, None
    
    # Handle scanner menu choices
    if menuOption in ["X", "C"]:
        menuOption, indexOption, executeOption, selectedChoice = getScannerMenuChoices(
            testBuild, downloadOnly, startupoptions,
            menuOption=menuOption, indexOption=indexOption, executeOption=executeOption,
            defaultAnswer_param=defaultAnswer, user=user
        )
    
    # Handle menu options
    handleMenu_XBG(menuOption, indexOption, executeOption)
    
    # Check for return to main menu
    if str(indexOption).upper() == "M" or str(executeOption).upper() == "M":
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        return None, None
    
    # Handle exit request for executeOption
    handleExitRequest(executeOption)
    
    if executeOption is None:
        executeOption = 0
    
    try:
        executeOption = int(executeOption)
    except:
        executeOption = 0
    
    # Update menu choice hierarchy for display
    menuChoiceHierarchy = updateMenuChoiceHierarchy()
    
    # Mark start time
    start_time = time.time()
    scanCycleRunning = True
    
    # Record start for timing
    elapsed_time = 0
    
    # Run the scan
    try:
        from pkscreener.classes.PKScreenerMain import PKScreenerMain
        screener = PKScreenerMain()
        screenResults, saveResults = screener.main(userArgs=userArgs, optionalFinalOutcome_df=optionalFinalOutcome_df)
    except ImportError:
        # Fallback to basic screening if PKScreenerMain is not available
        OutputControls().printOutput(
            colorText.FAIL + "  [+] PKScreenerMain module not available. Please check installation." + colorText.END
        )
        return None, None
    except Exception as e:
        default_logger().debug(e, exc_info=True)
        OutputControls().printOutput(
            colorText.FAIL + f"  [+] Error during screening: {e}" + colorText.END
        )
        return None, None
    finally:
        elapsed_time = time.time() - start_time
        scanCycleRunning = False
    
    return screenResults, saveResults


# =============================================================================
# END OF REFACTORED GLOBALS MODULE
# =============================================================================
# This module maintains backward compatibility by exposing the same API as
# the original globals.py while delegating to refactored classes:
#
# - PKGlobalStore: Centralized state management (GlobalStore.py)
# - ResultsManager: Results processing and display (ResultsManager.py)
# - TelegramNotifier: Telegram messaging (TelegramNotifier.py)
# - BacktestHandler: Backtesting operations (BacktestHandler.py)
# - MenuManager: Menu navigation (MenuManager.py)
# - PKScreenerMain: Main application orchestration (PKScreenerMain.py)
# =============================================================================
