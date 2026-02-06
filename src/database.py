from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import os
from typing import List

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./newsletter.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Association table for User-Category mapping (Many-to-Many)
subscription_table = Table(
    "subscriptions",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("category_id", Integer, ForeignKey("categories.id")),
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    subscriptions = relationship("Category", secondary=subscription_table, back_populates="subscribers")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)  # Use the API's CategoryId
    name = Column(String)
    subscribers = relationship("User", secondary=subscription_table, back_populates="subscriptions")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_email(db: SessionLocal, email: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def sync_categories(db: SessionLocal, categories_list: List[dict]):
    for cat_data in categories_list:
        cat_id = cat_data.get("TaskCategoryId") or cat_data.get("CategoryId")
        cat_name = cat_data.get("TaskCategoryName") or cat_data.get("CategoryName")
        
        category = db.query(Category).filter(Category.id == cat_id).first()
        if not category:
            category = Category(id=cat_id, name=cat_name)
            db.add(category)
        else:
            category.name = cat_name
    db.commit()

def get_user_subscriptions(db: SessionLocal, user_id: int) -> List[Category]:
    user = db.query(User).filter(User.id == user_id).first()
    return user.subscriptions if user else []

def update_user_subscriptions(db: SessionLocal, user_id: int, category_ids: List[int]):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return
    
    # Fetch categories matching the IDs
    categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
    user.subscriptions = categories
    db.commit()

def delete_user_subscriptions(db: SessionLocal, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.subscriptions = []
        db.commit()
