from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from app.dependencies import templates
from app.services.file_manager import save_config_files, save_msg_files, clear_configs
from app.services.config_state import STATUS, CONFIG_DATA

router = APIRouter(prefix="/status", tags=["status"])


@router.get("/", response_class=HTMLResponse)
async def status_page(request: Request):
    return templates.TemplateResponse(
        "status.html", {"request": request, "status": STATUS}
    )


@router.post("/upload_config")
async def upload_config(
    absolut_calib: UploadFile | None = None,
    spectral_calib: UploadFile | None = None,
    fe_expected: UploadFile | None = None,
    connections_json: UploadFile | None = None,
):
    files = {
        "absolut_calib": absolut_calib,
        "spectral_calib": spectral_calib,
        "fe_expected": fe_expected,
        "connections_json": connections_json,
    }
    await save_config_files(files)
    return RedirectResponse(url="/status", status_code=303)


@router.post("/upload_msgs")
async def upload_msgs(msg_files: list[UploadFile] | None = File(None)):
    if msg_files:
        await save_msg_files(msg_files)
    return RedirectResponse(url="/status", status_code=303)


@router.post("/clear_configs")
async def clear_configs_endpoint():
    clear_configs()
    return RedirectResponse(url="/status", status_code=303)


@router.post("/run_compute")
async def run_compute():
    STATUS["processing"] = True
    STATUS["processing"] = False
    STATUS["ready"] = True
    return RedirectResponse(url="/status", status_code=303)
