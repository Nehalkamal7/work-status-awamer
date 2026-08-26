from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(value: str) -> str: return pwd.hash(value)
def verify_password(value: str, hashed: str) -> bool: return pwd.verify(value, hashed)

def create_token(user_id: str, kind: str = "access") -> str:
    s = get_settings(); delta = timedelta(minutes=s.access_token_minutes) if kind == "access" else timedelta(days=s.refresh_token_days)
    return jwt.encode({"sub": user_id, "type": kind, "exp": datetime.now(timezone.utc) + delta}, s.jwt_secret, algorithm=s.jwt_algorithm)

def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        if payload.get("type") != "access": raise JWTError()
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.get(User, payload.get("sub"))
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user

