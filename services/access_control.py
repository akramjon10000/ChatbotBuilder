"""
Access Control Service - Foydalanuvchi ruxsatlarini boshqarish
Bu xizmat sinov tizimi va admin nazoratini boshqaradi
"""

from datetime import datetime, timedelta
from app import db
from models import User, AdminAction, AccessStatus, AdminActionType, SubscriptionType
import logging

class AccessControlService:
    
    @staticmethod
    def check_user_access(user):
        """Foydalanuvchi dostupini tekshirish"""
        if not user:
            return False
            
        if user.is_admin:
            return True
        
        if user.access_status == AccessStatus.APPROVED:
            return True
        
        if user.access_status == AccessStatus.TRIAL:
            if user.trial_end_date and datetime.utcnow() < user.trial_end_date:
                return True
            else:
                # Sinov tugagan - PENDING holatiga o'tkazish
                user.access_status = AccessStatus.PENDING
                user.is_trial_active = False
                db.session.commit()
                logging.info(f"User {user.username} trial expired, moved to PENDING")
                return False
        
        return False
    
    @staticmethod
    def grant_access(admin_user, target_user, reason=None):
        """Admin tomonidan dostup berish"""
        if not admin_user.is_admin:
            raise ValueError("Faqat adminlar dostup bera oladi")
        
        target_user.admin_approved = True
        target_user.access_status = AccessStatus.APPROVED
        target_user.access_granted_date = datetime.utcnow()
        target_user.is_trial_active = False
        target_user.marketing_opt_out = True  # Stop marketing messages
        
        # Admin harakatini yozib olish
        action = AdminAction()
        action.admin_id = admin_user.id
        action.target_user_id = target_user.id
        action.action_type = AdminActionType.GRANT_ACCESS
        action.reason = reason
        db.session.add(action)
        db.session.commit()
        
        logging.info(f"Admin {admin_user.username} granted access to {target_user.username}")
        return True
    
    @staticmethod
    def grant_monthly_subscription(admin_user, target_user, reason=None):
        """Oylik obuna berish"""
        if not admin_user.is_admin:
            raise ValueError("Faqat adminlar obuna bera oladi")
        
        target_user.access_status = AccessStatus.MONTHLY
        target_user.subscription_type = SubscriptionType.MONTHLY
        target_user.subscription_start_date = datetime.utcnow()
        target_user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
        target_user.subscription_granted_by = admin_user.id
        target_user.is_trial_active = False
        target_user.admin_approved = True
        target_user.access_granted_date = datetime.utcnow()
        target_user.marketing_opt_out = True  # Stop marketing messages
        
        # Admin harakatini yozib olish
        action = AdminAction()
        action.admin_id = admin_user.id
        action.target_user_id = target_user.id
        action.action_type = AdminActionType.GRANT_MONTHLY
        action.reason = reason
        db.session.add(action)
        db.session.commit()
        
        logging.info(f"Admin {admin_user.username} granted monthly subscription to {target_user.username}")
        return True
    
    @staticmethod
    def grant_yearly_subscription(admin_user, target_user, reason=None):
        """Yillik obuna berish"""
        if not admin_user.is_admin:
            raise ValueError("Faqat adminlar obuna bera oladi")
        
        target_user.access_status = AccessStatus.YEARLY
        target_user.subscription_type = SubscriptionType.YEARLY
        target_user.subscription_start_date = datetime.utcnow()
        target_user.subscription_end_date = datetime.utcnow() + timedelta(days=365)
        target_user.subscription_granted_by = admin_user.id
        target_user.is_trial_active = False
        target_user.admin_approved = True
        target_user.access_granted_date = datetime.utcnow()
        target_user.marketing_opt_out = True  # Stop marketing messages
        
        # Admin harakatini yozib olish
        action = AdminAction()
        action.admin_id = admin_user.id
        action.target_user_id = target_user.id
        action.action_type = AdminActionType.GRANT_YEARLY
        action.reason = reason
        db.session.add(action)
        db.session.commit()
        
        logging.info(f"Admin {admin_user.username} granted yearly subscription to {target_user.username}")
        return True
    
    @staticmethod
    def revoke_access(admin_user, target_user, reason=None):
        """Dostupni olib qo'yish"""
        if not admin_user.is_admin:
            raise ValueError("Faqat adminlar dostupni olib qo'ya oladi")
        
        target_user.admin_approved = False
        target_user.access_status = AccessStatus.SUSPENDED
        target_user.access_granted_date = None
        
        # Admin harakatini yozib olish
        action = AdminAction()
        action.admin_id = admin_user.id
        action.target_user_id = target_user.id
        action.action_type = AdminActionType.REVOKE_ACCESS
        action.reason = reason
        db.session.add(action)
        db.session.commit()
        
        logging.info(f"Admin {admin_user.username} revoked access from {target_user.username}")
        return True
    
    @staticmethod
    def extend_trial(admin_user, target_user, days=7, reason=None):
        """Sinov muddatini uzaytirish"""
        if not admin_user.is_admin:
            raise ValueError("Faqat adminlar sinovni uzaytira oladi")
        
        # Sinov holatiga qaytarish va muddatni uzaytirish
        target_user.access_status = AccessStatus.TRIAL
        target_user.is_trial_active = True
        if target_user.trial_end_date and target_user.trial_end_date > datetime.utcnow():
            # Agar hali sinov tugamagan bo'lsa, qo'shimcha kun qo'shish
            target_user.trial_end_date += timedelta(days=days)
        else:
            # Yangi sinov muddatini boshlash
            target_user.trial_end_date = datetime.utcnow() + timedelta(days=days)
        
        # Admin harakatini yozib olish
        action = AdminAction()
        action.admin_id = admin_user.id
        action.target_user_id = target_user.id
        action.action_type = AdminActionType.EXTEND_TRIAL
        action.reason = f"Sinov {days} kunga uzaytirildi. {reason or ''}"
        db.session.add(action)
        db.session.commit()
        
        logging.info(f"Admin {admin_user.username} extended trial for {target_user.username} by {days} days")
        return True
    
    @staticmethod
    def suspend_user(admin_user, target_user, reason=None):
        """Foydalanuvchini to'xtatish"""
        if not admin_user.is_admin:
            raise ValueError("Faqat adminlar foydalanuvchini to'xtata oladi")
        
        target_user.access_status = AccessStatus.SUSPENDED
        target_user.is_trial_active = False
        target_user.admin_approved = False
        
        # Admin harakatini yozib olish
        action = AdminAction()
        action.admin_id = admin_user.id
        action.target_user_id = target_user.id
        action.action_type = AdminActionType.SUSPEND_USER
        action.reason = reason
        db.session.add(action)
        db.session.commit()
        
        logging.info(f"Admin {admin_user.username} suspended user {target_user.username}")
        return True
    
    @staticmethod
    def get_pending_users():
        """Ruxsat kutayotgan foydalanuvchilarni olish"""
        return User.query.filter_by(access_status=AccessStatus.PENDING).order_by(User.created_at.desc()).all()
    
    @staticmethod
    def get_trial_users():
        """Sinov foydalanuvchilarini olish"""
        return User.query.filter_by(access_status=AccessStatus.TRIAL).order_by(User.trial_end_date.asc()).all()
    
    @staticmethod
    def get_approved_users():
        """Tasdiqlangan foydalanuvchilarni olish"""
        return User.query.filter_by(access_status=AccessStatus.APPROVED).order_by(User.access_granted_date.desc()).all()
    
    @staticmethod
    def get_recent_admin_actions(limit=50):
        """So'nggi admin harakatlarini olish"""
        return AdminAction.query.order_by(AdminAction.action_date.desc()).limit(limit).all()
    
    @staticmethod
    def get_user_statistics():
        """Foydalanuvchi statistikalarini olish"""
        stats = {
            'total_users': User.query.count(),
            'trial_users': User.query.filter_by(access_status=AccessStatus.TRIAL).count(),
            'pending_users': User.query.filter_by(access_status=AccessStatus.PENDING).count(),
            'approved_users': User.query.filter_by(access_status=AccessStatus.APPROVED).count(),
            'suspended_users': User.query.filter_by(access_status=AccessStatus.SUSPENDED).count(),
            'admin_users': User.query.filter_by(is_admin=True).count(),
        }
        
        # Bugun ro'yxatdan o'tganlar
        today = datetime.utcnow().date()
        stats['new_today'] = User.query.filter(
            db.func.date(User.created_at) == today
        ).count()
        
        # Sinov muddati tugash arafasida bo'lganlar (1 kun qolganda)
        tomorrow = datetime.utcnow() + timedelta(days=1)
        stats['expiring_soon'] = User.query.filter(
            User.access_status == AccessStatus.TRIAL,
            User.trial_end_date <= tomorrow,
            User.trial_end_date > datetime.utcnow()
        ).count()
        
        return stats