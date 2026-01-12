"""
PlayerAddModal hybrid mode - Insert database logic
"""
import re

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the line "cog = self.bot.get_cog("SquadPlayers")" in PlayerAddModal
# and insert hybrid mode check BEFORE it

# Pattern: after "await interaction.response.send_message" and before "# Now do slow operations"
insertion_marker = '# Now do slow operations in background'

hybrid_code = '''# HYBRID MODE: Check if using SQLite
        cog = self.bot.get_cog("SquadPlayers")
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            # SQLite mode - save to database instead of JSON
            try:
                player_exists = await cog.db.get_player_by_steam_id(s_id)
                if player_exists:
                    await cog.db.update_player(s_id, name=p_name, discord_id=parsed_d_id)
                else:
                    await cog.db.add_player(s_id, p_name, parsed_d_id)
                
                # Log to channel
                await cog.log_to_channel(interaction.guild, "✏️ Oyuncu (DB)", 
                    f"**Oyuncu:** {p_name}\\n**SteamID:** `{s_id}`\\n**Discord:** {parsed_d_id or '-'}", 
                    interaction.user)
                return  # Exit - database handled it
            except Exception as e:
                import logging
                logging.getLogger("SquadPlayers").error(f"DB save error: {e}, fallback to JSON")
        
        '''

if insertion_marker in content:
    content = content.replace(
        f'        {insertion_marker}',
        hybrid_code + f'        {insertion_marker}'
    )
    print("SUCCESS: Hybrid mode code inserted before JSON operations")
else:
    print("ERROR: Insertion marker not found")
    print("Searching for alternative markers...")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
