# Quick diagnostic script
import sqlite3
import os

os.chdir(r'\\192.168.1.174\cotabot\COTABOT - DEV')

print("=" * 60)
print("COTABOT INTEGRATION DIAGNOSTIC")
print("=" * 60)

# Check DB
conn = sqlite3.connect('cotabot_dev.db')
cur = conn.cursor()

# Check tables exist
print("\n1. CHECKING TABLES...")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cur.fetchall()]
print(f"   ✓ Tables: {', '.join(tables)}")

# Check web_bot_actions
print("\n2. CHECKING ACTION QUEUE...")
cur.execute("SELECT COUNT(*) FROM web_bot_actions")
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM web_bot_actions WHERE status='pending'")
pending = cur.fetchone()[0]
print(f"   Total actions: {total}")
print(f"   Pending: {pending}")

if total > 0:
    cur.execute("SELECT id, action_type, status, created_at FROM web_bot_actions ORDER BY created_at DESC LIMIT 3")
    print("   Recent actions:")
    for row in cur.fetchall():
        print(f"     - ID {row[0]}: {row[1]} ({row[2]}) at {row[3]}")

# Check events
print("\n3. CHECKING EVENTS...")
cur.execute("SELECT COUNT(*) FROM events")
total_events = cur.fetchone()[0]
print(f"   Total events: {total_events}")

if total_events > 0:
    cur.execute("SELECT id, title, active, timestamp FROM events ORDER BY created_at DESC LIMIT 3")
    print("   Recent events:")
    for row in cur.fetchall():
        status = "ACTIVE" if row[2] else "INACTIVE"
        print(f"     - ID {row[0]}: {row[1]} ({status}) at {row[3]}")

# Check cogs
print("\n4. CHECKING BOT FILES...")
cog_files = os.listdir('cogs')
print(f"   Cog files: {len([f for f in cog_files if f.endswith('.py')])} Python files")
if 'web_bridge.py' in cog_files:
    print("   ✓ web_bridge.py EXISTS")
else:
    print("   ✗ web_bridge.py MISSING!")

if 'event.py' in cog_files:
    print("   ✓ event.py EXISTS")
else:
    print("   ✗ event.py MISSING!")

conn.close()

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
