import pymysql
import pymysql.cursors
from flask import current_app
import os
from contextlib import contextmanager

def get_db_connection():
    """Get database connection using environment variables or config"""
    config = current_app.config
    
    # Try to get connection details from config
    if hasattr(config, 'MYSQL_USER'):
        user = config.MYSQL_USER
        password = config.MYSQL_PASSWORD
        host = config.MYSQL_HOST
        port = config.MYSQL_PORT
        database = config.MYSQL_DB
    else:
        # Fallback to environment variables
        user = os.getenv("MYSQL_USER", "spider1")
        password = os.getenv("MYSQL_PASSWORD", "whiskey")
        host = os.getenv("MYSQL_HOST", "127.0.0.1")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        database = os.getenv("MYSQL_DB", "secure_app")
    
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )
    
    return connection

@contextmanager
def get_db_cursor():
    """Context manager for database operations"""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        yield cursor
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        cursor.close()
        connection.close()

def create_tables():
    """Create database tables if they don't exist"""
    with get_db_cursor() as cursor:
        # Create Entry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entry (
                id INT AUTO_INCREMENT PRIMARY KEY,
                text TEXT,
                image_filename VARCHAR(255)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Create Comment table (if needed)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comment (
                id INT AUTO_INCREMENT PRIMARY KEY,
                text TEXT NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

def insert_entry(text, image_filename):
    """Insert a new entry into the database"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO entry (text, image_filename) 
            VALUES (%s, %s)
        """, (text, image_filename))
        return cursor.lastrowid

def get_recent_entries(limit=100):
    """Get recent entries from database"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, text, image_filename
            FROM entry 
            ORDER BY id DESC 
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()

def get_total_entries_count():
    """Get total count of entries"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) as count FROM entry")
        result = cursor.fetchone()
        return result['count'] if result else 0
