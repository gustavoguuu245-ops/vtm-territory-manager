"""Sistema de autenticação e autorização."""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from core.models.user import User
from config.settings import settings

class AuthManager:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    @staticmethod
    def create_token(username: str, role: str, user_id: int) -> str:
        payload = {
            "sub": username,
            "role": role,
            "user_id": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=settings.TOKEN_EXPIRE_HOURS),
            "iat": datetime.now(timezone.utc)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    @classmethod
    def authenticate(cls, db: Session, username: str, password: str) -> Optional[User]:
        user = db.query(User).filter(User.username == username, User.is_active == True).first()
        if user and cls.verify_password(password, user.hashed_password):
            user.last_login = datetime.now(timezone.utc)
            db.commit()
            return user
        return None
    
    @classmethod
    def create_user(cls, db: Session, username: str, password: str, 
                    role: str = "jogador", assigned_region: str = None,
                    clan: str = None, email: str = None) -> User:
        hashed = cls.hash_password(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed,
            role=role,
            assigned_region=assigned_region,
            clan=clan
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @classmethod
    def get_user_by_username(cls, db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()