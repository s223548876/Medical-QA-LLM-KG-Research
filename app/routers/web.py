import os
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/")
def frontend():
    return FileResponse(os.path.join("static", "index.html"))
