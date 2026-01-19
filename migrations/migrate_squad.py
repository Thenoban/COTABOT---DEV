# -*- coding: utf-8 -*-
"""
Migration script to migrate squad_db.json to database.
Transfers players, stats, and season stats.
"""

import json
import os
import sys
import shutil
import asyncio
from datetime import datetime

# Add parent directory to path to import database modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import Player, PlayerStats

STATS_FILE = "squad_db.json"
BACKUP_DIR = "migration_archive"

def backup_json_file():
    """Backup squad database file before migration"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if os.path.exists(STATS_FILE):
        backup_name = f"{BACKUP_DIR}/{STATS_FILE}.{timestamp}.backup"
        shutil.copy2(STATS_FILE, backup_name)
        print(f"[OK] Backed up {STATS_FILE} to {backup_name}")
        return True
    return False

def load_json_file(filename):
    """Load JSON file"""
    if not os.path.exists(filename):
        print(f"[WARN] {filename} not found")
        return {}
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Error reading {filename}: {e}")
        return {}

async def migrate_squad_db(db: DatabaseAdapter):
    """Migrate squad players and stats to database"""
    print("\n=== Migrating Squad Database ===")
    
    data = load_json_file(STATS_FILE)
    
    if not data or "players" not in data:
        print("No players data to migrate")
        return 0
    
    players_list = data["players"]
    total_players = len(players_list)
    print(f"Found {total_players} players to migrate")
    
    migrated_count = 0
    skipped_count = 0
    
    for i, p_data in enumerate(players_list, 1):
        try:
            steam_id = p_data.get("steam_id")
            name = p_data.get("name")
            discord_id = p_data.get("discord_id")
            
            # Normalize discord_id
            if discord_id and isinstance(discord_id, str):
                if discord_id.isdigit():
                    discord_id = int(discord_id)
                else:
                    # Ignore string usernames, we only want numeric IDs
                    discord_id = None
            
            if not steam_id or not name:
                print(f"  [WARN] Skipping invalid player data: {p_data}")
                skipped_count += 1
                continue
                
            # 1. Add/Update Player
            # Check if exists first to decide update or add (although adapter handles logic, explicit is better for migration)
            existing_player = await db.get_player_by_steam_id(steam_id)
            
            player_id = 0
            if existing_player:
                await db.update_player(steam_id, name=name, discord_id=discord_id)
                player_id = existing_player.id
            else:
                player_id = await db.add_player(steam_id, name=name, discord_id=discord_id)
            
            # 2. Add/Update Stats
            stats = p_data.get("stats", {})
            season_stats = p_data.get("season_stats", {})
            
            await db.add_or_update_stats(player_id, stats, season_stats)
            
            migrated_count += 1
            if i % 10 == 0:
                print(f"  Processed {i}/{total_players} players...")
                
        except Exception as e:
            print(f"  [ERROR] Error processing player {p_data.get('name', 'Unknown')}: {e}")
            skipped_count += 1
            
    print(f"\n[OK] Migrated {migrated_count} players, skipped {skipped_count}")
    return migrated_count

def main():
    print("=" * 60)
    print("SQUAD DATABASE MIGRATION SCRIPT")
    print("=" * 60)
    
    # Backup
    print("\n1. Creating backup...")
    if not backup_json_file():
        # If backup fails (file might not exist), confirm proceed
        if os.path.exists(STATS_FILE):
             print("[ERROR] Backup failed. Aborting.")
             return 1
        else:
             print("[INFO] No squad_db.json found. Skipping migration.")
             return 0

    # Initialize DB
    print("\n2. Initializing database...")
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    print("[OK] Database initialized")
    
    # Migrate
    print("\n3. Running migration...")
    try:
        asyncio.run(migrate_squad_db(db))
        print("\n[SUCCESS] Migration completed successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
