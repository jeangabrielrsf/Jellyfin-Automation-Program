"""Tests for logging configuration."""
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.logging_config import setup_logging, get_logger

def test_setup_logging_creates_logs_dir(tmp_path, monkeypatch):
    """Test that setup_logging creates logs directory and configures handlers."""
    monkeypatch.chdir(tmp_path)
    logs_dir = tmp_path / "logs"

    with patch('app.logging_config.logger') as mock_logger, \
         patch('app.logging_config.structlog') as mock_structlog:
        setup_logging()

        mock_logger.remove.assert_called_once()
        assert mock_logger.add.call_count == 2  # console + file
        mock_structlog.configure.assert_called_once()
        assert logs_dir.exists()

def test_get_logger_returns_bound_logger():
    """Test that get_logger returns a logger bound with the given name."""
    with patch('app.logging_config.logger') as mock_logger:
        mock_bound = MagicMock()
        mock_logger.bind.return_value = mock_bound
        
        result = get_logger("test")
        
        mock_logger.bind.assert_called_once_with(name="test")
        assert result is mock_bound
