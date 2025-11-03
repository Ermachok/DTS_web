import os
from fastapi import UploadFile

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

STATUS = {
    "msg_file": None,
    "csv_file": None,
    "json_file": None,
    "processing": False,
    "ready": False
}


async def save_file(file: UploadFile):
    ext = os.path.splitext(file.filename)[1].lower()
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    if ext == ".msg":
        STATUS["msg_file"] = file.filename
    elif ext == ".csv":
        STATUS["csv_file"] = file.filename
    elif ext == ".json":
        STATUS["json_file"] = file.filename
