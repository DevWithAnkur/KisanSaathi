from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

from .secrets_manager import get_secrets_manager


def get_secret_or_env(key: str, default: str = "") -> str:
    """
    Get a secret from AWS Secrets Manager, falling back to environment variable,
    then to default.
    """
    # Skip secrets manager in test environment
    if os.getenv("ENVIRONMENT") == "test":
        return os.getenv(key, default)

    secrets = get_secrets_manager()
    value = secrets.get_secret(key.lower().replace("_", "-"))
    if value:
        return value
    return os.getenv(key, default)


class Settings(BaseSettings):
    # WhatsApp API
    whatsapp_api_token: str = Field(
        default_factory=lambda: get_secret_or_env("whatsapp_api_token", "test_token")
    )
    whatsapp_phone_number_id: str = Field(
        default_factory=lambda: get_secret_or_env("whatsapp_phone_number_id", "test_id")
    )
    whatsapp_verify_token: str = Field(
        default_factory=lambda: get_secret_or_env(
            "whatsapp_verify_token", "test_verify_token"
        )
    )

    # Database
    database_url: str = Field(
        default_factory=lambda: get_secret_or_env(
            "database_url", "postgresql://kisan:kisan_pass@localhost:5432/kisan_saathi"
        )
    )

    # Redis
    redis_url: str = Field(
        default_factory=lambda: get_secret_or_env(
            "redis_url", "redis://localhost:6379/0"
        )
    )

    # External APIs
    weather_api_key: str = Field(
        default_factory=lambda: get_secret_or_env(
            "weather_api_key", "test_weather_api_key"
        )
    )
    asr_tts_api_key: str = Field(
        default_factory=lambda: get_secret_or_env(
            "asr_tts_api_key", "test_asr_tts_api_key"
        )
    )

    # Encryption
    encryption_key: str = Field(
        default_factory=lambda: get_secret_or_env(
            "encryption_key", "lR9N4tG8B6y-h0rN4_6wP3wzQc5JpA7bM2mZ_H8V4Xw="
        )
    )

    # Environment Settings
    environment: str = Field(
        default_factory=lambda: get_secret_or_env("environment", "development")
    )
    log_level: str = Field(
        default_factory=lambda: get_secret_or_env("log_level", "INFO")
    )

    # Rate Limiting
    rate_limit_requests: int = Field(
        default_factory=lambda: int(get_secret_or_env("rate_limit_requests", "10")),
        description="Max requests per window",
    )
    rate_limit_window_secs: int = Field(
        default_factory=lambda: int(get_secret_or_env("rate_limit_window_secs", "60")),
        description="Rate limit window in seconds",
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )


# Global settings instance
settings = Settings()
