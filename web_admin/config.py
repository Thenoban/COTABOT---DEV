"""
Configuration for Cotabot Web Admin Panel
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Environment configurations
ENVIRONMENTS = {
    'DEV': {
        'name': 'Development',
        'database_path': BASE_DIR / "cotabot_dev.db",
        'database_url': f"sqlite:///{BASE_DIR / 'cotabot_dev.db'}",
        'guild_id': 1234567890  # DEV guild ID (placeholder)
    },
    'LIVE': {
        'name': 'Production',
        'database_path': BASE_DIR.parent / "COTABOT" / "cotabot.db",
        'database_url': f"sqlite:///{BASE_DIR.parent / 'COTABOT' / 'cotabot.db'}",
        'guild_id': 9876543210  # LIVE guild ID (update with real ID)
    }
}

# Default environment
DEFAULT_ENVIRONMENT = 'DEV'

# Legacy database configuration (for backwards compatibility)
DATABASE_PATH = ENVIRONMENTS[DEFAULT_ENVIRONMENT]['database_path']
DATABASE_URL = ENVIRONMENTS[DEFAULT_ENVIRONMENT]['database_url']

# Flask configuration
SECRET_KEY = os.getenv("WEB_ADMIN_SECRET_KEY", "cotabot-web-admin-secret-key-change-in-production")
API_KEY = os.getenv("WEB_ADMIN_API_KEY", "cotabot-admin-2024")

# Server configuration
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5000

# CORS configuration
CORS_ORIGINS = ["*"]  # In production, specify exact origins

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# BattleMetrics API (for server status)
BM_API_URL = "https://api.battlemetrics.com"
SERVER_ID = "19262595"
BM_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbiI6ImZkNjFiNGUwNDg3NGVhOWMiLCJpYXQiOjE3Njc3ODQxMjMsIm5iZiI6MTc2Nzc4NDEyMywiaXNzIjoiaHR0cHM6Ly93d3cuYmF0dGxlbWV0cmljcy5jb20iLCJzdWIiOiJ1cm46dXNlcjoxMDUzOTEzIn0.jZ78RBn-O0_njNeGIJZlVrWXk5ptMdQ8bIFBgEsfmzw"

BATTLEMETRICS_TOKEN = os.getenv("BATTLEMETRICS_TOKEN", "")
BATTLEMETRICS_SERVER_ID = os.getenv("BATTLEMETRICS_SERVER_ID", "")

# Logging
LOG_LEVEL = "INFO"
