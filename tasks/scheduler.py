import logging
import atexit
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

def check_trial_expiry():
    """Check for expired trials and update user status"""
    try:
        from app import app, db
        from models import User, AdminAction
        
        with app.app_context():
            # Find users with expired trials
            expired_users = User.query.filter(
                User.is_trial_active == True,
                User.trial_end_date <= datetime.utcnow(),
                User.admin_approved == False,
                User.is_admin == False
            ).all()
            
            for user in expired_users:
                logging.info(f"Trial expired for user: {user.username}")
                # Trial expiry is handled by the has_access property
                # No need to change is_trial_active here
            
            if expired_users:
                logging.info(f"Found {len(expired_users)} users with expired trials")
            
    except Exception as e:
        logging.error(f"Error checking trial expiry: {e}")

def update_daily_stats():
    """Update daily statistics"""
    try:
        from app import app, db
        from models import User, Bot, Message, SystemStats
        from sqlalchemy import func
        
        with app.app_context():
            today = datetime.utcnow().date()
            
            # Check if stats for today already exist
            existing_stats = SystemStats.query.filter_by(date=today).first()
            if existing_stats:
                return  # Already updated today
            
            # Calculate statistics
            total_users = User.query.filter_by(is_admin=False).count()
            active_trials = User.query.filter(
                User.is_trial_active == True,
                User.trial_end_date > datetime.utcnow()
            ).count()
            approved_users = User.query.filter_by(admin_approved=True).count()
            total_bots = Bot.query.count()
            total_messages = Message.query.count()
            
            # Create daily stats
            stats = SystemStats()
            stats.date = today
            stats.total_users = total_users
            stats.active_trials = active_trials
            stats.approved_users = approved_users
            stats.total_bots = total_bots
            stats.total_messages = total_messages
            
            db.session.add(stats)
            db.session.commit()
            
            logging.info(f"Daily stats updated for {today}")
            
    except Exception as e:
        logging.error(f"Error updating daily stats: {e}")

def cleanup_old_data():
    """Clean up old data (optional)"""
    try:
        from app import app, db
        from models import Message, SystemStats
        
        with app.app_context():
            # Delete messages older than 90 days
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            old_messages = Message.query.filter(
                Message.created_at < ninety_days_ago
            ).delete()
            
            # Delete old stats (keep last 365 days)
            year_ago = datetime.utcnow().date() - timedelta(days=365)
            old_stats = SystemStats.query.filter(
                SystemStats.date < year_ago
            ).delete()
            
            db.session.commit()
            
            if old_messages > 0 or old_stats > 0:
                logging.info(f"Cleaned up {old_messages} old messages and {old_stats} old stats")
            
    except Exception as e:
        logging.error(f"Error cleaning up old data: {e}")

def send_marketing_telegrams():
    """Send marketing Telegram messages to trial users every 3 days"""
    try:
        from app import app, db
        from services.telegram_marketing_service import TelegramMarketingService, get_trial_expired_telegram_users
        
        with app.app_context():
            # Get trial expired users who have telegram_chat_id
            trial_expired_users = get_trial_expired_telegram_users()
            
            if not trial_expired_users:
                logging.info("No trial expired users with Telegram found for marketing messages")
                return
            
            # Initialize Telegram marketing service
            marketing_service = TelegramMarketingService()
            
            # Send marketing messages to each user
            sent_count = 0
            failed_count = 0
            
            for user_data in trial_expired_users:
                try:
                    result = marketing_service.send_trial_expired_message(
                        chat_id=user_data['telegram_chat_id'],
                        user_name=user_data['full_name'] or user_data['username']
                    )
                    
                    if result and result.get('success'):
                        sent_count += 1
                        logging.info(f"Marketing Telegram sent to user {user_data['full_name'] or user_data['username']} (chat_id: {user_data['telegram_chat_id']})")
                    else:
                        failed_count += 1
                        logging.warning(f"Failed to send marketing Telegram to user {user_data['full_name'] or user_data['username']}: {result.get('error', 'Unknown error')}")
                        
                except Exception as user_error:
                    failed_count += 1
                    logging.error(f"Error sending marketing Telegram to user {user_data['full_name'] or user_data['username']}: {user_error}")
            
            logging.info(f"Marketing Telegrams sent: {sent_count} successful, {failed_count} failed to {len(trial_expired_users)} trial expired users")
            
    except Exception as e:
        logging.error(f"Error sending marketing Telegrams: {e}")

def send_trial_expiry_notifications():
    """Send notifications for trial expiry"""
    try:
        from app import app, db
        from models import User
        
        with app.app_context():
            # Find users whose trial expires tomorrow
            tomorrow = datetime.utcnow() + timedelta(days=1)
            expiring_tomorrow = User.query.filter(
                User.is_trial_active == True,
                User.trial_end_date <= tomorrow,
                User.trial_end_date > datetime.utcnow(),
                User.admin_approved == False,
                User.is_admin == False
            ).all()
            
            for user in expiring_tomorrow:
                # Here you could send email or SMS notifications
                logging.info(f"Trial expiring tomorrow for user: {user.username}")
            
            # Find users whose trial expired today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            expired_today = User.query.filter(
                User.is_trial_active == True,
                User.trial_end_date >= today_start,
                User.trial_end_date < today_end,
                User.admin_approved == False,
                User.is_admin == False
            ).all()
            
            for user in expired_today:
                logging.info(f"Trial expired today for user: {user.username}")
            
    except Exception as e:
        logging.error(f"Error sending trial expiry notifications: {e}")

def start_scheduler():
    """Start the background scheduler"""
    scheduler = BackgroundScheduler()
    
    # Check trial expiry every hour
    scheduler.add_job(
        func=check_trial_expiry,
        trigger=CronTrigger(minute=0),  # Every hour at minute 0
        id='trial_expiry_check',
        name='Check trial expiry',
        replace_existing=True
    )
    
    # Update daily stats at midnight
    scheduler.add_job(
        func=update_daily_stats,
        trigger=CronTrigger(hour=0, minute=5),  # Daily at 00:05
        id='daily_stats_update',
        name='Update daily statistics',
        replace_existing=True
    )
    
    # Send notifications at 9 AM daily
    scheduler.add_job(
        func=send_trial_expiry_notifications,
        trigger=CronTrigger(hour=9, minute=0),  # Daily at 09:00
        id='trial_notifications',
        name='Send trial expiry notifications',
        replace_existing=True
    )
    
    # Send marketing Telegrams every 3 days at 10 AM
    scheduler.add_job(
        func=send_marketing_telegrams,
        trigger=CronTrigger(day='*/3', hour=10, minute=0),  # Every 3 days at 10:00
        id='marketing_telegrams',
        name='Send marketing Telegrams to trial users',
        replace_existing=True
    )
    
    # Clean up old data weekly on Sunday at 2 AM
    scheduler.add_job(
        func=cleanup_old_data,
        trigger=CronTrigger(day_of_week=6, hour=2, minute=0),  # Weekly on Sunday at 02:00
        id='data_cleanup',
        name='Clean up old data',
        replace_existing=True
    )
    
    scheduler.start()
    logging.info("Background scheduler started")
    
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
