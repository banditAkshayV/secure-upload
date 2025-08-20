from flask import Flask
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

    app.register_blueprint(main_bp)
    return app
