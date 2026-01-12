"""
Migrate Player Delete to hybrid mode
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find delete_btn function and add hybrid mode check
# Insert after "deleted = False" and before "if os.path.exists(db_file):"

old_delete_start = '''        deleted = False
        if os.path.exists(db_file):'''

new_delete_start = '''        deleted = False
        
        # HYBRID MODE: Try SQLite first
        cog = self.bot.get_cog("SquadPlayers")
        if cog and hasattr(cog, 'json_mode') and hasattr(cog, 'db') and not cog.json_mode:
            try:
                # Delete from database using async delete method (need to add to adapter)
                # For now, manually delete by getting player first
                player = await cog.db.get_player_by_steam_id(s_id)
                if player:
                    # Delete via SQL (adapter needs delete method)
                    from sqlalchemy import delete
                    def _delete_from_db():
                        with cog.db.session_scope() as session:
                            session.query(type(player)).filter_by(id=player.id).delete()
                    await asyncio.to_thread(_delete_from_db)
                    deleted = True
                    
                    # Log to channel
                    await cog.log_to_channel(interaction.guild, "🗑️ Oyuncu Silindi (DB)", 
                        f"**Oyuncu:** {name}\\n**SteamID:** `{s_id}`", 
                        interaction.user, color=COLORS.ERROR)
                    
                    await interaction.response.send_message(f"✅ **{name}** ({s_id}) başarıyla silindi (DB).", ephemeral=True)
                    return  # Exit - database handled it
            except Exception as e:
                import logging
                logging.getLogger("SquadPlayers").error(f"DB delete error: {e}, fallback to JSON")
        
        # JSON mode or fallback
        if os.path.exists(db_file):'''

if old_delete_start in content:
    content = content.replace(old_delete_start, new_delete_start)
    print("SUCCESS: Delete button hybrid mode added")
else:
    print("ERROR: Delete marker not found")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - Delete button migrated")
