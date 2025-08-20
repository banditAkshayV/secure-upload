import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # Use environment variables for all sensitive configuration
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        # Provide a fallback for development, but warn about it
        import warnings
        warnings.warn(
            "SECRET_KEY not set in environment. Using development fallback. "
            "Set SECRET_KEY environment variable for production use."
        )
        SECRET_KEY = "dev-secret-key-change-in-production"
    
    # Database configuration - prefer explicit DATABASE_URL; otherwise build from env vars
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # All database credentials must come from environment variables
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_PORT = os.getenv("MYSQL_PORT")
        MYSQL_DB = os.getenv("MYSQL_DB")
        
        # Validate required environment variables
        if not all([MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB]):
            # Provide fallback for development
            warnings.warn(
                "Database environment variables not set. Using development defaults. "
                "Set proper database credentials for production use."
            )
            MYSQL_USER = os.getenv("MYSQL_USER", "spider1")
            MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "whiskey")
            MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
            MYSQL_DB = os.getenv("MYSQL_DB", "secure_app")
        
        # Set defaults for optional values
        MYSQL_PORT = int(MYSQL_PORT) if MYSQL_PORT else 3306
        
        # URL encode password to handle special characters
        from urllib.parse import quote_plus
        pw = quote_plus(MYSQL_PASSWORD)
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{pw}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
        )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before use
        'pool_recycle': 300,    # Recycle connections every 5 minutes
        'connect_args': {
            'charset': 'utf8mb4',
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'
        }
    }

    # Upload settings
    BASE_DIR = os.path.abspath(os.path.dirname(__file__) + "/..")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "5")) * 1024 * 1024  # Configurable max file size
    ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}
    ALLOWED_MIME_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    
    # Rate limiting configuration
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    
    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }
