import asyncio
import sys
import os
import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter

async def verify_activity_system():
    print("=== Activity System Verification ===")
    
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    
    # 1. Setup Test Data
    print("1. Setting up test data...")
    steam_id = "76561198_TEST_ACT"
    name = "TestPlayer_Activity"
    
    # Create player
    await db.delete_player(steam_id)
    pid = await db.add_player(steam_id, name)
    
    today = datetime.date.today()
    now = datetime.datetime.now()
    
    # Add activity for today (10 mins)
    await db.add_or_update_activity(pid, today, 10, now)
    
    # Add activity for 2 days ago (20 mins)
    prev_date = today - datetime.timedelta(days=2)
    await db.add_or_update_activity(pid, prev_date, 20, now)
    
    print("   [PASS] Test data added")
    
    # 2. Test get_player_activity
    print("2. Testing get_player_activity...")
    logs = await db.get_player_activity(pid, days=7)
    
    total_mins = sum(l.minutes for l in logs)
    if total_mins == 30:
        print(f"   [PASS] Activity logs retrieved correctly: {total_mins} mins")
    else:
        print(f"   [FAIL] Activity log mismatch: {total_mins} vs 30")

    # 3. Test Bulk Fetch (Optimization)
    print("3. Testing Bulk Fetch (get_all_recent_activity)...")
    bulk_data = await db.get_all_recent_activity(days=30)
    found_bulk = False
    for log, player in bulk_data:
        if player.steam_id == steam_id:
            found_bulk = True
            break
            
    if found_bulk and len(bulk_data) >= 1:
        print(f"   [PASS] Bulk fetch worked. Found {len(bulk_data)} records.")
    else:
        print(f"   [FAIL] Bulk fetch failed or empty. Found {len(bulk_data)}")
        
    # 4. Simulate Panel Generation Logic
    print("4. Simulating Panel Stats...")
    
    week_ago = today - datetime.timedelta(days=7)
    month_ago = today - datetime.timedelta(days=30)
    
    daily = 0
    weekly = 0
    monthly = 0
    
    # Re-fetch 30 days
    all_logs = await db.get_player_activity(pid, days=30)
    
    for log in all_logs:
        if log.date == today:
            daily += log.minutes
        if log.date >= week_ago:
            weekly += log.minutes
        if log.date >= month_ago:
            monthly += log.minutes
            
    print(f"   Calculated: Daily={daily}, Weekly={weekly}, Monthly={monthly}")
    
    if daily == 10 and weekly == 30 and monthly == 30:
         print("   [PASS] Panel Stats Logic Correct")
    else:
         print("   [FAIL] Panel Stats Logic Wrong")

    # 4. Clean up
    print("4. Cleaning up...")
    await db.delete_player(steam_id)
    print("   [PASS] Cleanup complete")

if __name__ == "__main__":
    asyncio.run(verify_activity_system())
