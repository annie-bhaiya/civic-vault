import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Civic Vault Backend"
    SERVICE_NAME: str = "OnDeviceCivicVault"
    
    # Storage settings
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "vault_storage"
    DB_NAME: str = "vault_metadata.db"
    
    # Security / CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"

settings = Settings()

# Ensure local vault directory exists
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)