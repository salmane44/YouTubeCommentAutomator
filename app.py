import os
import logging
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up the base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Initialize Flask app
app = Flask(__name__, 
    static_folder='static',
    static_url_path='/static'
)

# Configure the app
app.secret_key = os.environ.get("SESSION_SECRET")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'google_auth.login'  # Redirect to Google login

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_APP_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
    app.logger.error('Email configuration missing in .env file')
else:
    app.logger.info(f'Email configured for: {app.config["MAIL_USERNAME"]}')

mail = Mail(app)

# Initialize OAuth
oauth = OAuth(app)

# Google OAuth Config
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.force-ssl https://www.googleapis.com/auth/youtube.readonly'
    }
)

# Initialize the database
db.init_app(app)
migrate = Migrate(app, db)

# Import models after db initialization to avoid circular imports
from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Error handlers
@app.errorhandler(Exception)
def handle_exception(e):
    """Log unhandled exceptions and return a generic error message"""
    app.logger.error("Unhandled Exception", exc_info=e)
    return jsonify({"error": "Internal Server Error", "type": str(type(e).__name__)}), 500

# Serve static files from attached_assets
@app.route('/attached_assets/<path:filename>')
def serve_attached_asset(filename):
    return send_from_directory('attached_assets', filename)

# Import views after app initialization to avoid circular imports
with app.app_context():
    from views import *  # This will handle regular routes
    from google_auth import auth_blueprint  # Import renamed blueprint

    # Register blueprints
    app.register_blueprint(auth_blueprint)

    # Create all tables
    db.create_all()