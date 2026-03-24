from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.services.selden_section import spect_dens_selden
from app.dependencies import templates
from typing import List, Tuple, Optional, Dict
import io
import os

router = APIRouter(prefix="/analysis", tags=["analysis"])

# In-memory cache for parsed filter files (per-process)
FILTERS_CACHE: Dict[str, object] = {
    # keys: "wl": List[float], "channels": List[List[float]], "ncols": int
}

# Default filters path (Windows)
DEFAULT_FILTERS_PATH = r"C:\dev\DTS_web\datasheets\filters_equator.csv"

# Plotting/filtering defaults
PLOT_MIN_WL = 1020.0  # nm - plot starting wavelength
DEFAULT_LAMBDA0_NM = 1064.4  # nm - default central/reference wavelength

# Physical constants (kept for reference if needed)
E_CHARGE = 1.602176634e-19  # Coulombs


def parse_filters_file_bytes(
    content_bytes: bytes,
) -> Tuple[List[float], List[List[float]]]:
    content = content_bytes.decode("utf-8", errors="replace")
    if content.startswith("\ufeff"):
        content = content.lstrip("\ufeff")

    wl: List[float] = []
    channels: List[List[float]] = []

    stream = io.StringIO(content)
    for raw_line in stream:
        line = raw_line.strip()
        if not line:
            continue
        parts = [
            p.strip() for p in line.replace(";", ",").split(",") if p.strip() != ""
        ]
        if len(parts) < 2:
            continue
        try:
            wl_val = float(parts[0])
        except ValueError:
            continue

        row_vals: List[float] = []
        for token in parts[1:]:
            try:
                row_vals.append(float(token))
            except Exception:
                row_vals.append(float("nan"))

        if not channels:
            channels = [[] for _ in range(len(row_vals))]

        if len(row_vals) < len(channels):
            row_vals += [float("nan")] * (len(channels) - len(row_vals))

        for i, v in enumerate(row_vals[: len(channels)]):
            channels[i].append(v)

        wl.append(wl_val)

    return wl, channels


# ---- cache helpers ----
def set_filters_cache(wl: List[float], channels: List[List[float]]) -> None:
    FILTERS_CACHE.clear()
    FILTERS_CACHE["wl"] = wl
    FILTERS_CACHE["channels"] = channels
    FILTERS_CACHE["ncols"] = len(channels)


def has_filters() -> bool:
    return "wl" in FILTERS_CACHE and isinstance(FILTERS_CACHE.get("wl"), list)


def get_filters() -> Tuple[List[float], List[List[float]]]:
    return FILTERS_CACHE.get("wl", []), FILTERS_CACHE.get("channels", [])


def load_filters_from_path(path: str) -> Tuple[bool, str]:
    """
    Try to read and parse filters file from given path.
    Returns (success, message).
    """
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    try:
        with open(path, "rb") as fh:
            content = fh.read()
        wl, channels = parse_filters_file_bytes(content)
        if not wl or not channels:
            return False, f"No valid data found in file: {path}"
        set_filters_cache(wl, channels)
        return True, f"Loaded {len(wl)} points, {len(channels)} channel(s)"
    except Exception as exc:
        return False, f"Error loading file {path}: {exc}"


# ---- routes ----
@router.get("/", response_class=HTMLResponse)
async def analysis_page(request: Request):
    """
    Render analysis page (upload + plotting UI).
    On GET attempt to load DEFAULT_FILTERS_PATH if cache empty.
    """
    default_loaded = False
    default_msg = ""
    if not has_filters():
        success, msg = load_filters_from_path(DEFAULT_FILTERS_PATH)
        default_loaded = success
        default_msg = msg

    context = {
        "request": request,
        "has_filters": has_filters(),
        "wl_count": len(FILTERS_CACHE.get("wl", [])),
        "channels": FILTERS_CACHE.get("ncols", 0),
        "default_loaded": default_loaded,
        "default_msg": default_msg,
        "default_path": DEFAULT_FILTERS_PATH,
        "default_lambda0": DEFAULT_LAMBDA0_NM,
        "plot_min_wl": PLOT_MIN_WL,
    }
    return templates.TemplateResponse("analysis.html", context)


@router.post("/load_default")
async def load_default():
    """
    Explicitly (re)load default filters file from DEFAULT_FILTERS_PATH.
    """
    success, msg = load_filters_from_path(DEFAULT_FILTERS_PATH)
    if not success:
        return JSONResponse({"ok": False, "error": msg}, status_code=400)
    return {
        "ok": True,
        "wl_count": len(FILTERS_CACHE.get("wl", [])),
        "channels": FILTERS_CACHE.get("ncols", 0),
        "msg": msg,
    }


@router.post("/upload_filters")
async def upload_filters(file: UploadFile = File(...)):
    try:
        content = await file.read()
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": f"Failed to read uploaded file: {exc}"},
            status_code=400,
        )

    try:
        wl, channels = parse_filters_file_bytes(content)
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": f"Parsing error: {exc}"}, status_code=422
        )

    if not wl or not channels:
        return JSONResponse(
            {"ok": False, "error": "No valid data found in uploaded file"},
            status_code=422,
        )

    set_filters_cache(wl, channels)
    return {"ok": True, "wl_count": len(wl), "channels": len(channels)}


@router.post("/plot_section")
async def plot_section(
    te_eV: float = Form(...),
    theta_deg: float = Form(90.0),
    lambda_0_nm: Optional[float] = Form(None),
):
    if not has_filters():
        return JSONResponse(
            {"ok": False, "error": "No filters uploaded"}, status_code=400
        )

    wl, channels = get_filters()

    try:
        if lambda_0_nm is None:
            lambda_0 = float(DEFAULT_LAMBDA0_NM)
        else:
            lambda_0 = float(lambda_0_nm)
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": f"Invalid lambda_0 value: {exc}"}, status_code=400
        )

    try:
        te_val = float(te_eV)
    except Exception:
        return JSONResponse(
            {"ok": False, "error": "Invalid T_e value"}, status_code=400
        )

    try:
        densities = spect_dens_selden(
            temperature=te_val,
            wl_grid_nm=wl,
            theta_deg=float(theta_deg),
            lambda_0_nm=lambda_0,
        )
    except TypeError:
        try:
            densities = spect_dens_selden(te_val, wl, float(theta_deg), lambda_0)
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": f"Error computing spectral density: {exc}"},
                status_code=500,
            )
    except Exception as exc:
        return JSONResponse(
            {"ok": False, "error": f"Error computing spectral density: {exc}"},
            status_code=500,
        )

    indices = [i for i, w in enumerate(wl) if w >= PLOT_MIN_WL]
    if not indices:
        return JSONResponse(
            {
                "ok": False,
                "error": f"No wavelengths >= {PLOT_MIN_WL} nm in uploaded data",
            },
            status_code=400,
        )

    wl_filtered = [wl[i] for i in indices]
    density_filtered = [densities[i] for i in indices]

    filters_to_send: List[List[float]] = []

    for i in range(min(2, len(channels))):
        ch = channels[i]
        filters_to_send.append([ch[j] for j in indices])

    return {
        "ok": True,
        "wl": wl_filtered,
        "density": density_filtered,
        "filters": filters_to_send,
        "lambda_0_nm": lambda_0,
        "plot_min_wl": PLOT_MIN_WL,
    }


@router.post("/clear_filters")
async def clear_filters():
    FILTERS_CACHE.clear()
    return {"ok": True}
