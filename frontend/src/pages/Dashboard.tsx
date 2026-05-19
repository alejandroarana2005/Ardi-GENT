import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Panel }       from "../components/shared/Panel";
import { KPI }         from "../components/shared/KPI";
import { Btn }         from "../components/shared/Btn";
import { UtilityRing } from "../components/shared/UtilityRing";
import { useSchedule } from "../context/ScheduleContext";
import { useLatestSchedule } from "../hooks/useLatestSchedule";
import { listSchedules } from "../api/endpoints";
import type { ScheduleListItem } from "../api/types";
import { timeAgo, formatMs } from "../lib/dateUtils";

// ─── Capa cards para el desglose de tiempos ──────────────────────────────────

const LAYER_NAMES = ["DataLoader", "AC-3", "Solver", "SA + AHP", "Dyn. Repair"] as const;

// ─── Componente principal ─────────────────────────────────────────────────────

export function Dashboard() {
  const navigate            = useNavigate();
  const { startCycle }      = useSchedule();
  const { schedule, metrics, isLoading, error, refetch } = useLatestSchedule();

  const [history,        setHistory]        = useState<ScheduleListItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    listSchedules({ limit: 5 })
      .then(r  => setHistory(r.items))
      .catch(() => {})
      .finally(() => setHistoryLoading(false));
  }, []);

  async function handleGenerateCycle() {
    try { await startCycle(); } catch { /* error surfaced in consola */ }
    navigate("/consola");
  }

  // ── Estado de carga ───────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="page" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 360 }}>
        <span className="mono" style={{ color: "var(--muted)", fontSize: 13 }}>
          Cargando datos del agente…
        </span>
      </div>
    );
  }

  // ── Estado de error ───────────────────────────────────────────────────────
  if (error) {
    console.error("[Dashboard] Error al cargar datos:", error);
    return (
      <div className="page">
        <Panel title="Error al cargar datos">
          <div style={{ padding: "12px 0 18px", color: "var(--muted)", fontSize: 13 }}>
            No se pudieron cargar los datos del horario. Comprueba que el servidor esté disponible.
          </div>
          <Btn onClick={refetch}>Reintentar</Btn>
        </Panel>
      </div>
    );
  }

  // ── Estado vacío ──────────────────────────────────────────────────────────
  if (!schedule) {
    return (
      <div className="page" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", maxWidth: 480, padding: "60px 0" }}>
          <div style={{ fontSize: 48, marginBottom: 20, opacity: 0.4 }}>📋</div>
          <h2 style={{ marginBottom: 12 }}>No hay horarios generados aún</h2>
          <p style={{ color: "var(--muted)", marginBottom: 28, lineHeight: 1.6 }}>
            Genera tu primer ciclo BDI para ver métricas y resultados aquí.
          </p>
          <Btn kind="primary" icon="▸" onClick={handleGenerateCycle}>
            Generar primer horario
          </Btn>
        </div>
      </div>
    );
  }

  // ── Vista principal con datos reales ──────────────────────────────────────

  const hcv = schedule.hard_constraint_violations ?? 0;
  const lt  = schedule.layer_times;

  return (
    <div className="page">

      {/* Cabecera */}
      <div className="page-head">
        <div>
          <div className="mono" style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.12em" }}>
            ÚLTIMO HORARIO GENERADO
          </div>
          <h1>Semestre {schedule.semester}</h1>
          <p className="lede">
            <span className="mono">ID: {schedule.schedule_id.slice(0, 8)}…</span>
            {"  ·  "}
            {timeAgo(schedule.created_at)}
            {"  ·  solver: "}
            <span className="mono">{schedule.solver_used}</span>
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          <Btn icon="↻" onClick={() => { refetch(); listSchedules({ limit: 5 }).then(r => setHistory(r.items)).catch(() => {}); }}>
            Actualizar
          </Btn>
          <Btn kind="primary" icon="▸" onClick={handleGenerateCycle}>
            Nuevo ciclo
          </Btn>
        </div>
      </div>

      {/* KPI grid */}
      <div className="kpi-grid" style={{ marginBottom: 18 }}>
        <KPI
          label="Utilidad U(A)"
          value={schedule.utility_score.toFixed(4)}
          delta="función objetivo global"
        />
        <KPI
          label="Violaciones HC"
          value={hcv}
          delta={hcv === 0 ? "todas las HC satisfechas" : `${hcv} restricción${hcv !== 1 ? "es" : ""} dura${hcv !== 1 ? "s" : ""}`}
          deltaKind={hcv === 0 ? "up" : "down"}
        />
        <KPI
          label="Asignaciones"
          value={schedule.assigned_courses}
          unit={` / ${schedule.total_courses}`}
          delta="materias programadas"
          deltaKind="up"
        />
        <KPI
          label="Tiempo de cómputo"
          value={schedule.elapsed_seconds.toFixed(1)}
          unit=" s"
          delta="pipeline BDI completo"
        />
      </div>

      {/* Fila intermedia: desglose U(A) + tiempos por capa */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 18 }}>

        {/* Desglose U(A) */}
        <Panel title="Desglose U(A)" meta="capa 4 · post-SA">
          {metrics ? (
            <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
              <UtilityRing value={schedule.utility_score} />
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em",
                  textTransform: "uppercase", marginBottom: 4,
                }}>
                  Componentes
                </div>
                {([
                  ["Ocupación",    metrics.u_occupancy,    "w₁"],
                  ["Preferencias", metrics.u_preference,   "w₂"],
                  ["Distribución", metrics.u_distribution, "w₃"],
                  ["Recursos",     metrics.u_resources,    "w₄"],
                ] as [string, number, string][]).map(([name, val, w]) => (
                  <div key={name} style={{ marginTop: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                      <span>{name}</span>
                      <span className="mono">
                        {val.toFixed(3)}
                        <span style={{ color: "var(--muted-2)", marginLeft: 6 }}>{w}</span>
                      </span>
                    </div>
                    <div className="progress" style={{ marginTop: 4 }}>
                      <i style={{ width: (val * 100) + "%" }}></i>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--muted)", fontSize: 13, padding: "8px 0" }}>
              Métricas no disponibles para este horario.
            </div>
          )}
        </Panel>

        {/* Tiempos por capa */}
        <Panel title="Tiempos por capa" meta={`solver: ${schedule.solver_used}`}>
          {lt ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
              {([
                lt.layer1_ms, lt.layer2_ms, lt.layer3_ms, lt.layer4_ms, lt.layer5_ms,
              ] as (number | null)[]).map((ms, i) => {
                const isL5 = i === 4;
                return (
                  <div key={i} style={{
                    padding: "12px 8px", textAlign: "center",
                    border: "1px solid var(--border)", borderRadius: 6,
                    background: ms != null && ms > 5000 ? "var(--agent-soft)" : "var(--surface-2)",
                  }}>
                    <div className="mono" style={{ fontSize: 9, color: "var(--muted)", letterSpacing: "0.12em" }}>
                      CAPA {i + 1}
                    </div>
                    <div className="serif" style={{ fontSize: 12, marginTop: 3 }}>
                      {LAYER_NAMES[i]}
                    </div>
                    <div className="mono" style={{
                      fontSize: 13, marginTop: 8, fontWeight: 500,
                      color: isL5 ? "var(--muted-2)" : "var(--ink-2)",
                    }}>
                      {isL5 ? "en espera" : ms != null ? formatMs(ms) : "—"}
                    </div>
                    {i === 2 && (
                      <div className="mono" style={{ fontSize: 8.5, color: "var(--muted-2)", marginTop: 2 }}>
                        {schedule.solver_used}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ color: "var(--muted)", fontSize: 13, padding: "8px 0" }}>
              Tiempos no disponibles (horario generado antes de v004).
            </div>
          )}
        </Panel>

      </div>

      {/* Fila inferior: historial + acciones */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 18 }}>

        {/* Historial reciente */}
        <Panel title="Historial reciente" meta="últimos 5 ciclos">
          {historyLoading ? (
            <div style={{ color: "var(--muted)", fontSize: 13 }}>Cargando historial…</div>
          ) : history.length === 0 ? (
            <div style={{ color: "var(--muted)", fontSize: 13 }}>Sin historial disponible.</div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Semestre</th>
                  <th className="num">U(A)</th>
                  <th className="num">HC</th>
                  <th className="num">Tiempo</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, idx) => (
                  <tr
                    key={item.schedule_id}
                    style={{ cursor: "pointer" }}
                    onClick={() => navigate("/horario", { state: { scheduleId: item.schedule_id } })}
                  >
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span className="mono" style={{ fontSize: 11 }}>
                          {new Date(item.created_at).toLocaleDateString("es-CO", {
                            day: "2-digit", month: "short",
                          })}
                        </span>
                        {idx === 0 && (
                          <span style={{
                            fontFamily: "var(--mono)", fontSize: 9,
                            background: "var(--agent-soft)", color: "var(--agent-ink)",
                            padding: "1px 6px", borderRadius: 99,
                            border: "1px solid var(--agent)",
                          }}>
                            activo
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                        {item.semester}
                      </span>
                    </td>
                    <td className="num mono" style={{ fontSize: 12 }}>
                      {item.utility_score != null ? item.utility_score.toFixed(4) : "—"}
                    </td>
                    <td className="num mono" style={{
                      fontSize: 12,
                      color: (item.hard_constraint_violations ?? 0) > 0
                        ? "var(--conflict-ink)"
                        : "oklch(0.42 0.10 145)",
                    }}>
                      {item.hard_constraint_violations ?? "—"}
                    </td>
                    <td className="num mono" style={{ fontSize: 12 }}>
                      {item.elapsed_seconds != null ? item.elapsed_seconds.toFixed(1) + " s" : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>

        {/* Acciones rápidas */}
        <Panel title="Acciones rápidas">
          <div style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 210 }}>
            <Btn kind="primary" icon="▸" onClick={handleGenerateCycle}>
              Generar nuevo ciclo
            </Btn>
            <Btn icon="↗" onClick={() => navigate("/horario")}>
              Ver horario
            </Btn>
            <Btn icon="⚠" onClick={() => navigate("/conflictos")}>
              Eventos
            </Btn>
          </div>
        </Panel>

      </div>
    </div>
  );
}
