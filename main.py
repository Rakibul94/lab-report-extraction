from __future__ import annotations

import logging

from fastapi import FastAPI

from adapters.factory import create_ocr_provider
from api.routes import create_router
from services.config import Settings, get_settings
from services.lab_report_service import LabReportService

logging.basicConfig(level=logging.INFO)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    provider = create_ocr_provider(settings)          # the ONLY line that knows about adapters
    service = LabReportService(provider)              # service gets a port, unaware of which one
    app = FastAPI(title=settings.app_name)
    app.include_router(create_router(service, settings))
    return app


app = create_app()