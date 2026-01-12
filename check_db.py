"""
Simple test - check database tables
"""
import sqlite3

db_path = r'\\192.168.1.174\cotabot\COTABOT - DEV\cotabot_dev.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== DATABASE TABLES ===\n")

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [t[0] for t in cursor.fetchall()]

print(f"Total tables: {len(tables)}\n")

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count} rows")

conn.close()

print("\n=== DONE ===")
