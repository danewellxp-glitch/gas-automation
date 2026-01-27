"""
Configurações do Notification Service.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações do serviço de notificações."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Serviço
    service_name: str = "Notification Service"
    service_version: str = "1.0.0"
    debug: bool = False

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Twilio (SMS)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None

    # SendGrid (Email)
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: str = "noreply@gasautomation.local"
    sendgrid_from_name: str = "Gas Automation"

    # WhatsApp (via backend principal)
    backend_url: str = "http://backend:8000"

    @property
    def twilio_enabled(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)

    @property
    def sendgrid_enabled(self) -> bool:
        return bool(self.sendgrid_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
