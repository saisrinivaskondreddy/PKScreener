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


class MenuManager:
    """
    Manages all menu navigation, selection, and hierarchy for the PKScreener application.
    Handles user input, menu rendering, and option validation across all menu levels.
    """

    def __init__(self, config_manager, user_passed_args):
        """
        Initialize the MenuManager with configuration and user arguments.
        
        Args:
            config_manager: Configuration manager instance
            user_passed_args: User passed arguments
        """
        self.config_manager = config_manager
        self.user_passed_args = user_passed_args
        self.m0 = menus()
        self.m1 = menus()
        self.m2 = menus()
        self.m3 = menus()
        self.m4 = menus()
        self.selected_choice = {"0": "", "1": "", "2": "", "3": "", "4": ""}
        self.menu_choice_hierarchy = ""
        self.n_value_for_menu = 0

    def ensure_menus_loaded(self, menu_option=None, index_option=None, execute_option=None):
        """
        Ensure all menus are loaded and rendered for the given options.
        
        Args:
            menu_option: Selected menu option
            index_option: Selected index option
            execute_option: Selected execute option
        """
        try:
            if len(self.m0.menuDict.keys()) == 0:
                self.m0.renderForMenu(asList=True)
                
            if len(self.m1.menuDict.keys()) == 0:
                self.m1.renderForMenu(selected_menu=self.m0.find(menu_option), asList=True)
                
            if len(self.m2.menuDict.keys()) == 0:
                self.m2.renderForMenu(selected_menu=self.m1.find(index_option), asList=True)
                
            if len(self.m3.menuDict.keys()) == 0:
                self.m3.renderForMenu(selected_menu=self.m2.find(execute_option), asList=True)
        except:
            pass

    def init_execution(self, menu_option=None):
        """
        Initialize execution by showing main menu and getting user selection.
        
        Args:
            menu_option: Pre-selected menu option
            
        Returns:
            object: Selected menu object
        """
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        
        if self.user_passed_args is not None and self.user_passed_args.pipedmenus is not None:
            OutputControls().printOutput(
                colorText.FAIL
                + "  [+] You chose: "
                + f" (Piped Scan Mode) [{self.user_passed_args.pipedmenus}]"
                + colorText.END
            )
            
        self.m0.renderForMenu(selected_menu=None, asList=(self.user_passed_args is not None and self.user_passed_args.options is not None))
        
        try:
            needs_calc = self.user_passed_args is not None and self.user_passed_args.backtestdaysago is not None
            past_date = f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(self.user_passed_args.backtestdaysago) if needs_calc else 0)}{colorText.END} ]\n" if needs_calc else ""
            
            if menu_option is None:
                if "PKDevTools_Default_Log_Level" in os.environ.keys():
                    from PKDevTools.classes import Archiver
                    log_file_path = os.path.join(Archiver.get_user_data_dir(), "pkscreener-logs.txt")
                    OutputControls().printOutput(colorText.FAIL + "\n      [+] Logs will be written to:" + colorText.END)
                    OutputControls().printOutput(colorText.GREEN + f"      [+] {log_file_path}" + colorText.END)
                    OutputControls().printOutput(colorText.FAIL + "      [+] If you need to share,run through the menus that are causing problems. At the end, open this folder, zip the log file to share at https://github.com/pkjmesra/PKScreener/issues .\n" + colorText.END)
                    
                menu_option = input(colorText.FAIL + f"{past_date}  [+] Select option: ") or "P"
                OutputControls().printOutput(colorText.END, end="")
                
            if menu_option == "" or menu_option is None:
                menu_option = "X"
                
            menu_option = menu_option.upper()
            selected_menu = self.m0.find(menu_option)
            
            if selected_menu is not None:
                if selected_menu.menuKey == "Z":
                    OutputControls().takeUserInput(
                        colorText.FAIL
                        + "  [+] Press <Enter> to Exit!"
                        + colorText.END
                    )
                    PKAnalyticsService().send_event("app_exit")
                    sys.exit(0)
                elif selected_menu.menuKey in ["B", "C", "G", "H", "U", "T", "S", "E", "X", "Y", "M", "D", "I", "L", "F"]:
                    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                    self.selected_choice["0"] = selected_menu.menuKey
                    return selected_menu
                elif selected_menu.menuKey in ["P"]:
                    return selected_menu
                    
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            self.show_option_error_message()
            return self.init_execution()

        self.show_option_error_message()
        return self.init_execution()

    def init_post_level0_execution(self, menu_option=None, index_option=None, execute_option=None, skip=[], retrial=False):
        """
        Initialize execution after level 0 menu selection.
        
        Args:
            menu_option: Selected menu option
            index_option: Selected index option
            execute_option: Selected execute option
            skip: List of options to skip
            retrial (bool): Whether this is a retry
            
        Returns:
            tuple: Index option and execute option
        """
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        
        if menu_option is None:
            OutputControls().printOutput('You must choose an option from the previous menu! Defaulting to "X"...')
            menu_option = "X"
            
        OutputControls().printOutput(
            colorText.FAIL
            + "  [+] You chose: "
            + level0MenuDict[menu_option].strip()
            + (f" (Piped Scan Mode) [{self.user_passed_args.pipedmenus}]" if (self.user_passed_args is not None and self.user_passed_args.pipedmenus is not None) else "")
            + colorText.END
        )
        
        if index_option is None:
            selected_menu = self.m0.find(menu_option)
            self.m1.renderForMenu(selected_menu=selected_menu, skip=skip, asList=(self.user_passed_args is not None and self.user_passed_args.options is not None))
            
        try:
            needs_calc = self.user_passed_args is not None and self.user_passed_args.backtestdaysago is not None
            past_date = f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(self.user_passed_args.backtestdaysago) if needs_calc else 0)}{colorText.END} ]\n" if needs_calc else ""
            
            if index_option is None:
                index_option = OutputControls().takeUserInput(
                    colorText.FAIL + f"{past_date}  [+] Select option: "
                )
                OutputControls().printOutput(colorText.END, end="")
                
            if (str(index_option).isnumeric() and int(index_option) > 1 and str(execute_option).isnumeric() and int(str(execute_option)) <= MAX_SUPPORTED_MENU_OPTION) or \
                    str(index_option).upper() in ["S", "E", "W"]:
                self.ensure_menus_loaded(menu_option, index_option, execute_option)
                
                if not PKPremiumHandler.hasPremium(self.m1.find(str(index_option).upper())):
                    PKAnalyticsService().send_event(f"non_premium_user_{menu_option}_{index_option}_{execute_option}")
                    return None, None
                    
            if index_option == "" or index_option is None:
                index_option = int(self.config_manager.defaultIndex)
            elif not str(index_option).isnumeric():
                index_option = index_option.upper()
                
                if index_option in ["M", "E", "N", "Z"]:
                    return index_option, 0
            else:
                index_option = int(index_option)
                
                if index_option < 0 or index_option > 15:
                    raise ValueError
                elif index_option == 13:
                    self.config_manager.period = "2y"
                    self.config_manager.getConfig(ConfigManager.parser)
                    self.newlyListedOnly = True
                    index_option = 12
                    
            if index_option == 15:
                from pkscreener.classes.MarketStatus import MarketStatus
                MarketStatus().exchange = "^IXIC"
                
            self.selected_choice["1"] = str(index_option)
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
                return self.init_post_level0_execution(retrial=True)
                
        return index_option, execute_option

    def init_post_level1_execution(self, index_option, execute_option=None, skip=[], retrial=False):
        """
        Initialize execution after level 1 menu selection.
        
        Args:
            index_option: Selected index option
            execute_option: Selected execute option
            skip: List of options to skip
            retrial (bool): Whether this is a retry
            
        Returns:
            tuple: Index option and execute option
        """
        list_stock_codes = [] if self.list_stock_codes is None or len(self.list_stock_codes) == 0 else self.list_stock_codes
        
        if execute_option is None:
            if index_option is not None and index_option != "W":
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                OutputControls().printOutput(
                    colorText.FAIL
                    + "  [+] You chose: "
                    + level0MenuDict[self.selected_choice["0"]].strip()
                    + " > "
                    + level1_X_MenuDict[self.selected_choice["1"]].strip()
                    + (f" (Piped Scan Mode) [{self.user_passed_args.pipedmenus}]" if (self.user_passed_args is not None and self.user_passed_args.pipedmenus is not None) else "")
                    + colorText.END
                )
                
                selected_menu = self.m1.find(index_option)
                self.m2.renderForMenu(selected_menu=selected_menu, skip=skip, asList=(self.user_passed_args is not None and self.user_passed_args.options is not None))
                stock_index_code = str(len(level1_index_options_sectoral.keys()))
                
                if index_option == "S":
                    self.ensure_menus_loaded("X", index_option, execute_option)
                    
                    if not PKPremiumHandler.hasPremium(selected_menu):
                        PKAnalyticsService().send_event(f"non_premium_user_X_{index_option}_{execute_option}")
                        PKAnalyticsService().send_event("app_exit")
                        sys.exit(0)
                        
                    index_keys = level1_index_options_sectoral.keys()
                    stock_index_code = input(
                        colorText.FAIL + "  [+] Select option: "
                    ) or str(len(index_keys))
                    OutputControls().printOutput(colorText.END, end="")
                    
                    if stock_index_code == str(len(index_keys)):
                        for index_code in index_keys:
                            if index_code != str(len(index_keys)):
                                self.list_stock_codes.append(level1_index_options_sectoral[str(index_code)].split("(")[1].split(")")[0])
                    else:
                        self.list_stock_codes = [level1_index_options_sectoral[str(stock_index_code)].split("(")[1].split(")")[0]]
                        
                    selected_menu.menuKey = "0"  # Reset because user must have selected specific index menu with single stock
                    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                    self.m2.renderForMenu(selected_menu=selected_menu, skip=skip, asList=(self.user_passed_args is not None and self.user_passed_args.options is not None))
                    
        try:
            needs_calc = self.user_passed_args is not None and self.user_passed_args.backtestdaysago is not None
            past_date = f"  [+] [ Running in Quick Backtest Mode for {colorText.WARN}{PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(self.user_passed_args.backtestdaysago) if needs_calc else 0)}{colorText.END} ]\n" if needs_calc else ""
            
            if index_option is not None and index_option != "W":
                if execute_option is None:
                    execute_option = input(
                        colorText.FAIL + f"{past_date}  [+] Select option: "
                    ) or "9"
                    OutputControls().printOutput(colorText.END, end="")
                    
                self.ensure_menus_loaded("X", index_option, execute_option)
                
                if not PKPremiumHandler.hasPremium(self.m2.find(str(execute_option))):
                    PKAnalyticsService().send_event(f"non_premium_user_X_{index_option}_{execute_option}")
                    return None, None
                    
                if execute_option == "":
                    execute_option = 1
                    
                if not str(execute_option).isnumeric():
                    execute_option = execute_option.upper()
                else:
                    execute_option = int(execute_option)
                    
                    if execute_option < 0 or execute_option > MAX_MENU_OPTION:
                        raise ValueError
            else:
                execute_option = 0
                
            self.selected_choice["2"] = str(execute_option)
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
                return self.init_post_level1_execution(index_option, execute_option, retrial=True)
                
        return index_option, execute_option

    def update_menu_choice_hierarchy(self):
        """
        Update the menu choice hierarchy string based on current selections.
        """
        try:
            self.menu_choice_hierarchy = f'{level0MenuDict[self.selected_choice["0"]].strip()}'
            top_level_menu_dict = level1_X_MenuDict if self.selected_choice["0"] not in "P" else level1_P_MenuDict
            level2_menu_dict = level2_X_MenuDict if self.selected_choice["0"] not in "P" else level2_P_MenuDict
            
            if len(self.selected_choice["1"]) > 0:
                self.menu_choice_hierarchy = f'{self.menu_choice_hierarchy}>{top_level_menu_dict[self.selected_choice["1"]].strip()}'
                
            if len(self.selected_choice["2"]) > 0:
                self.menu_choice_hierarchy = f'{self.menu_choice_hierarchy}>{level2_menu_dict[self.selected_choice["2"]].strip()}'
                
            if self.selected_choice["0"] not in "P":
                if self.selected_choice["2"] == "6":
                    self.menu_choice_hierarchy = (
                        self.menu_choice_hierarchy
                        + f'>{level3_X_Reversal_MenuDict[self.selected_choice["3"]].strip()}'
                    )
                    
                    if len(self.selected_choice) >= 5 and self.selected_choice["3"] in ["7", "10"]:
                        self.menu_choice_hierarchy = (
                            self.menu_choice_hierarchy
                            + f'>{level4_X_Lorenzian_MenuDict[self.selected_choice["4"]].strip()}'
                        )
                        
                elif self.selected_choice["2"] in ["30"]:
                    if len(self.selected_choice) >= 3:
                        self.menu_choice_hierarchy = (
                            self.menu_choice_hierarchy
                            + f'>{level4_X_Lorenzian_MenuDict[self.selected_choice["3"]].strip()}'
                        )
                        
                elif self.selected_choice["2"] == "7":
                    self.menu_choice_hierarchy = (
                        self.menu_choice_hierarchy
                        + f'>{level3_X_ChartPattern_MenuDict[self.selected_choice["3"]].strip()}'
                    )
                    
                    if len(self.selected_choice) >= 5 and self.selected_choice["3"] == "3":
                        self.menu_choice_hierarchy = (
                            self.menu_choice_hierarchy
                            + f'>{level4_X_ChartPattern_Confluence_MenuDict[self.selected_choice["4"]].strip()}'
                        )
                    elif len(self.selected_choice) >= 5 and self.selected_choice["3"] == "6":
                        self.menu_choice_hierarchy = (
                            self.menu_choice_hierarchy
                            + f'>{level4_X_ChartPattern_BBands_SQZ_MenuDict[self.selected_choice["4"]].strip()}'
                        )
                    elif len(self.selected_choice) >= 5 and self.selected_choice["3"] == "9":
                        self.menu_choice_hierarchy = (
                            self.menu_choice_hierarchy
                            + f'>{level4_X_ChartPattern_MASignalMenuDict[self.selected_choice["4"]].strip()}'
                        )
                    elif len(self.selected_choice) >= 5 and self.selected_choice["3"] == "7":
                        self.menu_choice_hierarchy = (
                            self.menu_choice_hierarchy
                            + f'>{CANDLESTICK_DICT[self.selected_choice["4"]].strip() if self.selected_choice["4"] != 0 else "No Filter"}'
                        )
                        
                elif self.selected_choice["2"] == "21":
                    self.menu_choice_hierarchy = (
                        self.menu_choice_hierarchy
                        + f'>{level3_X_PopularStocks_MenuDict[self.selected_choice["3"]].strip()}'
                    )
                    
                elif self.selected_choice["2"] == "33":
                    self.menu_choice_hierarchy = (
                        self.menu_choice_hierarchy
                        + f'>{level3_X_PotentialProfitable_MenuDict[self.selected_choice["3"]].strip()}'
                    )
                    
                elif self.selected_choice["2"] == "40":
                    self.menu_choice_hierarchy = (
                        self.menu_choice_hierarchy
                        + f'>{PRICE_CROSS_SMA_EMA_DIRECTION_MENUDICT[self.selected_choice["3"]].strip()}'
                    )
                    
                    self.menu_choice_hierarchy = (
                        self.menu_choice_hierarchy
                        + f'>{PRICE_CROSS_SMA_EMA_TYPE_MENUDICT[self.selected_choice["4"]].strip()}'
                    )
                    
                elif self.selected_choice["2"] == "41":
                    self.menu_choice_hierarchy = (
                        self.menu_choice_hierarchy
                        + f'>{PRICE_CROSS_PIVOT_POINT_TYPE_MENUDICT[self.selected_choice["3"]].strip()}'
                    )
                    
                    self.menu_choice_hierarchy = (
                        self.menu_choice_hierarchy
                        + f'>{PRICE_CROSS_SMA_EMA_DIRECTION_MENUDICT[self.selected_choice["4"]].strip()}'
                    )
            
            intraday = "(Intraday)" if ("Intraday" not in self.menu_choice_hierarchy and (self.user_passed_args is not None and self.user_passed_args.intraday) or self.config_manager.isIntradayConfig()) else ""
            self.menu_choice_hierarchy = f"{self.menu_choice_hierarchy}{intraday}"
            
            self.menu_choice_hierarchy = self.menu_choice_hierarchy.replace("N-", f"{self.n_value_for_menu}-")
        except:
            pass
            
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        needs_calc = self.user_passed_args is not None and self.user_passed_args.backtestdaysago is not None
        past_date = f"[ {PKDateUtilities.nthPastTradingDateStringFromFutureDate(int(self.user_passed_args.backtestdaysago) if needs_calc else 0)} ]" if needs_calc else ""
        
        report_title = f"{self.user_passed_args.pipedtitle}|" if self.user_passed_args is not None and self.user_passed_args.pipedtitle is not None else ""
        run_option_name = PKScanRunner.getFormattedChoices(self.user_passed_args, self.selected_choice)
        
        if ((":0:" in run_option_name or "_0_" in run_option_name) and self.user_passed_args.progressstatus is not None) or self.user_passed_args.progressstatus is not None:
            run_option_name = self.user_passed_args.progressstatus.split("=>")[0].split("  [+] ")[1].strip()
            
        report_title = f"{run_option_name} | {report_title}" if run_option_name is not None else report_title
        
        if len(run_option_name) >= 5:
            PKAnalyticsService().send_event(run_option_name)
            
        OutputControls().printOutput(
            colorText.FAIL
            + f"  [+] You chose: {report_title} "
            + self.menu_choice_hierarchy
            + (f" (Piped Scan Mode) [{self.user_passed_args.pipedmenus}] {past_date}" if (self.user_passed_args is not None and self.user_passed_args.pipedmenus is not None) else "")
            + colorText.END
        )
        
        default_logger().info(self.menu_choice_hierarchy)
        return self.menu_choice_hierarchy

    def show_option_error_message(self):
        """Display an error message for invalid menu options."""
        OutputControls().printOutput(
            colorText.FAIL
            + "\n  [+] Please enter a valid option & try Again!"
            + colorText.END
        )
        sleep(2)
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)

    def handle_secondary_menu_choices(self, menu_option, testing=False, default_answer=None, user=None):
        """
        Handle secondary menu choices (help, update, config, etc.).
        
        Args:
            menu_option: Selected menu option
            testing (bool): Whether running in test mode
            default_answer: Default answer for prompts
            user: User identifier
        """
        if menu_option == "H":
            self.show_send_help_info(default_answer, user)
        elif menu_option == "U":
            OTAUpdater.checkForUpdate(VERSION, skipDownload=testing)
            if default_answer is None:
                OutputControls().takeUserInput("Press <Enter> to continue...")
        elif menu_option == "T":
            if self.user_passed_args is None or self.user_passed_args.options is None:
                selected_menu = self.m0.find(menu_option)
                self.m1.renderForMenu(selected_menu=selected_menu)
                period_option = input(
                    colorText.FAIL + "  [+] Select option: "
                ) or ('L' if self.config_manager.period == '1y' else 'S')
                OutputControls().printOutput(colorText.END, end="")
                
                if period_option is None or period_option.upper() not in ["L", "S", "B"]:
                    return
                    
                ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                
                if period_option.upper() in ["L", "S"]:
                    selected_menu = self.m1.find(period_option)
                    self.m2.renderForMenu(selected_menu=selected_menu)
                    duration_option = input(
                        colorText.FAIL + "  [+] Select option: "
                    ) or "1"
                    OutputControls().printOutput(colorText.END, end="")
                    
                    if duration_option is None or duration_option.upper() not in ["1", "2", "3", "4", "5"]:
                        return
                        
                    ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
                    
                    if duration_option.upper() in ["1", "2", "3", "4"]:
                        selected_menu = self.m2.find(duration_option)
                        period_durations = selected_menu.menuText.split("(")[1].split(")")[0].split(", ")
                        self.config_manager.period = period_durations[0]
                        self.config_manager.duration = period_durations[1]
                        self.config_manager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
                        self.config_manager.deleteFileWithPattern(rootDir=Archiver.get_user_data_dir(), pattern="*stock_data_*.pkl*")
                    elif duration_option.upper() in ["5"]:
                        self.config_manager.setConfig(ConfigManager.parser, default=False, showFileCreatedText=True)
                        self.config_manager.deleteFileWithPattern(rootDir=Archiver.get_user_data_dir(), pattern="*stock_data_*.pkl*")
                    return
                elif period_option.upper() in ["B"]:
                    last_trading_date = PKDateUtilities.nthPastTradingDateStringFromFutureDate(n=(22 if self.config_manager.period == '1y' else 15))
                    backtest_days_ago = input(
                        f"{colorText.FAIL}  [+] Enter no. of days/candles in the past as starting candle for which you'd like to run the scans\n  [+] You can also enter a past date in {colorText.END}{colorText.GREEN}YYYY-MM-DD{colorText.END}{colorText.FAIL} format\n  [+] (e.g. {colorText.GREEN}10{colorText.END} for 10 candles ago or {colorText.GREEN}0{colorText.END} for today or {colorText.GREEN}{last_trading_date}{colorText.END}):"
                    ) or ('22' if self.config_manager.period == '1y' else '15')
                    OutputControls().printOutput(colorText.END, end="")
                    
                    if len(str(backtest_days_ago)) >= 3 and "-" in str(backtest_days_ago):
                        try:
                            backtest_days_ago = abs(PKDateUtilities.trading_days_between(
                                d1=PKDateUtilities.dateFromYmdString(str(backtest_days_ago)),
                                d2=PKDateUtilities.currentDateTime()))
                        except Exception as e:
                            default_logger().debug(e, exc_info=True)
                            OutputControls().printOutput(f"An error occured! Going ahead with default inputs.")
                            backtest_days_ago = ('22' if self.config_manager.period == '1y' else '15')
                            sleep(3)
                            pass
                            
                    launcher = f'"{sys.argv[0]}"' if " " in sys.argv[0] else sys.argv[0]
                    requesting_user = f" -u {self.user_passed_args.user}" if self.user_passed_args.user is not None else ""
                    enable_log = f" -l" if self.user_passed_args.log else ""
                    enable_telegram_mode = f" --telegram" if self.user_passed_args is not None and self.user_passed_args.telegram else ""
                    stock_list_param = f" --stocklist {self.user_passed_args.stocklist}" if self.user_passed_args.stocklist else ""
                    slicewindow_param = f" --slicewindow {self.user_passed_args.slicewindow}" if self.user_passed_args.slicewindow else ""
                    fname_param = f" --fname {self.results_contents_encoded}" if self.results_contents_encoded else ""
                    launcher = f"python3.12 {launcher}" if (launcher.endswith(".py\"") or launcher.endswith(".py")) else launcher
                    
                    OutputControls().printOutput(f"{colorText.GREEN}Launching PKScreener in quick backtest mode. If it does not launch, please try with the following:{colorText.END}\n{colorText.FAIL}{launcher} --backtestdaysago {int(backtest_days_ago)}{requesting_user}{enable_log}{enable_telegram_mode}{stock_list_param}{slicewindow_param}{fname_param}{colorText.END}\n{colorText.WARN}Press Ctrl + C to exit quick backtest mode.{colorText.END}")
                    sleep(2)
                    os.system(f"{launcher} --systemlaunched -a Y -e --backtestdaysago {int(backtest_days_ago)}{requesting_user}{enable_log}{enable_telegram_mode}{stock_list_param}{slicewindow_param}{fname_param}")
                    ConsoleUtility.PKConsoleTools.clearScreen(clearAlways=True, forceTop=True)
                    return None, None
            elif self.user_passed_args is not None and self.user_passed_args.options is not None:
                options = self.user_passed_args.options.split(":")
                selected_menu = self.m0.find(options[0])
                self.m1.renderForMenu(selected_menu=selected_menu, asList=True)
                selected_menu = self.m1.find(options[1])
                self.m2.renderForMenu(selected_menu=selected_menu, asList=True)
                
                if options[2] in ["1", "2", "3", "4"]:
                    selected_menu = self.m2.find(options[2])
                    period_durations = selected_menu.menuText.split("(")[1].split(")")[0].split(", ")
                    self.config_manager.period = period_durations[0]
                    self.config_manager.duration = period_durations[1]
                    self.config_manager.setConfig(ConfigManager.parser, default=True, showFileCreatedText=False)
                else:
                    self.toggle_user_config()
            else:
                self.toggle_user_config()
        elif menu_option == "E":
            self.config_manager.setConfig(ConfigManager.parser)
        elif menu_option == "Y":
            self.show_send_config_info(default_answer, user)
            
        return

    def show_send_config_info(self, default_answer=None, user=None):
        """
        Show and send configuration information.
        
        Args:
            default_answer: Default answer for prompts
            user: User identifier
        """
        config_data = self.config_manager.showConfigFile(default_answer=('Y' if user is not None else default_answer))
        
        if user is not None:
            self.send_message_to_telegram_channel(message=ImageUtility.PKImageTools.removeAllColorStyles(config_data), user=user)
            
        if default_answer is None:
            input("Press any key to continue...")

    def show_send_help_info(self, default_answer=None, user=None):
        """
        Show and send help information.
        
        Args:
            default_answer: Default answer for prompts
            user: User identifier
        """
        help_data = ConsoleUtility.PKConsoleTools.show