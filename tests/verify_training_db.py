
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import TrainingMatch, TrainingMatchPlayer

async def verify_training_db():
    print("="*60)
    print("VERIFYING TRAINING SYSTEM DATABASE")
    print("="*60)
    
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    db.init_db()
    
    # 1. Get Matches
    print("\n1. Testing get_training_matches...")
    matches = await db.get_training_matches(limit=5)
    print(f"   Matches found: {len(matches)}")
    for m in matches:
        print(f"   - Match #{m['match_id']} | Status: {m['status']} | Players: {len(m['players'])}")
        
    # 2. Test Create Match
    print("\n2. Testing create_training_match...")
    new_id = 9999
    try:
        await db.create_training_match(new_id, "127.0.0.1", "TestMap", datetime.now())
        print(f"   [OK] Match {new_id} created")
    except Exception as e:
        print(f"   [ERROR] Failed to create match: {e}")
        
    # 3. Test Update Match
    print("\n3. Testing update_training_match...")
    try:
        success = await db.update_training_match(new_id, status='completed', end_time=datetime.now())
        print(f"   [OK] Update status: {success}")
    except Exception as e:
        print(f"   [ERROR] Failed to update match: {e}")

    # 4. Test Add Player
    print("\n4. Testing add_training_player...")
    try:
        await db.add_training_player(new_id, {
            'steam_id': '76561198000000000',
            'name': 'TestPlayer',
            'kills_manual': 10,
            'deaths_manual': 5
        })
        print("   [OK] Player added")
    except Exception as e:
        print(f"   [ERROR] Failed to add player: {e}")
        
    # 5. Verify Data Persistence
    print("\n5. Verifying persistence...")
    matches = await db.get_training_matches(limit=10)
    found = False
    for m in matches:
        if m['match_id'] == new_id:
             found = True
             p_count = len(m['players'])
             print(f"   [OK] Match {new_id} found with {p_count} players")
             break
    
    if not found:
        print(f"   [ERROR] Match {new_id} NOT found after creation!")

    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(verify_training_db())
