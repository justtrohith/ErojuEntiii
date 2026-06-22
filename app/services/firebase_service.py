from typing import Any, Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.config import get_firebase_credentials_dict, get_settings

_db: Optional[firestore.Client] = None
_initialized = False


def init_firebase() -> None:
    global _initialized
    if _initialized or firebase_admin._apps:
        _initialized = True
        return

    settings = get_settings()
    cred_dict = get_firebase_credentials_dict()
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(
        cred,
        {"projectId": settings.firebase_project_id or cred_dict.get("project_id")},
    )
    _initialized = True


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        init_firebase()
        _db = firestore.client()
    return _db


def _user_ref(user_id: str) -> firestore.DocumentReference:
    return _get_db().collection("users").document(user_id)


def ensure_user(user_id: str, display_name: Optional[str] = None) -> dict[str, Any]:
    ref = _user_ref(user_id)
    doc = ref.get()
    if doc.exists:
        return doc.to_dict() or {}

    data: dict[str, Any] = {
        "user_id": user_id,
        "display_name": display_name,
        "prefs": {"cuisine": None, "region": None, "default_macros": {}},
        "pantry": [],
        "created_at": SERVER_TIMESTAMP,
        "updated_at": SERVER_TIMESTAMP,
    }
    ref.set(data)
    return {**data, "created_at": None, "updated_at": None}


def get_user(user_id: str) -> Optional[dict[str, Any]]:
    doc = _user_ref(user_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def update_pantry(user_id: str, pantry: list[str]) -> list[str]:
    ensure_user(user_id)
    cleaned = [item.strip() for item in pantry if item.strip()]
    _user_ref(user_id).update({"pantry": cleaned, "updated_at": SERVER_TIMESTAMP})
    return cleaned


def update_prefs(
    user_id: str,
    *,
    cuisine: Optional[str] = None,
    region: Optional[str] = None,
) -> dict[str, Any]:
    user = ensure_user(user_id)
    prefs = dict(user.get("prefs") or {})
    if cuisine is not None:
        prefs["cuisine"] = cuisine.strip() or None
    if region is not None:
        prefs["region"] = region.strip() or None
    _user_ref(user_id).update({"prefs": prefs, "updated_at": SERVER_TIMESTAMP})
    return prefs


def save_meal_history(user_id: str, params: dict[str, Any], meal: dict[str, Any]) -> str:
    ensure_user(user_id)
    _, doc_ref = _user_ref(user_id).collection("meals").add(
        {
            "params": params,
            "meal": meal,
            "created_at": SERVER_TIMESTAMP,
        }
    )
    return doc_ref.id


def list_meal_history(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    ensure_user(user_id)
    query = (
        _user_ref(user_id)
        .collection("meals")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    results: list[dict[str, Any]] = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        data["id"] = doc.id
        created_at = data.get("created_at")
        if created_at is not None and hasattr(created_at, "isoformat"):
            data["created_at"] = created_at.isoformat()
        results.append(data)
    return results
