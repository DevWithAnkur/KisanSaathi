from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # WhatsApp API
    whatsapp_api_token: str = Field(default="test_token")
    whatsapp_phone_number_id: str = Field(default="test_id")
    whatsapp_verify_token: str = Field(default="test_verify_token")

    # Database
    database_url: str = Field(default="postgresql://kisan:kisan_pass@localhost:5432/kisan_saathi")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # External APIs
    weather_api_key: str = Field(default="test_weather_api_key")
    asr_tts_api_key: str = Field(default="test_asr_tts_api_key")

    # Environment Settings
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Global settings instance
settings = Settings()
