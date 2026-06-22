import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import get_settings
from app.models.meal_params import MealParams, MealRecommendation, MealType
from app.services import firebase_service, meal_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

PENDING_MEAL_TYPE = "pending_meal_type"


def _meal_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Breakfast", callback_data="meal:breakfast"),
                InlineKeyboardButton("Lunch", callback_data="meal:lunch"),
                InlineKeyboardButton("Dinner", callback_data="meal:dinner"),
            ]
        ]
    )


def _format_meal(meal: MealRecommendation) -> str:
    macros = meal.macros_estimate
    macro_line = []
    if macros.calories is not None:
        macro_line.append(f"{macros.calories} cal")
    if macros.protein_g is not None:
        macro_line.append(f"{macros.protein_g}g protein")
    if macros.carbs_g is not None:
        macro_line.append(f"{macros.carbs_g}g carbs")
    if macros.fat_g is not None:
        macro_line.append(f"{macros.fat_g}g fat")

    lines = [
        f"*{meal.name}*",
        "",
        meal.description,
        "",
    ]
    if macro_line:
        lines.append(f"Est. macros: {' · '.join(macro_line)}")
    if meal.time_minutes:
        lines.append(f"Time: ~{meal.time_minutes} min")
    if meal.uses_pantry:
        lines.append(f"From your pantry: {', '.join(meal.uses_pantry)}")
    if meal.ingredients:
        lines.extend(["", "*Ingredients*", *[f"• {item}" for item in meal.ingredients]])
    if meal.steps:
        lines.extend(["", "*Steps*", *[f"{i}. {step}" for i, step in enumerate(meal.steps, 1)]])

    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    firebase_service.ensure_user(str(user.id), user.username)
    await update.message.reply_text(
        "Hi! I'm *ErojuEntiii* — I help you decide what to eat today.\n\n"
        "Commands:\n"
        "/meal — get a meal suggestion\n"
        "/pantry rice, eggs, spinach — set pantry items\n"
        "/setcuisine South Indian — save cuisine preference\n"
        "/setregion Hyderabad — save region\n"
        "/help — show commands",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Send /meal and pick breakfast, lunch, or dinner.\n"
            "Add pantry items with /pantry so suggestions use what you have.\n"
            "Set /setcuisine and /setregion once — they'll apply to future meals."
        )


async def pantry_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    raw = " ".join(context.args).strip()
    if not raw:
        stored = firebase_service.get_user(str(user.id)) or {}
        items = stored.get("pantry") or []
        if items:
            await update.message.reply_text(f"Your pantry: {', '.join(items)}")
        else:
            await update.message.reply_text("Usage: /pantry rice, eggs, tomatoes")
        return

    items = [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]
    firebase_service.update_pantry(str(user.id), items)
    await update.message.reply_text(f"Pantry updated: {', '.join(items)}")


async def setcuisine_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    value = " ".join(context.args).strip()
    if not value:
        await update.message.reply_text("Usage: /setcuisine South Indian")
        return

    firebase_service.update_prefs(str(user.id), cuisine=value)
    await update.message.reply_text(f"Cuisine set to: {value}")


async def setregion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    value = " ".join(context.args).strip()
    if not value:
        await update.message.reply_text("Usage: /setregion Hyderabad")
        return

    firebase_service.update_prefs(str(user.id), region=value)
    await update.message.reply_text(f"Region set to: {value}")


async def meal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "What meal are you planning?",
            reply_markup=_meal_type_keyboard(),
        )


async def meal_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not query.data.startswith("meal:"):
        return

    await query.answer()
    meal_type_value = query.data.split(":", 1)[1]
    context.user_data[PENDING_MEAL_TYPE] = meal_type_value

    skip_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Skip", callback_data="notes:skip")]])
    await query.edit_message_text(
        f"Got it — *{meal_type_value}*.\n\n"
        "Send any extra notes (time, macros, mood) or tap Skip.",
        parse_mode="Markdown",
        reply_markup=skip_keyboard,
    )


async def notes_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    await _generate_meal(update, context, custom=None, reply_target=query.message)


async def custom_notes_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get(PENDING_MEAL_TYPE) or not update.message:
        return

    await _generate_meal(update, context, custom=update.message.text)


async def _generate_meal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    custom: str | None,
    reply_target=None,
) -> None:
    user = update.effective_user
    meal_type_value = context.user_data.pop(PENDING_MEAL_TYPE, None)
    if not user or not meal_type_value:
        return

    message = reply_target or update.message
    if not message:
        return

    await message.reply_text("Thinking about what you should eat…")

    params = MealParams(
        meal_type=MealType(meal_type_value),
        custom=custom,
        user_id=str(user.id),
    )

    try:
        meal = await asyncio.to_thread(meal_service.get_meal, params, persist=True)
        await message.reply_text(_format_meal(meal), parse_mode="Markdown")
    except FileNotFoundError as exc:
        await message.reply_text(f"Firebase is not configured: {exc}")
    except Exception as exc:
        logger.exception("Meal generation failed")
        await message.reply_text(f"Sorry, I couldn't generate a meal: {exc}")


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("meal", meal_command))
    app.add_handler(CommandHandler("pantry", pantry_command))
    app.add_handler(CommandHandler("setcuisine", setcuisine_command))
    app.add_handler(CommandHandler("setregion", setregion_command))
    app.add_handler(CallbackQueryHandler(meal_type_chosen, pattern=r"^meal:"))
    app.add_handler(CallbackQueryHandler(notes_skip, pattern=r"^notes:skip$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, custom_notes_message),
    )
    return app


def main() -> None:
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
