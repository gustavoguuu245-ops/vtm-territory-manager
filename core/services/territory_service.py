from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from core.models.territory import Territory
from core.models.territory_history import TerritoryHistory
from core.models.session_lock import SessionLock
from core.models.region import Region
from core.models.user import User
from config.settings import settings

class TerritoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_territories(self, region_id: int = None, clan: str = None, owner_id: int = None, active_only: bool = True) -> List[Territory]:
        """Lista territórios com filtros."""
        query = self.db.query(Territory)
        if active_only:
            query = query.filter(Territory.is_active == 1)
        if region_id:
            query = query.filter(Territory.region_id == region_id)
        if clan:
            query = query.filter(Territory.controlling_clan == clan)
        if owner_id is not None: # <-- NOVO FILTRO POR ID DO DONO
            query = query.filter(Territory.owner_id == owner_id)
        return query.all()

    def get_territory(self, territory_id: int) -> Optional[Territory]:
        return self.db.query(Territory).filter(Territory.id == territory_id).first()

    def get_regions(self) -> List[Region]:
        return self.db.query(Region).all()

    def get_region_by_name(self, name: str) -> Optional[Region]:
        return self.db.query(Region).filter(Region.name == name).first()

    def acquire_lock(self, territory_id: int, user: User, session_id: str, duration_seconds: int = None) -> Dict[str, Any]:
        if duration_seconds is None:
            duration_seconds = settings.LOCK_TIMEOUT_SECONDS
        
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=duration_seconds)
        
        self.db.query(SessionLock).filter(
            SessionLock.territory_id == territory_id,
            SessionLock.expires_at < now
        ).delete()
        
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
        self.db.query(SessionLock).filter(
            SessionLock.territory_id == territory_id,
            SessionLock.locked_by == user.username
        ).update({"is_active": 0})
        self.db.commit()
        return True

    def release_all_user_locks(self, user: User):
        self.db.query(SessionLock).filter(
            SessionLock.locked_by == user.username
        ).update({"is_active": 0})
        self.db.commit()
    
    def update_territory(self, territory_id: int, user: User, changes: Dict[str, Any], reason: str = None, expected_version: int = None) -> Dict[str, Any]:
        territory = self.get_territory(territory_id)
        if not territory:
            return {"success": False, "error": "Território não encontrado"}
        
        if not user.can_edit_region(territory.region.name if territory.region else ""):
            return {"success": False, "error": "Você não tem permissão para editar esta região"}
        
        if expected_version is not None and territory.version != expected_version:
            return {
                "success": False,
                "error": "Conflito de versão! Outro usuário alterou este território.",
                "current_version": territory.version
            }
        
        snapshot = self._territory_to_dict(territory)
        
        for field, new_value in changes.items():
            if hasattr(territory, field):
                old_value = getattr(territory, field)
                setattr(territory, field, new_value)
                
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
        
        territory.version += 1
        territory.modified_by = user.username
        territory.modified_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(territory)
        self.release_lock(territory_id, user)
        return {"success": True, "territory": territory}

    def create_territory(self, user: User, name: str, region_id: int, latitude: float, longitude: float, controlling_clan: str = "Neutro", geojson_polygon: str = None, map_color: str = "#808080", owner_id: int = None, **kwargs) -> Territory:
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
            owner_id=owner_id, # <-- AGORA O SERVIÇO RECEBE E SALVA O OWNER_ID EXPLICITAMENTE
            **kwargs
        )
        self.db.add(territory)
        self.db.commit()
        self.db.refresh(territory)
        
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

    def delete_territory(self, territory_id: int, user: User, reason: str = None) -> Dict[str, Any]:
        """Remove logicamente um território (soft-delete)."""
        territory = self.get_territory(territory_id)
        if not territory:
            return {"success": False, "error": "Território não encontrado"}
        
        if not user.can_edit_region(territory.region.name if territory.region else ""):
            return {"success": False, "error": "Você não tem permissão para excluir territórios nesta região"}
        
        # Aplica o soft-delete (desativa o território)
        territory.is_active = 0
        territory.modified_by = user.username
        territory.modified_at = datetime.now(timezone.utc)
        
        # Registra a exclusão no histórico
        if settings.ENABLE_AUDIT_LOG:
            history = TerritoryHistory(
                territory_id=territory_id,
                modified_by=user.username,
                modified_by_role=user.role,
                field_changed="DELETED",
                old_value=territory.name,
                new_value=None,
                full_snapshot=self._territory_to_dict(territory),
                change_reason=reason or "Exclusão pelo usuário"
            )
            self.db.add(history)
        
        self.db.commit()
        self.db.refresh(territory)
        self.release_lock(territory_id, user)
        return {"success": True, "message": f"Território '{territory.name}' excluído com sucesso."}

    def get_history(self, territory_id: int = None, limit: int = 100) -> List[TerritoryHistory]:
        query = self.db.query(TerritoryHistory).order_by(TerritoryHistory.changed_at.desc())
        if territory_id:
            query = query.filter(TerritoryHistory.territory_id == territory_id)
        return query.limit(limit).all()

    def _territory_to_dict(self, territory: Territory) -> Dict[str, Any]:
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