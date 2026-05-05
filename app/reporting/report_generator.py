"""
HAIA Agent — Reporting: Generador de reportes JSON y HTML/PDF.

generate_full_report(schedule_id, db) → dict completo con todas las secciones.
generate_html_report(schedule_id, db, output_path) → HTML imprimible / PDF.

El método legacy generate_json(result: SchedulingResult) → str se mantiene
para backward-compat con los tests de Fase 1.

Para PDF en producción: instalar reportlab o weasyprint y reemplazar
_build_html() por una llamada a la librería PDF.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.domain.entities import Assignment, SchedulingResult

logger = logging.getLogger("[HAIA Reporting-ReportGenerator]")


class ReportGenerator:

    # ── API legacy (Fase 1) ───────────────────────────────────────────────────

    def generate_json(self, result: SchedulingResult) -> str:
        """Backward-compat: resumen JSON minimal de un SchedulingResult."""
        report = {
            "schedule_id": result.schedule_id,
            "semester": result.semester,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "solver_used": result.solver_used,
            "utility_score": result.utility_score,
            "is_feasible": result.is_feasible,
            "elapsed_seconds": result.elapsed_seconds,
            "total_assignments": len(result.assignments),
            "assignments": [
                {
                    "subject_code": a.subject_code,
                    "classroom_code": a.classroom_code,
                    "timeslot_code": a.timeslot_code,
                    "group": a.group_number,
                    "session": a.session_number,
                }
                for a in result.assignments
            ],
            "violations": result.violations,
        }
        return json.dumps(report, indent=2, ensure_ascii=False)

    # ── API Fase 5: DB-backed ─────────────────────────────────────────────────

    def generate_full_report(self, schedule_id: str, db) -> dict:
        """
        Reporte completo en dict (serializable a JSON) con secciones:
        - metadata
        - utility_breakdown
        - assignments (lista completa)
        - conflicts_detected (HC violadas)
        - event_history
        - version_tree
        """
        from app.database.models import (
            AssignmentModel, DynamicEventModel, ScheduleModel,
        )
        from app.layer1_perception.data_loader import DataLoader
        from app.reporting.metrics_calculator import MetricsCalculator
        from app.reporting.conflict_detector import ConflictDetector

        schedule = (
            db.query(ScheduleModel)
            .filter(ScheduleModel.schedule_id == schedule_id)
            .first()
        )
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        # Cargar asignaciones ORM → domain entities
        orm_assignments = (
            db.query(AssignmentModel)
            .filter(AssignmentModel.schedule_id == schedule.id)
            .all()
        )
        assignments = [
            Assignment(
                subject_code=a.subject_code,
                classroom_code=a.classroom_code,
                timeslot_code=a.timeslot_code,
                group_number=a.group_number,
                session_number=a.session_number,
                utilidad_score=a.utilidad_score,
            )
            for a in orm_assignments
        ]

        # Cargar instancia para métricas y detección de conflictos
        loader = DataLoader(db)
        try:
            instance, _ = loader.load_instance(schedule.semester)
        except Exception:
            instance = None

        # Métricas de utilidad
        utility_breakdown: dict = {}
        conflicts: list = []
        if instance:
            try:
                calc = MetricsCalculator()
                metrics = calc.compute(schedule_id, assignments, instance)
                utility_breakdown = {
                    "total": metrics.utility_score,
                    "u_occupancy": metrics.u_occupancy,
                    "u_preference": metrics.u_preference,
                    "u_distribution": metrics.u_distribution,
                    "u_resources": metrics.u_resources,
                    "penalty": metrics.penalty,
                    "hard_constraint_violations": metrics.hard_constraint_violations,
                    "soft_constraint_violations": metrics.soft_constraint_violations,
                    "soft_constraint_counts": metrics.soft_constraint_counts,
                    "weights_used": metrics.weights_used,
                }
                cd = ConflictDetector()
                conflicts = cd.detect(assignments, instance)
            except Exception as exc:
                logger.warning(f"[ReportGenerator] Métricas no disponibles: {exc}")

        # Historial de eventos
        events_orm = (
            db.query(DynamicEventModel)
            .filter(DynamicEventModel.schedule_id == schedule.id)
            .order_by(DynamicEventModel.created_at)
            .all()
        )
        event_history = [
            {
                "id": e.id,
                "event_type": e.event_type,
                "payload": json.loads(e.payload) if e.payload else {},
                "affected_assignments": e.affected_assignments,
                "repair_elapsed_seconds": e.repair_elapsed_seconds,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events_orm
        ]

        # Árbol de versiones (hijos directos)
        children = (
            db.query(ScheduleModel)
            .filter(ScheduleModel.parent_schedule_id == schedule_id)
            .order_by(ScheduleModel.created_at)
            .all()
        )
        version_tree = [
            {
                "schedule_id": c.schedule_id,
                "status": c.status,
                "utility_score": c.utility_score,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "parent_schedule_id": c.parent_schedule_id,
            }
            for c in children
        ]

        report = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "schedule_id": schedule_id,
                "semester": schedule.semester,
                "status": schedule.status,
                "solver_used": schedule.solver_used,
                "is_feasible": schedule.is_feasible,
                "elapsed_seconds": schedule.elapsed_seconds,
                "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
                "parent_schedule_id": schedule.parent_schedule_id,
                "total_assignments": len(assignments),
            },
            "utility_breakdown": utility_breakdown,
            "assignments": [
                {
                    "subject_code": a.subject_code,
                    "classroom_code": a.classroom_code,
                    "timeslot_code": a.timeslot_code,
                    "group_number": a.group_number,
                    "session_number": a.session_number,
                    "utilidad_score": round(a.utilidad_score, 4),
                }
                for a in assignments
            ],
            "conflicts_detected": conflicts,
            "event_history": event_history,
            "version_tree": version_tree,
        }
        logger.info(
            f"[ReportGenerator] Reporte generado — schedule={schedule_id}, "
            f"{len(assignments)} asignaciones, {len(event_history)} eventos"
        )
        return report

    # ── HTML / PDF ────────────────────────────────────────────────────────────

    def generate_html_report(
        self, schedule_id: str, db, output_path: Optional[str] = None
    ) -> str:
        """
        Genera un reporte HTML imprimible con CSS para @media print.
        Si output_path se provee, lo escribe al disco y retorna la ruta.
        Si no, retorna el HTML como string.
        """
        report = self.generate_full_report(schedule_id, db)
        html = self._build_html(report)
        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            logger.info(f"[ReportGenerator] HTML escrito en {output_path}")
            return output_path
        return html

    def generate_pdf(
        self, schedule_id: str, db, output_path: str
    ) -> str:
        """
        Intenta generar PDF con reportlab; si no está disponible genera HTML.
        Retorna la ruta del archivo generado.
        """
        try:
            from reportlab.lib.pagesizes import A4
            return self._generate_pdf_reportlab(schedule_id, db, output_path)
        except ImportError:
            html_path = output_path.replace(".pdf", ".html")
            logger.info(
                "[ReportGenerator] reportlab no instalado — "
                f"generando HTML en {html_path}"
            )
            return self.generate_html_report(schedule_id, db, html_path)

    # ── Construcción HTML ─────────────────────────────────────────────────────

    def _build_html(self, report: dict) -> str:
        meta = report["metadata"]
        ub = report.get("utility_breakdown", {})
        assignments = report.get("assignments", [])
        events = report.get("event_history", [])
        versions = report.get("version_tree", [])

        # Agrupar asignaciones por día (si hay timeslot_code con día embebido)
        def ts_day(ts_code: str) -> str:
            parts = ts_code.upper()
            for day in ["MON", "TUE", "WED", "THU", "FRI", "SAT"]:
                if day in parts:
                    return {"MON": "Lunes", "TUE": "Martes", "WED": "Miércoles",
                            "THU": "Jueves", "FRI": "Viernes", "SAT": "Sábado"}[day]
            return ts_code

        rows = "".join(
            f"<tr><td>{a['subject_code']}</td>"
            f"<td>{ts_day(a['timeslot_code'])}</td>"
            f"<td>{a['timeslot_code']}</td>"
            f"<td>{a['classroom_code']}</td>"
            f"<td>{a['group_number']}</td>"
            f"<td>{a['utilidad_score']:.4f}</td></tr>"
            for a in sorted(assignments, key=lambda x: x["timeslot_code"])
        )

        event_rows = "".join(
            f"<tr><td>{e['event_type']}</td>"
            f"<td>{e['affected_assignments']}</td>"
            f"<td>{e['repair_elapsed_seconds']:.3f}s</td>"
            f"<td>{e.get('created_at', '')[:19]}</td></tr>"
            for e in events
        )

        version_rows = "".join(
            f"<tr><td>{v['schedule_id'][:8]}…</td>"
            f"<td>{v['utility_score']:.4f}</td>"
            f"<td>{v['status']}</td>"
            f"<td>{(v.get('created_at') or '')[:19]}</td></tr>"
            for v in versions
        )

        hc = ub.get("hard_constraint_violations", "—")
        sc = ub.get("soft_constraint_violations", "—")

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>HAIA — Reporte de Horario {meta['schedule_id'][:8]}</title>
<style>
  body{{font-family:Arial,sans-serif;margin:2cm;color:#222;font-size:11pt}}
  h1{{color:#004080;border-bottom:2px solid #004080;padding-bottom:4px}}
  h2{{color:#004080;margin-top:1.5em;border-bottom:1px solid #aac}}
  table{{border-collapse:collapse;width:100%;margin-top:0.5em}}
  th{{background:#004080;color:#fff;padding:6px 10px;text-align:left}}
  td{{padding:4px 10px;border-bottom:1px solid #ddd}}
  tr:nth-child(even){{background:#f4f8ff}}
  .metric{{display:inline-block;margin:6px 12px 6px 0;padding:8px 14px;
           background:#e8f0fe;border-radius:4px;font-weight:bold}}
  .metric span{{font-size:0.85em;font-weight:normal;color:#555}}
  @media print{{body{{margin:1cm}}}}
</style>
</head>
<body>
<h1>HAIA — Reporte de Asignación de Horarios</h1>
<p><b>Universidad de Ibagué</b> &nbsp;|&nbsp; Ingeniería de Sistemas &nbsp;|&nbsp;
   Generado: {report['generated_at'][:19]}</p>

<h2>Resumen Ejecutivo</h2>
<div>
  <span class="metric">{meta['semester']} <span>semestre</span></span>
  <span class="metric">{meta['total_assignments']} <span>asignaciones</span></span>
  <span class="metric">{ub.get('total', 0):.4f} <span>U(A)</span></span>
  <span class="metric">{hc} <span>violaciones HC</span></span>
  <span class="metric">{sc} <span>violaciones SC</span></span>
  <span class="metric">{meta['solver_used']} <span>solver</span></span>
  <span class="metric">{meta['elapsed_seconds']:.2f}s <span>tiempo</span></span>
</div>

<h2>Desglose de U(A)</h2>
<table>
  <tr><th>Componente</th><th>Valor</th><th>Peso</th></tr>
  <tr><td>U_ocupación</td><td>{ub.get('u_occupancy',0):.4f}</td><td>w1</td></tr>
  <tr><td>U_preferencia</td><td>{ub.get('u_preference',0):.4f}</td><td>w2</td></tr>
  <tr><td>U_distribución</td><td>{ub.get('u_distribution',0):.4f}</td><td>w3</td></tr>
  <tr><td>U_recursos</td><td>{ub.get('u_resources',0):.4f}</td><td>w4</td></tr>
  <tr><td><b>Penalidad</b></td><td>{ub.get('penalty',0):.4f}</td><td>λ</td></tr>
  <tr><td><b>U(A) total</b></td><td><b>{ub.get('total',0):.4f}</b></td><td></td></tr>
</table>

<h2>Asignaciones ({len(assignments)})</h2>
<table>
  <tr><th>Materia</th><th>Día</th><th>Franja</th><th>Salón</th><th>Grupo</th><th>U_i</th></tr>
  {rows}
</table>

<h2>Historial de Eventos Dinámicos ({len(events)})</h2>
{'<table><tr><th>Tipo</th><th>Afectadas</th><th>Tiempo repair</th><th>Fecha</th></tr>'
 + event_rows + '</table>' if events else '<p>Sin eventos registrados.</p>'}

<h2>Árbol de Versiones ({len(versions)})</h2>
{'<table><tr><th>Schedule ID</th><th>U(A)</th><th>Estado</th><th>Creado</th></tr>'
 + version_rows + '</table>' if versions else '<p>Sin versiones derivadas.</p>'}

<p style="margin-top:2em;color:#888;font-size:9pt">
  HAIA v1.0 — Hybrid Adaptive Intelligent Agent &nbsp;|&nbsp;
  Schedule ID: {meta['schedule_id']}
</p>
</body>
</html>"""

    def _generate_pdf_reportlab(
        self, schedule_id: str, db, output_path: str
    ) -> str:
        """Genera PDF completo con reportlab: portada, métricas y tabla de asignaciones."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            HRFlowable, PageBreak, Paragraph, SimpleDocTemplate,
            Spacer, Table, TableStyle,
        )

        report = self.generate_full_report(schedule_id, db)
        meta = report["metadata"]
        ub = report.get("utility_breakdown", {})
        assignments = report.get("assignments", [])

        # Obtener professor_code directamente del ORM (no incluido en el dict de report)
        from app.database.models import AssignmentModel, ScheduleModel
        schedule_orm = (
            db.query(ScheduleModel)
            .filter(ScheduleModel.schedule_id == schedule_id)
            .first()
        )
        professor_map: dict = {}
        if schedule_orm:
            for a in db.query(AssignmentModel).filter(
                AssignmentModel.schedule_id == schedule_orm.id
            ).all():
                professor_map[
                    (a.subject_code, a.timeslot_code, a.group_number, a.session_number)
                ] = a.professor_code

        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        DARK_BLUE = colors.HexColor("#004080")
        LIGHT_BLUE = colors.HexColor("#e8f0fe")
        ALT_ROW = colors.HexColor("#f4f8ff")

        def _footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.grey)
            canvas.drawCentredString(
                A4[0] / 2,
                1.2 * cm,
                f"Generado: {generated_at}  |  Schedule ID: {schedule_id}  |  Página {doc.page}",
            )
            canvas.restoreState()

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
        )
        styles = getSampleStyleSheet()

        cover_title = ParagraphStyle(
            "CoverTitle", parent=styles["Title"],
            fontSize=26, spaceAfter=10,
            textColor=DARK_BLUE, alignment=1,
        )
        cover_sub = ParagraphStyle(
            "CoverSub", parent=styles["Normal"],
            fontSize=13, spaceAfter=6,
            textColor=DARK_BLUE, alignment=1,
        )
        section_head = ParagraphStyle(
            "SectionHead", parent=styles["Heading1"],
            fontSize=13, textColor=DARK_BLUE,
            spaceAfter=4, spaceBefore=8,
        )
        cover_foot = ParagraphStyle(
            "CoverFoot", parent=styles["Normal"],
            fontSize=10, alignment=1, textColor=colors.grey,
        )

        elements = []

        # ── PORTADA ───────────────────────────────────────────────────────────
        elements.append(Spacer(1, 4 * cm))
        elements.append(Paragraph("HAIA Schedule Report", cover_title))
        elements.append(HRFlowable(width="100%", thickness=2, color=DARK_BLUE))
        elements.append(Spacer(1, 0.4 * cm))
        elements.append(Paragraph("Hybrid Adaptive Intelligent Agent", cover_sub))
        elements.append(Paragraph(
            "Sistema de Asignación de Horarios Académicos — Universidad de Ibagué",
            cover_sub,
        ))
        elements.append(Spacer(1, 1.5 * cm))

        cover_data = [
            ["Semestre", meta["semester"]],
            ["Estado", meta["status"]],
            ["Solver", meta["solver_used"]],
            ["Total asignaciones", str(meta["total_assignments"])],
            ["U(A)", f"{ub.get('total', 0):.4f}"],
            ["HC violadas", str(ub.get("hard_constraint_violations", 0))],
            ["Tiempo solver", f"{meta['elapsed_seconds']:.2f} s"],
            ["Generado", generated_at],
            ["Schedule ID", schedule_id],
        ]
        ct = Table(cover_data, colWidths=[5 * cm, 10.6 * cm])
        ct.setStyle(TableStyle([
            ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE",  (0, 0), (-1, -1), 11),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, ALT_ROW]),
            ("GRID",      (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        elements.append(ct)
        elements.append(Spacer(1, 1.2 * cm))
        elements.append(Paragraph(
            "Ingeniería de Sistemas — Facultad de Ingeniería", cover_foot
        ))
        elements.append(PageBreak())

        # ── MÉTRICAS U(A) ─────────────────────────────────────────────────────
        elements.append(Paragraph("Desglose de U(A)", section_head))
        elements.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
        elements.append(Spacer(1, 0.3 * cm))

        metrics_rows = [
            ["Componente", "Valor", "Descripción"],
            ["U_ocupación",    f"{ub.get('u_occupancy', 0):.4f}",    "Aprovechamiento de salones"],
            ["U_preferencia",  f"{ub.get('u_preference', 0):.4f}",   "Preferencias horarias de profesores"],
            ["U_distribución", f"{ub.get('u_distribution', 0):.4f}", "Distribución equilibrada en la semana"],
            ["U_recursos",     f"{ub.get('u_resources', 0):.4f}",    "Uso eficiente de recursos físicos"],
            ["Penalidad (λ)",  f"{ub.get('penalty', 0):.4f}",        "Penalización por violaciones SC"],
            ["HC violadas",    str(ub.get("hard_constraint_violations", 0)), "Restricciones duras incumplidas"],
            ["SC violadas",    str(ub.get("soft_constraint_violations", 0)), "Restricciones blandas incumplidas"],
            ["U(A) Total",     f"{ub.get('total', 0):.4f}",          "Función objetivo final"],
        ]
        mt = Table(metrics_rows, colWidths=[4.5 * cm, 2.8 * cm, 9.3 * cm])
        mt.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND",    (0, -1), (-1, -1), LIGHT_BLUE),
            ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [colors.white, ALT_ROW]),
            ("GRID",          (0, 0), (-1, -1),  0.5, colors.grey),
            ("FONTSIZE",      (0, 0), (-1, -1),  10),
            ("TOPPADDING",    (0, 0), (-1, -1),  5),
            ("BOTTOMPADDING", (0, 0), (-1, -1),  5),
            ("LEFTPADDING",   (0, 0), (-1, -1),  8),
        ]))
        elements.append(mt)
        elements.append(Spacer(1, 0.8 * cm))

        # ── TABLA DE ASIGNACIONES ─────────────────────────────────────────────
        elements.append(Paragraph(
            f"Asignaciones ({meta['total_assignments']})", section_head
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE))
        elements.append(Spacer(1, 0.3 * cm))

        asgn_rows = [["Materia", "Franja", "Aula", "Profesor", "Grupo", "Ses.", "U_i"]]
        for a in sorted(assignments, key=lambda x: x["timeslot_code"]):
            key = (a["subject_code"], a["timeslot_code"], a["group_number"], a["session_number"])
            prof = professor_map.get(key, "—")
            asgn_rows.append([
                a["subject_code"],
                a["timeslot_code"],
                a["classroom_code"],
                prof,
                str(a["group_number"]),
                str(a["session_number"]),
                f"{a['utilidad_score']:.4f}",
            ])

        at = Table(
            asgn_rows,
            colWidths=[3.5 * cm, 3 * cm, 2.5 * cm, 3 * cm, 1.5 * cm, 1.2 * cm, 2 * cm],
            repeatRows=1,
        )
        at.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  DARK_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ALT_ROW]),
            ("GRID",          (0, 0), (-1, -1),  0.5, colors.grey),
            ("FONTSIZE",      (0, 0), (-1, -1),  9),
            ("TOPPADDING",    (0, 0), (-1, -1),  4),
            ("BOTTOMPADDING", (0, 0), (-1, -1),  4),
            ("LEFTPADDING",   (0, 0), (-1, -1),  6),
        ]))
        elements.append(at)

        doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
        logger.info(f"[ReportGenerator] PDF reportlab generado: {output_path}")
        return output_path
