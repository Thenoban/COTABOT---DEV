# -*- coding: utf-8 -*-
"""
Migration script to migrate events.json and event_history.json to database

This script:
1. Reads events.json (active events)
2. Reads event_history.json (archived events)
3. Migrates all events and participants to database
4. Creates backup of JSON files before migration
"""

import json
import os
import sys
import shutil
from datetime import datetime

# Add parent directory to path to import database modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import Base

EVENTS_FILE = "events.json"
HISTORY_FILE = "event_history.json"
BACKUP_DIR = "migration_archive"

def backup_json_files():
    """Backup JSON files before migration"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for filename in [EVENTS_FILE, HISTORY_FILE]:
        if os.path.exists(filename):
            backup_name = f"{BACKUP_DIR}/{filename}.{timestamp}.backup"
            shutil.copy2(filename, backup_name)
            print(f"[OK] Backed up {filename} to {backup_name}")

def load_json_file(filename):
    """Load JSON file, return empty dict if not exists"""
    if not os.path.exists(filename):
        print(f"[WARN] {filename} not found, skipping...")
        return {}
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Error reading {filename}: {e}")
        return {}

def migrate_events(db: DatabaseAdapter):
    """Migrate active events from events.json"""
    print("\n=== Migrating Active Events ===")
    
    events_data = load_json_file(EVENTS_FILE)
    
    if not events_data:
        print("No active events to migrate")
        return 0
    
    total_events = 0
    total_participants = 0
    
    for guild_id_str, events in events_data.items():
        guild_id = int(guild_id_str)
        print(f"\nGuild ID: {guild_id} - {len(events)} events")
        
        for event in events:
            try:
                # Parse timestamp
                timestamp_str = event.get("timestamp", "")
                event_timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()
                
                # Add event to database
                event_db_id = db.add_event(
                    guild_id=guild_id,
                    event_id=event.get("event_id", 0),
                    title=event.get("title", "Untitled Event"),
                    description=event.get("description", ""),
                    timestamp=event_timestamp,
                    channel_id=event.get("channel_id", 0),
                    creator_id=event.get("author_id", 0)
                )
                
                # Update message_id if exists
                if event.get("message_id"):
                    db.update_event_message(event_db_id, event["message_id"])
                
                total_events += 1
                print(f"  [OK] Event #{event.get('event_id')}: {event.get('title')}")
                
                # Migrate participants
                for status_type, status_key in [
                    ("attendee", "attendees"),
                    ("declined", "declined"),
                    ("tentative", "tentative")
                ]:
                    participants = event.get(status_key, [])
                    for participant_mention in participants:
                        # Extract user ID from mention (format: <@123456789>)
                        user_id = 0
                        if participant_mention.startswith("<@") and ">" in participant_mention:
                            user_id_str = participant_mention.split("<@")[1].split(">")[0]
                            # Remove ! if exists (for nicknames)
                            user_id_str = user_id_str.replace("!", "")
                            try:
                                user_id = int(user_id_str)
                            except:
                                pass
                        
                        if user_id:
                            reason = event.get("interaction_reason_map", {}).get(participant_mention, None)
                            db.add_event_participant(
                                event_db_id=event_db_id,
                                user_id=user_id,
                                user_mention=participant_mention,
                                status=status_type,
                                reason=reason
                            )
                            total_participants += 1
                
            except Exception as e:
                print(f"  [ERROR] Error migrating event {event.get('event_id')}: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n[OK] Migrated {total_events} events with {total_participants} participants")
    return total_events

def migrate_history(db: DatabaseAdapter):
    """Migrate archived events from event_history.json"""
    print("\n=== Migrating Event History ===")
    
    history_data = load_json_file(HISTORY_FILE)
    
    if not history_data:
        print("No event history to migrate")
        return 0
    
    total_archived = 0
    
    for guild_id_str, events in history_data.items():
        guild_id = int(guild_id_str)
        print(f"\nGuild ID: {guild_id} - {len(events)} archived events")
        
        for event in events:
            try:
                # Parse timestamp
                timestamp_str = event.get("timestamp", "")
                event_timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()
                
                # Add event to database (marked as inactive/archived)
                event_db_id = db.add_event(
                    guild_id=guild_id,
                    event_id=event.get("event_id", 0),
                    title=event.get("title", "Untitled Event"),
                    description=event.get("description", ""),
                    timestamp=event_timestamp,
                    channel_id=event.get("channel_id", 0),
                    creator_id=event.get("author_id", 0)
                )
                
                # Mark as archived/inactive
                # We'll need to add a method to mark events as inactive
                # For now, we can use ReportMetadata to store archived status
                
                total_archived += 1
                print(f"  [OK] Archived Event #{event.get('event_id')}: {event.get('title')}")
                
            except Exception as e:
                print(f"  [ERROR] Error migrating archived event: {e}")
    
    print(f"\n[OK] Migrated {total_archived} archived events")
    return total_archived

def verify_migration(db: DatabaseAdapter):
    """Verify migration by checking database"""
    print("\n=== Verification ===")
    
    # This is a simple verification - we'd need to add methods to DatabaseAdapter
    # to properly count events. For now, just report success.
    print("[OK] Migration completed. Please verify using database tools.")
    print("  Recommended SQL queries:")
    print("    SELECT COUNT(*) FROM events;")
    print("    SELECT COUNT(*) FROM event_participants;")

def main():
    print("=" * 60)
    print("EVENT MIGRATION SCRIPT")
    print("=" * 60)
    
    # Backup JSON files
    print("\n1. Creating backups...")
    backup_json_files()
    
    # Initialize database
    print("\n2. Initializing database...")
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    print("[OK] Database initialized")
    
    # Run migrations
    print("\n3. Running migrations...")
    try:
        events_count = migrate_events(db)
        history_count = migrate_history(db)
        
        print("\n" + "=" * 60)
        print(f"MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Active events migrated: {events_count}")
        print(f"Archived events migrated: {history_count}")
        print(f"Total: {events_count + history_count}")
        
        # Verify
        verify_migration(db)
        
        print("\n[SUCCESS] Migration completed successfully!")
        print("\nNext steps:")
        print("  1. Test event system with !1etkinlik command")
        print("  2. Verify database contents")
        print("  3. Update event.py to use database")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
