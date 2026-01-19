"""
Database Adapter - Async interface for database operations
Provides clean API for all database CRUD operations
"""
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import sessionmaker, scoped_session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager, asynccontextmanager
from .models import Base, Player, PlayerStats, ActivityLog, Event, EventParticipant, PassiveRequest, VoiceSession, VoiceBalance, TrainingMatch, TrainingMatchPlayer, AdminActivityLog
from exceptions import DatabaseError, DatabaseOperationError, DatabaseConnectionError
import asyncio
import logging
from typing import Optional, List
from datetime import date, datetime
import json

# Setup logger
logger = logging.getLogger(__name__)


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
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseOperationError(f"Database operation failed: {e}") from e
        except Exception as e:
            session.rollback()
            raise DatabaseError(f"Unexpected error in database transaction: {e}") from e
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
    

    async def delete_player(self, steam_id: str) -> bool:
        """Delete player by Steam ID, returns True if deleted"""
        def _delete():
            with self.session_scope() as session:
                player = session.query(Player).filter_by(steam_id=steam_id).first()
                if player:
                    session.delete(player)
                    return True
                return False
        return await asyncio.to_thread(_delete)
    
    async def get_all_players(self) -> List[Player]:
        """Get all players"""
        def _query():
            with self.session_scope() as session:
                players = session.query(Player).options(joinedload(Player.stats)).all()
                session.expunge_all()
                return players
        return await asyncio.to_thread(_query)

    async def search_players(self, query_str: str) -> List[Player]:
        """Search players by name or Steam ID"""
        def _query():
            with self.session_scope() as session:
                players = session.query(Player).options(joinedload(Player.stats)).filter(
                    (Player.name.ilike(f"%{query_str}%")) | 
                    (Player.steam_id.ilike(f"%{query_str}%"))
                ).all()
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
        
    async def get_all_recent_activity(self, days: int = 30):
        """Get all activity logs for all players for the last N days (Optimization)"""
        def _query():
            with self.session_scope() as session:
                from datetime import timedelta
                since = date.today() - timedelta(days=days)
                
                # Join with Player to get names eagerly
                results = session.query(ActivityLog, Player).\
                    join(Player, ActivityLog.player_id == Player.id).\
                    filter(ActivityLog.date >= since).\
                    all()
                
                # Detach all objects to use outside session
                session.expunge_all()
                
                return results
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
                events = session.query(Event).filter_by(
                    guild_id=guild_id,
                    active=True
                ).order_by(Event.timestamp).all()
                
                # Force load all attributes and relationships before expunge
                for event in events:
                    # Touch all lazy-loaded attributes
                    _ = event.event_id
                    _ = event.message_id
                    _ = event.channel_id
                    _ = event.creator_id
                    _ = event.title
                    _ = event.description
                    _ = event.timestamp
                    _ = event.reminder_sent
                    _ = event.active
                    
                    if event.participants:
                        for p in event.participants:
                            _ = p.user_id
                            _ = p.user_mention
                            _ = p.status
                            _ = p.reason
                            
                    session.expunge(event)
                
                return events
        return await asyncio.to_thread(_query)

    async def get_all_events(self, guild_id: int, limit: int = 50) -> List[Event]:
        """Get ALL events (active + archived) for a guild, sorted by date desc"""
        def _query():
            with self.session_scope() as session:
                events = session.query(Event).filter_by(
                    guild_id=guild_id
                ).order_by(Event.timestamp.desc()).limit(limit).all()
                
                for event in events:
                    # Touch attributes
                    _ = event.event_id
                    _ = event.message_id
                    _ = event.channel_id
                    _ = event.creator_id
                    _ = event.title
                    _ = event.description
                    _ = event.timestamp
                    _ = event.reminder_sent
                    _ = event.active
                    
                    if event.participants:
                        for p in event.participants:
                            _ = p.user_id
                            _ = p.user_mention
                            _ = p.status
                            _ = p.reason
                            
                    session.expunge(event)
                return events
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
                session.commit()
        return await asyncio.to_thread(_upsert)
    
    async def create_event(self, guild_id: int, title: str, description: str, timestamp: datetime, 
                          channel_id: int, creator_id: int) -> int:
        """Create a new event"""
        from .models import Event
        
        def _create():
            with self.session_scope() as session:
                # Get next event_id for this guild
                max_event = session.query(Event).filter_by(guild_id=guild_id).order_by(
                    Event.event_id.desc()
                ).first()
                next_event_id = (max_event.event_id + 1) if max_event else 1
                
                event = Event(
                    guild_id=guild_id,
                    event_id=next_event_id,
                    title=title,
                    description=description,
                    timestamp=timestamp,
                    channel_id=channel_id,
                    creator_id=creator_id,
                    active=True
                )
                session.add(event)
                session.commit()
                return event.id
        
        return await asyncio.to_thread(_create)
    
    async def get_event(self, event_db_id: int):
        """Get a single event by database ID"""
        def _get():
            with self.session_scope() as session:
                event = session.query(Event).filter_by(id=event_db_id).first()
                if event:
                    session.expunge(event)
                return event
        return await asyncio.to_thread(_get)
    
    async def update_event(self, event_db_id: int, title: str = None, description: str = None,
                          timestamp: datetime = None, reminder_sent: bool = None) -> bool:
        """Update event details"""
        def _update():
            with self.session_scope() as session:
                event = session.query(Event).filter_by(id=event_db_id).first()
                if event:
                    if title is not None:
                        event.title = title
                    if description is not None:
                        event.description = description
                    if timestamp is not None:
                        event.timestamp = timestamp
                    if reminder_sent is not None:
                        event.reminder_sent = reminder_sent
                    return True
                return False
        return await asyncio.to_thread(_update)
    
    async def deactivate_event(self, event_db_id: int) -> bool:
        """Mark event as inactive (archived)"""
        def _deactivate():
            with self.session_scope() as session:
                event = session.query(Event).filter_by(id=event_db_id).first()
                if event:
                    event.active = False
                    return True
                return False
        return await asyncio.to_thread(_deactivate)
    
    def get_event_participants(self, event_id):
        """Get all participants for an event"""
        try:
            with self.session_scope() as session:
                participants = session.query(EventParticipant)\
                    .filter_by(event_id=event_id)\
                    .order_by(EventParticipant.joined_at.desc())\
                    .all()
                
                # Detach from session
                session.expunge_all()
                return participants
        except Exception as e:
            logger.error(f"Error getting event participants: {e}")
            raise DatabaseOperationError(f"Failed to get event participants: {e}")
    
    async def delete_event(self, event_db_id: int) -> bool:
        """Permanently delete event"""
        def _delete():
            with self.session_scope() as session:
                event = session.query(Event).filter_by(id=event_db_id).first()
                if event:
                    session.delete(event)
                    return True
                return False
        return await asyncio.to_thread(_delete)
    
    async def update_reminder_status(self, event_db_id: int, reminder_sent: bool) -> bool:
        """Update reminder sent status"""
        def _update():
            with self.session_scope() as session:
                event = session.query(Event).filter_by(id=event_db_id).first()
                if event:
                    event.reminder_sent = reminder_sent
                    return True
                return False
        return await asyncio.to_thread(_update)
    
    async def get_event_by_message_id(self, guild_id: int, message_id: int) -> Optional[Event]:
        """Get event by Discord message ID"""
        def _query():
            with self.session_scope() as session:
                event = session.query(Event).filter_by(
                    guild_id=guild_id,
                    message_id=message_id
                ).first()
                if event:
                    # Load all attributes before expunge
                    _ = event.id
                    _ = event.event_id
                    _ = event.title
                    _ = event.description
                    _ = event.timestamp
                    _ = event.channel_id
                    _ = event.creator_id
                    _ = event.active
                    _ = event.reminder_sent
                    
                    # Load participants
                    if event.participants:
                        for p in event.participants:
                            _ = p.user_id
                            _ = p.user_mention
                            _ = p.status
                            _ = p.reason
                    
                    session.expunge(event)
                return event
        return await asyncio.to_thread(_query)
    
    # === PASSIVE REQUEST OPERATIONS ===
    
    async def add_passive_request(self, user_id: int, user_name: str, reason: str,
                                  start_date: date, end_date: date) -> int:
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
                session.flush()
                return request.id
        return await asyncio.to_thread(_add)
    
    async def get_active_passive_requests(self) -> List[PassiveRequest]:
        """Get all active passive requests (not expired)"""
        def _query():
            with self.session_scope() as session:
                today = date.today()
                requests = session.query(PassiveRequest).filter(
                    PassiveRequest.end_date >= today
                ).order_by(PassiveRequest.start_date).all()
                session.expunge_all()
                return requests
        return await asyncio.to_thread(_query)
    
    async def get_all_passive_requests(self) -> List[PassiveRequest]:
        """Get all passive requests (including expired)"""
        def _query():
            with self.session_scope() as session:
                requests = session.query(PassiveRequest).order_by(
                    PassiveRequest.created_at.desc()
                ).all()
                session.expunge_all()
                return requests
        return await asyncio.to_thread(_query)
    
    async def delete_passive_request(self, request_id: int) -> bool:
        """Delete passive request by ID"""
        def _delete():
            with self.session_scope() as session:
                request = session.query(PassiveRequest).filter_by(id=request_id).first()
                if request:
                    session.delete(request)
                    return True
                return False
        return await asyncio.to_thread(_delete)
    
    # ============================================
    # VOICE STATS OPERATIONS
    # ============================================
    
    async def start_voice_session(self, guild_id: int, user_id: int, 
                                  channel_id: int, channel_name: str) -> int:
        """Start a new voice session"""
        def _start():
            with self.session_scope() as session:
                voice_session = VoiceSession(
                    guild_id=guild_id,
                    user_id=user_id,
                    channel_id=channel_id,
                    channel_name=channel_name,
                    joined_at=datetime.now()
                )
                session.add(voice_session)
                session.flush()
                return voice_session.id
        return await asyncio.to_thread(_start)
    
    async def end_voice_session(self, session_id: int, coins_earned: int = 0) -> float:
        """End voice session, calculate duration, return duration in seconds"""
        def _end():
            with self.session_scope() as session:
                voice_session = session.query(VoiceSession).filter_by(id=session_id).first()
                if voice_session and not voice_session.left_at:
                    voice_session.left_at = datetime.now()
                    voice_session.duration_seconds = (voice_session.left_at - voice_session.joined_at).total_seconds()
                    voice_session.coins_earned = coins_earned
                    return voice_session.duration_seconds
                return 0.0
        return await asyncio.to_thread(_end)
    
    async def get_active_session(self, guild_id: int, user_id: int) -> Optional[VoiceSession]:
        """Get user's active session (left_at is NULL)"""
        def _query():
            with self.session_scope() as session:
                voice_session = session.query(VoiceSession).filter_by(
                    guild_id=guild_id,
                    user_id=user_id,
                    left_at=None
                ).first()
                if voice_session:
                    session.expunge(voice_session)
                return voice_session
        return await asyncio.to_thread(_query)
    
    async def get_voice_balance(self, guild_id: int, user_id: int) -> VoiceBalance:
        """Get or create voice balance"""
        def _get_or_create():
            with self.session_scope() as session:
                balance = session.query(VoiceBalance).filter_by(
                    guild_id=guild_id,
                    user_id=user_id
                ).first()
                
                if not balance:
                    balance = VoiceBalance(
                        guild_id=guild_id,
                        user_id=user_id,
                        balance=0,
                        pending_seconds=0.0,
                        total_time_seconds=0.0
                    )
                    session.add(balance)
                    session.flush()
                
                session.expunge(balance)
                return balance
        return await asyncio.to_thread(_get_or_create)
    
    async def update_voice_balance(self, guild_id: int, user_id: int, 
                                   coins_delta: int = 0, pending_secs_delta: float = 0,
                                   duration_delta: float = 0) -> bool:
        """Update voice balance (add/subtract coins, pending seconds, total time)"""
        def _update():
            with self.session_scope() as session:
                balance = session.query(VoiceBalance).filter_by(
                    guild_id=guild_id,
                    user_id=user_id
                ).first()
                
                if not balance:
                    balance = VoiceBalance(
                        guild_id=guild_id,
                        user_id=user_id,
                        balance=coins_delta,
                        pending_seconds=pending_secs_delta,
                        total_time_seconds=duration_delta
                    )
                    session.add(balance)
                else:
                    balance.balance += coins_delta
                    balance.pending_seconds += pending_secs_delta
                    balance.total_time_seconds += duration_delta
                    balance.last_updated = datetime.now()
                
                return True
        return await asyncio.to_thread(_update)
    
    async def transfer_voice_coins(self, guild_id: int, sender_id: int, 
                                   receiver_id: int, amount: int) -> bool:
        """Transfer coins between users"""
        def _transfer():
            with self.session_scope() as session:
                sender = session.query(VoiceBalance).filter_by(
                    guild_id=guild_id, user_id=sender_id
                ).first()
                
                if not sender or sender.balance < amount:
                    return False
                
                receiver = session.query(VoiceBalance).filter_by(
                    guild_id=guild_id, user_id=receiver_id
                ).first()
                
                if not receiver:
                    receiver = VoiceBalance(
                        guild_id=guild_id,
                        user_id=receiver_id,
                        balance=0,
                        pending_seconds=0.0,
                        total_time_seconds=0.0
                    )
                    session.add(receiver)
                    session.flush()
                
                sender.balance -= amount
                receiver.balance += amount
                return True
        return await asyncio.to_thread(_transfer)
    
    async def get_user_voice_stats(self, guild_id: int, user_id: int) -> dict:
        """Get user's voice stats (Historical Balance + Active Session)"""
        def _query():
            with self.session_scope() as session:
                # 1. Get total from VoiceBalance (Includes history + completed sessions)
                balance_record = session.query(VoiceBalance).filter_by(
                    guild_id=guild_id, user_id=user_id
                ).first()
                total_seconds = float(balance_record.total_time_seconds) if balance_record else 0.0
                
                # 2. Check for ACTIVE session (add real-time duration)
                active_session = session.query(VoiceSession).filter(
                    VoiceSession.guild_id == guild_id,
                    VoiceSession.user_id == user_id,
                    VoiceSession.left_at.is_(None)
                ).first()
                
                current_session_duration = 0.0
                if active_session:
                    current_session_duration = (datetime.now() - active_session.joined_at).total_seconds()
                    total_seconds += current_session_duration
                
                # 3. Per-channel breakdown (Completed Sessions)
                from sqlalchemy import func
                channel_stats = session.query(
                    VoiceSession.channel_id,
                    VoiceSession.channel_name,
                    func.sum(VoiceSession.duration_seconds).label('total_seconds')
                ).filter(
                    VoiceSession.guild_id == guild_id, 
                    VoiceSession.user_id == user_id,
                    VoiceSession.left_at.isnot(None) # Only completed
                ).group_by(
                    VoiceSession.channel_id, VoiceSession.channel_name
                ).all()
                
                channels = {}
                for cid, cname, secs in channel_stats:
                    if cid:
                        channels[str(cid)] = {
                            "name": cname or "Unknown",
                            "seconds": float(secs or 0.0)
                        }
                
                # Add active session to channel breakdown logic if needed
                if active_session and str(active_session.channel_id) in channels:
                    channels[str(active_session.channel_id)]["seconds"] += current_session_duration
                elif active_session:
                    channels[str(active_session.channel_id)] = {
                        "name": active_session.channel_name or "Unknown",
                        "seconds": current_session_duration
                    }
                
                return {
                    "total_seconds": total_seconds,
                    "channels": channels
                }
        return await asyncio.to_thread(_query)
    
    async def get_voice_leaderboard(self, guild_id: int, limit: int = 10) -> List[dict]:
        """Get top users by total voice time (Balance + Active Sessions)"""
        def _query():
            with self.session_scope() as session:
                # 1. Get all balances
                balances = session.query(
                    VoiceBalance.user_id,
                    VoiceBalance.total_time_seconds
                ).filter_by(guild_id=guild_id).all()
                
                # Use a dict to merge stats
                stats_map = {uid: float(secs or 0.0) for uid, secs in balances}
                
                # 2. Get active sessions to add real-time duration
                active_sessions = session.query(VoiceSession).filter(
                    VoiceSession.guild_id == guild_id,
                    VoiceSession.left_at.is_(None)
                ).all()
                
                now = datetime.now()
                for s in active_sessions:
                    if s.joined_at:
                        duration = (now - s.joined_at).total_seconds()
                        stats_map[s.user_id] = stats_map.get(s.user_id, 0.0) + duration
                
                # 3. Sort and limit
                sorted_stats = sorted(stats_map.items(), key=lambda x: x[1], reverse=True)[:limit]
                
                return [
                    {"user_id": int(uid), "total_seconds": secs}
                    for uid, secs in sorted_stats
                ]
        return await asyncio.to_thread(_query)
    
    async def get_user_voice_history(self, guild_id: int, user_id: int, days: int = 7) -> List[VoiceSession]:
        """Get recent session history"""
        def _query():
            with self.session_scope() as session:
                from_date = datetime.now() - timedelta(days=days)
                sessions = session.query(VoiceSession).filter(
                    VoiceSession.guild_id == guild_id,
                    VoiceSession.user_id == user_id,
                    VoiceSession.joined_at >= from_date
                ).order_by(VoiceSession.joined_at.desc()).all()
                
                session.expunge_all()
                return sessions
        return await asyncio.to_thread(_query)
    
    # ============================================
    # REPORT SYSTEM METHODS
    # ============================================
    
    async def create_snapshot(self, period_type: str):
        """Create a snapshot of current player stats"""
        from .models import ReportSnapshot, SnapshotEntry, Player, PlayerStats
        
        def _create():
            with self.session_scope() as session:
                # Create snapshot
                snapshot = ReportSnapshot(period_type=period_type)
                session.add(snapshot)
                session.flush()  # Get snapshot ID
                
                # Get all players with stats
                players = session.query(Player).join(PlayerStats).all()
                
                for player in players:
                    if player.stats:
                        entry = SnapshotEntry(
                            snapshot_id=snapshot.id,
                            steam_id=player.steam_id,
                            score=player.stats.total_score or 0,
                            kills=player.stats.total_kills or 0,
                            deaths=player.stats.total_deaths or 0,
                            revives=player.stats.total_revives or 0,
                            wounds=0,  # Add if needed
                            kd_ratio=player.stats.total_kd_ratio or 0.0
                        )
                        session.add(entry)
                
                return snapshot.id
        
        return await asyncio.to_thread(_create)
    
    async def get_latest_snapshot(self, period_type: str):
        """Get the most recent snapshot for a period"""
        from .models import ReportSnapshot
        
        def _get():
            with self.session_scope() as session:
                snapshot = session.query(ReportSnapshot).filter_by(period_type=period_type).order_by(ReportSnapshot.timestamp.desc()).first()
                
                if snapshot:
                    return {
                        'id': snapshot.id,
                        'timestamp': snapshot.timestamp,
                        'entries': [
                            {
                                'steam_id': e.steam_id,
                                'score': e.score,
                                'kills': e.kills,
                                'deaths': e.deaths,
                                'revives': e.revives,
                                'kd_ratio': e.kd_ratio
                            }
                            for e in snapshot.entries
                        ]
                    }
                return None
        
        return await asyncio.to_thread(_get)
    
    async def calculate_deltas(self, start_snapshot_id: int):
        """Calculate deltas from snapshot to current stats"""
        from .models import SnapshotEntry, Player, PlayerStats
        
        def _calculate():
            with self.session_scope() as session:
                # Get snapshot entries
                start_entries = {e.steam_id: e for e in session.query(SnapshotEntry).filter_by(snapshot_id=start_snapshot_id).all()}
                
                # Get current stats
                players = session.query(Player).join(PlayerStats).all()
                
                deltas = []
                for player in players:
                    if not player.stats:
                        continue
                    
                    start_entry = start_entries.get(player.steam_id)
                    current_score = player.stats.total_score or 0
                    current_kills = player.stats.total_kills or 0
                    current_deaths = player.stats.total_deaths or 0
                    current_revives = player.stats.total_revives or 0
                    
                    if start_entry:
                        delta = {
                            'steam_id': player.steam_id,
                            'player_name': player.name,
                            'score_delta': current_score - start_entry.score,
                            'kills_delta': current_kills - start_entry.kills,
                            'deaths_delta': current_deaths - start_entry.deaths,
                            'revives_delta': current_revives - start_entry.revives,
                            'wounds_delta': 0
                        }
                    else:
                        delta = {
                            'steam_id': player.steam_id,
                            'player_name': player.name,
                            'score_delta': current_score,
                            'kills_delta': current_kills,
                            'deaths_delta': current_deaths,
                            'revives_delta': current_revives,
                            'wounds_delta': 0
                        }
                    
                    deltas.append(delta)
                
                deltas.sort(key=lambda x: x['score_delta'], reverse=True)
                for rank, d in enumerate(deltas, 1):
                    d['rank'] = rank
                
                return deltas
        
        return await asyncio.to_thread(_calculate)
    
    async def save_report_delta(self, period_type: str, start_snapshot_id: int, delta_entries: list):
        """Save calculated deltas"""
        from .models import ReportDelta, DeltaEntry
        
        def _save():
            with self.session_scope() as session:
                delta_record = ReportDelta(period_type=period_type, start_snapshot_id=start_snapshot_id)
                session.add(delta_record)
                session.flush()
                
                for entry_data in delta_entries:
                    entry = DeltaEntry(
                        delta_id=delta_record.id,
                        steam_id=entry_data['steam_id'],
                        player_name=entry_data['player_name'],
                        score_delta=entry_data['score_delta'],
                        kills_delta=entry_data['kills_delta'],
                        deaths_delta=entry_data['deaths_delta'],
                        revives_delta=entry_data['revives_delta'],
                        rank=entry_data.get('rank')
                    )
                    session.add(entry)
                
                return delta_record.id
        
        return await asyncio.to_thread(_save)
    
    async def get_report_history(self, period_type: str, limit: int = 10):
        """Get recent deltas"""
        from .models import ReportDelta
        
        def _get():
            with self.session_scope() as session:
                deltas = session.query(ReportDelta).filter_by(period_type=period_type).order_by(ReportDelta.timestamp.desc()).limit(limit).all()
                
                return [{
                    'id': d.id,
                    'timestamp': d.timestamp,
                    'entries': [{'steam_id': e.steam_id, 'player_name': e.player_name, 'score_delta': e.score_delta, 'rank': e.rank} for e in d.entries]
                } for d in deltas]
        
        return await asyncio.to_thread(_get)
    
    async def set_report_metadata(self, key: str, value: str):
        """Set metadata"""
        from .models import ReportMetadata
        
        def _set():
            with self.session_scope() as session:
                meta = session.query(ReportMetadata).filter_by(key=key).first()
                if meta:
                    meta.value = value
                else:
                    session.add(ReportMetadata(key=key, value=value))
        
        await asyncio.to_thread(_set)
    
    async def get_report_metadata(self, key: str):
        """Get metadata"""
        from .models import ReportMetadata
        
        def _get():
            with self.session_scope() as session:
                meta = session.query(ReportMetadata).filter_by(key=key).first()
                return meta.value if meta else None
        
        return await asyncio.to_thread(_get)


    
    # ============================================
    # TRAINING MATCH METHODS
    # ============================================
    
    async def create_training_match(self, match_id: str, server_ip: str, map_name: str, start_time):
        """Create new training match"""
        def _create():
            from .models import TrainingMatch
            with self.session_scope() as session:
                match = TrainingMatch(
                    match_id=match_id,
                    server_ip=server_ip,
                    map_name=map_name,
                    start_time=start_time,
                    status='active'
                )
                session.add(match)
                session.flush()
                return match.id
        return await asyncio.to_thread(_create)
    
    async def get_training_match(self, match_id: str):
        """Get training match by match_id"""
        def _get():
            from .models import TrainingMatch
            with self.session_scope() as session:
                match = session.query(TrainingMatch).filter_by(match_id=match_id).first()
                if match:
                    return {
                        'id': match.id,
                        'match_id': match.match_id,
                        'server_ip': match.server_ip,
                        'map_name': match.map_name,
                        'start_time': match.start_time,
                        'end_time': match.end_time,
                        'status': match.status,
                        'snapshot_start_json': match.snapshot_start_json,
                        'snapshot_end_json': match.snapshot_end_json
                    }
                return None
        return await asyncio.to_thread(_get)
    
    async def update_training_match(self, match_id: str, status: str = None, end_time = None, 
                                   snapshot_start: str = None, snapshot_end: str = None):
        """Update training match"""
        def _update():
            from .models import TrainingMatch
            with self.session_scope() as session:
                match = session.query(TrainingMatch).filter_by(match_id=match_id).first()
                if match:
                    if status: match.status = status
                    if end_time: match.end_time = end_time
                    if snapshot_start: match.snapshot_start_json = snapshot_start
                    if snapshot_end: match.snapshot_end_json = snapshot_end
                    return True
                return False
        return await asyncio.to_thread(_update)
    
    async def add_training_player(self, match_id: str, player_data: dict):
        """Add or update player KDA for training match"""
        def _upsert():
            from .models import TrainingMatch, TrainingPlayer
            with self.session_scope() as session:
                # Get match
                match = session.query(TrainingMatch).filter_by(match_id=match_id).first()
                if not match:
                    return False
                
                # Check if player exists
                player = session.query(TrainingPlayer).filter_by(
                    match_id=match.id,
                    steam_id=player_data.get('steam_id')
                ).first()
                
                if player:
                    # Update
                    for key, value in player_data.items():
                        if hasattr(player, key):
                            setattr(player, key, value)
                else:
                    # Create
                    player = TrainingPlayer(
                        match_id=match.id,
                        steam_id=player_data.get('steam_id'),
                        name=player_data.get('name'),
                        kills_manual=player_data.get('kills_manual'),
                        deaths_manual=player_data.get('deaths_manual'),
                        assists_manual=player_data.get('assists_manual'),
                        final_kills=player_data.get('final_kills', 0),
                        final_deaths=player_data.get('final_deaths', 0),
                        final_assists=player_data.get('final_assists', 0),
                        kd_ratio=player_data.get('kd_ratio', 0.0),
                        data_source=player_data.get('data_source', 'manual')
                    )
                    session.add(player)
                return True
        return await asyncio.to_thread(_upsert)
    

    # ============================================
    # TRAINING SYSTEM METHODS
    # ============================================
    
    async def create_training_match(self, match_id: int, server_ip: str, map_name: str, start_time: datetime = None) -> int:
        """Create a new training match record"""
        def _create():
            with self.session_scope() as session:
                if not start_time:
                    s_time = datetime.now()
                else:
                    s_time = start_time
                
                # Check consistency if needed, but here we just blindly insert
                # Note: 'id' is autoincrement DB ID, we might store 'match_id' as metadata or separate column if needed.
                # The model has 'id' as PK. Creating a separate logical match_id column might be confusing if not aligned.
                # However, the migration script suggests 'match_id' from json is just an integer sequence.
                # We can use the DB's ID as the match_id if we migrate sequentially.
                # But migration script passes 'match_id'.
                # Let's check models.py again. I defined 'id' as Integer PK.
                # So I should probably insert with that ID if I want to preserve JSON IDs, OR let DB handle it.
                # For migration, we want to preserve IDs.
                
                existing = session.query(TrainingMatch).filter_by(id=match_id).first()
                if existing:
                    return existing.id
                
                match = TrainingMatch(
                    id=match_id, # Force ID from JSON to maintain history
                    server_ip=server_ip,
                    map_name=map_name,
                    start_time=s_time,
                    status='active'
                )
                session.add(match)
                session.flush()
                return match.id
        return await asyncio.to_thread(_create)

    async def update_training_match(self, match_id: int, status: str = None, end_time: datetime = None, 
                                  snapshot_start: str = None, snapshot_end: str = None) -> bool:
        """Update training match details (status, snapshots)"""
        def _update():
            with self.session_scope() as session:
                match = session.query(TrainingMatch).filter_by(id=match_id).first()
                if not match:
                    return False
                
                if status: match.status = status
                if end_time: match.end_time = end_time
                if snapshot_start: match.snapshot_start_json = snapshot_start
                if snapshot_end: match.snapshot_end_json = snapshot_end
                
                return True
        return await asyncio.to_thread(_update)

    async def add_training_player(self, match_id: int, player_data: dict) -> bool:
        """Add or update player stats for a match"""
        def _upsert():
            with self.session_scope() as session:
                # Expects player_data to contain 'steam_id'
                steam_id = player_data.get('steam_id')
                if not steam_id: return False
                
                # Ensure Player exists in main table first (Migration does this usually, but safe to check)
                # But migration script might run before player sync. 
                # Ideally, we should ensure player exists.
                # For now, simplistic approach:
                
                # Check existing match player
                mpConnection = session.query(TrainingMatchPlayer).filter_by(
                    match_id=match_id,
                    steam_id=steam_id
                ).first()
                
                if not mpConnection:
                    mpConnection = TrainingMatchPlayer(
                        match_id=match_id,
                        steam_id=steam_id
                    )
                    session.add(mpConnection)
                
                # Update fields
                if 'kills_manual' in player_data: mpConnection.manual_kills = player_data['kills_manual']
                if 'deaths_manual' in player_data: mpConnection.manual_deaths = player_data['deaths_manual']
                if 'assists_manual' in player_data: mpConnection.manual_assists = player_data['assists_manual']
                
                if 'final_kills' in player_data: mpConnection.final_kills = player_data['final_kills']
                if 'final_deaths' in player_data: mpConnection.final_deaths = player_data['final_deaths']
                if 'final_assists' in player_data: mpConnection.final_assists = player_data['final_assists']
                if 'kd_ratio' in player_data: mpConnection.kd_ratio = player_data['kd_ratio']
                if 'data_source' in player_data: mpConnection.data_source = player_data['data_source']
                
                return True
        return await asyncio.to_thread(_upsert)

    async def get_active_training_match(self):
        """Get the currently active training match"""
        def _get():
            with self.session_scope() as session:
                return session.query(TrainingMatch).filter_by(status='active').order_by(TrainingMatch.start_time.desc()).first()
        return await asyncio.to_thread(_get)

    async def get_training_matches(self, limit: int = 10, status: str = None):
        """Get recent training matches with full details"""
        def _get():
            with self.session_scope() as session:
                query = session.query(TrainingMatch)
                if status:
                    query = query.filter_by(status=status)
                
                # Order by ID desc (newest first)
                query = query.order_by(TrainingMatch.id.desc()).limit(limit)
                
                matches = []
                for match in query.all():
                    # Get players
                    players = match.players # Relationship
                    
                    matches.append({
                        'match_id': match.id,
                        'server_ip': match.server_ip,
                        'map_name': match.map_name,
                        'start_time': match.start_time.isoformat() if match.start_time else None,
                        'end_time': match.end_time.isoformat() if match.end_time else None,
                        'status': match.status,
                        'players': [{
                            'steam_id': p.steam_id,
                            'name': p.player.name if p.player else "Unknown", # Resolve via relationship
                            'final_kills': p.final_kills,
                            'final_deaths': p.final_deaths,
                            'final_assists': p.final_assists,
                            'kd_ratio': p.kd_ratio,
                            'data_source': p.data_source
                        } for p in players]
                    })
                return matches
        return await asyncio.to_thread(_get)

    # ============================================
    # HALL OF FAME OPERATIONS
    # ============================================
    
    async def get_hall_of_fame_records(self):
        """Get all Hall of Fame records"""
        from .models import HallOfFameRecord
        
        def _query():
            with self.session_scope() as session:
                records = session.query(HallOfFameRecord).order_by(
                    HallOfFameRecord.achieved_at.desc()
                ).all()
                session.expunge_all()
                return records
        
        return await asyncio.to_thread(_query)
    
    # ============================================
    # WEB-BOT ACTION QUEUE OPERATIONS
    # ============================================
    
    async def queue_bot_action(self, action_type: str, data: dict):
        """Queue an action for the bot to process"""
        from .models import WebBotAction
        import json
        
        def _queue():
            with self.session_scope() as session:
                action = WebBotAction(
                    action_type=action_type,
                    data=json.dumps(data)
                )
                session.add(action)
                session.commit()
                return action.id
        
        return await asyncio.to_thread(_queue)
    
    async def get_pending_web_actions(self, limit: int = 50):
        """Get pending actions for bot to process"""
        from .models import WebBotAction
        
        def _query():
            with self.session_scope() as session:
                actions = session.query(WebBotAction).filter(
                    WebBotAction.status == 'pending'
                ).order_by(
                    WebBotAction.created_at.asc()
                ).limit(limit).all()
                session.expunge_all()
                return actions
        
        return await asyncio.to_thread(_query)
    
    async def mark_action_processed(self, action_id: int):
        """Mark an action as successfully processed"""
        from .models import WebBotAction
        from datetime import datetime # Added import for datetime
        
        def _update():
            with self.session_scope() as session:
                action = session.query(WebBotAction).filter_by(id=action_id).first()
                if action:
                    action.status = 'processed'
                    action.processed_at = datetime.utcnow()
                    session.commit()
        
        return await asyncio.to_thread(_update)
    
    async def mark_action_failed(self, action_id: int, error_message: str):
        """Mark an action as failed"""
        from .models import WebBotAction
        from datetime import datetime # Added import for datetime
        
        def _update():
            with self.session_scope() as session:
                action = session.query(WebBotAction).filter_by(id=action_id).first()
                if action:
                    action.status = 'failed'
                    action.error_message = error_message
                    action.retry_count += 1
                    action.processed_at = datetime.utcnow()
                    session.commit()
        
        return await asyncio.to_thread(_update)
    # ============================================
    # ADMIN ACTIVITY LOG METHODS  
    # ============================================
    
    async def log_activity(self, action_type: str, target: str, details: str = None, admin_user: str = 'web_admin'):
        """Log an admin activity"""
        from .models import AdminActivityLog
        
        def _log():
            with self.session_scope() as session:
                log = AdminActivityLog(
                    action_type=action_type,
                    admin_user=admin_user,
                    target=target,
                    details=details
                )
                session.add(log)
                session.commit()
        
        return await asyncio.to_thread(_log)
    
    async def get_recent_activities(self, limit: int = 20):
        """Get recent admin activities"""
        from .models import AdminActivityLog
        
        def _query():
            with self.session_scope() as session:
                activities = session.query(AdminActivityLog).order_by(
                    AdminActivityLog.timestamp.desc()
                ).limit(limit).all()
                session.expunge_all()
                return activities
        
        return await asyncio.to_thread(_query)

