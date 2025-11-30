import copy

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
COMBISCOPE_TIMES_CACHE = None


def _polychromators_list_from_cache():
    """
    Возвращает список словарей [{'name': ..., 'z_cm': ...}, ...] из POLYCHROMATORS_CACHE
    в порядке добавления (если важен порядок — cache строится в порядке fibers).
    """
    lst = []
    for key, p in POLYCHROMATORS_CACHE.items():
        name = getattr(p, "poly_name", key)
        z = getattr(p, "z_cm", None)
        try:
            z_val = float(z) if z is not None else None
        except Exception:
            z_val = None
        lst.append({"name": name, "z_cm": z_val})
    return lst


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
        "polychromators": _polychromators_list_from_cache(),
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
    global COMBISCOPE_TIMES_CACHE
    """
    Возвращает список доступных полихроматоров и их каналов, а также краткую информацию о полихроматорах.
    Формат ответа:
      {
        "channels": { "poly_name": [0,1,2,...], ... },
        "polychromators": [ {"name": "...", "z_cm": 38.6}, ... ]
      }
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
        laser_energy=1.5
    )

    COMBISCOPE_TIMES_CACHE = copy.deepcopy(combiscope_times)
    poly_dict = {}
    # Обновляем кеш полихроматоров
    POLYCHROMATORS_CACHE.clear()
    for p in fibers:
        if not hasattr(p, "poly_name") or not hasattr(p, "signals"):
            continue
        poly_dict[p.poly_name] = list(range(len(p.signals)))
        POLYCHROMATORS_CACHE[p.poly_name] = p

    polychromators_short = _polychromators_list_from_cache()

    return JSONResponse({"channels": poly_dict, "polychromators": polychromators_short})


@router.post("/raw_signals")
async def raw_signals(request: Request,
                      polychromator_name: str = Form(...),
                      from_shot: int = Form(...),
                      to_shot: str = Form(...)):
    """
    Возвращает HTML-график сырых сигналов выбранного полихроматора.
    По умолчанию строит каналы 0 и 1 (один над другим).
    """
    poly = POLYCHROMATORS_CACHE.get(polychromator_name)
    if not poly:
        return {"plot_html": f"<p>Полихроматор {polychromator_name} не найден</p>"}

    # to_shot может быть "all" или число в строке
    to_shot_param = int(to_shot) if to_shot.isdigit() else to_shot

    # Строим каналы 0 и 1
    html = make_raw_signals_plot(poly, channels=[0, 1], from_shot=from_shot, to_shot=to_shot_param,
                                 combiscope_times=COMBISCOPE_TIMES_CACHE)
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
                                            laser_energy=1.5
                                            )

    calculate_Te_ne(fibers=fibers)

    # Обновляем кеш полихроматоров для шаблона
    POLYCHROMATORS_CACHE.clear()
    for p in fibers:
        if not hasattr(p, "poly_name"):
            continue
        POLYCHROMATORS_CACHE[p.poly_name] = p

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
        "polychromators": _polychromators_list_from_cache(),
    }
    return templates.TemplateResponse("analytics.html", context)
