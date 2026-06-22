from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


class MacroTargets(BaseModel):
    model_config = ConfigDict(extra="ignore")

    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None

    @property
    def is_empty(self) -> bool:
        return all(
            value is None for value in (self.calories, self.protein_g, self.carbs_g, self.fat_g)
        )


class MealParams(BaseModel):
    """Only meal_type is required; everything else is optional."""

    model_config = ConfigDict(extra="ignore")

    meal_type: MealType
    cuisine_type: Optional[str] = Field(default=None)
    region: Optional[str] = Field(default=None)
    weather: Optional[str] = Field(default=None)
    macros: Optional[MacroTargets] = Field(default=None)
    pantry: list[str] = Field(default_factory=list)
    custom: Optional[str] = Field(default=None)
    time_available_minutes: Optional[int] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    telegram_user_id: Optional[str] = Field(default=None)
    rejected_meals: list[str] = Field(default_factory=list)

    @property
    def resolved_user_id(self) -> Optional[str]:
        return self.user_id or self.telegram_user_id

    @field_validator("cuisine_type", "region", "weather", "custom", mode="before")
    @classmethod
    def empty_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("pantry", mode="before")
    @classmethod
    def normalize_pantry(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("rejected_meals", mode="before")
    @classmethod
    def normalize_rejected_meals(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("macros", mode="before")
    @classmethod
    def normalize_macros(cls, value: Any) -> Any:
        if value in (None, {}):
            return None
        macros = value if isinstance(value, MacroTargets) else MacroTargets.model_validate(value)
        return None if macros.is_empty else macros


class MealRecommendation(BaseModel):
    name: str
    description: str = ""
    ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    macros_estimate: MacroTargets = Field(default_factory=MacroTargets)
    time_minutes: Optional[int] = None
    uses_pantry: list[str] = Field(default_factory=list)


class MealSuggestionResponse(BaseModel):
    meal: MealRecommendation
    params: MealParams
