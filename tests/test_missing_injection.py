import asyncio
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, User, Category
from src.graph import broadcast_newsletter_node
from src.models import CategoryData, Task
from unittest.mock import MagicMock, patch

# Setup in-memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.mark.asyncio
async def test_missing_subscription_injection():
    """Verify that if a user is subscribed to Category 7 but API doesn't return it, it's injected."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # 1. Setup DB with Category 7 and a User
    cat7 = Category(id=7, name="ScribeRyte Issues")
    cat2 = Category(id=2, name="Medcode")
    db.add(cat7)
    db.add(cat2)
    user = User(email="user3@scribeemr.com")
    db.add(user)
    db.commit()
    
    # Subscribe user to both
    user.subscriptions = [cat7, cat2]
    db.commit()
    
    # 2. Setup State: API only returns Medcode
    state = {
        "categories": [
            CategoryData(CategoryId=2, CategoryName="Medcode", tasks=[Task(TaskId=1, SubjectLine="T", LastStatusCode="O", TaskPriority="H", AssigneeName="A")])
        ],
        "recipient_email": "user3@scribeemr.com",
        "error": None
    }
    
    # 3. Mock dependencies in graph.py for the node call
    import src.graph
    original_session = src.graph.SessionLocal
    src.graph.SessionLocal = TestingSessionLocal
    
    try:
        with patch("src.html_generator.HTMLGenerator.generate", return_value="<html></html>") as mock_gen:
            with patch("src.email_client.EmailClient.send_newsletter") as mock_email:
                await broadcast_newsletter_node(state)
                
                # Verify that HTMLGenerator.generate was called with BOTH categories
                passed_categories = mock_gen.call_args[0][0]
                
                assert len(passed_categories) == 2
                names = [c.categoryName for c in passed_categories]
                assert "Medcode" in names
                assert "ScribeRyte Issues" in names
                
                print("Success: Category 7 was injected as a placeholder!")
    finally:
        src.graph.SessionLocal = original_session
        Base.metadata.drop_all(bind=engine)
        db.close()

if __name__ == "__main__":
    asyncio.run(test_missing_subscription_injection())
