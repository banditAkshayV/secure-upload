from flask import Flask, session, request, abort
from .limits import limiter
from flask_limiter.util import get_remote_address
from .models import db
from .routes import main_bp
import os
import secrets
import hmac
import hashlib
from datetime import datetime, timedelta
from PIL import Image
import warnings

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")
    app.secret_key = "wvgoeiw7tyo784vyot7cy0w78y4c78yi8fcybh7bh7cose8n"

    # CSRF Configuration
    CSRF_SECRET_KEY = "sbilhhhlbgviushrgiuiubsuilrsiulvislvulvruisghbliugflisgrliuvsgui"  # Change this!
    CSRF_TOKEN_LIFETIME = 3600  # 1 hour in seconds

    def generate_csrf_token():
        """Generate a secure CSRF token without storing it in session/cookie"""
        # Create timestamp
        timestamp = str(int(datetime.utcnow().timestamp()))
        
        # Generate random data
        random_data = secrets.token_hex(16)
        
        # Create the payload
        payload = f"{timestamp}:{random_data}"
        
        # Create HMAC signature
        signature = hmac.new(
            CSRF_SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Return the complete token
        return f"{payload}:{signature}"

    def validate_csrf_token(token):
        """Validate CSRF token without relying on session storage"""
        if not token:
            return False
            
        try:
            # Split the token
            parts = token.split(':')
            if len(parts) != 3:
                return False
                
            timestamp_str, random_data, signature = parts
            
            # Recreate the payload
            payload = f"{timestamp_str}:{random_data}"
            
            # Verify the signature
            expected_signature = hmac.new(
                CSRF_SECRET_KEY.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return False
            
            # Check if token is still valid (not expired)
            token_time = datetime.fromtimestamp(int(timestamp_str))
            current_time = datetime.utcnow()
            
            if (current_time - token_time).total_seconds() > CSRF_TOKEN_LIFETIME:
                return False
                
            return True
            
        except (ValueError, TypeError):
            return False

    # Make token generator available in templates
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.before_request
    def csrf_protect():
        """CSRF protection for POST requests"""
        if request.method == "POST":
            # Get token from form
            form_token = request.form.get("csrf_token")
            
            if not validate_csrf_token(form_token):
                abort(403, "CSRF token missing or invalid")

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

    # Configure Pillow to guard against decompression bombs
    # Set max pixels and elevate warnings to errors
    Image.MAX_IMAGE_PIXELS = app.config.get("IMAGE_MAX_PIXELS")
    warnings.simplefilter('error', Image.DecompressionBombWarning)
    
    # Additional aggressive protection
    Image.MAX_IMAGE_PIXELS = min(Image.MAX_IMAGE_PIXELS, 25000000)  # Hard cap at 25M pixels
    Image.MAX_IMAGE_PIXELS = max(Image.MAX_IMAGE_PIXELS, 1000000)   # Minimum 1M pixels

    db.init_app(app)

    # Create tables if not exist
    with app.app_context():
        db.create_all()

    # Rate limiting
    limiter.init_app(app)
    
    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        security_headers = app.config.get('SECURITY_HEADERS', {})
        for header, value in security_headers.items():
            response.headers[header] = value
        return response
    
    # Additional security measures
    @app.before_request
    def security_checks():
        """Perform security checks before each request."""
        # Block requests with suspicious headers
        suspicious_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Forwarded-Host',
            'X-Forwarded-Proto'
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                app.logger.warning(f"Suspicious header detected: {header}")
                #abort(400, description="Suspicious request")

    app.register_blueprint(main_bp)
    return app