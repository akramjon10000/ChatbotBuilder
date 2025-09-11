import os
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

class ServiceResponse:
    """Standard response object for all platform services"""
    def __init__(self, success: bool, data: Any = None, error_message: Optional[str] = None, status_code: Optional[int] = None):
        self.success = success
        self.data = data
        self.error_message = error_message
        self.status_code = status_code

class TelegramService:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.timeout = 30  # 30 seconds timeout for all requests
    
    def send_message(self, chat_id, text, reply_markup=None) -> ServiceResponse:
        """Send message to Telegram with robust error handling"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            if reply_markup:
                data['reply_markup'] = reply_markup
            
            response = requests.post(url, json=data, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: Failed to send message to Telegram"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from Telegram API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check Telegram API 'ok' flag
            if not json_response.get('ok', False):
                error_code = json_response.get('error_code', 'unknown')
                error_description = json_response.get('description', 'No description provided')
                error_msg = f"Telegram API error {error_code}: {error_description}"
                logging.error(f"Failed to send message to chat {chat_id}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            logging.info(f"Successfully sent message to Telegram chat {chat_id}")
            return ServiceResponse(True, data=json_response.get('result'))
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while sending message to Telegram"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Telegram API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while sending message to Telegram: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while sending message to Telegram: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
    
    def edit_message(self, chat_id, message_id, text, reply_markup=None) -> ServiceResponse:
        """Edit existing message with robust error handling"""
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
            
            response = requests.post(url, json=data, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: Failed to edit message on Telegram"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from Telegram API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check Telegram API 'ok' flag
            if not json_response.get('ok', False):
                error_code = json_response.get('error_code', 'unknown')
                error_description = json_response.get('description', 'No description provided')
                error_msg = f"Telegram API error {error_code}: {error_description}"
                logging.error(f"Failed to edit message {message_id} in chat {chat_id}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            logging.info(f"Successfully edited message {message_id} in Telegram chat {chat_id}")
            return ServiceResponse(True, data=json_response.get('result'))
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while editing message on Telegram"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Telegram API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while editing message on Telegram: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while editing message on Telegram: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
    
    def answer_callback_query(self, callback_query_id, text=None) -> ServiceResponse:
        """Answer callback query with robust error handling"""
        try:
            url = f"{self.base_url}/answerCallbackQuery"
            data = {'callback_query_id': callback_query_id}
            if text:
                data['text'] = text
            
            response = requests.post(url, json=data, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: Failed to answer callback query on Telegram"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from Telegram API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check Telegram API 'ok' flag
            if not json_response.get('ok', False):
                error_code = json_response.get('error_code', 'unknown')
                error_description = json_response.get('description', 'No description provided')
                error_msg = f"Telegram API error {error_code}: {error_description}"
                logging.error(f"Failed to answer callback query {callback_query_id}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            logging.info(f"Successfully answered callback query {callback_query_id}")
            return ServiceResponse(True, data=json_response.get('result'))
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while answering callback query"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Telegram API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while answering callback query: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while answering callback query: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
    
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
    
    def set_webhook(self, webhook_url) -> ServiceResponse:
        """Set webhook for Telegram bot with robust error handling"""
        try:
            url = f"{self.base_url}/setWebhook"
            data = {'url': webhook_url}
            
            response = requests.post(url, json=data, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: Failed to set webhook on Telegram"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from Telegram API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check Telegram API 'ok' flag
            if not json_response.get('ok', False):
                error_code = json_response.get('error_code', 'unknown')
                error_description = json_response.get('description', 'No description provided')
                error_msg = f"Telegram API error {error_code}: {error_description}"
                logging.error(f"Failed to set webhook {webhook_url}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            logging.info(f"Successfully set webhook to {webhook_url}")
            return ServiceResponse(True, data=json_response.get('result'))
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while setting webhook"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Telegram API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while setting webhook: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while setting webhook: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
    
    def get_bot_info(self) -> ServiceResponse:
        """Get bot information with robust error handling"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: Failed to get bot info from Telegram"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from Telegram API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check Telegram API 'ok' flag
            if not json_response.get('ok', False):
                error_code = json_response.get('error_code', 'unknown')
                error_description = json_response.get('description', 'No description provided')
                error_msg = f"Telegram API error {error_code}: {error_description}"
                logging.error(f"Failed to get bot info: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            logging.info("Successfully retrieved bot information")
            return ServiceResponse(True, data=json_response.get('result'))
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while getting bot info"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Telegram API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while getting bot info: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while getting bot info: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)

class WhatsAppService:
    def __init__(self, access_token, phone_number_id):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/v17.0/{phone_number_id}"
        self.timeout = 30  # 30 seconds timeout for all requests
    
    def send_message(self, to, message_text) -> ServiceResponse:
        """Send message to WhatsApp with robust error handling"""
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
            
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code not in [200, 201]:
                error_msg = f"HTTP {response.status_code}: Failed to send message to WhatsApp"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from WhatsApp API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check for error in response
            if 'error' in json_response:
                error_info = json_response['error']
                error_code = error_info.get('code', 'unknown')
                error_message = error_info.get('message', 'No error message provided')
                error_msg = f"WhatsApp API error {error_code}: {error_message}"
                logging.error(f"Failed to send message to {to}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            # Check for successful message ID
            messages = json_response.get('messages', [])
            if not messages:
                error_msg = "WhatsApp API returned no message ID"
                logging.error(f"Failed to send message to {to}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg)
            
            logging.info(f"Successfully sent WhatsApp message to {to}")
            return ServiceResponse(True, data=json_response)
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while sending message to WhatsApp"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to WhatsApp API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while sending message to WhatsApp: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while sending message to WhatsApp: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
    
    def send_template_message(self, to, template_name, language_code='en_US') -> ServiceResponse:
        """Send template message to WhatsApp with robust error handling"""
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
            
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code not in [200, 201]:
                error_msg = f"HTTP {response.status_code}: Failed to send template message to WhatsApp"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from WhatsApp API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check for error in response
            if 'error' in json_response:
                error_info = json_response['error']
                error_code = error_info.get('code', 'unknown')
                error_message = error_info.get('message', 'No error message provided')
                error_msg = f"WhatsApp API error {error_code}: {error_message}"
                logging.error(f"Failed to send template message {template_name} to {to}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            # Check for successful message ID
            messages = json_response.get('messages', [])
            if not messages:
                error_msg = "WhatsApp API returned no message ID"
                logging.error(f"Failed to send template message {template_name} to {to}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg)
            
            logging.info(f"Successfully sent WhatsApp template message {template_name} to {to}")
            return ServiceResponse(True, data=json_response)
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while sending template message to WhatsApp"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to WhatsApp API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while sending template message to WhatsApp: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while sending template message to WhatsApp: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)

class InstagramService:
    def __init__(self, access_token, page_id):
        self.access_token = access_token
        self.page_id = page_id
        self.base_url = f"https://graph.facebook.com/v17.0/{page_id}"
        self.timeout = 30  # 30 seconds timeout for all requests
    
    def send_message(self, recipient_id, message_text) -> ServiceResponse:
        """Send message to Instagram with robust error handling"""
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
            
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code not in [200, 201]:
                error_msg = f"HTTP {response.status_code}: Failed to send message to Instagram"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from Instagram API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check for error in response
            if 'error' in json_response:
                error_info = json_response['error']
                error_code = error_info.get('code', 'unknown')
                error_message = error_info.get('message', 'No error message provided')
                error_msg = f"Instagram API error {error_code}: {error_message}"
                logging.error(f"Failed to send message to {recipient_id}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            # Check for successful message ID
            message_id = json_response.get('message_id')
            if not message_id:
                error_msg = "Instagram API returned no message ID"
                logging.error(f"Failed to send message to {recipient_id}: {error_msg}")
                return ServiceResponse(False, error_message=error_msg)
            
            logging.info(f"Successfully sent Instagram message to {recipient_id}")
            return ServiceResponse(True, data=json_response)
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while sending message to Instagram"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Instagram API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while sending message to Instagram: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while sending message to Instagram: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
    
    def get_page_info(self) -> ServiceResponse:
        """Get page information with robust error handling"""
        try:
            url = f"{self.base_url}?fields=name,followers_count&access_token={self.access_token}"
            response = requests.get(url, timeout=self.timeout)
            
            # Check HTTP status code
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: Failed to get page info from Instagram"
                logging.error(f"{error_msg}. Response: {response.text}")
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Parse JSON response
            try:
                json_response = response.json()
            except ValueError as e:
                error_msg = f"Invalid JSON response from Instagram API: {str(e)}"
                logging.error(error_msg)
                return ServiceResponse(False, error_message=error_msg, status_code=response.status_code)
            
            # Check for error in response
            if 'error' in json_response:
                error_info = json_response['error']
                error_code = error_info.get('code', 'unknown')
                error_message = error_info.get('message', 'No error message provided')
                error_msg = f"Instagram API error {error_code}: {error_message}"
                logging.error(f"Failed to get page info: {error_msg}")
                return ServiceResponse(False, error_message=error_msg, status_code=error_code)
            
            logging.info("Successfully retrieved Instagram page information")
            return ServiceResponse(True, data=json_response)
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout after {self.timeout} seconds while getting page info"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to Instagram API"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error while getting page info: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while getting page info: {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)

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
    
    def send_message(self, platform_key, *args, **kwargs) -> ServiceResponse:
        """Send message through specific platform with robust error handling"""
        if platform_key not in self.platforms:
            error_msg = f"Platform '{platform_key}' not found in registered platforms"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
        
        try:
            result = self.platforms[platform_key].send_message(*args, **kwargs)
            if isinstance(result, ServiceResponse):
                return result
            else:
                # Handle legacy responses that might still return raw data
                if result:
                    logging.warning(f"Platform '{platform_key}' returned non-ServiceResponse object")
                    return ServiceResponse(True, data=result)
                else:
                    return ServiceResponse(False, error_message=f"Platform '{platform_key}' returned None")
        except Exception as e:
            error_msg = f"Unexpected error sending message through platform '{platform_key}': {str(e)}"
            logging.error(error_msg)
            return ServiceResponse(False, error_message=error_msg)
    
    def broadcast_message(self, bot_id, message, recipients) -> Dict[str, ServiceResponse]:
        """Broadcast message to multiple platforms with detailed results"""
        results = {}
        successful_count = 0
        failed_count = 0
        
        for platform, recipient_id in recipients:
            platform_key = f"{platform}_{bot_id}"
            result_key = f"{platform}_{recipient_id}"
            
            if platform_key not in self.platforms:
                error_msg = f"Platform '{platform_key}' not found in registered platforms"
                logging.error(f"Broadcast failed for {result_key}: {error_msg}")
                results[result_key] = ServiceResponse(False, error_message=error_msg)
                failed_count += 1
                continue
            
            try:
                result = self.platforms[platform_key].send_message(recipient_id, message)
                if isinstance(result, ServiceResponse):
                    results[result_key] = result
                    if result.success:
                        successful_count += 1
                    else:
                        failed_count += 1
                else:
                    # Handle legacy responses
                    if result:
                        logging.warning(f"Platform '{platform_key}' returned non-ServiceResponse object")
                        results[result_key] = ServiceResponse(True, data=result)
                        successful_count += 1
                    else:
                        results[result_key] = ServiceResponse(False, error_message=f"Platform '{platform_key}' returned None")
                        failed_count += 1
            except Exception as e:
                error_msg = f"Unexpected error broadcasting to {platform_key}: {str(e)}"
                logging.error(error_msg)
                results[result_key] = ServiceResponse(False, error_message=error_msg)
                failed_count += 1
        
        logging.info(f"Broadcast completed: {successful_count} successful, {failed_count} failed")
        return results
