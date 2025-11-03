from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from app.services.file_manager import save_file, STATUS
from app.dependencies import templates

router = APIRouter(prefix="/status", tags=["status"])


@router.get("/", response_class=HTMLResponse)
async def status_page(request: Request):
    return templates.TemplateResponse("status.html", {"request": request, "status": STATUS})


@router.post("/upload")
async def upload_file(file: UploadFile):
    await save_file(file)
    return RedirectResponse(url="/status", status_code=303)
