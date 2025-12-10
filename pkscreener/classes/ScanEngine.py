"""
ScanEngine - Orchestrates stock scanning operations

This module encapsulates the scanning logic from globals.py into a clean,
maintainable class structure.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
from alive_progress import alive_bar

from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.OutputControls import OutputControls
from PKDevTools.classes.log import default_logger

from pkscreener.classes import Utility


@dataclass
class ScanConfig:
    """Configuration for a scan operation"""
    menu_option: str = "X"
    index_option: int = 12
    execute_option: int = 0
    volume_ratio: float = 2.5
    min_rsi: float = 0
    max_rsi: float = 100
    inside_bar_lookback: int = 7
    days_for_lowest_volume: int = 30
    backtest_period: int = 0
    reversal_option: Optional[int] = None
    ma_length: int = 0
    resp_chart_pattern: Optional[str] = None
    newly_listed_only: bool = False
    download_only: bool = False
    testing: bool = False
    test_build: bool = False


@dataclass
class ScanResult:
    """Results from a scan operation"""
    screen_results: Optional[pd.DataFrame] = None
    save_results: Optional[pd.DataFrame] = None
    backtest_df: Optional[pd.DataFrame] = None
    elapsed_time: float = 0
    stocks_scanned: int = 0
    stocks_found: int = 0


class ScanEngine:
    """
    Orchestrates stock scanning operations.
    
    This class provides a clean interface for running scans while
    encapsulating the complex logic previously in globals.py.
    """
    
    def __init__(self, config_manager, user_args=None):
        self.config_manager = config_manager
        self.user_args = user_args
        self.scan_config = ScanConfig()
        
        # Multiprocessing components
        self.tasks_queue = None
        self.results_queue = None
        self.consumers = None
        self.logging_queue = None
        
        # State
        self.keyboard_interrupt_event = None
        self.keyboard_interrupt_fired = False
        self.screen_counter = None
        self.screen_results_counter = None
        
        # Stock data
        self.stock_dict_primary = None
        self.stock_dict_secondary = None
        self.list_stock_codes: List[str] = []
        
    def configure(self, config: ScanConfig):
        """Configure the scan parameters"""
        self.scan_config = config
    
    def prepare_scan(
        self, 
        stock_dict_primary,
        stock_dict_secondary,
        list_stock_codes: List[str],
        keyboard_interrupt_event,
        screen_counter,
        screen_results_counter
    ):
        """Prepare for scanning by setting up required state"""
        self.stock_dict_primary = stock_dict_primary
        self.stock_dict_secondary = stock_dict_secondary
        self.list_stock_codes = list_stock_codes
        self.keyboard_interrupt_event = keyboard_interrupt_event
        self.screen_counter = screen_counter
        self.screen_results_counter = screen_results_counter
    
    def run_scan(
        self, 
        selected_choice: Dict[str, str],
        menu_choice_hierarchy: str,
        run_scanners_callback
    ) -> ScanResult:
        """
        Execute the scan operation.
        
        Args:
            selected_choice: Dictionary of menu choices
            menu_choice_hierarchy: String representation of menu path
            run_scanners_callback: Callback function for actual scanning
            
        Returns:
            ScanResult containing the scan results
        """
        from pkscreener.classes.PKScanRunner import PKScanRunner
        
        start_time = time.time()
        result = ScanResult()
        
        # Initialize dataframes
        screen_results, save_results = PKScanRunner.initDataframes()
        
        # Get scan duration parameters
        sampling_duration, filler_placeholder, actual_duration = \
            PKScanRunner.getScanDurationParameters(
                self.scan_config.testing, 
                self.scan_config.menu_option
            )
        
        # Prepare items for scanning
        items = self._prepare_scan_items(
            selected_choice, 
            menu_choice_hierarchy,
            sampling_duration, 
            filler_placeholder
        )
        
        if self.keyboard_interrupt_fired:
            result.elapsed_time = time.time() - start_time
            return result
        
        # Run the actual scan
        try:
            screen_results, save_results, backtest_df, \
            self.tasks_queue, self.results_queue, \
            self.consumers, self.logging_queue = PKScanRunner.runScanWithParams(
                self.user_args,
                self.keyboard_interrupt_event,
                self.screen_counter,
                self.screen_results_counter,
                self.stock_dict_primary,
                self.stock_dict_secondary,
                self.scan_config.testing,
                self.scan_config.backtest_period,
                self.scan_config.menu_option,
                self.scan_config.execute_option,
                sampling_duration,
                items,
                screen_results,
                save_results,
                None,  # backtest_df
                scanningCb=run_scanners_callback,
                tasks_queue=self.tasks_queue,
                results_queue=self.results_queue,
                consumers=self.consumers,
                logging_queue=self.logging_queue
            )
            
            result.screen_results = screen_results
            result.save_results = save_results
            result.backtest_df = backtest_df
            result.stocks_scanned = len(items)
            result.stocks_found = len(screen_results) if screen_results is not None else 0
            
        except Exception as e:
            default_logger().debug(e, exc_info=True)
            OutputControls().printOutput(
                f"{colorText.FAIL}Scan error: {e}{colorText.END}"
            )
        
        result.elapsed_time = time.time() - start_time
        return result
    
    def _prepare_scan_items(
        self, 
        selected_choice: Dict[str, str],
        menu_choice_hierarchy: str,
        sampling_duration: int, 
        filler_placeholder: int
    ) -> List:
        """Prepare the list of items to scan"""
        from pkscreener.classes.PKScanRunner import PKScanRunner
        
        items = []
        actual_duration = sampling_duration - filler_placeholder
        
        # Determine exchange
        index_opt = self.scan_config.index_option
        default_index = self.config_manager.defaultIndex if self.config_manager else 12
        exchange_name = "NASDAQ" if (index_opt == 15 or (default_index == 15 and index_opt == 0)) else "INDIA"
        
        # Get formatted run option name
        run_option_name = PKScanRunner.getFormattedChoices(self.user_args, selected_choice)
        if self.user_args and self.user_args.progressstatus is not None:
            if (":0:" in run_option_name or "_0_" in run_option_name):
                run_option_name = self.user_args.progressstatus.split("=>")[0].split("  [+] ")[1]
        
        bar, spinner = Utility.tools.getProgressbarStyle()
        OutputControls().printOutput(f"{colorText.GREEN}  [+] Adding stocks to the queue...{colorText.END}")
        
        with alive_bar(actual_duration, bar=bar, spinner=spinner) as progressbar:
            while actual_duration >= 0:
                days_in_past = PKScanRunner.getBacktestDaysForScan(
                    self.user_args, 
                    self.scan_config.backtest_period, 
                    self.scan_config.menu_option, 
                    actual_duration
                )
                
                try:
                    if self.scan_config.menu_option != "C":
                        self.list_stock_codes, saved_count, past_date = \
                            PKScanRunner.getStocksListForScan(
                                self.user_args,
                                self.scan_config.menu_option,
                                len(items),
                                False,  # downloaded_recently
                                days_in_past
                            )
                    else:
                        saved_count, past_date = 0, ""
                        
                except KeyboardInterrupt:
                    self.keyboard_interrupt_fired = True
                    if self.keyboard_interrupt_event:
                        self.keyboard_interrupt_event.set()
                    OutputControls().printOutput(
                        f"{colorText.FAIL}\n  [+] Terminating Script...{colorText.END}"
                    )
                    break
                except Exception:
                    pass
                
                run_option = f"{self.user_args.options if self.user_args else ''} =>{run_option_name} => {menu_choice_hierarchy}"
                
                if self.scan_config.menu_option == "F":
                    # Remove index if present
                    if "^NSEI" in self.list_stock_codes:
                        self.list_stock_codes.remove("^NSEI")
                    
                    items = PKScanRunner.addScansWithDefaultParams(
                        self.user_args,
                        self.scan_config.testing,
                        self.scan_config.test_build,
                        self.scan_config.newly_listed_only,
                        self.scan_config.download_only,
                        self.scan_config.backtest_period,
                        self.list_stock_codes,
                        self.scan_config.menu_option,
                        exchange_name,
                        self.scan_config.execute_option,
                        self.scan_config.volume_ratio,
                        items,
                        days_in_past,
                        runOption=run_option
                    )
                else:
                    PKScanRunner.addStocksToItemList(
                        self.user_args,
                        self.scan_config.testing,
                        self.scan_config.test_build,
                        self.scan_config.newly_listed_only,
                        self.scan_config.download_only,
                        self.scan_config.min_rsi,
                        self.scan_config.max_rsi,
                        self.scan_config.inside_bar_lookback,
                        self.scan_config.resp_chart_pattern,
                        self.scan_config.days_for_lowest_volume,
                        self.scan_config.backtest_period,
                        self.scan_config.reversal_option,
                        self.scan_config.ma_length,
                        self.list_stock_codes,
                        self.scan_config.menu_option,
                        exchange_name,
                        self.scan_config.execute_option,
                        self.scan_config.volume_ratio,
                        items,
                        days_in_past,
                        runOption=run_option
                    )
                
                if saved_count > 0:
                    progressbar.text(
                        f"{colorText.GREEN}Total Stocks: {len(items)}. "
                        f"Added {saved_count} from {past_date}{colorText.END}"
                    )
                
                filler_placeholder += 1
                actual_duration = sampling_duration - filler_placeholder
                
                if actual_duration >= 0:
                    progressbar()
        
        return items
    
    def cleanup(self):
        """Clean up resources after scanning"""
        from pkscreener.classes.PKScanRunner import PKScanRunner
        
        if (self.user_args is not None and 
            not self.user_args.testalloptions and 
            self.user_args.monitor is None and 
            "|" not in (self.user_args.options or "") and 
            not (self.user_args.options or "").upper().startswith("C")):
            
            PKScanRunner.terminateAllWorkers(
                self.user_args, 
                self.consumers, 
                self.tasks_queue, 
                self.scan_config.testing
            )
            
            self.tasks_queue = None
            self.results_queue = None
            self.consumers = None
