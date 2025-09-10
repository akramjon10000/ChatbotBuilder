# AI Chatbot Platform

## Overview

This is a multilingual AI chatbot platform built with Flask that allows users to create and deploy intelligent chatbots. The platform supports Uzbek, Russian, and English languages and integrates with multiple messaging platforms including Telegram, WhatsApp, and Instagram. Users get a 3-day free trial before requiring admin approval for continued access.

Key features include:
- AI-powered chatbots using Google Gemini API
- Multi-platform deployment (Telegram, WhatsApp, Instagram)
- User management with trial system and admin approval workflow
- Real-time chat interface with conversation history
- Knowledge base upload and management
- Comprehensive admin panel with analytics
- Internationalization support with Flask-Babel

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
- **Session Management**: Server-side sessions with configurable secret key
- **Database Models**: User, Bot, Conversation, Message, KnowledgeBase, AdminAction, SystemStats
- **Route Organization**: Modular routing with separate files for admin, auth, and main functionality

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
- **Scheduler**: APScheduler for automated trial expiry checks and statistics updates
- **Daily Statistics**: Automated collection of usage metrics and system health data
- **Cleanup Tasks**: Periodic maintenance and data archival processes

## External Dependencies

### AI Services
- **Google Gemini API**: Primary AI service for generating chatbot responses
- **Configuration**: API key-based authentication via environment variables

### Messaging Platform APIs
- **Telegram Bot API**: Full integration for bot deployment and webhook management
- **WhatsApp Business API**: Business messaging integration (framework prepared)
- **Instagram Business API**: Social media messaging integration (framework prepared)

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