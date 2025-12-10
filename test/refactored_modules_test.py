"""
Tests for the refactored modular components of PKScreener.

These tests verify that the new modular architecture works correctly:
- GlobalState: Centralized state management
- MenuHandlers: Menu processing logic
- ScanEngine: Scanning orchestration
- ResultsProcessor: Results handling
- ScreenerOrchestrator: High-level coordinator
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock


class TestGlobalState:
    """Tests for GlobalState class"""
    
    def test_singleton_pattern(self):
        """GlobalState should be a singleton"""
        from pkscreener.classes.GlobalState import GlobalState, get_global_state
        
        state1 = get_global_state()
        state2 = get_global_state()
        
        assert state1 is state2
    
    def test_reset_clears_state(self):
        """Reset should clear all state to defaults"""
        from pkscreener.classes.GlobalState import get_global_state
        
        state = get_global_state()
        state.user_passed_args = "test"
        state.menu_choice.level0 = "X"
        
        state.reset()
        
        assert state.user_passed_args is None
        assert state.menu_choice.level0 == ""
    
    def test_update_from_args(self):
        """Should update state from user arguments"""
        from pkscreener.classes.GlobalState import get_global_state
        
        state = get_global_state()
        state.reset()
        
        mock_args = Mock()
        mock_args.answerdefault = "Y"
        mock_args.user = "12345"
        
        state.update_from_args(mock_args)
        
        assert state.default_answer == "Y"
        assert state.user == "12345"
        
        state.reset()  # Cleanup
    
    def test_is_interrupted(self):
        """Should track keyboard interrupt state"""
        from pkscreener.classes.GlobalState import get_global_state
        
        state = get_global_state()
        state.reset()
        
        assert state.is_interrupted() is False
        
        state.set_interrupted(True)
        assert state.is_interrupted() is True
        
        state.reset()  # Cleanup


class TestMenuChoice:
    """Tests for MenuChoice dataclass"""
    
    def test_to_dict(self):
        """Should convert to dictionary format"""
        from pkscreener.classes.GlobalState import MenuChoice
        
        choice = MenuChoice(level0="X", level1="12", level2="9")
        d = choice.to_dict()
        
        assert d["0"] == "X"
        assert d["1"] == "12"
        assert d["2"] == "9"
    
    def test_from_dict(self):
        """Should create from dictionary"""
        from pkscreener.classes.GlobalState import MenuChoice
        
        choice = MenuChoice()
        choice.from_dict({"0": "X", "1": "12", "2": "9"})
        
        assert choice.level0 == "X"
        assert choice.level1 == "12"
        assert choice.level2 == "9"
    
    def test_reset(self):
        """Should reset all levels to empty"""
        from pkscreener.classes.GlobalState import MenuChoice
        
        choice = MenuChoice(level0="X", level1="12")
        choice.reset()
        
        assert choice.level0 == ""
        assert choice.level1 == ""


class TestScanConfig:
    """Tests for ScanConfig dataclass"""
    
    def test_defaults(self):
        """Should have sensible defaults"""
        from pkscreener.classes.ScanEngine import ScanConfig
        
        config = ScanConfig()
        
        assert config.menu_option == "X"
        assert config.index_option == 12
        assert config.execute_option == 0
        assert config.volume_ratio == 2.5
    
    def test_custom_values(self):
        """Should accept custom values"""
        from pkscreener.classes.ScanEngine import ScanConfig
        
        config = ScanConfig(
            menu_option="C",
            index_option=15,
            execute_option=44,
            volume_ratio=3.0
        )
        
        assert config.menu_option == "C"
        assert config.index_option == 15
        assert config.execute_option == 44
        assert config.volume_ratio == 3.0


class TestScanEngine:
    """Tests for ScanEngine class"""
    
    def test_initialization(self):
        """Should initialize with config manager"""
        from pkscreener.classes.ScanEngine import ScanEngine
        
        mock_config = Mock()
        engine = ScanEngine(mock_config)
        
        assert engine.config_manager == mock_config
        assert engine.tasks_queue is None
        assert engine.keyboard_interrupt_fired is False
    
    def test_configure(self):
        """Should accept scan configuration"""
        from pkscreener.classes.ScanEngine import ScanEngine, ScanConfig
        
        mock_config = Mock()
        engine = ScanEngine(mock_config)
        
        config = ScanConfig(menu_option="X", execute_option=44)
        engine.configure(config)
        
        assert engine.scan_config.menu_option == "X"
        assert engine.scan_config.execute_option == 44


class TestResultsProcessor:
    """Tests for ResultsProcessor class"""
    
    def test_initialization(self):
        """Should initialize with config manager"""
        from pkscreener.classes.ResultsProcessor import ResultsProcessor
        
        mock_config = Mock()
        processor = ResultsProcessor(mock_config)
        
        assert processor.config_manager == mock_config
        assert processor.strategy_filter == []
    
    def test_get_summary_stats_empty(self):
        """Should return zeros for empty results"""
        from pkscreener.classes.ResultsProcessor import ResultsProcessor
        
        mock_config = Mock()
        processor = ResultsProcessor(mock_config)
        
        stats = processor.get_summary_stats(pd.DataFrame())
        
        assert stats["total_stocks"] == 0
        assert stats["bullish_count"] == 0
    
    def test_get_summary_stats_with_data(self):
        """Should calculate stats from results"""
        from pkscreener.classes.ResultsProcessor import ResultsProcessor
        
        mock_config = Mock()
        processor = ResultsProcessor(mock_config)
        
        df = pd.DataFrame({
            "Stock": ["A", "B", "C"],
            "Trend": ["Bullish", "Bearish", "Strong Up"],
            "%Chng": [5.0, -2.0, 3.0]
        })
        
        stats = processor.get_summary_stats(df)
        
        assert stats["total_stocks"] == 3
        assert stats["bullish_count"] == 2  # "Bullish" and "Strong Up"
        assert stats["bearish_count"] == 1


class TestMenuContext:
    """Tests for MenuContext class"""
    
    def test_initialization(self):
        """Should initialize with defaults"""
        from pkscreener.classes.MenuHandlers import MenuContext
        
        ctx = MenuContext()
        
        assert ctx.menu_option == ""
        assert ctx.index_option is None
        assert ctx.testing is False
    
    def test_update_from_args(self):
        """Should update from user arguments"""
        from pkscreener.classes.MenuHandlers import MenuContext
        
        mock_args = Mock()
        mock_args.testbuild = True
        mock_args.prodbuild = True
        mock_args.download = False
        mock_args.answerdefault = "Y"
        mock_args.user = None
        mock_args.options = "X:12:9"
        
        ctx = MenuContext()
        ctx.update_from_args(mock_args)
        
        assert ctx.testing is True
        assert ctx.download_only is False
        assert ctx.startup_options == "X:12:9"


class TestMenuHandlerFactory:
    """Tests for MenuHandlerFactory"""
    
    def test_get_handler_for_monitor(self):
        """Should return MonitorMenuHandler for M"""
        from pkscreener.classes.MenuHandlers import (
            MenuContext, MenuHandlerFactory, MonitorMenuHandler
        )
        
        ctx = MenuContext()
        handler = MenuHandlerFactory.get_handler("M", ctx, {})
        
        assert isinstance(handler, MonitorMenuHandler)
    
    def test_get_handler_for_download(self):
        """Should return DownloadMenuHandler for D"""
        from pkscreener.classes.MenuHandlers import (
            MenuContext, MenuHandlerFactory, DownloadMenuHandler
        )
        
        ctx = MenuContext()
        handler = MenuHandlerFactory.get_handler("D", ctx, {})
        
        assert isinstance(handler, DownloadMenuHandler)
    
    def test_get_handler_returns_none_for_unknown(self):
        """Should return None for unknown menu options"""
        from pkscreener.classes.MenuHandlers import MenuContext, MenuHandlerFactory
        
        ctx = MenuContext()
        handler = MenuHandlerFactory.get_handler("UNKNOWN", ctx, {})
        
        assert handler is None


class TestScreenerOrchestrator:
    """Tests for ScreenerOrchestrator class"""
    
    def test_initialization(self):
        """Should initialize with components"""
        from pkscreener.classes.ScreenerOrchestrator import ScreenerOrchestrator
        
        mock_config = Mock()
        orchestrator = ScreenerOrchestrator(mock_config)
        
        assert orchestrator.config_manager == mock_config
        assert orchestrator.scan_engine is not None
        assert orchestrator.results_processor is not None
    
    def test_configure_scan(self):
        """Should configure scan parameters"""
        from pkscreener.classes.ScreenerOrchestrator import ScreenerOrchestrator
        
        mock_config = Mock()
        orchestrator = ScreenerOrchestrator(mock_config)
        
        config = orchestrator.configure_scan(
            menu_option="X",
            index_option=12,
            execute_option=44,
            volume_ratio=3.0
        )
        
        assert config.menu_option == "X"
        assert config.execute_option == 44
        assert config.volume_ratio == 3.0


class TestScanParameters:
    """Tests for ScanParameters dataclass"""
    
    def test_defaults(self):
        """Should have sensible defaults"""
        from pkscreener.classes.GlobalState import ScanParameters
        
        params = ScanParameters()
        
        assert params.min_rsi == 0
        assert params.max_rsi == 100
        assert params.volume_ratio == 2.5
        assert params.backtest_period == 0


class TestIntegration:
    """Integration tests for the refactored modules"""
    
    def test_end_to_end_configuration(self):
        """Should work together for configuration"""
        from pkscreener.classes.GlobalState import get_global_state
        from pkscreener.classes.ScreenerOrchestrator import ScreenerOrchestrator
        
        mock_config = Mock()
        mock_args = Mock()
        mock_args.answerdefault = "Y"
        mock_args.user = None
        
        # Initialize state
        state = get_global_state()
        state.reset()
        state.update_from_args(mock_args)
        
        # Create orchestrator
        orchestrator = ScreenerOrchestrator(mock_config, mock_args)
        orchestrator.initialize()
        
        # Configure scan
        config = orchestrator.configure_scan(
            menu_option="X",
            index_option=12,
            execute_option=44
        )
        
        assert config.menu_option == "X"
        assert state.default_answer == "Y"
        
        state.reset()  # Cleanup


class TestBacktestResultsProcessor:
    """Tests for BacktestResultsProcessor class"""
    
    def test_cleanup_empty(self):
        """Should handle empty backtest data"""
        from pkscreener.classes.ResultsProcessor import BacktestResultsProcessor
        
        mock_config = Mock()
        processor = BacktestResultsProcessor(mock_config)
        
        result_df, xray_df = processor.cleanup_backtest_data(None, None)
        
        assert result_df is None
        assert xray_df is None
    
    def test_cleanup_with_data(self):
        """Should clean up backtest data"""
        from pkscreener.classes.ResultsProcessor import BacktestResultsProcessor
        
        mock_config = Mock()
        processor = BacktestResultsProcessor(mock_config)
        
        df = pd.DataFrame({
            "Stock": ["A", "B", "A"],
            "Value": [1, 2, 1]
        })
        
        result_df, _ = processor.cleanup_backtest_data(df, None)
        
        # Should remove duplicates
        assert len(result_df) == 2
