
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, User, Category, sync_categories, update_user_subscriptions, get_user_subscriptions

# Setup in-memory DB for isolation testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # 1. Preset Categories
    sync_categories(db, [
        {"CategoryId": 1, "CategoryName": "Cat 1"},
        {"CategoryId": 2, "CategoryName": "Cat 2"},
        {"CategoryId": 3, "CategoryName": "Cat 3"},
        {"CategoryId": 4, "CategoryName": "Cat 4"},
        {"CategoryId": 5, "CategoryName": "Cat 5"},
        {"CategoryId": 6, "CategoryName": "Cat 6"},
        {"CategoryId": 7, "CategoryName": "Cat 7"},
    ])
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_user_subscription_isolation(db):
    """
    Verifies that User A's subscription changes do not affect User B.
    """
    # 2. Create Users
    user_a = User(email="userA@example.com", name="User A")
    user_b = User(email="userB@example.com", name="User B")
    db.add(user_a)
    db.add(user_b)
    db.commit()
    
    # 3. Initial Subscriptions
    # User A -> [1, 2, 3]
    # User B -> [4, 5, 6, 7]
    update_user_subscriptions(db, user_a.id, [1, 2, 3])
    update_user_subscriptions(db, user_b.id, [4, 5, 6, 7])
    
    # Verify Initial State
    subs_a = [c.id for c in get_user_subscriptions(db, user_a.id)]
    subs_b = [c.id for c in get_user_subscriptions(db, user_b.id)]
    
    assert sorted(subs_a) == [1, 2, 3]
    assert sorted(subs_b) == [4, 5, 6, 7]
    
    print("\nInitial State Verified:")
    print(f"User A: {subs_a}")
    print(f"User B: {subs_b}")
    
    # 4. Modify User A
    # User A changes to [1, 7] (Unsubscribes from 2, 3; Subscribes to 7)
    print("\nUpdating User A -> [1, 7]...")
    update_user_subscriptions(db, user_a.id, [1, 7])
    
    # 5. Verify User A Update
    subs_a_new = [c.id for c in get_user_subscriptions(db, user_a.id)]
    assert sorted(subs_a_new) == [1, 7]
    print(f"User A New State: {subs_a_new}")
    
    # 6. CRITICAL: Verify User B is UNTOUCHED
    subs_b_new = [c.id for c in get_user_subscriptions(db, user_b.id)]
    assert sorted(subs_b_new) == [4, 5, 6, 7], "User B's subscriptions should not change!"
    print(f"User B State (Should be unchanged): {subs_b_new}")
    
    # 7. Modify User B
    # User B drops everything except 5
    print("\nUpdating User B -> [5]...")
    update_user_subscriptions(db, user_b.id, [5])
    
    # 8. Verify User B Update
    subs_b_final = [c.id for c in get_user_subscriptions(db, user_b.id)]
    assert sorted(subs_b_final) == [5]
    
    # 9. CRITICAL: Verify User A is UNTOUCHED by User B's change
    subs_a_final = [c.id for c in get_user_subscriptions(db, user_a.id)]
    assert sorted(subs_a_final) == [1, 7], "User A's subscriptions should not change!"
    
    print("\nIsolation Test Passed Successfully.")

if __name__ == "__main__":
    # Manually run the test function if executed as a script
    # Setup DB
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    sync_categories(db, [
        {"CategoryId": i, "CategoryName": f"Cat {i}"} for i in range(1, 8)
    ])
    test_user_subscription_isolation(db)
