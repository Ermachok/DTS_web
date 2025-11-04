from pathlib import Path

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STATUS = {
    "absolut_calib_file": None,
    "spectral_calib_file": None,
    "fe_expected_file": None,
    "connections_file": None,
    "msgpk_count": 0,
    "processing": False,
    "ready": False,
}

CONFIG_DATA = {
    "absolut_calib": None,  # dict
    "spectral_calib": None,  # dict
    "fe_expected": None,  # dict
    "connections": None,  # dict
    "msg_files": [],
}
