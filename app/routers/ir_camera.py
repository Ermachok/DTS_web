from fastapi import APIRouter, Request, UploadFile, File, Form, Query
from fastapi.responses import RedirectResponse, JSONResponse
from app.dependencies import templates
from app.services.ir_camera_handler import (
    load_txt_matrix,
    extract_times,
    extract_radii,
    slice_T,
)
import os
import numpy as np

router = APIRouter(prefix="/ir_camera", tags=["ir_camera"])

UPLOAD_DIR = "uploads/ir_camera"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/", name="ir_camera.index")
async def ir_camera_index(request: Request, filename: str = Query(None)):
    times = []
    status = ""

    if filename:
        path = os.path.join(UPLOAD_DIR, filename)

        if os.path.exists(path):
            try:
                M = load_txt_matrix(path)
                times = extract_times(M)
                status = f"Файл {filename} загружен ({len(times)} точек времени)"
            except Exception as e:
                status = f"Ошибка чтения файла: {e}"
        else:
            status = "Файл не найден"

    return templates.TemplateResponse(
        "ir_camera.html",
        {
            "request": request,
            "filename": filename or "",
            "times": times,
            "status": status,
        },
    )


@router.post("/upload", name="ir_camera.upload")
async def ir_camera_upload(file: UploadFile = File(...)):
    if not (file.filename.lower().endswith(".txt")):
        return RedirectResponse(url="/ir_camera", status_code=303)

    dst = os.path.join(UPLOAD_DIR, file.filename)
    with open(dst, "wb") as f:
        f.write(await file.read())

    return RedirectResponse(url=f"/ir_camera?filename={file.filename}", status_code=303)


@router.get("/data", name="ir_camera.data")
async def ir_camera_data(filename: str = Query(...), time_ms: float = Query(...)):
    path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(path):
        return JSONResponse({"error": "file not found"}, status_code=404)

    try:
        M = load_txt_matrix(path)

        times = extract_times(M)
        R = extract_radii(M)

        # nearest time index
        idx = int(np.argmin(abs(np.array(times) - time_ms)))
        T = slice_T(M, idx)

        return {"requested_time": round(times[idx], 1), "R": R, "T": T}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
