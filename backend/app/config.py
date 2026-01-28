"""
Configurações da aplicação usando Pydantic Settings.
Carrega variáveis de ambiente automaticamente.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


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
    secret_key: str = Field(..., min_length=32, description="Chave secreta para sessões (mínimo 32 caracteres)")

    # PostgreSQL
    # Obs: no docker-compose o Postgres expõe a porta 5433 no host (5433:5432).
    database_url: str = "postgresql+asyncpg://gasadmin:gasadmin123@localhost:5433/gas_automation"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_conversation_ttl: int = 1800  # 30 minutos em segundos
    redis_socket_connect_timeout: float = 1.0
    redis_socket_timeout: float = 2.0

    # WAHA (WhatsApp HTTP API)
    waha_url: str = "http://localhost:3000"
    waha_api_key: str = "gasautomation123"
    waha_session_name: str = "default"

    # Asaas (Gateway de Pagamento)
    asaas_api_key: str = ""
    asaas_api_url: str = "https://api.asaas.com/v3"
    asaas_webhook_token: Optional[str] = None

    # Sync Service (Firebird Sync Service)
    sync_service_url: str = "http://localhost:8003"

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
    firebird_export_on_delivered: bool = False
    firebird_trade_table: str = "TRADE"
    firebird_trade_item_table: str = "TRADEITEM"
    firebird_trade_estab_id: Optional[int] = None
    firebird_trade_tipomovest_id: Optional[int] = None
    firebird_trade_estlocal_id: Optional[int] = 1
    firebird_trade_bxestoque: Optional[str] = None  # 'S'/'N' ou 1/0 conforme schema
    firebird_trade_bxfinanc: Optional[str] = None   # 'S'/'N' ou 1/0 conforme schema

    # MinIO (Object Storage)
    minio_endpoint: Optional[str] = None
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False

    # Segurança
    cors_origins: List[str] = [
        "http://localhost:3001",
        "http://localhost:3000",
        "http://localhost:3003",
        "http://192.168.10.156:3001",
        "http://192.168.10.156:3003",
        "http://192.168.10.156:8000",
        "http://192.168.10.156",
        # Em produção, adicionar apenas o domínio real:
        # "https://seu-dominio.com.br"
    ]
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # segundos

    # JWT Authentication
    access_token_expire_minutes: int = 30
    jwt_secret_key: str = Field(..., min_length=32, description="Chave secreta para JWT (mínimo 32 caracteres)")
    jwt_algorithm: str = "HS256"
    
    # Métricas
    metrics_token: Optional[str] = Field(None, description="Token para acesso ao endpoint /metrics")

    # Negócio
    default_delivery_time_minutes: int = 40
    supported_bairros: List[str] = [
        "Alto Boqueirão",
        "Boqueirão",
        "Ganchinho",
        "Hauer",
        "Sítio Cercado",
        "Umbará",
        "Xaxim"
    ]

    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        """Valida que CORS não permite todas as origens (wildcard)."""
        if "*" in v:
            raise ValueError(
                "CORS com '*' (wildcard) não é permitido por questões de segurança. "
                "Especifique apenas as origens necessárias no formato: "
                "http://dominio.com ou https://dominio.com"
            )
        
        # Validar formato básico das URLs
        for origin in v:
            if not origin.startswith(('http://', 'https://')):
                raise ValueError(
                    f"Origem CORS inválida: '{origin}'. "
                    f"Deve começar com http:// ou https://"
                )
        
        return v
    
    @field_validator('secret_key', 'jwt_secret_key')
    @classmethod
    def validate_secret_keys(cls, v: str, info) -> str:
        """Valida que chaves de segurança são fortes e não são valores padrão."""
        dangerous_keys = [
            "supersecretkey123changeme",
            "your-jwt-secret-key-change-in-production",
            "changeme",
            "secret",
            "key123",
            "password",
            "admin",
            "test"
        ]
        
        # Verificar se é uma chave padrão/perigosa
        if v.lower() in [k.lower() for k in dangerous_keys]:
            raise ValueError(
                f"{info.field_name} não pode ser uma chave padrão. "
                f"Gere uma nova: openssl rand -hex 32"
            )
        
        # Verificar comprimento mínimo
        if len(v) < 32:
            raise ValueError(
                f"{info.field_name} deve ter no mínimo 32 caracteres. "
                f"Gere uma nova: openssl rand -hex 32"
            )
        
        return v

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
