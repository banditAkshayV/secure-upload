import os

class Config:
    SECRET_KEY = "KMCTMWlCVXgY3yc5pQjRjfhcoldHVRL8"  # Change in prod
    # Prefer explicit DATABASE_URL; otherwise build a MySQL URI from env vars
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        MYSQL_USER = os.getenv("MYSQL_USER", "root")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "whiskey")
        MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
        MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
        MYSQL_DB = os.getenv("MYSQL_DB", "secure_app")

        # URL encode password if needed
        from urllib.parse import quote_plus
        pw = quote_plus(MYSQL_PASSWORD)
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{pw}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload settings
    BASE_DIR = os.path.abspath(os.path.dirname(__file__) + "/..")
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}
    ALLOWED_MIME_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
