"""
Quick Snapshot Test
Tests report system snapshot creation
"""
import sys
sys.path.append(r'\\192.168.1.174\cotabot\COTABOT - DEV')

import asyncio
import sqlite3
from database.adapter import DatabaseAdapter

async def test_snapshot():
    print("=== SNAPSHOT TEST ===\n")
    
    # Initialize adapter
    db_path = r'\\192.168.1.174\cotabot\COTABOT - DEV\cotabot_dev.db'
    db = DatabaseAdapter(f'sqlite:///{db_path}')
    
    # Test 1: Create snapshot
    print("1. Creating weekly snapshot...")
    try:
        snapshot_id = await db.create_snapshot("weekly")
        print(f"   ✅ Snapshot created! ID: {snapshot_id}\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
        return
    
    # Test 2: Set metadata
    print("2. Setting metadata...")
    try:
        await db.set_report_metadata("last_weekly", "2026-01-13 00:30:00")
        await db.set_report_metadata("last_weekly_snapshot_id", str(snapshot_id))
        print("   ✅ Metadata set\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 3: Get snapshot back
    print("3. Getting latest snapshot...")
    try:
        snapshot = await db.get_latest_snapshot("weekly")
        if snapshot:
            print(f"   ✅ Snapshot retrieved!")
            print(f"   - ID: {snapshot['id']}")
            print(f"   - Timestamp: {snapshot['timestamp']}")
            print(f"   - Entries: {len(snapshot['entries'])}\n")
        else:
            print("   ❌ No snapshot found\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
    
    # Test 4: Database integrity
    print("4. Database verification...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM report_snapshots")
    snapshots = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM snapshot_entries")
    entries = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM report_metadata")
    metadata = cursor.fetchone()[0]
    
    print(f"   - Snapshots: {snapshots}")
    print(f"   - Entries: {entries}")
    print(f"   - Metadata: {metadata}\n")
    
    conn.close()
    
    # Test 5: Calculate deltas (if we have snapshot)
    if snapshot_id:
        print("5. Calculating deltas...")
        try:
            deltas = await db.calculate_deltas(snapshot_id)
            print(f"   ✅ Deltas calculated: {len(deltas)}")
            if deltas:
                top_3 = deltas[:3]
                for i, d in enumerate(top_3, 1):
                    print(f"   {i}. {d['player_name']}: +{d['score_delta']} score")
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
    
    print("\n=== TEST COMPLETE ===")

# Run test
asyncio.run(test_snapshot())
