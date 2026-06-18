from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from core.settings import settings
from core.middleware import setup_cors
from routers.api import router as api_router
from routers.web import router as web_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
setup_cors(app, settings)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(api_router)
app.include_router(web_router)
