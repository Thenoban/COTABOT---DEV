"""
Fix message - show correct action (EKLENDI vs GÜNCELLENDI)
The message is sent BEFORE checking database, so we need better logic
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# In PlayerAddModal, the action message shows BEFORE database check
# We need to determine if player exists FIRST

old_message_section = '''        # CRITICAL: Respond to interaction FIRST (before slow sync)
        action = "GÜNCELLEND İ" if found else "EKLEND İ"
        await interaction.response.send_message(f"✅ Oyuncu başarıyla **{action}**!\\nİsim: {p_name}\\nSteamID: {s_id}", ephemeral=True)
        
        # HYBRID MODE: Check if using SQLite
        cog = self.bot.get_cog("SquadPlayers")
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            # SQLite mode - save to database instead of JSON
            try:
                player_exists = await cog.db.get_player_by_steam_id(s_id)
                if player_exists:
                    await cog.db.update_player(s_id, name=p_name, discord_id=parsed_d_id)
                else:
                    await cog.db.add_player(s_id, p_name, parsed_d_id)'''

new_message_section = '''        # HYBRID MODE: Check database first to determine action
        cog = self.bot.get_cog("SquadPlayers")
        player_exists = False
        
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            # SQLite mode - check if exists
            try:
                player_exists = await cog.db.get_player_by_steam_id(s_id)
                player_exists = bool(player_exists)
            except:
                pass
        else:
            # JSON mode - use 'found' from earlier
            player_exists = found
        
        # CRITICAL: Respond to interaction FIRST (before slow sync)
        action = "GÜNCELLEND İ" if player_exists else "EKLEND İ"
        await interaction.response.send_message(f"✅ Oyuncu başarıyla **{action}**!\\nİsim: {p_name}\\nSteamID: {s_id}", ephemeral=True)
        
        # HYBRID MODE: Save to database
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            # SQLite mode - save to database instead of JSON
            try:
                if player_exists:
                    await cog.db.update_player(s_id, name=p_name, discord_id=parsed_d_id)
                else:
                    await cog.db.add_player(s_id, p_name, parsed_d_id)'''

if old_message_section in content:
    content = content.replace(old_message_section, new_message_section)
    print("SUCCESS: Message now shows correct action")
else:
    print("ERROR: Section not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - action message fixed")
