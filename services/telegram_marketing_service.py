import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

class TelegramMarketingService:
    """Telegram orqali marketing xabarlar yuborish servisi"""
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        TelegramMarketingService yaratish
        
        Args:
            bot_token: Telegram bot token. Agar berilmasa, environment'dan olinadi
        """
        if not bot_token:
            bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable yoki bot_token parametri kerak")
        
        self.telegram_service = TelegramService(bot_token)
        self.bot_token = bot_token
    
    def send_marketing_message(self, chat_id: str, message: str, parse_mode: str = 'HTML') -> Dict:
        """
        Bitta foydalanuvchiga marketing xabari yuborish
        
        Args:
            chat_id: Telegram chat ID
            message: Yuborilayotgan xabar matni
            parse_mode: Matn formati (HTML yoki Markdown)
            
        Returns:
            dict: Yuborish natijasi
        """
        try:
            result = self.telegram_service.send_message(chat_id, message, parse_mode)
            
            if result['success']:
                logger.info(f"Marketing message sent successfully to chat_id: {chat_id}")
                return {
                    'success': True,
                    'chat_id': chat_id,
                    'message_id': result['message_id']
                }
            else:
                logger.error(f"Failed to send marketing message to {chat_id}: {result.get('error_description', 'Unknown error')}")
                return {
                    'success': False,
                    'chat_id': chat_id,
                    'error': result.get('error_description', 'Unknown error'),
                    'error_code': result.get('error_code', 'unknown')
                }
                
        except Exception as e:
            logger.error(f"Exception sending marketing message to {chat_id}: {e}")
            return {
                'success': False,
                'chat_id': chat_id,
                'error': str(e),
                'error_code': 'exception'
            }
    
    def send_bulk_marketing_messages(self, chat_ids: List[str], message: str) -> Dict:
        """
        Ko'p foydalanuvchilarga marketing xabarlarini yuborish
        
        Args:
            chat_ids: Chat ID'lar ro'yxati
            message: Yuborilayotgan xabar matni
            
        Returns:
            dict: Yuborish statistikasi
        """
        sent_count = 0
        failed_count = 0
        failed_chats = []
        successful_chats = []
        
        logger.info(f"Starting bulk marketing message send to {len(chat_ids)} chats")
        
        for chat_id in chat_ids:
            result = self.send_marketing_message(chat_id, message)
            
            if result['success']:
                sent_count += 1
                successful_chats.append(chat_id)
            else:
                failed_count += 1
                failed_chats.append({
                    'chat_id': chat_id,
                    'error': result.get('error', 'Unknown error'),
                    'error_code': result.get('error_code', 'unknown')
                })
        
        logger.info(f"Bulk marketing send completed: {sent_count} sent, {failed_count} failed")
        
        return {
            'sent': sent_count,
            'failed': failed_count,
            'total': len(chat_ids),
            'successful_chats': successful_chats,
            'failed_chats': failed_chats
        }
    
    def create_trial_expired_message(self, user_name: str = "Aziz foydalanuvchi", include_contact: bool = True) -> str:
        """
        Trial muddati tugagan foydalanuvchilar uchun marketing xabari yaratish
        
        Args:
            user_name: Foydalanuvchi nomi
            include_contact: Aloqa ma'lumotlarini qo'shish
            
        Returns:
            str: HTML formatdagi xabar matni
        """
        message = f"""
🚀 <b>{user_name}!</b>

Sizning AI Chatbot Platform'dagi 3 kunlik bepul sinov muddati tugadi.

🤖 <b>Platformamizda nimalar mavjud:</b>
• Ko'p tilli AI chatbotlar (O'zbek, Rus, Ingliz)
• Telegram, WhatsApp, Instagram integratsiyasi
• Knowledge base boshqaruvi
• Real-time chat interfeysi
• To'liq admin panel

💡 <b>Nima uchun bizni tanlashingiz kerak?</b>
• Professional AI chatbot yechimlar
• Oson sozlash va boshqarish
• 24/7 texnik yordam
• Arzon narxlar

🎯 To'liq dostupni olish uchun aloqa qiling:
"""
        
        if include_contact:
            message += """
📞 <b>Aloqa:</b>
• Telefon: +998 99 644 84 44
• Telegram: @Akramjon1984

🔥 <i>Bizga aloqa qiling va professional AI chatbot xizmatidan foydalaning!</i>
"""
        
        return message.strip()
    
    def create_trial_active_message(self, user_name: str = "Aziz foydalanuvchi", days_left: int = 1) -> str:
        """
        Hali trial davom etayotgan foydalanuvchilar uchun xabar
        
        Args:
            user_name: Foydalanuvchi nomi
            days_left: Qolgan kunlar soni
            
        Returns:
            str: HTML formatdagi xabar matni
        """
        message = f"""
⏰ <b>{user_name}!</b>

Sizning bepul sinov mudatingiz {days_left} kun qoldi!

🚀 <b>Bu vaqt ichida sinab ko'rishingiz mumkin:</b>
• AI chatbot yaratish
• Turli platformalarga ulash
• Knowledge base yuklash
• Botingizni test qilish

💰 <b>To'liq dostup uchun:</b>
📞 Telefon: +998 99 644 84 44
📱 Telegram: @Akramjon1984

🎯 <i>Sinov mudatii tugashidan oldin aloqa qiling!</i>
"""
        
        return message.strip()


def get_trial_expired_telegram_users() -> List[Dict]:
    """Trial muddati tugagan foydalanuvchilarni olish"""
    from app import app, db
    from models import User, AccessStatus
    
    with app.app_context():
        users = User.query.filter(
            User.access_status == AccessStatus.TRIAL,
            User.trial_end_date <= datetime.utcnow(),
            User.admin_approved == False,
            User.is_admin == False,
            User.telegram_chat_id != None,
            User.marketing_opt_out == False
        ).all()
        
        result = []
        for user in users:
            # 3 kun ichida oxirgi xabar yuborilgan bo'lsa, qayta yubormaymiz
            if user.marketing_last_sent_at:
                last_sent = user.marketing_last_sent_at
                if datetime.utcnow() - last_sent < timedelta(days=3):
                    continue
            
            result.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name or user.username,
                'telegram_chat_id': user.telegram_chat_id,
                'trial_end_date': user.trial_end_date,
                'marketing_last_sent_at': user.marketing_last_sent_at
            })
        
        return result


def get_active_trial_users() -> List[Dict]:
    """Hali trial davom etayotgan foydalanuvchilarni olish"""
    from app import app, db
    from models import User, AccessStatus
    
    with app.app_context():
        users = User.query.filter(
            User.access_status == AccessStatus.TRIAL,
            User.trial_end_date > datetime.utcnow(),
            User.admin_approved == False,
            User.is_admin == False,
            User.telegram_chat_id != None,
            User.marketing_opt_out == False
        ).all()
        
        result = []
        for user in users:
            # Faqat trial tugashiga 1 kun qolganda xabar yuboramiz
            days_left = (user.trial_end_date - datetime.utcnow()).days
            if days_left != 1:
                continue
                
            # 1 kun ichida oxirgi xabar yuborilgan bo'lsa, qayta yubormaymiz
            if user.marketing_last_sent_at:
                last_sent = user.marketing_last_sent_at
                if datetime.utcnow() - last_sent < timedelta(days=1):
                    continue
            
            result.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name or user.username,
                'telegram_chat_id': user.telegram_chat_id,
                'trial_end_date': user.trial_end_date,
                'days_left': days_left,
                'marketing_last_sent_at': user.marketing_last_sent_at
            })
        
        return result


def get_all_telegram_users() -> List[Dict]:
    """Telegram chat_id ga ega barcha foydalanuvchilarni olish"""
    from app import app, db
    from models import User
    
    with app.app_context():
        users = User.query.filter(
            User.is_admin == False,
            User.telegram_chat_id != None,
            User.marketing_opt_out == False
        ).all()
        
        result = []
        for user in users:
            result.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name or user.username,
                'telegram_chat_id': user.telegram_chat_id,
                'access_status': user.access_status.value if user.access_status else 'unknown',
                'admin_approved': user.admin_approved,
                'marketing_last_sent_at': user.marketing_last_sent_at
            })
        
        return result


def update_marketing_sent_timestamp(user_ids: List[int]) -> None:
    """Foydalanuvchilar uchun marketing yuborilgan vaqtni yangilash"""
    from app import app, db
    from models import User
    
    with app.app_context():
        try:
            User.query.filter(User.id.in_(user_ids)).update(
                {User.marketing_last_sent_at: datetime.utcnow()},
                synchronize_session=False
            )
            db.session.commit()
            logger.info(f"Updated marketing timestamp for {len(user_ids)} users")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update marketing timestamps: {e}")