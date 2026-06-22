import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_api_port, get_cors_origins, get_settings

app = FastAPI(title="ErojuEntiii", description="Meal recommendation API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


def main() -> None:
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.api_host, port=get_api_port(), reload=False)


if __name__ == "__main__":
    main()
