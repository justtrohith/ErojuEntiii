from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    firebase_credentials_path: str = "./firebase-credentials.json"
    api_host: str = "0.0.0.0"
    api_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_firebase_credentials_path() -> Path:
    path = Path(get_settings().firebase_credentials_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(
            f"Firebase credentials not found at {path}. "
            "Download a service account JSON from Firebase Console and set FIREBASE_CREDENTIALS_PATH."
        )
    return path
