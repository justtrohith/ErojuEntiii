import json
import re
from functools import lru_cache
from typing import Any

from google import genai

from app.config import get_settings
from app.models.meal_params import MealParams, MealRecommendation


@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    return genai.Client(api_key=settings.gemini_api_key)


def _build_prompt(params: MealParams) -> str:
    lines = [
        "You are a helpful meal planner. Suggest ONE specific meal that fits the constraints.",
        "Respond with JSON only, no markdown fences, using this schema:",
        "{",
        '  "name": "meal name",',
        '  "description": "one sentence",',
        '  "ingredients": ["item1", "item2"],',
        '  "steps": ["step1", "step2"],',
        '  "macros_estimate": {"calories": 450, "protein_g": 30, "carbs_g": 40, "fat_g": 15},',
        '  "time_minutes": 25,',
        '  "uses_pantry": ["items from pantry used"]',
        "}",
        "",
        f"Meal type: {params.meal_type.value}",
    ]

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


def generate_meal(params: MealParams) -> MealRecommendation:
    settings = get_settings()
    client = _get_client()
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=_build_prompt(params),
    )
    raw = response.text or ""
    data = _extract_json(raw)
    return MealRecommendation.model_validate(data)
