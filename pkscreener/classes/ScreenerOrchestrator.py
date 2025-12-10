"""
ScreenerOrchestrator - Main orchestrator for PKScreener operations

This module provides a clean, high-level interface for running stock screenings.
It coordinates between GlobalState, MenuHandlers, ScanEngine, and ResultsProcessor.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from PKDevTools.classes.ColorText import colorText
from PKDevTools.classes.OutputControls import OutputControls
from PKDevTools.classes.log import default_logger

from pkscreener.classes.GlobalState import get_global_state, GlobalState
from pkscreener.classes.MenuHandlers import MenuContext, MenuHandlerFactory
from pkscreener.classes.ScanEngine import ScanEngine, ScanConfig, ScanResult
from pkscreener.classes.ResultsProcessor import ResultsProcessor


class ScreenerOrchestrator:
    """
    High-level orchestrator for PKScreener operations.
    
    This class provides a clean interface that coordinates:
    - Global state management
    - Menu navigation and handling
    - Scan execution
    - Results processing
    
    Usage:
        orchestrator = ScreenerOrchestrator(config_manager, user_args)
        screen_results, save_results = orchestrator.run_scan(
            menu_option="X",
            index_option=12,
            execute_option=9
        )
    """
    
    def __init__(self, config_manager, user_args=None):
        self.config_manager = config_manager
        self.user_args = user_args
        self.state = get_global_state()
        
        # Initialize components
        self.scan_engine = ScanEngine(config_manager, user_args)
        self.results_processor = ResultsProcessor(config_manager, user_args)
        
        # Menu state
        self.menu_context = MenuContext(user_args, config_manager)
        self.menus_dict: Dict[str, Any] = {}
    
    def initialize(self):
        """Initialize the orchestrator and global state"""
        self.state.update_from_args(self.user_args)
        self.menu_context.update_from_args(self.user_args)
    
    def set_menus(self, m0, m1, m2, m3, m4):
        """Set the menu objects for navigation"""
        self.menus_dict = {
            'm0': m0,
            'm1': m1,
            'm2': m2,
            'm3': m3,
            'm4': m4
        }
    
    def handle_menu(self, menu_option: str) -> Tuple[bool, Optional[Any]]:
        """
        Handle a menu option using the appropriate handler.
        
        Args:
            menu_option: The selected menu option (M, D, P, F, etc.)
            
        Returns:
            Tuple of (should_continue, result)
        """
        self.menu_context.menu_option = menu_option
        
        handler = MenuHandlerFactory.get_handler(
            menu_option,
            self.menu_context,
            self.menus_dict
        )
        
        if handler:
            return handler.handle()
        
        # No special handler - continue with normal flow
        return True, None
    
    def configure_scan(
        self,
        menu_option: str = "X",
        index_option: int = 12,
        execute_option: int = 0,
        **kwargs
    ) -> ScanConfig:
        """
        Configure scan parameters.
        
        Args:
            menu_option: Menu selection (X, C, F, etc.)
            index_option: Index selection
            execute_option: Execute option (scanner type)
            **kwargs: Additional scan parameters
            
        Returns:
            Configured ScanConfig object
        """
        config = ScanConfig(
            menu_option=menu_option,
            index_option=index_option,
            execute_option=execute_option,
            volume_ratio=kwargs.get('volume_ratio', 2.5),
            min_rsi=kwargs.get('min_rsi', 0),
            max_rsi=kwargs.get('max_rsi', 100),
            inside_bar_lookback=kwargs.get('inside_bar_lookback', 7),
            days_for_lowest_volume=kwargs.get('days_for_lowest_volume', 30),
            backtest_period=kwargs.get('backtest_period', 0),
            reversal_option=kwargs.get('reversal_option'),
            ma_length=kwargs.get('ma_length', 0),
            resp_chart_pattern=kwargs.get('resp_chart_pattern'),
            newly_listed_only=kwargs.get('newly_listed_only', False),
            download_only=kwargs.get('download_only', False),
            testing=kwargs.get('testing', False),
            test_build=kwargs.get('test_build', False)
        )
        
        self.scan_engine.configure(config)
        return config
    
    def run_scan(
        self,
        stock_dict_primary,
        stock_dict_secondary,
        list_stock_codes: List[str],
        keyboard_interrupt_event,
        screen_counter,
        screen_results_counter,
        selected_choice: Dict[str, str],
        menu_choice_hierarchy: str,
        run_scanners_callback
    ) -> ScanResult:
        """
        Execute a stock scan.
        
        Args:
            stock_dict_primary: Primary stock data dictionary
            stock_dict_secondary: Secondary stock data dictionary
            list_stock_codes: List of stock codes to scan
            keyboard_interrupt_event: Event for handling interrupts
            screen_counter: Counter for screen progress
            screen_results_counter: Counter for results
            selected_choice: Menu choice dictionary
            menu_choice_hierarchy: String representation of menu path
            run_scanners_callback: Callback function for scanning
            
        Returns:
            ScanResult containing results
        """
        # Prepare the scan engine
        self.scan_engine.prepare_scan(
            stock_dict_primary,
            stock_dict_secondary,
            list_stock_codes,
            keyboard_interrupt_event,
            screen_counter,
            screen_results_counter
        )
        
        # Run the scan
        result = self.scan_engine.run_scan(
            selected_choice,
            menu_choice_hierarchy,
            run_scanners_callback
        )
        
        return result
    
    def process_results(
        self,
        scan_result: ScanResult,
        execute_option: int,
        reversal_option: Optional[int],
        menu_option: str,
        volume_ratio: float = 2.5
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Process scan results.
        
        Args:
            scan_result: Results from scan
            execute_option: Selected execute option
            reversal_option: Reversal option if applicable
            menu_option: Selected menu option
            volume_ratio: Volume ratio threshold
            
        Returns:
            Tuple of (screen_results, save_results)
        """
        screen_results = scan_result.screen_results
        save_results = scan_result.save_results
        
        if screen_results is None or len(screen_results) == 0:
            return screen_results, save_results
        
        # Label results for display
        screen_results, save_results = self.results_processor.label_results(
            screen_results,
            save_results,
            volume_ratio,
            execute_option,
            reversal_option,
            menu_option
        )
        
        # Remove unknowns if configured
        if not self.state.scan_params.newly_listed_only:
            screen_results, save_results = self.results_processor.remove_unknowns(
                screen_results,
                save_results
            )
        
        # Apply strategy filters
        if self.results_processor.strategy_filter:
            screen_results, save_results = self.results_processor.apply_strategy_filter(
                screen_results,
                save_results,
                self.results_processor.strategy_filter
            )
        
        return screen_results, save_results
    
    def display_results(
        self,
        screen_results: pd.DataFrame,
        save_results: pd.DataFrame,
        elapsed_time: float,
        criteria_date_time=None
    ):
        """Display results to console"""
        from pkscreener.classes.PKScanRunner import PKScanRunner
        
        if screen_results is None or len(screen_results) == 0:
            OutputControls().printOutput(
                f"{colorText.FAIL}  [+] No stocks found matching criteria.{colorText.END}"
            )
            return
        
        # Format and display
        formatted = self.results_processor.format_for_display(screen_results, save_results)
        OutputControls().printOutput(formatted)
        
        # Show summary
        stats = self.results_processor.get_summary_stats(save_results)
        OutputControls().printOutput(
            f"\n{colorText.GREEN}  [+] Found {stats['total_stocks']} stocks "
            f"in {elapsed_time:.2f} seconds.{colorText.END}"
        )
    
    def cleanup(self):
        """Clean up resources"""
        self.scan_engine.cleanup()


# Convenience function for simple scans
def quick_scan(
    config_manager,
    user_args,
    menu_option: str = "X",
    index_option: int = 12,
    execute_option: int = 0,
    **kwargs
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run a quick scan with minimal setup.
    
    This is a convenience function for running scans without
    manually setting up the orchestrator.
    
    Args:
        config_manager: Configuration manager instance
        user_args: User arguments
        menu_option: Menu selection
        index_option: Index selection
        execute_option: Scanner type
        **kwargs: Additional parameters
        
    Returns:
        Tuple of (screen_results, save_results)
    """
    orchestrator = ScreenerOrchestrator(config_manager, user_args)
    orchestrator.initialize()
    orchestrator.configure_scan(
        menu_option=menu_option,
        index_option=index_option,
        execute_option=execute_option,
        **kwargs
    )
    
    # Note: For a full scan, you'd need to set up the stock data,
    # multiprocessing components, and callbacks.
    # This function provides a template for the interface.
    
    return None, None
