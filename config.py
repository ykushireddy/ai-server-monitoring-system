"""
Application configuration module.
Supports multiple environments: development, testing, production.
Database can be SQLite (default) or MySQL via environment variables.
"""
import os
from datetime import timedelta
# Base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
class Config:
    """Base configuration class with default settings."""
    
    # Flask core settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'server-monitoring-secret-key-change-in-production'
    
    # Database configuration
    # Default: SQLite, can switch to MySQL via DATABASE_URL environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(BASE_DIR, 'database', 'monitoring.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Monitoring settings
    MONITORING_INTERVAL = int(os.environ.get('MONITORING_INTERVAL', 5))  # seconds
    METRICS_RETENTION_DAYS = int(os.environ.get('METRICS_RETENTION_DAYS', 30))
    
    # Alert thresholds
    CPU_WARNING_THRESHOLD = float(os.environ.get('CPU_WARNING_THRESHOLD', 70.0))
    CPU_CRITICAL_THRESHOLD = float(os.environ.get('CPU_CRITICAL_THRESHOLD', 90.0))
    MEMORY_WARNING_THRESHOLD = float(os.environ.get('MEMORY_WARNING_THRESHOLD', 75.0))
    MEMORY_CRITICAL_THRESHOLD = float(os.environ.get('MEMORY_CRITICAL_THRESHOLD', 90.0))
    DISK_WARNING_THRESHOLD = float(os.environ.get('DISK_WARNING_THRESHOLD', 80.0))
    DISK_CRITICAL_THRESHOLD = float(os.environ.get('DISK_CRITICAL_THRESHOLD', 95.0))
    
    # Machine Learning settings
    ML_RETRAIN_INTERVAL = int(os.environ.get('ML_RETRAIN_INTERVAL', 3600))  # 1 hour
    ML_CONTAMINATION = float(os.environ.get('ML_CONTAMINATION', 0.05))  # 5% expected anomalies
    ML_MIN_SAMPLES = int(os.environ.get('ML_MIN_SAMPLES', 100))  # minimum samples for training
    
    # Email settings (simulation mode by default)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'alerts@monitoring.local')
    MAIL_RECIPIENTS = os.environ.get('MAIL_RECIPIENTS', 'admin@monitoring.local').split(',')
    MAIL_SIMULATION_MODE = os.environ.get('MAIL_SIMULATION_MODE', 'true').lower() == 'true'
    
    # Logging settings
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'monitoring.log')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Report settings
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
    
    # Pagination
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 25))

    # Admin authentication (change in production)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set to True to see SQL queries
class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    MONITORING_INTERVAL = 60  # Slower for testing
class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
def get_config():
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.environ.get('FLASK_ENV', 'development')
    cfg_class = config.get(env, config['default'])

    if env == 'production':
        secret = os.environ.get('SECRET_KEY')
        if not secret:
            raise ValueError(
                'SECRET_KEY environment variable must be set in production'
            )
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if not admin_password:
            raise ValueError(
                'ADMIN_PASSWORD environment variable must be set in production'
            )

        class ProductionConfigResolved(ProductionConfig):
            SECRET_KEY = secret
            ADMIN_PASSWORD = admin_password

        return ProductionConfigResolved

    return cfg_class