"""
Flask-SocketIO integration for real-time web-bot communication
Install: pip install flask-socketio python-socketio
"""
from flask_socketio import SocketIO, emit
from flask import request
import logging

logger = logging.getLogger("SocketIO")

# Initialize SocketIO
socketio = None

def init_socketio(app):
    """Initialize SocketIO with Flask app"""
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",  # Configure based on security needs
        async_mode='threading',
        logger=True,
        engineio_logger=False
    )
    
    # Register event handlers
    register_handlers(socketio)
    
    logger.info("✅ SocketIO initialized")
    return socketio


def register_handlers(sio):
    """Register SocketIO event handlers"""
    
    @sio.on('connect')
    def handle_connect():
        logger.info(f"🔌 Client connected: {request.sid}")
        emit('server_message', {'data': 'Connected to Cotabot Web Admin'})
    
    @sio.on('disconnect')
    def handle_disconnect():
        logger.info(f"🔌 Client disconnected: {request.sid}")
    
    @sio.on('ping')
    def handle_ping(data):
        """Ping-pong for connection testing"""
        emit('pong', {'timestamp': data.get('timestamp')})
    
    @sio.on('bot_status_request')
    def handle_bot_status_request():
        """Request bot status"""
        # This will be handled by bot bridge
        emit('bot_status_pending', {'message': 'Checking bot status...'})


def broadcast_event(event_type: str, data: dict):
    """Broadcast event to all connected clients"""
    if socketio:
        socketio.emit(event_type, data)
        logger.info(f"📡 Broadcasted: {event_type}")


def send_to_client(sid: str, event_type: str, data: dict):
    """Send event to specific client"""
    if socketio:
        socketio.emit(event_type, data, room=sid)
