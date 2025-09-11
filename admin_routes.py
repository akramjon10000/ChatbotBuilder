from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func

from app import app, db
from models import User, Bot, Conversation, Message, AdminAction, SystemStats, Notification, UserNotification, NotificationStatus, NotificationType, AccessStatus
from utils.helpers import admin_required
from services.marketing_service import MarketingEmailService, get_trial_expired_users, get_active_trial_users, get_all_users
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
    user.marketing_opt_out = True  # Stop marketing messages
    
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

@app.route('/admin/marketing')
@login_required
@admin_required
def admin_marketing():
    """Marketing Telegram xabarlari yuborish sahifasi"""
    # Get recent marketing notifications (last 10)
    notifications = Notification.query.filter(
        Notification.title.contains('Telegram') | Notification.title.contains('Marketing')
    ).order_by(Notification.created_at.desc()).limit(10).all()
    
    # Count users by type for Telegram marketing
    all_users_count = User.query.filter_by(is_admin=False).count()
    all_telegram_users_count = User.query.filter(
        User.is_admin == False,
        User.telegram_chat_id != None,
        User.marketing_opt_out == False
    ).count()
    
    # Import Telegram marketing functions
    from services.telegram_marketing_service import get_trial_expired_telegram_users
    trial_expired_count = len(get_trial_expired_telegram_users())
    
    # Count active trial users with Telegram
    active_trial_telegram_count = User.query.filter(
        User.is_trial_active == True,
        User.trial_end_date > datetime.utcnow(),
        User.admin_approved == False,
        User.is_admin == False,
        User.telegram_chat_id != None,
        User.marketing_opt_out == False
    ).count()
    
    user_counts = {
        'all': all_users_count,
        'all_telegram': all_telegram_users_count,
        'trial_expired': trial_expired_count,
        'trial_active': active_trial_telegram_count
    }
    
    return render_template('admin/notifications.html', 
                         notifications=notifications,
                         user_counts=user_counts)

@app.route('/admin/marketing/send', methods=['POST'])
@login_required
@admin_required
def send_marketing_telegram():
    """Marketing Telegram xabar yuborish"""
    try:
        # Get form data
        content = request.form.get('content', '').strip()
        target_audience = request.form.get('target_audience', 'trial_expired')
        include_contact = request.form.get('include_contact') == '1'
        
        # Validation
        if not content:
            flash('Xabar matni kiritilishi kerak!', 'error')
            return redirect(url_for('admin_marketing'))
        
        # Initialize Telegram marketing service
        from services.telegram_marketing_service import TelegramMarketingService, get_trial_expired_telegram_users
        marketing_service = TelegramMarketingService()
        
        # Get target users based on audience
        if target_audience == 'trial_expired':
            target_users = get_trial_expired_telegram_users()
        elif target_audience == 'trial_active':
            # Get active trial users with Telegram
            target_users = []
            users = User.query.filter(
                User.is_trial_active == True,
                User.trial_end_date > datetime.utcnow(),
                User.admin_approved == False,
                User.is_admin == False,
                User.telegram_chat_id != None,
                User.marketing_opt_out == False
            ).all()
            
            for user in users:
                target_users.append({
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name or user.username,
                    'telegram_chat_id': user.telegram_chat_id
                })
        elif target_audience == 'all_telegram':
            # Get all users with Telegram
            target_users = []
            users = User.query.filter(
                User.is_admin == False,
                User.telegram_chat_id != None,
                User.marketing_opt_out == False
            ).all()
            
            for user in users:
                target_users.append({
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name or user.username,
                    'telegram_chat_id': user.telegram_chat_id
                })
        else:
            flash('Noto\'g\'ri auditoriya tanlandi!', 'error')
            return redirect(url_for('admin_marketing'))
        
        if not target_users:
            flash('Tanlangan auditoriyada Telegram bog\'lagan foydalanuvchilar topilmadi!', 'error')
            return redirect(url_for('admin_marketing'))
        
        # Send Telegram messages to each user
        sent_count = 0
        failed_count = 0
        
        for user_data in target_users:
            try:
                if target_audience == 'trial_expired':
                    # Use predefined trial expired message
                    result = marketing_service.send_trial_expired_message(
                        chat_id=user_data['telegram_chat_id'],
                        user_name=user_data['full_name'] or user_data['username']
                    )
                else:
                    # Use custom message
                    custom_message = content
                    if include_contact:
                        custom_message += "\n\n📞 Aloqa:\n• Telefon: +998 99 644 84 44\n• Telegram: @Akramjon1984"
                    
                    result = marketing_service.send_marketing_message(
                        chat_id=user_data['telegram_chat_id'],
                        message=custom_message
                    )
                
                if result and result.get('success'):
                    sent_count += 1
                    
                    # Update user's marketing last sent timestamp
                    user = User.query.get(user_data['id'])
                    if user:
                        user.marketing_last_sent_at = datetime.utcnow()
                        db.session.commit()
                else:
                    failed_count += 1
                    
            except Exception as user_error:
                failed_count += 1
                logging.error(f"Error sending Telegram to user {user_data['full_name']}: {user_error}")
        
        # Create notification record
        notification = Notification(
            title=f"Telegram Marketing - {target_audience.replace('_', ' ').title()}",
            message=content[:500] + '...' if len(content) > 500 else content,
            notification_type=NotificationType.GENERAL,
            created_by=current_user.id,
            send_telegram=True,
            target_all_users=(target_audience == 'all_telegram'),
            target_trial_users=(target_audience == 'trial_active'),
            sent_count=sent_count,
            failed_count=failed_count,
            status=NotificationStatus.SENT if sent_count > 0 else NotificationStatus.FAILED,
            sent_at=datetime.utcnow()
        )
        
        db.session.add(notification)
        db.session.commit()
        
        if sent_count > 0:
            flash(f'Marketing Telegram xabarlari muvaffaqiyatli yuborildi! Yuborilgan: {sent_count}, Xatolik: {failed_count}', 'success')
            logging.info(f"Marketing Telegrams sent: {sent_count} successful, {failed_count} failed to {target_audience} audience")
        else:
            flash('Telegram xabar yuborishda xatolik yuz berdi!', 'error')
            
    except Exception as e:
        logging.error(f"Marketing Telegram sending error: {e}")
        flash('Telegram xabar yuborishda xatolik yuz berdi!', 'error')
        db.session.rollback()
    
    return redirect(url_for('admin_marketing'))
