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
from unittest.mock import patch, MagicMock
import os


class TestTelegramNotifier:
    """Test cases for TelegramNotifier class."""
    
    @pytest.fixture
    def mock_user_args(self):
        """Create mock user arguments."""
        mock = MagicMock()
        mock.log = False
        mock.telegram = False
        mock.user = "12345"
        mock.monitor = False
        mock.options = "X:1:2"
        return mock
    
    @pytest.fixture
    def notifier(self, mock_user_args):
        """Create a TelegramNotifier instance."""
        from pkscreener.classes.TelegramNotifier import TelegramNotifier
        return TelegramNotifier(mock_user_args)
    
    def test_initialization(self, mock_user_args):
        """Test TelegramNotifier initialization."""
        from pkscreener.classes.TelegramNotifier import TelegramNotifier
        
        notifier = TelegramNotifier(mock_user_args)
        
        assert notifier.user_passed_args is mock_user_args
        assert notifier.test_messages_queue == []
        assert notifier.media_group_dict == {}
    
    def test_initialization_with_custom_queue(self, mock_user_args):
        """Test initialization with custom message queue."""
        from pkscreener.classes.TelegramNotifier import TelegramNotifier
        
        custom_queue = ["message1", "message2"]
        custom_dict = {"key": "value"}
        
        notifier = TelegramNotifier(mock_user_args, custom_queue, custom_dict)
        
        assert notifier.test_messages_queue == custom_queue
        assert notifier.media_group_dict == custom_dict
    
    def test_dev_channel_id_constant(self, mock_user_args):
        """Test that DEV_CHANNEL_ID is correctly set."""
        from pkscreener.classes.TelegramNotifier import TelegramNotifier
        
        notifier = TelegramNotifier(mock_user_args)
        
        assert notifier.DEV_CHANNEL_ID == "-1001785195297"
    
    def test_add_attachment(self, notifier):
        """Test adding an attachment."""
        notifier.add_attachment("/path/to/file.png", "Test caption & special")
        
        assert "ATTACHMENTS" in notifier.media_group_dict
        assert len(notifier.media_group_dict["ATTACHMENTS"]) == 1
        assert notifier.media_group_dict["ATTACHMENTS"][0]["FILEPATH"] == "/path/to/file.png"
        assert notifier.media_group_dict["ATTACHMENTS"][0]["CAPTION"] == "Test caption n special"
    
    def test_add_multiple_attachments(self, notifier):
        """Test adding multiple attachments."""
        notifier.add_attachment("/path/to/file1.png", "Caption 1")
        notifier.add_attachment("/path/to/file2.png", "Caption 2")
        
        assert len(notifier.media_group_dict["ATTACHMENTS"]) == 2
    
    def test_set_caption(self, notifier):
        """Test setting the main caption."""
        notifier.set_caption("Main caption text")
        
        assert notifier.media_group_dict["CAPTION"] == "Main caption text"
    
    def test_send_test_status_success(self, notifier):
        """Test sending success status."""
        screen_results = pd.DataFrame({'Stock': ['SBIN', 'HDFC']})
        
        with patch.object(notifier, 'send_message_to_telegram') as mock_send:
            notifier.send_test_status(screen_results, "Test Label", "12345")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "<b>SUCCESS</b>" in call_args[1]['message']
            assert "2 Stocks" in call_args[1]['message']
    
    def test_send_test_status_fail(self, notifier):
        """Test sending fail status with no results."""
        with patch.object(notifier, 'send_message_to_telegram') as mock_send:
            notifier.send_test_status(None, "Test Label", "12345")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "<b>FAIL</b>" in call_args[1]['message']
    
    def test_send_test_status_empty_results(self, notifier):
        """Test sending fail status with empty results."""
        screen_results = pd.DataFrame()
        
        with patch.object(notifier, 'send_message_to_telegram') as mock_send:
            notifier.send_test_status(screen_results, "Test Label", "12345")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "<b>FAIL</b>" in call_args[1]['message']


class TestTelegramNotifierSendMessage:
    """Test cases for send_message_to_telegram method."""
    
    @pytest.fixture
    def mock_user_args(self):
        """Create mock user arguments."""
        mock = MagicMock()
        mock.log = True
        mock.telegram = False
        mock.user = "12345"
        mock.monitor = False
        mock.options = "X:1:2"
        return mock
    
    def test_send_message_not_in_runner_mode(self, mock_user_args):
        """Test that message is not sent when not in runner mode and log is false."""
        from pkscreener.classes.TelegramNotifier import TelegramNotifier
        
        mock_user_args.log = False
        notifier = TelegramNotifier(mock_user_args)
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('pkscreener.classes.TelegramNotifier.send_message') as mock_send:
                notifier.send_message_to_telegram(message="Test message")
                
                # Message should not be sent when not in runner mode
                mock_send.assert_not_called()
    
    def test_send_message_with_telegram_flag(self, mock_user_args):
        """Test that message is not sent when telegram flag is set."""
        from pkscreener.classes.TelegramNotifier import TelegramNotifier
        
        mock_user_args.telegram = True
        notifier = TelegramNotifier(mock_user_args)
        
        with patch('pkscreener.classes.TelegramNotifier.send_message') as mock_send:
            notifier.send_message_to_telegram(message="Test message")
            
            mock_send.assert_not_called()


class TestTelegramNotifierQuickScanResult:
    """Test cases for send_quick_scan_result method."""
    
    @pytest.fixture
    def mock_user_args(self):
        """Create mock user arguments."""
        mock = MagicMock()
        mock.log = True
        mock.telegram = False
        mock.user = "12345"
        mock.monitor = False
        mock.options = "X:1:2"
        return mock
    
    def test_quick_scan_result_not_configured(self, mock_user_args):
        """Test quick scan result when not configured."""
        from pkscreener.classes.TelegramNotifier import TelegramNotifier
        
        notifier = TelegramNotifier(mock_user_args)
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('pkscreener.classes.TelegramNotifier.is_token_telegram_configured') as mock_config:
                mock_config.return_value = False
                
                # Should return early when not configured
                notifier.send_quick_scan_result(
                    menu_choice_hierarchy="X > 1 > 2",
                    user="12345",
                    tabulated_results="results",
                    markdown_results="markdown",
                    caption="Test caption",
                    png_name="test",
                    png_extension=".png"
                )
                
                # No exception should be raised


class TestTelegramNotifierAlertSubscriptions:
    """Test cases for alert subscription handling."""
    
    @pytest.fixture
    def notifier(self):
        """Create a TelegramNotifier instance."""
        from pkscreener.classes.TelegramNotifier import TelegramNotifier
        
        mock_user_args = MagicMock()
        mock_user_args.log = True
        mock_user_args.user = "12345"
        mock_user_args.monitor = False
        return TelegramNotifier(mock_user_args)
    
    def test_handle_alert_subscriptions_no_pipe(self, notifier):
        """Test alert handling when no pipe in message."""
        with patch('pkscreener.classes.TelegramNotifier.send_message') as mock_send:
            notifier._handle_alert_subscriptions("12345", "Simple message")
            
            # Should not send any message
            mock_send.assert_not_called()
    
    def test_handle_alert_subscriptions_negative_user(self, notifier):
        """Test alert handling with negative user ID (group)."""
        with patch('pkscreener.classes.TelegramNotifier.send_message') as mock_send:
            notifier._handle_alert_subscriptions("-12345", "Message | with pipe")
            
            # Should not send for group users
            mock_send.assert_not_called()
    
    def test_handle_alert_subscriptions_none_user(self, notifier):
        """Test alert handling with None user."""
        with patch('pkscreener.classes.TelegramNotifier.send_message') as mock_send:
            notifier._handle_alert_subscriptions(None, "Message | with pipe")
            
            mock_send.assert_not_called()





