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


class TestResultsManager:
    """Test cases for ResultsManager class."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock config manager."""
        mock = MagicMock()
        mock.daysToLookback = 22
        mock.volumeRatio = 2.5
        mock.calculatersiintraday = True
        mock.periodsRange = [1, 2, 3, 5, 10, 15, 22, 30]
        return mock
    
    @pytest.fixture
    def mock_user_args(self):
        """Create mock user arguments."""
        mock = MagicMock()
        mock.options = "X:1:2"
        mock.monitor = None
        mock.backtestdaysago = None
        return mock
    
    @pytest.fixture
    def sample_screen_results(self):
        """Create sample screen results dataframe."""
        return pd.DataFrame({
            'Stock': ['SBIN', 'HDFC', 'INFY'],
            '%Chng': ['2.5', '-1.2', '0.8'],
            'volume': ['1.5', '2.0', '0.8'],
            'RSI': [65, 45, 55],
            'RSIi': [62, 48, 58],
            'Pattern': ['Bullish', 'Bearish', 'Neutral'],
            'Trend': ['Up', 'Down', 'Sideways']
        })
    
    @pytest.fixture
    def sample_save_results(self):
        """Create sample save results dataframe."""
        return pd.DataFrame({
            'Stock': ['SBIN', 'HDFC', 'INFY'],
            '%Chng': [2.5, -1.2, 0.8],
            'volume': ['1.5x', '2.0x', '0.8x'],
            'RSI': [65, 45, 55],
            'RSIi': [62, 48, 58],
            'Pattern': ['Bullish', 'Bearish', 'Neutral'],
            'Trend': ['Up', 'Down', 'Sideways']
        })
    
    def test_initialization(self, mock_config_manager, mock_user_args):
        """Test ResultsManager initialization."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        manager = ResultsManager(mock_config_manager, mock_user_args)
        
        assert manager.config_manager is mock_config_manager
        assert manager.user_passed_args is mock_user_args
    
    def test_initialization_without_user_args(self, mock_config_manager):
        """Test ResultsManager initialization without user args."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        manager = ResultsManager(mock_config_manager)
        
        assert manager.config_manager is mock_config_manager
        assert manager.user_passed_args is None
    
    def test_remove_unknowns(self, mock_config_manager):
        """Test removing rows with 'Unknown' values."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        manager = ResultsManager(mock_config_manager)
        
        screen_results = pd.DataFrame({
            'Stock': ['SBIN', 'HDFC', 'INFY'],
            'Pattern': ['Bullish', 'Unknown', 'Neutral'],
            'Trend': ['Up', 'Down', 'Unknown']
        })
        
        save_results = screen_results.copy()
        
        filtered_screen, filtered_save = manager.remove_unknowns(screen_results, save_results)
        
        # Only SBIN should remain (no Unknown values)
        assert len(filtered_screen) == 1
        assert filtered_screen['Stock'].iloc[0] == 'SBIN'
    
    def test_remove_unused_columns(self, mock_config_manager, mock_user_args):
        """Test removing unused columns."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        manager = ResultsManager(mock_config_manager, mock_user_args)
        
        save_results = pd.DataFrame({
            'Stock': ['SBIN', 'HDFC'],
            'LTP': [100, 200],
            'LTP1': [101, 201],
            'LTP2': [102, 202],
            'Growth1': [1.0, 0.5],
            'Growth2': [2.0, 1.0],
            'Date': ['2023-01-01', '2023-01-01']
        })
        
        screen_results = save_results.copy()
        
        summary = manager.remove_unused_columns(screen_results, save_results, ['Date'])
        
        # LTP1, LTP2, Growth1, Growth2, Date should be removed
        assert 'LTP1' not in save_results.columns
        assert 'Growth1' not in save_results.columns
        assert 'Date' not in save_results.columns
        assert 'LTP' in save_results.columns
        assert 'Stock' in save_results.columns
    
    def test_save_screen_results_encoded(self, mock_config_manager):
        """Test saving encoded screen results."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        with patch('pkscreener.classes.ResultsManager.Archiver') as mock_archiver:
            mock_archiver.get_user_outputs_dir.return_value = tempfile.gettempdir()
            
            manager = ResultsManager(mock_config_manager)
            
            test_text = "Test encoded results"
            result = manager.save_screen_results_encoded(test_text)
            
            # Result should contain UUID and timestamp
            assert '~' in result
            parts = result.split('~')
            assert len(parts) >= 2
    
    def test_read_screen_results_decoded(self, mock_config_manager):
        """Test reading decoded screen results."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        with patch('pkscreener.classes.ResultsManager.Archiver') as mock_archiver:
            mock_archiver.get_user_outputs_dir.return_value = tempfile.gettempdir()
            
            manager = ResultsManager(mock_config_manager)
            
            # Save some content first
            test_text = "Test content"
            encoded_name = manager.save_screen_results_encoded(test_text)
            filename = encoded_name.split('~')[0]
            
            # Read it back
            content = manager.read_screen_results_decoded(filename)
            
            assert content == test_text
    
    def test_format_table_results_empty(self, mock_config_manager):
        """Test formatting empty results."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        manager = ResultsManager(mock_config_manager)
        
        result = manager.format_table_results(None)
        assert result == ""
        
        result = manager.format_table_results(pd.DataFrame())
        assert result == ""
    
    def test_format_table_results_with_data(self, mock_config_manager, sample_screen_results):
        """Test formatting results with data."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        with patch('pkscreener.classes.ResultsManager.Utility') as mock_utility, \
             patch('pkscreener.classes.ResultsManager.colorText') as mock_color:
            
            mock_utility.tools.getMaxColumnWidths.return_value = [10] * len(sample_screen_results.columns)
            mock_color.miniTabulator.return_value.tabulate.return_value = b"formatted_table"
            mock_color.No_Pad_GridFormat = "grid"
            
            manager = ResultsManager(mock_config_manager)
            result = manager.format_table_results(sample_screen_results)
            
            assert result is not None
    
    def test_reformat_table_for_html_with_sorting(self, mock_config_manager):
        """Test HTML table reformatting with sorting enabled."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        with patch('pkscreener.classes.ResultsManager.colorText') as mock_color:
            mock_color.BOLD = '\033[1m'
            mock_color.GREEN = '\033[92m'
            mock_color.FAIL = '\033[91m'
            mock_color.WARN = '\033[93m'
            mock_color.WHITE = '\033[97m'
            mock_color.END = '\033[0m'
            
            manager = ResultsManager(mock_config_manager)
            
            input_html = '<table><tr><td>data</td></tr></table>'
            header_dict = {0: '<th></th>', 1: '<th>Col1</th>'}
            summary = "Test Summary"
            
            result = manager.reformat_table_for_html(summary, header_dict, input_html, sorting=True)
            
            # Check that HTML structure is present
            assert '<!DOCTYPE html>' in result
            assert 'resultsTable' in result
    
    def test_reformat_table_for_html_without_sorting(self, mock_config_manager):
        """Test HTML table reformatting without sorting."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        with patch('pkscreener.classes.ResultsManager.colorText') as mock_color:
            mock_color.BOLD = '\033[1m'
            mock_color.GREEN = '\033[92m'
            mock_color.FAIL = '\033[91m'
            mock_color.WARN = '\033[93m'
            mock_color.WHITE = '\033[97m'
            mock_color.END = '\033[0m'
            
            manager = ResultsManager(mock_config_manager)
            
            input_html = '<table border="1" class="dataframe"><tbody><tr></tr></tbody></table>'
            header_dict = {}
            summary = ""
            
            result = manager.reformat_table_for_html(summary, header_dict, input_html, sorting=False)
            
            # Check that table elements are removed
            assert '<table' not in result
            assert '<tbody>' not in result
    
    def test_get_latest_trade_datetime(self, mock_config_manager):
        """Test getting latest trade datetime."""
        from pkscreener.classes.ResultsManager import ResultsManager
        
        manager = ResultsManager(mock_config_manager)
        
        # Test with empty dict
        date, time_val = manager.get_latest_trade_datetime({})
        assert date is None
        assert time_val is None
        
        # Test with valid data
        stock_dict = {
            'SBIN': {
                'data': [[100, 200, 90, 195, 1000]],
                'columns': ['Open', 'High', 'Low', 'Close', 'Volume'],
                'index': [1704067200]  # 2024-01-01 00:00:00 UTC
            }
        }
        
        date, time_val = manager.get_latest_trade_datetime(stock_dict)
        
        assert date is not None
        assert time_val is not None


class TestResultsManagerSortKey:
    """Test cases for sort key determination."""
    
    @pytest.fixture
    def manager(self):
        """Create a ResultsManager instance."""
        mock_config = MagicMock()
        mock_config.daysToLookback = 22
        mock_config.volumeRatio = 2.5
        mock_config.periodsRange = [1, 2, 3, 5]
        
        from pkscreener.classes.ResultsManager import ResultsManager
        return ResultsManager(mock_config)
    
    def test_get_sort_key_default(self, manager):
        """Test default sort key."""
        save_results = pd.DataFrame({'volume': [1.0, 2.0]})
        screen_results = save_results.copy()
        
        sort_key, ascending = manager._get_sort_key(
            "Test Hierarchy", 0, None, False, save_results, screen_results
        )
        
        assert sort_key == ["volume"]
        assert ascending == [False]
    
    def test_get_sort_key_rsi(self, manager):
        """Test RSI sort key."""
        save_results = pd.DataFrame({'RSI': [50, 60], 'RSIi': [52, 58]})
        screen_results = save_results.copy()
        
        sort_key, ascending = manager._get_sort_key(
            "RSI Test", 0, None, True, save_results, screen_results
        )
        
        assert sort_key == "RSIi"
        assert ascending == [True]
    
    def test_get_sort_key_execute_option_21(self, manager):
        """Test sort key for execute option 21."""
        save_results = pd.DataFrame({'MFI': [50, 60]})
        screen_results = save_results.copy()
        
        sort_key, ascending = manager._get_sort_key(
            "Test", 21, 3, False, save_results, screen_results
        )
        
        assert sort_key == ["MFI"]
        assert ascending == [False]
    
    def test_get_sort_key_execute_option_31(self, manager):
        """Test sort key for DEEL Momentum (option 31)."""
        save_results = pd.DataFrame({'%Chng': [2.5, -1.0]})
        screen_results = save_results.copy()
        
        sort_key, ascending = manager._get_sort_key(
            "Test", 31, None, False, save_results, screen_results
        )
        
        assert sort_key == ["%Chng"]
        assert ascending == [False]



