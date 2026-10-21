"""
Logging configuration for Blood Bank Management System
"""
import logging
import os
from logging.handlers import RotatingFileHandler

_CONFIGURED = False


def setup_logging(app):
    """Attach rotating-file and console handlers to the root logger.

    Handlers go on the *root* logger rather than app.logger: every module in
    this project logs through get_logger(__name__), and those loggers
    propagate to root. Attaching only to app.logger would silently discard
    all of them.
    """
    global _CONFIGURED

    log_level_name = app.config.get('LOG_LEVEL', 'INFO')
    log_file = app.config.get('LOG_FILE', 'logs/app.log')
    log_level = getattr(logging, str(log_level_name).upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    if _CONFIGURED:
        # Reloader and test fixtures re-enter this; don't stack duplicate handlers.
        return

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root.addHandler(console_handler)

    log_dir = os.path.dirname(log_file) or '.'
    try:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root.addHandler(file_handler)
    except OSError as exc:
        # A read-only filesystem (some container setups) shouldn't stop the app.
        console_handler.handle(logging.LogRecord(
            name=__name__, level=logging.WARNING, pathname=__file__, lineno=0,
            msg=f'File logging disabled: {exc}', args=(), exc_info=None
        ))

    # app.logger propagates to root, so it inherits the handlers above.
    app.logger.handlers.clear()
    app.logger.propagate = True
    app.logger.setLevel(log_level)

    # Keep the request access log out of the way.
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    _CONFIGURED = True

    logger = logging.getLogger(__name__)
    logger.info('=' * 72)
    logger.info('Blood Bank Management System - Logging Started')
    logger.info(f'Log Level: {log_level_name}  |  Log File: {log_file}')
    logger.info('=' * 72)


def get_logger(name):
    """Get a logger instance"""
    return logging.getLogger(name)
