# -*- coding: utf-8 -*-
"""
Migration script to migrate voice_stats.json to database.
Only migrates balances and total time as historical data.
Sessions will start fresh.
"""

import json
import os
import sys
import shutil
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

def migrate_voice_stats(db: DatabaseAdapter):
    """Migrate voice stats to database"""
    print("\n=== Migrating Voice Stats ===")
    
    data = load_json_file(STATS_FILE)
    
    if not data:
        print("No voice stats to migrate")
        return 0
    
    total_migrated = 0
    total_skipped = 0
    
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
            
            # Use raw SQL or adapter? Adapter update_voice_balance handles create/update nicely
            # Assuming guild_id is unknown from JSON structure, we might need a default
            # But wait, VoiceBalance needs a guild_id.
            # Voice stats JSON didn't track guild_id (it was bot-wide or implicit single guild)
            # We'll use the main guild ID if possible, or fetch from bot config
            # For migration, we'll try to get it from a known constant or assume active guild
            # Since this is a script, we can't access bot.guilds.
            # PROBLEM: We need a guild_id for the database unique constraint.
            # SOLUTION: We'll use a placeholder guild_id (e.g., from config) or iterate all common guilds.
            # Let's inspect config.py for a main guild ID or fetch from database if possible.
            # For now, let's use a hardcoded main guild ID or 0 if global.
            # But wait, VoiceBalance has (guild_id, user_id) unique constraint.
            
            # Let's check config.py for main guild ID
            # It seems user has multiple guilds but usually 1 main active one.
            # Let's assume the main guild ID is 1132812488880083046 (from previous logs/context)
            # OR we can try to find it from adapter if possible.
            
            # Better approach: Migrate to ALL guilds? No.
            # Let's use a config value or argument.
            # Inspecting config.py...
            
            pass
            
        except Exception as e:
            print(f"  [ERROR] Error processing user {user_id_str}: {e}")
            total_skipped += 1
            
    # Re-reading: The JSON structure is:
    # "user_id": { ... }
    # It has NO guild info.
    # We must pick a target guild ID.
    # Let's temporarily check config.py content again to find a suitable ID.
    
    return total_migrated

# We'll pause writing to check config for Guild ID first.
