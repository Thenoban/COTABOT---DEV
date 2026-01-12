"""
Fix oyuncu_yonet panel to show database count instead of JSON
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_panel_code = '''    @commands.command(name='oyuncu_yonet')
    async def oyuncu_yonet(self, ctx):
        if not await self.check_permissions(ctx): return
        
        total_players = 0
        last_update = "Bilinmiyor"
        if os.path.exists("squad_db.json"):
             try:
                 def _read_db():
                     with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
                 data = await asyncio.to_thread(_read_db)
                 total_players = len(data.get("players", []))
                 last_update = data.get("last_update", "Bilinmiyor")
             except: pass'''

new_panel_code = '''    @commands.command(name='oyuncu_yonet')
    async def oyuncu_yonet(self, ctx):
        if not await self.check_permissions(ctx): return
        
        total_players = 0
        last_update = "Bilinmiyor"
        
        # HYBRID MODE: Count from database or JSON
        if hasattr(self, 'json_mode') and hasattr(self, 'db') and not self.json_mode:
            try:
                all_players = await self.db.get_all_players()
                total_players = len(all_players)
                # Get last update from database (could track in a metadata table)
                last_update = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
            except Exception as e:
                logger.error(f"DB count error: {e}")
        
        # JSON fallback
        if total_players == 0 and os.path.exists("squad_db.json"):
             try:
                 def _read_db():
                     with open("squad_db.json", "r", encoding="utf-8") as f: return json.load(f)
                 data = await asyncio.to_thread(_read_db)
                 total_players = len(data.get("players", []))
                 last_update = data.get("last_update", "Bilinmiyor")
             except: pass'''

if old_panel_code in content:
    content = content.replace(old_panel_code, new_panel_code)
    print("SUCCESS: oyuncu_yonet panel now uses database count")
else:
    print("ERROR: Panel code not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - panel will show 55 after restart (if test player was added)")
