"""
HAIA Agent — Función objetivo U(A) declarada a nivel de dominio.
La implementación completa está en layer4_optimization/utility_function.py.
Este módulo expone solo las constantes y tipos del dominio.
"""

from dataclasses import dataclass

DEFAULT_WEIGHTS: dict[str, float] = {
    "w1": 0.40,  # ocupación del aula
    "w2": 0.25,  # preferencia del docente
    "w3": 0.20,  # distribución temporal
    "w4": 0.15,  # recursos opcionales satisfechos
    "lambda": 1.5,  # penalización por SC violadas
}


@dataclass(frozen=True)
class UtilityWeights:
    """Pesos calibrados de la función U(A). Por defecto los del informe IEEE HAIA."""
    w1: float = 0.40
    w2: float = 0.25
    w3: float = 0.20
    w4: float = 0.15
    lambda_penalty: float = 1.5

    def __post_init__(self) -> None:
        total = self.w1 + self.w2 + self.w3 + self.w4
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    def as_dict(self) -> dict[str, float]:
        return {
            "w1": self.w1,
            "w2": self.w2,
            "w3": self.w3,
            "w4": self.w4,
            "lambda": self.lambda_penalty,
        }
