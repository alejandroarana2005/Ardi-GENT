import { useState } from "react";
import { Panel }     from "../components/shared/Panel";
import { Tag }       from "../components/shared/Tag";
import { Btn }       from "../components/shared/Btn";
import { StatusDot } from "../components/shared/StatusDot";
import { mockData as data } from "../data/mockData";
import type { Conflicto } from "../data/mockData";

const TYPE_LABELS: Record<string, string> = {
  CLASSROOM_UNAVAILABLE: "Aula no disponible",
  PROFESSOR_CANCELLED:   "Cancelación de docente",
  ENROLLMENT_SURGE:      "Aumento de matrícula",
  SLOT_BLOCKED:          "Franja bloqueada",
  NEW_COURSE_ADDED:      "Nueva materia",
};

function KPIc({ label, value, unit, delta, kind }: {
  label: string; value: string | number; unit?: string; delta: string; kind?: string;
}) {
  const color = kind === "conflict" ? "var(--conflict)"
    : kind === "ok" ? "var(--ok)"
    : kind === "warn" ? "var(--warn)"
    : "var(--ink)";
  return (
    <div className="kpi" style={{ borderTop: `3px solid ${color}` }}>
      <div className="lbl">{label}</div>
      <div className="num">{value}{unit ? <small>{unit}</small> : null}</div>
      <div className="delta">{delta}</div>
    </div>
  );
}

interface PlanRow { mat: string; slot: string; aula: string; prof: string; u: number; changed?: boolean; }

function Plan({ rows }: { rows: PlanRow[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {rows.map((r, i) => (
        <div key={i} style={{
          padding: 8,
          border: "1px solid " + (r.changed ? "var(--agent)" : "var(--border)"),
          borderRadius: 4, background: "var(--surface)",
          fontSize: 12, display: "grid", gridTemplateColumns: "1fr auto", gap: 4,
        }}>
          <div className="mono" style={{ color: "var(--muted)", fontSize: 11 }}>{r.mat}</div>
          <div className="mono" style={{ fontSize: 11 }}>U {r.u.toFixed(2)}</div>
          <div>{r.slot}</div>
          <div style={{ color: "var(--muted)" }}>{r.aula} · {r.prof}</div>
        </div>
      ))}
    </div>
  );
}

export function Conflictos() {
  const [sel,   setSel]   = useState<Conflicto>(data.CONFLICTOS[0]);
  const [stage, setStage] = useState(0);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Conflictos &amp; reparación dinámica</h1>
          <p className="lede">
            Capa 5 del agente: ante un evento dinámico, HAIA aplica el principio de mínima
            perturbación — ajusta lo necesario sin re-resolver el horario completo.
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Btn icon="◷">Historial de eventos</Btn>
          <Btn kind="primary" icon="+">Reportar evento</Btn>
        </div>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 18 }}>
        <KPIc label="Conflictos abiertos"   value="4"      delta="2 nuevos hoy"                  kind="conflict" />
        <KPIc label="Resueltos · 7 días"    value="11"     delta="100% factibles tras reparación" kind="ok" />
        <KPIc label="Δ utilidad media"      value="-0.018" delta="post-reparación"                kind="warn" />
        <KPIc label="Asignaciones tocadas"  value="2.3"    unit=" prom." delta="principio mín. perturbación" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 18, alignItems: "start" }}>
        <Panel title="Cola de eventos" meta={`${data.CONFLICTOS.length} abiertos`} flush>
          {data.CONFLICTOS.map(c => {
            const active = sel.id === c.id;
            return (
              <button key={c.id} onClick={() => { setSel(c); setStage(0); }} style={{
                width: "100%", textAlign: "left",
                padding: "14px 18px", border: "none",
                background: active ? "var(--surface-2)" : "var(--surface)",
                borderLeft: "3px solid " + (active ? "var(--conflict)" : "transparent"),
                borderBottom: "1px solid var(--border)",
                cursor: "pointer", fontFamily: "inherit",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{c.id}</span>
                  {c.severity === "alta"  ? <Tag kind="hard">alta</Tag>
                  : c.severity === "media" ? <Tag kind="warn">media</Tag>
                  :                          <Tag>baja</Tag>}
                  <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--muted)" }}>{c.ts}</span>
                </div>
                <div style={{ marginTop: 6, fontSize: 14 }}>{TYPE_LABELS[c.type] ?? c.type}</div>
                <div style={{ marginTop: 4, fontSize: 12, color: "var(--muted)" }}>
                  <span className="mono">{c.subject}</span> · {c.afected} asignaciones afectadas
                </div>
              </button>
            );
          })}
        </Panel>

        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <Panel title={`Reparación · ${sel.id}`} meta={`event_type · ${sel.type}`}>
            <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 18 }}>
              {["Detectado", "Diagnóstico", "Propuesta", "Aplicado"].map((s, i) => (
                <div key={s} style={{ display: "contents" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <StatusDot status={i < stage ? "ok" : i === stage ? "run" : "wait"} />
                    <span style={{ fontSize: 12, color: i <= stage ? "var(--ink)" : "var(--muted)" }}>{s}</span>
                  </div>
                  {i < 3 ? <div style={{
                    flex: 1, height: 1, margin: "0 14px",
                    background: i < stage ? "var(--agent)" : "var(--border)",
                    transition: "background 200ms",
                  }}></div> : null}
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
              <div>
                <div className="divider-label" style={{ marginTop: 0 }}>Evento detectado</div>
                <div style={{ fontSize: 13, lineHeight: 1.6 }}>{sel.desc}</div>
                <div style={{ marginTop: 12, fontSize: 12, color: "var(--muted)" }}>
                  Recibido vía POST <span className="mono">/agent/event</span> · payload validado por DynamicEventRequest.
                </div>
              </div>
              <div>
                <div className="divider-label" style={{ marginTop: 0 }}>Asignaciones afectadas</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {[
                    { mat: "ISIS-450", g: 1, s: 1, when: "Mar · 18:00–20:00" },
                    { mat: "ISIS-450", g: 1, s: 2, when: "Jue · 18:00–20:00" },
                  ].map((a, i) => (
                    <div key={i} style={{
                      padding: 8, border: "1px solid var(--border)", borderRadius: 4,
                      display: "flex", alignItems: "center", gap: 10,
                    }}>
                      <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{a.mat} G{a.g} S{a.s}</span>
                      <span style={{ fontSize: 12 }}>{a.when}</span>
                      <Tag kind="hard">a reparar</Tag>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ marginTop: 22, display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <Btn kind="ghost" onClick={() => setStage(0)}>Reiniciar</Btn>
              <Btn kind="primary" icon="▸" onClick={() => setStage(s => Math.min(3, s + 1))}>
                {stage === 0 ? "Diagnosticar"
                : stage === 1 ? "Generar propuesta"
                : stage === 2 ? "Aplicar reparación"
                : "Cerrar evento"}
              </Btn>
            </div>
          </Panel>

          <Panel title="Propuesta del agente" meta="layer5.repair · principio de mínima perturbación">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
              <div className="hairline" style={{ borderRadius: 6, padding: 14, background: "var(--surface-2)" }}>
                <div className="divider-label" style={{ margin: 0, marginBottom: 8 }}>Antes</div>
                <Plan rows={[
                  { mat: "ISIS-450 · G1 · S1", aula: "L-301", slot: "Mar 18:00–20:00", prof: "Severeyn", u: 0.66 },
                  { mat: "ISIS-450 · G1 · S2", aula: "L-301", slot: "Jue 18:00–20:00", prof: "Severeyn", u: 0.65 },
                ]} />
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12, fontSize: 12 }}>
                  <span style={{ color: "var(--muted)" }}>U(A) global</span>
                  <span className="mono">0.842</span>
                </div>
              </div>

              <div className="hairline" style={{ borderRadius: 6, padding: 14, background: "var(--agent-soft)", borderColor: "var(--agent)" }}>
                <div className="divider-label" style={{ margin: 0, marginBottom: 8, color: "var(--agent-ink)" }}>Después de reparar</div>
                <Plan rows={[
                  { mat: "ISIS-450 · G1 · S1", aula: "L-301", slot: "Mié 16:00–18:00", prof: "La Cruz", u: 0.71, changed: true },
                  { mat: "ISIS-450 · G1 · S2", aula: "L-301", slot: "Vie 16:00–18:00", prof: "La Cruz", u: 0.69, changed: true },
                ]} />
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12, fontSize: 12 }}>
                  <span style={{ color: "var(--muted)" }}>U(A) global</span>
                  <span className="mono">0.831 <span style={{ color: "var(--conflict-ink)" }}>(−0.011)</span></span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 16, padding: 12, background: "var(--paper-deep)", borderRadius: 4, fontSize: 12.5, color: "var(--ink-2)" }}>
              <span className="mono" style={{ color: "var(--muted)" }}>HAIA · razonamiento</span>
              <p style={{ margin: "6px 0 0" }}>
                Reasignar a Dr. La Cruz (P-002) preserva la disponibilidad declarada y satisface SC-01
                (preferencia 0.83). Sólo se mueven 2 asignaciones · 0 violaciones HC · ΔU(A) = −0.011.
                Alternativas descartadas: cambio de aula (rompía SC-04 por falta de software_lab) y
                aplazamiento (rompía cohorte semanal).
              </p>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
