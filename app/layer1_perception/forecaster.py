"""
HAIA Agent — Capa 1: Stub del pronóstico de matrícula (LSTM futuro).
En la versión actual retorna el enrollment histórico sin modificación.
Punto de extensión para integrar un modelo LSTM de series temporales
que pronostique fluctuaciones de matrícula antes de la asignación.
"""

import logging

from app.domain.entities import Subject

logger = logging.getLogger("[HAIA Layer1-Forecaster]")


class EnrollmentForecaster:
    """
    Stub del modelo de pronóstico de matrícula.
    Interfaz estable para cuando se integre el modelo LSTM real.
    """

    def forecast(self, subjects: list[Subject], semester: str) -> dict[str, int]:
        """
        Retorna {subject_code: enrollment_forecast}.
        Actualmente usa el enrollment histórico sin ajuste.
        """
        logger.info("[Layer1-Forecaster] Usando enrollment histórico (stub LSTM)")
        return {s.code: s.enrollment for s in subjects}

    def adjust_instance(
        self, subjects: list[Subject], forecasts: dict[str, int]
    ) -> list[Subject]:
        """
        Retorna una nueva lista de Subject con enrollment ajustado según pronóstico.
        Preserva inmutabilidad creando nuevas instancias con replace().
        """
        import dataclasses

        adjusted = []
        for s in subjects:
            forecast = forecasts.get(s.code, s.enrollment)
            if forecast != s.enrollment:
                logger.debug(
                    f"[Layer1-Forecaster] {s.code}: enrollment {s.enrollment} → {forecast}"
                )
                adjusted.append(dataclasses.replace(s, enrollment=forecast))
            else:
                adjusted.append(s)
        return adjusted
