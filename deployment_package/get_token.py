
import sqlite3
from src.security import create_manage_token

def get_token():
    conn = sqlite3.connect("newsletter.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        token = create_manage_token(row[0])
        print(f"TOKEN:{token}")
    else:
        # Fallback if no users exist
        token = create_manage_token("admin@example.com")
        print(f"TOKEN:{token}")

if __name__ == "__main__":
    get_token()
