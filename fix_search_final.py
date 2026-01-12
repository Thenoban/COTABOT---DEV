"""
Fix PlayerSearchModal - correct code pattern
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Exact code from view_code_item
old_search = '''    async def on_submit(self, interaction: discord.Interaction):
        query = self.name_query.value.lower()
        
        matches = []
        if os.path.exists("squad_db.json"):
            try:
                def _read_search():
                    with open("squad_db.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return [p for p in data.get("players", []) if query in p["name"].lower()]
                matches = await asyncio.to_thread(_read_search)
            except: pass'''

new_search = '''    async def on_submit(self, interaction: discord.Interaction):
        query = self.name_query.value.lower()
        
        # HYBRID MODE: Search in database or JSON
        cog = self.bot.get_cog("SquadPlayers")
        matches = []
        
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            # SQLite mode
            try:
                all_players = await cog.db.get_all_players()
                matches = [{
                    "steam_id": p.steam_id,
                    "name": p.name,
                    "discord_id": p.discord_id
                } for p in all_players if query in p.name.lower()]
            except Exception as e:
                import logging
                logging.getLogger("SquadPlayers").error(f"DB search error: {e}")
        
        # JSON fallback
        if not matches and os.path.exists("squad_db.json"):
            try:
                def _read_search():
                    with open("squad_db.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return [p for p in data.get("players", []) if query in p["name"].lower()]
                matches = await asyncio.to_thread(_read_search)
            except: pass'''

if old_search in content:
    content = content.replace(old_search, new_search)
    print("SUCCESS: PlayerSearchModal migrated")
else:
    print("ERROR: Code not found, trying alternative")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
