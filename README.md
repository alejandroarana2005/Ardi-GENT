# HAIA Agent

**Hybrid Adaptive Intelligent Agent** — asignación de salones universitarios.
Universidad de Ibagué — Ingeniería de Sistemas.

---

## Correr la aplicación

### Backend

```bash
cp .env.example .env
docker-compose up --build -d
docker exec haia_agent-api-1 alembic upgrade head
```

API disponible en `http://localhost:8000` · Docs en `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Interfaz disponible en `http://localhost:5173`.

---

## Tecnologías

**Backend:** Python · FastAPI · SQLAlchemy · PostgreSQL · Alembic · OR-Tools · Pydantic · Docker

**Frontend:** TypeScript · React · Vite · React Router · Axios

**Testing:** Pytest · SQLite (in-memory)

---

## Referencia

La Cruz, A., Herrera, L., Cortes, J., García-León, A., y Severeyn, E. (2024). *UniSchedApi: A comprehensive solution for university resource scheduling and methodology comparison*. Transactions on Energy Systems and Engineering Applications, 5(2), 633. https://doi.org/10.32397/tesea.vol5.n2.633
