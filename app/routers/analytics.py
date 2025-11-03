from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.dependencies import templates

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/", response_class=HTMLResponse)
async def analytics_page(request: Request):
    return templates.TemplateResponse("analytics.html", {"request": request})
