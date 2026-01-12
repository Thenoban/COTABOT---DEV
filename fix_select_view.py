"""
Fix PlayerSelectView callback - it's re-reading JSON to get player data
Need to use the matches data that was already fetched
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The issue is in player_select_callback - it re-reads from JSON
# We need to use self.players (matches) directly instead

old_callback = '''    async def player_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        s_id = select.values[0]
        
        # Re-read from JSON to get full data
        player_data = None
        if os.path.exists("squad_db.json"):
            try:
                def _find():
                    with open("squad_db.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for p in data.get("players", []):
                            if p["steam_id"] == s_id:
                                return p
                        return None
                player_data = await asyncio.to_thread(_find)
            except: pass'''

new_callback = '''    async def player_select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        s_id = select.values[0]
        
        # Get player data from matches (already fetched in search)
        player_data = None
        for p in self.players:
            if p["steam_id"] == s_id:
                player_data = p
                break'''

if old_callback in content:
    content = content.replace(old_callback, new_callback)
    print("SUCCESS: PlayerSelectView callback simplified")
else:
    print("ERROR: Callback not found, checking actual structure")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - select view uses cached data")
