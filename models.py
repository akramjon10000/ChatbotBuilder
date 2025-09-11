from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
import enum

class AccessStatus(enum.Enum):
    TRIAL = "trial"           # 3 kunlik sinov
    PENDING = "pending"       # Sinov tugagan, admin ruxsatini kutmoqda
    APPROVED = "approved"     # Admin ruxsat bergan
    SUSPENDED = "suspended"   # Admin dostupni to'xtatgan

class AdminActionType(enum.Enum):
    GRANT_ACCESS = "grant_access"
    REVOKE_ACCESS = "revoke_access"
    EXTEND_TRIAL = "extend_trial"
    SUSPEND_USER = "suspend_user"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # SINOV TIZIMI
    trial_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    trial_end_date = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=3))
    is_trial_active = db.Column(db.Boolean, default=True)
    
    # ADMIN NAZORATI
    admin_approved = db.Column(db.Boolean, default=False)
    access_granted_date = db.Column(db.DateTime)
    access_status = db.Column(db.Enum(AccessStatus), default=AccessStatus.TRIAL)
    
    # FOYDALANUVCHI MA'LUMOTLARI
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    preferred_language = db.Column(db.String(5), default='uz')
    
    # ADMIN VA HOLAT
    is_admin = db.Column(db.Boolean, default=False)
    _is_active = db.Column('is_active', db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    @property
    def is_active(self):
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        self._is_active = value
    
    # RELATIONSHIPS
    bots = db.relationship('Bot', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    @property
    def trial_days_left(self):
        """Sinov kunlari qolganini hisoblash"""
        if self.access_status != AccessStatus.TRIAL or self.admin_approved:
            return 0
        if self.trial_end_date:
            delta = self.trial_end_date - datetime.utcnow()
            return max(0, delta.days)
        return 0
    
    @property
    def has_access(self):
        """Foydalanuvchi dostupini tekshirish"""
        if self.is_admin:
            return True
        if self.access_status == AccessStatus.APPROVED:
            return True
        if self.access_status == AccessStatus.TRIAL:
            return self.trial_days_left > 0
        return False
    
    @property
    def status_display(self):
        """Holat nomini chiqarish"""
        if self.is_admin:
            return "Administrator"
        elif self.access_status == AccessStatus.TRIAL:
            if self.trial_days_left > 0:
                return f"Sinov ({self.trial_days_left} kun qoldi)"
            else:
                return "Sinov tugagan"
        elif self.access_status == AccessStatus.PENDING:
            return "Admin ruxsatini kutmoqda"
        elif self.access_status == AccessStatus.APPROVED:
            return "Tasdiqlangan"
        elif self.access_status == AccessStatus.SUSPENDED:
            return "To'xtatilgan"
        return "Noma'lum"
    
    def set_password(self, password):
        """Parol o'rnatish"""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Parolni tekshirish"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Bot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Bot configuration
    system_prompt = db.Column(db.Text)
    languages = db.Column(db.String(20), default='uz,ru,en')  # Comma-separated
    
    # Platform integrations
    telegram_token = db.Column(db.String(500))
    telegram_webhook_url = db.Column(db.String(300))
    whatsapp_token = db.Column(db.String(500))
    instagram_token = db.Column(db.String(500))
    instagram_page_id = db.Column(db.String(100))
    
    # Monitoring settings
    admin_chat_id = db.Column(db.String(100))  # Admin's personal Telegram chat ID
    notification_channel = db.Column(db.String(100))  # Telegram channel for team notifications
    
    # Settings
    is_active = db.Column(db.Boolean, default=True)
    max_daily_messages = db.Column(db.Integer, default=100)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship('Conversation', backref='bot', lazy=True, cascade='all, delete-orphan')
    knowledge_base = db.relationship('KnowledgeBase', backref='bot', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Bot {self.name}>'

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'), nullable=False)
    platform = db.Column(db.String(20), nullable=False)  # telegram, whatsapp, instagram
    platform_user_id = db.Column(db.String(100), nullable=False)
    platform_username = db.Column(db.String(100))
    
    # Conversation data
    language = db.Column(db.String(2), default='uz')
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Conversation {self.platform}:{self.platform_user_id}>'

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    
    # Message content
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, image, document
    is_from_user = db.Column(db.Boolean, nullable=False)
    
    # AI response data
    tokens_used = db.Column(db.Integer, default=0)
    response_time = db.Column(db.Float, default=0.0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}>'

class KnowledgeBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'), nullable=False)
    
    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    
    # Content
    content = db.Column(db.Text)
    summary = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<KnowledgeBase {self.original_filename}>'

class AdminAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # HARAKAT MA'LUMOTLARI
    action_type = db.Column(db.Enum(AdminActionType), nullable=False)
    reason = db.Column(db.Text)
    
    # METADATA
    action_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # RELATIONSHIPS (relationships will be added after all models are defined)
    # admin va target_user relationships are defined later
    
    @property
    def action_display(self):
        """Harakat nomini chiqarish"""
        action_names = {
            AdminActionType.GRANT_ACCESS: "Ruxsat berish",
            AdminActionType.REVOKE_ACCESS: "Ruxsatni olib qo'yish",
            AdminActionType.EXTEND_TRIAL: "Sinovni uzaytirish",
            AdminActionType.SUSPEND_USER: "Foydalanuvchini to'xtatish"
        }
        return action_names.get(self.action_type, str(self.action_type))
    
    def __repr__(self):
        return f'<AdminAction {self.action_type}>'

class SystemStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=lambda: datetime.utcnow().date())
    
    # STATISTIKALAR
    total_users = db.Column(db.Integer, default=0)
    active_trials = db.Column(db.Integer, default=0)
    pending_users = db.Column(db.Integer, default=0)
    approved_users = db.Column(db.Integer, default=0)
    suspended_users = db.Column(db.Integer, default=0)
    total_bots = db.Column(db.Integer, default=0)
    total_conversations = db.Column(db.Integer, default=0)
    total_messages = db.Column(db.Integer, default=0)
    
    # METADATA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemStats {self.date}>'
