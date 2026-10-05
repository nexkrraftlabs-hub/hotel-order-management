"""Application configuration module."""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database (Neon PostgreSQL, Render Postgres, or SQLite fallback)
    _db_env = os.environ.get('DATABASE_URL')
    if _db_env and not _db_env.startswith('sqlite:///instance'):
        # Render and older tools use 'postgres://', SQLAlchemy 1.4+ requires 'postgresql://'
        if _db_env.startswith('postgres://'):
            _db_env = _db_env.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = _db_env
    else:
        _db_path = os.path.join(basedir, "instance", "restaurant.db").replace('\\', '/')
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{_db_path}'
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,  # Recommended for serverless databases like Neon
    }
    
    # Cloudinary configuration (for cloud media & uploaded assets)
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(basedir, 'app', 'static', 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE', 5 * 1024 * 1024))  # 5MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Domains & Base URLs
    APP_BASE_URL = os.environ.get('APP_BASE_URL') or 'https://hotel-order-management-zdnb.onrender.com/'
    CUSTOMER_DOMAIN = os.environ.get('CUSTOMER_DOMAIN', 'localhost:5000')
    ADMIN_DOMAIN = os.environ.get('ADMIN_DOMAIN', 'admin.localhost:5000')
    KITCHEN_DOMAIN = os.environ.get('KITCHEN_DOMAIN', 'kitchen.localhost:5000')
    WAITER_DOMAIN = os.environ.get('WAITER_DOMAIN', 'waiter.localhost:5000')
    
    # Business
    TAX_PERCENT = float(os.environ.get('TAX_PERCENT', 10.0))
    SERVICE_CHARGE_PERCENT = float(os.environ.get('SERVICE_CHARGE_PERCENT', 5.0))
    CURRENCY_SYMBOL = os.environ.get('CURRENCY_SYMBOL', '₹')
    
    # Token
    TOKEN_START = int(os.environ.get('TOKEN_START', 1))
    TOKEN_END = int(os.environ.get('TOKEN_END', 50))
    
    # SocketIO
    SOCKETIO_ASYNC_MODE = os.environ.get('SOCKETIO_ASYNC_MODE', 'threading')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}
