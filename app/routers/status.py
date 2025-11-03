from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app.services.file_manager import save_files
from app.dependencies import templates

router = APIRouter(prefix="/status", tags=["status"])


@router.get("/", response_class=HTMLResponse)
async def status_page(request: Request):
    status = {
        "msgpk_file": "Not ready",
        "csv_file": "Not ready",
        "json_file": "Not ready",
        "processing": False,
        "ready": False
    }
    return templates.TemplateResponse("status.html", {"request": request, "status": status})


@router.post("/upload")
async def upload_files(request: Request, files: list[UploadFile]):
    status = {
        "msgpk_file": "Not ready",
        "csv_file": "Not ready",
        "json_file": "Not ready",
        "processing": True,
        "ready": False
    }

    saved_files = await save_files(files)

    for file_info in saved_files:
        ext = file_info["extension"]
        filename = file_info["filename"]

        if ext == ".msgpk":
            status["msgpk_file"] = "Downloaded"
        elif ext == ".csv":
            status["csv_file"] = filename
        elif ext == ".json":
            status["json_file"] = filename

    status["processing"] = False
    status["ready"] = True

    return templates.TemplateResponse("status.html", {"request": request, "status": status})
