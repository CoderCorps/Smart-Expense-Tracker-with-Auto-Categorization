"""
App-wide settings, loaded from environment variables (see .env.example).
Nobody should need to touch this file to add a feature — new config goes
here once, then gets imported wherever it's needed via `settings`.
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/, resolved from this file rather than the working directory.
# "sqlite:///./expense_tracker.db" would otherwise point at a different
# file depending on where the process was started — `poe dev` runs from
# backend/, a script run from the repo root doesn't — and the symptom is
# a database that looks empty for no reason.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Expense Tracker API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = f"sqlite:///{BACKEND_DIR / 'expense_tracker.db'}"

    # Where per-user ML categorization models are written. Outside the
    # package so trained models are never mistaken for source, and
    # gitignored so one developer's model can't be committed and then
    # applied to everyone else's transactions.
    ML_MODEL_DIR: str = str(BACKEND_DIR / "ml_models")

    SECRET_KEY: str = "change-this-to-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours, fine for a student project

    # Frontend dev server origins allowed to call this API. Add your deployed
    # frontend URL here too once it exists.
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    @field_validator("DATABASE_URL")
    @classmethod
    def _anchor_sqlite_path(cls, value: str) -> str:
        """
        Resolve a relative SQLite path against backend/, not the cwd.

        The default is already absolute, but .env files in the wild carry
        "sqlite:///./expense_tracker.db" — and that means a different file
        depending on whether the process started in backend/ or the repo
        root. The symptom is a database that looks empty, or a seed script
        that writes somewhere the server never reads.
        """
        prefix = "sqlite:///"

        if not value.startswith(prefix):
            return value

        path = value[len(prefix):]

        # ":memory:" and absolute paths are already unambiguous.
        if path.startswith(":") or Path(path).is_absolute():
            return value

        return f"{prefix}{(BACKEND_DIR / path).resolve()}"

    @field_validator("ML_MODEL_DIR")
    @classmethod
    def _anchor_model_dir(cls, value: str) -> str:
        path = Path(value)
        return str(path if path.is_absolute() else (BACKEND_DIR / path).resolve())

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8"
    )


settings = Settings()
