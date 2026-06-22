from typing import Optional

from pydantic import BaseModel, Field


class UserPrefs(BaseModel):
    cuisine: Optional[str] = None
    region: Optional[str] = None
    default_macros: dict = Field(default_factory=dict)


class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    pantry: list[str] = Field(default_factory=list)
    prefs: UserPrefs = Field(default_factory=UserPrefs)


class PantryUpdate(BaseModel):
    pantry: list[str] = Field(default_factory=list)


class PrefsUpdate(BaseModel):
    cuisine: Optional[str] = None
    region: Optional[str] = None


class MealHistoryItem(BaseModel):
    id: str
    meal: dict
    params: dict
    created_at: Optional[str] = None
