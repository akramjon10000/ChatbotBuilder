from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import logging

from app import app, db
from models import User, Bot, Conversation, Message, KnowledgeBase, AdminAction
from services.ai_service import AIService
from utils.helpers import allowed_file, detect_language

# Initialize AI service
ai_service = AIService()

@app.route('/')
def index():
    """Ana sahifa"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/set_language/<language>')
def set_language(language):
    """Tilni o'zgartirish"""
    if language in app.config['LANGUAGES']:
        session['language'] = language
    return redirect(request.referrer or url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Ro'yxatdan o'tish"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        
        # Validation
        if User.query.filter_by(username=username).first():
            flash('Bu foydalanuvchi nomi band', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Bu email manzil ro\'yxatdan o\'tgan', 'error')
            return render_template('auth/register.html')
        
        # Create new user with 3-day trial
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            full_name=full_name,
            phone=phone,
            trial_start_date=datetime.utcnow(),
            trial_end_date=datetime.utcnow() + timedelta(days=3),
            is_trial_active=True,
            preferred_language=session.get('language', 'uz')
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Ro\'yxatdan o\'tish muvaffaqiyatli! 3 kunlik bepul sinov boshlandi.', 'success')
        login_user(user)
        return redirect(url_for('dashboard'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Tizimga kirish"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Sizning hisobingiz faol emas', 'error')
                return render_template('auth/login.html')
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Noto\'g\'ri foydalanuvchi nomi yoki parol', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    """Tizimdan chiqish"""
    logout_user()
    flash('Tizimdan muvaffaqiyatli chiqdingiz', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Foydalanuvchi paneli"""
    # Check if user has access
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
    
    # Get user's bots
    bots = Bot.query.filter_by(user_id=current_user.id).all()
    
    # Get recent conversations
    recent_conversations = []
    if bots:
        bot_ids = [bot.id for bot in bots]
        recent_conversations = Conversation.query.filter(
            Conversation.bot_id.in_(bot_ids)
        ).order_by(Conversation.updated_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         bots=bots,
                         recent_conversations=recent_conversations,
                         trial_days_left=current_user.trial_days_left)

@app.route('/trial_expired')
@login_required
def trial_expired():
    """Sinov muddati tugagan sahifa"""
    if current_user.has_access:
        return redirect(url_for('dashboard'))
    
    return render_template('trial_expired.html')

@app.route('/bot/create', methods=['GET', 'POST'])
@login_required
def create_bot():
    """Chatbot yaratish"""
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        system_prompt = request.form.get('system_prompt')
        languages = ','.join(request.form.getlist('languages'))
        
        bot = Bot(
            name=name,
            description=description,
            system_prompt=system_prompt,
            languages=languages,
            user_id=current_user.id
        )
        
        db.session.add(bot)
        db.session.commit()
        
        flash('Chatbot muvaffaqiyatli yaratildi!', 'success')
        return redirect(url_for('bot_detail', bot_id=bot.id))
    
    return render_template('bot/create.html')

@app.route('/bot/<int:bot_id>')
@login_required
def bot_detail(bot_id):
    """Chatbot tafsilotlari"""
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
    
    bot = Bot.query.get_or_404(bot_id)
    
    # Check ownership
    if bot.user_id != current_user.id:
        flash('Bu chatbotga ruxsatingiz yo\'q', 'error')
        return redirect(url_for('dashboard'))
    
    # Get conversations
    conversations = Conversation.query.filter_by(bot_id=bot.id).order_by(
        Conversation.updated_at.desc()
    ).limit(10).all()
    
    # Get knowledge base
    knowledge_files = KnowledgeBase.query.filter_by(
        bot_id=bot.id, is_active=True
    ).all()
    
    return render_template('bot/detail.html',
                         bot=bot,
                         conversations=conversations,
                         knowledge_files=knowledge_files)

@app.route('/bot/<int:bot_id>/chat', methods=['GET', 'POST'])
@login_required
def bot_chat(bot_id):
    """Chatbot bilan suhbat"""
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
    
    bot = Bot.query.get_or_404(bot_id)
    
    # Check ownership
    if bot.user_id != current_user.id:
        flash('Bu chatbotga ruxsatingiz yo\'q', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        message_content = request.form.get('message')
        
        if message_content:
            # Detect language
            detected_language = detect_language(message_content)
            
            # Get or create conversation
            conversation = Conversation.query.filter_by(
                bot_id=bot.id,
                platform='web',
                platform_user_id=str(current_user.id)
            ).first()
            
            if not conversation:
                conversation = Conversation(
                    bot_id=bot.id,
                    platform='web',
                    platform_user_id=str(current_user.id),
                    platform_username=current_user.username,
                    language=detected_language
                )
                db.session.add(conversation)
                db.session.flush()
            
            # Save user message
            user_message = Message(
                conversation_id=conversation.id,
                content=message_content,
                is_from_user=True
            )
            db.session.add(user_message)
            
            # Get AI response
            try:
                start_time = datetime.utcnow()
                ai_response = ai_service.generate_response(
                    message_content,
                    bot.system_prompt,
                    detected_language,
                    conversation.id
                )
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Save AI response
                ai_message = Message(
                    conversation_id=conversation.id,
                    content=ai_response,
                    is_from_user=False,
                    response_time=response_time
                )
                db.session.add(ai_message)
                
            except Exception as e:
                logging.error(f"AI response error: {e}")
                ai_message = Message(
                    conversation_id=conversation.id,
                    content="Kechirasiz, hozir javob bera olmayman. Iltimos, keyinroq urinib ko'ring.",
                    is_from_user=False
                )
                db.session.add(ai_message)
            
            db.session.commit()
    
    # Get conversation messages
    conversation = Conversation.query.filter_by(
        bot_id=bot.id,
        platform='web',
        platform_user_id=str(current_user.id)
    ).first()
    
    messages = []
    if conversation:
        messages = Message.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Message.created_at.asc()).all()
    
    return render_template('chat.html', bot=bot, messages=messages)

@app.route('/bot/<int:bot_id>/upload_knowledge', methods=['POST'])
@login_required
def upload_knowledge(bot_id):
    """Bilim bazasi faylini yuklash"""
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
    
    bot = Bot.query.get_or_404(bot_id)
    
    # Check ownership
    if bot.user_id != current_user.id:
        flash('Bu chatbotga ruxsatingiz yo\'q', 'error')
        return redirect(url_for('dashboard'))
    
    if 'file' not in request.files:
        flash('Fayl tanlanmagan', 'error')
        return redirect(url_for('bot_detail', bot_id=bot_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('Fayl tanlanmagan', 'error')
        return redirect(url_for('bot_detail', bot_id=bot_id))
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(app.root_path, 'uploads', 'knowledge')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file
            unique_filename = f"{datetime.utcnow().timestamp()}_{filename}"
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            
            # Read file content
            content = ""
            if filename.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            # Create knowledge base entry
            kb = KnowledgeBase(
                bot_id=bot.id,
                filename=unique_filename,
                original_filename=filename,
                file_type=file.content_type,
                file_size=os.path.getsize(file_path),
                content=content
            )
            
            db.session.add(kb)
            db.session.commit()
            
            flash('Fayl muvaffaqiyatli yuklandi!', 'success')
            
        except Exception as e:
            logging.error(f"File upload error: {e}")
            flash('Fayl yuklashda xatolik yuz berdi', 'error')
    else:
        flash('Fayl turi qo\'llab-quvvatlanmaydi', 'error')
    
    return redirect(url_for('bot_detail', bot_id=bot_id))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Foydalanuvchi profili"""
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        current_user.preferred_language = request.form.get('preferred_language')
        
        # Change password if provided
        new_password = request.form.get('new_password')
        if new_password:
            current_user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        flash('Profil muvaffaqiyatli yangilandi!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
