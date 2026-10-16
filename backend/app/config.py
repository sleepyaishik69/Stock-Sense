from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./stocksense.db"
    secret_key: str = "development-only-change-me"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"
    ollama_timeout_seconds: int = 25
    max_upload_mb: int = 15
    cors_origins: str = "http://localhost:3000"


settings = Settings()
