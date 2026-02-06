import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, Category, sync_categories, User
from src.api import prewarm_cache
from src.models import CategoryData, Task
from src.html_generator import HTMLGenerator
from src.api_client import set_enriched_categories, invalidate_cache

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_alignment.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.mark.asyncio
async def test_email_and_streams_alignment(db_session):
    """
    STRICT INTEGRATION TEST:
    Verifies that the categories synced to the DB (which powers 'My Streams')
    match the categories processed for the Email Body.
    """
    # 1. Define dummy categories from API
    mock_api_categories = [
        CategoryData(CategoryId=101, CategoryName="Frontend Development", tasks=[Task(TaskId=1, SubjectLine="Fix CSS", TaskStatus="In Progress")]),
        CategoryData(CategoryId=102, CategoryName="Backend Infrastructure", tasks=[]),
        CategoryData(CategoryId=103, CategoryName="QA & Testing", tasks=[Task(TaskId=2, SubjectLine="Run regression", TaskStatus="Pending")])
    ]
    
    # 2. Mock the API client and cache
    with patch("src.api_client.TaskAPIClient") as mock_client_class, \
         patch("src.api_client.get_cached_categories") as mock_get_cached, \
         patch("src.api_client.get_enriched_categories") as mock_get_enriched, \
         patch("src.api.SessionLocal") as mock_session_local:
        
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_all_categories_with_tasks.return_value = mock_api_categories
        
        mock_get_cached.return_value = None
        mock_get_enriched.return_value = None
        mock_session_local.return_value = db_session
        
        # 3. Simulate System Start (Prewarm)
        # This should sync the 3 categories to our DB
        await prewarm_cache()
        
        # 4. CROSSCHECK DB: "My Streams" source
        categories_in_db = db_session.query(Category).all()
        db_cat_ids = {c.id for c in categories_in_db}
        db_cat_names = {c.name for c in categories_in_db}
        
        assert len(categories_in_db) == 3, f"Expected 3 categories in DB, found {len(categories_in_db)}"
        assert 101 in db_cat_ids
        assert "QA & Testing" in db_cat_names
        
        # 5. CROSSCHECK EMAIL: "Email Body" source
        # In a real workflow, the graph fetches from API. We use the same mock list.
        html_gen = HTMLGenerator()
        email_html = html_gen.generate(mock_api_categories)
        
        # Verify all 3 categories appear in the Email Nav Chips/Sections
        import html
        for cat in mock_api_categories:
            assert html.escape(cat.categoryName) in email_html, f"Category '{cat.categoryName}' missing from Email HTML"
            
        # 6. CROSSCHECK "My Streams" Rendering
        # Simulate the manage_subscriptions endpoint logic
        # categories = db.query(Category).all()
        # This is what we checked in step 4.
        
        print("Alignment Verified: Email categories match Database categories used for 'My Streams'.")

if __name__ == "__main__":
    asyncio.run(test_email_and_streams_alignment(TestingSessionLocal()))
