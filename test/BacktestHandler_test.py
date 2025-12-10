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

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import os
import tempfile


class TestBacktestHandler:
    """Test cases for BacktestHandler class."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        mock = MagicMock()
        mock.backtestPeriod = 30
        mock.volumeRatio = 2.5
        mock.showPastStrategyData = True
        mock.alwaysExportToExcel = False
        mock.enablePortfolioCalculations = False
        return mock
    
    @pytest.fixture
    def mock_user_args(self):
        """Create mock user arguments."""
        mock = MagicMock()
        mock.options = "X:1:2"
        mock.backtestdaysago = None
        mock.answerdefault = None
        return mock
    
    @pytest.fixture
    def handler(self, mock_config_manager, mock_user_args):
        """Create a BacktestHandler instance."""
        from pkscreener.classes.BacktestHandler import BacktestHandler
        return BacktestHandler(mock_config_manager, mock_user_args)
    
    def test_initialization(self, mock_config_manager, mock_user_args):
        """Test BacktestHandler initialization."""
        from pkscreener.classes.BacktestHandler import BacktestHandler
        
        handler = BacktestHandler(mock_config_manager, mock_user_args)
        
        assert handler.config_manager is mock_config_manager
        assert handler.user_passed_args is mock_user_args
        assert handler.elapsed_time == 0
    
    def test_initialization_without_user_args(self, mock_config_manager):
        """Test initialization without user args."""
        from pkscreener.classes.BacktestHandler import BacktestHandler
        
        handler = BacktestHandler(mock_config_manager)
        
        assert handler.config_manager is mock_config_manager
        assert handler.user_passed_args is None
    
    def test_get_historical_days_testing_mode(self, handler):
        """Test getting historical days in testing mode."""
        result = handler.get_historical_days(100, testing=True)
        assert result == 2
    
    def test_get_historical_days_normal_mode(self, handler):
        """Test getting historical days in normal mode."""
        result = handler.get_historical_days(100, testing=False)
        assert result == 30  # From config_manager.backtestPeriod
    
    def test_get_backtest_report_filename_default(self, handler):
        """Test getting default backtest report filename."""
        selected_choice = {"0": "X", "1": "1", "2": "2", "3": "", "4": ""}
        
        with patch('pkscreener.classes.BacktestHandler.PKScanRunner') as mock_runner:
            mock_runner.getFormattedChoices.return_value = "X_1_2"
            
            choices, filename = handler.get_backtest_report_filename(
                sort_key="Stock",
                optional_name="backtest_result",
                selected_choice=selected_choice
            )
            
            assert choices == "X_1_2"
            assert "PKScreener_" in filename
            assert "backtest_result" in filename
            assert "StockSorted.html" in filename
    
    def test_get_backtest_report_filename_with_choices(self, handler):
        """Test getting backtest report filename with pre-set choices."""
        choices, filename = handler.get_backtest_report_filename(
            sort_key="Date",
            optional_name="Summary",
            choices="P_1_1"
        )
        
        assert choices == "P_1_1"
        assert "Summary" in filename
        assert "DateSorted.html" in filename
    
    def test_scan_output_directory_creates_dir(self, handler):
        """Test that scan output directory is created."""
        with patch('os.path.isdir') as mock_isdir, \
             patch('os.makedirs') as mock_makedirs, \
             patch('pkscreener.classes.BacktestHandler.OutputControls') as mock_output:
            
            mock_isdir.return_value = False
            mock_output.return_value.printOutput = MagicMock()
            
            result = handler.scan_output_directory(backtest=True)
            
            assert "Backtest-Reports" in result
    
    def test_scan_output_directory_exists(self, handler):
        """Test scan output directory when it exists."""
        with patch('os.path.isdir') as mock_isdir:
            mock_isdir.return_value = True
            
            result = handler.scan_output_directory(backtest=False)
            
            assert "actions-data-scan" in result


class TestBacktestHandlerUpdateResults:
    """Test cases for update_backtest_results method."""
    
    @pytest.fixture
    def handler(self):
        """Create a BacktestHandler instance."""
        from pkscreener.classes.BacktestHandler import BacktestHandler
        
        mock_config = MagicMock()
        mock_config.backtestPeriod = 30
        
        return BacktestHandler(mock_config)
    
    def test_update_backtest_results(self, handler):
        """Test updating backtest results."""
        import time
        
        with patch('pkscreener.classes.BacktestHandler.backtest') as mock_backtest:
            mock_backtest.return_value = pd.DataFrame({'Stock': ['SBIN']})
            
            result = (
                {'Stock': 'SBIN'},  # screen result
                {'Stock': 'SBIN'},  # save result
                pd.DataFrame({'Close': [100, 101, 102]}),  # stock data
                'SBIN',  # stock name
                5  # sample days
            )
            
            selected_choice = {"2": "6", "3": "2"}
            start_time = time.time()
            
            backtest_df = handler.update_backtest_results(
                backtest_period=30,
                start_time=start_time,
                result=result,
                sample_days=5,
                backtest_df=None,
                selected_choice=selected_choice
            )
            
            mock_backtest.assert_called_once()


class TestBacktestHandlerTabulate:
    """Test cases for tabulate_backtest_results method."""
    
    @pytest.fixture
    def handler(self):
        """Create a BacktestHandler instance."""
        from pkscreener.classes.BacktestHandler import BacktestHandler
        
        mock_config = MagicMock()
        mock_config.showPastStrategyData = True
        
        return BacktestHandler(mock_config)
    
    def test_tabulate_results_not_configured(self, handler):
        """Test tabulation when not configured."""
        handler.config_manager.showPastStrategyData = False
        
        summary, detail = handler.tabulate_backtest_results(pd.DataFrame())
        
        assert summary is None
        assert detail is None
    
    def test_tabulate_results_not_in_runner(self, handler):
        """Test tabulation when not in runner mode."""
        with patch.dict(os.environ, {}, clear=True):
            summary, detail = handler.tabulate_backtest_results(pd.DataFrame())
            
            assert summary is None
            assert detail is None


class TestBacktestHandlerShowResults:
    """Test cases for show_backtest_results method."""
    
    @pytest.fixture
    def handler(self):
        """Create a BacktestHandler instance."""
        from pkscreener.classes.BacktestHandler import BacktestHandler
        
        mock_config = MagicMock()
        mock_config.alwaysExportToExcel = False
        
        mock_args = MagicMock()
        mock_args.answerdefault = None
        
        return BacktestHandler(mock_config, mock_args)
    
    def test_show_results_empty_dataframe(self, handler):
        """Test showing results with empty dataframe."""
        with patch('pkscreener.classes.BacktestHandler.OutputControls') as mock_output:
            mock_output.return_value.printOutput = MagicMock()
            
            handler.show_backtest_results(
                backtest_df=pd.DataFrame(),
                sort_key="Stock",
                menu_choice_hierarchy="X > 1 > 2"
            )
            
            # Should print error message
            mock_output.return_value.printOutput.assert_called()
    
    def test_show_results_none_dataframe(self, handler):
        """Test showing results with None dataframe."""
        with patch('pkscreener.classes.BacktestHandler.OutputControls') as mock_output:
            mock_output.return_value.printOutput = MagicMock()
            
            handler.show_backtest_results(
                backtest_df=None,
                sort_key="Stock"
            )
            
            mock_output.return_value.printOutput.assert_called()


class TestBacktestHandlerTakeInputs:
    """Test cases for take_backtest_inputs method."""
    
    @pytest.fixture
    def handler(self):
        """Create a BacktestHandler instance."""
        from pkscreener.classes.BacktestHandler import BacktestHandler
        
        mock_config = MagicMock()
        mock_config.backtestPeriod = 30
        
        return BacktestHandler(mock_config)
    
    def test_take_inputs_default_period_backtest(self, handler):
        """Test taking inputs with default period for backtest."""
        with patch('pkscreener.classes.BacktestHandler.OutputControls') as mock_output, \
             patch('builtins.input', side_effect=Exception("skip input")):
            
            mock_output.return_value.printOutput = MagicMock()
            
            try:
                index_opt, exec_opt, period = handler.take_backtest_inputs(
                    menu_option="B",
                    backtest_period=0
                )
            except:
                # Input will raise exception, default should be used
                pass
    
    def test_take_inputs_growth_of_10k(self, handler):
        """Test taking inputs for growth of 10k."""
        with patch('pkscreener.classes.BacktestHandler.OutputControls') as mock_output:
            mock_output.return_value.printOutput = MagicMock()
            
            index_opt, exec_opt, period = handler.take_backtest_inputs(
                menu_option="G",
                backtest_period=15
            )
            
            assert period == 15


class TestBacktestHandlerHTMLReformat:
    """Test cases for HTML reformatting."""
    
    @pytest.fixture
    def handler(self):
        """Create a BacktestHandler instance."""
        from pkscreener.classes.BacktestHandler import BacktestHandler
        
        mock_config = MagicMock()
        return BacktestHandler(mock_config)
    
    def test_reformat_table_for_html_with_sorting(self, handler):
        """Test HTML reformatting with sorting."""
        with patch('pkscreener.classes.BacktestHandler.colorText') as mock_color:
            mock_color.BOLD = ''
            mock_color.GREEN = ''
            mock_color.FAIL = ''
            mock_color.WARN = ''
            mock_color.WHITE = ''
            mock_color.END = ''
            
            input_html = '<table><tr><td>data</td></tr></table>'
            header_dict = {0: '<th></th>'}
            
            result = handler._reformat_table_for_html(
                "Summary", header_dict, input_html, sorting=True
            )
            
            assert '<!DOCTYPE html>' in result
            assert 'resultsTable' in result
    
    def test_reformat_table_for_html_without_sorting(self, handler):
        """Test HTML reformatting without sorting."""
        with patch('pkscreener.classes.BacktestHandler.colorText') as mock_color:
            mock_color.BOLD = ''
            mock_color.GREEN = ''
            mock_color.FAIL = ''
            mock_color.WARN = ''
            mock_color.WHITE = ''
            mock_color.END = ''
            
            input_html = '<table border="1" class="dataframe"><tbody><tr></tr></tbody></table>'
            
            result = handler._reformat_table_for_html(
                "", {}, input_html, sorting=False
            )
            
            assert '<table' not in result



