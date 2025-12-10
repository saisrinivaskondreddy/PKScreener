"""
GlobalState - Centralized state management for PKScreener

This module encapsulates all global variables into a single, manageable class,
providing better organization, testability, and maintainability.
"""

import multiprocessing
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class MenuChoice:
    """Represents the hierarchical menu choices made by user"""
    level0: str = ""
    level1: str = ""
    level2: str = ""
    level3: str = ""
    level4: str = ""
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "0": self.level0,
            "1": self.level1,
            "2": self.level2,
            "3": self.level3,
            "4": self.level4
        }
    
    def from_dict(self, d: Dict[str, str]) -> 'MenuChoice':
        self.level0 = d.get("0", "")
        self.level1 = d.get("1", "")
        self.level2 = d.get("2", "")
        self.level3 = d.get("3", "")
        self.level4 = d.get("4", "")
        return self
    
    def reset(self):
        self.level0 = ""
        self.level1 = ""
        self.level2 = ""
        self.level3 = ""
        self.level4 = ""


@dataclass
class ScanParameters:
    """Parameters for stock screening"""
    min_rsi: float = 0
    max_rsi: float = 100
    inside_bar_lookback: int = 7
    days_for_lowest_volume: int = 30
    backtest_period: int = 0
    reversal_option: Optional[int] = None
    ma_length: int = 0
    newly_listed_only: bool = False
    resp_chart_pattern: Optional[str] = None
    volume_ratio: float = 2.5


@dataclass  
class ScanState:
    """State tracking for scan execution"""
    scan_cycle_running: bool = False
    elapsed_time: float = 0
    start_time: float = 0
    load_count: int = 0
    loaded_stock_data: bool = False
    keyboard_interrupt_fired: bool = False


class GlobalState:
    """
    Centralized state management for PKScreener.
    
    This class encapsulates all global variables that were previously scattered
    throughout globals.py, providing:
    - Clear ownership of state
    - Easy initialization and reset
    - Better testability
    - Thread-safe access where needed
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure single global state"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.reset()
    
    def reset(self):
        """Reset all state to initial values"""
        # User and session state
        self.user_passed_args = None
        self.default_answer = None
        self.user = None
        
        # Menu state
        self.menu_choice = MenuChoice()
        self.menu_choice_hierarchy = ""
        self.selected_choice = {"0": "", "1": "", "2": "", "3": "", "4": ""}
        
        # Scan parameters
        self.scan_params = ScanParameters()
        self.scan_state = ScanState()
        
        # Stock data
        self.stock_dict_primary = None
        self.stock_dict_secondary = None
        self.list_stock_codes: Optional[List[str]] = None
        self.last_scan_output_stock_codes: Optional[List[str]] = None
        
        # Results
        self.screen_results: Optional[pd.DataFrame] = None
        self.save_results: Optional[pd.DataFrame] = None
        self.backtest_df: Optional[pd.DataFrame] = None
        self.criteria_date_time = None
        
        # Multiprocessing
        self.mp_manager = None
        self.keyboard_interrupt_event = None
        self.screen_counter = None
        self.screen_results_counter = None
        self.tasks_queue = None
        self.results_queue = None
        self.consumers = None
        self.logging_queue = None
        
        # Analysis and caching
        self.analysis_dict: Dict[str, Any] = {}
        self.strategy_filter: List = []
        self.test_messages_queue: List = []
        self.media_group_dict: Dict = {}
        
        # Configuration
        self.show_saved_diff_results = False
        self.run_cleanup = False
        
    def initialize_multiprocessing(self, testing: bool = False):
        """Initialize multiprocessing components"""
        if self.mp_manager is None and not testing:
            self.mp_manager = multiprocessing.Manager()
        
        if self.keyboard_interrupt_event is None and not self.scan_state.keyboard_interrupt_fired and not testing:
            self.keyboard_interrupt_event = self.mp_manager.Event()
            
        self.screen_counter = multiprocessing.Value("i", 1)
        self.screen_results_counter = multiprocessing.Value("i", 0)
        
        if self.stock_dict_primary is None or isinstance(self.stock_dict_primary, dict):
            if self.mp_manager is not None:
                self.stock_dict_primary = self.mp_manager.dict()
                self.stock_dict_secondary = self.mp_manager.dict()
            self.scan_state.load_count = 0
    
    def update_from_args(self, user_args):
        """Update state from user arguments"""
        self.user_passed_args = user_args
        if user_args is not None:
            self.default_answer = user_args.answerdefault
            self.user = user_args.user
    
    def is_interrupted(self) -> bool:
        """Check if keyboard interrupt was fired"""
        return self.scan_state.keyboard_interrupt_fired
    
    def set_interrupted(self, value: bool = True):
        """Set keyboard interrupt state"""
        self.scan_state.keyboard_interrupt_fired = value
        if value and self.keyboard_interrupt_event is not None:
            self.keyboard_interrupt_event.set()


# Global instance for backward compatibility
_global_state = None

def get_global_state() -> GlobalState:
    """Get the global state singleton"""
    global _global_state
    if _global_state is None:
        _global_state = GlobalState()
    return _global_state

def reset_global_state():
    """Reset global state to initial values"""
    get_global_state().reset()
