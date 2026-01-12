"""
Migration script: JSON to SQLite
Converts existing JSON files to SQLite database
"""
import json
import asyncio
import sys
import os
from datetime import datetime, date

# Import database modules directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from database.adapter import DatabaseAdapter


def safe_print(*args, **kwargs):
    """Safe print that handles unicode encoding issues on Windows"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: encode with ignore errors
        safe_args = [str(arg).encode('ascii', 'replace').decode('ascii') for arg in args]
        print(*safe_args, **kwargs)


async def migrate_players(db: DatabaseAdapter, json_file='squad_db.json'):
    """Migrate players from JSON to SQLite"""
    safe_print(f"\nMigrating players from {json_file}...")
    
    if not os.path.exists(json_file):
        safe_print(f"ERROR: File not found: {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    players = data.get('players', [])
    safe_print(f"Found {len(players)} players")
    
    success_count = 0
    error_count = 0
    
    for p in players:
        try:
            steam_id = p['steam_id']
            name = p['name']
            discord_id = p.get('discord_id')
            
            # Add player
            player_id = await db.add_player(steam_id, name, discord_id)
            
            # Add stats if available
            if 'stats' in p and p['stats']:
                all_time_data = p['stats']
                season_data = p.get('season_stats', {})
                await db.add_or_update_stats(player_id, all_time_data, season_data or {})
            
            success_count += 1
            safe_print(f"  OK {name}")
            
        except Exception as e:
            error_count += 1
            safe_print(f"  ERR Error with player: {str(e)[:50]}")
    
    safe_print(f"\nPlayer migration complete")
    safe_print(f"   Success: {success_count}")
    safe_print(f"   Errors: {error_count}")


async def migrate_activity(db: DatabaseAdapter, json_file='squad_activity.json'):
    """Migrate activity logs from JSON to SQLite"""
    safe_print(f"\nMigrating activity from {json_file}...")
    
    if not os.path.exists(json_file):
        safe_print(f"ERROR: File not found: {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    safe_print(f"Found activity for {len(data)} players")
    
    success_count = 0
    error_count = 0
    
    for steam_id, activity_data in data.items():
        try:
            player = await db.get_player_by_steam_id(steam_id)
            if not player:
                safe_print(f"  WARNING Player {steam_id} not found, skipping")
                error_count += 1
                continue
            
            history = activity_data.get('history', {})
            for date_str, minutes in history.items():
                try:
                    activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    last_seen = datetime.fromisoformat(activity_data.get('last_seen', datetime.now().isoformat()))
                    
                    await db.add_or_update_activity(
                        player_id=player.id,
                        activity_date=activity_date,
                        minutes=minutes,
                        last_seen=last_seen
                    )
                except:
                    pass
            
            success_count += 1
            safe_print(f"  OK {activity_data.get('name', steam_id)}: {len(history)} days")
            
        except Exception as e:
            error_count += 1
            safe_print(f"  ERR Error: {str(e)[:50]}")
    
    safe_print(f"\nActivity migration complete")
    safe_print(f"   Success: {success_count}")
    safe_print(f"   Errors: {error_count}")


async def migrate_events(db: DatabaseAdapter, json_file='events.json'):
    """Migrate events from JSON to SQLite"""
    safe_print(f"\nMigrating events from {json_file}...")
    
    if not os.path.exists(json_file):
        safe_print(f"ERROR: File not found: {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    success_count = 0
    error_count = 0
    
    for guild_id, events_list in data.items():
        for event_data in events_list:
            try:
                event_id = await db.add_event(
                    guild_id=int(guild_id),
                    event_id=event_data['id'],
                    title=event_data['title'],
                    description=event_data['description'],
                    timestamp=datetime.fromisoformat(event_data['timestamp']),
                    channel_id=event_data['channel_id'],
                    creator_id=event_data['creator_id']
                )
                
                # Add participants
                for attendee in event_data.get('attendees', []):
                    await db.add_event_participant(event_id, attendee['user_id'], 
                                                   attendee['mention'], 'attendee')
                
                for declined in event_data.get('declined', []):
                    await db.add_event_participant(event_id, declined['user_id'],
                                                   declined['mention'], 'declined',
                                                   declined.get('reason'))
                
                for tentative in event_data.get('tentative', []):
                    await db.add_event_participant(event_id, tentative['user_id'],
                                                   tentative['mention'], 'tentative')
                
                success_count += 1
                safe_print(f"  OK Event migrated")
                
            except Exception as e:
                error_count += 1
                safe_print(f"  ERR Error: {str(e)[:50]}")
    
    safe_print(f"\nEvent migration complete")
    safe_print(f"   Success: {success_count}")
    safe_print(f"   Errors: {error_count}")


async def main():
    """Main migration function"""
    safe_print("=" * 60)
    safe_print("Cotabot JSON to SQLite Migration")
    safe_print("=" * 60)
    
    # Initialize database
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    
    safe_print("\nStarting migration...")
    
    # Migrate players first (required for foreign keys)
    await migrate_players(db)
    
    # Migrate activity logs
    await migrate_activity(db)
    
    # Migrate events
    await migrate_events(db)
    
    safe_print("\n" + "=" * 60)
    safe_print("Migration Complete!")
    safe_print("=" * 60)
    safe_print("\nDatabase: cotabot_dev.db")
    safe_print("You can now test the new database layer")


if __name__ == '__main__':
    asyncio.run(main())
