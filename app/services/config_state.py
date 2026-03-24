import json
from pathlib import Path

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

DEFAULT_PATHS = {
    "connections": Path("config/config_connection_03_2026.json"),
    "absolut_calib": Path("calibrations/absolute/absolute_calib_jan2026_no_pest_for03_2026_wrong.json"),
    "spectral_calib": Path("calibrations/relative/EN_spectral_config_2026_03_WRONG.json"),
    "fe_expected": Path("fe_expected/f_expected_equator_june2024.json"),
}

STATUS = {
    "absolut_calib_file": None,
    "spectral_calib_file": None,
    "fe_expected_file": None,
    "connections_file": None,
    "msgpk_count": 0,
    "ready": False,
    "processing": False,
}

CONFIG_DATA = {
    "absolut_calib": None,
    "spectral_calib": None,
    "fe_expected": None,
    "connections": None,
    "msg_files": [],
}


def load_single_config(file_path: Path, key: str):
    if not file_path.exists():
        print(f"[config_state] Файл {file_path} не найден.")
        CONFIG_DATA[key] = None
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            CONFIG_DATA[key] = json.load(f)
        STATUS[f"{key}_file"] = str(file_path)
        print(f"[config_state] Загружен {key} из {file_path}")
        return True
    except Exception as e:
        CONFIG_DATA[key] = None
        print(f"[config_state] Ошибка при загрузке {file_path}: {e}")
        return False


def auto_load_configs():
    """
    Загружает все конфиги по умолчанию при запуске приложения.
    """
    loaded = [load_single_config(p, key) for key, p in DEFAULT_PATHS.items()]
    STATUS["ready"] = all(loaded)
    print(f"[config_state] Автозагрузка завершена. STATUS.ready={STATUS['ready']}")


def clear_configs():
    for k in CONFIG_DATA:
        CONFIG_DATA[k] = None
    for k in STATUS:
        if "_file" in k:
            STATUS[k] = None
    STATUS["ready"] = False
    STATUS["processing"] = False
