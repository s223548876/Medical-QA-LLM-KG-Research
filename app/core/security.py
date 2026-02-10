import warnings
from fastapi import Request, HTTPException, status
from core.settings import Settings


def warn_if_api_key_unset(settings: Settings) -> None:
    if not settings.APP_API_KEY:
        warnings.warn("APP_API_KEY is not set; API key check is disabled for local testing.")


def require_api_key(request: Request, settings: Settings) -> None:
    if not settings.APP_API_KEY:
        return
    if request.headers.get("X-API-KEY") != settings.APP_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )
