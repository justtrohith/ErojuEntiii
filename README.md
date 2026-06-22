# ErojuEntiii

Decide what to eat today — web app + Python API backed by Gemini and Firestore.

## Architecture

```text
web/ (Firebase Hosting)  →  Python API (Render / Cloud Run)  →  Firestore + Gemini
```

No auth for now — the web app uses a random `user_id` in `localStorage` to save pantry, prefs, and meal history.

## Prerequisites

1. [Gemini API key](https://aistudio.google.com/apikey)
2. Firebase project **erojuentiii** with Firestore enabled
3. Firebase service account JSON (Project settings → Service accounts)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your Gemini key and Firebase credentials path.

## Run locally

**API:**

```bash
python -m app.main
```

**Web** (separate terminal):

```bash
# Option A: Firebase emulator
firebase emulators:start --only hosting

# Option B: any static server from web/
python -m http.server 5000 --directory web
```

Set `web/js/config.js`:

```javascript
window.APP_CONFIG = { API_BASE: "http://localhost:8000" };
```

Open `http://localhost:5000` (or emulator URL).

## Deploy

### 1. API → Render (or Cloud Run)

**Render:** New Web Service → connect repo → Environment:

- `GEMINI_API_KEY`
- `FIREBASE_CREDENTIALS_JSON` (paste full service account JSON)
- `CORS_ORIGINS=https://erojuentiii.web.app,https://erojuentiii.firebaseapp.com`

**Cloud Run:**

```bash
gcloud run deploy erojuentiii-api --source . --region asia-south1 --allow-unauthenticated
```

### 2. Web → Firebase Hosting

Update `web/js/config.js` with your deployed API URL, then:

```bash
firebase deploy --only hosting,firestore:rules
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /api/get-meal` | Generate meal (`meal_type` required) |
| `GET /api/user?user_id=` | Load profile |
| `PUT /api/user/pantry?user_id=` | Save pantry |
| `PUT /api/user/prefs?user_id=` | Save cuisine / region |
| `GET /api/user/meals?user_id=` | Recent meals |

Legacy routes `GET/POST /get-meal` still work.

## Optional: Telegram bot (dev)

```bash
# Set TELEGRAM_BOT_TOKEN in .env
python -m app.bot.telegram_bot
```

## Project layout

```text
app/           Python API + services
web/           Static frontend (Firebase Hosting)
firebase.json  Hosting + Firestore rules
Dockerfile     Container deploy for API
```

## Firestore structure

```text
users/{user_id}
  prefs: { cuisine, region, default_macros }
  pantry: ["rice", "eggs"]
  meals/{meal_id}
    params, meal, created_at
```
