"""
Fix PlayerSelectDropdown callback - store players list and use it
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Add players to PlayerSelectView __init__
old_init = '''class PlayerSelectView(discord.ui.View):
    def __init__(self, bot, players):
        super().__init__(timeout=180)
        self.bot = bot
        options = []
        for p in players:
            label = p['name'][:100]
            desc = f"SID: {p['steam_id']}"
            options.append(discord.SelectOption(label=label, description=desc, value=p['steam_id']))
        
        self.add_item(PlayerSelectDropdown(bot, options))'''

new_init = '''class PlayerSelectView(discord.ui.View):
    def __init__(self, bot, players):
        super().__init__(timeout=180)
        self.bot = bot
        self.players = players  # Store for later use
        options = []
        for p in players:
            label = p['name'][:100]
            desc = f"SID: {p['steam_id']}"
            options.append(discord.SelectOption(label=label, description=desc, value=p['steam_id']))
        
        self.add_item(PlayerSelectDropdown(bot, options, players))'''  # Pass players

#Fix 2: Update PlayerSelectDropdown to receive and use players
old_dropdown_init = '''class PlayerSelectDropdown(discord.ui.Select):
    def __init__(self, bot, options):
        self.bot = bot
        super().__init__(placeholder="Bir oyuncu seçin...", min_values=1, max_values=1, options=options)'''

new_dropdown_init = '''class PlayerSelectDropdown(discord.ui.Select):
    def __init__(self, bot, options, players):
        self.bot = bot
        self.players = players  # Store player data
        super().__init__(placeholder="Bir oyuncu seçin...", min_values=1, max_values=1, options=options)'''

# Fix 3: Update callback to use self.players instead of re-reading JSON
old_callback_start = '''    async def callback(self, interaction: discord.Interaction):
        steam_id = self.values[0]
        
        target_player = None
        if os.path.exists("squad_db.json"):'''

new_callback_start = '''    async def callback(self, interaction: discord.Interaction):
        steam_id = self.values[0]
        
        # Use cached player data
        target_player = None
        for p in self.players:
            if p.get("steam_id") == steam_id:
                target_player = p
                break
        
        # JSON fallback if not found
        if not target_player and os.path.exists("squad_db.json"):'''

content = content.replace(old_init, new_init)
content = content.replace(old_dropdown_init, new_dropdown_init)
content = content.replace(old_callback_start, new_callback_start)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: PlayerSelectView now uses cached player data")
print("Docker restart required")
