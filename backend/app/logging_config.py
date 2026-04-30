"""Logging configuration with structured logs and rotation."""
import sys
from pathlib import Path
from loguru import logger
import structlog
from app.config import get_settings

CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

def setup_logging() -> "loguru.Logger":
    """Configure application logging."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Console handler - human readable in development
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format=CONSOLE_FORMAT,
        colorize=True,
    )
    
    # File handler - JSON structured for machine parsing
    logger.add(
        logs_dir / "app.log",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention=5,
        compression="zip",
        enqueue=True,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logger.info("Logging configured", level=settings.log_level)
    
    return logger

def get_logger(name: str) -> "loguru.Logger":
    """Get a logger instance with the given name."""
    return logger.bind(name=name)
