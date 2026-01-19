import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.adapter import DatabaseAdapter
from database.models import Event

async def test_event_logic():
    print("=== Testing Event DB Logic ===")
    
    # Setup
    db = DatabaseAdapter('sqlite:///cotabot_dev.db')
    guild_id = 999999999
    user_id = 123456789
    channel_id = 111222333
    
    print(f"Test Guild: {guild_id}")
    
    # 1. Clean previous test data
    def clean():
        with db.session_scope() as session:
            session.query(Event).filter_by(guild_id=guild_id).delete()
    await asyncio.to_thread(clean)
    print("[OK] Cleaned previous test data")
    
    # 2. Add Event
    start_time = datetime.now() + timedelta(hours=1)
    event_id = await db.add_event(
        guild_id=guild_id,
        event_id=1,
        title="Test Event",
        description="Test Description",
        timestamp=start_time,
        channel_id=channel_id,
        creator_id=user_id
    )
    print(f"[OK] Added event with DB ID: {event_id}")
    
    # 3. Update Event
    new_title = "Updated Event Title"
    new_desc = "Updated Description"
    updated = await db.update_event(event_id, title=new_title, description=new_desc)
    assert updated == True
    print("[OK] Updated event details")
    
    # Verify Update
    def get_event():
        with db.session_scope() as session:
            e = session.query(Event).filter_by(id=event_id).first()
            if e:
                return e.title, e.description, e.reminder_sent, e.active
            return None
    
    data = await asyncio.to_thread(get_event)
    assert data[0] == new_title
    assert data[1] == new_desc
    assert data[2] == False # Default reminder status
    assert data[3] == True  # Default active status
    print("[OK] Verified update results")
    
    # 4. Update Reminder Status
    rem_updated = await db.update_reminder_status(event_id, True)
    assert rem_updated == True
    
    data = await asyncio.to_thread(get_event)
    assert data[2] == True
    print("[OK] Updated reminder status")
    
    # 5. Deactivate Event
    deactivated = await db.deactivate_event(event_id)
    assert deactivated == True
    
    data = await asyncio.to_thread(get_event)
    assert data[3] == False
    print("[OK] Deactivated event")
    
    # Final check: get_active_events should not return this event
    active_events = await db.get_active_events(guild_id)
    assert len(active_events) == 0
    print("[OK] Active events query verified (empty)")
    
    print("\n[SUCCESS] All event logic tests passed!")

if __name__ == "__main__":
    asyncio.run(test_event_logic())
