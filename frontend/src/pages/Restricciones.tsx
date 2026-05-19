import { useState } from "react";
import { Panel } from "../components/shared/Panel";
import { Tag }   from "../components/shared/Tag";
import { Btn }   from "../components/shared/Btn";
import { mockData as data } from "../data/mockData";

function Toggle({ checked, disabled }: { checked: boolean; disabled?: boolean }) {
  return (
    <button disabled={disabled} style={{
      width: 32, height: 18, borderRadius: 99,
      background: checked ? "var(--agent)" : "var(--border-strong)",
      border: "none", padding: 0, position: "relative",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.6 : 1,
    }}>
      <span style={{
        position: "absolute", top: 2, left: checked ? 16 : 2,
        width: 14, height: 14, borderRadius: "50%", background: "white",
        transition: "left 120ms",
      }}></span>
    </button>
  );
}

function CatalogoTab() {
  const hard = data.RESTRICCIONES.filter(r => r.type === "hard");
  const soft = data.RESTRICCIONES.filter(r => r.type === "soft");
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
      <Panel title="Restricciones duras (HC)" meta={`${hard.length} activas · 100% satisfechas`} flush>
        <table className="tbl">
          <thead><tr><th>Código</th><th>Restricción</th><th className="num">Satisf.</th><th></th></tr></thead>
          <tbody>
            {hard.map(r => (
              <tr key={r.code}>
                <td><span className="mono" style={{ color: "var(--muted)" }}>{r.code}</span></td>
                <td>
                  <div>{r.name}</div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2 }}>{r.desc}</div>
                </td>
                <td className="num"><Tag kind="ok">{r.satisf}%</Tag></td>
                <td style={{ textAlign: "right" }}><Toggle checked={r.active} disabled /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel title="Restricciones blandas (SC)" meta={`${soft.length} · ponderan U(A)`} flush>
        <table className="tbl">
          <thead><tr><th>Código</th><th>Restricción</th><th className="num">Cumpl.</th><th></th></tr></thead>
          <tbody>
            {soft.map(r => (
              <tr key={r.code}>
                <td><span className="mono" style={{ color: "var(--muted)" }}>{r.code}</span></td>
                <td>
                  <div>{r.name}</div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2 }}>{r.desc}</div>
                </td>
                <td className="num">
                  {r.active ? (
                    r.satisf >= 80 ? <Tag kind="ok">{r.satisf}%</Tag>
                    : r.satisf >= 60 ? <Tag kind="warn">{r.satisf}%</Tag>
                    : <Tag kind="hard">{r.satisf}%</Tag>
                  ) : <span style={{ color: "var(--muted-2)", fontSize: 11 }}>desactivada</span>}
                </td>
                <td style={{ textAlign: "right" }}><Toggle checked={r.active} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}

function AhpTab() {
  const ahp = data.AHP;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 18 }}>
      <Panel title="Matriz pareada de criterios" meta="Saaty (1980) · método del eigenvector">
        <div style={{ display: "grid", gridTemplateColumns: "120px repeat(4, 1fr)", gap: 0, fontSize: 12 }}>
          <div></div>
          {ahp.labels.map(l => (
            <div key={l} style={{ padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11, color: "var(--muted)", textAlign: "center", letterSpacing: "0.06em", textTransform: "uppercase" }}>{l}</div>
          ))}
          {ahp.labels.map((row, i) => (
            <div key={row} style={{ display: "contents" }}>
              <div style={{ padding: "10px 8px", fontFamily: "var(--mono)", fontSize: 11, color: "var(--muted)", letterSpacing: "0.06em", textTransform: "uppercase", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center" }}>{row}</div>
              {ahp.labels.map((col, j) => {
                const v = ahp.matrix[i][j];
                const isDiag = i === j;
                const above  = i < j;
                return (
                  <div key={col} style={{
                    padding: 10, borderTop: "1px solid var(--border)", borderLeft: "1px solid var(--border)",
                    background: isDiag ? "var(--surface-2)" : above ? "var(--surface)" : "var(--paper-deep)",
                    textAlign: "center",
                  }}>
                    {isDiag ? <span className="mono" style={{ color: "var(--muted-2)" }}>1</span>
                    : !above ? <span className="mono" style={{ color: "var(--muted-2)" }}>1/{(1/v).toFixed(0)}</span>
                    : <span className="mono" style={{ color: "var(--ink)" }}>{v >= 1 ? v.toFixed(0) : `1/${(1/v).toFixed(0)}`}</span>}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div style={{ marginTop: 22, display: "flex", alignItems: "center", gap: 16, padding: 12, background: "var(--paper-deep)", borderRadius: 4 }}>
          <div>
            <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase" }}>Razón de consistencia (CR)</div>
            <div className="serif" style={{ fontSize: 28, marginTop: 4, color: "var(--ink)" }}>{ahp.cr.toFixed(3)}</div>
          </div>
          <div style={{ flex: 1 }}>
            <Tag kind="ok">CR &lt; 0.10 · matriz consistente</Tag>
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
              Aceptada según Saaty (1980). Se permitirán cambios mientras CR no supere 0.10.
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="Pesos resultantes" meta="eigenvector principal">
        {([
          ["w₁", "Ocupación",    ahp.weights.w1],
          ["w₂", "Preferencia",  ahp.weights.w2],
          ["w₃", "Distribución", ahp.weights.w3],
          ["w₄", "Recursos",     ahp.weights.w4],
        ] as [string, string, number][]).map(([k, lbl, v]) => (
          <div key={k} style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
              <span><span className="mono" style={{ color: "var(--muted)", marginRight: 8 }}>{k}</span>{lbl}</span>
              <span className="serif" style={{ fontSize: 22, letterSpacing: "-0.02em" }}>{v.toFixed(2)}</span>
            </div>
            <div className="progress"><i style={{ width: (v * 100 / 0.5) + "%" }}></i></div>
          </div>
        ))}
        <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
          <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase" }}>Penalización λ</div>
          <div className="serif" style={{ fontSize: 26, marginTop: 4 }}>{ahp.lambda_.toFixed(2)}</div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
            Multiplica violaciones de SC. U(A) = Σ wᵢ·uᵢ − λ · penalty.
          </div>
        </div>
      </Panel>
    </div>
  );
}

function DocenteTab() {
  const [profCode, setProfCode] = useState(data.PROFS[0].code);
  const prof = data.PROFS.find(p => p.code === profCode)!;

  const grid = data.DAYS.map(d => data.SLOTS.map(s => {
    const seed = (d.length * 7 + s.code.charCodeAt(1) + prof.code.charCodeAt(2)) % 11;
    if (seed < 2) return 0;
    if (seed < 4) return 0.2;
    if (seed < 7) return 0.6;
    return 1;
  }));

  return (
    <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 18 }}>
      <Panel title="Docentes" meta={`${data.PROFS.length} activos`} flush>
        {data.PROFS.map(p => (
          <button key={p.code} onClick={() => setProfCode(p.code)} style={{
            display: "block", width: "100%", textAlign: "left",
            padding: "10px 16px", border: "none", borderBottom: "1px solid var(--border)",
            background: p.code === profCode ? "var(--surface-2)" : "transparent",
            borderLeft: "3px solid " + (p.code === profCode ? "var(--agent)" : "transparent"),
            cursor: "pointer", fontFamily: "inherit",
          }}>
            <div style={{ fontSize: 13 }}>{p.name}</div>
            <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
              <span className="mono">{p.code}</span> · {p.contract.replace("_", " ")} · {p.load}/{p.max}h
            </div>
          </button>
        ))}
      </Panel>

      <Panel title={`Disponibilidad & preferencias · ${prof.name}`} meta="0 = no disponible · 1 = ideal">
        <div style={{ display: "grid", gridTemplateColumns: `90px repeat(${data.SLOTS.length}, 1fr)`, gap: 4 }}>
          <div></div>
          {data.SLOTS.map(s => (
            <div key={s.code} className="mono" style={{ fontSize: 10, color: "var(--muted)", textAlign: "center", padding: 6 }}>
              {s.label.split("–")[0]}
            </div>
          ))}
          {data.DAYS.map((d, di) => (
            <div key={d} style={{ display: "contents" }}>
              <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase", padding: "12px 0" }}>{d.slice(0, 3)}</div>
              {data.SLOTS.map((s, si) => {
                const v  = grid[di][si];
                const bg = v === 0
                  ? "repeating-linear-gradient(45deg, var(--paper-deep), var(--paper-deep) 4px, transparent 4px, transparent 8px)"
                  : v < 0.4 ? "oklch(0.95 0.015 200)"
                  : v < 0.8 ? "oklch(0.85 0.05 200)"
                  :           "oklch(0.65 0.10 200)";
                const color = v >= 0.8 ? "white" : v === 0 ? "var(--muted-2)" : "var(--ink-2)";
                return (
                  <div key={s.code} style={{
                    height: 44, background: bg, borderRadius: 3,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontFamily: "var(--mono)", fontSize: 11, color,
                  }}>{v === 0 ? "—" : v.toFixed(1)}</div>
                );
              })}
            </div>
          ))}
        </div>
        <div style={{ marginTop: 18, display: "flex", gap: 16, fontSize: 12, color: "var(--muted)" }}>
          <span>Carga semanal · <span className="mono" style={{ color: "var(--ink)" }}>{prof.load}h / {prof.max}h</span></span>
          <span>Tipo · <span className="mono" style={{ color: "var(--ink)" }}>{prof.contract}</span></span>
          <span>Disponibilidad efectiva · <span className="mono" style={{ color: "var(--ink)" }}>{Math.round(grid.flat().filter(x => x > 0).length / 36 * 100)}%</span></span>
        </div>
      </Panel>
    </div>
  );
}

export function Restricciones() {
  const [tab, setTab] = useState<"catalogo" | "ahp" | "docente">("catalogo");

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Restricciones &amp; calibración AHP</h1>
          <p className="lede">
            Catálogo de restricciones duras (HC) y blandas (SC) — La Cruz et al. (2024).
            Pesos de U(A) calibrados con AHP (Saaty, 1980) · matriz pareada 4×4 con CR &lt; 0.10.
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Btn icon="↻">Recalibrar AHP</Btn>
          <Btn kind="primary" icon="✓">Guardar cambios</Btn>
        </div>
      </div>

      <div style={{ display: "flex", gap: 0, marginBottom: 18, borderBottom: "1px solid var(--border)" }}>
        {([ ["catalogo", "Catálogo HC / SC"], ["ahp", "Pesos AHP"], ["docente", "Preferencias docentes"] ] as [typeof tab, string][]).map(([k, lbl]) => (
          <button key={k} onClick={() => setTab(k)} style={{
            padding: "10px 16px", border: "none", background: "transparent",
            borderBottom: "2px solid " + (tab === k ? "var(--ink)" : "transparent"),
            color: tab === k ? "var(--ink)" : "var(--muted)",
            fontFamily: "inherit", fontSize: 13.5, cursor: "pointer",
            fontWeight: tab === k ? 500 : 400,
          }}>{lbl}</button>
        ))}
      </div>

      {tab === "catalogo" ? <CatalogoTab /> : null}
      {tab === "ahp"      ? <AhpTab />      : null}
      {tab === "docente"  ? <DocenteTab />  : null}
    </div>
  );
}
