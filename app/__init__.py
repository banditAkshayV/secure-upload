from flask import Flask, request, abort
from .limits import limiter
from flask_limiter.util import get_remote_address
from .models import db
from .routes import main_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

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
                abort(400, description="Suspicious request")

    app.register_blueprint(main_bp)
    return app
