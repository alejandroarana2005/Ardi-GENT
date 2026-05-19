import { useState, useEffect, useRef } from "react";
import { Panel }       from "../components/shared/Panel";
import { Tag }         from "../components/shared/Tag";
import { Pill }        from "../components/shared/Pill";
import { Btn }         from "../components/shared/Btn";
import { StatusDot }   from "../components/shared/StatusDot";
import { useSchedule } from "../context/ScheduleContext";
import {
  listSubjects, listClassrooms, listProfessors, listTimeslots,
} from "../api/endpoints";
import type { LayerTimes } from "../api/types";
import type { PollingStatus } from "../hooks/useSchedulePolling";

// ─── Time helpers ─────────────────────────────────────────────────────────────

function formatSeconds(ms: number): string {
  if (ms < 1000)  return (ms / 1000).toFixed(2) + " s";
  if (ms < 10000) return (ms / 1000).toFixed(1)  + " s";
  return Math.round(ms / 1000) + " s";
}

/** Wall-clock relative timestamp mm:ss.SSS from startMs */
function relTs(startMs: number): string {
  const diff = Math.max(0, Date.now() - startMs);
  const min  = Math.floor(diff / 60000);
  const sec  = Math.floor((diff % 60000) / 1000);
  const ms   = diff % 1000;
  return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}.${String(ms).padStart(3, "0")}`;
}

/** Cumulative timestamp from backend execution time: mm:ss.SSS */
function formatTimestamp(ms: number): string {
  const totalSec = ms / 1000;
  const min      = Math.floor(totalSec / 60);
  const sec      = totalSec - min * 60;
  return `${min.toString().padStart(2, "0")}:${sec.toFixed(3).padStart(6, "0")}`;
}

// ─── Layer timestamp accumulator ─────────────────────────────────────────────

function buildLayerTimestamps(lt: LayerTimes): Record<string, number> {
  const cum: Record<string, number> = {};
  let total = 0;
  for (let i = 1; i <= 5; i++) {
    const ms = lt[`layer${i}_ms` as keyof LayerTimes];
    if (ms !== null && ms !== undefined) {
      total += ms;
      cum[`layer${i}`] = total;
    }
  }
  return cum;
}

// ─── Estimated total for progress bar (based on production measurements) ─────

const ESTIMATED_TOTAL_MS = 40_000;

// ─── Layer status — derived from API data, no hardcoded thresholds ────────────

type LayerStat = "wait" | "run" | "ok" | "standby";

function layerStatus(i: number, ps: PollingStatus, lt: LayerTimes | null): LayerStat {
  if (i === 4) {
    if (ps === "completed") return lt?.layer5_ms != null ? "ok" : "standby";
    return "wait";
  }
  if (ps === "idle")      return "wait";
  if (ps === "running")   return "run";
  if (ps === "completed") return "ok";
  if (ps === "failed")    return "wait";
  return "wait";
}

// ─── Layer metadata ───────────────────────────────────────────────────────────

const LAYER_META = [
  {
    label: "DataLoader",
    desc:  "Carga entidades desde la BD y valida integridad referencial.",
  },
  {
    label: "DomainFilter · AC-3",
    desc:  "Propaga restricciones, reduce dominios y verifica factibilidad.",
  },
  {
    label: "Solver híbrido",
    desc:  "Selecciona automáticamente entre CSP, Tabu Search o MILP según tamaño de instancia (factory pattern).",
  },
  {
    label: "SA + AHP Optimizer",
    desc:  "Refinamiento por Simulated Annealing con pesos AHP calibrados.",
  },
  {
    label: "Dynamic Repair",
    desc:  "Aplica correcciones ante eventos dinámicos post-asignación. Se activa solo con POST /events.",
  },
];

// ─── Desires ──────────────────────────────────────────────────────────────────

const DESIRES_DEF = [
  { code: "D1", name: "Maximizar U(A)",            weight: 0.40 },
  { code: "D2", name: "Satisfacer todas las HC",   weight: 1.00 },
  { code: "D3", name: "Minimizar perturbación",    weight: 0.25 },
  { code: "D4", name: "Reducir tiempo de cómputo", weight: 0.15 },
  { code: "D5", name: "Equidad entre docentes",    weight: 0.20 },
];

function desireStatus(code: string, ps: PollingStatus): string {
  if (ps === "idle")      return "pending";
  if (ps === "running")   return "active";
  if (ps === "completed") return code === "D1" || code === "D2" ? "fulfilled" : "active";
  if (ps === "failed")    return code === "D2" ? "violated" : "monitoring";
  return "monitoring";
}

// ─── Intentions ───────────────────────────────────────────────────────────────

const INTENTION_STEPS = ["Percibir", "Preparar", "Resolver", "Optimizar", "Persistir"];

function intentionTime(i: number, ps: PollingStatus, lt: LayerTimes | null): string {
  if (i === 4) return "—";
  if (ps === "idle" || ps === "failed") return "—";
  if (ps === "running") return "";
  if (!lt) return "—";
  const ms = lt[`layer${i + 1}_ms` as keyof LayerTimes];
  if (ms === null || ms === undefined) return "—";
  return formatSeconds(ms);
}

// ─── BDI Progress Bar ─────────────────────────────────────────────────────────

interface BdiProgressBarProps { elapsedMs: number; }

function BdiProgressBar({ elapsedMs }: BdiProgressBarProps) {
  const progress = Math.min(elapsedMs / ESTIMATED_TOTAL_MS, 0.95);
  const pct      = Math.round(progress * 100);
  const elapsedS = Math.round(elapsedMs / 1000);

  let message: string;
  if      (elapsedMs < 2_000)  message = "Inicializando agente BDI...";
  else if (elapsedMs < 5_000)  message = "Capas 1 y 2: percepción y filtrado de dominios...";
  else if (elapsedMs < 10_000) message = "Capa 3: aplicando solver híbrido...";
  else                         message = "Capa 4: optimizando con Simulated Annealing (~85% del tiempo total)...";

  return (
    <div style={{
      padding: "16px 20px", marginBottom: 18, borderRadius: 6,
      border: "1px solid var(--border)", background: "var(--surface-2)",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10, alignItems: "center" }}>
        <span style={{ fontSize: 13, color: "var(--ink-2)" }}>Procesando ciclo BDI…</span>
        <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>
          {elapsedS} s / ~{ESTIMATED_TOTAL_MS / 1000} s
        </span>
      </div>
      <div style={{
        height: 8, background: "var(--border)", borderRadius: 4,
        overflow: "hidden", marginBottom: 10,
      }}>
        <div style={{
          height: "100%",
          width: `${pct}%`,
          borderRadius: 4,
          background: "var(--agent)",
          backgroundImage: "linear-gradient(90deg, var(--agent) 0%, oklch(0.65 0.10 200) 50%, var(--agent) 100%)",
          backgroundSize: "200% 100%",
          animation: "bdi-shimmer 1.8s ease-in-out infinite",
          transition: "width 0.8s ease",
        }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 11.5, color: "var(--muted)", fontStyle: "italic" }}>{message}</span>
        <span className="mono" style={{ fontSize: 11.5, color: "var(--agent-ink)", fontWeight: 500 }}>{pct}%</span>
      </div>
    </div>
  );
}

// ─── Log types ────────────────────────────────────────────────────────────────

interface LogLine { t: string; lvl: string; m: string; }

// ─── Component ────────────────────────────────────────────────────────────────

export function ConsolaBDI() {
  const {
    activeScheduleId, pollingStatus, metrics, error, elapsedMs,
    layerTimes, scheduleDetail,
    startCycle, cancelTracking,
  } = useSchedule();

  const isRunning  = pollingStatus === "running";
  const isComplete = pollingStatus === "completed";
  const isFailed   = pollingStatus === "failed";

  // ── Catalog ──────────────────────────────────────────────────────────────────
  const [catalog, setCatalog] = useState<{
    subjects: number; classrooms: number; professors: number; timeslots: number;
  } | null>(null);
  const catalogRef = useRef(catalog);
  useEffect(() => { catalogRef.current = catalog; }, [catalog]);

  useEffect(() => {
    Promise.all([listSubjects(), listClassrooms(), listProfessors(), listTimeslots()])
      .then(([s, c, p, t]) => setCatalog({
        subjects: s.length, classrooms: c.length,
        professors: p.length, timeslots: t.length,
      }))
      .catch(() => {});
  }, []);

  // ── Schedule detail ref (for use inside effects without stale closures) ───────
  const scheduleDetailRef = useRef(scheduleDetail);
  useEffect(() => { scheduleDetailRef.current = scheduleDetail; }, [scheduleDetail]);

  // ── Trace log ─────────────────────────────────────────────────────────────────
  const [logs, setLogs]          = useState<LogLine[]>([]);
  const logsRef                  = useRef<LogLine[]>([]);
  const startTimeRef             = useRef<number | null>(null);
  const prevSidRef               = useRef<string | null>(null);
  const pollCountRef             = useRef(0);
  const completionLoggedRef      = useRef(false);

  function pushLogs(lines: LogLine[]) {
    if (lines.length === 0) return;
    const next = [...logsRef.current, ...lines];
    logsRef.current = next;
    setLogs(next);
  }

  // 1) New / reset cycle — emit start lines only
  useEffect(() => {
    if (!activeScheduleId) {
      prevSidRef.current          = null;
      startTimeRef.current        = null;
      pollCountRef.current        = 0;
      completionLoggedRef.current = false;
      logsRef.current             = [];
      setLogs([]);
      return;
    }
    if (activeScheduleId === prevSidRef.current) return;
    prevSidRef.current          = activeScheduleId;
    startTimeRef.current        = Date.now();
    pollCountRef.current        = 0;
    completionLoggedRef.current = false;

    const st       = startTimeRef.current;
    const shortId  = activeScheduleId.slice(0, 8);
    const init: LogLine[] = [
      { t: relTs(st), lvl: "info", m: "[HAIA] Iniciando ciclo de asignación · semestre=2024-A" },
      { t: relTs(st), lvl: "info", m: `[HAIA] Schedule creado · id=${shortId}…` },
    ];
    logsRef.current = init;
    setLogs(init);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeScheduleId]);

  // 2) Honest poll lines during running — one entry per poll tick (no synthetic events)
  useEffect(() => {
    if (pollingStatus !== "running") return;
    if (!startTimeRef.current)       return;
    if (elapsedMs === 0)             return; // skip initial state before first poll

    pollCountRef.current += 1;
    const st = startTimeRef.current;
    pushLogs([{
      t:   relTs(st),
      lvl: "info",
      m:   `[Poll #${pollCountRef.current}] Estado: running · elapsed=${Math.round(elapsedMs / 1000)} s`,
    }]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elapsedMs, pollingStatus]);

  // 3) Terminal: completed with real layer timestamps OR failed
  useEffect(() => {
    if (completionLoggedRef.current) return;
    if (!startTimeRef.current)       return;

    if (pollingStatus === "completed" && metrics) {
      completionLoggedRef.current = true;
      const st  = startTimeRef.current;
      const lt  = layerTimes;
      const sd  = scheduleDetailRef.current;
      const cat = catalogRef.current;
      const lines: LogLine[] = [];

      if (lt) {
        // Real cumulative timestamps from backend measurements
        const cum = buildLayerTimestamps(lt);

        if (cum.layer1 !== undefined) {
          lines.push({
            t: formatTimestamp(cum.layer1), lvl: "ok",
            m: `[Layer1] DataLoader · ${cat?.subjects ?? "?"} materias, ${cat?.classrooms ?? "?"} aulas`,
          });
        }
        if (cum.layer2 !== undefined) {
          lines.push({
            t: formatTimestamp(cum.layer2), lvl: "ok",
            m: "[Layer2] DomainFilter + AC-3 · feasible=true",
          });
        }
        if (cum.layer3 !== undefined) {
          lines.push({
            t: formatTimestamp(cum.layer3), lvl: "ok",
            m: `[Layer3] ${sd?.solver_used ?? "solver"} · ${metrics.total_assignments} asignaciones · feasible=true`,
          });
        }
        if (cum.layer4 !== undefined) {
          lines.push({
            t: formatTimestamp(cum.layer4), lvl: "ok",
            m: `[Layer4] SA convergió · U(A)=${metrics.utility_score.toFixed(4)}`,
          });
          lines.push({
            t: formatTimestamp(cum.layer4), lvl: "ok",
            m: `[HAIA] Ciclo completado · HC=${metrics.hard_constraint_violations} · ${metrics.total_assignments} asignaciones`,
          });
        }
      } else {
        // Old schedule without layer_times — single completion line
        lines.push({
          t: relTs(st), lvl: "ok",
          m: `[HAIA] Ciclo completado · HC=${metrics.hard_constraint_violations} · ${metrics.total_assignments} asignaciones · (telemetría no disponible)`,
        });
      }
      pushLogs(lines);
      return;
    }

    if (pollingStatus === "failed") {
      completionLoggedRef.current = true;
      const st = startTimeRef.current ?? Date.now();
      pushLogs([{
        t: relTs(st), lvl: "err",
        m: `[Error] ${error ?? "el agente no pudo generar un horario factible"}`,
      }]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollingStatus, metrics, layerTimes]);

  // ── Beliefs ───────────────────────────────────────────────────────────────────
  const sidDisplay = activeScheduleId
    ? activeScheduleId.length > 26 ? `${activeScheduleId.slice(0, 26)}…` : activeScheduleId
    : "—";

  const beliefs: string[] = [
    `instance.semester = '2024-A'`,
    catalog
      ? `instance.subjects = ${catalog.subjects}  ·  classrooms = ${catalog.classrooms}`
      : `instance.subjects = …  ·  classrooms = …`,
    catalog
      ? `instance.professors = ${catalog.professors}  ·  timeslots = ${catalog.timeslots}`
      : `instance.professors = …  ·  timeslots = …`,
    `ac3.feasible = ${isComplete ? "true" : isFailed ? "false" : "—"}`,
    `active_schedule_id = ${sidDisplay}`,
    isComplete && metrics
      ? `utility_score = ${metrics.utility_score.toFixed(4)}  ·  hcv = ${metrics.hard_constraint_violations}`
      : `utility_score = —`,
  ];

  async function handleStart() {
    try { await startCycle(); } catch { /* surfaces via context */ }
  }

  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="page">

      {/* Header */}
      <div className="page-head">
        <div>
          <div className="mono" style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.12em" }}>
            HAIA — HYBRID ADAPTIVE INTELLIGENT AGENT
          </div>
          <h1>Consola del agente</h1>
          <p className="lede">
            Arquitectura BDI · Agente basado en utilidad (Russell &amp; Norvig, 2020). El pipeline ejecuta
            cinco capas: percepción, preprocesamiento (AC-3), solver (CSP / MILP / Tabu), optimización
            (SA + AHP) y dinámica (reparación).
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          {isRunning  && <Pill kind="agent">running · {(elapsedMs / 1000).toFixed(0)} s</Pill>}
          {isComplete && <Pill kind="ok">completado</Pill>}
          {isFailed   && <Pill kind="ok">fallido</Pill>}
          {!isRunning && !isComplete && !isFailed && <Pill kind="ok">idle</Pill>}
          <Btn
            kind={isRunning ? "danger" : "primary"}
            icon={isRunning ? "■" : "▸"}
            onClick={isRunning ? cancelTracking : handleStart}
          >
            {isRunning ? "Detener ciclo" : isComplete ? "Nuevo ciclo" : "Iniciar ciclo"}
          </Btn>
        </div>
      </div>

      {/* Error banner */}
      {isFailed && (
        <div style={{
          padding: "12px 16px", marginBottom: 18, borderRadius: 6,
          background: "oklch(0.95 0.04 15)", border: "1px solid oklch(0.80 0.12 15)",
          color: "oklch(0.35 0.12 15)", fontFamily: "var(--mono)", fontSize: 12,
        }}>
          ✗ {error ?? "El agente no pudo generar un horario factible."}
        </div>
      )}

      {/* Progress bar — visible only during running */}
      {isRunning && <BdiProgressBar elapsedMs={elapsedMs} />}

      {/* Metrics banner — visible only after completion */}
      {isComplete && metrics && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14, marginBottom: 18 }}>
          {([
            ["U(A) total",   metrics.utility_score.toFixed(4)],
            ["U_ocup",       metrics.u_occupancy.toFixed(4)],
            ["U_pref",       metrics.u_preference.toFixed(4)],
            ["U_dist",       metrics.u_distribution.toFixed(4)],
            ["Asignaciones", String(metrics.total_assignments)],
          ] as [string, string][]).map(([label, val]) => (
            <div key={label} style={{
              padding: "14px 16px", borderRadius: 6,
              border: "1px solid var(--border)", background: "var(--surface-2)",
            }}>
              <div className="mono" style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.1em", marginBottom: 4 }}>
                {label}
              </div>
              <div className="serif" style={{ fontSize: 22, color: "var(--ink)" }}>{val}</div>
            </div>
          ))}
        </div>
      )}

      {/* Pipeline */}
      <Panel title="Pipeline de las 5 capas" meta="POST /schedule · semester=2024-A" style={{ marginBottom: 18 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
          {LAYER_META.map((lm, i) => {
            const stat      = layerStatus(i, pollingStatus, layerTimes);
            const isStandby = stat === "standby";

            // Time badge: real data after completion, nothing during run or wait
            let timeBadge: string | null = null;
            if (isStandby) {
              timeBadge = "—";
            } else if (stat === "ok") {
              if (layerTimes) {
                const ms = layerTimes[`layer${i + 1}_ms` as keyof LayerTimes];
                timeBadge = (ms !== null && ms !== undefined) ? formatSeconds(ms) : "—";
              } else {
                timeBadge = "—"; // completed but pre-migration schedule
              }
            }
            // stat === "run" or "wait": no badge rendered

            return (
              <div key={i} style={{
                padding: 16, borderRadius: 6,
                border: "1px solid var(--border)",
                background: stat === "run" ? "var(--agent-soft)"
                          : stat === "ok"  ? "var(--surface-2)"
                          : "var(--surface)",
                position: "relative",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <StatusDot status={isStandby ? "wait" : stat as "ok" | "run" | "wait"} />
                  <div>
                    <div className="mono" style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.12em" }}>
                      LAYER {i + 1}
                    </div>
                    <div className="serif" style={{ fontSize: 15 }}>{lm.label}</div>
                    {i === 2 && stat === "ok" && scheduleDetail?.solver_used && (
                      <div className="mono" style={{ fontSize: 10, color: "var(--ink-2)", marginTop: 2 }}>
                        {scheduleDetail.solver_used}
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 8 }}>{lm.desc}</div>

                <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed var(--border)" }}>
                  {isStandby ? (
                    <div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
                      en espera de eventos dinámicos
                    </div>
                  ) : stat === "wait" ? (
                    <div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>
                      esperando upstream…
                    </div>
                  ) : stat === "run" ? (
                    <div className="mono" style={{ fontSize: 11, color: "var(--agent-ink)" }}>
                      procesando…
                    </div>
                  ) : stat === "ok" && i === 3 && metrics ? (
                    <>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, padding: "2px 0" }}>
                        <span style={{ color: "var(--muted)" }}>U(A)</span>
                        <span className="mono">{metrics.utility_score.toFixed(4)}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, padding: "2px 0" }}>
                        <span style={{ color: "var(--muted)" }}>penalty</span>
                        <span className="mono">{metrics.penalty.toFixed(4)}</span>
                      </div>
                    </>
                  ) : stat === "ok" ? (
                    <div className="mono" style={{ fontSize: 11, color: "oklch(0.78 0.13 145)" }}>completado ✓</div>
                  ) : null}
                </div>

                {timeBadge !== null && (
                  <div className="mono" style={{
                    position: "absolute", top: 10, right: 12,
                    fontSize: 10.5, color: "var(--muted-2)",
                  }}>
                    {timeBadge}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Panel>

      {/* BDI panels */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 18, marginBottom: 18 }}>

        {/* Beliefs */}
        <Panel title="B · Beliefs" meta="estado del entorno">
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {beliefs.map((b, i) => (
              <li key={i} className="mono" style={{
                fontSize: 11.5, padding: "5px 0",
                borderTop: i ? "1px solid var(--border)" : "none",
                color: "var(--ink-2)",
              }}>
                <span style={{ color: "var(--muted-2)" }}>›</span> {b}
              </li>
            ))}
          </ul>
        </Panel>

        {/* Desires */}
        <Panel title="D · Desires" meta="objetivos ponderados">
          {DESIRES_DEF.map((d, i) => {
            const ds = desireStatus(d.code, pollingStatus);
            return (
              <div key={d.code} style={{ padding: "8px 0", borderTop: i ? "1px solid var(--border)" : "none" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="mono" style={{ color: "var(--muted-2)", fontSize: 11, width: 24 }}>{d.code}</span>
                  <span style={{ flex: 1 }}>{d.name}</span>
                  {ds === "fulfilled" ? <Tag kind="ok">fulfilled</Tag>
                  : ds === "active"   ? <Tag kind="soft">active</Tag>
                  : ds === "violated" ? <Tag kind="warn">violated</Tag>
                  :                     <Tag>{ds}</Tag>}
                </div>
                <div className="progress" style={{ marginTop: 6 }}>
                  <i style={{ width: (d.weight * 100) + "%" }}></i>
                </div>
              </div>
            );
          })}
        </Panel>

        {/* Intentions — real times from layer_times, nothing during running */}
        <Panel title="I · Intentions" meta="plan en curso">
          {INTENTION_STEPS.map((step, i) => {
            const ls    = layerStatus(i, pollingStatus, layerTimes);
            const iTime = intentionTime(i, pollingStatus, layerTimes);
            return (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "10px 0", borderTop: i ? "1px solid var(--border)" : "none",
              }}>
                <StatusDot status={ls === "standby" ? "wait" : ls as "ok" | "run" | "wait"} />
                <span className="mono" style={{ color: "var(--muted-2)", fontSize: 11 }}>I{i + 1}</span>
                <span>{step}</span>
                {iTime !== "" && (
                  <span className="mono" style={{ marginLeft: "auto", color: "var(--muted)", fontSize: 11.5 }}>
                    {iTime}
                  </span>
                )}
              </div>
            );
          })}
        </Panel>
      </div>

      {/* Trace en vivo — honest polling log + real layer timestamps on completion */}
      <Panel
        title="Trace en vivo"
        meta={`logger · ${logs.length} entradas`}
        actions={<Btn kind="ghost" icon="↓">Descargar</Btn>}
      >
        <div style={{
          background: "#1c1a16", color: "#e3dccd",
          fontFamily: "var(--mono)", fontSize: 12, lineHeight: 1.55,
          padding: 14, borderRadius: 4, maxHeight: 280, overflowY: "auto",
        }}>
          {logs.length === 0 ? (
            <span style={{ color: "rgba(227,220,205,0.35)" }}>Esperando inicio del ciclo…</span>
          ) : (
            logs.map((l, i) => {
              const color = l.lvl === "ok"  ? "oklch(0.78 0.13 145)"
                         : l.lvl === "err" ? "oklch(0.70 0.18 15)"
                         : "rgba(227,220,205,0.75)";
              return (
                <div key={i}>
                  <span style={{ color: "rgba(227,220,205,0.40)" }}>{l.t} </span>
                  <span style={{ color: "rgba(227,220,205,0.50)", textTransform: "uppercase" }}>
                    {l.lvl.padEnd(4, " ")}{" "}
                  </span>
                  <span style={{ color }}>{l.m}</span>
                </div>
              );
            })
          )}
        </div>
      </Panel>
    </div>
  );
}
