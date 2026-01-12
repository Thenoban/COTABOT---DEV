"""Fix event.py - Add reminder_sent field to prevent duplicate announcements"""

filepath = r'\\192.168.1.174\cotabot\COTABOT - DEV\cogs\event.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find event_data dict and add reminder_sent field
old_event_data = """            event_data = {
                "event_id": new_event_id,
                "message_id": msg.id,
                "channel_id": self.target_channel.id,
                "author_id": interaction.user.id,
                "title": self.event_title.value,
                "timestamp": local_time.isoformat(),
                "end_timestamp": local_end_time.isoformat() if local_end_time else None,
                "description": self.event_desc.value,
                "attendees": [],
                "declined": [],
                "tentative": []
            }"""

new_event_data = """            event_data = {
                "event_id": new_event_id,
                "message_id": msg.id,
                "channel_id": self.target_channel.id,
                "author_id": interaction.user.id,
                "title": self.event_title.value,
                "timestamp": local_time.isoformat(),
                "end_timestamp": local_end_time.isoformat() if local_end_time else None,
                "description": self.event_desc.value,
                "attendees": [],
                "declined": [],
                "tentative": [],
                "reminder_sent": False  # Prevent duplicate reminders on bot restart
            }"""

if old_event_data in content:
    content = content.replace(old_event_data, new_event_data)
    print("SUCCESS: Added reminder_sent field to event creation")
else:
    print("ERROR: event_data dict not found - checking alternatives")

# Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done - Docker restart needed")
