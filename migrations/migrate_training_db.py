"""
Migrate training_db.json → SQLite
Reads training_db.json and imports all matches to database
"""
import asyncio
import json
import os
import sys
import shutil
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter

async def migrate_training_db():
    """Main migration function"""
    print("=" * 60)
    print("TRAINING DB MIGRATION")
    print("=" * 60)
    
    # 1. Load training_db.json
    if not os.path.exists('training_db.json'):
        print("[ERROR] training_db.json not found!")
        return False
    
    with open('training_db.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    matches = data.get('matches', [])
    print(f"\n[INFO] Found {len(matches)} matches in training_db.json")
    
    if not matches:
        print("[WARN]  No matches to migrate")
        return True
    
    # 2. Backup original file
    backup_dir = f'backups/migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy('training_db.json', f'{backup_dir}/training_db.json.backup')
    print(f"[OK] Backup created: {backup_dir}/training_db.json.backup")
    
    # 3. Connect to database
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    print("[OK] Database connected")
    
    # 4. Migrate each match
    migrated = 0
    failed = []
    
    for match in matches:
        try:
            match_id = match.get('match_id')
            print(f"\n  Migrating match #{match_id}...")
            
            # Create match record
            await db.create_training_match(
                match_id=match_id,
                server_ip=match.get('server_ip', ''),
                map_name=match.get('map', 'Unknown'),
                start_time=datetime.fromisoformat(match['start_time']) if match.get('start_time') else datetime.now()
            )
            
            # Update end time and status if completed
            if match.get('end_time'):
                await db.update_training_match(
                    match_id=match_id,
                    status=match.get('status', 'completed'),
                    end_time=datetime.fromisoformat(match['end_time']),
                    snapshot_start=json.dumps(match.get('snapshot_start')) if match.get('snapshot_start') else None,
                    snapshot_end=json.dumps(match.get('snapshot_end')) if match.get('snapshot_end') else None
                )
            
            # Migrate players
            players = match.get('players', [])
            for player in players:
                await db.add_training_player(
                    match_id=match_id,
                    player_data={
                        'steam_id': player.get('steam_id', 'unknown'),
                        'name': player.get('name', 'Unknown'),
                        'kills_manual': player.get('kills_manual'),
                        'deaths_manual': player.get('deaths_manual'),
                        'assists_manual': player.get('assists_manual'),
                        'final_kills': player.get('final_kills', 0),
                        'final_deaths': player.get('final_deaths', 0),
                        'final_assists': player.get('final_assists', 0),
                        'kd_ratio': player.get('kd_ratio', 0.0),
                        'data_source': player.get('data_source', 'manual')
                    }
                )
            
            print(f"    [OK] Match #{match_id}: {len(players)} players migrated")
            migrated += 1
            
        except Exception as e:
            print(f"    [ERROR] Match #{match_id} failed: {e}")
            failed.append((match_id, str(e)))
    
    # 5. Verify migration
    print(f"\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    db_matches = await db.get_training_matches(limit=100)
    print(f"[OK] Database contains {len(db_matches)} matches")
    print(f"[OK] Successfully migrated: {migrated}/{len(matches)}")
    
    if failed:
        print(f"[ERROR] Failed: {len(failed)}")
        for match_id, error in failed:
            print(f"   - Match #{match_id}: {error}")
    
    # 6. Summary
    success_rate = (migrated / len(matches)) * 100 if matches else 100
    print(f"\n{'=' * 60}")
    print(f"Migration complete: {success_rate:.1f}% success rate")
    print(f"{'=' * 60}\n")
    
    return success_rate == 100.0

if __name__ == '__main__':
    success = asyncio.run(migrate_training_db())
    if success:
        print("\n[SUCCESS] Training DB migration successful!")
        print("   Original file backed up.")
        print("   You can now remove training_db.json or keep as archive.")
    else:
        print("\n[WARN]  Migration completed with errors!")
        print("   Check errors above and retry if needed.")
