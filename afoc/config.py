"""Configuration helpers for the AFOC project."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseSettings, Field, PostgresDsn

# Load environment variables from a `.env` file if present so the application
# works out of the box during local development.
load_dotenv(dotenv_path=Path(".env"), override=False)


class Settings(BaseSettings):
    """Runtime configuration for database and service settings."""

    app_name: str = "AFOC"
    database_url: PostgresDsn = Field(
        "postgres://afoc:afoc@db:5432/afoc", env="DATABASE_URL"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""

    return Settings()


settings = get_settings()
