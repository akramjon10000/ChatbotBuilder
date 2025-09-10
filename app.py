import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_babel import Babel
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
babel = Babel()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///chatbot_platform.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Babel configuration
app.config['LANGUAGES'] = {
    'uz': 'O\'zbek',
    'ru': 'Русский', 
    'en': 'English'
}
app.config['BABEL_DEFAULT_LOCALE'] = 'uz'
app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
babel.init_app(app)

# Login manager settings
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Tizimga kirish talab qilinadi.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

@babel.locale_selector
def get_locale():
    from flask import request, session
    # Check if language is set in session
    if 'language' in session and session['language'] in app.config['LANGUAGES']:
        return session['language']
    # Check if language is in URL parameters
    if 'lang' in request.args and request.args['lang'] in app.config['LANGUAGES']:
        session['language'] = request.args['lang']
        return request.args['lang']
    # Default to Uzbek
    return 'uz'

with app.app_context():
    # Import models
    import models
    # Create all tables
    db.create_all()
    
    # Create admin user if not exists
    from models import User
    from werkzeug.security import generate_password_hash
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin_user = User(
            username='admin',
            email='admin@chatbot.uz',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            admin_approved=True,
            is_trial_active=False
        )
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Admin user created: admin/admin123")

# Import routes
from routes import *
from admin_routes import *

# Start scheduler
from tasks.scheduler import start_scheduler
start_scheduler()
