"""
Database Adapter - Async interface for database operations
Provides clean API for all database CRUD operations
"""
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager, asynccontextmanager
from .models import Base, Player, PlayerStats, ActivityLog, Event, EventParticipant, PassiveRequest
import asyncio
from typing import Optional, List
from datetime import date, datetime
import json


class DatabaseAdapter:
    """
    Main database adapter providing async interface to SQLite
    """
    
    def __init__(self, db_url='sqlite:///cotabot.db'):
        self.engine = create_engine(db_url, echo=False)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
    def init_db(self):
        """Create all tables if they don't exist"""
        Base.metadata.create_all(self.engine)
        print("Database tables created")
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope for synchronous operations"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # === PLAYER OPERATIONS ===
    
    async def get_player_by_steam_id(self, steam_id: str) -> Optional[Player]:
        """Get player by Steam ID"""
        def _query():
            with self.session_scope() as session:
                player = session.query(Player).filter_by(steam_id=steam_id).first()
                if player:
                    session.expunge(player)  # Detach from session
                return player
        return await asyncio.to_thread(_query)
    
    async def get_player_by_discord_id(self, discord_id: int) -> Optional[Player]:
        """Get player by Discord ID"""
        def _query():
            with self.session_scope() as session:
                player = session.query(Player).filter_by(discord_id=discord_id).first()
                if player:
                    session.expunge(player)
                return player
        return await asyncio.to_thread(_query)
    
    async def add_player(self, steam_id: str, name: str, discord_id: Optional[int] = None) -> int:
        """Add new player, returns player ID"""
        def _add():
            with self.session_scope() as session:
                player = Player(steam_id=steam_id, name=name, discord_id=discord_id)
                session.add(player)
                session.flush()
                return player.id
        return await asyncio.to_thread(_add)
    
    async def update_player(self, steam_id: str, name: Optional[str] = None, discord_id: Optional[int] = None):
        """Update player information"""
        def _update():
            with self.session_scope() as session:
                player = session.query(Player).filter_by(steam_id=steam_id).first()
                if player:
                    if name:
                        player.name = name
                    if discord_id is not None:
                        player.discord_id = discord_id
                    player.updated_at = datetime.utcnow()
                    return True
                return False
        return await asyncio.to_thread(_update)
    
    async def get_all_players(self) -> List[Player]:
        """Get all players"""
        def _query():
            with self.session_scope() as session:
                players = session.query(Player).all()
                session.expunge_all()
                return players
        return await asyncio.to_thread(_query)
    
    # === PLAYER STATS OPERATIONS ===
    
    async def add_or_update_stats(self, player_id: int, all_time_data: dict, season_data: dict):
        """Add or update player statistics"""
        def _upsert():
            with self.session_scope() as session:
                stats = session.query(PlayerStats).filter_by(player_id=player_id).first()
                
                if not stats:
                    stats = PlayerStats(player_id=player_id)
                    session.add(stats)
                
                # Update all-time stats
                stats.total_score = all_time_data.get('totalScore', 0)
                stats.total_kills = all_time_data.get('totalKills', 0)
                stats.total_deaths = all_time_data.get('totalDeaths', 0)
                stats.total_revives = all_time_data.get('totalRevives', 0)
                stats.total_kd_ratio = all_time_data.get('totalKdRatio', 0.0)
                stats.all_time_json = json.dumps(all_time_data)
                
                # Update season stats
                if season_data:
                    stats.season_score = season_data.get('seasonScore', 0)
                    stats.season_kills = season_data.get('seasonKills', 0)
                    stats.season_deaths = season_data.get('seasonDeaths', 0)
                    stats.season_revives = season_data.get('seasonRevives', 0)
                    stats.season_kd_ratio = season_data.get('seasonKdRatio', 0.0)
                    stats.season_json = json.dumps(season_data)
                
                stats.updated_at = datetime.utcnow()
        
        return await asyncio.to_thread(_upsert)
    
    async def get_player_stats(self, player_id: int) -> Optional[PlayerStats]:
        """Get player statistics"""
        def _query():
            with self.session_scope() as session:
                stats = session.query(PlayerStats).filter_by(player_id=player_id).first()
                if stats:
                    session.expunge(stats)
                return stats
        return await asyncio.to_thread(_query)
    
    # === ACTIVITY LOG OPERATIONS ===
    
    async def add_or_update_activity(self, player_id: int, activity_date: date, minutes: int, last_seen: datetime):
        """Add or update activity log for a player on a specific date"""
        def _upsert():
            with self.session_scope() as session:
                log = session.query(ActivityLog).filter_by(
                    player_id=player_id, 
                    date=activity_date
                ).first()
                
                if log:
                    log.minutes += minutes
                    log.last_seen = last_seen
                else:
                    log = ActivityLog(
                        player_id=player_id,
                        date=activity_date,
                        minutes=minutes,
                        last_seen=last_seen
                    )
                    session.add(log)
        
        return await asyncio.to_thread(_upsert)
    
    async def get_player_activity(self, player_id: int, days: int = 30) -> List[ActivityLog]:
        """Get player activity for the last N days"""
        def _query():
            with self.session_scope() as session:
                from datetime import timedelta
                since = date.today() - timedelta(days=days)
                logs = session.query(ActivityLog).filter(
                    ActivityLog.player_id == player_id,
                    ActivityLog.date >= since
                ).order_by(ActivityLog.date.desc()).all()
                session.expunge_all()
                return logs
        return await asyncio.to_thread(_query)
    
    # === EVENT OPERATIONS ===
    
    async def add_event(self, guild_id: int, event_id: int, title: str, description: str,
                       timestamp: datetime, channel_id: int, creator_id: int) -> int:
        """Add new event"""
        def _add():
            with self.session_scope() as session:
                event = Event(
                    guild_id=guild_id,
                    event_id=event_id,
                    title=title,
                    description=description,
                    timestamp=timestamp,
                    channel_id=channel_id,
                    creator_id=creator_id
                )
                session.add(event)
                session.flush()
                return event.id
        return await asyncio.to_thread(_add)
    
    async def get_active_events(self, guild_id: int) -> List[Event]:
        """Get all active events for a guild"""
        def _query():
            with self.session_scope() as session:
                return session.query(Event).filter_by(
                    guild_id=guild_id,
                    active=True
                ).order_by(Event.timestamp).all()
        return await asyncio.to_thread(_query)
    
    async def update_event_message(self, event_db_id: int, message_id: int):
        """Update event message ID"""
        def _update():
            with self.session_scope() as session:
                event = session.query(Event).filter_by(id=event_db_id).first()
                if event:
                    event.message_id = message_id
        return await asyncio.to_thread(_update)
    
    async def add_event_participant(self, event_db_id: int, user_id: int, 
                                    user_mention: str, status: str, reason: str = None):
        """Add or update event participant"""
        def _upsert():
            with self.session_scope() as session:
                participant = session.query(EventParticipant).filter_by(
                    event_id=event_db_id,
                    user_id=user_id
                ).first()
                
                if participant:
                    participant.status = status
                    participant.reason = reason
                else:
                    participant = EventParticipant(
                        event_id=event_db_id,
                        user_id=user_id,
                        user_mention=user_mention,
                        status=status,
                        reason=reason
                    )
                    session.add(participant)
        return await asyncio.to_thread(_upsert)
    
    # === PASSIVE REQUEST OPERATIONS ===
    
    async def add_passive_request(self, user_id: int, user_name: str, reason: str,
                                  start_date: date, end_date: date):
        """Add passive/away request"""
        def _add():
            with self.session_scope() as session:
                request = PassiveRequest(
                    user_id=user_id,
                    user_name=user_name,
                    reason=reason,
                    start_date=start_date,
                    end_date=end_date
                )
                session.add(request)
        return await asyncio.to_thread(_add)
    
    async def get_active_passive_requests(self) -> List[PassiveRequest]:
        """Get all active passive requests (not expired)"""
        def _query():
            with self.session_scope() as session:
                today = date.today()
                return session.query(PassiveRequest).filter(
                    PassiveRequest.end_date >= today
                ).all()
        return await asyncio.to_thread(_query)
