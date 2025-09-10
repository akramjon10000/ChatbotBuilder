import os
import re
import logging
from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin huquqlari talab qilinadi', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def trial_required(f):
    """Decorator to require active trial or admin approval"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        
        if not current_user.has_access:
            return redirect(url_for('trial_expired'))
        
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'json', 'csv'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_language(text):
    """Detect language of the text"""
    try:
        # Simple language detection based on character patterns
        if not text:
            return 'uz'
        
        # Count specific characters for each language
        uzbek_chars = set('qxʻoʻgʻ')
        russian_chars = set('ёяю')
        
        uzbek_count = sum(1 for char in text.lower() if char in uzbek_chars)
        russian_count = sum(1 for char in text.lower() if char in russian_chars)
        
        # Check for Cyrillic characters
        cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        
        if russian_count > 0 or cyrillic_count > len(text) * 0.3:
            return 'ru'
        elif uzbek_count > 0:
            return 'uz'
        elif any(ord(char) > 127 for char in text):
            return 'uz'  # Default to Uzbek for non-ASCII
        else:
            return 'en'  # Default to English for ASCII
            
    except Exception as e:
        logging.error(f"Language detection error: {e}")
        return 'uz'  # Default to Uzbek

def format_datetime(dt, format_type='full'):
    """Format datetime for display"""
    if not dt:
        return ''
    
    if format_type == 'date':
        return dt.strftime('%d.%m.%Y')
    elif format_type == 'time':
        return dt.strftime('%H:%M')
    elif format_type == 'short':
        return dt.strftime('%d.%m.%Y %H:%M')
    else:  # full
        return dt.strftime('%d.%m.%Y %H:%M:%S')

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format"""
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (9-15 digits)
    return 9 <= len(digits_only) <= 15

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def get_user_trial_status(user):
    """Get detailed trial status for a user"""
    if user.is_admin:
        return {
            'status': 'admin',
            'message': 'Administrator',
            'class': 'success'
        }
    
    if user.admin_approved:
        return {
            'status': 'approved',
            'message': 'Tasdiqlangan',
            'class': 'success'
        }
    
    if user.is_trial_active:
        days_left = user.trial_days_left
        if days_left > 0:
            return {
                'status': 'trial_active',
                'message': f'{days_left} kun qoldi',
                'class': 'warning' if days_left <= 1 else 'info'
            }
        else:
            return {
                'status': 'trial_expired',
                'message': 'Sinov muddati tugagan',
                'class': 'danger'
            }
    
    return {
        'status': 'unknown',
        'message': 'Noma\'lum holat',
        'class': 'secondary'
    }

def create_upload_directory(directory_type='general'):
    """Create upload directory if it doesn't exist"""
    upload_dir = os.path.join(current_app.root_path, 'uploads', directory_type)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

def log_user_action(user_id, action, details=None):
    """Log user action for audit trail"""
    try:
        message = f"User {user_id}: {action}"
        if details:
            message += f" - {details}"
        logging.info(message)
    except Exception as e:
        logging.error(f"Error logging user action: {e}")
