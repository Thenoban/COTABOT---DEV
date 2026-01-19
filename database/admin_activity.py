"""
Admin Activity Log Model
Tracks all admin actions for dashboard display
"""
from sqlalchemy import Column, Integer, String, BigInteger, Text, DateTime
from datetime import datetime
from .models import Base

class AdminActivityLog(Base):
    """Logs all admin actions for web panel activity display"""
    __tablename__ = 'admin_activity_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String(50), nullable=False, index=True)  # player_add, player_delete, event_create, etc.
    admin_user = Column(String(100), default='web_admin')  # Who performed the action
    target = Column(String(200))  # What was affected (player name, event title, etc.)
    details = Column(Text)  # JSON details or description
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<AdminActivityLog(action={self.action_type}, target={self.target}, time={self.timestamp})>"
