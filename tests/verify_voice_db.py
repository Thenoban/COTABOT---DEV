import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import VoiceBalance, VoiceSession

async def test_voice_logic():
    print("=== Testing Voice Stats DB Logic ===")
    
    # Setup
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    guild_id = 1132812488880083046
    user_id = 123456789  # Test User
    channel_id = 987654321
    
    print(f"Test User: {user_id}, Guild: {guild_id}")
    
    # 1. Clean previous test data
    def clean():
        with db.session_scope() as session:
            session.query(VoiceBalance).filter_by(user_id=user_id).delete()
            session.query(VoiceSession).filter_by(user_id=user_id).delete()
    await asyncio.to_thread(clean)
    print("[OK] Cleaned previous test data")
    
    # 2. Add Initial Balance (Simulate Migration)
    initial_balance = 100
    initial_time = 3600.0 # 1 hour
    await db.update_voice_balance(guild_id, user_id, 
                                  coins_delta=initial_balance, 
                                  duration_delta=initial_time)
    print(f"[OK] Set initial balance: {initial_balance}, time: {initial_time}")
    
    # Verify Initial Stats
    stats = await db.get_user_voice_stats(guild_id, user_id)
    print(f"Stats after init: {stats}")
    assert stats['total_seconds'] == initial_time
    
    # 3. Start Session
    session_id = await db.start_voice_session(guild_id, user_id, channel_id, "Test Channel")
    print(f"[OK] Started session {session_id}")
    
    # Verify Active Session
    active = await db.get_active_session(guild_id, user_id)
    assert active is not None
    assert active.id == session_id
    
    # 4. End Session (Simulate 30 mins later)
    # We cheat by updating joined_at manually to be 30 mins ago
    def backdate_session():
        with db.session_scope() as session:
            s = session.query(VoiceSession).filter_by(id=session_id).first()
            s.joined_at = datetime.now() - timedelta(minutes=30)
    await asyncio.to_thread(backdate_session)
    
    # End it
    earned_coins = 50
    duration = await db.end_voice_session(session_id, coins_earned=earned_coins)
    print(f"[OK] Ended session. Duration: {duration}s")
    
    # 5. Update Balance with Session Result
    # In the actual cog, this happens in on_voice_state_update
    await db.update_voice_balance(guild_id, user_id, 
                                  coins_delta=earned_coins, 
                                  duration_delta=duration)
    
    # 6. Verify Final Stats
    final_stats = await db.get_user_voice_stats(guild_id, user_id)
    print(f"Final Stats: {final_stats}")
    
    expected_total = initial_time + duration
    # Allow small epsilon for execution time difference
    assert abs(final_stats['total_seconds'] - expected_total) < 5.0
    
    # Verify Balance Record
    def check_balance():
        with db.session_scope() as session:
            b = session.query(VoiceBalance).filter_by(user_id=user_id).first()
            if b:
                return b.balance, b.total_time_seconds
            return 0, 0.0
    bal_coins, bal_time = await asyncio.to_thread(check_balance)
    print(f"Final Balance in DB: {bal_coins} coins, {bal_time}s")
    
    assert bal_coins == initial_balance + earned_coins
    # The total time in balance should also be updated
    assert abs(bal_time - expected_total) < 5.0
    
    print("\n[SUCCESS] All logic tests passed!")

if __name__ == "__main__":
    asyncio.run(test_voice_logic())
