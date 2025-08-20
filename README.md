# secure-upload
Secure application immutable to file upload and SQL injection attacks

## Environment Variables

Copy `env.example` to `.env` and configure the following variables:

### Required
- `SECRET_KEY`: Flask secret key (generate a strong random key)
- Database credentials (either `DATABASE_URL` or individual MySQL variables)

### Database Configuration
```bash
# Option 1: Complete DATABASE_URL
DATABASE_URL=mysql+pymysql://user:password@host:port/database?charset=utf8mb4

# Option 2: Individual variables
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DB=your_database_name
```

### Optional
- `MAX_CONTENT_LENGTH`: Maximum file size in MB (default: 5)
- `RATELIMIT_STORAGE_URL`: Rate limiting storage backend

## Installation

1. Clone the repository
2. Copy `env.example` to `.env` and configure your environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Initialize the database
5. Run the application: `python run.py`
