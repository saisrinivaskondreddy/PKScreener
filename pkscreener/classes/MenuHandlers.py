"""
MenuHandlers - Modular menu handling for PKScreener

This module extracts menu handling logic from the monolithic main() function
into focused, testable handler classes.
"""

import os
import sys
from time import sleep
from typing import Tuple, Optional, List, Dict, Any

import pandas as pd
from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.OutputControls import OutputControls
from PKDevTools.classes.PKDateUtilities import PKDateUtilities
from PKDevTools.classes import Archiver
from PKDevTools.classes.SuppressOutput import SuppressOutput

from pkscreener.classes.MenuOptions import (
    menus, level1_index_options_sectoral,
    PIPED_SCANNERS, PREDEFINED_SCAN_MENU_KEYS, PREDEFINED_SCAN_MENU_TEXTS,
    INDICES_MAP
)
from pkscreener.classes.PKAnalytics import PKAnalyticsService


class MenuContext:
    """Context object passed between menu handlers"""
    
    def __init__(self, user_args=None, config_manager=None):
        self.user_args = user_args
        self.config_manager = config_manager
        self.menu_option: str = ""
        self.index_option: Optional[int] = None
        self.execute_option: Optional[int] = None
        self.selected_choice: Dict[str, str] = {"0": "", "1": "", "2": "", "3": "", "4": ""}
        self.list_stock_codes: Optional[List[str]] = None
        self.testing = False
        self.test_build = False
        self.download_only = False
        self.default_answer = None
        self.user = None
        self.startup_options = None
        
    def update_from_args(self, user_args):
        """Update context from user arguments"""
        if user_args is None:
            return
        self.user_args = user_args
        self.testing = user_args.testbuild and user_args.prodbuild if user_args else False
        self.test_build = user_args.testbuild and not self.testing if user_args else False
        self.download_only = user_args.download if user_args else False
        self.default_answer = user_args.answerdefault if user_args else None
        self.user = user_args.user if user_args else None
        self.startup_options = user_args.options if user_args else None


class BaseMenuHandler:
    """Base class for menu handlers"""
    
    def __init__(self, context: MenuContext, menus_dict: Dict):
        self.context = context
        self.m0 = menus_dict.get('m0')
        self.m1 = menus_dict.get('m1')
        self.m2 = menus_dict.get('m2')
        self.m3 = menus_dict.get('m3')
        self.m4 = menus_dict.get('m4')
    
    def get_launcher(self) -> str:
        """Get the launcher command for subprocess calls"""
        launcher = f'"{sys.argv[0]}"' if " " in sys.argv[0] else sys.argv[0]
        if launcher.endswith(".py\"") or launcher.endswith(".py"):
            launcher = f"python3.12 {launcher}"
        return launcher
    
    def handle(self) -> Tuple[bool, Optional[Any]]:
        """
        Handle the menu option.
        
        Returns:
            Tuple of (should_continue, result)
            - should_continue: True if main flow should continue, False to return
            - result: Optional result to return if should_continue is False
        """
        raise NotImplementedError


class MonitorMenuHandler(BaseMenuHandler):
    """Handler for Monitor mode (M)"""
    
    def handle(self) -> Tuple[bool, Optional[Any]]:
        launcher = self.get_launcher()
        OutputControls().printOutput(
            f"{colorText.GREEN}Launching PKScreener in monitoring mode. "
            f"If it does not launch, please try with the following:{colorText.END}\n"
            f"{colorText.FAIL}{launcher} --systemlaunched -a Y -m 'X'{colorText.END}\n"
            f"{colorText.WARN}Press Ctrl + C to exit monitoring mode.{colorText.END}"
        )
        PKAnalyticsService().send_event(f"monitor_{self.context.menu_option}")
        sleep(2)
        os.system(f"{launcher} --systemlaunched -a Y -m 'X'")
        return False, (None, None)


class DownloadMenuHandler(BaseMenuHandler):
    """Handler for Download options (D)"""
    
    def handle(self) -> Tuple[bool, Optional[Any]]:
        from pkscreener.classes.Fetcher import screenerStockDataFetcher
        from PKNSETools.Nasdaq.PKNasdaqIndex import PKNasdaqIndexFetcher
        
        fetcher = screenerStockDataFetcher(self.context.config_manager)
        launcher = self.get_launcher()
        selected_menu = self.m0.find(self.context.menu_option)
        
        from pkscreener.classes import ConsoleUtility
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        self.m1.renderForMenu(selected_menu)
        
        sel_option = input(colorText.FAIL + "  [+] Select option: ") or "D"
        OutputControls().printOutput(colorText.END, end="")
        
        if sel_option.upper() == "D":
            return self._handle_daily_download(launcher)
        elif sel_option.upper() == "I":
            return self._handle_intraday_download(launcher)
        elif sel_option.upper() == "N":
            return self._handle_index_download(fetcher)
        elif sel_option.upper() == "S":
            return self._handle_sector_download(fetcher)
        elif sel_option.upper() == "M":
            PKAnalyticsService().send_event(f"{self.context.menu_option}_{sel_option.upper()}")
            return False, (None, None)
        
        return False, (None, None)
    
    def _handle_daily_download(self, launcher: str) -> Tuple[bool, Optional[Any]]:
        OutputControls().printOutput(
            f"{colorText.GREEN}Launching PKScreener to Download daily OHLC data.{colorText.END}\n"
            f"{colorText.FAIL}{launcher} -a Y -e -d{colorText.END}\n"
            f"{colorText.WARN}Press Ctrl + C to exit at any time.{colorText.END}"
        )
        PKAnalyticsService().send_event(f"{self.context.menu_option}_D")
        sleep(2)
        os.system(f"{launcher} -a Y -e -d")
        return False, (None, None)
    
    def _handle_intraday_download(self, launcher: str) -> Tuple[bool, Optional[Any]]:
        OutputControls().printOutput(
            f"{colorText.GREEN}Launching PKScreener to Download intraday OHLC data.{colorText.END}\n"
            f"{colorText.FAIL}{launcher} -a Y -e -d -i 1m{colorText.END}\n"
            f"{colorText.WARN}Press Ctrl + C to exit at any time.{colorText.END}"
        )
        PKAnalyticsService().send_event(f"{self.context.menu_option}_I")
        sleep(2)
        os.system(f"{launcher} -a Y -e -d -i 1m")
        return False, (None, None)
    
    def _handle_index_download(self, fetcher) -> Tuple[bool, Optional[Any]]:
        from PKNSETools.Nasdaq.PKNasdaqIndex import PKNasdaqIndexFetcher
        from pkscreener.classes import ConsoleUtility
        
        selected_menu = self.m1.find("N")
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        self.m2.renderForMenu(selected_menu)
        PKAnalyticsService().send_event(f"{self.context.menu_option}_N")
        
        sel_option = input(colorText.FAIL + "  [+] Select option: ") or "12"
        OutputControls().printOutput(colorText.END, end="")
        
        file_prefix = INDICES_MAP.get(sel_option.upper(), "Download").replace(" ", "")
        filename = f"PKS_Data_{file_prefix}_{PKDateUtilities.currentDateTime().strftime('%d-%m-%y_%H.%M.%S')}.csv"
        file_path = os.path.join(Archiver.get_user_indices_dir(), filename)
        
        PKAnalyticsService().send_event(f"{self.context.menu_option}_{sel_option.upper()}")
        
        if sel_option.upper() == "15":
            nasdaq = PKNasdaqIndexFetcher(self.context.config_manager)
            _, nasdaq_df = nasdaq.fetchNasdaqIndexConstituents()
            try:
                nasdaq_df.to_csv(file_path)
                OutputControls().printOutput(f"{colorText.GREEN}{file_prefix} Saved at: {file_path}{colorText.END}")
            except Exception as e:
                OutputControls().printOutput(f"{colorText.FAIL}Error: {e}{colorText.END}")
            input(f"{colorText.GREEN}Press any key to continue...{colorText.END}")
        elif sel_option.upper() == "M":
            pass
        else:
            file_contents = fetcher.fetchFileFromHostServer(
                filePath=file_path,
                tickerOption=int(sel_option),
                fileContents=""
            )
            if len(file_contents) > 0:
                OutputControls().printOutput(f"{colorText.GREEN}{file_prefix} Saved at: {file_path}{colorText.END}")
            else:
                OutputControls().printOutput(f"{colorText.FAIL}Error occurred. Please try again!{colorText.END}")
            input(f"{colorText.GREEN}Press any key to continue...{colorText.END}")
        
        return False, (None, None)
    
    def _handle_sector_download(self, fetcher) -> Tuple[bool, Optional[Any]]:
        from pkscreener.classes import ConsoleUtility
        from pkscreener.classes.PKDataService import PKDataService
        
        selected_menu = self.m1.find("S")
        ConsoleUtility.PKConsoleTools.clearScreen(forceTop=True)
        self.m2.renderForMenu(selected_menu, skip=["15"])
        
        sel_option = input(colorText.FAIL + "  [+] Select option: ") or "12"
        OutputControls().printOutput(colorText.END, end="")
        
        file_prefix = INDICES_MAP.get(sel_option.upper(), "Download").replace(" ", "")
        filename = f"PKS_Data_{file_prefix}_{PKDateUtilities.currentDateTime().strftime('%d-%m-%y_%H.%M.%S')}.csv"
        file_path = os.path.join(Archiver.get_user_reports_dir(), filename)
        
        PKAnalyticsService().send_event(f"{self.context.menu_option}_{sel_option.upper()}")
        
        if sel_option.upper() == "M":
            return False, (None, None)
        
        index_option = int(sel_option)
        if 0 < index_option <= 14:
            should_suppress = not OutputControls().enableMultipleLineOutput
            with SuppressOutput(suppress_stderr=should_suppress, suppress_stdout=should_suppress):
                list_codes = fetcher.fetchStockCodes(index_option, stockCode=None)
            
            OutputControls().printOutput(f"{colorText.GREEN}Please be patient. It might take a while...{colorText.END}")
            
            data_svc = PKDataService()
            stock_dict_list, _ = data_svc.getSymbolsAndSectorInfo(
                self.context.config_manager, 
                stockCodes=list_codes
            )
            
            if len(stock_dict_list) > 0:
                sector_df = pd.DataFrame(stock_dict_list)
                sector_df.to_csv(file_path)
                OutputControls().printOutput(
                    f"{colorText.GREEN}Sector/Industry info for {file_prefix}, saved at: {file_path}{colorText.END}"
                )
            else:
                OutputControls().printOutput(f"{colorText.FAIL}Error occurred. Please try again!{colorText.END}")
            
            input(f"{colorText.GREEN}Press any key to continue...{colorText.END}")
        
        return False, (None, None)


class PredefinedMenuHandler(BaseMenuHandler):
    """Handler for Predefined scans (P)"""
    
    def handle(self) -> Tuple[bool, Optional[Any]]:
        from pkscreener.classes import ConsoleUtility
        
        options = []
        if self.context.startup_options:
            options = self.context.startup_options.split(":")
        
        predefined_option = None
        sel_predefined_option = None
        sel_index_option = None
        
        if len(options) >= 3:
            predefined_option = str(options[1]) if str(options[1]).isnumeric() else '1'
            sel_predefined_option = str(options[2]) if str(options[2]).isnumeric() else '1'
            if len(options) >= 4:
                sel_index_option = str(options[3]) if str(options[3]).isnumeric() else '12'
        
        self.context.selected_choice["0"] = "P"
        
        selected_menu = self.m0.find("P")
        self.m1.renderForMenu(
            selected_menu, 
            asList=(self.context.user_args is not None and self.context.user_args.options is not None)
        )
        
        # Show backtest mode info if applicable
        needs_calc = (self.context.user_args is not None and 
                     self.context.user_args.backtestdaysago is not None)
        past_date = ""
        if needs_calc:
            days_ago = int(self.context.user_args.backtestdaysago)
            past_date = (f"  [+] [ Running in Quick Backtest Mode for "
                        f"{colorText.WARN}{PKDateUtilities.nthPastTradingDateStringFromFutureDate(days_ago)}"
                        f"{colorText.END} ]\n")
        
        if predefined_option is None:
            predefined_option = input(colorText.FAIL + f"{past_date}  [+] Select option: ") or "1"
        OutputControls().printOutput(colorText.END, end="")
        
        if predefined_option not in ["1", "2", "3", "4"]:
            return False, (None, None)
        
        self.context.selected_choice["1"] = predefined_option
        
        if predefined_option in ["1", "4"]:
            return self._handle_predefined_or_watchlist(
                predefined_option, sel_predefined_option, sel_index_option, past_date
            )
        elif predefined_option == "2":
            # User chose custom - switch to X menu
            self.context.menu_option = "X"
            if self.context.user_args and self.context.user_args.pipedmenus is None:
                self.context.user_args.pipedmenus = ""
            return True, None  # Continue with X menu processing
        elif predefined_option == "3":
            # Run piped menus
            if self.context.user_args and self.context.user_args.pipedmenus is not None:
                # This would call addOrRunPipedMenus() in original
                pass
        
        return False, (None, None)
    
    def _handle_predefined_or_watchlist(
        self, 
        predefined_option: str, 
        sel_predefined_option: Optional[str],
        sel_index_option: Optional[str],
        past_date: str
    ) -> Tuple[bool, Optional[Any]]:
        from pkscreener.classes import ConsoleUtility
        
        selected_menu = self.m1.find(predefined_option)
        self.m2.renderForMenu(
            selectedMenu=selected_menu,
            asList=(self.context.user_args is not None and self.context.user_args.options is not None)
        )
        
        if sel_predefined_option is None:
            sel_predefined_option = input(colorText.FAIL + f"{past_date}  [+] Select option: ") or "1"
        OutputControls().printOutput(colorText.END, end="")
        
        if sel_predefined_option in PREDEFINED_SCAN_MENU_KEYS:
            scanner_option = PIPED_SCANNERS[sel_predefined_option]
            
            if predefined_option == "4":  # Watchlist
                scanner_option = scanner_option.replace("-o 'X:12:", "-o 'X:W:")
            elif predefined_option == "1":  # Predefined
                if sel_index_option is None and (
                    self.context.user_args is None or 
                    self.context.user_args.answerdefault is None
                ):
                    self.m1.renderForMenu(
                        self.m0.find(key="X"),
                        skip=["W", "N", "E", "S", "Z"],
                        asList=(self.context.user_args is not None and 
                               self.context.user_args.options is not None)
                    )
                    sel_index_option = input(
                        colorText.FAIL + f"{past_date}  [+] Select option: "
                    ) or str(self.context.config_manager.defaultIndex if self.context.config_manager else "12")
                    
                    if str(sel_index_option).upper() == "M":
                        return False, (None, None)
                
                if sel_index_option is not None:
                    scanner_option = scanner_option.replace(
                        "-o 'X:12:", f"-o 'X:{sel_index_option}:"
                    )
            
            if self.context.user_args is not None:
                self.context.user_args.usertag = PREDEFINED_SCAN_MENU_TEXTS[int(sel_predefined_option) - 1]
            
            self.context.selected_choice["2"] = sel_predefined_option
            
            # Launch the piped scanner
            return self._launch_piped_scanner(scanner_option)
        
        return False, (None, None)
    
    def _launch_piped_scanner(self, scanner_option: str) -> Tuple[bool, Optional[Any]]:
        from pkscreener.classes import ConsoleUtility
        
        launcher = self.get_launcher()
        scanner_option_quoted = scanner_option.replace("'", '"')
        
        # Build additional parameters
        params = []
        if self.context.user_args:
            if self.context.user_args.user is not None:
                params.append(f" -u {self.context.user_args.user}")
            if self.context.user_args.log:
                params.append(" -l")
            if self.context.user_args.telegram:
                params.append(" --telegram")
            if self.context.user_args.backtestdaysago:
                params.append(f" --backtestdaysago {self.context.user_args.backtestdaysago}")
            if self.context.user_args.stocklist:
                params.append(f" --stocklist {self.context.user_args.stocklist}")
            if self.context.user_args.slicewindow:
                params.append(f" --slicewindow {self.context.user_args.slicewindow}")
            if self.context.user_args.monitor and "-e -o" in scanner_option_quoted:
                scanner_option_quoted = scanner_option_quoted.replace("-e -o", "-m")
        
        extra_params = "".join(params)
        
        OutputControls().printOutput(
            f"{colorText.GREEN}Launching PKScreener with piped scanners.{colorText.END}\n"
            f"{colorText.FAIL}{launcher} {scanner_option_quoted}{extra_params}{colorText.END}"
        )
        sleep(2)
        os.system(f"{launcher} {scanner_option_quoted}{extra_params}")
        
        OutputControls().printOutput(
            f"{colorText.GREEN}  [+] Finished running all piped scanners!{colorText.END}"
        )
        
        if self.context.default_answer is None:
            OutputControls().takeUserInput("Press <Enter> to continue...")
        
        ConsoleUtility.PKConsoleTools.clearScreen(clearAlways=True, forceTop=True)
        return False, (None, None)


class LogsMenuHandler(BaseMenuHandler):
    """Handler for Logs collection (L)"""
    
    def handle(self) -> Tuple[bool, Optional[Any]]:
        launcher = self.get_launcher()
        PKAnalyticsService().send_event(f"{self.context.menu_option}")
        OutputControls().printOutput(
            f"{colorText.GREEN}Launching PKScreener to collect logs.{colorText.END}\n"
            f"{colorText.FAIL}{launcher} -a Y -l{colorText.END}\n"
            f"{colorText.WARN}Press Ctrl + C to exit at any time.{colorText.END}"
        )
        sleep(2)
        os.system(f"{launcher} -a Y -l")
        return False, (None, None)


class FundamentalsMenuHandler(BaseMenuHandler):
    """Handler for Fundamentals screening (F)"""
    
    def handle(self) -> Tuple[bool, Optional[Any]]:
        from pkscreener.classes import ConsoleUtility
        from pkscreener.classes.Fetcher import screenerStockDataFetcher
        
        PKAnalyticsService().send_event(f"{self.context.menu_option}")
        
        self.context.index_option = 0
        self.context.selected_choice["0"] = "F"
        self.context.selected_choice["1"] = "0"
        self.context.execute_option = None
        
        should_suppress = not OutputControls().enableMultipleLineOutput
        
        # Check if stock codes provided in options
        if (self.context.user_args is not None and 
            self.context.user_args.options is not None and 
            len(self.context.user_args.options.split(":")) >= 3):
            stock_options = self.context.user_args.options.split(":")
            stock_options = stock_options[2 if len(stock_options) <= 3 else 3]
            self.context.list_stock_codes = stock_options.replace(".", ",").split(",")
        
        if self.context.list_stock_codes is None or len(self.context.list_stock_codes) == 0:
            fetcher = screenerStockDataFetcher(self.context.config_manager)
            with SuppressOutput(suppress_stderr=should_suppress, suppress_stdout=should_suppress):
                self.context.list_stock_codes = fetcher.fetchStockCodes(tickerOption=0, stockCode=None)
        
        ConsoleUtility.PKConsoleTools.clearScreen(clearAlways=True, forceTop=True)
        return True, None  # Continue with screening


class MenuHandlerFactory:
    """Factory for creating appropriate menu handlers"""
    
    @staticmethod
    def get_handler(
        menu_option: str, 
        context: MenuContext, 
        menus_dict: Dict
    ) -> Optional[BaseMenuHandler]:
        """Get the appropriate handler for a menu option"""
        handlers = {
            "M": MonitorMenuHandler,
            "D": DownloadMenuHandler,
            "L": LogsMenuHandler,
            "F": FundamentalsMenuHandler,
            "P": PredefinedMenuHandler,
        }
        
        handler_class = handlers.get(menu_option)
        if handler_class:
            return handler_class(context, menus_dict)
        return None
