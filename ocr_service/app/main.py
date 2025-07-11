from fastapi import FastAPI
from ocr_service.core.config import settings
from ocr_service.app.api.v1 import endpoints

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

app.include_router(endpoints.router, prefix="/v1")
