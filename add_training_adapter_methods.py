"""
Add Training Match CRUD methods to DatabaseAdapter
"""

# Read current adapter.py
with open('database/adapter.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already added
if 'create_training_match' in content:
    print("Training Match methods already exist!")
else:
    # Training match methods to append
    training_methods = """
    
    # ============================================
    # TRAINING MATCH METHODS
    # ============================================
    
    async def create_training_match(self, match_id: str, server_ip: str, map_name: str, start_time):
        \"\"\"Create new training match\"\"\"
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
        \"\"\"Get training match by match_id\"\"\"
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
        \"\"\"Update training match\"\"\"
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
        \"\"\"Add or update player KDA for training match\"\"\"
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
    
    async def get_training_matches(self, limit: int = 10, status: str = None):
        \"\"\"Get recent training matches\"\"\"
        def _get():
            from .models import TrainingMatch, TrainingPlayer
            with self.session_scope() as session:
                query = session.query(TrainingMatch)
                if status:
                    query = query.filter_by(status=status)
                query = query.order_by(TrainingMatch.start_time.desc()).limit(limit)
                
                matches = []
                for match in query.all():
                    # Get players for this match
                    players = session.query(TrainingPlayer).filter_by(match_id=match.id).all()
                    
                    matches.append({
                        'match_id': match.match_id,
                        'server_ip': match.server_ip,
                        'map_name': match.map_name,
                        'start_time': match.start_time.isoformat() if match.start_time else None,
                        'end_time': match.end_time.isoformat() if match.end_time else None,
                        'status': match.status,
                        'players': [{
                            'steam_id': p.steam_id,
                            'name': p.name,
                            'final_kills': p.final_kills,
                            'final_deaths': p.final_deaths,
                            'final_assists': p.final_assists,
                            'kd_ratio': p.kd_ratio,
                            'data_source': p.data_source
                        } for p in players]
                    })
                return matches
        return await asyncio.to_thread(_get)
"""
    
    # Find the last method and append before the final line
    # Append before the last line (if there's a closing bracket or similar)
    with open('database/adapter.py', 'w', encoding='utf-8') as f:
        f.write(content + training_methods)
    
    print("SUCCESS: Training Match methods added to DatabaseAdapter")

print("\nVerifying import...")
from database.adapter import DatabaseAdapter
print("SUCCESS: DatabaseAdapter imports correctly!")
