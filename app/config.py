import os
from functools import lru_cache
from pathlib import Path
from typing import Any
import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    meal_prompt: str = ""
    firebase_project_id: str = "erojuentiii"
    firebase_credentials_path: str = "./erojuentiii-firebase-adminsdk-fbsvc-53b519dfe0.json"
    firebase_credentials_json: str = ""
    cors_origins: str = "*"
    api_host: str = "0.0.0.0"
    api_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_api_port() -> int:
    return int(os.getenv("PORT", os.getenv("API_PORT", str(get_settings().api_port))))


def get_cors_origins() -> list[str]:
    raw = get_settings().cors_origins.strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def get_firebase_credentials_dict() -> dict[str, Any]:
    settings = get_settings()
    if settings.firebase_credentials_json.strip():
        return json.loads(settings.firebase_credentials_json)

    path = Path(settings.firebase_credentials_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(
            f"Firebase credentials not found at {path}. "
            "Set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON."
        )
    return json.loads(path.read_text(encoding="utf-8"))


_PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "default_meal_prompt.txt"


def get_meal_prompt_template() -> str:
    prompt = get_settings().meal_prompt.strip()
    if prompt:
        return prompt.replace("\\n", "\n")
    if _PROMPT_FILE.exists():
        return _PROMPT_FILE.read_text(encoding="utf-8").strip()
    raise FileNotFoundError(f"Default meal prompt not found at {_PROMPT_FILE}")
