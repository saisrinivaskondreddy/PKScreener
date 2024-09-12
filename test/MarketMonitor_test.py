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
import unittest
import pandas as pd
from unittest.mock import patch, MagicMock
import pytest

from pkscreener.classes.MarketMonitor import MarketMonitor

class TestMarketMonitor(unittest.TestCase):
    
    def setUp(self):
        self.market_monitor = MarketMonitor(monitors=['Monitor1', 'Monitor2'])

    def test_currentMonitorOption(self):
        # Positive test case
        option = self.market_monitor.currentMonitorOption()
        self.assertEqual(option, 'Monitor1')
        
        # Test wrapping around monitor index
        self.market_monitor.monitorIndex = 1
        option = self.market_monitor.currentMonitorOption()
        self.assertEqual(option, 'Monitor2')
        
        option = self.market_monitor.currentMonitorOption()
        self.assertEqual(option, 'Monitor1')  # Should wrap back to the first monitor

    # def test_saveMonitorResultStocks(self):
    #     # Positive test case
    #     results_df = pd.DataFrame(index=['AAPL', 'GOOGL'])
    #     self.market_monitor.saveMonitorResultStocks(results_df)
    #     self.assertIn('1', self.market_monitor.monitorResultStocks)
    #     self.assertEqual(self.market_monitor.monitorResultStocks['1'], 'AAPL,GOOGL')
        
    #     # Negative test case with empty DataFrame
    #     results_df = pd.DataFrame()
    #     self.market_monitor.saveMonitorResultStocks(results_df)
    #     self.assertIn('1', self.market_monitor.monitorResultStocks)
    #     self.assertEqual(self.market_monitor.monitorResultStocks['1'], 'NONE')

    # def test_refresh(self):
    #     # Positive test case with valid DataFrame
    #     screen_df = pd.DataFrame({
    #         'Stock': ['AAPL', 'GOOGL'],
    #         'LTP': [150, 2800],
    #         '%Chng': ['1% (up)', '2% (up)'],
    #         '52Wk-H': [200, 2900],
    #         'RSI': [70, 65],
    #         'Volume': [1000, 2000]
    #     })
    #     self.market_monitor.refresh(screen_df=screen_df, screenOptions='Monitor1', chosenMenu='Menu1')
    #     self.assertFalse(self.market_monitor.monitor_df.empty)

    #     # Negative test case with empty DataFrame
    #     self.market_monitor.refresh(screen_df=None, screenOptions=None)
    #     self.assertTrue(self.market_monitor.monitor_df.empty)

    def test_updateDataFrameForTelegramMode(self):
        # Positive test case
        screen_monitor_df = pd.DataFrame({
            'Stock': ['AAPL', 'GOOGL'],
            'LTP': [150, 2800],
            'Ch%': ['1% (up)', '2% (up)'],
            'Vol': ['1000x', '2000x']
        })
        telegram_df = self.market_monitor.updateDataFrameForTelegramMode(telegram=True, screen_monitor_df=screen_monitor_df)
        self.assertEqual(telegram_df.shape[0], 2)  # Should return a DataFrame with 2 rows

        # Negative test case
        telegram_df = self.market_monitor.updateDataFrameForTelegramMode(telegram=False, screen_monitor_df=screen_monitor_df)
        self.assertIsNone(telegram_df)

    def test_getScanOptionName(self):
        # Positive test case
        option_name = self.market_monitor.getScanOptionName("X:12:9:2.5:>|X:0:31:")
        self.assertEqual(option_name, "P_1_3:")  # Assuming predefined scan exists

        # Negative test case with invalid input
        option_name = self.market_monitor.getScanOptionName(None)
        self.assertEqual(option_name, "")
