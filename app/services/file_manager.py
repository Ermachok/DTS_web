import os
from fastapi import UploadFile

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_files(files: list[UploadFile]):
    saved_files = []

    for file in files:
        path = os.path.join(UPLOAD_DIR, file.filename)

        with open(path, "wb") as f:
            content = await file.read()
            f.write(content)

        saved_files.append({
            "filename": file.filename,
            "extension": os.path.splitext(file.filename)[1].lower()
        })

    return saved_files


async def save_file(file: UploadFile):
    result = await save_files([file])
    return result[0] if result else None
