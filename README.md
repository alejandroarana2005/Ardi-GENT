# HAIA Agent

**Hybrid Adaptive Intelligent Agent** para asignación de salones universitarios.
Universidad de Ibagué — Ingeniería de Sistemas / Agentes Inteligentes.

Basado en el modelo de datos de **La Cruz et al. (2024) "UniSchedApi"**
(DOI: 10.32397/tesea.vol5.n2.633).

---

## Arquitectura

HAIA implementa un agente BDI (Belief-Desire-Intention) con 5 capas funcionales:

```
Percepción → AC-3 Preprocesamiento → Solver CSP/MILP → SA Post-optimización → Re-optimización Dinámica
```

**Función objetivo:**
```
U(A) = w1·U_ocup + w2·U_pref + w3·U_dist + w4·U_rec − λ·Pen(A)
       w1=0.40    w2=0.25    w3=0.20    w4=0.15    λ=1.5
```

**Clasificación del agente:** Agente Basado en Utilidad (Russell & Norvig, 2020).

---

## Estructura del proyecto

```
haia_agent/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Pydantic BaseSettings
│   ├── domain/
│   │   ├── entities.py            # Subject, Classroom, TimeSlot, Professor, Assignment
│   │   ├── constraints.py         # HC1-HC5 (hard) y SC1-SC6 (soft)
│   │   └── objective.py           # Función U(A)
│   ├── layer1_perception/         # Carga y validación de datos
│   ├── layer2_preprocessing/      # Filtro de dominios + AC-3
│   ├── layer3_solver/             # Backtracking / MILP (OR-Tools) / Tabu Search
│   ├── layer4_optimization/       # Simulated Annealing + pesos AHP
│   ├── layer5_dynamic/            # Re-optimización ante eventos en tiempo real
│   ├── bdi/                       # Beliefs, Desires, Intentions, Agent principal
│   ├── api/                       # Rutas FastAPI + schemas Pydantic
│   ├── database/                  # Modelos SQLAlchemy, sesión, repositorios
│   └── reporting/                 # Detector de conflictos y generador de reportes
├── alembic/                       # Migraciones de base de datos
├── tests/
│   └── fixtures/sample_data.py    # 30 materias, 15 aulas, 24 franjas, 20 docentes
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Puesta en marcha

### Con Docker (recomendado)

```bash
cp .env.example .env
docker-compose up --build
```

La API queda disponible en `http://localhost:8000`.
Documentación interactiva: `http://localhost:8000/docs`.

### Local (sin Docker)

Requiere Python 3.11+ y PostgreSQL 16.

```bash
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar DATABASE_URL en .env

# Crear tablas
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Variables de entorno

| Variable | Descripción | Defecto |
|---|---|---|
| `DATABASE_URL` | URL de conexión PostgreSQL | `postgresql://haia_user:haia_pass@localhost:5432/haia_db` |
| `API_HOST` | Host del servidor | `0.0.0.0` |
| `API_PORT` | Puerto | `8000` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `SOLVER_THRESHOLD` | Umbral backtracking → MILP (nº cursos) | `150` |
| `SA_T0` | Temperatura inicial SA | `100.0` |
| `SA_ALPHA` | Factor de enfriamiento SA | `0.95` |
| `W1` — `W4` | Pesos de la función U(A) | `0.40, 0.25, 0.20, 0.15` |

Ver `.env.example` para la lista completa.

---

## API REST

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/v1/health` | Estado del sistema y conexión a BD |
| `POST` | `/api/v1/schedule` | Iniciar ciclo de asignación completo |
| `GET` | `/api/v1/schedule/{id}` | Consultar resultado de una asignación |
| `GET` | `/api/v1/schedule/{id}/assignments` | Listar todas las asignaciones |
| `PUT` | `/api/v1/schedule/{id}/accept` | Aceptar la propuesta generada |
| `DELETE` | `/api/v1/schedule/{id}` | Rechazar y reintentar |
| `POST` | `/api/v1/events` | Reportar evento dinámico |
| `GET` | `/api/v1/events/{schedule_id}` | Historial de eventos |
| `GET` | `/api/v1/metrics/{schedule_id}` | U(A), ocupación, conflictos |
| `GET` | `/api/v1/conflicts/{schedule_id}` | HC violadas |
| `POST` | `/api/v1/subjects` | Crear materia |
| `POST` | `/api/v1/classrooms` | Crear aula |
| `POST` | `/api/v1/timeslots` | Crear franja horaria |
| `POST` | `/api/v1/professors` | Crear docente |

---

## Restricciones implementadas

### Hard Constraints (HC) — nunca se pueden violar

| Código | Descripción |
|---|---|
| HC1 | Un aula no puede tener dos clases en la misma franja |
| HC2 | Un docente no puede dictar dos clases simultáneamente |
| HC3 | El aula debe tener capacidad suficiente para el grupo |
| HC4 | El aula debe disponer de todos los recursos requeridos |
| HC5 | El docente debe estar disponible en la franja asignada |

### Soft Constraints (SC) — penalizan U(A) si se violan

| Código | Descripción | Penalización δ |
|---|---|---|
| SC1 | Respetar preferencias horarias del docente | 0.3 |
| SC2 | Evitar franjas de lunes 07:00 | 0.2 |
| SC3 | No más de 3 horas consecutivas para un docente | 0.4 |
| SC4 | Maximizar ocupación del aula | 0.1 |
| SC5 | Preferir franjas de mañana | 0.15 |
| SC6 | Distribuir carga uniformemente en la semana | 0.25 |

---

## Selección de solver

El `solver_factory.py` selecciona el algoritmo según el tamaño de la instancia:

| Condición | Solver |
|---|---|
| ≤ 150 cursos sin asignar | Backtracking + MRV + LCV + Forward Checking |
| > 150 cursos | MILP con OR-Tools CP-SAT |
| Post-solución | Tabu Search mejorado (memoria larga + criterio de aspiración) |

Tabu Search extiende el algoritmo de La Cruz et al. (2024) con:
- Memoria de largo plazo (frecuencia de uso de slots)
- Criterio de aspiración (acepta movimiento tabú si mejora el óptimo global)
- Integración directa con U(A) como función de evaluación

---

## Eventos dinámicos soportados

| Evento | Acción del agente |
|---|---|
| `CLASSROOM_UNAVAILABLE` | Desasigna cursos del aula → reparación local |
| `PROFESSOR_CANCELLED` | Busca sustituto o nueva franja |
| `ENROLLMENT_SURGE` | Busca aula alternativa con mayor capacidad |
| `SLOT_BLOCKED` | Desasigna cursos en la franja → reparación local |
| `NEW_COURSE_ADDED` | Asigna solo el curso nuevo sin tocar el resto |

Principio de Mínima Perturbación:
`U_repair(A) = U(A) − w_stab · |A_nueva △ A_original|`

Target: < 30 segundos para eventos que afecten ≤ 10 cursos.

---

## Tests

```bash
# Instalar dependencias de test
pip install pytest httpx

# Ejecutar todos los tests
pytest tests/

# Solo tests unitarios
pytest tests/unit/

# Usar datos de prueba
python -c "from tests.fixtures.sample_data import build_sample_instance; print(build_sample_instance().summary())"
```

Los fixtures incluyen datos basados en la Universidad de Ibagué:
30 materias de Ingeniería de Sistemas, 15 aulas, 24 franjas horarias (4 × 6 días), 20 docentes.

---

## Fases de implementación

| Fase | Estado | Contenido |
|---|---|---|
| **Fase 1** | ✅ Completa | Dominio, BD, percepción, API base |
| **Fase 2** | ✅ Completa | AC-3, backtracking MRV/LCV, Tabu Search, POST /schedule |
| **Fase 3** | ✅ Completa | U(A), SA, MILP OR-Tools, GET /metrics |
| **Fase 4** | ✅ Completa | BDI agent, eventos dinámicos, POST /events |
| **Fase 5** | Pendiente | LSTM stub, AHP weights, tests completos |

---

## Referencias

- La Cruz, A. et al. (2024). *UniSchedApi: A comprehensive solution for university resource scheduling and methodology comparison*. TESEA, vol. 5, n. 2. DOI: 10.32397/tesea.vol5.n2.633
- Russell, S. & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson.
