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


# ============================================
# REPORT SYSTEM MODELS
# ============================================

class ReportSnapshot(Base):
    """Stores player stats snapshots for period comparisons"""
    __tablename__ = 'report_snapshots'
    
    id = Column(Integer, primary_key=True)
    period_type = Column(String(20), nullable=False)  # 'weekly' or 'monthly'
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Snapshot entries (one per player)
    entries = relationship("SnapshotEntry", back_populates="snapshot", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ReportSnapshot(period={self.period_type}, timestamp={self.timestamp})>"



class SnapshotEntry(Base):
    """Individual player entry in a snapshot"""
    __tablename__ = 'snapshot_entries'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('report_snapshots.id'), nullable=False)
    steam_id = Column(String(50), nullable=False)
    
    # Stats at snapshot time
    score = Column(Integer, default=0)
    kills = Column(Integer, default=0)
    deaths = Column(Integer, default=0)
    revives = Column(Integer, default=0)
    wounds = Column(Integer, default=0)
    kd_ratio = Column(Float, default=0.0)
    
    # Relationship
    snapshot = relationship("ReportSnapshot", back_populates="entries")
    
    def __repr__(self):
        return f"<SnapshotEntry(steam_id={self.steam_id}, score={self.score})>"



class ReportDelta(Base):
    """Stores calculated deltas between snapshots"""
    __tablename__ = 'report_deltas'
    
    id = Column(Integer, primary_key=True)
    period_type = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Before/After snapshots
    start_snapshot_id = Column(Integer, ForeignKey('report_snapshots.id'))
    end_snapshot_id = Column(Integer, ForeignKey('report_snapshots.id'))
    
    # Delta entries
    entries = relationship("DeltaEntry", back_populates="delta", cascade="all, delete-orphan")
    
    # Relationships
    start_snapshot = relationship("ReportSnapshot", foreign_keys=[start_snapshot_id])
    end_snapshot = relationship("ReportSnapshot", foreign_keys=[end_snapshot_id])
    
    def __repr__(self):
        return f"<ReportDelta(period={self.period_type}, timestamp={self.timestamp})>"



class DeltaEntry(Base):
    """Individual player delta in a report"""
    __tablename__ = 'delta_entries'
    
    id = Column(Integer, primary_key=True)
    delta_id = Column(Integer, ForeignKey('report_deltas.id'), nullable=False)
    steam_id = Column(String(50), nullable=False)
    player_name = Column(String(100))
    
    # Deltas
    score_delta = Column(Integer, default=0)
    kills_delta = Column(Integer, default=0)
    deaths_delta = Column(Integer, default=0)
    revives_delta = Column(Integer, default=0)
    wounds_delta = Column(Integer, default=0)
    
    # Rankings
    rank = Column(Integer)
    
    # Relationship
    delta = relationship("ReportDelta", back_populates="entries")
    
    def __repr__(self):
        return f"<DeltaEntry(player={self.player_name}, score_delta={self.score_delta})>"



class ReportMetadata(Base):
    """Stores report system metadata (last run times, etc)"""
    __tablename__ = 'report_metadata'
    
    key = Column(String(50), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ReportMetadata(key={self.key}, value={self.value})>"



class HallOfFameRecord(Base):
    """Stores hall of fame records"""
    __tablename__ = 'hall_of_fame'
    
    id = Column(Integer, primary_key=True)
    record_type = Column(String(50), nullable=False)  # e.g. 'highest_weekly_score'
    steam_id = Column(String(50), nullable=False)
    player_name = Column(String(100))
    value = Column(Float, nullable=False)
    achieved_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<HallOfFameRecord(type={self.record_type}, player={self.player_name}, value={self.value})>"


print("Report system schema defined!")
print("\nTables:")
print("  - report_snapshots: Periodic snapshots of player stats")
print("  - snapshot_entries: Individual player stats in snapshots")
print("  - report_deltas: Calculated changes between periods")
print("  - delta_entries: Individual player deltas")
print("  - report_metadata: System metadata (last run times)")
print("  - hall_of_fame: Record achievements")



# ============================================
# TRAINING MATCHES MODELS
# ============================================

class TrainingMatch(Base):
    """Training match records"""
    __tablename__ = 'training_matches'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(20), unique=True, nullable=False, index=True)
    server_ip = Column(String(50))
    map_name = Column(String(100))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String(20), default='active')
    snapshot_start_json = Column(Text)
    snapshot_end_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    players = relationship("TrainingPlayer", back_populates="match", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TrainingMatch(id={self.match_id}, map={self.map_name})>"


class TrainingPlayer(Base):
    """Player participation in training match"""
    __tablename__ = 'training_players'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey('training_matches.id'), nullable=False, index=True)
    steam_id = Column(String(20))
    name = Column(String(100))
    kills_manual = Column(Integer)
    deaths_manual = Column(Integer)
    assists_manual = Column(Integer)
    final_kills = Column(Integer, default=0)
    final_deaths = Column(Integer, default=0)
    final_assists = Column(Integer, default=0)
    kd_ratio = Column(Float, default=0.0)
    data_source = Column(String(20))
    
    match = relationship("TrainingMatch", back_populates="players")
    
    __table_args__ = (
        UniqueConstraint('match_id', 'steam_id', name='_match_player_uc'),
    )
    
    def __repr__(self):
        return f"<TrainingPlayer(name={self.name})>"
