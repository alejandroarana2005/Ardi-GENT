/* global React, Panel, Tag, Pill, Btn */
const { useState: useStateH, useMemo: useMemoH } = React;

window.ScreenHorario = function ScreenHorario({ data }) {
  const [sel, setSel] = useStateH(null);
  const [filter, setFilter] = useStateH("todos");

  const days = data.DAYS;
  const slots = data.SLOTS;

  const matByCode = useMemoH(() => Object.fromEntries(data.MATERIAS.map(m => [m.code, m])), [data]);
  const profByCode = useMemoH(() => Object.fromEntries(data.PROFS.map(p => [p.code, p])), [data]);

  const cellAsig = (day, slot) =>
    data.ASIGNACIONES.filter(a => a.day === day && a.slot === slot)
      .filter(a => filter === "todos" || matByCode[a.mat]?.fac === filter);

  const colorFor = (m) => {
    // Stable hash → soft hue
    const idx = data.MATERIAS.findIndex(x => x.code === m);
    const hues = [200, 35, 145, 80, 260, 320, 180, 50, 120, 0];
    const h = hues[idx % hues.length];
    return {
      bg: `oklch(0.96 0.04 ${h})`,
      bd: `oklch(0.84 0.07 ${h})`,
      ink: `oklch(0.34 0.10 ${h})`,
    };
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Horario semanal · 2024-A</h1>
          <p className="lede">
            Vista de las 34 asignaciones programadas por el agente. Click en una sesión para ver
            su U(A) componente a componente y los recursos del aula.
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Btn icon="⇅">Comparar v06</Btn>
          <Btn icon="↗">Exportar PDF</Btn>
          <Btn kind="primary" icon="✎">Editar manualmente</Btn>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14, flexWrap: "wrap" }}>
        <span style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.12em", textTransform: "uppercase" }}>Facultad</span>
        {[
          ["todos",      "Todas"],
          ["ingenieria", "Ingeniería"],
          ["ciencias",   "Ciencias"],
        ].map(([k, lbl]) => (
          <button key={k}
            onClick={() => setFilter(k)}
            className="btn"
            style={{
              background: filter === k ? "var(--ink)" : "var(--surface)",
              color: filter === k ? "var(--paper)" : "var(--ink)",
              borderColor: filter === k ? "var(--ink)" : "var(--border-strong)",
            }}>{lbl}</button>
        ))}
        <span style={{ marginLeft: 18, fontSize: 11, color: "var(--muted)", letterSpacing: "0.12em", textTransform: "uppercase" }}>Vista</span>
        <Btn icon="▦">Por aula</Btn>
        <Btn icon="✦">Por docente</Btn>

        <div style={{ marginLeft: "auto", display: "flex", gap: 14, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.12em", textTransform: "uppercase" }}>Leyenda U(A)</span>
          {[["≥ 0.85", "var(--ok)"], ["0.70–0.85", "var(--warn)"], ["< 0.70", "var(--conflict)"]].map(([lbl, c]) => (
            <span key={lbl} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12 }}>
              <span style={{ width: 10, height: 10, background: c, borderRadius: 2 }}></span>{lbl}
            </span>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: sel ? "1fr 320px" : "1fr", gap: 18, alignItems: "start" }}>
        <div className="panel" style={{ padding: 0 }}>
          <div style={{
            display: "grid",
            gridTemplateColumns: `108px repeat(${days.length}, 1fr)`,
            borderBottom: "1px solid var(--border)",
            background: "var(--surface-2)",
          }}>
            <div></div>
            {days.map(d => (
              <div key={d} style={{
                padding: "12px 14px", borderLeft: "1px solid var(--border)",
                fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)",
              }}>{d}</div>
            ))}
          </div>

          {slots.map((s, ri) => (
            <div key={s.code} style={{
              display: "grid",
              gridTemplateColumns: `108px repeat(${days.length}, 1fr)`,
              borderBottom: ri < slots.length - 1 ? "1px solid var(--border)" : "none",
              minHeight: 96,
            }}>
              <div style={{ padding: "10px 14px", background: "var(--surface-2)", borderRight: "1px solid var(--border)" }}>
                <div className="mono" style={{ fontSize: 10, color: "var(--muted-2)", letterSpacing: "0.12em" }}>{s.code}</div>
                <div style={{ fontSize: 12, marginTop: 2 }}>{s.label}</div>
              </div>
              {days.map(d => {
                const items = cellAsig(d, s.code);
                return (
                  <div key={d} style={{
                    borderLeft: "1px solid var(--border)", padding: 6,
                    display: "flex", flexDirection: "column", gap: 4,
                    background: items.length > 1 ? "var(--surface-2)" : "transparent",
                  }}>
                    {items.map(a => {
                      const m = matByCode[a.mat];
                      const c = colorFor(a.mat);
                      const uColor = a.u >= 0.85 ? "var(--ok)" : a.u >= 0.70 ? "var(--warn)" : "var(--conflict)";
                      return (
                        <button key={a.mat + a.g + a.s} onClick={() => setSel(a)} style={{
                          textAlign: "left", padding: "6px 8px",
                          background: c.bg, color: c.ink, border: `1px solid ${c.bd}`,
                          borderRadius: 4, cursor: "pointer", fontFamily: "inherit",
                          position: "relative",
                        }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span className="mono" style={{ fontSize: 10, opacity: 0.75 }}>{a.mat}</span>
                            <span className="mono" style={{ fontSize: 10, opacity: 0.6 }}>G{a.g}</span>
                            <span style={{
                              marginLeft: "auto", width: 6, height: 6, borderRadius: 99, background: uColor,
                            }}></span>
                          </div>
                          <div style={{ fontSize: 12, marginTop: 2, color: "var(--ink)", lineHeight: 1.25 }}>{m?.name}</div>
                          <div style={{ fontSize: 10.5, color: "var(--muted)", marginTop: 2 }}>{a.aula} · {profByCode[a.prof]?.name.replace(/^Dra?\.\s|Mg\.\s|Esp\.\s/, "")}</div>
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {sel ? (
          <Panel
            title={matByCode[sel.mat]?.name}
            meta={sel.mat + " · G" + sel.g + " · S" + sel.s}
            actions={<Btn kind="ghost" onClick={() => setSel(null)}>✕</Btn>}
          >
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span className="serif" style={{ fontSize: 36, letterSpacing: "-0.02em" }}>{sel.u.toFixed(2)}</span>
              <span style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase" }}>U(A)</span>
            </div>

            <div style={{ marginTop: 18, fontSize: 13, lineHeight: 1.7 }}>
              <Row k="Docente"  v={profByCode[sel.prof]?.name} />
              <Row k="Aula"     v={sel.aula + " · cap " + (data.AULAS.find(x => x.code === sel.aula)?.capacity ?? "—")} />
              <Row k="Día / franja" v={sel.day + " · " + (data.SLOTS.find(s => s.code === sel.slot)?.label)} />
              <Row k="Matrícula" v={matByCode[sel.mat]?.mat + " estudiantes"} />
              <Row k="Recursos" v={(data.AULAS.find(x => x.code === sel.aula)?.resources || []).join(", ") || "—"} />
            </div>

            <div style={{ marginTop: 18 }}>
              <div style={{ fontSize: 11, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" }}>Componentes U(A)</div>
              {[
                ["Ocupación",    Math.min(0.99, 0.6 + sel.u * 0.4)],
                ["Preferencia",  sel.u],
                ["Distribución", Math.max(0.4, sel.u - 0.05)],
                ["Recursos",     0.92],
              ].map(([k, v]) => (
                <div key={k} style={{ marginTop: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                    <span>{k}</span><span className="mono">{v.toFixed(2)}</span>
                  </div>
                  <div className="progress"><i style={{ width: (v*100) + "%" }}></i></div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 18, display: "flex", gap: 8 }}>
              <Btn kind="primary" icon="↻">Re-asignar</Btn>
              <Btn icon="✎">Editar</Btn>
            </div>
          </Panel>
        ) : null}
      </div>
    </div>
  );
};

function Row({ k, v }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ color: "var(--muted)" }}>{k}</span>
      <span style={{ textAlign: "right" }}>{v}</span>
    </div>
  );
}
