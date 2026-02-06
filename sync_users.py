import os
from dotenv import load_dotenv
from src.database import SessionLocal, get_user_by_email

def sync_users():
    load_dotenv()
    recipient_email = os.getenv("RECIPIENT_EMAIL", "")
    emails = [e.strip() for e in recipient_email.split(",") if e.strip()]
    
    db = SessionLocal()
    try:
        print(f"Syncing {len(emails)} users to database...")
        for email in emails:
            user = get_user_by_email(db, email)
            print(f"✔ Verified: {email} (ID: {user.id})")
    finally:
        db.close()

if __name__ == "__main__":
    sync_users()
