import os
import unittest
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.database import init_db, SessionLocal, User, Category, get_user_by_email
from src.security import create_manage_token
from fastapi.testclient import TestClient
from src.api import app
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db, User, Category, get_user_by_email

# --- TEST SETUP ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_host_logic.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

class TestHostImpact(unittest.TestCase):
    def setUp(self):
        load_dotenv()
        # Reset dependency overrides and point to test DB
        app.dependency_overrides = {}
        app.dependency_overrides[get_db] = override_get_db
        
        # Create tables in the test DB
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        self.client = TestClient(app)
        
        # In current config: host == sender
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.host_email = os.getenv("HOST_EMAIL")
        self.user_email = "other_user@example.com"
        
        # Ensure categories exist in test DB
        self.c1 = self.db.query(Category).filter(Category.id == 2).first()
        self.c2 = self.db.query(Category).filter(Category.id == 3).first()
        if not self.c1:
            self.c1 = Category(id=2, name="Medcode")
            self.db.add(self.c1)
        if not self.c2:
            self.c2 = Category(id=3, name="Task Master")
            self.db.add(self.c2)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides = {}

    def test_host_access_allowed_even_if_sender(self):
        print("\nTesting host access (when host == sender)...")
        token = create_manage_token(self.host_email)
        response = self.client.get(f"/manage/{token}")
        self.assertEqual(response.status_code, 200)
        print("Host correctly allowed access.")

    def test_other_sender_blocked_if_host_different(self):
        # Temporarily mock a different host to see if sender is blocked
        original_host = os.environ.get("HOST_EMAIL")
        os.environ["HOST_EMAIL"] = "someone_else@example.com"
        
        try:
            print("\nTesting sender block (when sender != host)...")
            token = create_manage_token(self.sender_email)
            response = self.client.get(f"/manage/{token}")
            self.assertEqual(response.status_code, 403)
            print("Sender correctly blocked when not the host.")
        finally:
            if original_host:
                os.environ["HOST_EMAIL"] = original_host
            else:
                del os.environ["HOST_EMAIL"]

    def test_master_filter_logic(self):
        print("\nTesting master filter logic simulation...")
        # 1. Host subscribes to ONLY Category 2 (Medcode)
        host_user = get_user_by_email(self.db, self.host_email)
        host_user.subscriptions = [self.c1]
        self.db.commit()
        
        # 2. Other user subscribes to Category 2 (Medcode) AND Category 3 (Task Master)
        other_user = get_user_by_email(self.db, self.user_email)
        other_user.subscriptions = [self.c1, self.c2]
        self.db.commit()
        
        # 3. Simulate the filter logic from graph.py
        from src.models import CategoryData
        mock_categories = [
            CategoryData(CategoryId=2, CategoryName="Medcode", tasks=[]),
            CategoryData(CategoryId=3, CategoryName="Task Master", tasks=[])
        ]
        
        # Apply Global Filter (Host Influence)
        # We fetch the user again to ensure we have the latest state from DB
        host_user_fresh = self.db.query(User).filter(User.email == self.host_email).first()
        host_sub_ids = [c.id for c in host_user_fresh.subscriptions]
        filtered_categories = [cat for cat in mock_categories if cat.categoryId in host_sub_ids]
        
        print(f"Categories before filter: {[c.categoryName for c in mock_categories]}")
        print(f"Categories after host filter: {[c.categoryName for c in filtered_categories]}")
        
        self.assertEqual(len(filtered_categories), 1)
        self.assertEqual(filtered_categories[0].categoryName, "Medcode")
        
        # 4. Filter for specific user
        other_user_fresh = self.db.query(User).filter(User.email == self.user_email).first()
        other_user_sub_ids = [c.id for c in other_user_fresh.subscriptions]
        user_specific_categories = [cat for cat in filtered_categories if cat.categoryId in other_user_sub_ids]
        
        print(f"Final categories for {self.user_email}: {[c.categoryName for c in user_specific_categories]}")
        self.assertEqual(len(user_specific_categories), 1)
        self.assertEqual(user_specific_categories[0].categoryName, "Medcode")
        print("Master filter logic verified.")

if __name__ == "__main__":
    unittest.main()
