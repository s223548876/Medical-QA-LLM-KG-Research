from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@router.get("/")
def frontend():
    return FileResponse(STATIC_DIR / "index.html")
