/* global React, Pill, Tag, Btn, Panel, KPI, Sparkline, UtilityRing, StatusDot */
const { useState: useStateSB, useMemo: useMemoSB } = React;

const NAV = [
  { group: "Operación", items: [
    { id: "dashboard",    label: "Panel general",  glyph: "◆" },
    { id: "horario",      label: "Horario",        glyph: "▦" },
    { id: "conflictos",   label: "Conflictos",     glyph: "△", badge: 4 },
  ]},
  { group: "Agente HAIA", items: [
    { id: "agente",       label: "Consola BDI",     glyph: "✦" },
    { id: "restricciones",label: "Restricciones",   glyph: "≡" },
  ]},
  { group: "Análisis", items: [
    { id: "reportes",     label: "Reportes",       glyph: "∎" },
    { id: "versiones",    label: "Versiones",      glyph: "⌥" },
  ]},
];

window.Sidebar = function Sidebar({ route, setRoute }) {
  return (
    <aside className="rail">
      <div className="rail-brand">
        <div>
          <div className="logo"><span className="dot"></span>HAIA</div>
          <div className="sub">Universidad de Ibagué</div>
        </div>
      </div>

      {NAV.map(grp => (
        <React.Fragment key={grp.group}>
          <div className="rail-section">{grp.group}</div>
          {grp.items.map(it => (
            <div
              key={it.id}
              className={"rail-link" + (route === it.id ? " active" : "")}
              onClick={() => setRoute(it.id)}
            >
              <span className="glyph">{it.glyph}</span>
              <span>{it.label}</span>
              {it.badge ? <span className="badge">{it.badge}</span> : null}
            </div>
          ))}
        </React.Fragment>
      ))}

      <div className="rail-foot">
        <span className="led" style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ok)" }}></span>
        <span>API conectada · v0.9.2</span>
      </div>
    </aside>
  );
};

window.TopBar = function TopBar({ route, semestre = "2024-A", agentRunning, onRun }) {
  const titles = {
    dashboard: ["Panel", "Resumen del semestre"],
    horario: ["Horario", "Vista semanal · " + semestre],
    agente: ["Agente", "Consola BDI · 5 capas"],
    conflictos: ["Conflictos", "Eventos dinámicos & reparación"],
    restricciones: ["Restricciones", "Catálogo HC/SC y pesos AHP"],
    reportes: ["Reportes", "Métricas y exportables"],
    versiones: ["Versiones", "Historial y comparación"],
  };
  const [crumb, title] = titles[route] || ["", ""];

  return (
    <header className="topbar">
      <div>
        <div className="crumb">HAIA · {crumb}</div>
        <div className="title serif">{title}</div>
      </div>

      <div className="grow"></div>

      <span className="pill">
        <span className="led" style={{ background: "var(--ink-2)" }}></span>
        <span style={{ fontFamily: "var(--mono)" }}>Semestre</span>
        <span style={{ fontFamily: "var(--mono)", color: "var(--ink)" }}>{semestre}</span>
      </span>

      {agentRunning
        ? <Pill kind="agent">Agente · ejecutando</Pill>
        : <Pill kind="ok">Agente · inactivo</Pill>}

      <Btn icon="◷">Historial</Btn>
      <Btn kind="primary" onClick={onRun}>
        {agentRunning ? "Cancelar ciclo" : "Ejecutar ciclo"}
      </Btn>
    </header>
  );
};
