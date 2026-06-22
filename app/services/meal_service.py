from app.models.meal_params import MealParams, MealRecommendation
from app.services import ai_agent, firebase_service


def _merge_user_context(params: MealParams) -> MealParams:
    user_id = params.resolved_user_id
    if not user_id:
        return params

    user = firebase_service.get_user(user_id)
    if not user:
        firebase_service.ensure_user(user_id)
        return params

    prefs = user.get("prefs") or {}
    pantry = user.get("pantry") or []

    merged = params.model_copy(deep=True)
    if not merged.cuisine_type and prefs.get("cuisine"):
        merged.cuisine_type = prefs["cuisine"]
    if not merged.region and prefs.get("region"):
        merged.region = prefs["region"]
    if not merged.pantry and pantry:
        merged.pantry = list(pantry)

    recent_names = firebase_service.list_recent_meal_names(user_id, days=6)
    exclude: list[str] = []
    seen: set[str] = set()
    for name in list(merged.rejected_meals) + recent_names:
        key = name.strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        exclude.append(name.strip())
    merged.rejected_meals = exclude

    return merged


def suggest_meal(params: MealParams) -> tuple[MealParams, MealRecommendation]:
    enriched = _merge_user_context(params)
    meal = ai_agent.generate_meal(enriched)
    return enriched, meal


def approve_meal(user_id: str, params: MealParams, meal: MealRecommendation) -> str:
    return firebase_service.save_meal_history(
        user_id,
        params.model_dump(mode="json"),
        meal.model_dump(mode="json"),
    )


def get_meal(params: MealParams, *, persist: bool = False) -> MealRecommendation:
    enriched, meal = suggest_meal(params)
    user_id = params.resolved_user_id
    if persist and user_id:
        approve_meal(user_id, enriched, meal)
    return meal
