"""
Configurações da aplicação usando Pydantic Settings.
Carrega variáveis de ambiente automaticamente.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações principais da aplicação."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Aplicação
    app_name: str = "Gas Automation API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    secret_key: str = "supersecretkey123changeme"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://gasadmin:gasadmin123@localhost:5432/gas_automation"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_conversation_ttl: int = 1800  # 30 minutos em segundos

    # WAHA (WhatsApp HTTP API)
    waha_url: str = "http://localhost:3000"
    waha_api_key: str = "gasautomation123"
    waha_session_name: str = "default"

    # Asaas (Gateway de Pagamento)
    asaas_api_key: str = ""
    asaas_api_url: str = "https://api.asaas.com/v3"
    asaas_webhook_token: Optional[str] = None

    # Ollama (IA Local)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: int = 30
    ai_confidence_threshold: float = 0.7

    # Firebird (Sistema Legado)
    firebird_host: Optional[str] = None
    firebird_database: Optional[str] = None
    firebird_user: str = "SYSDBA"
    firebird_password: Optional[str] = None
    firebird_charset: str = "UTF8"

    # MinIO (Object Storage)
    minio_endpoint: Optional[str] = None
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False

    # Segurança
    cors_origins: list[str] = [
        "http://localhost:3001",
        "http://localhost:3000",
        "http://localhost:3003",
        "http://192.168.10.156:3001",
        "http://192.168.10.156:3003",
        "http://192.168.10.156:8000",
        "http://192.168.10.156",
        "*"  # Permitir todas as origens durante desenvolvimento
    ]
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # segundos

    # JWT Authentication
    access_token_expire_minutes: int = 30
    jwt_secret_key: str = "your-jwt-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    # Negócio
    default_delivery_time_minutes: int = 40
    supported_bairros: list[str] = [
        "Alto Boqueirão",
        "Boqueirão",
        "Ganchinho",
        "Hauer",
        "Sítio Cercado",
        "Umbará",
        "Xaxim"
    ]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def firebird_enabled(self) -> bool:
        return bool(self.firebird_host and self.firebird_database)


@lru_cache
def get_settings() -> Settings:
    """
    Retorna instância cacheada das configurações.
    Usa lru_cache para evitar recarregar a cada requisição.
    """
    return Settings()


# Instância global para importação direta
settings = get_settings()
