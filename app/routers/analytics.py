from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse
from app.dependencies import templates
from app.services.file_manager import save_msg_files
from app.services.config_state import CONFIG_DATA, STATUS
from app.services.caen_handler import handle_all_caens
from app.services.poly_factory import built_fibers, calculate_Te_ne
from app.services.plot_factory import make_interactive_plots
from app.services.plots_raw import make_raw_signals_plot

router = APIRouter(prefix="/analytics", tags=["analytics"])

POLYCHROMATORS_CACHE = {}


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


@router.get("/raw_options")
async def get_raw_options():
    """
    Возвращает список доступных полихроматоров и их каналов.
    """
    experiment_data = handle_all_caens()
    combiscope_times = experiment_data["combiscope_times"]
    all_caens = experiment_data["caens_data"]

    config = CONFIG_DATA["connections"]
    expected_fe = CONFIG_DATA["fe_expected"]
    absolut_calibration = CONFIG_DATA["absolut_calib"]
    spectral_calibration = CONFIG_DATA["spectral_calib"]

    combiscope_times, fibers = built_fibers(
        config_connection=config,
        all_caens=all_caens,
        combiscope_times=combiscope_times,
        expected_fe=expected_fe,
        spectral_calib=spectral_calibration,
        absolut_calib=absolut_calibration,
        laser_energy=1.2
    )

    poly_dict = {}
    for p in fibers:
        if not hasattr(p, "poly_name") or not hasattr(p, "signals"):
            continue
        poly_dict[p.poly_name] = list(range(len(p.signals)))
        POLYCHROMATORS_CACHE[p.poly_name] = p

    return JSONResponse(poly_dict)


@router.post("/raw_signals")
async def raw_signals(request: Request,
                      polychromator_name: str = Form(...),
                      channel: int = Form(...),
                      from_shot: int = Form(...),
                      to_shot: str = Form(...)):
    """
    Возвращает HTML-график сырых сигналов выбранного полихроматора и канала.
    """
    poly = POLYCHROMATORS_CACHE.get(polychromator_name)
    if not poly:
        return {"plot_html": f"<p>Полихроматор {polychromator_name} не найден</p>"}

    html = make_raw_signals_plot(poly, channel, from_shot, int(to_shot) if to_shot.isdigit() else to_shot)
    return {"plot_html": html}


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
                                            laser_energy=1.2
                                            )

    calculate_Te_ne(fibers=fibers)
    plots_html = make_interactive_plots(fibers, combiscope_times=combiscope_times)

    STATUS.update({
        "processing": False,
        "ready": True,
        "graphs": plots_html,
    })

    context = {
        "request": request,
        "has_results": True,
        "status": STATUS,
        "graphs": plots_html,
    }
    return templates.TemplateResponse("analytics.html", context)
