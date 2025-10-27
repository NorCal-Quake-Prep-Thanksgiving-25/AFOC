"""Configuration helpers for the AFOC project."""

from functools import lru_cache
from os import PathLike
from pathlib import Path
from typing import IO, Optional

from pydantic import Field  # type: ignore[import-not-found]
from pydantic_settings import (  # type: ignore[import-not-found]
    BaseSettings,
    SettingsConfigDict,
)

try:  # pragma: no cover - optional dependency for local overrides
    from dotenv import load_dotenv  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - keep runtime working without dotenv

    def load_dotenv(  # type: ignore[override]
        dotenv_path: str | PathLike[str] | None = None,
        stream: IO[str] | None = None,
        verbose: bool = False,
        override: bool = False,
        interpolate: bool = True,
        encoding: str | None = None,
    ) -> bool:
        """Fallback no-op when python-dotenv is not installed."""

        return False


# Load environment variables from a `.env` file if present so the application
# works out of the box during local development without leaking production
# secrets into source control.
load_dotenv(dotenv_path=Path(".env"), override=False)


class Settings(BaseSettings):
    """Runtime configuration for database and service settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AFOC"
    database_url: str = Field(
        default="postgres://afoc:afoc@db:5432/afoc", alias="DATABASE_URL"
    )
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(
        default=None, alias="AWS_SECRET_ACCESS_KEY"
    )
    aws_region: Optional[str] = Field(default=None, alias="AWS_DEFAULT_REGION")
    stripe_api_key: Optional[str] = Field(default=None, alias="STRIPE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_organization: Optional[str] = Field(
        default=None, alias="OPENAI_ORGANIZATION"
    )
    openai_project: Optional[str] = Field(default=None, alias="OPENAI_PROJECT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""

    return Settings()


settings = get_settings()
