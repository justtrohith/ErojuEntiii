import json
import re
from functools import lru_cache
from typing import Any

from google import genai

from app.config import get_meal_prompt_template, get_settings
from app.models.meal_params import MealParams, MealRecommendation, MealType


@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=settings.gemini_api_key)


def _build_prompt(params: MealParams) -> str:
    lines = [get_meal_prompt_template(), "", f"Meal type: {params.meal_type.value}"]

    if params.cuisine_type:
        lines.append(f"Cuisine: {params.cuisine_type}")
    if params.region:
        lines.append(f"Region: {params.region}")
    if params.weather:
        lines.append(f"Weather: {params.weather}")
    if params.time_available_minutes:
        lines.append(f"Time available (minutes): {params.time_available_minutes}")
    if params.macros:
        macro_parts = []
        for field in ("calories", "protein_g", "carbs_g", "fat_g"):
            value = getattr(params.macros, field)
            if value is not None:
                macro_parts.append(f"{field}={value}")
        if macro_parts:
            lines.append(f"Macro targets: {', '.join(macro_parts)}")
    if params.pantry:
        lines.append(f"Pantry (prefer these): {', '.join(params.pantry)}")
    if params.custom:
        lines.append(f"Additional notes: {params.custom}")
    if params.rejected_meals:
        lines.append(
            "Do NOT suggest these exact dishes (eaten in the last 6 days or rejected this session): "
            + ", ".join(params.rejected_meals)
        )
        lines.append("Suggest a clearly different plate name and recipe.")

    if params.meal_type in (MealType.LUNCH, MealType.DINNER):
        lines.append("Reminder: full plate protein_g must be >= 40 in macros_estimate.")

    lines.append("Keep steps practical and concise.")
    return "\n".join(lines)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("Gemini response did not contain valid JSON.") from None
        return json.loads(match.group())


def _validate_meal(meal: MealRecommendation, params: MealParams) -> None:
    if not meal.components:
        raise ValueError("Meal response must include a non-empty components array.")

    if params.meal_type in (MealType.LUNCH, MealType.DINNER):
        protein = meal.macros_estimate.protein_g
        if protein is None or protein < 40:
            raise ValueError(
                f"Lunch/dinner plate must have protein_g >= 40 (got {protein})."
            )


def generate_meal(params: MealParams) -> MealRecommendation:
    settings = get_settings()
    client = _get_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=_build_prompt(params),
    )
    raw = response.text or ""
    data = _extract_json(raw)
    meal = MealRecommendation.model_validate(data)
    _validate_meal(meal, params)
    return meal
