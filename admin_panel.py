"""
Admin Panel Routes - Administrator boshqaruv paneli
Faqat adminlar uchun maxsus sahifalar va funksiyalar
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta

from app import db
from models import User, Bot, AdminAction, SystemStats, AccessStatus, AdminActionType
from services.access_control import AccessControlService

# Admin blueprint yaratish
admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Admin ruxsati talab qiladigan decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bu sahifaga faqat adminlar kira oladi!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin asosiy dashboard"""
    # Statistikalarni olish
    stats = AccessControlService.get_user_statistics()
    
    # So'nggi admin harakatlarini olish
    recent_actions = AccessControlService.get_recent_admin_actions(10)
    
    # Sinov muddati tugash arafasida bo'lgan foydalanuvchilar
    expiring_trials = User.query.filter(
        User.access_status == AccessStatus.TRIAL,
        User.trial_end_date <= datetime.utcnow() + timedelta(days=1),
        User.trial_end_date > datetime.utcnow()
    ).all()
    
    # Ruxsat kutayotgan foydalanuvchilar
    pending_users = AccessControlService.get_pending_users()[:5]  # Faqat 5 tasi
    
    return render_template('admin/dashboard.html', 
                         stats=stats,
                         recent_actions=recent_actions,
                         expiring_trials=expiring_trials,
                         pending_users=pending_users)

@admin.route('/users')
@login_required
@admin_required
def users():
    """Barcha foydalanuvchilar ro'yxati"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status')
    search_query = request.args.get('search', '')
    
    # Bazaviy so'rov
    query = User.query
    
    # Qidiruv filtri
    if search_query:
        query = query.filter(
            db.or_(
                User.username.contains(search_query),
                User.email.contains(search_query),
                User.full_name.contains(search_query)
            )
        )
    
    # Status filtri
    if status_filter and status_filter != 'all':
        if status_filter == 'admin':
            query = query.filter(User.is_admin == True)
        else:
            try:
                status_enum = AccessStatus(status_filter)
                query = query.filter(User.access_status == status_enum)
            except ValueError:
                pass
    
    # Sahifalash
    users_paginated = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', 
                         users=users_paginated, 
                         current_filter=status_filter,
                         search_query=search_query)

@admin.route('/pending-users')
@login_required
@admin_required
def pending_users():
    """Ruxsat kutayotgan foydalanuvchilar"""
    pending = AccessControlService.get_pending_users()
    return render_template('admin/pending_users.html', users=pending)

@admin.route('/grant-access/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def grant_access(user_id):
    """Foydalanuvchiga dostup berish"""
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', '')
    
    try:
        AccessControlService.grant_access(current_user, user, reason)
        flash(f'{user.username} ga dostup berildi!', 'success')
    except Exception as e:
        flash(f'Xatolik: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('admin.pending_users'))

@admin.route('/revoke-access/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def revoke_access(user_id):
    """Dostupni olib qo'yish"""
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', '')
    
    try:
        AccessControlService.revoke_access(current_user, user, reason)
        flash(f'{user.username} dan dostup olib qo\'yildi!', 'warning')
    except Exception as e:
        flash(f'Xatolik: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('admin.users'))

@admin.route('/extend-trial/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def extend_trial(user_id):
    """Sinov muddatini uzaytirish"""
    user = User.query.get_or_404(user_id)
    days = request.form.get('days', 7, type=int)
    reason = request.form.get('reason', '')
    
    try:
        AccessControlService.extend_trial(current_user, user, days, reason)
        flash(f'{user.username} ning sinovi {days} kunga uzaytirildi!', 'info')
    except Exception as e:
        flash(f'Xatolik: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('admin.users'))

@admin.route('/suspend-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def suspend_user(user_id):
    """Foydalanuvchini to'xtatish"""
    user = User.query.get_or_404(user_id)
    reason = request.form.get('reason', '')
    
    try:
        AccessControlService.suspend_user(current_user, user, reason)
        flash(f'{user.username} to\'xtatildi!', 'warning')
    except Exception as e:
        flash(f'Xatolik: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('admin.users'))

@admin.route('/actions-history')
@login_required
@admin_required
def actions_history():
    """Admin harakatlari tarixi"""
    page = request.args.get('page', 1, type=int)
    admin_filter = request.args.get('admin_id', type=int)
    action_filter = request.args.get('action_type')
    
    query = AdminAction.query
    
    # Admin filtri
    if admin_filter:
        query = query.filter(AdminAction.admin_id == admin_filter)
    
    # Harakat turi filtri
    if action_filter and action_filter != 'all':
        try:
            action_enum = AdminActionType(action_filter)
            query = query.filter(AdminAction.action_type == action_enum)
        except ValueError:
            pass
    
    actions = query.order_by(AdminAction.action_date.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Admin ro'yxati filter uchun
    admins = User.query.filter(User.is_admin == True).all()
    
    return render_template('admin/actions_history.html', 
                         actions=actions,
                         admins=admins,
                         current_admin_filter=admin_filter,
                         current_action_filter=action_filter)

@admin.route('/statistics')
@login_required
@admin_required
def statistics():
    """Batafsil statistikalar"""
    stats = AccessControlService.get_user_statistics()
    
    # Oxirgi 30 kunlik statistika
    daily_stats = []
    for i in range(30):
        date = datetime.utcnow().date() - timedelta(days=i)
        day_stats = SystemStats.query.filter(
            SystemStats.date == date
        ).first()
        
        if not day_stats:
            # Agar o'sha kun uchun statistika bo'lmasa, hisoblash
            day_data = {
                'date': date,
                'total_users': User.query.filter(
                    db.func.date(User.created_at) <= date
                ).count(),
                'new_users': User.query.filter(
                    db.func.date(User.created_at) == date
                ).count()
            }
        else:
            day_data = {
                'date': day_stats.date,
                'total_users': day_stats.total_users,
                'new_users': 0  # Keyinroq hisoblash
            }
        
        daily_stats.append(day_data)
    
    daily_stats.reverse()  # Eskilardan yangiga
    
    return render_template('admin/statistics.html', 
                         stats=stats,
                         daily_stats=daily_stats)

@admin.route('/api/user-stats')
@login_required
@admin_required
def api_user_stats():
    """API: Foydalanuvchi statistikalari (AJAX uchun)"""
    stats = AccessControlService.get_user_statistics()
    return jsonify(stats)

@admin.route('/settings')
@login_required
@admin_required
def settings():
    """Admin sozlamalari"""
    return render_template('admin/settings.html')