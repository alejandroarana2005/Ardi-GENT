import { useState } from "react";
import { Panel } from "../components/shared/Panel";
import { Tag }   from "../components/shared/Tag";
import { Btn }   from "../components/shared/Btn";
import { mockData as data } from "../data/mockData";
import type { Version } from "../data/mockData";

function Cell({ k, v }: { k: string; v: string | number }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>{k}</div>
      <div className="mono" style={{ marginTop: 2 }}>{v}</div>
    </div>
  );
}

function VersionCard({ v, role }: { v: Version; role: "A" | "B" }) {
  return (
    <div className="panel">
      <div className="panel-h">
        <span className="mono" style={{
          width: 22, height: 22, borderRadius: 99,
          background: role === "A" ? "var(--ink)" : "var(--surface-2)",
          color: role === "A" ? "var(--paper)" : "var(--ink)",
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          fontSize: 11, border: "1px solid var(--border)",
        }}>{role}</span>
        <h3>{v.id}</h3>
        {v.active ? <Tag kind="ok">activa</Tag> : null}
        <span className="meta">solver · {v.solver}</span>
      </div>
      <div className="panel-b">
        <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
          <span className="serif" style={{ fontSize: 40, letterSpacing: "-0.02em" }}>{v.U.toFixed(3)}</span>
          <span style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase" }}>U(A)</span>
        </div>
        <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", rowGap: 10, fontSize: 13 }}>
          <Cell k="Tiempo"         v={v.t} />
          <Cell k="Generada"       v={v.date} />
          <Cell k="Padre"          v={v.parent ?? "—"} />
          <Cell k="Violaciones HC" v={v.hcv} />
          <Cell k="Violaciones SC" v={v.scv} />
          <Cell k="Asignaciones"   v="34" />
        </div>
        <div style={{ marginTop: 14, padding: 10, background: "var(--paper-deep)", borderRadius: 4, fontSize: 12.5, color: "var(--ink-2)" }}>
          <span className="mono" style={{ color: "var(--muted)", fontSize: 11 }}>nota</span>
          <p style={{ margin: "4px 0 0" }}>{v.note}</p>
        </div>
        <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
          <Btn icon="↗">Ver horario</Btn>
          {!v.active ? <Btn>Restaurar</Btn> : null}
        </div>
      </div>
    </div>
  );
}

export function Versiones() {
  const [a, setA] = useState("sch_2024A_v07");
  const [b, setB] = useState("sch_2024A_v06");
  const verA = data.VERSIONES.find(v => v.id === a)!;
  const verB = data.VERSIONES.find(v => v.id === b)!;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Versiones &amp; what-if</h1>
          <p className="lede">
            Cada ejecución del agente produce una versión inmutable con su <span className="mono">parent_schedule_id</span>.
            La línea de tiempo permite comparar dos cualesquiera lado a lado o restaurar una versión previa.
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Btn icon="⇅">Comparar seleccionadas</Btn>
          <Btn kind="primary" icon="✦">Crear simulación what-if</Btn>
        </div>
      </div>

      <Panel title="Línea de tiempo del semestre" meta={`${data.VERSIONES.length} versiones`} style={{ marginBottom: 18 }}>
        <div style={{ position: "relative", padding: "24px 0 4px" }}>
          <div style={{ position: "absolute", top: 36, left: 12, right: 12, height: 1, background: "var(--border)" }}></div>
          <div style={{ display: "grid", gridTemplateColumns: `repeat(${data.VERSIONES.length}, 1fr)`, gap: 0 }}>
            {[...data.VERSIONES].reverse().map((v) => (
              <div key={v.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "0 6px" }}>
                <div className="mono" style={{ fontSize: 10, color: "var(--muted)", marginBottom: 8 }}>{v.date}</div>
                <button
                  type="button"
                  aria-label={`Seleccionar versión ${v.id}`}
                  onClick={() => { setB(a); setA(v.id); }}
                  style={{
                    width: 28, height: 28, borderRadius: "50%",
                    border: `2px solid ${v.active ? "var(--agent)" : (a === v.id || b === v.id) ? "var(--ink)" : "var(--border-strong)"}`,
                    background: v.active ? "var(--agent)" : (a === v.id || b === v.id) ? "var(--ink)" : "var(--surface)",
                    cursor: "pointer", padding: 0,
                  }}
                />
                <div className="serif" style={{ fontSize: 14, marginTop: 8 }}>{v.U.toFixed(3)}</div>
                <div className="mono" style={{ fontSize: 10, color: "var(--muted-2)", marginTop: 2 }}>v{v.id.slice(-2)}</div>
                <div style={{ fontSize: 11, color: "var(--muted)", textAlign: "center", marginTop: 6, lineHeight: 1.3 }}>{v.note}</div>
              </div>
            ))}
          </div>
        </div>
      </Panel>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 18 }}>
        <VersionCard v={verA} role="A" />
        <VersionCard v={verB} role="B" />
      </div>

      <Panel title="Diferencias asignación a asignación" meta={`${verA.id} vs ${verB.id}`} flush>
        <table className="tbl">
          <thead><tr>
            <th>Asignación</th>
            <th>{verA.id.slice(-3)}</th>
            <th>{verB.id.slice(-3)}</th>
            <th className="num">Δ U(A)</th>
            <th>Causa</th>
          </tr></thead>
          <tbody>
            {[
              { mat: "ISIS-450 G1S1", a: "Mié 16:00 · L-301 · La Cruz",  b: "Mar 18:00 · L-301 · Severeyn", du:  0.05, why: "PROFESSOR_CANCELLED · C-014" },
              { mat: "ISIS-450 G1S2", a: "Vie 16:00 · L-301 · La Cruz",  b: "Jue 18:00 · L-301 · Severeyn", du:  0.04, why: "PROFESSOR_CANCELLED · C-014" },
              { mat: "MATE-101 G3S1", a: "Sáb 08:00 · A-201",            b: "Sáb 08:00 · A-202",            du: -0.03, why: "ENROLLMENT_SURGE · C-012" },
              { mat: "ISIS-410 G2S1", a: "Lun 16:00 · L-303",            b: "Lun 16:00 · L-303",            du:  0.00, why: "sin cambios" },
            ].map(r => (
              <tr key={r.mat}>
                <td className="mono" style={{ fontSize: 12 }}>{r.mat}</td>
                <td>{r.a}</td>
                <td style={{ color: "var(--muted)" }}>{r.b}</td>
                <td className="num">
                  <span style={{ color: r.du > 0 ? "var(--ok)" : r.du < 0 ? "var(--conflict-ink)" : "var(--muted-2)" }}>
                    {r.du > 0 ? "+" : ""}{r.du.toFixed(2)}
                  </span>
                </td>
                <td style={{ color: "var(--muted)", fontSize: 12 }}>{r.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
