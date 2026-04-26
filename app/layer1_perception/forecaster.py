"""
HAIA Agent — Capa 1: Pronóstico de matrícula con suavizado exponencial doble.

Implementa el Método de Holt (suavizado exponencial con tendencia lineal):
    level_t  = alpha * y_t  + (1-alpha) * (level_{t-1} + trend_{t-1})
    trend_t  = beta  * (level_t - level_{t-1}) + (1-beta) * trend_{t-1}
    yhat_{t+1} = level_t + trend_t

Si history < min_history (3 semestres), retorna el último valor sin cambio.

Aborda Brecha G5 del informe: inteligencia predictiva para anticipar
ENROLLMENT_SURGE antes de que ocurra como evento dinámico.
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.domain.entities import Subject

logger = logging.getLogger("[HAIA Layer1-Forecaster]")


@dataclass
class EnrollmentPrediction:
    """Predicción de matrícula para un semestre futuro."""
    subject_code: str
    predicted_enrollment: int
    confidence_interval: tuple[int, int]  # (low_95, high_95)
    semesters_used: int
    method: str = "holt_exponential_smoothing"


class EnrollmentForecaster:
    """
    Pronóstico de matrícula por materia usando suavizado exponencial de Holt.

    Uso proactivo: el agente invoca predict_batch() antes de la Capa 2
    para ajustar enrollments y anticipar presiones de capacidad.
    """

    def __init__(
        self,
        alpha: float = 0.4,
        beta: float = 0.3,
        min_history_semesters: int = 3,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.min_history = min_history_semesters

    # ── API de predicción ─────────────────────────────────────────────────────

    def predict(
        self,
        subject_code: str,
        history: list[dict],
    ) -> EnrollmentPrediction:
        """
        Args:
            subject_code: código de la materia.
            history: lista de {"semester": "2023-A", "enrollment": 28}, ordenada
                     cronológicamente (más antiguo primero).

        Returns:
            EnrollmentPrediction con predicted_enrollment e intervalo de confianza.
        """
        if len(history) < self.min_history:
            last = history[-1]["enrollment"] if history else 30
            return EnrollmentPrediction(
                subject_code=subject_code,
                predicted_enrollment=int(last),
                confidence_interval=(int(last), int(last)),
                semesters_used=len(history),
                method="passthrough",
            )

        series = np.array([h["enrollment"] for h in history], dtype=float)
        predicted, residuals = self._holt_forecast(series)
        predicted_int = max(1, int(round(predicted)))

        std = float(np.std(residuals)) if len(residuals) > 1 else predicted * 0.10
        low  = max(1, int(round(predicted - 1.96 * std)))
        high = int(round(predicted + 1.96 * std))

        logger.debug(
            f"[Layer1-Forecaster] {subject_code}: "
            f"últimos {len(history)} sem → {predicted_int} "
            f"CI=[{low}, {high}]"
        )
        return EnrollmentPrediction(
            subject_code=subject_code,
            predicted_enrollment=predicted_int,
            confidence_interval=(low, high),
            semesters_used=len(history),
        )

    def predict_batch(
        self,
        subjects_history: dict[str, list[dict]],
    ) -> dict[str, EnrollmentPrediction]:
        """Predicción en lote para múltiples materias."""
        return {
            code: self.predict(code, hist)
            for code, hist in subjects_history.items()
        }

    # ── Interfaz legada (backward-compat con stub Fase 1) ─────────────────────

    def forecast(self, subjects: list[Subject], semester: str) -> dict[str, int]:
        """
        Retorna {subject_code: enrollment_forecast}.
        Sin datos históricos: devuelve enrollment actual sin cambio.
        """
        logger.info(
            "[Layer1-Forecaster] forecast() sin histórico — "
            "usando enrollment registrado"
        )
        return {s.code: s.enrollment for s in subjects}

    def adjust_instance(
        self, subjects: list[Subject], forecasts: dict[str, int]
    ) -> list[Subject]:
        """
        Retorna lista de Subject con enrollment ajustado según pronóstico.
        Preserva inmutabilidad creando nuevas instancias con dataclasses.replace().
        """
        adjusted = []
        for s in subjects:
            forecast = forecasts.get(s.code, s.enrollment)
            if forecast != s.enrollment:
                logger.info(
                    f"[Layer1-Forecaster] {s.code}: "
                    f"enrollment {s.enrollment} → {forecast}"
                )
                adjusted.append(dataclasses.replace(s, enrollment=forecast))
            else:
                adjusted.append(s)
        return adjusted

    # ── Holt exponential smoothing ─────────────────────────────────────────────

    def _holt_forecast(
        self, series: np.ndarray
    ) -> tuple[float, list[float]]:
        """
        Suavizado exponencial doble de Holt.
        Retorna (predicción_un_paso_adelante, residuales_in-sample).
        """
        alpha, beta = self.alpha, self.beta
        level = float(series[0])
        trend = float(series[1] - series[0]) if len(series) > 1 else 0.0

        residuals: list[float] = []
        for t in range(1, len(series)):
            forecast_t = level + trend
            residuals.append(float(series[t]) - forecast_t)
            new_level = alpha * float(series[t]) + (1 - alpha) * (level + trend)
            new_trend = beta * (new_level - level) + (1 - beta) * trend
            level, trend = new_level, new_trend

        return level + trend, residuals
