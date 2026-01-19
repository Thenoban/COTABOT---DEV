# Test script to create a sample event
import sys
sys.path.insert(0, r'\\192.168.1.174\cotabot\COTABOT - DEV')

from database.adapter import DatabaseAdapter
from datetime import datetime, timedelta
import asyncio

async def create_test_events():
    db = DatabaseAdapter(r'\\192.168.1.174\cotabot\COTABOT - DEV\cotabot_dev.db')
    
    # Create 3 test events
    test_events = [
        {
            'title': 'Haftalık Antrenman',
            'description': 'Squad antrenmanı - herkes katılsın!',
            'timestamp': datetime.now() + timedelta(days=2),
            'channel_id': 1234567890,
            'active': True
        },
        {
            'title': 'Turnuva Hazırlığı',
            'description': 'Gelecek haftaki turnuva için hazırlık maçı',
            'timestamp': datetime.now() + timedelta(days=5),
            'channel_id': 1234567890,
            'active': True
        },
        {
            'title': 'Geçmiş Etkinlik',
           'description': 'Tamamlanmış etkinlik örneği',
            'timestamp': datetime.now() - timedelta(days=3),
            'channel_id': 1234567890,
            'active': False
        }
    ]
    
    for event_data in test_events:
        event_id = await db.create_event(
            guild_id=1234567890,
            title=event_data['title'],
            description=event_data['description'],
            timestamp=event_data['timestamp'],
            channel_id=event_data['channel_id'],
            creator_id=0
        )
        print(f"✅ Created event: {event_data['title']} (ID: {event_id})")
    
    # List all events
    events = await db.get_all_events(1234567890)
    print(f"\n📋 Total events in DB: {len(events)}")
    for e in events:
        status = "Aktif" if e.active else "Pasif"
        print(f"  - {e.title} ({status}) - {e.timestamp}")

if __name__ == '__main__':
    asyncio.run(create_test_events())
