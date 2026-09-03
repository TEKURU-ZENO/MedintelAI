from app.core.database import engine
from sqlalchemy import text

def add_columns():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN user_streak INTEGER DEFAULT 0;"))
            print("Added user_streak column.")
        except Exception as e:
            print(f"user_streak column might already exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_active_date DATE;"))
            print("Added last_active_date column.")
        except Exception as e:
            print(f"last_active_date column might already exist: {e}")

if __name__ == "__main__":
    add_columns()
