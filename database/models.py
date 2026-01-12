"""
SQLAlchemy models for Cotabot database schema
"""
from sqlalchemy import Column, Integer, String, BigInteger, Float, DateTime, Date, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Player(Base):
    """Player model - stores basic player information"""
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    steam_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    discord_id = Column(BigInteger, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stats = relationship("PlayerStats", back_populates="player", cascade="all, delete-orphan", uselist=False)
    activity = relationship("ActivityLog", back_populates="player", cascade="all, delete-orphan")


class PlayerStats(Base):
    """Player statistics - all-time and season stats"""
    __tablename__ = 'player_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False, index=True, unique=True)
    
    # All-time stats
    total_score = Column(Integer, default=0)
    total_kills = Column(Integer, default=0)
    total_deaths = Column(Integer, default=0)
    total_revives = Column(Integer, default=0)
    total_kd_ratio = Column(Float, default=0.0)
    
    # Season stats
    season_score = Column(Integer, default=0)
    season_kills = Column(Integer, default=0)
    season_deaths = Column(Integer, default=0)
    season_revives = Column(Integer, default=0)
    season_kd_ratio = Column(Float, default=0.0)
    
    # Additional stats stored as JSON string (for flexibility)
    all_time_json = Column(Text)  # Full MySquadStats all-time data
    season_json = Column(Text)     # Full MySquadStats season data
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    player = relationship("Player", back_populates="stats")


class ActivityLog(Base):
    """Daily activity logs for players"""
    __tablename__ = 'activity_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey('players.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    minutes = Column(Integer, default=0)
    last_seen = Column(DateTime)
    
    player = relationship("Player", back_populates="activity")
    
    __table_args__ = (
        UniqueConstraint('player_id', 'date', name='_player_date_uc'),
    )


class Event(Base):
    """Discord events"""
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False, index=True)
    event_id = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    timestamp = Column(DateTime, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger)
    creator_id = Column(BigInteger, nullable=False)
    active = Column(Boolean, default=True, index=True)
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('guild_id', 'event_id', name='_guild_event_uc'),
    )


class EventParticipant(Base):
    """Event participants with their status"""
    __tablename__ = 'event_participants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    user_mention = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # 'attendee', 'declined', 'tentative'
    reason = Column(Text)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    event = relationship("Event", back_populates="participants")
    
    __table_args__ = (
        UniqueConstraint('event_id', 'user_id', name='_event_user_uc'),
    )


class PassiveRequest(Base):
    """Passive/away requests from users"""
    __tablename__ = 'passive_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    user_name = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
