"""HAIA Agent — Endpoints de reportes (JSON y HTML/PDF)."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database.models import ScheduleModel
from app.database.session import get_db

logger = logging.getLogger("[HAIA API]")
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{schedule_id}/json", summary="Reporte completo en JSON")
def get_report_json(
    schedule_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Retorna el reporte completo del horario en JSON."""
    _require_schedule(schedule_id, db)
    from app.reporting.report_generator import ReportGenerator
    try:
        report = ReportGenerator().generate_full_report(schedule_id, db)
        return report
    except Exception as exc:
        logger.error(f"[API] Error generando reporte JSON: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{schedule_id}/html", summary="Reporte HTML imprimible")
def get_report_html(
    schedule_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """Retorna el reporte como HTML con estilos @media print."""
    _require_schedule(schedule_id, db)
    from app.reporting.report_generator import ReportGenerator
    try:
        html = ReportGenerator().generate_html_report(schedule_id, db)
        return Response(content=html, media_type="text/html; charset=utf-8")
    except Exception as exc:
        logger.error(f"[API] Error generando reporte HTML: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{schedule_id}/pdf", summary="Reporte PDF descargable")
def get_report_pdf(
    schedule_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """
    Genera el reporte en PDF (reportlab) o HTML si reportlab no está instalado.
    Devuelve el archivo para descarga.
    """
    _require_schedule(schedule_id, db)
    from app.reporting.report_generator import ReportGenerator
    import tempfile, os

    gen = ReportGenerator()
    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, f"haia_report_{schedule_id[:8]}.pdf")
        actual_path = gen.generate_pdf(schedule_id, db, out_path)
        with open(actual_path, "rb") as f:
            content = f.read()

    ext = os.path.splitext(actual_path)[1].lower()
    if ext == ".pdf":
        media_type = "application/pdf"
        filename = f"haia_report_{schedule_id[:8]}.pdf"
    else:
        media_type = "text/html; charset=utf-8"
        filename = f"haia_report_{schedule_id[:8]}.html"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _require_schedule(schedule_id: str, db: Session) -> ScheduleModel:
    schedule = (
        db.query(ScheduleModel)
        .filter(ScheduleModel.schedule_id == schedule_id)
        .first()
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule
