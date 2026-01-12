"""
Fix existing events in events.json - add reminder_sent field to prevent duplicate notifications
"""
import json

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\events.json'

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        events_data = json.load(f)
    
    # Backup
    with open(filepath + '.backup', 'w', encoding='utf-8') as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)
    
    fixed_count = 0
    
    # Fix each server's events
    for server_id, events in events_data.items():
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict) and 'reminder_sent' not in event:
                    event['reminder_sent'] = True  # Mark as sent to stop notifications
                    fixed_count += 1
                    print(f"Fixed event: {event.get('title', 'Unknown')}")
    
    # Save fixed events
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nSUCCESS: Fixed {fixed_count} events")
    print("All old events now have reminder_sent=True")
    
except Exception as e:
    print(f"ERROR: {e}")
