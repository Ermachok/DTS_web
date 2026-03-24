from fastapi import APIRouter, Request, UploadFile, File, Form, Query
from fastapi.responses import RedirectResponse, JSONResponse
from app.dependencies import templates
from app.services import separatrix_data_handler as separatrix_service
from app.services.plot_factory import plot_separatrix_to_html
import os

router = APIRouter(prefix="/separatrix", tags=["separatrix"])


@router.get("/", name="separatrix.index")
async def separatrix_index(request: Request, filename: str = Query(None)):
    """
    Страница загрузки и управления separatrix.
    Если передан filename в query, шаблон отобразит слайдер времени и INIT_* переменные для JS.
    """
    times_ms = []
    status = ""
    step = 1
    if filename:
        path = os.path.join(separatrix_service.UPLOAD_DIR, filename)
        if os.path.exists(path):
            try:
                times_ms = separatrix_service.get_available_timestamps_ms(path)
                if times_ms:
                    first = int(times_ms[0])
                    last = int(times_ms[-1])
                    if len(times_ms) > 1:
                        step = max(1, round((last - first) / max(1, len(times_ms) - 1)))
                    else:
                        step = 1
                status = f"Файл {filename} найден ({len(times_ms)} точек)."
            except Exception as e:
                status = f"Ошибка чтения: {e}"
        else:
            status = "Файл не найден на сервере."

    ctx = {
        "request": request,
        "filename": filename or "",
        "times_ms": times_ms,
        "time_step": step,
        "plot_html": "",
        "status": status,
    }
    return templates.TemplateResponse("separatrix.html", ctx)


@router.post("/upload", name="separatrix.upload")
async def upload_separatrix(file: UploadFile = File(...)):
    """
    Сохраняет загруженный JSON и редиректит обратно на страницу с filename в query.
    """
    if not file.filename.lower().endswith(".json"):
        return RedirectResponse(url="/separatrix", status_code=303)

    saved_path = separatrix_service.save_uploaded_file(file, file.filename)
    return RedirectResponse(
        url=f"/separatrix?filename={file.filename}", status_code=303
    )


@router.post("/view", name="separatrix.view")
async def view_separatrix(
    request: Request, filename: str = Form(...), time_ms: float = Form(...)
):
    """
    Генерирует график для выбранного времени и рендерит страницу с plot_html.
    Оставляем для совместимости / серверного построения.
    """
    path = os.path.join(separatrix_service.UPLOAD_DIR, filename)
    if not os.path.exists(path):
        ctx = {
            "request": request,
            "filename": "",
            "times_ms": [],
            "plot_html": "",
            "status": "Файл не найден",
            "time_step": 1,
        }
        return templates.TemplateResponse("separatrix.html", ctx)

    try:
        sep = separatrix_service.get_separatrix_at_time(path, float(time_ms))
        plot_html = plot_separatrix_to_html(sep)
        times_ms = separatrix_service.get_available_timestamps_ms(path)
        if times_ms:
            first = int(times_ms[0])
            last = int(times_ms[-1])
            if len(times_ms) > 1:
                step = max(1, round((last - first) / max(1, len(times_ms) - 1)))
            else:
                step = 1
        else:
            step = 1

        ctx = {
            "request": request,
            "filename": filename,
            "times_ms": times_ms,
            "time_step": step,
            "plot_html": plot_html,
            "status": None,
        }
        return templates.TemplateResponse("separatrix.html", ctx)
    except Exception as e:
        ctx = {
            "request": request,
            "filename": filename,
            "times_ms": [],
            "plot_html": "",
            "status": f"Ошибка: {e}",
            "time_step": 1,
        }
        return templates.TemplateResponse("separatrix.html", ctx)


@router.get("/data", name="separatrix.data")
async def separatrix_data(filename: str = Query(...), time_ms: float = Query(...)):
    """
    Возвращает separatrix в формате JSON для моментального (AJAX) запроса.
    Используется клиентским JS при движении слайдера.
    """
    path = os.path.join(separatrix_service.UPLOAD_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse({"error": "file not found"}, status_code=404)
    try:
        data = separatrix_service.get_separatrix_at_time(path, float(time_ms))
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
