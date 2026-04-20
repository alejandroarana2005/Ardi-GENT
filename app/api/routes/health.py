"""HAIA Agent — Endpoint GET /health."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas import HealthResponse
from app.database.session import get_db

logger = logging.getLogger("[HAIA API]")
router = APIRouter()

VERSION = "1.0.0"


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Verifica que la API y la conexión a BD estén operativas."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error(f"[API] DB health check failed: {exc}")

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=VERSION,
        db_connected=db_ok,
    )
