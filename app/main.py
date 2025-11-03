from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import status, analytics, config

app = FastAPI(title="Data Analysis Web Interface")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(status.router)
app.include_router(analytics.router)
app.include_router(config.router)


@app.get("/")
async def index():
    return {"message": "Добро пожаловать! Перейдите на /status или /analytics"}
