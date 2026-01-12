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

