import pytest
import asyncio
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, User, Category
from src.graph import broadcast_newsletter_node
from src.models import CategoryData, Task
import src.graph

# Setup in-memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.mark.asyncio
async def test_new_user_gets_all_categories():
    """Verify that a user with NO subscriptions receives ALL categories."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # 1. Setup New User (No Subs)
    user = User(email="newuser@example.com")
    db.add(user)
    db.commit()
    
    # 2. Setup State: Multiple categories
    all_cats = [
        CategoryData(CategoryId=1, CategoryName="Cat A", tasks=[]),
        CategoryData(CategoryId=2, CategoryName="Cat B", tasks=[]),
        CategoryData(CategoryId=3, CategoryName="Cat C", tasks=[])
    ]
    
    state = {
        "categories": all_cats,
        "recipient_email": "newuser@example.com",
        "error": None
    }
    
    # 3. Mock dependencies
    original_session = src.graph.SessionLocal
    src.graph.SessionLocal = TestingSessionLocal
    
    try:
        with patch("src.html_generator.HTMLGenerator.generate", return_value="<html></html>") as mock_gen:
            with patch("src.email_client.EmailClient.send_newsletter") as mock_email:
                await broadcast_newsletter_node(state)
                
                # Check that ALL 3 categories were passed to generation
                passed_cats = mock_gen.call_args[0][0]
                assert len(passed_cats) == 3
                assert passed_cats == all_cats
                
                print("Success: New user received all 3 categories!")
    finally:
        src.graph.SessionLocal = original_session
        Base.metadata.drop_all(bind=engine)
        db.close()

if __name__ == "__main__":
    asyncio.run(test_new_user_gets_all_categories())
