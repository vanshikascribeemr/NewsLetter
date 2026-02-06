import jwt
import os
from datetime import datetime, timedelta
from typing import Optional

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-phase-2-must-be-very-long")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

def create_subscription_token(email: str, category_id: int, action: str) -> str:
    """
    Creates a token for subscribe/unsubscribe actions.
    action: 'subscribe' or 'unsubscribe'
    """
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    to_encode = {
        "email": email,
        "category_id": category_id,
        "action": action,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_manage_token(email: str) -> str:
    """
    Creates a token for the unified management page.
    """
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    to_encode = {
        "email": email,
        "action": "manage",
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """
    Verifies the JWT token and returns the payload.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
