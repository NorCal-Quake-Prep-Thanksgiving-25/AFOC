"""Configuration helpers for the AFOC project."""

from functools import lru_cache
from os import PathLike, getenv
from pathlib import Path
from typing import IO, Optional

try:  # pragma: no cover - optional dependency
    from pydantic import Field, field_validator  # type: ignore[import-not-found]
    from pydantic_settings import (  # type: ignore[import-not-found]
        BaseSettings,
        SettingsConfigDict,
    )

    _PYDANTIC_AVAILABLE = True
except ImportError:  # pragma: no cover - keep runtime working without pydantic
    from dataclasses import dataclass

    _PYDANTIC_AVAILABLE = False

    def Field(default=None, **_kwargs):  # type: ignore[misc]
        return default

    def field_validator(*_args, **_kwargs):  # type: ignore[misc]
        def decorator(func):
            return func

        return decorator

    class SettingsConfigDict(dict):  # type: ignore[no-redef]
        """Minimal stub so configuration works without pydantic."""

        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    @dataclass
    class BaseSettings:  # type: ignore[no-redef]
        """Fallback settings base when pydantic is unavailable."""

        def model_dump(self) -> dict[str, object]:  # pragma: no cover - compatibility
            return self.__dict__.copy()


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


def _split_tokens(value: object) -> tuple[str, ...]:
    """Normalise token configuration into a tuple."""

    if value is None:
        return ("dev-token",)
    if isinstance(value, str):
        tokens = [token.strip() for token in value.split(",") if token.strip()]
        return tuple(tokens) if tokens else ("dev-token",)
    if isinstance(value, (list, tuple)):
        tokens = [str(token).strip() for token in value if str(token).strip()]
        return tuple(tokens) if tokens else ("dev-token",)
    return ("dev-token",)


if _PYDANTIC_AVAILABLE:

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
        aws_access_key_id: Optional[str] = Field(
            default=None, alias="AWS_ACCESS_KEY_ID"
        )
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
        api_tokens: tuple[str, ...] = Field(default=("dev-token",), alias="API_TOKENS")
        api_rate_limit_per_minute: int = Field(
            default=120, alias="API_RATE_LIMIT", gt=0
        )

        @field_validator("api_tokens", mode="before")
        @classmethod
        def _normalise_tokens(cls, value: object) -> tuple[str, ...]:
            """Split comma-separated tokens into a tuple for authentication checks."""

            return _split_tokens(value)

else:

    class Settings(BaseSettings):  # type: ignore[no-redef]
        """Fallback configuration when pydantic is unavailable."""

        def __init__(self) -> None:
            self.app_name: str = "AFOC"
            self.database_url = getenv(
                "DATABASE_URL", "postgres://afoc:afoc@db:5432/afoc"
            )
            self.aws_access_key_id = getenv("AWS_ACCESS_KEY_ID")
            self.aws_secret_access_key = getenv("AWS_SECRET_ACCESS_KEY")
            self.aws_region = getenv("AWS_DEFAULT_REGION")
            self.stripe_api_key = getenv("STRIPE_API_KEY")
            self.openai_api_key = getenv("OPENAI_API_KEY")
            self.openai_organization = getenv("OPENAI_ORGANIZATION")
            self.openai_project = getenv("OPENAI_PROJECT")
            self.api_tokens = _split_tokens(getenv("API_TOKENS", "dev-token"))
            try:
                rate_limit = int(getenv("API_RATE_LIMIT", "120"))
            except ValueError:
                rate_limit = 120
            self.api_rate_limit_per_minute = max(rate_limit, 1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""

    return Settings()


settings = get_settings()
