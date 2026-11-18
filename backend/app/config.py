from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = 480
    cookie_secure: bool = False

    # File storage: "local" on laptops and in tests, "s3" in production
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "storage"
    aws_s3_bucket: str | None = None
    aws_region: str = "ap-southeast-1"

    # Upload limits
    max_file_mb: int = 25
    max_files_per_upload: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
