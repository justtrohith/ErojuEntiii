# ErojuEntiii

Decide what to eat today — a Telegram bot backed by Gemini and Firebase.

## What it does

- Suggests breakfast, lunch, or dinner based on your preferences
- Uses pantry items, cuisine, and region stored in Firestore
- Saves meal history per Telegram user
- Exposes a REST API at `GET /get-meal` and `POST /get-meal`

## Prerequisites

1. [Telegram Bot Token](https://t.me/BotFather)
2. [Gemini API key](https://aistudio.google.com/apikey)
3. Firebase project with Firestore enabled
4. Firebase service account JSON (Project settings → Service accounts → Generate new private key)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and place your Firebase service account file at the path set in `FIREBASE_CREDENTIALS_PATH`.

## Run the Telegram bot

```bash
python -m app.bot.telegram_bot
```

## Run the API

```bash
python -m app.main
```

Open `http://localhost:8000/docs` for interactive API docs.

### Example API requests

Only `meal_type` is required. Everything else is optional.

```bash
# Minimal
curl "http://localhost:8000/get-meal?meal_type=lunch"

# With optional params
curl "http://localhost:8000/get-meal?meal_type=lunch&cuisine_type=South%20Indian&region=Hyderabad&pantry=rice,dal,tomatoes&custom=light%20meal,%2020%20minutes%20max"
```

```bash
curl -X POST http://localhost:8000/get-meal \
  -H "Content-Type: application/json" \
  -d '{"meal_type": "lunch"}'
```

## Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome and register user |
| `/meal` | Get a meal suggestion |
| `/pantry rice, eggs` | Set pantry items |
| `/setcuisine South Indian` | Save cuisine preference |
| `/setregion Hyderabad` | Save region |
| `/help` | Show help |

## Project layout

```
app/
├── api/routes.py       # FastAPI routes
├── bot/telegram_bot.py # Telegram handlers
├── models/             # Pydantic models
├── services/
│   ├── ai_agent.py     # Gemini integration
│   ├── firebase_service.py
│   └── meal_service.py # Orchestration
├── config.py
└── main.py
```

## Firestore structure

```
users/{telegram_user_id}
  prefs: { cuisine, region, default_macros }
  pantry: ["rice", "eggs"]
  meals/{meal_id}
    params: { ... }
    meal: { ... }
```
