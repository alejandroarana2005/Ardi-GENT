"""HAIA Agent — Capa 4: Calibración de pesos AHP. Stub Fase 1."""

import logging

logger = logging.getLogger("[HAIA Layer4-AHP]")

DEFAULT_AHP_WEIGHTS = {
    "w1": 0.40,  # ocupación
    "w2": 0.25,  # preferencia docente
    "w3": 0.20,  # distribución temporal
    "w4": 0.15,  # recursos
    "lambda": 1.5,
}


class AHPWeightCalibrator:
    """
    Calibra los pesos de U(A) mediante el proceso analítico jerárquico (AHP).
    Fase 1: retorna los pesos por defecto del informe IEEE HAIA.
    """

    def calibrate(self, pairwise_matrix: list[list[float]] | None = None) -> dict[str, float]:
        if pairwise_matrix is None:
            logger.info("[Layer4-AHP] Usando pesos por defecto (stub AHP)")
            return dict(DEFAULT_AHP_WEIGHTS)
        # Implementación completa en Fase 5
        logger.info("[Layer4-AHP] Calibración AHP — pendiente Fase 5")
        return dict(DEFAULT_AHP_WEIGHTS)
