"""Application configuration via environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AIVOA Pharma Complaint System"
    app_version: str = "1.0.0"
    debug: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/complaint_system"

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    groq_heavy_model: str = "llama-3.3-70b-versatile"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
