from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.settings import Settings
from core.security import warn_if_api_key_unset


def setup_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.FRONTEND_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-KEY"],
    )
    warn_if_api_key_unset(settings)
