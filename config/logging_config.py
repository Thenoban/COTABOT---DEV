"""
Logging Configuration with Rotation Support
Provides centralized logging setup with RotatingFileHandler
"""
import logging
import os
from logging.handlers import RotatingFileHandler
import sys


def setup_logging(log_level=None, log_file="bot.log", max_bytes=5*1024*1024, backup_count=5):
    """
    Configure logging with rotation and environment-based configuration
    
    Args:
        log_level (str): Log level (DEBUG, INFO, WARNING, ERROR). 
                        If None, reads from LOG_LEVEL env variable (default: INFO)
        log_file (str): Path to log file (default: "bot.log")
        max_bytes (int): Maximum file size in bytes before rotation (default: 5MB)
        backup_count (int): Number of backup files to keep (default: 5)
    
    Returns:
        logging.Logger: Configured root logger
    
    Example:
        >>> from config.logging_config import setup_logging
        >>> setup_logging()  # Uses INFO level from env or defaults
        >>> setup_logging(log_level="DEBUG")  # Force DEBUG level
    """
    # Get log level from env or default to INFO
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Get max bytes from env if available
    env_max_bytes = os.getenv("LOG_MAX_BYTES")
    if env_max_bytes:
        try:
            max_bytes = int(env_max_bytes)
        except ValueError:
            pass  # Use default
    
    # Get backup count from env if available
    env_backup_count = os.getenv("LOG_BACKUP_COUNT")
    if env_backup_count:
        try:
            backup_count = int(env_backup_count)
        except ValueError:
            pass  # Use default
    
    # Convert log level string to logging constant
    level = getattr(logging, log_level, logging.INFO)
    
    # Create formatters
    # Detailed format for file logs
    detailed_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Simpler format for console (no timestamp, already in Docker logs)
    simple_formatter = logging.Formatter(
        '[%(levelname)s] %(name)s: %(message)s'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler (simpler format for readability)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers (avoid duplicates)
    root_logger.handlers.clear()
    
    # Add new handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log the configuration
    root_logger.info(f"Logging configured: Level={log_level}, MaxSize={max_bytes/1024/1024:.1f}MB, Backups={backup_count}")
    
    return root_logger
