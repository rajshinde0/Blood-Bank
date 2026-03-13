"""
Logging configuration for Blood Bank Management System
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from config import Config


def setup_logging(app):
    """Setup logging for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Get log level from config
    log_level = getattr(Config, 'LOG_LEVEL', 'INFO')
    log_file = getattr(Config, 'LOG_FILE', 'logs/app.log')
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup file handler (logs to file)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level))
    
    # Setup console handler (logs to console)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level))
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(getattr(logging, log_level))
    
    # Set werkzeug logger to be less verbose
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.WARNING)
    
    app.logger.info('=' * 80)
    app.logger.info('Blood Bank Management System - Logging Started')
    app.logger.info(f'Log Level: {log_level}')
    app.logger.info(f'Log File: {log_file}')
    app.logger.info('=' * 80)


def get_logger(name):
    """Get a logger instance"""
    return logging.getLogger(name)
