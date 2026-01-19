
import os
import sys
from sqlalchemy import create_engine, text

def reset_tables():
    print("Resetting Training Tables...")
    try:
        engine = create_engine('sqlite:///cotabot_dev.db')
        with engine.connect() as conn:
            # Drop new table names
            conn.execute(text("DROP TABLE IF EXISTS training_match_players"))
            conn.execute(text("DROP TABLE IF EXISTS training_matches"))
            
            # Drop old/legacy table names just in case
            conn.execute(text("DROP TABLE IF EXISTS training_players"))
            
            print("Dropped tables: training_match_players, training_matches, training_players")
    except Exception as e:
        print(f"Error resetting tables: {e}")

if __name__ == "__main__":
    reset_tables()
