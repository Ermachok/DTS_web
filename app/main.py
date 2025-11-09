from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.services.config_state import auto_load_configs
from app.routers import status, analytics, config, laser

app = FastAPI(title="Data Analysis Web Interface")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def startup_event():
    auto_load_configs()

app.include_router(status.router)
app.include_router(analytics.router)
app.include_router(config.router)
app.include_router(laser.router)


@app.get("/")
async def index():
    return {"message": "Перейдите на /status или /analytics"}
