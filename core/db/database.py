from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from core.models.base import Base

# Engine com pool para SQLite (thread-safe) ou PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Cria todas as tabelas se não existirem."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Gerenciador de contexto para sessões do banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''

with open(f"{base}/core/db/database.py", "w", encoding="utf-8") as f:
    f.write(database_py)

session_py = '''"""Gerenciamento de sessões para Streamlit."""
import streamlit as st
from core.db.database import SessionLocal

def get_streamlit_db():
    """Retorna uma sessão de banco para uso no Streamlit.
    
    Usa st.session_state para reusar a mesma sessão
    durante a interação do usuário.
    """
    if "db_session" not in st.session_state:
        st.session_state.db_session = SessionLocal()
    return st.session_state.db_session

def close_streamlit_db():
    """Fecha a sessão do banco no Streamlit."""
    if "db_session" in st.session_state:
        st.session_state.db_session.close()
        del st.session_state.db_session
'''

with open(f"{base}/core/db/session.py", "w", encoding="utf-8") as f:
    f.write(session_py)

# ============================================
# 5. core/auth/authenticator.py
# ============================================
auth_py = '''"""Sistema de autenticação e autorização."""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from core.models.user import User
from config.settings import settings

class AuthManager:
    """Gerencia login, registro e verificação de permissões."""
    
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
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
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
        """Cria um novo usuário."""
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
'''

with open(f"{base}/core/auth/authenticator.py", "w", encoding="utf-8") as f:
    f.write(auth_py)

# ============================================
# 6. core/services/territory_service.py
# ============================================
territory_service = '''"""Serviço de negócio para Territórios com controle de conflitos."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from core.models.territory import Territory
from core.models.territory_history import TerritoryHistory
from core.models.session_lock import SessionLock
from core.models.region import Region
from core.models.user import User
from config.settings import settings

class TerritoryService:
    """Serviço central para operações de território.
    
    Resolve conflitos com:
    1. Optimistic Locking (version field)
    2. Session Locking (trava temporária por território)
    3. Audit Log completo (histórico de todas as alterações)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== LEITURA ==========
    
    def get_territories(self, region_id: int = None, clan: str = None, 
                        active_only: bool = True) -> List[Territory]:
        """Lista territórios com filtros."""
        query = self.db.query(Territory)
        if active_only:
            query = query.filter(Territory.is_active == 1)
        if region_id:
            query = query.filter(Territory.region_id == region_id)
        if clan:
            query = query.filter(Territory.controlling_clan == clan)
        return query.all()
    
    def get_territory(self, territory_id: int) -> Optional[Territory]:
        return self.db.query(Territory).filter(Territory.id == territory_id).first()
    
    def get_regions(self) -> List[Region]:
        return self.db.query(Region).all()
    
    def get_region_by_name(self, name: str) -> Optional[Region]:
        return self.db.query(Region).filter(Region.name == name).first()
    
    # ========== LOCK / UNLOCK ==========
    
    def acquire_lock(self, territory_id: int, user: User, 
                     session_id: str, duration_seconds: int = None) -> Dict[str, Any]:
        """Tenta adquirir um lock de edição para um território.
        
        Retorna {"success": True} se conseguiu,
        {"success": False, "locked_by": "...", "expires_at": ...} se já está travado.
        """
        if duration_seconds is None:
            duration_seconds = settings.LOCK_TIMEOUT_SECONDS
        
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=duration_seconds)
        
        # Limpa locks expirados
        self.db.query(SessionLock).filter(
            SessionLock.territory_id == territory_id,
            SessionLock.expires_at < now
        ).delete()
        
        # Verifica se já existe lock ativo de OUTRO usuário
        existing = self.db.query(SessionLock).filter(
            SessionLock.territory_id == territory_id,
            SessionLock.is_active == 1,
            SessionLock.locked_by != user.username
        ).first()
        
        if existing:
            return {
                "success": False,
                "locked_by": existing.locked_by,
                "expires_at": existing.expires_at,
                "message": f"Território travado por {existing.locked_by} até {existing.expires_at}"
            }
        
        # Se o próprio usuário já tem lock, renova
        own_lock = self.db.query(SessionLock).filter(
            SessionLock.territory_id == territory_id,
            SessionLock.locked_by == user.username,
            SessionLock.is_active == 1
        ).first()
        
        if own_lock:
            own_lock.expires_at = expires
            own_lock.session_id = session_id
        else:
            lock = SessionLock(
                territory_id=territory_id,
                locked_by=user.username,
                locked_by_user_id=user.id,
                expires_at=expires,
                session_id=session_id
            )
            self.db.add(lock)
        
        self.db.commit()
        return {"success": True, "expires_at": expires}
    
    def release_lock(self, territory_id: int, user: User) -> bool:
        """Libera o lock de um território."""
        self.db.query(SessionLock).filter(
            SessionLock.territory_id == territory_id,
            SessionLock.locked_by == user.username
        ).update({"is_active": 0})
        self.db.commit()
        return True
    
    def release_all_user_locks(self, user: User):
        """Libera todos os locks de um usuário (útil no logout)."""
        self.db.query(SessionLock).filter(
            SessionLock.locked_by == user.username
        ).update({"is_active": 0})
        self.db.commit()
    
    # ========== EDIÇÃO COM CONFLITO ==========
    
    def update_territory(self, territory_id: int, user: User, 
                         changes: Dict[str, Any], reason: str = None,
                         expected_version: int = None) -> Dict[str, Any]:
        """Atualiza um território com controle de conflitos.
        
        Args:
            territory_id: ID do território
            user: Usuário que está editando
            changes: Dict com campos a alterar
            reason: Motivo da alteração (para histórico)
            expected_version: Versão esperada (optimistic locking)
        
        Returns:
            {"success": True, "territory": Territory} ou
            {"success": False, "error": "...", "current_version": int}
        """
        territory = self.get_territory(territory_id)
        if not territory:
            return {"success": False, "error": "Território não encontrado"}
        
        # Verifica permissão de região
        if not user.can_edit_region(territory.region.name if territory.region else ""):
            return {"success": False, "error": "Você não tem permissão para editar esta região"}
        
        # Verifica lock (narradores podem bypassar se quiserem, mas recomenda-se usar)
        if user.role == "jogador":
            lock = self.db.query(SessionLock).filter(
                SessionLock.territory_id == territory_id,
                SessionLock.is_active == 1,
                SessionLock.locked_by == user.username
            ).first()
            if not lock:
                return {"success": False, "error": "Você precisa travar o território antes de editar"}
        
        # Optimistic Locking: verifica versão
        if expected_version is not None and territory.version != expected_version:
            return {
                "success": False,
                "error": "Conflito de versão! Outro usuário alterou este território.",
                "current_version": territory.version,
                "message": f"Versão esperada: {expected_version}, versão atual: {territory.version}. Recarregue e tente novamente."
            }
        
        # Aplica as mudanças e registra no histórico
        snapshot = self._territory_to_dict(territory)
        
        for field, new_value in changes.items():
            if hasattr(territory, field):
                old_value = getattr(territory, field)
                setattr(territory, field, new_value)
                
                # Registra no histórico
                if settings.ENABLE_AUDIT_LOG:
                    history = TerritoryHistory(
                        territory_id=territory_id,
                        modified_by=user.username,
                        modified_by_role=user.role,
                        field_changed=field,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None,
                        full_snapshot=snapshot,
                        change_reason=reason
                    )
                    self.db.add(history)
        
        # Incrementa versão (optimistic locking)
        territory.version += 1
        territory.modified_by = user.username
        territory.modified_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(territory)
        
        # Libera o lock após edição
        self.release_lock(territory_id, user)
        
        return {"success": True, "territory": territory}
    
    def create_territory(self, user: User, name: str, region_id: int,
                         latitude: float, longitude: float,
                         controlling_clan: str = "Neutro",
                         geojson_polygon: str = None,
                         map_color: str = "#808080",
                         **kwargs) -> Territory:
        """Cria um novo território."""
        region = self.db.query(Region).filter(Region.id == region_id).first()
        if not region:
            raise ValueError("Região não encontrada")
        
        if not user.can_edit_region(region.name):
            raise PermissionError("Sem permissão para criar territórios nesta região")
        
        territory = Territory(
            name=name,
            region_id=region_id,
            latitude=latitude,
            longitude=longitude,
            controlling_clan=controlling_clan,
            geojson_polygon=geojson_polygon,
            map_color=map_color,
            created_by=user.username,
            modified_by=user.username,
            **kwargs
        )
        self.db.add(territory)
        self.db.commit()
        self.db.refresh(territory)
        
        # Registra criação no histórico
        if settings.ENABLE_AUDIT_LOG:
            history = TerritoryHistory(
                territory_id=territory.id,
                modified_by=user.username,
                modified_by_role=user.role,
                field_changed="CREATED",
                old_value=None,
                new_value=name,
                change_reason="Criação do território"
            )
            self.db.add(history)
            self.db.commit()
        
        return territory
    
    def get_history(self, territory_id: int = None, limit: int = 100) -> List[TerritoryHistory]:
        """Retorna histórico de alterações."""
        query = self.db.query(TerritoryHistory).order_by(TerritoryHistory.changed_at.desc())
        if territory_id:
            query = query.filter(TerritoryHistory.territory_id == territory_id)
        return query.limit(limit).all()
    
    def _territory_to_dict(self, territory: Territory) -> Dict[str, Any]:
        """Converte território em dict para snapshot."""
        return {
            "id": territory.id,
            "name": territory.name,
            "controlling_clan": territory.controlling_clan,
            "region_id": territory.region_id,
            "latitude": territory.latitude,
            "longitude": territory.longitude,
            "influence_level": territory.influence_level,
            "danger_level": territory.danger_level,
            "map_color": territory.map_color,
            "version": territory.version
        }

        


