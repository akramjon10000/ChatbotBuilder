from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func

from app import app, db
from models import User, Bot, Conversation, Message, AdminAction, SystemStats, Notification, UserNotification, NotificationStatus, NotificationType
from utils.helpers import admin_required
from services.telegram_service import TelegramService, get_user_chat_ids_from_conversations
import logging

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin panel bosh sahifa"""
    # Get statistics
    total_users = User.query.count()
    active_trials = User.query.filter(
        User.is_trial_active == True,
        User.trial_end_date > datetime.utcnow()
    ).count()
    
    approved_users = User.query.filter_by(admin_approved=True).count()
    trial_expired = User.query.filter(
        User.is_trial_active == True,
        User.trial_end_date <= datetime.utcnow(),
        User.admin_approved == False
    ).count()
    
    total_bots = Bot.query.count()
    total_conversations = Conversation.query.count()
    total_messages = Message.query.count()
    
    # Recent registrations
    recent_users = User.query.filter_by(is_admin=False).order_by(
        User.created_at.desc()
    ).limit(10).all()
    
    # Users needing approval
    users_needing_approval = User.query.filter(
        User.is_trial_active == True,
        User.trial_end_date <= datetime.utcnow(),
        User.admin_approved == False,
        User.is_admin == False
    ).all()
    
    stats = {
        'total_users': total_users,
        'active_trials': active_trials,
        'approved_users': approved_users,
        'trial_expired': trial_expired,
        'total_bots': total_bots,
        'total_conversations': total_conversations,
        'total_messages': total_messages
    }
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_users=recent_users,
                         users_needing_approval=users_needing_approval)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Barcha foydalanuvchilar ro'yxati"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filter options
    status_filter = request.args.get('status', 'all')
    search = request.args.get('search', '')
    
    query = User.query.filter_by(is_admin=False)
    
    # Apply filters
    if status_filter == 'trial_active':
        query = query.filter(
            User.is_trial_active == True,
            User.trial_end_date > datetime.utcnow()
        )
    elif status_filter == 'trial_expired':
        query = query.filter(
            User.is_trial_active == True,
            User.trial_end_date <= datetime.utcnow(),
            User.admin_approved == False
        )
    elif status_filter == 'approved':
        query = query.filter_by(admin_approved=True)
    
    if search:
        query = query.filter(
            User.username.contains(search) |
            User.email.contains(search) |
            User.full_name.contains(search)
        )
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/users.html',
                         users=users,
                         status_filter=status_filter,
                         search=search)

@app.route('/admin/users/<int:user_id>/grant_access', methods=['POST'])
@login_required
@admin_required
def grant_user_access(user_id):
    """Foydalanuvchiga dostup berish"""
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', '')
    
    if user.is_admin:
        flash('Admin foydalanuvchisiga dostup berish mumkin emas', 'error')
        return redirect(url_for('admin_users'))
    
    # Grant access
    user.admin_approved = True
    user.access_granted_date = datetime.utcnow()
    user.is_trial_active = False  # End trial
    
    # Log admin action
    action = AdminAction(
        admin_id=current_user.id,
        user_id=user.id,
        action_type='GRANT_ACCESS',
        reason=reason
    )
    
    db.session.add(action)
    db.session.commit()
    
    flash(f'{user.username} ga dostup berildi!', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/grant_monthly', methods=['POST'])
@login_required
@admin_required
def grant_monthly_subscription(user_id):
    """Foydalanuvchiga oylik obuna berish"""
    from services.access_control import AccessControlService
    
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', '')
    
    if user.is_admin:
        flash('Admin foydalanuvchisiga obuna berish mumkin emas', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        AccessControlService.grant_monthly_subscription(current_user, user, reason)
        flash(f'{user.username}ga oylik obuna berildi', 'success')
    except Exception as e:
        flash(f'Xatolik: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/grant_yearly', methods=['POST'])
@login_required
@admin_required
def grant_yearly_subscription(user_id):
    """Foydalanuvchiga yillik obuna berish"""
    from services.access_control import AccessControlService
    
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', '')
    
    if user.is_admin:
        flash('Admin foydalanuvchisiga obuna berish mumkin emas', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        AccessControlService.grant_yearly_subscription(current_user, user, reason)
        flash(f'{user.username}ga yillik obuna berildi', 'success')
    except Exception as e:
        flash(f'Xatolik: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/revoke_access', methods=['POST'])
@login_required
@admin_required
def revoke_user_access(user_id):
    """Foydalanuvchi dostupini bekor qilish"""
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', '')
    
    if user.is_admin:
        flash('Admin foydalanuvchisining dostupini bekor qilish mumkin emas', 'error')
        return redirect(url_for('admin_users'))
    
    # Revoke access
    user.admin_approved = False
    user.access_granted_date = None
    
    # Log admin action
    action = AdminAction(
        admin_id=current_user.id,
        user_id=user.id,
        action_type='REVOKE_ACCESS',
        reason=reason
    )
    
    db.session.add(action)
    db.session.commit()
    
    flash(f'{user.username} ning dostupi bekor qilindi!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Foydalanuvchini faollashtirish/faolsizlashtirish"""
    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash('Admin foydalanuvchisini faolsizlashtirish mumkin emas', 'error')
        return redirect(url_for('admin_users'))
    
    user.is_active = not user.is_active
    
    # Log admin action
    action_type = 'ACTIVATE_USER' if user.is_active else 'DEACTIVATE_USER'
    action = AdminAction(
        admin_id=current_user.id,
        user_id=user.id,
        action_type=action_type,
        reason=f'User {"activated" if user.is_active else "deactivated"} by admin'
    )
    
    db.session.add(action)
    db.session.commit()
    
    status = 'faollashtirildi' if user.is_active else 'faolsizlashtirildi'
    flash(f'{user.username} {status}!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/trial_expired')
@login_required
@admin_required
def admin_trial_expired():
    """Sinov muddati tugagan foydalanuvchilar"""
    users = User.query.filter(
        User.is_trial_active == True,
        User.trial_end_date <= datetime.utcnow(),
        User.admin_approved == False,
        User.is_admin == False
    ).order_by(User.trial_end_date.desc()).all()
    
    return render_template('admin/trial_expired.html', users=users)

@app.route('/admin/bots')
@login_required
@admin_required
def admin_bots():
    """Barcha chatbotlar"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    bots = Bot.query.join(User).order_by(Bot.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/bots.html', bots=bots)

@app.route('/admin/conversations')
@login_required
@admin_required
def admin_conversations():
    """Barcha suhbatlar"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    conversations = Conversation.query.join(Bot).join(User).order_by(
        Conversation.updated_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/conversations.html', conversations=conversations)

@app.route('/admin/actions')
@login_required
@admin_required
def admin_actions():
    """Admin harakatlari tarixi"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    actions = AdminAction.query.join(
        User, AdminAction.admin_id == User.id
    ).order_by(AdminAction.action_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/actions.html', actions=actions)

@app.route('/admin/stats')
@login_required
@admin_required
def admin_stats():
    """Tizim statistikalari"""
    # Daily stats for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    daily_stats = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('new_users')
    ).filter(
        User.created_at >= thirty_days_ago,
        User.is_admin == False
    ).group_by(func.date(User.created_at)).all()
    
    # Message stats
    message_stats = db.session.query(
        func.date(Message.created_at).label('date'),
        func.count(Message.id).label('message_count')
    ).filter(
        Message.created_at >= thirty_days_ago
    ).group_by(func.date(Message.created_at)).all()
    
    return render_template('admin/stats.html',
                         daily_stats=daily_stats,
                         message_stats=message_stats)

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_settings():
    """Tizim sozlamalari"""
    if request.method == 'POST':
        # Update system settings
        flash('Sozlamalar saqlandi!', 'success')
        return redirect(url_for('admin_settings'))
    
    return render_template('admin/settings.html')

@app.route('/admin/notifications')
@login_required
@admin_required
def admin_notifications():
    """Telegram habar yuborish sahifasi"""
    # Get recent notifications
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(10).all()
    
    # Get available bots with Telegram tokens
    telegram_bots = Bot.query.filter(
        Bot.telegram_token.isnot(None),
        Bot.telegram_token != ''
    ).all()
    
    # Count users by type
    all_users_count = User.query.filter_by(is_admin=False).count()
    trial_users_count = User.query.filter(
        User.access_status.in_(['trial']),
        User.is_admin == False
    ).count()
    subscription_users_count = User.query.filter(
        User.access_status.in_(['monthly', 'yearly']),
        User.is_admin == False
    ).count()
    approved_users_count = User.query.filter(
        User.access_status.in_(['approved']),
        User.is_admin == False
    ).count()
    
    user_counts = {
        'all': all_users_count,
        'trial': trial_users_count,
        'subscription': subscription_users_count,
        'approved': approved_users_count
    }
    
    return render_template('admin/notifications.html', 
                         notifications=notifications,
                         telegram_bots=telegram_bots,
                         user_counts=user_counts)

@app.route('/admin/notifications/send', methods=['POST'])
@login_required
@admin_required
def send_notification():
    """Telegram orqali notification yuborish"""
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        notification_type = request.form.get('notification_type', 'general')
        telegram_bot_id = request.form.get('telegram_bot_id')
        
        # Target audience
        target_all_users = request.form.get('target_all_users') == 'on'
        target_trial_users = request.form.get('target_trial_users') == 'on'
        target_subscription_users = request.form.get('target_subscription_users') == 'on'
        target_approved_users = request.form.get('target_approved_users') == 'on'
        
        # Delivery method
        send_to_channel = request.form.get('send_to_channel') == 'on'
        send_direct_messages = request.form.get('send_direct_messages') == 'on'
        
        # Validation
        if not title or not message:
            flash('Sarlavha va habar matni kiritilishi kerak!', 'error')
            return redirect(url_for('admin_notifications'))
        
        if not telegram_bot_id:
            flash('Telegram bot tanlanishi kerak!', 'error')
            return redirect(url_for('admin_notifications'))
            
        # Get bot
        bot = Bot.query.get(telegram_bot_id)
        if not bot or not bot.telegram_token:
            flash('Bot topilmadi yoki Telegram token mavjud emas!', 'error')
            return redirect(url_for('admin_notifications'))
        
        # Create notification record
        notification = Notification(
            title=title,
            message=message,
            notification_type=getattr(NotificationType, notification_type.upper(), NotificationType.GENERAL),
            created_by=current_user.id,
            send_telegram=True,
            target_all_users=target_all_users,
            target_trial_users=target_trial_users,
            target_subscription_users=target_subscription_users,
            target_approved_users=target_approved_users,
            target_telegram_channel=send_to_channel,
            target_direct_telegram=send_direct_messages
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # Initialize Telegram service
        telegram_service = TelegramService(bot.telegram_token)
        
        sent_count = 0
        failed_count = 0
        
        # Send to channel if requested
        if send_to_channel:
            if not bot.notification_channel:
                failed_count += 1
                logging.error(f"Channel sending requested but bot {bot.name} has no notification_channel configured")
                flash('Kanalga yuborish tanlangan lekin bot sozlamalarida kanal ko\'rsatilmagan!', 'warning')
            else:
                try:
                    formatted_message = f"<b>{title}</b>\n\n{message}"
                    result = telegram_service.send_channel_message(
                        bot.notification_channel, 
                        formatted_message,
                        'HTML'
                    )
                    
                    if result['success']:
                        sent_count += 1
                        logging.info(f"Channel message sent successfully to {bot.notification_channel}")
                    else:
                        failed_count += 1
                        logging.error(f"Failed to send channel message: {result.get('error_description')}")
                        
                except Exception as e:
                    failed_count += 1
                    logging.error(f"Channel message error: {e}")
        
        # Send direct messages if requested
        if send_direct_messages:
            try:
                # Get target users
                target_users = []
                
                if target_all_users:
                    target_users = User.query.filter_by(is_admin=False).all()
                else:
                    if target_trial_users:
                        trial_users = User.query.filter(
                            User.access_status.in_(['trial']),
                            User.is_admin == False
                        ).all()
                        target_users.extend(trial_users)
                    
                    if target_subscription_users:
                        sub_users = User.query.filter(
                            User.access_status.in_(['monthly', 'yearly']),
                            User.is_admin == False
                        ).all()
                        target_users.extend(sub_users)
                    
                    if target_approved_users:
                        approved_users = User.query.filter(
                            User.access_status.in_(['approved']),
                            User.is_admin == False
                        ).all()
                        target_users.extend(approved_users)
                
                # Get chat IDs for users who have interacted via Telegram with proper filtering
                chat_ids = get_user_chat_ids_from_conversations(
                    target_all_users=target_all_users,
                    target_trial_users=target_trial_users,
                    target_subscription_users=target_subscription_users,
                    target_approved_users=target_approved_users
                )
                
                if chat_ids:
                    formatted_message = f"<b>{title}</b>\n\n{message}"
                    bulk_result = telegram_service.send_bulk_messages(
                        chat_ids,
                        formatted_message,
                        'HTML'
                    )
                    
                    sent_count += bulk_result['sent']
                    failed_count += bulk_result['failed']
                    
                    # Create UserNotification records for successful sends
                    for chat_id in bulk_result['successful_chat_ids']:
                        # Find user by chat_id (from conversations)
                        conversation = Conversation.query.filter_by(
                            platform='telegram',
                            platform_user_id=chat_id
                        ).first()
                        
                        if conversation:
                            user_notification = UserNotification(
                                user_id=conversation.user_id,
                                notification_id=notification.id,
                                is_telegram_sent=True,
                                telegram_sent_at=datetime.utcnow()
                            )
                            db.session.add(user_notification)
                    
                    db.session.commit()
                    
            except Exception as e:
                logging.error(f"Direct message error: {e}")
                failed_count += len(chat_ids) if 'chat_ids' in locals() else 1
        
        # Update notification status
        notification.sent_count = sent_count
        notification.failed_count = failed_count
        notification.status = NotificationStatus.SENT if sent_count > 0 else NotificationStatus.FAILED
        notification.sent_at = datetime.utcnow()
        
        db.session.commit()
        
        if sent_count > 0:
            flash(f'Habar muvaffaqiyatli yuborildi! Yuborilgan: {sent_count}, Xatolik: {failed_count}', 'success')
        else:
            flash('Habar yuborishda xatolik yuz berdi!', 'error')
            
    except Exception as e:
        logging.error(f"Notification sending error: {e}")
        flash('Habar yuborishda xatolik yuz berdi!', 'error')
        db.session.rollback()
    
    return redirect(url_for('admin_notifications'))
