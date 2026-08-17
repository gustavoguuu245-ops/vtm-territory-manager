import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "VTM Territory Manager"
    # Chave secreta com mais de 32 bytes para atender ao padrão HMAC SHA256 do JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "vtm_super_secret_jwt_key_32bytes_long_minimum_security!")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'vtm_territories.db'}")
    TOKEN_EXPIRE_HOURS: int = 24
    LOCK_TIMEOUT_SECONDS: int = 300
    ENABLE_AUDIT_LOG: bool = True
    DEFAULT_MAP_CENTER: tuple = (-22.9068, -43.1729)
    DEFAULT_MAP_ZOOM: int = 12

    class Config:
        env_file = ".env"

settings = Settings()