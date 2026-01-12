"""
Migrate PlayerSearchModal to hybrid mode
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find PlayerSearchModal.on_submit and add hybrid mode at the beginning
# After loading JSON data, add SQLite check

old_search_code = '''        # Load players from JSON
        db_file = "squad_db.json"
        players = []
        if os.path.exists(db_file):
            try:
                def _read():
                    with open(db_file, "r", encoding="utf-8") as f: return json.load(f)
                data = await asyncio.to_thread(_read)
                players = data.get("players", [])
            except:
                pass'''

new_search_code = '''        # HYBRID MODE: Load players from SQLite or JSON
        cog = self.bot.get_cog("SquadPlayers")
        players = []
        
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            # SQLite mode - search in database
            try:
                all_players = await cog.db.get_all_players()
                # Convert to dict format for compatibility
                players = [{
                    "steam_id": p.steam_id,
                    "name": p.name,
                    "discord_id": p.discord_id,
                    "stats": {},
                    "season_stats": {}
                } for p in all_players]
            except Exception as e:
                import logging
                logging.getLogger("SquadPlayers").error(f"DB search error: {e}, fallback to JSON")
        
        # JSON mode or fallback
        if not players:
            db_file = "squad_db.json"
            if os.path.exists(db_file):
                try:
                    def _read():
                        with open(db_file, "r", encoding="utf-8") as f: return json.load(f)
                    data = await asyncio.to_thread(_read)
                    players = data.get("players", [])
                except:
                    pass'''

if old_search_code in content:
    content = content.replace(old_search_code, new_search_code)
    print("SUCCESS: PlayerSearchModal migrated to hybrid mode")
else:
    print("ERROR: Search code not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - Search now uses database")
