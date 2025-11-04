import json
from fastapi import UploadFile
from pathlib import Path
from app.services.config_state import CONFIG_DATA, STATUS, UPLOAD_DIR


async def save_bytes_to_file(upload_file: UploadFile, target_path: Path):
    data = await upload_file.read()
    with open(target_path, "wb") as f:
        f.write(data)
    return target_path


async def save_config_files(files: dict):
    """
    files: dict с ключами absolut_calib, spectral_calib, fe_expected, connections_json
    """
    mapping = {
        "absolut_calib": "absolut_calib_file",
        "spectral_calib": "spectral_calib_file",
        "fe_expected": "fe_expected_file",
        "connections_json": "connections_file",
    }

    for key, status_key in mapping.items():
        upload = files.get(key)
        if not upload:
            continue

        try:
            target = UPLOAD_DIR / upload.filename
            await save_bytes_to_file(upload, target)
            with open(target, "r", encoding="utf-8") as f:
                CONFIG_DATA[key.replace("_json", "")] = json.load(f)
            STATUS[status_key] = upload.filename
        except Exception as e:
            print(f"[save_config_files] Error loading {key}: {e}")


async def save_msg_files(msg_files: list[UploadFile]):
    msg_dir = UPLOAD_DIR / "msg_pkgs"
    msg_dir.mkdir(parents=True, exist_ok=True)

    for f in msg_files:
        try:
            target = msg_dir / f.filename
            await save_bytes_to_file(f, target)
            CONFIG_DATA["msg_files"].append(str(target))
        except Exception as e:
            print(f"[save_msg_files] Error saving {f.filename}: {e}")

    STATUS["msgpk_count"] = len(CONFIG_DATA["msg_files"])


def clear_configs():
    CONFIG_DATA.update({
        "absolut_calib": None,
        "spectral_calib": None,
        "fe_expected": None,
        "connections": None,
        "msg_files": [],
    })
    STATUS.update({
        "absolut_calib_file": None,
        "spectral_calib_file": None,
        "fe_expected_file": None,
        "connections_file": None,
        "msgpk_count": 0,
        "processing": False,
        "ready": False,
    })
