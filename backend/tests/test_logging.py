"""Tests for logging configuration."""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.logging_config import setup_logging, get_logger

def test_setup_logging_creates_logs_dir():
    """Test that setup_logging creates logs directory."""
    # Remove logs dir if exists
    if Path("logs").exists():
        import shutil
        shutil.rmtree("logs")
    
    with patch('app.logging_config.logger'):
        setup_logging()
        assert Path("logs").exists()

def test_get_logger_returns_logger():
    """Test that get_logger returns a logger instance."""
    logger = get_logger("test")
    assert logger is not None
