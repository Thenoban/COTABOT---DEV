
import sys
import os
import asyncio
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import VoiceBalance, VoiceSession

async def reset_voice_stats():
    print("WARNING: Resetting ALL Voice Stats...")
    # confirm = input("Are you sure? (yes/no): ")
    # if confirm.lower() != "yes":
    #    print("Aborted.")
    #    return

    db_url = 'sqlite:///cotabot_dev.db'
    adapter = DatabaseAdapter(db_url)
    
    print(f"Connecting to {db_url}...")
    
    try:
        def _truncate():
            with adapter.session_scope() as session:
                # Delete all rows
                deleted_sessions = session.query(VoiceSession).delete()
                deleted_balances = session.query(VoiceBalance).delete()
                print(f"Deleted {deleted_sessions} voice sessions.")
                print(f"Deleted {deleted_balances} voice balances.")
        
        await asyncio.to_thread(_truncate)
        print("✅ Voice stats reset complete.")
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_voice_stats())
