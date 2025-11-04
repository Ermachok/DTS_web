from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from app.dependencies import templates
from app.services.file_manager import save_msg_files
from app.services.config_state import CONFIG_DATA, STATUS
from app.services.caen_handler import handle_all_caens
from app.services.poly_factory import built_fibers, calculate_Te_ne

import matplotlib.pyplot as plt
import io, base64

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """
    Страница загрузки .msg файлов и отображения графиков
    """
    context = {
        "request": request,
        "has_results": STATUS.get("ready", False),
        "status": STATUS,
        "graphs": STATUS.get("graphs", []),
    }
    return templates.TemplateResponse("analytics.html", context)


@router.post("/upload_msgs")
async def upload_msgs(msg_files: list[UploadFile] | None = File(None)):
    """
    Загрузка .msgpk файлов для анализа
    """
    if msg_files:
        await save_msg_files(msg_files)
        CONFIG_DATA["msg_files"] = [f.filename for f in msg_files]
        STATUS["msgpk_count"] = len(msg_files)
        STATUS["ready"] = False

    return RedirectResponse(url="/analytics", status_code=303)


@router.post("/run_compute")
async def run_compute(request: Request):
    """
    Запуск расчёта и построение графиков
    """
    STATUS["processing"] = True

    config = CONFIG_DATA["connections"]
    expected_fe = CONFIG_DATA["fe_expected"]
    absolut_calibration = CONFIG_DATA["absolut_calib"]
    spectral_calibration = CONFIG_DATA["spectral_calib"]

    experiment_data = handle_all_caens()
    all_caens = experiment_data["caens_data"]
    combiscope_times = experiment_data["combiscope_times"]

    combiscope_times, fibers = built_fibers(config_connection=config,
                                            all_caens=all_caens,
                                            combiscope_times=combiscope_times,
                                            expected_fe=expected_fe,
                                            spectral_calib=spectral_calibration,
                                            absolut_calib=absolut_calibration,
                                            )

    print(config)
    print('here')
    calculate_Te_ne(fibers=fibers)



    fig_data = []
    for i in range(4):
        plt.figure(figsize=(6, 3))
        plt.plot([x for x in range(100)], [x * (i + 1) for x in range(100)], label=f"Graph {i + 1}")
        plt.legend()
        plt.title(f"График {i + 1}")
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        fig_data.append(img_b64)
        plt.close()

    STATUS["processing"] = False
    STATUS["ready"] = True
    STATUS["graphs"] = fig_data

    context = {
        "request": request,
        "has_results": True,
        "status": STATUS,
        "graphs": fig_data,
    }
    return templates.TemplateResponse("analytics.html", context)
