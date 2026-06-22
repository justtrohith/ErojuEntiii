from app.models.meal_params import MealParams, MealRecommendation
from app.services import ai_agent, firebase_service


def _merge_user_context(params: MealParams) -> MealParams:
    if not params.telegram_user_id:
        return params

    user = firebase_service.get_user(params.telegram_user_id)
    if not user:
        firebase_service.ensure_user(params.telegram_user_id)
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

    return merged


def get_meal(params: MealParams) -> MealRecommendation:
    enriched = _merge_user_context(params)
    meal = ai_agent.generate_meal(enriched)

    if params.telegram_user_id:
        firebase_service.save_meal_history(
            params.telegram_user_id,
            enriched.model_dump(mode="json"),
            meal.model_dump(mode="json"),
        )

    return meal
