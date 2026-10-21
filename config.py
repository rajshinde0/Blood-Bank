"""
Configuration settings for Blood Bank Management System
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SECRET_KEY = 'dev-secret-key-change-in-production'


def env_bool(name, default=False):
    """Read a boolean from the environment.

    os.getenv always hands back a string, and a non-empty string is truthy -
    so 'False' would otherwise enable the flag it was meant to disable.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def env_int(name, default):
    """Read an int from the environment, falling back on anything unparseable"""
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', DEFAULT_SECRET_KEY)

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///blood_bank.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = env_bool('SQLALCHEMY_ECHO', False)

    # Session - SESSION_TIMEOUT is expressed in seconds
    PERMANENT_SESSION_LIFETIME = timedelta(seconds=env_int('SESSION_TIMEOUT', 3600))
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Logging
    LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

    # Security
    PASSWORD_HASH_METHOD = os.getenv('PASSWORD_HASH_METHOD', 'pbkdf2:sha256')

    # CSRF. The token stays valid for as long as the session does - a separate
    # expiry would silently break a dashboard that was left open, and the
    # session lifetime above is already the real bound.
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Cache
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300

    # SocketIO
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_CORS_ALLOWED_ORIGINS = ['*']

    # Pagination
    ITEMS_PER_PAGE = env_int('ITEMS_PER_PAGE', 20)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    def __init__(self):
        if self.SECRET_KEY == DEFAULT_SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY is still the development default. Set a real "
                "SECRET_KEY in the environment before running in production."
            )


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')

    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig
    }

    config_class = config_map.get(env, DevelopmentConfig)

    # Instantiating ProductionConfig runs its secret-key guard; the others are
    # inert, and Flask's from_object() accepts an instance just as happily.
    return config_class()
