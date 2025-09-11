"""
Telegram Bot API service for mass broadcasting and user messaging
Telegram Bot API integratsiyasi uchun servis - python_sendgrid integratsiyasidan ilhomlangan
"""
import os
import sys
import time
import requests
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class TelegramService:
    """Telegram Bot API bilan ishlash uchun servis"""
    
    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("Telegram bot token bo'sh bo'lishi mumkin emas")
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
    def send_message(self, chat_id: str, text: str, parse_mode: str = 'HTML') -> Dict:
        """
        Bitta foydalanuvchiga habar yuborish
        
        Args:
            chat_id: Telegram chat ID yoki username (@username)
            text: Yuborilayotgan habar matni
            parse_mode: Matn formati (HTML yoki Markdown)
            
        Returns:
            dict: API javob ma'lumotlari
        """
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            result = response.json()
            
            if response.status_code == 200 and result.get('ok'):
                return {
                    'success': True,
                    'message_id': result['result']['message_id'],
                    'chat_id': result['result']['chat']['id']
                }
            else:
                error_code = result.get('error_code', 'unknown')
                error_description = result.get('description', 'Unknown error')
                logger.error(f"Telegram API error {error_code}: {error_description}")
                
                return {
                    'success': False,
                    'error_code': error_code,
                    'error_description': error_description
                }
                
        except requests.RequestException as e:
            logger.error(f"Telegram network error: {e}")
            return {
                'success': False,
                'error_code': 'network_error',
                'error_description': str(e)
            }
    
    def send_channel_message(self, channel_id: str, text: str, parse_mode: str = 'HTML') -> Dict:
        """
        Kanal yoki gruppaga habar yuborish
        
        Args:
            channel_id: Kanal ID (@channel_name yoki -100xxxxxxxxx)
            text: Yuborilayotgan habar matni
            parse_mode: Matn formati
            
        Returns:
            dict: Yuborish natijasi
        """
        return self.send_message(channel_id, text, parse_mode)
    
    def send_bulk_messages(self, chat_ids: List[str], text: str, 
                          parse_mode: str = 'HTML', 
                          rate_limit_delay: float = 0.05) -> Dict:
        """
        Ko'p foydalanuvchilarga habar yuborish (rate limiting bilan)
        
        Args:
            chat_ids: Chat ID'lar ro'yxati
            text: Yuborilayotgan habar
            parse_mode: Matn formati
            rate_limit_delay: Habarlar orasidagi kutish vaqti (soniyalarda)
            
        Returns:
            dict: Yuborish statistikasi
        """
        results = {
            'total': len(chat_ids),
            'sent': 0,
            'failed': 0,
            'errors': [],
            'successful_chat_ids': [],
            'failed_chat_ids': []
        }
        
        for i, chat_id in enumerate(chat_ids):
            # Rate limiting - Telegram API cheklovlari uchun
            if i > 0:
                time.sleep(rate_limit_delay)
            
            result = self.send_message(chat_id, text, parse_mode)
            
            if result['success']:
                results['sent'] += 1
                results['successful_chat_ids'].append(chat_id)
            else:
                results['failed'] += 1
                results['failed_chat_ids'].append(chat_id)
                results['errors'].append({
                    'chat_id': chat_id,
                    'error_code': result.get('error_code'),
                    'error_description': result.get('error_description')
                })
                
                # Agar 429 (Too Many Requests) xatosi bo'lsa, ko'proq kutamiz
                if result.get('error_code') == 429:
                    retry_after = result.get('parameters', {}).get('retry_after', 1)
                    logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                    time.sleep(retry_after)
        
        return results
    
    def get_bot_info(self) -> Dict:
        """Bot ma'lumotlarini olish"""
        url = f"{self.base_url}/getMe"
        
        try:
            response = requests.get(url, timeout=10)
            result = response.json()
            
            if response.status_code == 200 and result.get('ok'):
                return {
                    'success': True,
                    'bot_info': result['result']
                }
            else:
                return {
                    'success': False,
                    'error': result.get('description', 'Unknown error')
                }
                
        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }

def send_telegram_notification(bot_token: str, chat_id: str, title: str, 
                             message: str, parse_mode: str = 'HTML') -> bool:
    """
    Telegram habar yuborish uchun oddiy funksiya
    
    Args:
        bot_token: Telegram bot token
        chat_id: Maqsad chat ID
        title: Habar sarlavhasi
        message: Habar matni
        parse_mode: Matn formati
        
    Returns:
        bool: Muvaffaqiyat holati
    """
    try:
        service = TelegramService(bot_token)
        
        # HTML formatda habar tayyorlash
        if parse_mode == 'HTML':
            formatted_message = f"<b>{title}</b>\n\n{message}"
        else:
            formatted_message = f"*{title}*\n\n{message}"
            
        result = service.send_message(chat_id, formatted_message, parse_mode)
        return result['success']
        
    except Exception as e:
        logger.error(f"Telegram notification error: {e}")
        return False

def get_user_chat_ids_from_conversations(target_all_users: bool = True,
                                        target_trial_users: bool = False,
                                        target_subscription_users: bool = False,
                                        target_approved_users: bool = False) -> List[str]:
    """
    Conversation jadvali orqali foydalanuvchilar chat_id larini olish
    Telegram webhook orqali saqlangan chat_id larni qaytaradi
    
    Args:
        target_all_users: Barcha foydalanuvchilarni maqsad qilish
        target_trial_users: Sinov foydalanuvchilarini maqsad qilish
        target_subscription_users: Obuna foydalanuvchilarini maqsad qilish
        target_approved_users: Tasdiqlangan foydalanuvchilarini maqsad qilish
        
    Returns:
        List[str]: Chat ID'lar ro'yxati
    """
    from models import Conversation, User, AccessStatus
    from sqlalchemy import and_
    
    # Base query - join Conversation with User and Bot
    base_query = Conversation.query.join(
        User, 
        and_(
            Conversation.user_id == User.id,
            User.is_admin == False,  # Exclude admins
            User.is_active == True   # Only active users
        )
    ).filter(
        Conversation.platform == 'telegram',
        Conversation.platform_user_id.isnot(None),
        Conversation.is_active == True
    )
    
    # Apply user segment filters
    if not target_all_users:
        user_filters = []
        
        if target_trial_users:
            user_filters.append(User.access_status == AccessStatus.TRIAL)
        
        if target_subscription_users:
            user_filters.append(
                User.access_status.in_([AccessStatus.MONTHLY, AccessStatus.YEARLY])
            )
        
        if target_approved_users:
            user_filters.append(User.access_status == AccessStatus.APPROVED)
        
        # If no specific targets selected but target_all_users is False, return empty
        if not user_filters:
            return []
        
        # Apply OR condition for multiple user types
        from sqlalchemy import or_
        base_query = base_query.filter(or_(*user_filters))
    
    # Get distinct chat IDs
    conversations = base_query.distinct(Conversation.platform_user_id).all()
    
    chat_ids = [conv.platform_user_id for conv in conversations if conv.platform_user_id]
    return chat_ids