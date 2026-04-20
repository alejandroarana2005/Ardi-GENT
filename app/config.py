"""
HAIA Agent — Configuración central con Pydantic BaseSettings.
Todos los parámetros del sistema se configuran aquí y se leen desde variables de entorno.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class HAIAConfig(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql://haia_user:haia_pass@localhost:5432/haia_db",
        alias="DATABASE_URL",
    )

    # API server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Solver selection threshold (La Cruz et al., 2024 — extended)
    solver_backtrack_threshold: int = Field(default=150, alias="SOLVER_BACKTRACK_THRESHOLD")

    # Simulated Annealing parameters
    # Calibración basada en los deltas REALES de U(A):
    #   Delta típico ≈ cambio_por_asignación / n ≈ 0.003 (con n=105)
    #   T0=0.05 → exp(-0.003/0.05) ≈ 0.94 → ~94% aceptación inicial
    #   A T=0.005 (cerca del fin): exp(-0.003/0.005) ≈ 0.55 → búsqueda dirigida
    #   alpha=0.95, iters_per_T=50 → ~121 pasos × 50 = 6,050 iteraciones totales ≈ 50s
    sa_t0: float = Field(default=0.05, alias="SA_T0")
    sa_t_min: float = Field(default=0.0001, alias="SA_T_MIN")
    sa_alpha: float = Field(default=0.95, alias="SA_ALPHA")
    sa_iters_per_t: int = Field(default=50, alias="SA_ITERS_PER_T")

    # Utility function weights — U(A) = w1·ocup + w2·pref + w3·dist + w4·rec − λ·Pen
    w1_occupancy: float = Field(default=0.40, alias="W1_OCCUPANCY")
    w2_preference: float = Field(default=0.25, alias="W2_PREFERENCE")
    w3_distribution: float = Field(default=0.20, alias="W3_DISTRIBUTION")
    w4_resources: float = Field(default=0.15, alias="W4_RESOURCES")
    lambda_penalty: float = Field(default=1.5, alias="LAMBDA_PENALTY")

    # Dynamic re-optimization
    repair_neighborhood_k: int = Field(default=2, alias="REPAIR_NEIGHBORHOOD_K")
    repair_max_seconds: int = Field(default=30, alias="REPAIR_MAX_SECONDS")

    @property
    def utility_weights(self) -> dict:
        return {
            "w1": self.w1_occupancy,
            "w2": self.w2_preference,
            "w3": self.w3_distribution,
            "w4": self.w4_resources,
            "lambda": self.lambda_penalty,
        }

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = HAIAConfig()
