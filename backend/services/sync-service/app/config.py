"""
Configurações do Sync Service.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Caminho para o .env do backend (diretório pai)
_env_file = Path(__file__).parent.parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Configurações do serviço de sincronização."""

    model_config = SettingsConfigDict(
        env_file=str(_env_file) if _env_file.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Serviço
    service_name: str = "Sync Service"
    service_version: str = "1.0.0"
    debug: bool = False

    # PostgreSQL (destino)
    database_url: str = "postgresql+asyncpg://gasadmin:gasadmin123@postgres:5432/gas_automation"

    # Firebird (origem - sistema legado)
    firebird_host: Optional[str] = None
    firebird_port: int = 3050
    firebird_database: Optional[str] = None
    firebird_user: str = "SYSDBA"
    firebird_password: Optional[str] = None
    firebird_charset: str = "UTF8"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Sincronização
    sync_interval_minutes: int = 15  # Intervalo de sincronização automática
    sync_batch_size: int = 100  # Registros por batch
    sync_enabled: bool = True  # Habilitar sincronização automática

    @property
    def firebird_enabled(self) -> bool:
        return bool(self.firebird_host and self.firebird_database)

    @property
    def firebird_dsn(self) -> str:
        """Retorna DSN de conexão Firebird."""
        if not self.firebird_enabled:
            return ""
        return f"{self.firebird_host}/{self.firebird_port}:{self.firebird_database}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
