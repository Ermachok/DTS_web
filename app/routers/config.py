from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.dependencies import templates
from app.services.config_manager import (
    load_ini_config,
    save_ini_config,
    load_json_config,
    save_json_config,
)
from pathlib import Path
import json

router = APIRouter(prefix="/config", tags=["config"])

INI_PATH = "config/paths.ini"
JSON_PATH = "config/connections.json"


@router.get("/", response_class=HTMLResponse)
async def config_main(request: Request):
    ini_data = load_ini_config(INI_PATH)
    json_data = load_json_config(JSON_PATH)
    return templates.TemplateResponse(
        "config.html",
        {"request": request, "ini_data": ini_data, "json_data": json_data},
    )


@router.post("/update_ini")
async def update_ini(
    section: str = Form(...),
    key: str = Form(...),
    value: str = Form(...),
):
    ini_data = load_ini_config(INI_PATH)
    if section in ini_data and key in ini_data[section]:
        ini_data[section][key] = value
        save_ini_config(INI_PATH, ini_data)
    return RedirectResponse("/config", status_code=303)


@router.post("/update_json")
async def update_json(content: str = Form(...)):
    try:
        parsed = json.loads(content)
        save_json_config(JSON_PATH, parsed)
    except json.JSONDecodeError:
        print("Ошибка парсинга JSON, изменения не сохранены.")
    return RedirectResponse("/config", status_code=303)


@router.post("/save_as_json")
async def save_as_json(content: str = Form(...), filename: str = Form(...)):
    if not filename.strip():
        return await update_json(content)

    try:
        parsed = json.loads(content)

        filename = filename.strip()
        if not filename.endswith(".json"):
            filename += ".json"

        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)

        new_path = config_dir / filename
        save_json_config(str(new_path), parsed)

        print(f"Файл успешно сохранен как: {filename}")

    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")

    return RedirectResponse("/config", status_code=303)


@router.get("/laser")
async def laser_page(request: Request):
    return templates.TemplateResponse(
        "config.html", {"request": request, "page": "laser"}
    )


@router.get("/polychromators")
async def polychromators_page(request: Request):
    return templates.TemplateResponse(
        "config.html", {"request": request, "page": "polychromators"}
    )


@router.get("/caen")
async def caen_page(request: Request):
    return templates.TemplateResponse(
        "config.html", {"request": request, "page": "caen"}
    )
