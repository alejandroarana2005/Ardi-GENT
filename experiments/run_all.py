"""
Ejecuta los 4 experimentos en secuencia.
Cada uno captura sus propias excepciones para que un fallo no cancele los siguientes.
"""

from __future__ import annotations

import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s — %(message)s",
)
logger = logging.getLogger("[run_all]")


def _run(name: str, fn) -> bool:
    t0 = time.perf_counter()
    logger.info(f"{'='*60}")
    logger.info(f"Iniciando {name}")
    logger.info(f"{'='*60}")
    try:
        fn()
        elapsed = time.perf_counter() - t0
        logger.info(f"{name} completado en {elapsed:.1f}s")
        return True
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.exception(f"{name} FALLÓ después de {elapsed:.1f}s: {exc}")
        return False


def main() -> None:
    from experiments.exp1_scalability    import run_experiment as exp1
    from experiments.exp2_sa_iterations  import run_experiment as exp2
    from experiments.exp3_solver_comparison import run_experiment as exp3
    from experiments.exp4_dynamic_events import run_experiment as exp4

    results = {
        "Exp1 Scalability":     _run("Exp1 Scalability",     exp1),
        "Exp2 SA Iterations":   _run("Exp2 SA Iterations",   exp2),
        "Exp3 Solver Comparison": _run("Exp3 Solver Comparison", exp3),
        "Exp4 Dynamic Events":  _run("Exp4 Dynamic Events",  exp4),
    }

    logger.info("=" * 60)
    logger.info("RESUMEN:")
    for name, ok in results.items():
        status = "OK" if ok else "FAILED"
        logger.info(f"  {status:6s}  {name}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
