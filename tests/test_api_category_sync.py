import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, Category, sync_categories
from src.api import prewarm_cache
from src.models import CategoryData

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api_sync.db"
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

@patch("src.api.SessionLocal")
@patch("src.api_client.TaskAPIClient")
@patch("src.api_client.get_cached_categories")
@patch("src.api_client.get_enriched_categories")
@pytest.mark.asyncio
async def test_category_sync_during_prewarm(mock_get_enriched, mock_get_cached, mock_client_class, mock_session_local, db_session):
    # Setup mocks
    mock_get_enriched.return_value = None
    mock_get_cached.return_value = None
    
    # Mock database session used by prewarm_cache
    mock_session_local.return_value = db_session
    
    # Mock API client response
    mock_client = AsyncMock()
    mock_client_class.return_value = mock_client
    
    mock_categories = [
        CategoryData(CategoryId=1, CategoryName="Category One"),
        CategoryData(CategoryId=2, CategoryName="Category Two")
    ]
    mock_client.get_all_categories_with_tasks.return_value = mock_categories
    
    # Run the function
    from src.api import prewarm_cache
    await prewarm_cache()
    
    # Verify categories are in the database
    categories_in_db = db_session.query(Category).all()
    assert len(categories_in_db) == 2
    assert any(c.id == 1 and c.name == "Category One" for c in categories_in_db)
    assert any(c.id == 2 and c.name == "Category Two" for c in categories_in_db)

@pytest.mark.asyncio
async def test_sync_categories_logic_directly(db_session):
    # Test the direct sync_categories utility
    categories_list = [
        {"CategoryId": 10, "CategoryName": "Direct Sync 1"},
        {"CategoryId": 11, "CategoryName": "Direct Sync 2"}
    ]
    
    sync_categories(db_session, categories_list)
    
    # Verify
    assert db_session.query(Category).count() == 2
    cat10 = db_session.query(Category).filter(Category.id == 10).first()
    assert cat10.name == "Direct Sync 1"
    
    # Test update existing category
    categories_list[0]["CategoryName"] = "Updated Name"
    sync_categories(db_session, categories_list)
    
    db_session.expire_all()
    cat10_updated = db_session.query(Category).filter(Category.id == 10).first()
    assert cat10_updated.name == "Updated Name"
    assert db_session.query(Category).count() == 2
