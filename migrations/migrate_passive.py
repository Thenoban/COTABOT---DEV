# -*- coding: utf-8 -*-
"""
Migration script to migrate passive_db.json to database

This script:
1. Reads passive_db.json
2. Migrates all passive requests to database
3. Creates backup of JSON file before migration
"""

import json
import os
import sys
import shutil
from datetime import datetime, date

# Add parent directory to path to import database modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import Base

PASSIVE_DB_FILE = "passive_db.json"
PASSIVE_CONFIG_FILE = "passive_config.json"
BACKUP_DIR = "migration_archive"

def backup_json_files():
    """Backup JSON files before migration"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for filename in [PASSIVE_DB_FILE, PASSIVE_CONFIG_FILE]:
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

def parse_date(date_str):
    """Parse date string in format DD.MM.YYYY"""
    try:
        day, month, year = map(int, date_str.split('.'))
        return date(year, month, day)
    except Exception as e:
        print(f"[WARN] Could not parse date '{date_str}': {e}")
        return None

def migrate_passive_requests(db: DatabaseAdapter):
    """Migrate passive requests from passive_db.json"""
    print("\n=== Migrating Passive Requests ===")
    
    data = load_json_file(PASSIVE_DB_FILE)
    
    if not data or not data.get("requests"):
        print("No passive requests to migrate")
        return 0
    
    total_migrated = 0
    total_skipped = 0
    
    for req in data.get("requests", []):
        try:
            user_id = req.get("user_id")
            user_name = req.get("user_name", "Unknown")
            reason = req.get("reason", "")
            start_date_str = req.get("start_date", "")
            end_date_str = req.get("end_date", "")
            
            # Parse dates
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            
            if not start_date or not end_date:
                print(f"  [SKIP] Invalid dates for {user_name}: {start_date_str} - {end_date_str}")
                total_skipped += 1
                continue
            
            # Add to database
            import asyncio
            request_id = asyncio.run(db.add_passive_request(
                user_id=user_id,
                user_name=user_name,
                reason=reason,
                start_date=start_date,
                end_date=end_date
            ))
            
            total_migrated += 1
            print(f"  [OK] Migrated: {user_name} ({start_date_str} - {end_date_str})")
            
        except Exception as e:
            print(f"  [ERROR] Error migrating request: {e}")
            import traceback
            traceback.print_exc()
            total_skipped += 1
    
    print(f"\n[OK] Migrated {total_migrated} passive requests, skipped {total_skipped}")
    return total_migrated

def verify_migration(db: DatabaseAdapter):
    """Verify migration by checking database"""
    print("\n=== Verification ===")
    
    try:
        import asyncio
        all_requests = asyncio.run(db.get_all_passive_requests())
        active_requests = asyncio.run(db.get_active_passive_requests())
        
        print(f"[OK] Total requests in database: {len(all_requests)}")
        print(f"[OK] Active requests in database: {len(active_requests)}")
        
        if all_requests:
            print("\nSample requests:")
            for req in all_requests[:5]:
                print(f"  - {req.user_name}: {req.start_date} to {req.end_date}")
    except Exception as e:
        print(f"[ERROR] Verification error: {e}")

def main():
    print("=" * 60)
    print("PASSIVE SYSTEM MIGRATION SCRIPT")
    print("=" * 60)
    
    # Backup JSON files
    print("\n1. Creating backups...")
    backup_json_files()
    
    # Initialize database
    print("\n2. Initializing database...")
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    print("[OK] Database initialized")
    
    # Run migration
    print("\n3. Running migration...")
    try:
        migrated_count = migrate_passive_requests(db)
        
        print("\n" + "=" * 60)
        print(f"MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Passive requests migrated: {migrated_count}")
        
        # Verify
        verify_migration(db)
        
        print("\n[SUCCESS] Migration completed successfully!")
        print("\nNext steps:")
        print("  1. Test passive system with !1pasif_panel command")
        print("  2. Verify database contents")
        print("  3. Archive passive_db.json")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
