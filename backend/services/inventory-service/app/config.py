"""
Configurações do Inventory Service.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações do serviço de estoque."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Serviço
    service_name: str = "Inventory Service"
    service_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://gasadmin:gasadmin123@postgres:5432/gas_automation"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Alertas
    low_stock_threshold: int = 10  # Alerta quando estoque abaixo
    critical_stock_threshold: int = 5  # Alerta crítico


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
