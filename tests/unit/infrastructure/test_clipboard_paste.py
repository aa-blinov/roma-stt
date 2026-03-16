"""Infrastructure: paste text to clipboard and send Ctrl+V."""

from unittest.mock import patch

from infrastructure.clipboard_paste import paste_text


@patch("infrastructure.clipboard_paste.pyperclip.copy")
@patch("infrastructure.clipboard_paste.send_keys_ctrl_v")
def test_paste_text_copies_then_sends_ctrl_v(mock_send, mock_copy):
    paste_text("Hello")
    mock_copy.assert_called_once_with("Hello")
    mock_send.assert_called_once()


@patch("infrastructure.clipboard_paste.pyperclip.copy")
@patch("infrastructure.clipboard_paste.send_keys_ctrl_v")
def test_paste_text_handles_empty_string(mock_send, mock_copy):
    paste_text("")
    mock_copy.assert_called_once_with("")
    mock_send.assert_called_once()
