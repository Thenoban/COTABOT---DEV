"""
Simple API Key Authentication Middleware
"""
from functools import wraps
from flask import request, jsonify
import config

def require_api_key(f):
    """
    Decorator to require API key authentication
    Usage: @require_api_key
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        
        # Check if API key is valid
        if api_key != config.API_KEY:
            return jsonify({
                'success': False,
                'error': 'Invalid or missing API key'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def login_with_api_key(api_key):
    """
    Validate API key for login
    Returns: (success: bool, message: str)
    """
    if api_key == config.API_KEY:
        return True, "Login successful"
    return False, "Invalid API key"
