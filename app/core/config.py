"""
App-wide settings, loaded from environment variables (see .env.example).
Nobody should need to touch this file to add a feature — new config goes
here once, then gets imported wherever it's needed via `settings`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Expense Tracker API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./expense_tracker.db"

    SECRET_KEY: str = "change-this-to-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours, fine for a student project

    # Frontend dev server origins allowed to call this API. Add your deployed
    # frontend URL here too once it exists.
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
