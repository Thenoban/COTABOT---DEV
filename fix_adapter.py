"""
Fix DatabaseAdapter - Add expunge to all query methods to prevent DetachedInstanceError
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\database\adapter.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: get_player_by_steam_id
old1 = """    async def get_player_by_steam_id(self, steam_id: str) -> Optional[Player]:
        \"\"\"Get player by Steam ID\"\"\"
        def _query():
            with self.session_scope() as session:
                return session.query(Player).filter_by(steam_id=steam_id).first()
        return await asyncio.to_thread(_query)"""

new1 = """    async def get_player_by_steam_id(self, steam_id: str) -> Optional[Player]:
        \"\"\"Get player by Steam ID\"\"\"
        def _query():
            with self.session_scope() as session:
                player = session.query(Player).filter_by(steam_id=steam_id).first()
                if player:
                    session.expunge(player)  # Detach from session
                return player
        return await asyncio.to_thread(_query)"""

# Fix 2: get_player_by_discord_id
old2 = """    async def get_player_by_discord_id(self, discord_id: int) -> Optional[Player]:
        \"\"\"Get player by Discord ID\"\"\"
        def _query():
            with self.session_scope() as session:
                return session.query(Player).filter_by(discord_id=discord_id).first()
        return await asyncio.to_thread(_query)"""

new2 = """    async def get_player_by_discord_id(self, discord_id: int) -> Optional[Player]:
        \"\"\"Get player by Discord ID\"\"\"
        def _query():
            with self.session_scope() as session:
                player = session.query(Player).filter_by(discord_id=discord_id).first()
                if player:
                    session.expunge(player)
                return player
        return await asyncio.to_thread(_query)"""

# Fix 3: get_all_players
old3 = """    async def get_all_players(self) -> List[Player]:
        \"\"\"Get all players\"\"\"
        def _query():
            with self.session_scope() as session:
                return session.query(Player).all()
        return await asyncio.to_thread(_query)"""

new3 = """    async def get_all_players(self) -> List[Player]:
        \"\"\"Get all players\"\"\"
        def _query():
            with self.session_scope() as session:
                players = session.query(Player).all()
                session.expunge_all()
                return players
        return await asyncio.to_thread(_query)"""

# Fix 4: get_player_stats
old4 = """    async def get_player_stats(self, player_id: int) -> Optional[PlayerStats]:
        \"\"\"Get player statistics\"\"\"
        def _query():
            with self.session_scope() as session:
                return session.query(PlayerStats).filter_by(player_id=player_id).first()
        return await asyncio.to_thread(_query)"""

new4 = """    async def get_player_stats(self, player_id: int) -> Optional[PlayerStats]:
        \"\"\"Get player statistics\"\"\"
        def _query():
            with self.session_scope() as session:
                stats = session.query(PlayerStats).filter_by(player_id=player_id).first()
                if stats:
                    session.expunge(stats)
                return stats
        return await asyncio.to_thread(_query)"""

# Fix 5: get_player_activity
old5 = """    async def get_player_activity(self, player_id: int, days: int = 30) -> List[ActivityLog]:
        \"\"\"Get player activity for the last N days\"\"\"
        def _query():
            with self.session_scope() as session:
                from datetime import timedelta
                since = date.today() - timedelta(days=days)
                return session.query(ActivityLog).filter(
                    ActivityLog.player_id == player_id,
                    ActivityLog.date >= since
                ).order_by(ActivityLog.date.desc()).all()
        return await asyncio.to_thread(_query)"""

new5 = """    async def get_player_activity(self, player_id: int, days: int = 30) -> List[ActivityLog]:
        \"\"\"Get player activity for the last N days\"\"\"
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
        return await asyncio.to_thread(_query)"""

# Apply fixes
content = content.replace(old1, new1)
content = content.replace(old2, new2)
content = content.replace(old3, new3)
content = content.replace(old4, new4)
content = content.replace(old5, new5)

# Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed 5 methods in DatabaseAdapter")
print("Now restart Docker: sudo docker compose restart")
