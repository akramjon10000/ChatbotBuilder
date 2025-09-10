import os
import logging
import requests
from datetime import datetime

class TelegramService:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, chat_id, text, reply_markup=None):
        """Send message to Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            if reply_markup:
                data['reply_markup'] = reply_markup
            
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            logging.error(f"Telegram send message error: {e}")
            return None
    
    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        """Edit existing message"""
        try:
            url = f"{self.base_url}/editMessageText"
            data = {
                'chat_id': chat_id,
                'message_id': message_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            if reply_markup:
                data['reply_markup'] = reply_markup
            
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            logging.error(f"Telegram edit message error: {e}")
            return None
    
    def answer_callback_query(self, callback_query_id, text=None):
        """Answer callback query"""
        try:
            url = f"{self.base_url}/answerCallbackQuery"
            data = {'callback_query_id': callback_query_id}
            if text:
                data['text'] = text
            
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            logging.error(f"Telegram callback query error: {e}")
            return None
    
    def create_language_keyboard(self):
        """Create inline keyboard for language selection"""
        return {
            'inline_keyboard': [
                [
                    {'text': '🇺🇿 O\'zbek', 'callback_data': 'lang_uz'},
                    {'text': '🇷🇺 Русский', 'callback_data': 'lang_ru'}
                ],
                [
                    {'text': '🇺🇸 English', 'callback_data': 'lang_en'}
                ]
            ]
        }
    
    def set_webhook(self, webhook_url):
        """Set webhook for Telegram bot"""
        try:
            url = f"{self.base_url}/setWebhook"
            data = {'url': webhook_url}
            
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            logging.error(f"Telegram webhook error: {e}")
            return None
    
    def get_bot_info(self):
        """Get bot information"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url)
            return response.json()
        except Exception as e:
            logging.error(f"Telegram bot info error: {e}")
            return None

class WhatsAppService:
    def __init__(self, access_token, phone_number_id):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/v17.0/{phone_number_id}"
    
    def send_message(self, to, message_text):
        """Send message to WhatsApp"""
        try:
            url = f"{self.base_url}/messages"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            data = {
                'messaging_product': 'whatsapp',
                'to': to,
                'text': {'body': message_text}
            }
            
            response = requests.post(url, json=data, headers=headers)
            return response.json()
        except Exception as e:
            logging.error(f"WhatsApp send message error: {e}")
            return None
    
    def send_template_message(self, to, template_name, language_code='en_US'):
        """Send template message to WhatsApp"""
        try:
            url = f"{self.base_url}/messages"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            data = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'template',
                'template': {
                    'name': template_name,
                    'language': {'code': language_code}
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            return response.json()
        except Exception as e:
            logging.error(f"WhatsApp template message error: {e}")
            return None

class InstagramService:
    def __init__(self, access_token, page_id):
        self.access_token = access_token
        self.page_id = page_id
        self.base_url = f"https://graph.facebook.com/v17.0/{page_id}"
    
    def send_message(self, recipient_id, message_text):
        """Send message to Instagram"""
        try:
            url = f"{self.base_url}/messages"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            data = {
                'recipient': {'id': recipient_id},
                'message': {'text': message_text}
            }
            
            response = requests.post(url, json=data, headers=headers)
            return response.json()
        except Exception as e:
            logging.error(f"Instagram send message error: {e}")
            return None
    
    def get_page_info(self):
        """Get page information"""
        try:
            url = f"{self.base_url}?fields=name,followers_count&access_token={self.access_token}"
            response = requests.get(url)
            return response.json()
        except Exception as e:
            logging.error(f"Instagram page info error: {e}")
            return None

class PlatformManager:
    """Manage multiple platform integrations"""
    
    def __init__(self):
        self.platforms = {}
    
    def add_telegram_bot(self, bot_id, token):
        """Add Telegram bot"""
        self.platforms[f'telegram_{bot_id}'] = TelegramService(token)
    
    def add_whatsapp_bot(self, bot_id, access_token, phone_number_id):
        """Add WhatsApp bot"""
        self.platforms[f'whatsapp_{bot_id}'] = WhatsAppService(access_token, phone_number_id)
    
    def add_instagram_bot(self, bot_id, access_token, page_id):
        """Add Instagram bot"""
        self.platforms[f'instagram_{bot_id}'] = InstagramService(access_token, page_id)
    
    def send_message(self, platform_key, *args, **kwargs):
        """Send message through specific platform"""
        if platform_key in self.platforms:
            return self.platforms[platform_key].send_message(*args, **kwargs)
        return None
    
    def broadcast_message(self, bot_id, message, recipients):
        """Broadcast message to multiple platforms"""
        results = {}
        
        for platform, recipient_id in recipients:
            platform_key = f"{platform}_{bot_id}"
            if platform_key in self.platforms:
                result = self.platforms[platform_key].send_message(recipient_id, message)
                results[f"{platform}_{recipient_id}"] = result
        
        return results
