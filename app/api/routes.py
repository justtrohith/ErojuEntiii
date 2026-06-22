from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.meal_params import MacroTargets, MealParams, MealRecommendation, MealType
from app.services import meal_service

router = APIRouter()


def _get_meal(params: MealParams) -> MealRecommendation:
    try:
        return meal_service.get_meal(params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Meal generation failed: {exc}") from exc


def _macros_from_query(
    calories: Optional[int],
    protein_g: Optional[float],
    carbs_g: Optional[float],
    fat_g: Optional[float],
) -> Optional[MacroTargets]:
    if all(value is None for value in (calories, protein_g, carbs_g, fat_g)):
        return None
    return MacroTargets(calories=calories, protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/get-meal", response_model=MealRecommendation)
def get_meal_query(
    meal_type: MealType,
    cuisine_type: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    weather: Optional[str] = Query(default=None),
    custom: Optional[str] = Query(default=None),
    time_available_minutes: Optional[int] = Query(default=None),
    telegram_user_id: Optional[str] = Query(default=None),
    pantry: Optional[str] = Query(default=None, description="Comma-separated pantry items"),
    calories: Optional[int] = Query(default=None),
    protein_g: Optional[float] = Query(default=None),
    carbs_g: Optional[float] = Query(default=None),
    fat_g: Optional[float] = Query(default=None),
) -> MealRecommendation:
    params = MealParams(
        meal_type=meal_type,
        cuisine_type=cuisine_type,
        region=region,
        weather=weather,
        custom=custom,
        time_available_minutes=time_available_minutes,
        telegram_user_id=telegram_user_id,
        pantry=pantry,
        macros=_macros_from_query(calories, protein_g, carbs_g, fat_g),
    )
    return _get_meal(params)


@router.post("/get-meal", response_model=MealRecommendation)
def get_meal_body(params: MealParams) -> MealRecommendation:
    return _get_meal(params)
