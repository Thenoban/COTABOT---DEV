"""
Migrate PlayerAddModal to hybrid mode (JSON + SQLite)
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find PlayerAddModal.on_submit and add hybrid mode logic
# The function starts around line 56

# We need to insert code after interaction.response.send_message (around line 111)
# to save to database if in SQLite mode

new_code_insertion = '''
    # Save to database (hybrid mode)
    cog = self.bot.get_cog("SquadPlayers")
    if cog and not cog.json_mode:
        # SQLite mode - save to database
        try:
            player_exists = await cog.db.get_player_by_steam_id(s_id)
            if player_exists:
                # Update existing player
                await cog.db.update_player(s_id, name=p_name, discord_id=parsed_d_id)
            else:
                # Add new player
                await cog.db.add_player(s_id, p_name, parsed_d_id)
            
            # Log success
            action = "GUNCELLENDI" if player_exists else "EKLENDI"
            logger.info(f"Player {action} (SQLite): {p_name} ({s_id})")
        except Exception as e:
            logger.error(f"Database save error in PlayerAddModal: {e}")
            # Fallback to JSON will happen below
    
    # JSON mode or SQLite fallback
    if cog and cog.json_mode or not cog:
'''

# This is complex - let's use a targeted replacement approach
# Find the section after "await interaction.response.send_message" and before "cog = self.bot.get_cog"

search_marker = '''    # CRITICAL: Respond to interaction FIRST (before slow sync)
    action = "GÜNCELLENDI" if found else "EKLENDI"
    await interaction.response.send_message(f"✅ Oyuncu başarıyla **{action}**!\\nİsim: {p_name}\\nSteamID: {s_id}", ephemeral=True)
    
    # Now do slow operations in background
    cog = self.bot.get_cog("SquadPlayers")'''

replacement = '''    # CRITICAL: Respond to interaction FIRST (before slow sync)
    action = "GÜNCELLENDI" if found else "EKLENDI"
    await interaction.response.send_message(f"✅ Oyuncu başarıyla **{action}**!\\nİsim: {p_name}\\nSteamID: {s_id}", ephemeral=True)
    
    # HYBRID MODE: Save to database or JSON
    cog = self.bot.get_cog("SquadPlayers")
    if cog and hasattr(cog, 'json_mode') and not cog.json_mode:
        # SQLite mode - save to database
        try:
            player_exists = await cog.db.get_player_by_steam_id(s_id)
            if player_exists:
                await cog.db.update_player(s_id, name=p_name, discord_id=parsed_d_id)
            else:
                await cog.db.add_player(s_id, p_name, parsed_d_id)
            
            # Skip JSON file operations - database handled it
            await cog.log_to_channel(interaction.guild, "✏️ Oyuncu Düzenlendi/Eklendi (DB)", 
                f"**Oyuncu:** {p_name}\\n**SteamID:** `{s_id}`\\n**Discord:** {parsed_d_id or '-'}", 
                interaction.user)
            return  # Exit early - no need for JSON operations
        except Exception as e:
            import logging
            logger = logging.getLogger("SquadPlayers")
            logger.error(f"Database save error in PlayerAddModal: {e}, falling back to JSON")
    
    # JSON mode or fallback - original code
    cog = self.bot.get_cog("SquadPlayers")'''

content = ''.join(lines)
if search_marker in content:
    content = content.replace(search_marker, replacement)
    print("SUCCESS: PlayerAddModal migrated to hybrid mode")
else:
    print("ERROR: Marker not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - test with !1oyuncu_yonet")
