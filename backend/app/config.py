from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    database_url: str = "sqlite+aiosqlite:///./toolloop.db"
    frontend_origin: str = "http://localhost:5173"

    # Opcional: si no se configura, `buscar_web` devuelve resultados mockeados.
    tavily_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
