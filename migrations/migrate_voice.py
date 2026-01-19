# -*- coding: utf-8 -*-
"""
Migration script to migrate voice_stats.json to database.
Only migrates balances and total time as historical data.
Sessions will start fresh.

Usage: python migrations/migrate_voice.py <GUILD_ID>
"""

import json
import os
import sys
import shutil
import argparse
from datetime import datetime

# Add parent directory to path to import database modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import VoiceBalance

STATS_FILE = "voice_stats.json"
BACKUP_DIR = "migration_archive"

def backup_json_file():
    """Backup voice stats file before migration"""
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

def migrate_voice_stats(db: DatabaseAdapter, guild_id: int):
    """Migrate voice stats to database"""
    print(f"\n=== Migrating Voice Stats (Guild: {guild_id}) ===")
    
    data = load_json_file(STATS_FILE)
    
    if not data:
        print("No voice stats to migrate")
        return 0
    
    total_migrated = 0
    total_skipped = 0
    
    import asyncio
    
    for user_id_str, stats in data.items():
        try:
            user_id = int(user_id_str)
            
            # Handle both old (int/float) and new (dict) formats
            if isinstance(stats, (int, float)):
                total_time = float(stats)
                balance = 0
                pending = 0.0
            else:
                total_time = float(stats.get("total_time", 0.0))
                balance = int(stats.get("balance", 0))
                pending = float(stats.get("pending_seconds", 0.0))
            
            # Use update_voice_balance to creating/updating
            # We set initial balance by passing deltas, but since it assumes start from 0 for new records,
            # we can just use the values directly. 
            # But the adapter methods are additive (delta).
            # So we need a direct create or set method, OR we assume empty DB and add full amount.
            # Adapter update_voice_balance adds to existing. If empty, it starts with delta.
            # So passing the total values as deltas works for fresh DB.
            
            asyncio.run(db.update_voice_balance(
                guild_id=guild_id,
                user_id=user_id,
                coins_delta=balance,
                pending_secs_delta=pending,
                duration_delta=total_time
            ))
            
            total_migrated += 1
            if total_migrated % 10 == 0:
                print(f"  Processed {total_migrated} users...")
                
        except Exception as e:
            print(f"  [ERROR] Error processing user {user_id_str}: {e}")
            total_skipped += 1
            
    print(f"\n[OK] Migrated {total_migrated} users, skipped {total_skipped}")
    return total_migrated

def verify_migration(db: DatabaseAdapter, guild_id: int):
    """Verify migration"""
    print("\n=== Verification ===")
    import asyncio
    
    # Check leaderboard to see top users
    leaderboard = asyncio.run(db.get_voice_leaderboard(guild_id, limit=5))
    
    if leaderboard:
        print(f"[OK] Found {len(leaderboard)} users in leaderboard")
        for i, entry in enumerate(leaderboard, 1):
            print(f"  {i}. User {entry['user_id']}: {entry['total_seconds']:.1f}s")
    else:
        print("[WARN] Leaderboard is empty")

def main():
    parser = argparse.ArgumentParser(description="Migrate voice stats to database")
    parser.add_argument("guild_id", type=int, help="Target Guild ID for migration")
    args = parser.parse_args()
    
    print("=" * 60)
    print("VOICE STATS MIGRATION SCRIPT")
    print("=" * 60)
    
    # Backup
    print("\n1. Creating backup...")
    backup_json_file()
    
    # Initialize DB
    print("\n2. Initializing database...")
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    print("[OK] Database initialized")
    
    # Migrate
    print("\n3. Running migration...")
    try:
        migrate_voice_stats(db, args.guild_id)
        verify_migration(db, args.guild_id)
        print("\n[SUCCESS] Migration completed successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
