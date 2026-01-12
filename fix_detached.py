import sys

# Read file
filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\squad_players.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the problematic section (around line 1972-1981)
content = ''.join(lines)

old_section = """            # Convert DB object to dict (backward compatibility)
            if player_obj:
                stats_obj = await self.db.get_player_stats(player_obj.id)
                resolved_player = {
                    "steam_id": player_obj.steam_id,
                    "name": player_obj.name,
                    "discord_id": player_obj.discord_id,
                    "stats": json.loads(stats_obj.all_time_json) if stats_obj and stats_obj.all_time_json else {},
                    "season_stats": json.loads(stats_obj.season_json) if stats_obj and stats_obj.season_json else {}
                }"""

new_section = """            # Convert DB object to dict (backward compatibility)
            if player_obj:
                # Extract ALL attributes BEFORE session closes (avoid DetachedInstanceError)
                player_id = player_obj.id
                player_steam_id = player_obj.steam_id
                player_name = player_obj.name
                player_discord_id = player_obj.discord_id
                
                stats_obj = await self.db.get_player_stats(player_id)
                all_time_json = stats_obj.all_time_json if stats_obj else None
                season_json = stats_obj.season_json if stats_obj else None
                
                resolved_player = {
                    "steam_id": player_steam_id,
                    "name": player_name,
                    "discord_id": player_discord_id,
                    "stats": json.loads(all_time_json) if all_time_json else {},
                    "season_stats": json.loads(season_json) if season_json else {}
                }"""

if old_section in content:
    content = content.replace(old_section, new_section)
    print("FIXED: DetachedInstanceError section replaced")
else:
    print("ERROR: Section not found")

# Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
