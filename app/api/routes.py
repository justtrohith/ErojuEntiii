from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.meal_params import (
    MacroTargets,
    MealParams,
    MealRecommendation,
    MealSuggestionResponse,
    MealType,
)
from app.models.user import (
    ApproveMealRequest,
    ApproveMealResponse,
    MealHistoryItem,
    PantryUpdate,
    PrefsUpdate,
    UserPrefs,
    UserProfile,
)
from app.services import firebase_service, meal_service

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


def _suggest_meal(params: MealParams) -> MealSuggestionResponse:
    try:
        enriched, meal = meal_service.suggest_meal(params)
        return MealSuggestionResponse(meal=meal, params=enriched)
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


def _user_profile(user_id: str) -> UserProfile:
    user = firebase_service.ensure_user(user_id)
    prefs = user.get("prefs") or {}
    return UserProfile(
        user_id=user_id,
        display_name=user.get("display_name"),
        pantry=user.get("pantry") or [],
        prefs=UserPrefs.model_validate(prefs),
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/user", response_model=UserProfile)
def get_user_profile(user_id: Annotated[str, Query(min_length=1)]) -> UserProfile:
    try:
        return _user_profile(user_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/api/user/pantry", response_model=UserProfile)
def update_user_pantry(user_id: Annotated[str, Query(min_length=1)], body: PantryUpdate) -> UserProfile:
    try:
        firebase_service.update_pantry(user_id, body.pantry)
        return _user_profile(user_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/api/user/prefs", response_model=UserProfile)
def update_user_prefs(user_id: Annotated[str, Query(min_length=1)], body: PrefsUpdate) -> UserProfile:
    try:
        firebase_service.update_prefs(user_id, cuisine=body.cuisine, region=body.region)
        return _user_profile(user_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/user/meals", response_model=list[MealHistoryItem])
def get_user_meals(
    user_id: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[MealHistoryItem]:
    try:
        meals = firebase_service.list_meal_history(user_id, limit=limit)
        return [MealHistoryItem.model_validate(item) for item in meals]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/get-meal", response_model=MealRecommendation)
def get_meal_query(
    meal_type: MealType,
    cuisine_type: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    weather: Optional[str] = Query(default=None),
    custom: Optional[str] = Query(default=None),
    time_available_minutes: Optional[int] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
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
        user_id=user_id,
        telegram_user_id=telegram_user_id,
        pantry=pantry,
        macros=_macros_from_query(calories, protein_g, carbs_g, fat_g),
    )
    return _get_meal(params)


@router.post("/get-meal", response_model=MealRecommendation)
def get_meal_body(params: MealParams) -> MealRecommendation:
    return _get_meal(params)


@router.post("/api/get-meal", response_model=MealSuggestionResponse)
def suggest_meal_body(params: MealParams) -> MealSuggestionResponse:
    return _suggest_meal(params)


@router.post("/api/meals/approve", response_model=ApproveMealResponse)
def approve_meal(body: ApproveMealRequest) -> ApproveMealResponse:
    try:
        meal_id = meal_service.approve_meal(body.user_id, body.params, body.meal)
        return ApproveMealResponse(id=meal_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
