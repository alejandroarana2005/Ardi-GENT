/* global React, Panel, Btn, Tag, KPI, UtilityRing */

window.ScreenReportes = function ScreenReportes({ data }) {
  // Synthesize trend bars from version history (oldest → newest)
  const versions = [...data.VERSIONES].reverse();
  const maxU = 1.0;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <div className="crumb mono" style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.12em" }}>HORARIO 2024-A · sch_2024A_v07</div>
          <h1>Reporte semestral</h1>
          <p className="lede">
            Métricas exportables generadas por <span className="mono">app.reporting.report_generator</span>.
            Exportable como PDF (3 hojas) y CSV de asignaciones.
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Btn icon="↗">CSV asignaciones</Btn>
          <Btn icon="↗">JSON métricas</Btn>
          <Btn kind="primary" icon="◰">Generar PDF</Btn>
        </div>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 18 }}>
        <KPI label="U(A) final"           value="0.842" delta="objetivo ≥ 0.80"        deltaKind="up" />
        <KPI label="Asignaciones"         value="34"    delta="100% factibles"          deltaKind="up" />
        <KPI label="Ocupación promedio"   value="0.91"  delta="matrícula / capacidad"   />
        <KPI label="Tiempo total"         value="12.4"  unit="s" delta="solver csp_backtracking" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 18 }}>
        <Panel title="Trayectoria de U(A) por versión" meta="histórico del semestre">
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 200, padding: "12px 0" }}>
            {versions.map((v, i) => {
              const h = (v.U / maxU) * 170;
              const isLast = i === versions.length - 1;
              return (
                <div key={v.id} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                  <div className="mono" style={{ fontSize: 10, color: "var(--muted)" }}>{v.U.toFixed(3)}</div>
                  <div style={{
                    width: "100%", height: h,
                    background: isLast ? "var(--agent)" : "var(--paper-deep)",
                    borderTop: "2px solid " + (isLast ? "var(--agent)" : "var(--border-strong)"),
                    borderRadius: "2px 2px 0 0",
                  }}></div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--muted)" }}>v0{i+1}</div>
                </div>
              );
            })}
          </div>
          <div style={{ paddingTop: 10, borderTop: "1px solid var(--border)", display: "flex", gap: 18, fontSize: 12, color: "var(--muted)" }}>
            <span>Δ total · <span className="mono" style={{ color: "var(--ok)" }}>+0.139</span></span>
            <span>Mejor · <span className="mono">v07 (0.842)</span></span>
            <span>Pendiente · <span className="mono">objetivo 0.86</span></span>
          </div>
        </Panel>

        <Panel title="Distribución de cumplimiento" meta="catálogo de restricciones">
          <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
            <UtilityRing value={0.86} size={140} />
            <div style={{ flex: 1 }}>
              {data.RESTRICCIONES.filter(r => r.active).map(r => (
                <div key={r.code} style={{ marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                    <span>
                      <span className="mono" style={{ color: "var(--muted-2)", fontSize: 11, marginRight: 6 }}>{r.code}</span>
                      {r.name}
                    </span>
                    <span className="mono">{r.satisf}%</span>
                  </div>
                  <div className={"progress" + (r.satisf < 70 ? " warn" : "")}>
                    <i style={{ width: r.satisf + "%" }}></i>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Carga por docente" meta="auditoría de equidad" flush>
        <table className="tbl">
          <thead><tr>
            <th>Docente</th><th>Tipo de contrato</th>
            <th className="num">Horas asignadas</th><th className="num">Máx.</th>
            <th>Carga</th><th className="num">Pref. media</th>
          </tr></thead>
          <tbody>
            {data.PROFS.map(p => {
              const ratio = p.load / p.max;
              const pref = 0.55 + ((p.code.charCodeAt(2) % 5) * 0.07);
              return (
                <tr key={p.code}>
                  <td>
                    <div>{p.name}</div>
                    <div className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>{p.code}</div>
                  </td>
                  <td><Tag>{p.contract.replace("_", " ")}</Tag></td>
                  <td className="num">{p.load}h</td>
                  <td className="num" style={{ color: "var(--muted)" }}>{p.max}h</td>
                  <td style={{ width: 220 }}>
                    <div className={"progress" + (ratio > 0.95 ? " warn" : "")}><i style={{ width: ratio * 100 + "%" }}></i></div>
                  </td>
                  <td className="num">
                    <span style={{ color: pref > 0.75 ? "var(--ok)" : pref > 0.55 ? "var(--ink)" : "var(--conflict-ink)" }}>{pref.toFixed(2)}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
    </div>
  );
};
