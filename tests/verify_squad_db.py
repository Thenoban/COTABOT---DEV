import asyncio
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import Player, PlayerStats

async def verify_squad_db():
    print("=== Squad DB Verification ===")
    
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    
    # 1. Add Player
    steam_id = "76561198_TEST_VERIFY"
    name = "TestPlayer_Verification"
    discord_id = 123456789
    
    print(f"1. Adding player: {name} ({steam_id})")
    # Clean up first just in case
    await db.delete_player(steam_id)
    
    player_id = await db.add_player(steam_id, name, discord_id)
    
    # Check
    p = await db.get_player_by_steam_id(steam_id)
    if p and p.name == name:
        print("   [PASS] Player added successfully")
    else:
        print("   [FAIL] Player not found")
        return

    # 2. Add Stats
    print("2. Adding stats...")
    stats = {
        "totalScore": 1000,
        "totalKills": 50,
        "totalDeaths": 10,
        "totalKdRatio": 5.0
    }
    season_stats = {
        "seasonScore": 100,
        "seasonKills": 5,
        "seasonDeaths": 1,
        "seasonKdRatio": 5.0
    }
    
    await db.add_or_update_stats(p.id, stats, season_stats)
    
    # Check Stats
    p_stats = await db.get_player_stats(p.id)
    if p_stats:
        print(f"   Stats found: Kills={p_stats.total_kills}, SeasonKills={p_stats.season_kills}")
        # Check JSON fields too
        all_time_json = json.loads(p_stats.all_time_json)
        if p_stats.total_kills == 50 and all_time_json.get("totalKills") == 50:
             print("   [PASS] Stats updated correctly (Columns + JSON)")
        else:
             print(f"   [FAIL] Stats mismatch: {p_stats.total_kills} vs 50")
    else:
        print("   [FAIL] Stats not found")

    # 3. Simulate Search & Eager Load Check
    print("3. Testing Search & Eager Loading...")
    results = await db.search_players("TestPlayer_Verif")
    if len(results) > 0 and results[0].steam_id == steam_id:
         print(f"   [PASS] Search found {len(results)} player(s)")
         # Verify we can access stats without session (DetachedInstanceError check)
         try:
             s = results[0].stats
             if s and s.total_kills == 50:
                 print("   [PASS] Stats eager loaded successfully")
             else:
                 print("   [FAIL] Stats loaded but values missing/wrong")
         except Exception as e:
             print(f"   [FAIL] Eager load failed (DetachedInstanceError?): {e}")
    else:
         print(f"   [FAIL] Search failed. Found: {len(results)}")
         
    # Test get_all_players too
    all_p = await db.get_all_players()
    found_in_all = False
    for p_obj in all_p:
        if p_obj.steam_id == steam_id:
            found_in_all = True
            try:
                _ = p_obj.stats.total_score
            except Exception as e:
                print(f"   [FAIL] get_all_players eager load failed: {e}")
    if found_in_all: print("   [PASS] get_all_players verified")

    # 4. Clean up
    print("4. Cleaning up...")
    await db.delete_player(steam_id)
    check = await db.get_player_by_steam_id(steam_id)
    if not check:
        print("   [PASS] Cleanup complete")
    else:
        print("   [FAIL] Cleanup failed")

if __name__ == "__main__":
    asyncio.run(verify_squad_db())
