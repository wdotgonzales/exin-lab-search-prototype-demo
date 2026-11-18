from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = 480
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
