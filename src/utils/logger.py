"""
Logging utilities for the video analysis system.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup logger with consistent formatting and file rotation."""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with basic rotation
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)
    
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_path / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    except ImportError:
        # Fallback to basic file handler
        file_handler = logging.FileHandler(log_path / "app.log")
    
    file_handler.setLevel(getattr(logging, level))
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
      return logger
    except Exception:
        # If file logging fails, continue with console only
        pass
    
    return logger
