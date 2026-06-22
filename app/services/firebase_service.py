from typing import Any, Optional

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import get_firebase_credentials_path

_db: Optional[firestore.Client] = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(get_firebase_credentials_path()))
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db


def _user_ref(telegram_user_id: str) -> firestore.DocumentReference:
    return _get_db().collection("users").document(telegram_user_id)


def ensure_user(telegram_user_id: str, username: Optional[str] = None) -> dict[str, Any]:
    ref = _user_ref(telegram_user_id)
    doc = ref.get()
    if doc.exists:
        return doc.to_dict() or {}

    data: dict[str, Any] = {
        "telegram_user_id": telegram_user_id,
        "username": username,
        "prefs": {"cuisine": None, "region": None, "default_macros": {}},
        "pantry": [],
    }
    ref.set(data)
    return data


def get_user(telegram_user_id: str) -> Optional[dict[str, Any]]:
    doc = _user_ref(telegram_user_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def update_pantry(telegram_user_id: str, pantry: list[str]) -> list[str]:
    ensure_user(telegram_user_id)
    cleaned = [item.strip() for item in pantry if item.strip()]
    _user_ref(telegram_user_id).update({"pantry": cleaned})
    return cleaned


def update_prefs(
    telegram_user_id: str,
    *,
    cuisine: Optional[str] = None,
    region: Optional[str] = None,
) -> dict[str, Any]:
    user = ensure_user(telegram_user_id)
    prefs = dict(user.get("prefs") or {})
    if cuisine is not None:
        prefs["cuisine"] = cuisine
    if region is not None:
        prefs["region"] = region
    _user_ref(telegram_user_id).update({"prefs": prefs})
    return prefs


def save_meal_history(telegram_user_id: str, params: dict[str, Any], meal: dict[str, Any]) -> str:
    ensure_user(telegram_user_id)
    _, doc_ref = _user_ref(telegram_user_id).collection("meals").add(
        {
            "params": params,
            "meal": meal,
        }
    )
    return doc_ref.id
