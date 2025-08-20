from flask_sqlalchemy import SQLAlchemy
import os
import re

db = SQLAlchemy()

def validate_filename(filename):
    """Validate and sanitize filename to prevent path traversal attacks."""
    if not filename:
        return None
    
    # Remove path traversal attempts
    filename = os.path.basename(filename)
    
    # Remove null bytes and control characters
    filename = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', filename)
    
    # Only allow alphanumeric, dots, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return None
    
    # Limit length
    if len(filename) > 255:
        return None
    
    return filename

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    
    def __repr__(self):
        return f"<Comment {self.id}>"

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"<Entry {self.id}>"
