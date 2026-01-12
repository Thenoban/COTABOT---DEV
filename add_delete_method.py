"""
Add delete_player method to DatabaseAdapter
"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\database\adapter.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the end of player operations section (after update_player)
# Insert new delete_player method

new_method = '''
    async def delete_player(self, steam_id: str) -> bool:
        """Delete player by Steam ID, returns True if deleted"""
        def _delete():
            with self.session_scope() as session:
                player = session.query(Player).filter_by(steam_id=steam_id).first()
                if player:
                    session.delete(player)
                    return True
                return False
        return await asyncio.to_thread(_delete)
    
'''

# Find line after "async def get_all_players" and insert before it
for i, line in enumerate(lines):
    if 'async def get_all_players' in line:
        # Insert before this line
        lines.insert(i, new_method)
        print(f"Inserted delete_player method at line {i}")
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("DatabaseAdapter updated with delete_player method")
