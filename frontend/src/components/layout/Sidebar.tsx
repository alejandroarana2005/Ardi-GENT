import { NavLink } from "react-router-dom";

const NAV = [
  { group: "Operación", items: [
    { id: "dashboard",     label: "Panel general",  glyph: "◆", path: "/dashboard" },
    { id: "horario",       label: "Horario",        glyph: "▦", path: "/horario" },
    { id: "conflictos",    label: "Conflictos",     glyph: "△", path: "/conflictos", badge: 4 },
  ]},
  { group: "Agente HAIA", items: [
    { id: "consola",       label: "Consola BDI",    glyph: "✦", path: "/consola" },
    { id: "restricciones", label: "Restricciones",  glyph: "≡", path: "/restricciones" },
  ]},
  { group: "Análisis", items: [
    { id: "reportes",      label: "Reportes",       glyph: "∎", path: "/reportes" },
    { id: "versiones",     label: "Versiones",      glyph: "⌥", path: "/versiones" },
  ]},
];

export function Sidebar() {
  return (
    <aside className="rail">
      <div className="rail-brand">
        <div>
          <div className="logo"><span className="dot"></span>HAIA</div>
          <div className="sub">Universidad de Ibagué</div>
        </div>
      </div>

      {NAV.map(grp => (
        <div key={grp.group}>
          <div className="rail-section">{grp.group}</div>
          {grp.items.map(it => (
            <NavLink
              key={it.id}
              to={it.path}
              className={({ isActive }) => "rail-link" + (isActive ? " active" : "")}
            >
              <span className="glyph">{it.glyph}</span>
              <span>{it.label}</span>
              {it.badge ? <span className="badge">{it.badge}</span> : null}
            </NavLink>
          ))}
        </div>
      ))}

      <div className="rail-foot">
        <span className="led" style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ok)" }}></span>
        <span>API conectada · v0.9.2</span>
      </div>
    </aside>
  );
}
