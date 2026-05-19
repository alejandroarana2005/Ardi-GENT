/* global React, Panel, KPI, Tag, Pill, Btn, Sparkline, UtilityRing, StatusDot */
const { useState: useStateD } = React;

window.ScreenDashboard = function ScreenDashboard({ data, agentRunning, goto }) {
  const totalAsig = data.ASIGNACIONES.length;
  const totalNeed = data.MATERIAS.reduce((a, m) => a + m.grupos * m.sesiones, 0);
  const okHC = data.RESTRICCIONES.filter(r => r.type === "hard").every(r => r.satisf === 100);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Programación 2024-A en marcha</h1>
          <p className="lede">
            El agente HAIA mantiene un horario factible con 0 violaciones duras.
            Función de utilidad U(A) = 0.842 · 18 grupos · 7 aulas · 8 docentes.
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Btn icon="↗" onClick={() => goto("reportes")}>Exportar PDF</Btn>
          <Btn kind="primary" icon="✦" onClick={() => goto("agente")}>Ver consola del agente</Btn>
        </div>
      </div>

      {/* KPI strip */}
      <div className="kpi-grid" style={{ marginBottom: 18 }}>
        <KPI label="Utilidad U(A)"        value="0.842" delta="+0.011 vs v06"  deltaKind="up" />
        <KPI label="Asignaciones"         value={totalAsig} unit={` / ${totalNeed}`} delta="100% asignadas" deltaKind="up" />
        <KPI label="Violaciones HC"       value="0"     delta="todas las HC satisfechas" deltaKind="up" />
        <KPI label="Tiempo de cómputo"    value="12.4"  unit="s" delta="−2.6 s vs v06" deltaKind="up" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 18 }}>
        {/* Left col */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <Panel
            title="Estado del ciclo de asignación"
            meta="schedule_id · sch_2024A_v07"
            actions={<Btn icon="↻" onClick={() => goto("agente")}>Abrir consola</Btn>}
          >
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10 }}>
              {data.PIPELINE.map((p, i) => (
                <div key={p.key} style={{
                  padding: 14,
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  background: p.status === "run" ? "var(--agent-soft)" : "var(--surface-2)",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <StatusDot status={p.status} />
                    <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>L{p.n}</span>
                  </div>
                  <div className="serif" style={{ fontSize: 15, marginTop: 8 }}>{p.name.split("·")[1]}</div>
                  <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>{p.desc}</div>
                  <div className="mono" style={{ fontSize: 10.5, color: "var(--muted-2)", marginTop: 10 }}>
                    {p.status === "ok" ? `${p.ms} ms` : p.status === "run" ? "en ejecución…" : "—"}
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Eventos recientes del semestre" meta="últimas 24 h">
            <table className="tbl">
              <thead><tr>
                <th>Evento</th><th>Materia / recurso</th>
                <th>Severidad</th><th>Cuándo</th><th></th>
              </tr></thead>
              <tbody>
                {data.CONFLICTOS.map(c => (
                  <tr key={c.id}>
                    <td>
                      <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{c.id}</div>
                      <div>{c.type.replace(/_/g, " ").toLowerCase()}</div>
                    </td>
                    <td><span className="mono">{c.subject}</span></td>
                    <td>
                      {c.severity === "alta"  ? <Tag kind="hard">alta</Tag>
                      : c.severity === "media" ? <Tag kind="warn">media</Tag>
                      :                          <Tag>baja</Tag>}
                    </td>
                    <td style={{ color: "var(--muted)" }}>{c.ts}</td>
                    <td style={{ textAlign: "right" }}>
                      <Btn kind="ghost" onClick={() => goto("conflictos")}>Reparar →</Btn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>

        {/* Right col */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <Panel title="Función de utilidad U(A)" meta="capa 4 · post-SA">
            <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
              <UtilityRing value={0.842} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase" }}>Componentes</div>
                {[
                  ["Ocupación",    0.91, "w₁ 0.40"],
                  ["Preferencia",  0.78, "w₂ 0.25"],
                  ["Distribución", 0.83, "w₃ 0.20"],
                  ["Recursos",     0.86, "w₄ 0.15"],
                ].map(([k, v, w]) => (
                  <div key={k} style={{ marginTop: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                      <span>{k}</span>
                      <span className="mono">{v.toFixed(2)} <span style={{ color: "var(--muted-2)", marginLeft: 6 }}>{w}</span></span>
                    </div>
                    <div className="progress" style={{ marginTop: 4 }}><i style={{ width: (v*100) + "%" }}></i></div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <Panel title="Carga por aula" meta="ratio matrícula / capacidad">
            <div>
              {data.AULAS.slice(0, 6).map(a => {
                const used = data.ASIGNACIONES.filter(x => x.aula === a.code).length;
                const ratio = Math.min(1, used / 12);
                return (
                  <div key={a.code} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                      <span><span className="mono" style={{ color: "var(--muted)" }}>{a.code}</span> · {a.name}</span>
                      <span className="mono">{used} sesiones · cap {a.capacity}</span>
                    </div>
                    <div className={"progress" + (ratio > 0.85 ? " warn" : "")}>
                      <i style={{ width: (ratio * 100) + "%" }}></i>
                    </div>
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title="Próximas decisiones del agente" meta="cola de intenciones">
            <ul style={{ margin: 0, padding: 0, listStyle: "none", fontSize: 13 }}>
              {[
                "Reasignar L-301 ante mantenimiento del jueves.",
                "Recalibrar pesos AHP w₁/w₂ tras encuesta docente.",
                "Comprimir MATE-101 G3 fuera del sábado.",
                "Re-optimizar U(A) (próximo barrido en 14 min).",
              ].map((t, i) => (
                <li key={i} style={{ display: "flex", gap: 10, padding: "8px 0", borderTop: i ? "1px solid var(--border)" : "none" }}>
                  <span className="mono" style={{ color: "var(--muted-2)", fontSize: 11, width: 22 }}>I{i+6}</span>
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>
    </div>
  );
};
