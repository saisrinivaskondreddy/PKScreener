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
import pickle
import unittest
from unittest.mock import patch, mock_open, MagicMock

from PKDevTools.classes.ColorText import colorText

from pkscreener.classes.AssetsManager import PKAssetsManager

class TestAssetsManager(unittest.TestCase):

    def test_make_hyperlink_valid_url(self):
        url = "https://www.example.com"
        expected = '=HYPERLINK("https://in.tradingview.com/chart?symbol=NSE:https://www.example.com", "https://www.example.com")'
        result = PKAssetsManager.make_hyperlink(url)
        self.assertEqual(result, expected)

    def test_make_hyperlink_empty_string(self):
        url = ""
        expected = '=HYPERLINK("https://in.tradingview.com/chart?symbol=NSE:", "")'
        result = PKAssetsManager.make_hyperlink(url)
        self.assertEqual(result, expected)

    def test_make_hyperlink_none(self):
        url = None
        with self.assertRaises(TypeError):
            PKAssetsManager.make_hyperlink(url)

    @patch('builtins.input', return_value='y')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pandas.core.generic.NDFrame.to_excel')
    def test_prompt_save_results_yes(self, mock_to_csv, mock_open, mock_input):
        # Create a sample DataFrame
        sample_df = MagicMock()
        # Call the method under test
        PKAssetsManager.promptSaveResults("Sheetname",sample_df)
        # Check that input was called to prompt the user
        mock_input.assert_called_once_with(colorText.WARN + f"[>] Do you want to save the results in excel file? [Y/N](Default:{colorText.END}{colorText.FAIL}N{colorText.END}): ")

    @patch('os.path.exists')
    def test_after_market_stock_data_exists_true(self, mock_exists):
        # Mock os.path.exists to return True
        mock_exists.return_value = True
        symbol = 'AAPL'
        date = '2025-02-06'
        # Call the class method
        exist,result = PKAssetsManager.afterMarketStockDataExists(True, True)
        # Assertions
        self.assertFalse(exist)
        self.assertTrue(result.startswith("intraday_stock_data_"))


    @patch('pkscreener.classes.AssetsManager.PKAssetsManager.afterMarketStockDataExists', return_value=(False, 'test.pkl'))
    @patch('PKDevTools.classes.Archiver.get_user_data_dir', return_value='test_results')
    @patch('PKDevTools.classes.OutputControls.OutputControls.printOutput')
    @patch('os.path.exists', return_value=False)
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.dump')
    def test_save_stock_data_success(self, mock_pickle_dump, mock_open, mock_path_exists, mock_print, mock_get_data_dir, mock_after_market_exists):
        stock_dict = {'AAPL': {'price': 150}}
        config_manager = MagicMock()
        config_manager.isIntradayConfig.return_value = False
        config_manager.deleteFileWithPattern = MagicMock()
        load_count = 10
        result = PKAssetsManager.saveStockData(stock_dict, config_manager, load_count)
        # Verify cache file path
        expected_cache_path = os.path.join('test_results', 'test.pkl')
        self.assertEqual(result, expected_cache_path)
        # Verify file write operations
        mock_open.assert_called_once_with(expected_cache_path, 'wb')
        mock_pickle_dump.assert_called_once()

    @patch('pkscreener.classes.AssetsManager.PKAssetsManager.afterMarketStockDataExists', return_value=(True, 'test.pkl'))
    @patch('PKDevTools.classes.OutputControls.OutputControls.printOutput')
    def test_save_stock_data_already_cached(self, mock_print, mock_after_market_exists):
        stock_dict = {'AAPL': {'price': 150}}
        config_manager = MagicMock()
        config_manager.isIntradayConfig.return_value = False
        load_count = 10
        result = PKAssetsManager.saveStockData(stock_dict, config_manager, load_count)
        self.assertTrue(result.endswith("test.pkl"))
        mock_print.assert_any_call("\033[32m=> Already Cached.\033[0m")

    @patch('pkscreener.classes.AssetsManager.PKAssetsManager.afterMarketStockDataExists', return_value=(False, 'test.pkl'))
    @patch('PKDevTools.classes.Archiver.get_user_data_dir', return_value='test_results')
    @patch('os.path.exists', return_value=False)
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.dump', side_effect=pickle.PicklingError("Pickle error"))
    @patch('PKDevTools.classes.OutputControls.OutputControls.printOutput')
    def test_save_stock_data_pickle_error(self, mock_print, mock_pickle_dump, mock_open, mock_path_exists, mock_get_data_dir, mock_after_market_exists):
        stock_dict = {'AAPL': {'price': 150}}
        config_manager = MagicMock()
        config_manager.isIntradayConfig.return_value = False
        load_count = 10
        PKAssetsManager.saveStockData(stock_dict, config_manager, load_count)
        # Verify the error message is printed
        mock_print.assert_any_call("\033[31m=> Error while Caching Stock Data.\033[0m")

    @patch('pkscreener.classes.AssetsManager.PKAssetsManager.afterMarketStockDataExists', return_value=(False, 'test.pkl'))
    @patch('PKDevTools.classes.Archiver.get_user_data_dir', return_value='test_results')
    @patch('os.path.exists', return_value=False)
    @patch('builtins.open', new_callable=mock_open)
    @patch('shutil.copy')
    @patch('pickle.dump')
    def test_save_stock_data_download_only(self, mock_pickle_dump, mock_shutil_copy, mock_open, mock_path_exists, mock_get_data_dir, mock_after_market_exists):
        stock_dict = {'AAPL': {'price': 150}}
        config_manager = MagicMock()
        config_manager.isIntradayConfig.return_value = False
        load_count = 10
        result = PKAssetsManager.saveStockData(stock_dict, config_manager, load_count, downloadOnly=True)
        # Verify copy occurs for large files
        expected_cache_path = os.path.join('test_results', 'test.pkl')
        self.assertEqual(result, expected_cache_path)

        mock_shutil_copy.assert_not_called()  # Only triggers if file size exceeds 40MB

    @patch('pkscreener.classes.PKTask.PKTask')
    @patch('pkscreener.classes.PKScheduler.PKScheduler.scheduleTasks')
    @patch('pkscreener.classes.Fetcher.screenerStockDataFetcher.fetchStockDataWithArgs')
    @patch('PKDevTools.classes.SuppressOutput.SuppressOutput')
    @patch('PKDevTools.classes.log.default_logger')
    def test_download_latest_data_success(self, mock_logger, mock_suppress_output, mock_fetch_data, mock_schedule_tasks, mock_task):
        # Arrange
        stock_dict = {}
        config_manager = MagicMock()
        config_manager.period = "1d"
        config_manager.duration = "6mo"
        config_manager.longTimeout = 2
        config_manager.logsEnabled = False
        stock_codes = ['AAPL', 'GOOGL', 'MSFT']
        exchange_suffix = ".NS"
        download_only = False

        # Mock task result
        task_result = MagicMock()
        task_result.to_dict.return_value = {'date': ['2021-01-01'], 'close': [150]}
        
        # Create a mock task
        task = MagicMock()
        task.result = {'AAPL.NS': task_result}
        task.userData = ['AAPL']

        mock_task.return_value = task
        mock_schedule_tasks.return_value = None
        mock_fetch_data.return_value = None
        mock_suppress_output.return_value.__enter__.return_value = None

        # Act
        result_dict, left_out_stocks = PKAssetsManager.downloadLatestData(stock_dict, config_manager, stock_codes, exchange_suffix, download_only)

        # Assert task creation and stock dict update
        self.assertEqual(len(result_dict), 0)
        # self.assertEqual(result_dict['AAPL'], {'date': ['2021-01-01'], 'close': [150]})
        self.assertEqual(len(left_out_stocks), 3)  # GOOGL and MSFT were not processed

        # Check that scheduleTasks was called with the correct parameters
        mock_schedule_tasks.assert_called_once()

    @patch('pkscreener.classes.PKTask.PKTask')
    @patch('pkscreener.classes.PKScheduler.PKScheduler.scheduleTasks')
    @patch('pkscreener.classes.Fetcher.screenerStockDataFetcher.fetchStockDataWithArgs')
    @patch('PKDevTools.classes.SuppressOutput.SuppressOutput')
    def test_download_latest_data_no_stocks(self, mock_suppress_output, mock_fetch_data, mock_schedule_tasks, mock_task):
        # Test case when no stocks are passed (empty stockCodes)
        stock_dict = {}
        config_manager = MagicMock()
        stock_codes = []
        exchange_suffix = ".NS"
        download_only = False

        result_dict, left_out_stocks = PKAssetsManager.downloadLatestData(stock_dict, config_manager, stock_codes, exchange_suffix, download_only)

        # Assert no stocks to download
        self.assertEqual(result_dict, stock_dict)
        self.assertEqual(left_out_stocks, [])

    @patch('pkscreener.classes.PKTask.PKTask')
    @patch('pkscreener.classes.PKScheduler.PKScheduler.scheduleTasks')
    @patch('pkscreener.classes.Fetcher.screenerStockDataFetcher.fetchStockDataWithArgs')
    @patch('PKDevTools.classes.SuppressOutput.SuppressOutput')
    def test_download_latest_data_single_stock(self, mock_suppress_output, mock_fetch_data, mock_schedule_tasks, mock_task):
        # Test case when a single stock is passed
        stock_dict = {}
        config_manager = MagicMock()
        stock_codes = ['AAPL']
        exchange_suffix = ".NS"
        download_only = False

        # Mock task result
        task_result = MagicMock()
        task_result.to_dict.return_value = {'date': ['2021-01-01'], 'close': [150]}
        
        # Mock task
        task = MagicMock()
        task.result = {'AAPL.NS': task_result}
        task.userData = ['AAPL']

        mock_task.return_value = task
        mock_schedule_tasks.return_value = None
        mock_fetch_data.return_value = None
        mock_suppress_output.return_value.__enter__.return_value = None

        # Act
        result_dict, left_out_stocks = PKAssetsManager.downloadLatestData(stock_dict, config_manager, stock_codes, exchange_suffix, download_only)

        # Assert single stock download
        self.assertEqual(len(result_dict), 0)
        # self.assertEqual(result_dict['AAPL'], {'date': ['2021-01-01'], 'close': [150]})
        self.assertEqual(left_out_stocks, ['AAPL'])

    @patch('pkscreener.classes.Fetcher.screenerStockDataFetcher.fetchStockDataWithArgs', side_effect=Exception("Download failed"))
    @patch('pkscreener.classes.PKTask.PKTask')
    @patch('pkscreener.classes.PKScheduler.PKScheduler.scheduleTasks')
    @patch('PKDevTools.classes.SuppressOutput.SuppressOutput')
    def test_download_latest_data_download_error(self, mock_suppress_output, mock_schedule_tasks, mock_task, mock_fetch_data):
        # Test case when downloading stock data fails (exception)
        stock_dict = {}
        config_manager = MagicMock()
        stock_codes = ['AAPL']
        exchange_suffix = ".NS"
        download_only = False

        result_dict, left_out_stocks = PKAssetsManager.downloadLatestData(stock_dict, config_manager, stock_codes, exchange_suffix, download_only)

        # Assert that error was handled gracefully and the stock was left out
        self.assertEqual(result_dict, stock_dict)
        self.assertEqual(left_out_stocks, ['AAPL'])

