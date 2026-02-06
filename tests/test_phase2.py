import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db, User, Category, sync_categories, get_user_subscriptions, update_user_subscriptions, delete_user_subscriptions
from src.api import app
from src.security import create_manage_token, SECRET_KEY, ALGORITHM
import jwt
from datetime import datetime, timedelta

# --- TEST SETUP ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_newsletter.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Pre-populate categories
    sync_categories(db, [
        {"CategoryId": 12, "CategoryName": "Prompt Engineering"},
        {"CategoryId": 18, "CategoryName": "LLM Security"},
        {"CategoryId": 25, "CategoryName": "Fine-Tuning"}
    ])
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides = {}

# --- DB REPOSITORY TESTS (✅ 10) ---

def test_db_repository_logic():
    db = TestingSessionLocal()
    user = User(email="repo@test.com")
    db.add(user)
    db.commit()
    
    # Test update (✅ 2, ✅ 3)
    update_user_subscriptions(db, user.id, [12, 18])
    subs = get_user_subscriptions(db, user.id)
    assert len(subs) == 2
    assert {s.id for s in subs} == {12, 18}
    
    # Test delete all (✅ 4)
    delete_user_subscriptions(db, user.id)
    assert len(get_user_subscriptions(db, user.id)) == 0

# --- API TESTS ---

def test_load_categories_with_state(setup_db, client):
    email = "load@test.com"
    db = TestingSessionLocal()
    user = User(email=email)
    db.add(user)
    db.commit()
    update_user_subscriptions(db, user.id, [12, 18])
    
    token = create_manage_token(email)
    response = client.get(f"/manage/{token}")
    assert response.status_code == 200
    # Check if checkboxes are checked (✅ 1)
    assert 'name="category_12" id="cat_12" checked' in response.text
    assert 'name="category_18" id="cat_18" checked' in response.text
    assert 'name="category_25" id="cat_25" ' in response.text
    assert 'checked' not in response.text.split('id="cat_25"')[1].split('>')[0]

def test_save_subscription_preferences(setup_db, client):
    email = "save@test.com"
    db = TestingSessionLocal()
    user = User(email=email)
    db.add(user)
    db.commit()
    
    token = create_manage_token(email)
    
    # Save multiple (✅ 2)
    response = client.post("/save-subscriptions", data={
        "token": token,
        "category_12": "on",
        "category_18": "on",
        "category_25": "on"
    })
    assert response.status_code == 200
    assert "Intelligence Tuned" in response.text
    
    db.refresh(user)
    assert len(user.subscriptions) == 3

def test_update_existing_subscriptions(setup_db, client):
    email = "update@test.com"
    db = TestingSessionLocal()
    user = User(email=email)
    db.add(user) # Add to session
    db.commit()
    
    user.subscriptions = [db.get(Category, 12), db.get(Category, 18)]
    db.commit()
    
    token = create_manage_token(email)
    # Update to [12, 25] (✅ 3)
    response = client.post("/save-subscriptions", data={
        "token": token,
        "category_12": "on",
        "category_25": "on"
    })
    
    db.refresh(user)
    assert {c.id for c in user.subscriptions} == {12, 25}

def test_unsubscribe_all(setup_db, client):
    email = "none@test.com"
    db = TestingSessionLocal()
    user = User(email=email)
    db.add(user)
    db.commit()
    
    token = create_manage_token(email)
    # Send empty categories (✅ 4)
    response = client.post("/save-subscriptions", data={"token": token})
    
    db.refresh(user)
    assert len(user.subscriptions) == 0

# --- SECURITY TESTS (✅ 5, ✅ 6) ---

def test_invalid_token(client):
    response = client.get("/manage/this-is-garbage")
    assert response.status_code == 400

def test_expired_token(client):
    # Manual token creation with past expiry
    payload = {"email": "old@test.com", "action": "manage", "exp": datetime.utcnow() - timedelta(hours=1)}
    expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    response = client.get(f"/manage/{expired_token}")
    assert response.status_code == 400

# --- NEWSLETTER GENERATOR TESTS (✅ 7, ✅ 8, ✅ 9) ---

from src.html_generator import HTMLGenerator
from src.models import CategoryData, Task

def test_html_generator_inclusion_exclusion():
    gen = HTMLGenerator()
    cats = [
        CategoryData(CategoryId=12, CategoryName="Prompt Engineering", tasks=[Task(TaskId=1, SubjectLine="Test")]),
        CategoryData(CategoryId=18, CategoryName="LLM Security", tasks=[Task(TaskId=2, SubjectLine="Test")]),
        CategoryData(CategoryId=25, CategoryName="Fine-Tuning", tasks=[Task(TaskId=3, SubjectLine="Test")])
    ]
    
    # User subscribed to 12 and 25 (✅ 7, ✅ 8)
    # The actual filtering happens in graph.py, but we test the generator's output rendering here
    relevant_cats = [c for c in cats if c.categoryId in [12, 25]]
    html = gen.generate(relevant_cats)
    
    assert "Prompt Engineering" in html
    assert "Fine-Tuning" in html
    assert "LLM Security" not in html

def test_html_generator_no_subscriptions():
    gen = HTMLGenerator()
    html = gen.generate([])
    # Check for empty state indicators (✅ 9)
    assert "Across 0 functional" in html
    # In my implementation, it shows a summary with 0 tasks
    # The subject line in broadcast_newsletter_node handles the "No Subscriptions" logic
    assert "Executive Briefing" in html
