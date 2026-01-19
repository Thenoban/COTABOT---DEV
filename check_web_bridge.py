import sqlite3
import os

os.chdir(r'\\192.168.1.174\cotabot\COTABOT - DEV')

conn = sqlite3.connect('cotabot_dev.db')
cur = conn.cursor()

print("="*60)
print("WEB-BOT BRIDGE DEBUG")
print("="*60)

# Check web_bot_actions
print("\n1. WEB BOT ACTIONS:")
cur.execute("SELECT COUNT(*) FROM web_bot_actions")
total = cur.fetchone()[0]
print(f"   Total actions: {total}")

cur.execute("SELECT COUNT(*) FROM web_bot_actions WHERE status='pending'")
pending = cur.fetchone()[0]
print(f"   Pending: {pending}")

cur.execute("SELECT COUNT(*) FROM web_bot_actions WHERE status='processed'")
processed = cur.fetchone()[0]
print(f"   Processed: {processed}")

cur.execute("SELECT COUNT(*) FROM web_bot_actions WHERE status='failed'")
failed = cur.fetchone()[0]
print(f"   Failed: {failed}")

# Show recent actions
print("\n2. RECENT ACTIONS (Last 5):")
cur.execute("""
    SELECT id, action_type, status, created_at, processed_at, error_message 
    FROM web_bot_actions 
    ORDER BY created_at DESC 
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"   ID: {row[0]}")
    print(f"     Type: {row[1]}")
    print(f"     Status: {row[2]}")
    print(f"     Created: {row[3]}")
    print(f"     Processed: {row[4]}")
    if row[5]:
        print(f"     Error: {row[5]}")
    print()

# Show recent events
print("3. RECENT EVENTS (Last 3):")
cur.execute("""
    SELECT id, title, channel_id, active, created_at 
    FROM events 
    ORDER BY created_at DESC 
    LIMIT 3
""")
for row in cur.fetchall():
    print(f"   ID: {row[0]}, Title: '{row[1]}', Channel: {row[2]}")
    print(f"     Active: {row[3]}, Created: {row[4]}")
    print()

conn.close()

print("="*60)
print("NEXT STEPS:")
print("="*60)
print("1. Discord bot çalışıyor mu? -> python main.py")
print("2. web_bridge cog yüklendi mi? -> !1web_status")
print("3. Pending action varsa işlenecek (her 10 saniyede)")
print("="*60)
