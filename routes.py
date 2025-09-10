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
from services.platform_service import TelegramService, PlatformManager
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
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not username or not email or not password:
            flash('Barcha majburiy maydonlarni to\'ldiring', 'error')
            return render_template('auth/register.html')
            
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Foydalanuvchi nomi va parolni kiriting', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.password_hash and check_password_hash(user.password_hash, password):
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

@app.route('/bot/<int:bot_id>', methods=['GET', 'POST'])
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
    if not file.filename or file.filename == '':
        flash('Fayl tanlanmagan', 'error')
        return redirect(url_for('bot_detail', bot_id=bot_id))
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename or '')
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

# Platform integrations and webhook handlers

@app.route('/webhook/telegram/<int:bot_id>', methods=['POST'])
def telegram_webhook(bot_id):
    """Telegram webhook handler"""
    try:
        # Get bot
        bot = Bot.query.get_or_404(bot_id)
        
        # Check if bot has telegram token
        if not bot.telegram_token:
            logging.error(f"Bot {bot_id} has no Telegram token")
            return "No token", 400
        
        # Get incoming message data
        data = request.get_json()
        
        if not data or 'message' not in data:
            return "No message", 400
        
        message = data['message']
        chat_id = message['chat']['id']
        user_message = message.get('text', '')
        
        if not user_message:
            return "Empty message", 400
        
        # Detect language
        detected_language = detect_language(user_message)
        
        # Create or get conversation
        conversation = Conversation.query.filter_by(
            bot_id=bot.id,
            platform='telegram',
            platform_user_id=str(chat_id)
        ).first()
        
        if not conversation:
            conversation = Conversation(
                bot_id=bot.id,
                platform='telegram',
                platform_user_id=str(chat_id),
                user_name=message['from'].get('first_name', 'Unknown'),
                language=detected_language
            )
            db.session.add(conversation)
            db.session.commit()
        
        # Save user message
        user_msg = Message(
            conversation_id=conversation.id,
            content=user_message,
            is_from_user=True,
            language=detected_language
        )
        db.session.add(user_msg)
        
        # Get conversation history for context
        history = Message.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        # Generate AI response
        try:
            if len(history) > 1:
                response_text = ai_service.generate_response_with_context(
                    user_message, 
                    history[1:], 
                    bot.system_prompt,
                    detected_language
                )
            else:
                response_text = ai_service.generate_response(
                    user_message,
                    bot.system_prompt,
                    detected_language
                )
        except Exception as e:
            logging.error(f"AI service error: {e}")
            response_text = ai_service._get_fallback_response(detected_language)
        
        # Save bot response
        bot_msg = Message(
            conversation_id=conversation.id,
            content=response_text,
            is_from_user=False,
            language=detected_language
        )
        db.session.add(bot_msg)
        
        # Update conversation
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Send response via Telegram
        telegram_service = TelegramService(bot.telegram_token)
        result = telegram_service.send_message(chat_id, response_text)
        
        if result and result.get('ok'):
            logging.info(f"Telegram message sent successfully to chat {chat_id}")
            return "OK", 200
        else:
            logging.error(f"Failed to send Telegram message: {result}")
            return "Send failed", 500
            
    except Exception as e:
        logging.error(f"Telegram webhook error: {e}")
        db.session.rollback()
        return "Error", 500

@app.route('/bot/<int:bot_id>/deploy_telegram', methods=['POST'])
@login_required
def deploy_telegram(bot_id):
    """Deploy bot to Telegram"""
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
        
    bot = Bot.query.get_or_404(bot_id)
    
    # Check ownership
    if bot.user_id != current_user.id:
        flash('Bu chatbotga ruxsatingiz yo\'q', 'error')
        return redirect(url_for('dashboard'))
    
    telegram_token = request.form.get('telegram_token', '').strip()
    
    if not telegram_token:
        flash('Telegram bot token kiritilmagan', 'error')
        return redirect(url_for('bot_detail', bot_id=bot_id))
    
    try:
        # Initialize Telegram service
        telegram_service = TelegramService(telegram_token)
        
        # Check if token is valid
        bot_info = telegram_service.get_bot_info()
        if not bot_info or not bot_info.get('ok'):
            flash('Telegram bot token noto\'g\'ri yoki yaroqsiz', 'error')
            return redirect(url_for('bot_detail', bot_id=bot_id))
        
        # Set webhook URL
        webhook_url = f"{request.host_url}webhook/telegram/{bot_id}"
        webhook_result = telegram_service.set_webhook(webhook_url)
        
        if webhook_result and webhook_result.get('ok'):
            # Save token to bot
            bot.telegram_token = telegram_token
            bot.telegram_webhook_url = webhook_url
            bot.is_active = True
            db.session.commit()
            
            flash(f'Telegram bot muvaffaqiyatli ulandi! Bot nomi: {bot_info["result"]["first_name"]}', 'success')
        else:
            flash('Webhook o\'rnatishda xatolik', 'error')
            
    except Exception as e:
        logging.error(f"Telegram deployment error: {e}")
        flash('Telegram botni ulashda xatolik yuz berdi', 'error')
    
    return redirect(url_for('bot_detail', bot_id=bot_id))

@app.route('/bot/<int:bot_id>/disconnect_telegram', methods=['POST'])
@login_required
def disconnect_telegram(bot_id):
    """Disconnect bot from Telegram"""
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
        
    bot = Bot.query.get_or_404(bot_id)
    
    # Check ownership
    if bot.user_id != current_user.id:
        flash('Bu chatbotga ruxsatingiz yo\'q', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if bot.telegram_token:
            # Remove webhook
            telegram_service = TelegramService(bot.telegram_token)
            telegram_service.set_webhook('')  # Empty URL removes webhook
            
            # Clear token and webhook URL
            bot.telegram_token = None
            bot.telegram_webhook_url = None
            db.session.commit()
            
            flash('Telegram bot muvaffaqiyatli uzildi', 'success')
        else:
            flash('Bot Telegram bilan ulanmagan', 'warning')
            
    except Exception as e:
        logging.error(f"Telegram disconnect error: {e}")
        flash('Telegram botni uzishda xatolik', 'error')
    
    return redirect(url_for('bot_detail', bot_id=bot_id))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
