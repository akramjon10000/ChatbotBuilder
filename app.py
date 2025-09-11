import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
babel = Babel()
csrf = CSRFProtect()

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
csrf.init_app(app)

# Login manager settings
login_manager.login_view = 'login'
login_manager.login_message = 'Tizimga kirish talab qilinadi.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

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

babel.init_app(app, locale_selector=get_locale)

# Make get_locale available in templates
@app.context_processor
def inject_locale():
    return dict(get_locale=get_locale)

with app.app_context():
    # Import models
    import models
    
    # Create tables if they don't exist
    db.create_all()
    
    # Create admin user if not exists
    from models import User, AccessStatus
    from werkzeug.security import generate_password_hash
    
    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    
    if admin_username and admin_password:
        # Check if admin user already exists
        existing_admin = User.query.filter_by(username=admin_username).first()
        if not existing_admin:
            admin_user = User()
            admin_user.username = admin_username
            admin_user.email = f"{admin_username}@chatbot.uz"
            admin_user.password_hash = generate_password_hash(admin_password)
            admin_user.is_admin = True
            admin_user.admin_approved = True
            admin_user.is_trial_active = False
            admin_user.access_status = AccessStatus.APPROVED
            db.session.add(admin_user)
            db.session.commit()
            logging.info(f"Admin user created: {admin_username}")
        else:
            logging.info(f"Admin user already exists: {admin_username}")
    else:
        logging.warning("ADMIN_USERNAME or ADMIN_PASSWORD not set in environment variables")

# Import routes
from routes import *
from admin_routes import *

# Import admin panel
from admin_panel import admin
app.register_blueprint(admin)

# Start scheduler
from tasks.scheduler import start_scheduler
start_scheduler()