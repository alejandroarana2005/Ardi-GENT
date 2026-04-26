"""
HAIA Agent — Capa 4: Calibración AHP (Analytic Hierarchy Process).

Método del eigenvector principal (Saaty, 1980):
    1. Construir matriz de comparación pareada n×n.
    2. Calcular eigenvector del eigenvalor máximo → normalizar → pesos.
    3. CR = CI / RI; aceptar si CR < 0.10.

Aborda Brecha G2 del informe: calibración multi-criterio formal y defendible.
Ref: Saaty, T. L. (1980). The Analytic Hierarchy Process. McGraw-Hill.
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger("[HAIA Layer4-AHP]")

DEFAULT_AHP_WEIGHTS: dict[str, float] = {
    "w1": 0.40,   # ocupación
    "w2": 0.25,   # preferencia docente
    "w3": 0.20,   # distribución temporal
    "w4": 0.15,   # recursos
    "lambda": 1.5,
}

# Índices aleatorios de Saaty (1980) para n = 1..10
_RANDOM_INDEX: dict[int, float] = {
    1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49,
}


class AHPCalibrator:
    """
    Calibra los pesos w1-w4 de U(A) mediante AHP (Saaty, 1980).

    Criterios (en orden fijo):
        0 → ocupacion    (w1)
        1 → preferencia  (w2)
        2 → distribucion (w3)
        3 → recursos     (w4)

    Ejemplo:
        ahp = AHPCalibrator()
        ahp.set_pairwise_comparison("ocupacion", "preferencia", 2)
        ahp.set_pairwise_comparison("ocupacion", "distribucion", 3)
        ahp.set_pairwise_comparison("ocupacion", "recursos", 4)
        ahp.set_pairwise_comparison("preferencia", "distribucion", 2)
        ahp.set_pairwise_comparison("preferencia", "recursos", 2)
        ahp.set_pairwise_comparison("distribucion", "recursos", 1)
        weights = ahp.compute_weights()   # {"w1": 0.477, ...}
        assert ahp.consistency_ratio() < 0.10
    """

    CRITERIA = ["ocupacion", "preferencia", "distribucion", "recursos"]

    def __init__(self) -> None:
        n = len(self.CRITERIA)
        self._matrix: np.ndarray = np.ones((n, n), dtype=float)

    # ── Configuración ─────────────────────────────────────────────────────────

    def set_pairwise_comparison(
        self, criterion_a: str, criterion_b: str, intensity: float
    ) -> None:
        """
        Escala de Saaty:
            1 = igualmente importantes  3 = moderadamente  5 = fuertemente
            7 = muy fuertemente         9 = absolutamente
        Establece M[i,j] = intensity y M[j,i] = 1/intensity.
        """
        i = self.CRITERIA.index(criterion_a)
        j = self.CRITERIA.index(criterion_b)
        self._matrix[i, j] = float(intensity)
        self._matrix[j, i] = 1.0 / float(intensity)

    # ── Cálculo AHP ───────────────────────────────────────────────────────────

    def compute_weights(self) -> dict[str, float]:
        """
        Eigenvector principal normalizado → pesos w1..w4.
        Retorna dict {w1, w2, w3, w4, lambda}.
        """
        eigenvalues, eigenvectors = np.linalg.eig(self._matrix)
        max_idx = int(np.argmax(eigenvalues.real))
        principal = eigenvectors[:, max_idx].real

        if principal[0] < 0:
            principal = -principal

        weights = principal / principal.sum()
        result: dict[str, float] = {
            "w1": float(weights[0]),
            "w2": float(weights[1]),
            "w3": float(weights[2]),
            "w4": float(weights[3]),
            "lambda": DEFAULT_AHP_WEIGHTS["lambda"],
        }
        logger.info(
            f"[Layer4-AHP] Pesos: w1={result['w1']:.3f} w2={result['w2']:.3f} "
            f"w3={result['w3']:.3f} w4={result['w4']:.3f}"
        )
        return result

    def consistency_ratio(self) -> float:
        """
        CR = CI / RI  donde  CI = (λ_max − n) / (n − 1).
        Matriz aceptable si CR < 0.10.
        """
        eigenvalues, _ = np.linalg.eig(self._matrix)
        lambda_max = float(np.max(eigenvalues.real))
        n = len(self.CRITERIA)
        ci = (lambda_max - n) / (n - 1)
        ri = _RANDOM_INDEX.get(n, 1.49)
        cr = ci / ri if ri > 0 else 0.0
        logger.info(
            f"[Layer4-AHP] λ_max={lambda_max:.4f} CI={ci:.4f} RI={ri} CR={cr:.4f}"
        )
        return cr

    def pairwise_matrix_as_list(self) -> list[list[float]]:
        """Devuelve la matriz interna como lista de listas."""
        return self._matrix.tolist()

    # ── Constructores de conveniencia ─────────────────────────────────────────

    @classmethod
    def from_paper(cls) -> "AHPCalibrator":
        """
        Matriz de comparación del informe IEEE HAIA.
        Deriva w1≈0.48, w2≈0.26, w3≈0.14, w4≈0.12 con CR < 0.05.
        """
        ahp = cls()
        ahp.set_pairwise_comparison("ocupacion",    "preferencia",  2)
        ahp.set_pairwise_comparison("ocupacion",    "distribucion", 3)
        ahp.set_pairwise_comparison("ocupacion",    "recursos",     4)
        ahp.set_pairwise_comparison("preferencia",  "distribucion", 2)
        ahp.set_pairwise_comparison("preferencia",  "recursos",     2)
        ahp.set_pairwise_comparison("distribucion", "recursos",     1)
        return ahp

    @classmethod
    def from_matrix(cls, matrix: list[list[float]]) -> "AHPCalibrator":
        """Carga una matriz de comparación 4×4 directamente."""
        ahp = cls()
        ahp._matrix = np.array(matrix, dtype=float)
        return ahp


# ── Wrapper backward-compatible con el stub Fase 1 ───────────────────────────

class AHPWeightCalibrator:
    """
    Preserva la interfaz del stub Fase 1.
    Cuando se pasa pairwise_matrix verifica consistencia antes de aceptar.
    """

    def calibrate(
        self,
        pairwise_matrix: list[list[float]] | None = None,
    ) -> dict[str, float]:
        if pairwise_matrix is None:
            logger.info("[Layer4-AHP] Sin matriz — devolviendo pesos por defecto")
            return dict(DEFAULT_AHP_WEIGHTS)

        ahp = AHPCalibrator.from_matrix(pairwise_matrix)
        cr = ahp.consistency_ratio()
        if cr > 0.10:
            logger.warning(
                f"[Layer4-AHP] Matriz inconsistente (CR={cr:.3f} > 0.10) — "
                "usando pesos por defecto"
            )
            return dict(DEFAULT_AHP_WEIGHTS)
        return ahp.compute_weights()
