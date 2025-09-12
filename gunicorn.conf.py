# Gunicorn configuration for production
import multiprocessing
import os

# Server socket - Use PORT env var for Render deployment
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"
backlog = 2048

# Worker processes - Use WEB_CONCURRENCY if available (for Render deployment)
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Preload app for better performance
preload_app = True

# Logging
accesslog = "-"
errorlog = "-" 
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'ai_chatbot_platform'

# Server mechanics
daemon = False
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# SSL - uncomment for HTTPS
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190