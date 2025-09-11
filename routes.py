from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import logging
import csv
import hashlib
import hmac

from app import app, db, limiter, csrf
from models import User, Bot, Conversation, Message, KnowledgeBase, AdminAction
from services.ai_service import AIService
from services.platform_service import TelegramService, InstagramService, PlatformManager
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
@limiter.limit("5 per minute")
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
@limiter.limit("10 per minute")
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
                         trial_days_left=current_user.trial_days_left,
                         subscription_days_left=current_user.subscription_days_left,
                         is_subscription_member=current_user.is_subscription_member,
                         subscription_label=current_user.subscription_label)

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
    
    # Handle POST requests for bot updates and platform integrations
    if request.method == 'POST':
        platform = request.form.get('platform')
        
        if platform == 'instagram':
            # Handle Instagram token and page_id update
            instagram_token = request.form.get('instagram_token', '').strip()
            instagram_page_id = request.form.get('instagram_page_id', '').strip()
            
            if instagram_token and instagram_page_id:
                bot.instagram_token = instagram_token
                bot.instagram_page_id = instagram_page_id
                db.session.commit()
                
                # Instagram webhook URL - user needs to set this in Facebook Developer Console
                webhook_url = f"{request.host_url}webhook/instagram/{bot.id}"
                flash(f'Instagram token va Page ID saqlandi! Webhook URL: {webhook_url}', 'success')
            else:
                bot.instagram_token = None
                bot.instagram_page_id = None
                db.session.commit()
                flash('Instagram ma\'lumotlari o\'chirildi', 'info')
        
        elif platform == 'whatsapp':
            # Handle WhatsApp token update
            whatsapp_token = request.form.get('whatsapp_token', '').strip()
            if whatsapp_token:
                bot.whatsapp_token = whatsapp_token
                db.session.commit()
                flash('WhatsApp token muvaffaqiyatli saqlandi!', 'success')
            else:
                bot.whatsapp_token = None
                db.session.commit()
                flash('WhatsApp token o\'chirildi', 'info')
        
        elif platform == 'telegram_notifications':
            # Handle Telegram notification settings update
            admin_chat_id = request.form.get('admin_chat_id', '').strip()
            notification_channel = request.form.get('notification_channel', '').strip()
            
            bot.admin_chat_id = admin_chat_id if admin_chat_id else None
            bot.notification_channel = notification_channel if notification_channel else None
            db.session.commit()
            flash('Telegram bildirishnoma sozlamalari yangilandi!', 'success')
        
        else:
            # Handle regular bot updates (name, description, etc.)
            name = request.form.get('name')
            description = request.form.get('description')
            system_prompt = request.form.get('system_prompt')
            languages = ','.join(request.form.getlist('languages'))
            max_daily_messages = request.form.get('max_daily_messages', type=int)
            is_active = 'is_active' in request.form
            
            if name:
                bot.name = name
                bot.description = description
                bot.system_prompt = system_prompt
                bot.languages = languages
                bot.max_daily_messages = max_daily_messages
                bot.is_active = is_active
                bot.updated_at = datetime.utcnow()
                db.session.commit()
                flash('Bot ma\'lumotlari yangilandi!', 'success')
        
        return redirect(url_for('bot_detail', bot_id=bot.id))
    
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
                    bot.id
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
            elif filename.endswith('.csv'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    csv_reader = csv.reader(f)
                    rows = []
                    for row in csv_reader:
                        rows.append(','.join(row))
                    content = '\n'.join(rows)
            
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

@app.route('/knowledge-guide')
@login_required
def knowledge_guide():
    """Bilimlar bazasi yo'riqnomasi"""
    return render_template('knowledge_guide.html')

# Platform integrations and webhook handlers

@app.route('/webhook/telegram/<int:bot_id>', methods=['POST'])
@csrf.exempt
@limiter.limit("100 per minute")
def telegram_webhook(bot_id):
    """Telegram webhook handler"""
    try:
        # Get bot
        bot = Bot.query.get_or_404(bot_id)
        
        # Verify webhook signature for security
        if bot.telegram_token:
            telegram_secret = hashlib.sha256(bot.telegram_token.encode()).digest()
            signature = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
            if signature:
                # Verify the signature matches
                expected = hmac.new(telegram_secret, request.get_data(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(signature, expected):
                    logging.warning(f"Invalid Telegram webhook signature for bot {bot_id}")
                    return "Unauthorized", 401
        
        # Check if bot has telegram token
        if not bot.telegram_token:
            logging.error(f"Bot {bot_id} has no Telegram token")
            return "No token", 400
        
        # Get incoming message data
        data = request.get_json()
        
        # Handle callback queries (inline keyboard responses)
        if 'callback_query' in data:
            return handle_telegram_callback(bot, data['callback_query'])
        
        if not data or 'message' not in data:
            return "No message", 400
        
        message = data['message']
        chat_id = message['chat']['id']
        user_message = message.get('text', '')
        
        if not user_message:
            return "Empty message", 400
        
        # Handle special commands first
        if user_message.startswith('/'):
            return handle_telegram_command(bot, chat_id, user_message, message)
        
        # Create or get conversation
        conversation = Conversation.query.filter_by(
            bot_id=bot.id,
            platform='telegram',
            platform_user_id=str(chat_id)
        ).first()
        
        # Extract username from message
        telegram_username = message['from'].get('username')
        user_display_name = message['from'].get('first_name', 'Unknown')
        
        if not conversation:
            # Detect language for new conversations
            detected_language = detect_language(user_message)
            conversation = Conversation(
                bot_id=bot.id,
                platform='telegram',
                platform_user_id=str(chat_id),
                platform_username=telegram_username or user_display_name,
                language=detected_language
            )
            db.session.add(conversation)
            db.session.commit()
        else:
            # Update username if it exists and is different
            if telegram_username and conversation.platform_username != telegram_username:
                conversation.platform_username = telegram_username
                db.session.commit()
        
        # Use the conversation's language preference
        user_language = conversation.language
        
        # Save user message
        user_msg = Message(
            conversation_id=conversation.id,
            content=user_message,
            is_from_user=True
        )
        db.session.add(user_msg)
        
        # Get conversation history for context
        history = Message.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        # Generate AI response using user's language preference and knowledge base
        try:
            if len(history) > 1:
                response_text = ai_service.generate_response_with_context(
                    user_message, 
                    history[1:], 
                    bot.system_prompt,
                    user_language,
                    bot.id
                )
            else:
                response_text = ai_service.generate_response(
                    user_message,
                    bot.system_prompt,
                    user_language,
                    bot.id
                )
        except Exception as e:
            logging.error(f"AI service error: {e}")
            response_text = ai_service._get_fallback_response(user_language)
        
        # Save bot response
        bot_msg = Message(
            conversation_id=conversation.id,
            content=response_text,
            is_from_user=False
        )
        db.session.add(bot_msg)
        
        # Update conversation
        conversation.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Send response via Telegram
        telegram_service = TelegramService(bot.telegram_token)
        result = telegram_service.send_message(chat_id, response_text)
        
        if result and result.success:
            logging.info(f"Telegram message sent successfully to chat {chat_id}")
            
            # Send monitoring notification if configured
            send_monitoring_notification(bot, conversation, user_message, response_text, 'telegram')
            
            return "OK", 200
        else:
            logging.error(f"Failed to send Telegram message: {result}")
            return "Send failed", 500
            
    except Exception as e:
        logging.error(f"Telegram webhook error: {e}")
        db.session.rollback()
        return "Error", 500

def send_monitoring_notification(bot, conversation, user_message, bot_response, platform):
    """Send monitoring notification to admin chat or channel"""
    try:
        if not bot.telegram_token:
            return
            
        telegram_service = TelegramService(bot.telegram_token)
        
        # Format notification message
        platform_emoji = {'telegram': '💬', 'instagram': '📸', 'whatsapp': '💚'}.get(platform, '🤖')
        
        # Format username safely with @ symbol
        if conversation.platform_username:
            username = f"@{conversation.platform_username}"
        else:
            username = "Noma'lum"
        
        notification_text = f"""
{platform_emoji} {platform.title()} Conversation

👤 Foydalanuvchi: {username}
🆔 Chat ID: {conversation.platform_user_id}
🤖 Bot: {bot.name}

📝 Foydalanuvchi xabari:
{user_message}

🤖 Bot javobi:
{bot_response}

🕐 Vaqt: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""

        # Send to admin chat if configured
        if bot.admin_chat_id:
            try:
                telegram_service.send_message(bot.admin_chat_id, notification_text)
                logging.info(f"Monitoring notification sent to admin chat {bot.admin_chat_id}")
            except Exception as e:
                logging.error(f"Failed to send notification to admin chat: {e}")
        
        # Send to notification channel if configured
        if bot.notification_channel:
            try:
                telegram_service.send_message(bot.notification_channel, notification_text)
                logging.info(f"Monitoring notification sent to channel {bot.notification_channel}")
            except Exception as e:
                logging.error(f"Failed to send notification to channel: {e}")
                
    except Exception as e:
        logging.error(f"Monitoring notification error: {e}")

@app.route('/webhook/instagram/<int:bot_id>', methods=['GET', 'POST'])
@limiter.limit("100 per minute")
def instagram_webhook(bot_id):
    """Instagram webhook handler"""
    
    # Handle GET request for webhook verification
    if request.method == 'GET':
        verify_token = "your_verify_token"  # This should match your Instagram webhook config
        
        challenge = request.args.get('hub.challenge')
        verify_token_param = request.args.get('hub.verify_token')
        
        if verify_token_param == verify_token:
            return challenge
        else:
            return "Forbidden", 403
    
    # Handle POST request for incoming messages
    try:
        # Get bot
        bot = Bot.query.get_or_404(bot_id)
        
        # Check if bot has instagram token
        if not bot.instagram_token:
            logging.error(f"Bot {bot_id} has no Instagram token")
            return "No token", 400
        
        # Get incoming message data
        data = request.get_json()
        
        if not data or 'entry' not in data:
            return "No entry", 400
        
        # Process each entry
        for entry in data['entry']:
            if 'messaging' in entry:
                for messaging_event in entry['messaging']:
                    if 'message' in messaging_event:
                        message = messaging_event['message']
                        sender_id = messaging_event['sender']['id']
                        
                        # Skip if no text in message
                        if 'text' not in message:
                            continue
                            
                        user_message = message['text']
                        
                        # Create or get conversation
                        conversation = Conversation.query.filter_by(
                            bot_id=bot.id,
                            platform='instagram',
                            platform_user_id=str(sender_id)
                        ).first()
                        
                        if not conversation:
                            # Detect language for new conversations
                            detected_language = detect_language(user_message)
                            conversation = Conversation(
                                bot_id=bot.id,
                                platform='instagram',
                                platform_user_id=str(sender_id),
                                platform_username='Instagram User',
                                language=detected_language
                            )
                            db.session.add(conversation)
                            db.session.commit()
                        
                        # Use the conversation's language preference
                        user_language = conversation.language
                        
                        # Save user message
                        user_msg = Message(
                            conversation_id=conversation.id,
                            content=user_message,
                            is_from_user=True
                        )
                        db.session.add(user_msg)
                        
                        # Get conversation history for context
                        history = Message.query.filter_by(
                            conversation_id=conversation.id
                        ).order_by(Message.created_at.desc()).limit(10).all()
                        
                        # Generate AI response using user's language preference and knowledge base
                        try:
                            if len(history) > 1:
                                response_text = ai_service.generate_response_with_context(
                                    user_message, 
                                    history[1:], 
                                    bot.system_prompt,
                                    user_language,
                                    bot.id
                                )
                            else:
                                response_text = ai_service.generate_response(
                                    user_message,
                                    bot.system_prompt,
                                    user_language,
                                    bot.id
                                )
                        except Exception as e:
                            logging.error(f"AI service error: {e}")
                            response_text = ai_service._get_fallback_response(user_language)
                        
                        # Save bot response
                        bot_msg = Message(
                            conversation_id=conversation.id,
                            content=response_text,
                            is_from_user=False
                        )
                        db.session.add(bot_msg)
                        
                        # Update conversation
                        conversation.updated_at = datetime.utcnow()
                        db.session.commit()
                        
                        # Send response via Instagram
                        # Use the stored page_id for Instagram service
                        if bot.instagram_page_id:
                            instagram_service = InstagramService(bot.instagram_token, bot.instagram_page_id)
                            result = instagram_service.send_message(sender_id, response_text)
                            
                            if result:
                                logging.info(f"Instagram message sent successfully to user {sender_id}")
                                
                                # Send monitoring notification if configured
                                send_monitoring_notification(bot, conversation, user_message, response_text, 'instagram')
                            else:
                                logging.error(f"Failed to send Instagram message to user {sender_id}")
        
        return "OK", 200
            
    except Exception as e:
        logging.error(f"Instagram webhook error: {e}")
        db.session.rollback()
        return "Error", 500

def handle_telegram_command(bot, chat_id, command, message):
    """Handle Telegram bot commands"""
    try:
        telegram_service = TelegramService(bot.telegram_token)
        
        # Get or create conversation
        conversation = Conversation.query.filter_by(
            bot_id=bot.id,
            platform='telegram',
            platform_user_id=str(chat_id)
        ).first()
        
        if not conversation:
            # Extract username from message  
            telegram_username = message['from'].get('username')
            user_display_name = message['from'].get('first_name', 'Unknown')
            
            conversation = Conversation(
                bot_id=bot.id,
                platform='telegram',
                platform_user_id=str(chat_id),
                platform_username=telegram_username or user_display_name,
                language='uz'  # Default to Uzbek
            )
            db.session.add(conversation)
            db.session.commit()
        else:
            # Update username if it exists and is different
            telegram_username = message['from'].get('username')
            if telegram_username and conversation.platform_username != telegram_username:
                conversation.platform_username = telegram_username
                db.session.commit()
        
        if command.startswith('/start'):
            # Welcome message with language selection
            welcome_messages = {
                'uz': f"Assalom alaykum! 👋\n\nMen <b>{bot.name}</b> botman.\n\n{bot.description or 'Sizga yordam berish uchun tayyorman!'}\n\n📣 Tilni o'zgartirish uchun /til buyrug'idan foydalaning.",
                'ru': f"Привет! 👋\n\nЯ бот <b>{bot.name}</b>.\n\n{bot.description or 'Готов помочь вам!'}\n\n📣 Используйте команду /til для смены языка.",
                'en': f"Hello! 👋\n\nI'm the <b>{bot.name}</b> bot.\n\n{bot.description or 'Ready to help you!'}\n\n📣 Use /til command to change language."
            }
            
            text = welcome_messages.get(conversation.language, welcome_messages['uz'])
            keyboard = telegram_service.create_language_keyboard()
            
            telegram_service.send_message(chat_id, text, keyboard)
            
        elif command.startswith('/til') or command.startswith('/language') or command.startswith('/lang'):
            # Language selection
            language_messages = {
                'uz': "🌐 Tilni tanlang:",
                'ru': "🌐 Выберите язык:",
                'en': "🌐 Choose your language:"
            }
            
            text = language_messages.get(conversation.language, language_messages['uz'])
            keyboard = telegram_service.create_language_keyboard()
            
            telegram_service.send_message(chat_id, text, keyboard)
            
        elif command.startswith('/help'):
            # Help message
            help_messages = {
                'uz': f"🤖 <b>{bot.name}</b> - Yordam\n\n📋 Mavjud buyruqlar:\n/start - Botni ishga tushirish\n/til - Tilni o'zgartirish\n/help - Yordam\n\n💬 Menga savollaringizni yozing va men javob beraman!",
                'ru': f"🤖 <b>{bot.name}</b> - Помощь\n\n📋 Доступные команды:\n/start - Запустить бота\n/til - Сменить язык\n/help - Помощь\n\n💬 Задавайте мне вопросы и я отвечу!",
                'en': f"🤖 <b>{bot.name}</b> - Help\n\n📋 Available commands:\n/start - Start the bot\n/til - Change language\n/help - Help\n\n💬 Ask me questions and I'll answer!"
            }
            
            text = help_messages.get(conversation.language, help_messages['uz'])
            telegram_service.send_message(chat_id, text)
        
        return "OK", 200
        
    except Exception as e:
        logging.error(f"Telegram command error: {e}")
        return "Error", 500

def handle_telegram_callback(bot, callback_query):
    """Handle Telegram callback queries (inline keyboard responses)"""
    try:
        telegram_service = TelegramService(bot.telegram_token)
        
        chat_id = callback_query['message']['chat']['id']
        callback_data = callback_query['data']
        callback_id = callback_query['id']
        message_id = callback_query['message']['message_id']
        
        # Get conversation
        conversation = Conversation.query.filter_by(
            bot_id=bot.id,
            platform='telegram',
            platform_user_id=str(chat_id)
        ).first()
        
        if not conversation:
            telegram_service.answer_callback_query(callback_id, "Error: Conversation not found")
            return "Error", 400
        
        if callback_data.startswith('lang_'):
            # Language selection
            new_language = callback_data.split('_')[1]
            
            if new_language in ['uz', 'ru', 'en']:
                # Update conversation language
                conversation.language = new_language
                db.session.commit()
                
                # Success messages
                success_messages = {
                    'uz': "✅ Til o'zgartirildi: O'zbek",
                    'ru': "✅ Язык изменен: Русский", 
                    'en': "✅ Language changed: English"
                }
                
                # Updated language selection message
                language_messages = {
                    'uz': "🌐 Til tanlandi: O'zbek\n\nEndi men sizga O'zbek tilida javob beraman!",
                    'ru': "🌐 Язык выбран: Русский\n\nТеперь я буду отвечать вам на русском языке!",
                    'en': "🌐 Language selected: English\n\nNow I will respond to you in English!"
                }
                
                # Edit the original message
                text = language_messages.get(new_language, language_messages['uz'])
                telegram_service.edit_message(chat_id, message_id, text)
                
                # Answer callback query
                telegram_service.answer_callback_query(callback_id, success_messages.get(new_language))
            
        return "OK", 200
        
    except Exception as e:
        logging.error(f"Telegram callback error: {e}")
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
        bot_info_response = telegram_service.get_bot_info()
        if not bot_info_response.success:
            flash('Telegram bot token noto\'g\'ri yoki yaroqsiz', 'error')
            return redirect(url_for('bot_detail', bot_id=bot_id))
        
        bot_info = bot_info_response.data
        
        # Set webhook URL
        webhook_url = f"{request.host_url}webhook/telegram/{bot_id}"
        webhook_response = telegram_service.set_webhook(webhook_url)
        
        if webhook_response.success:
            # Save token to bot
            bot.telegram_token = telegram_token
            bot.telegram_webhook_url = webhook_url
            bot.is_active = True
            
            # Save notification settings if provided
            admin_chat_id = request.form.get('admin_chat_id', '').strip()
            notification_channel = request.form.get('notification_channel', '').strip()
            
            if admin_chat_id:
                bot.admin_chat_id = admin_chat_id
            if notification_channel:
                bot.notification_channel = notification_channel
                
            db.session.commit()
            
            flash(f'Telegram bot muvaffaqiyatli ulandi! Bot nomi: {bot_info.get("first_name", "Bot")}', 'success')
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

@app.route('/bot/<int:bot_id>/send-message', methods=['GET', 'POST'])
@login_required
def send_manual_message(bot_id):
    """Send manual message to customers"""
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
        
    bot = Bot.query.get_or_404(bot_id)
    
    # Check ownership
    if bot.user_id != current_user.id:
        flash('Bu chatbotga ruxsatingiz yo\'q', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            conversation_id = request.form.get('conversation_id')
            platform = request.form.get('platform')
            platform_user_id = request.form.get('platform_user_id')
            message_text = request.form.get('message')
            
            if not all([conversation_id, platform, platform_user_id, message_text]):
                return jsonify({'success': False, 'error': 'Barcha maydonlar to\'ldirilishi kerak'})
            
            conversation = Conversation.query.get_or_404(conversation_id)
            
            # Check if conversation belongs to this bot
            if conversation.bot_id != bot.id:
                return jsonify({'success': False, 'error': 'Suhbat bu botga tegishli emas'})
            
            # Send message through appropriate platform with transactional database operations
            response = None
            error_message = 'Xabar yuborishda xatolik yuz berdi'
            
            try:
                if platform == 'telegram' and bot.telegram_token:
                    telegram_service = TelegramService(bot.telegram_token)
                    response = telegram_service.send_message(platform_user_id, message_text)
                elif platform == 'instagram' and bot.instagram_token:
                    instagram_service = InstagramService(bot.instagram_token, bot.instagram_page_id)
                    response = instagram_service.send_message(platform_user_id, message_text)
                elif platform == 'whatsapp':
                    error_message = 'WhatsApp integratsiyasi hozircha mavjud emas'
                    return jsonify({'success': False, 'error': error_message})
                else:
                    error_message = f'{platform.title()} platformasi uchun kerakli konfiguratsiya yo\'q'
                    return jsonify({'success': False, 'error': error_message})
                
                if response and response.success:
                    # Save message to database in a transaction
                    try:
                        with db.session.begin():
                            message = Message(
                                conversation_id=conversation.id,
                                content=message_text,
                                is_from_user=False,  # This is from admin/bot
                                created_at=datetime.utcnow()
                            )
                            db.session.add(message)
                            conversation.updated_at = datetime.utcnow()
                        
                        return jsonify({'success': True, 'message': 'Xabar muvaffaqiyatli yuborildi'})
                    except Exception as db_error:
                        logging.error(f"Database error while saving manual message: {db_error}")
                        return jsonify({'success': False, 'error': 'Xabar yuborildi, lekin saqlashda xatolik'})
                else:
                    error_detail = response.error_message if response else 'Platform xizmati javob bermadi'
                    logging.error(f"Platform service failed for {platform}: {error_detail}")
                    return jsonify({'success': False, 'error': f'Platform xatoligi: {error_detail}'})
                    
            except Exception as send_error:
                logging.error(f"Error sending manual message via {platform}: {send_error}")
                return jsonify({'success': False, 'error': f'Xabar yuborishda xatolik: {str(send_error)}'})
                
        except Exception as e:
            logging.error(f"Manual message send error: {e}")
            return jsonify({'success': False, 'error': 'Server xatoligi'})
    
    # GET request - show message sending page
    conversations = Conversation.query.filter_by(bot_id=bot.id, is_active=True).order_by(Conversation.updated_at.desc()).limit(50).all()
    
    return render_template('bot/send_message.html', bot=bot, conversations=conversations)


@app.route('/bot/<int:bot_id>/broadcast-message', methods=['GET', 'POST'])
@login_required
def broadcast_message(bot_id):
    """Send broadcast message to all customers"""
    if not current_user.has_access:
        return redirect(url_for('trial_expired'))
        
    bot = Bot.query.get_or_404(bot_id)
    
    # Check ownership
    if bot.user_id != current_user.id:
        flash('Bu chatbotga ruxsatingiz yo\'q', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            message_text = request.form.get('message')
            
            if not message_text or not message_text.strip():
                return jsonify({'success': False, 'error': 'Xabar matnini kiriting'})
            
            # Get all active conversations for this bot
            conversations = Conversation.query.filter_by(bot_id=bot.id, is_active=True).all()
            
            if not conversations:
                return jsonify({'success': False, 'error': 'Hech qanday faol suhbat topilmadi'})
            
            successful_sends = 0
            failed_sends = 0
            errors = []
            
            # Send message to each conversation
            for conversation in conversations:
                try:
                    response = None
                    
                    # Send via appropriate platform
                    if conversation.platform == 'telegram' and bot.telegram_token:
                        telegram_service = TelegramService(bot.telegram_token)
                        response = telegram_service.send_message(conversation.platform_user_id, message_text)
                    elif conversation.platform == 'instagram' and bot.instagram_token:
                        instagram_service = InstagramService(bot.instagram_token, bot.instagram_page_id)
                        response = instagram_service.send_message(conversation.platform_user_id, message_text)
                    elif conversation.platform == 'whatsapp':
                        errors.append(f'WhatsApp (@{conversation.platform_username}): Integratsiya mavjud emas')
                        failed_sends += 1
                        continue
                    else:
                        errors.append(f'{conversation.platform.title()} (@{conversation.platform_username}): Konfiguratsiya yo\'q')
                        failed_sends += 1
                        continue
                    
                    if response and response.success:
                        # Save message to database
                        try:
                            with db.session.begin():
                                message = Message(
                                    conversation_id=conversation.id,
                                    content=message_text,
                                    is_from_user=False,  # This is from admin/bot
                                    created_at=datetime.utcnow()
                                )
                                db.session.add(message)
                                conversation.updated_at = datetime.utcnow()
                            successful_sends += 1
                        except Exception as db_error:
                            logging.error(f"Database error for conversation {conversation.id}: {db_error}")
                            errors.append(f'@{conversation.platform_username}: Xabar yuborildi, lekin saqlashda xatolik')
                            failed_sends += 1
                    else:
                        error_detail = response.error_message if response else 'Platform xizmati javob bermadi'
                        logging.error(f"Failed to send broadcast to {conversation.platform}:{conversation.platform_user_id}: {error_detail}")
                        errors.append(f'@{conversation.platform_username} ({conversation.platform}): {error_detail}')
                        failed_sends += 1
                        
                except Exception as send_error:
                    logging.error(f"Error sending broadcast to conversation {conversation.id}: {send_error}")
                    errors.append(f'@{conversation.platform_username}: Xatolik - {str(send_error)}')
                    failed_sends += 1
            
            # Prepare result message
            if successful_sends > 0:
                result_message = f'✅ {successful_sends} ta foydalanuvchiga xabar yuborildi'
                if failed_sends > 0:
                    result_message += f'\n❌ {failed_sends} ta xabar yuborilmadi'
                    if errors:
                        result_message += f'\n\nXatoliklar:\n' + '\n'.join(errors[:5])  # Show first 5 errors
                        if len(errors) > 5:
                            result_message += f'\n... va yana {len(errors) - 5} ta xatolik'
                
                return jsonify({'success': True, 'message': result_message, 'stats': {
                    'successful': successful_sends,
                    'failed': failed_sends,
                    'total': len(conversations)
                }})
            else:
                return jsonify({'success': False, 'error': f'Hech qanday xabar yuborilmadi. {failed_sends} ta xatolik.'})
                    
        except Exception as e:
            logging.error(f"Error in broadcast message: {e}")
            return jsonify({'success': False, 'error': f'Broadcast xatoligi: {str(e)}'})
    
    # GET request - show broadcast form
    conversations_count = Conversation.query.filter_by(bot_id=bot.id, is_active=True).count()
    platforms = db.session.query(Conversation.platform).filter_by(bot_id=bot.id, is_active=True).distinct().all()
    platform_list = [p[0] for p in platforms]
    
    return render_template('bot/broadcast_message.html', 
                         bot=bot, 
                         conversations_count=conversations_count,
                         platforms=platform_list)

@app.route('/conversation/<int:conversation_id>/messages')
@login_required
def get_conversation_messages(conversation_id):
    """Get messages for a conversation"""
    if not current_user.has_access:
        return jsonify({'error': 'Access denied'}), 403
        
    conversation = Conversation.query.get_or_404(conversation_id)
    
    # Check if conversation belongs to user's bot
    if conversation.bot.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    messages = Message.query.filter_by(conversation_id=conversation_id)\
                           .order_by(Message.created_at.desc())\
                           .limit(10).all()
    
    messages_data = []
    for message in reversed(messages):  # Reverse to show oldest first
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'is_from_user': message.is_from_user,
            'created_at': message.created_at.isoformat()
        })
    
    return jsonify({'messages': messages_data})

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
