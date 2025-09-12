# AI Chatbot Platform

## Loyiha G'oyasi va Natijalar

Bu AI chatbot platform Flask asosida qurilgan bo'lib, foydalanuvchilarga aqlli chatbotlarni yaratish va deploy qilish imkonini beradi. Platform o'zbek, rus va ingliz tillarini qo'llab-quvvatlaydi va Telegram, WhatsApp, Instagram kabi ko'p platformalarga integratsiya qiladi.

### Asosiy Erishilgan Natijalar

**Texnik Yetakchilik:**
- ✅ To'liq responsive mobil dizayn (juda qulay mobil interfeys)
- ✅ Bilimlar bazasiga to'g'ridan-to'g'ri matn kiritish funksiyasi
- ✅ Google Gemini AI integratsiyasi
- ✅ Ko'p tillikni qo'llab-quvvatlash
- ✅ Render hosting uchun production-ready konfiguratsiya
- ✅ Xavfsizlik va autentifikatsiya tizimi

**Biznes Logikasi:**
- ✅ 3 kunlik bepul sinov muddat
- ✅ Admin tasdiqlash tizimi
- ✅ Real-time suhbat interfeysi
- ✅ Keng qamrovli admin panel va statistika
- ✅ Foydalanuvchi boshqaruvi va access control

**Mobil Optimizatsiya:**
- ✅ Touch-friendly interfeys elementlari
- ✅ Responsive navigation va formlar
- ✅ Mobile-first dizayn prinsipi
- ✅ Optimal loading va performance

### Boshqa Loyihalar Uchun G'oya va Yo'l-Yo'riq

Bu loyiha quyidagi texnologik yechimlarni namuna sifatida ko'rsatadi:

**1. AI Platform Yaratish Naqshasi:**
```
Flask (Backend) + Bootstrap (Frontend) + AI API + Cloud Hosting
```

**2. Zaruriy Komponentlar:**
- Web framework (Flask/Django/FastAPI)
- AI service integratsiyasi (Gemini/OpenAI/Claude)
- Database (PostgreSQL/SQLite)
- Authentication tizimi
- File upload va processing
- Real-time messaging
- Admin dashboard

**3. Deployment va Hosting:**
- Production server (Gunicorn)
- Cloud hosting (Render/Heroku/Vercel)
- Environment variables boshqaruvi
- Database migratsiya
- Static files serving

Bu loyiha AI-powered SaaS platformalar yaratishning to'liq namunasi hisoblanadi.

**4. Practical Implementation Guide:**
- Environment Variables: SESSION_SECRET, DATABASE_URL, GEMINI_API_KEY
- Running: `gunicorn --bind 0.0.0.0:5000 main:app`
- Mobile Optimization: CSS improvements in static/css/style.css
- Knowledge Base: Direct text input via /bot/<id> page modal system
- File Storage: uploads/knowledge/ directory for user-uploaded files

**5. Key Mobile Features Implemented:**
- Touch-friendly button sizes (min-height: 44px)
- Responsive forms with 16px font-size (prevents iOS zoom)
- Mobile navigation improvements
- Optimized modal systems for small screens
- Responsive table handling

## Overview

This is a multilingual AI chatbot platform built with Flask that allows users to create and deploy intelligent chatbots. The platform supports Uzbek, Russian, and English languages and integrates with multiple messaging platforms including Telegram, WhatsApp, and Instagram. Users get a 3-day free trial before requiring admin approval for continued access.

Key features include:
- AI-powered chatbots using Google Gemini API
- Multi-platform deployment (Telegram, WhatsApp, Instagram)
- User management with trial system and admin approval workflow
- Real-time chat interface with conversation history
- Knowledge base upload and management (file upload + direct text input)
- Comprehensive admin panel with analytics
- Internationalization support with Flask-Babel
- Mobile-optimized responsive design
- Production-ready deployment configuration

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI
- **Styling**: Custom CSS with Font Awesome icons, chart.js for analytics visualization
- **JavaScript**: Vanilla JavaScript with Bootstrap components for interactivity
- **Language Support**: Flask-Babel for internationalization across Uzbek, Russian, and English

### Backend Architecture
- **Web Framework**: Flask with SQLAlchemy ORM for database operations
- **Authentication**: Flask-Login with password hashing using Werkzeug security
- **Session Management**: Flask cookie-based sessions with configurable secret key
- **Database Models**: User model (with extensible structure for future models)
- **Route Organization**: Modular routing with routes.py and admin_routes.py

### Trial and Access Control System
- **Trial Management**: 3-day free trial for new users with automatic expiration tracking
- **Access Control**: Decorator-based permission system (@admin_required, @trial_required)
- **Admin Approval Workflow**: Manual approval process after trial expiration
- **User Status Tracking**: Real-time monitoring of trial status and access permissions

### AI Integration
- **AI Service**: Google Gemini API integration for multilingual response generation
- **Language Detection**: Automatic language detection with fallback responses
- **Context Management**: System prompts and conversation context preservation
- **Error Handling**: Graceful degradation with fallback responses when AI service fails

### Background Tasks
- **Scheduler**: APScheduler framework prepared for future automated tasks
- **Statistics**: Basic usage tracking and system metrics collection
- **Future Features**: Trial expiry automation and maintenance tasks (ready for implementation)

## External Dependencies

### AI Services
- **Google Gemini API**: Primary AI service for generating chatbot responses
- **Configuration**: API key-based authentication via environment variables

### Messaging Platform APIs
- **Telegram Bot API**: Full integration for bot deployment and webhook management
- **WhatsApp Business API**: Framework prepared for future integration
- **Instagram Business API**: Framework prepared for future integration

### Database
- **SQLAlchemy**: Database abstraction layer supporting multiple database backends
- **Default Database**: SQLite for development, configurable for PostgreSQL in production
- **Connection Pooling**: Configured with pool recycling and pre-ping for reliability

### Development and Production Tools
- **Gunicorn**: WSGI HTTP Server for production deployment
- **APScheduler**: Background task scheduling for maintenance operations
- **Flask Extensions**: Flask-Login, Flask-Babel, Flask-SQLAlchemy for core functionality

### Frontend Dependencies
- **Bootstrap 5**: CSS framework for responsive design
- **Font Awesome**: Icon library for consistent UI elements
- **Chart.js**: Data visualization for admin analytics
- **CDN Delivery**: External CDN for frontend assets to improve performance