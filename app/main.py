from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from core.settings import settings
from core.middleware import setup_cors
from routers.api import router as api_router
from routers.web import router as web_router

app = FastAPI()
setup_cors(app, settings)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api_router)
app.include_router(web_router)
