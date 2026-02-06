import asyncio
import os
from dotenv import load_dotenv
from src.graph import create_newsletter_graph
from src.database import init_db, SessionLocal, User, Category, sync_categories
import structlog

# Set TEST_MODE to true to use dummy data in api_client.py
os.environ["TEST_MODE"] = "true"

async def run_dummy_newsletter():
    load_dotenv()
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()]
    )
    
    # Initialize DB and create a dummy user with subscriptions
    init_db()
    db = SessionLocal()
    
    recipient_email = "vanshikauttarwar14@gmail.com" 
    host_email = "vanshikascribeemr@gmail.com"
    
    # 1. Ensure user exists
    user = db.query(User).filter(User.email == recipient_email).first()
    if not user:
        user = User(email=recipient_email)
        db.add(user)
    
    host = db.query(User).filter(User.email == host_email).first()
    if not host:
        host = User(email=host_email)
        db.add(host)
    db.commit()
    
    # 2. Sync dummy categories to DB
    dummy_categories = [
        {"CategoryId": 7, "CategoryName": "ScribeRyte Issues"},
        {"CategoryId": 12, "CategoryName": "Bug Fixes"},
        {"CategoryId": 15, "CategoryName": "Feature Requests"},
        {"CategoryId": 1022, "CategoryName": "ScribeRyte-related tasks"},
    ]
    sync_categories(db, dummy_categories)
    
    # 3. Subscribe both users to all dummy categories (to bypass master filter)
    all_cats = db.query(Category).all()
    user.subscriptions = all_cats
    # Ensure Host has NO subscriptions to verify the filter is truly gone
    # If the filter was active, the user would receive NOTHING.
    # Since it's removed, the user should receive ALL categories.
    host.subscriptions = []
    db.commit()
    db.close()
    
    print(f"START: Initialized dummy user {recipient_email} and host {host_email} with {len(all_cats)} subscriptions.")
    
    # 4. Run the graph
    app = create_newsletter_graph()
    initial_state = {
        "categories": [],
        "newsletter": None,
        "recipient_email": recipient_email,
        "error": None
    }
    
    print("Generating and sending dummy newsletter...")
    await app.ainvoke(initial_state)
    print("DONE: Dummy newsletter sent successfully!")

if __name__ == "__main__":
    asyncio.run(run_dummy_newsletter())
