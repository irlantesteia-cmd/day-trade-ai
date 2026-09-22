from unittest.mock import patch, MagicMock
import pytest
from src.api.webhook import WebhookDispatcher


def test_dispatcher_no_url():
    dispatcher = WebhookDispatcher()
    assert dispatcher.dispatch({"test": "data"}) is False


@patch("urllib.request.urlopen")
def test_dispatch_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    dispatcher = WebhookDispatcher(default_url="http://localhost/webhook")
    result = dispatcher.dispatch({"event": "ping"})

    assert result is True
    assert mock_urlopen.called


@patch("urllib.request.urlopen")
def test_send_alert(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    dispatcher = WebhookDispatcher(default_url="http://localhost/webhook")
    result = dispatcher.send_alert(
        title="Risco Elevado",
        message="Drawdown ultrapassou limite",
        level="WARNING",
    )

    assert result is True


@patch("urllib.request.urlopen")
def test_send_report(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    dispatcher = WebhookDispatcher(default_url="http://localhost/webhook")
    result = dispatcher.send_report(report_markdown="# Relatorio Executivo")

    assert result is True