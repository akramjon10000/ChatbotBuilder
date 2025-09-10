from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Trial system fields
    trial_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    trial_end_date = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=3))
    is_trial_active = db.Column(db.Boolean, default=True)
    admin_approved = db.Column(db.Boolean, default=False)
    access_granted_date = db.Column(db.DateTime)
    
    # User profile
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    preferred_language = db.Column(db.String(2), default='uz')
    
    # Admin and status
    is_admin = db.Column(db.Boolean, default=False)
    _is_active = db.Column('is_active', db.Boolean, default=True)
    
    @property
    def is_active(self):
        return self._is_active
    
    @is_active.setter
    def is_active(self, value):
        self._is_active = value
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    bots = db.relationship('Bot', backref='owner', lazy=True, cascade='all, delete-orphan')
    admin_actions = db.relationship('AdminAction', foreign_keys='AdminAction.user_id', backref='target_user', lazy=True)
    
    @property
    def trial_days_left(self):
        if not self.is_trial_active or self.admin_approved:
            return 0
        if self.trial_end_date:
            delta = self.trial_end_date - datetime.utcnow()
            return max(0, delta.days)
        return 0
    
    @property
    def has_access(self):
        return self.admin_approved or (self.is_trial_active and self.trial_days_left > 0)
    
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
    telegram_token = db.Column(db.String(200))
    telegram_webhook_url = db.Column(db.String(300))
    whatsapp_token = db.Column(db.String(200))
    instagram_token = db.Column(db.String(200))
    
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Action details
    action_type = db.Column(db.String(50), nullable=False)  # GRANT_ACCESS, REVOKE_ACCESS
    reason = db.Column(db.Text)
    
    # Metadata
    action_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    admin = db.relationship('User', foreign_keys=[admin_id], backref='performed_actions')
    
    def __repr__(self):
        return f'<AdminAction {self.action_type}>'

class SystemStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    
    # Statistics
    total_users = db.Column(db.Integer, default=0)
    active_trials = db.Column(db.Integer, default=0)
    approved_users = db.Column(db.Integer, default=0)
    total_bots = db.Column(db.Integer, default=0)
    total_messages = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemStats {self.date}>'
