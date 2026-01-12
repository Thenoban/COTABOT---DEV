"""
Update delete button to use new delete_player method
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the manual SQL delete with cleaner adapter method call
old_sql_delete = '''                # Delete from database using async delete method (need to add to adapter)
                # For now, manually delete by getting player first
                player = await cog.db.get_player_by_steam_id(s_id)
                if player:
                    # Delete via SQL (adapter needs delete method)
                    from sqlalchemy import delete
                    def _delete_from_db():
                        with cog.db.session_scope() as session:
                            session.query(type(player)).filter_by(id=player.id).delete()
                    await asyncio.to_thread(_delete_from_db)
                    deleted = True'''

new_clean_delete = '''                # Delete from database
                deleted = await cog.db.delete_player(s_id)
                if deleted:'''

if old_sql_delete in content:
    content = content.replace(old_sql_delete, new_clean_delete)
    print("SUCCESS: Cleaned up delete code to use adapter method")
else:
    print("WARNING: Old code not found, may already be updated")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - Delete uses clean adapter method")
