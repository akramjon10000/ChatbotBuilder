"""
Marketing Email Service using SendGrid
Marketing email yuborish uchun servis - SendGrid integratsiyasidan foydalanadi
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)

class MarketingEmailService:
    """SendGrid orqali marketing emaillar yuborish uchun servis"""
    
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        if not self.api_key:
            logger.error("SENDGRID_API_KEY environment variable not set")
            raise ValueError("SENDGRID_API_KEY environment variable must be set")
        
        self.client = SendGridAPIClient(self.api_key)
        self.from_email = "noreply@chatbot.uz"  # Default from email
        self.from_name = "AI Chatbot Platform"
    
    def send_single_email(self, to_email: str, subject: str, html_content: str, 
                         text_content: Optional[str] = None) -> Dict:
        """
        Bitta foydalanuvchiga email yuborish
        
        Args:
            to_email: Maqsad email manzil
            subject: Email sarlavhasi
            html_content: HTML format email matni
            text_content: Matn format email matni (ixtiyoriy)
            
        Returns:
            dict: Yuborish natijasi
        """
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject
            )
            
            # HTML content qo'shish
            if html_content:
                message.content = Content("text/html", html_content)
            elif text_content:
                message.content = Content("text/plain", text_content)
            
            response = self.client.send(message)
            
            return {
                'success': True,
                'status_code': response.status_code,
                'message_id': response.headers.get('X-Message-Id', ''),
                'to_email': to_email
            }
            
        except Exception as e:
            logger.error(f"SendGrid email error to {to_email}: {e}")
            return {
                'success': False,
                'error': str(e),
                'to_email': to_email
            }
    
    def send_bulk_emails(self, email_list: List[str], subject: str, 
                        html_content: str, text_content: Optional[str] = None) -> Dict:
        """
        Ko'p foydalanuvchilarga email yuborish
        
        Args:
            email_list: Email manzillar ro'yxati
            subject: Email sarlavhasi
            html_content: HTML format email matni
            text_content: Matn format email matni
            
        Returns:
            dict: Yuborish statistikasi
        """
        results = {
            'total': len(email_list),
            'sent': 0,
            'failed': 0,
            'errors': [],
            'successful_emails': [],
            'failed_emails': []
        }
        
        for email in email_list:
            result = self.send_single_email(email, subject, html_content, text_content)
            
            if result['success']:
                results['sent'] += 1
                results['successful_emails'].append(email)
            else:
                results['failed'] += 1
                results['failed_emails'].append(email)
                results['errors'].append({
                    'email': email,
                    'error': result.get('error')
                })
        
        return results
    
    def create_trial_expired_email(self, user_name: str, include_contact: bool = True) -> str:
        """
        Sinov muddati tugagan foydalanuvchilar uchun email yaratish
        
        Args:
            user_name: Foydalanuvchi nomi
            include_contact: Aloqa ma'lumotlarini qo'shish
            
        Returns:
            str: HTML format email matni
        """
        contact_section = ""
        if include_contact:
            contact_section = f"""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #007bff; margin-bottom: 15px;">🚀 To'liq dostupga ega bo'ling!</h3>
                <p style="margin-bottom: 15px;">To'liq dostup uchun bizga aloqa chiqing:</p>
                <div style="margin-bottom: 10px;">
                    <strong>📞 Telefon:</strong> 
                    <a href="tel:+998996448444" style="color: #007bff; text-decoration: none;">+998 99 644 84 44</a>
                </div>
                <div style="margin-bottom: 10px;">
                    <strong>💬 Telegram:</strong> 
                    <a href="https://t.me/Akramjon1984" style="color: #007bff; text-decoration: none;">@Akramjon1984</a>
                </div>
                <p style="font-size: 14px; color: #6c757d; margin-top: 15px;">
                    Bir marta to'lov qilib, cheksiz foydalaning!
                </p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Chatbot Platform - Yana qaytib keling!</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #007bff; margin-bottom: 10px;">🤖 AI Chatbot Platform</h1>
                <p style="font-size: 18px; color: #6c757d;">Professional AI chatbot yaratish platformasi</p>
            </div>
            
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #856404; margin-bottom: 15px;">⏰ Salom, {user_name}!</h2>
                <p>3 kunlik bepul sinov muddatingiz tugagan. Lekin xavotir olmang - siz hali ham to'liq dostupga ega bo'lishingiz mumkin!</p>
            </div>
            
            <div style="margin-bottom: 30px;">
                <h3 style="color: #007bff;">✨ Siz nimalarga ega bo'lasiz:</h3>
                <ul style="padding-left: 20px;">
                    <li style="margin-bottom: 10px;">🤖 <strong>Cheksiz chatbotlar</strong> yaratish</li>
                    <li style="margin-bottom: 10px;">💬 <strong>Cheksiz xabarlar</strong> almashish</li>
                    <li style="margin-bottom: 10px;">🌍 <strong>Uch tilda</strong> (O'zbek, Rus, Ingliz) AI javoblar</li>
                    <li style="margin-bottom: 10px;">📱 <strong>Telegram, WhatsApp, Instagram</strong> integratsiyasi</li>
                    <li style="margin-bottom: 10px;">⚡ <strong>24/7 qo'llab-quvvatlash</strong></li>
                    <li style="margin-bottom: 10px;">📊 <strong>Batafsil statistika</strong> va hisobotlar</li>
                </ul>
            </div>
            
            {contact_section}
            
            <div style="text-align: center; margin: 30px 0;">
                <p style="font-size: 16px; color: #6c757d;">Yana platform foydalanishni boshlang!</p>
            </div>
            
            <div style="text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                <p style="font-size: 14px; color: #6c757d; margin: 0;">
                    © 2024 AI Chatbot Platform. Barcha huquqlar himoyalangan.<br>
                    Agar bu emailni olmashni istamasangiz, bizga aloqa chiqing.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def create_general_marketing_email(self, subject: str, content: str, 
                                     include_contact: bool = True) -> str:
        """
        Umumiy marketing email yaratish
        
        Args:
            subject: Email sarlavhasi
            content: Email asosiy matni
            include_contact: Aloqa ma'lumotlarini qo'shish
            
        Returns:
            str: HTML format email matni
        """
        contact_section = ""
        if include_contact:
            contact_section = f"""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #007bff; margin-bottom: 15px;">📞 Bizga aloqa chiqing</h3>
                <div style="margin-bottom: 10px;">
                    <strong>Telefon:</strong> 
                    <a href="tel:+998996448444" style="color: #007bff; text-decoration: none;">+998 99 644 84 44</a>
                </div>
                <div>
                    <strong>Telegram:</strong> 
                    <a href="https://t.me/Akramjon1984" style="color: #007bff; text-decoration: none;">@Akramjon1984</a>
                </div>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #007bff; margin-bottom: 10px;">🤖 AI Chatbot Platform</h1>
                <p style="font-size: 18px; color: #6c757d;">Professional AI chatbot yaratish platformasi</p>
            </div>
            
            <div style="background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
                <div style="margin-bottom: 20px;">
                    {content}
                </div>
            </div>
            
            {contact_section}
            
            <div style="text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                <p style="font-size: 14px; color: #6c757d; margin: 0;">
                    © 2024 AI Chatbot Platform. Barcha huquqlar himoyalangan.<br>
                    Bu emailni olmashni istamasangiz, bizga aloqa chiqing.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html_content

def get_trial_expired_users() -> List[Dict]:
    """
    Sinov muddati tugagan foydalanuvchilarni olish
    
    Returns:
        List[Dict]: Foydalanuvchilar ro'yxati
    """
    from models import User, AccessStatus
    from datetime import datetime
    
    # Sinov muddati tugagan foydalanuvchilar
    expired_users = User.query.filter(
        User.is_trial_active == True,
        User.trial_end_date <= datetime.utcnow(),
        User.admin_approved == False,
        User.is_admin == False,
        User.email.isnot(None)
    ).all()
    
    return [{'email': user.email, 'name': user.username or user.full_name or 'Foydalanuvchi'} 
            for user in expired_users if user.email]

def get_active_trial_users() -> List[Dict]:
    """
    Faol sinov foydalanuvchilarini olish
    
    Returns:
        List[Dict]: Foydalanuvchilar ro'yxati
    """
    from models import User, AccessStatus
    from datetime import datetime
    
    # Faol sinov foydalanuvchilari
    active_trial_users = User.query.filter(
        User.is_trial_active == True,
        User.trial_end_date > datetime.utcnow(),
        User.is_admin == False,
        User.email.isnot(None)
    ).all()
    
    return [{'email': user.email, 'name': user.username or user.full_name or 'Foydalanuvchi'} 
            for user in active_trial_users if user.email]

def get_all_users() -> List[Dict]:
    """
    Barcha foydalanuvchilarni olish
    
    Returns:
        List[Dict]: Foydalanuvchilar ro'yxati
    """
    from models import User
    
    # Barcha foydalanuvchilar (adminlarni hisobga olmasdan)
    all_users = User.query.filter(
        User.is_admin == False,
        User.email.isnot(None)
    ).all()
    
    return [{'email': user.email, 'name': user.username or user.full_name or 'Foydalanuvchi'} 
            for user in all_users if user.email]