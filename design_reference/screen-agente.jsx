/* global React, Panel, KPI, Tag, Pill, Btn, StatusDot */
const { useState: useStateA, useEffect: useEffectA, useRef: useRefA } = React;

window.ScreenAgente = function ScreenAgente({ data, agentRunning, onToggle }) {
  const [tick, setTick] = useStateA(0);
  const [trace, setTrace] = useStateA([
    { t: "00:00.000", lvl: "info",  m: "[HAIA BDI-Agent] Iniciando ciclo de asignación — semestre=2024-A, id=sch_2024A_v07" },
    { t: "00:00.412", lvl: "ok",    m: "[Layer1] DataLoader → 312 entidades cargadas · Validator OK · 0 alertas" },
    { t: "00:01.215", lvl: "info",  m: "[Layer2] DomainFilter aplicado · 91 200 → 32 410 candidatos (-64%)" },
    { t: "00:02.216", lvl: "ok",    m: "[Layer2] AC-3 convergió · feasible=true · revisiones=14 802" },
    { t: "00:02.560", lvl: "info",  m: "[Layer3] solver_factory → csp_backtracking (heurística MRV+LCV)" },
    { t: "00:06.342", lvl: "run",   m: "[Layer3] Backtracking · expansiones=18 432 · backtracks=412 · profundidad=14" },
  ]);

  useEffectA(() => {
    if (!agentRunning) return;
    const id = setInterval(() => setTick(t => t + 1), 800);
    return () => clearInterval(id);
  }, [agentRunning]);

  useEffectA(() => {
    if (!agentRunning) return;
    const lines = [
      { lvl: "run",  m: "[Layer3] Backtracking · expansiones={e} · backtracks={b}" },
      { lvl: "info", m: "[Layer3] heurística MRV seleccionó variable=ISIS-220.G3.S2" },
      { lvl: "info", m: "[Layer3] LCV ordenó dominio (12 valores)" },
      { lvl: "ok",   m: "[Layer3] asignación parcial completa · 34/34 · pasando a Layer4" },
      { lvl: "info", m: "[Layer4] SimulatedAnnealing T₀=1.5 cooling=0.97" },
      { lvl: "ok",   m: "[Layer4] U(A) 0.819 → 0.842 (Δ +0.023)" },
    ];
    const next = lines[tick % lines.length];
    if (!next) return;
    const fmt = m => m.replace("{e}", String(18432 + tick * 1124)).replace("{b}", String(412 + tick * 17));
    setTrace(tr => [...tr.slice(-40), {
      t: String((6.342 + tick * 0.8).toFixed(3)).padStart(7, "0").slice(0, 7),
      lvl: next.lvl,
      m: fmt(next.m),
    }]);
  }, [tick, agentRunning]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="crumb mono" style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.12em" }}>
            HAIA — HYBRID ADAPTIVE INTELLIGENT AGENT
          </div>
          <h1>Consola del agente</h1>
          <p className="lede">
            Arquitectura BDI · Agente basado en utilidad (Russell &amp; Norvig, 2020). El pipeline
            ejecuta cinco capas: percepción, preprocesamiento (AC-3), solver (CSP / MILP / Tabu),
            optimización (SA + AHP) y dinámica (reparación).
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          {agentRunning ? <Pill kind="agent">running · cycle 7</Pill> : <Pill kind="ok">idle</Pill>}
          <Btn kind={agentRunning ? "danger" : "primary"} icon={agentRunning ? "■" : "▸"} onClick={onToggle}>
            {agentRunning ? "Detener ciclo" : "Iniciar ciclo"}
          </Btn>
        </div>
      </div>

      {/* Pipeline lane */}
      <Panel
        title="Pipeline de las 5 capas"
        meta="POST /agent/cycle · semester=2024-A"
        style={{ marginBottom: 18 }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14 }}>
          {data.PIPELINE.map((p, i) => (
            <div key={p.key} style={{
              padding: 16, borderRadius: 6,
              border: "1px solid var(--border)",
              background: p.status === "run" ? "var(--agent-soft)"
                       : p.status === "ok"  ? "var(--surface-2)"
                       : "var(--surface)",
              position: "relative",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <StatusDot status={p.status} />
                <div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.12em" }}>
                    LAYER {p.n}
                  </div>
                  <div className="serif" style={{ fontSize: 16 }}>{p.name.split("·")[1]}</div>
                </div>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 8 }}>{p.desc}</div>

              <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed var(--border)" }}>
                {Object.keys(p.detail).length === 0 ? (
                  <div className="mono" style={{ fontSize: 11, color: "var(--muted-2)" }}>esperando upstream…</div>
                ) : (
                  Object.entries(p.detail).map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, padding: "2px 0" }}>
                      <span style={{ color: "var(--muted)" }}>{k}</span>
                      <span className="mono">{String(v)}</span>
                    </div>
                  ))
                )}
              </div>

              <div className="mono" style={{ position: "absolute", top: 10, right: 12, fontSize: 10.5, color: "var(--muted-2)" }}>
                {p.status === "ok" ? `${p.ms} ms` : p.status === "run" ? `${(p.ms/1000).toFixed(1)} s` : "—"}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* BDI mental state */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 18, marginBottom: 18 }}>
        <Panel title="B · Beliefs" meta="estado del entorno">
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {data.BELIEFS.map((b, i) => (
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

        <Panel title="D · Desires" meta="objetivos ponderados">
          {data.DESIRES.map((d, i) => (
            <div key={d.code} style={{ padding: "8px 0", borderTop: i ? "1px solid var(--border)" : "none" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="mono" style={{ color: "var(--muted-2)", fontSize: 11, width: 24 }}>{d.code}</span>
                <span style={{ flex: 1 }}>{d.name}</span>
                {d.status === "fulfilled" ? <Tag kind="ok">fulfilled</Tag>
                 : d.status === "active"   ? <Tag kind="soft">active</Tag>
                 :                           <Tag>monitoring</Tag>}
              </div>
              <div className="progress" style={{ marginTop: 6 }}><i style={{ width: (d.weight * 100) + "%" }}></i></div>
            </div>
          ))}
        </Panel>

        <Panel title="I · Intentions" meta="plan en curso">
          {data.INTENTIONS.map((it, i) => (
            <div key={it.code} style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "10px 0", borderTop: i ? "1px solid var(--border)" : "none",
            }}>
              <StatusDot status={
                it.status === "completed" ? "ok"
                : it.status === "running" ? "run"
                : "wait"
              } />
              <span className="mono" style={{ color: "var(--muted-2)", fontSize: 11 }}>{it.code}</span>
              <span>{it.step}</span>
              <span className="mono" style={{ marginLeft: "auto", color: "var(--muted)", fontSize: 11.5 }}>{it.t}</span>
            </div>
          ))}
        </Panel>
      </div>

      {/* Live log */}
      <Panel title="Trace en vivo" meta={"logger · " + trace.length + " entradas"} actions={<Btn kind="ghost" icon="↓">Descargar</Btn>}>
        <div style={{
          background: "#1c1a16", color: "#e3dccd",
          fontFamily: "var(--mono)", fontSize: 12, lineHeight: 1.55,
          padding: 14, borderRadius: 4, maxHeight: 280, overflowY: "auto",
        }}>
          {trace.map((l, i) => {
            const color = l.lvl === "ok" ? "oklch(0.78 0.13 145)"
                       : l.lvl === "run" ? "oklch(0.85 0.10 200)"
                       : l.lvl === "warn" ? "oklch(0.80 0.13 80)"
                       : "rgba(227,220,205,0.85)";
            return (
              <div key={i}>
                <span style={{ color: "rgba(227,220,205,0.45)" }}>{l.t} </span>
                <span style={{ color: "rgba(227,220,205,0.55)", textTransform: "uppercase" }}>{l.lvl.padEnd(4)} </span>
                <span style={{ color }}>{l.m}</span>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
};
