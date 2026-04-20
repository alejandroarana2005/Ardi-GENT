"""
HAIA Agent — FastAPI entry point.
HAIA: Hybrid Adaptive Intelligent Agent para asignación de salones universitarios.
Universidad de Ibagué | Ingeniería de Sistemas.

Ref: La Cruz et al. (2024) — UniSchedApi (modelo de datos base).
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, schedule, events, metrics, assignments
from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("[HAIA]")

app = FastAPI(
    title="HAIA — Hybrid Adaptive Intelligent Agent",
    description=(
        "Agente inteligente BDI para asignación óptima de salones universitarios. "
        "Universidad de Ibagué — Ingeniería de Sistemas.\n\n"
        "**Arquitectura:** BDI con 5 capas funcionales (Percepción → AC-3 → "
        "CSP/MILP → SA → Re-optimización dinámica).\n\n"
        "**Función objetivo:** U(A) = w1·U_ocup + w2·U_pref + w3·U_dist + w4·U_rec − λ·Pen"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(schedule.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)
app.include_router(metrics.router, prefix=API_PREFIX)
app.include_router(assignments.router, prefix=API_PREFIX)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("[HAIA] Iniciando servidor...")
    logger.info(f"[HAIA] Docs disponibles en http://{settings.api_host}:{settings.api_port}/docs")
