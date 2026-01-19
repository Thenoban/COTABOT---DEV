"""
Gunicorn configuration file for Cotabot Web Panel
Production WSGI server configuration
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
# Using eventlet for SocketIO WebSocket support
workers = 1  # Eventlet workers handle concurrency internally
worker_class = "eventlet"  # Required for SocketIO/WebSocket support
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "cotabot-panel"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed in future)
# keyfile = None
# certfile = None

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🚀 Starting Cotabot Web Panel with Gunicorn")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("🔄 Reloading Cotabot Web Panel")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("✅ Cotabot Web Panel is ready to accept connections")
    server.log.info(f"📡 Listening on: {bind}")
    server.log.info(f"👷 Workers: {workers}")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("👋 Shutting down Cotabot Web Panel")
