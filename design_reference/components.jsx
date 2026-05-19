/* global React */
const { useState, useMemo, useEffect, useRef } = React;

// ────────────────────────────────────────────────────────────
// Shared atoms
// ────────────────────────────────────────────────────────────

window.Pill = function Pill({ kind = "default", children }) {
  const cls = "pill" + (kind === "agent" ? " agent" : kind === "conflict" ? " conflict" : kind === "ok" ? " ok" : "");
  return (
    <span className={cls}>
      <span className="led"></span>
      {children}
    </span>
  );
};

window.Tag = function Tag({ kind, children }) {
  return <span className={"tag" + (kind ? " " + kind : "")}>{children}</span>;
};

window.Btn = function Btn({ kind = "default", children, onClick, icon }) {
  const cls = "btn" + (kind !== "default" ? " " + kind : "");
  return (
    <button className={cls} onClick={onClick}>
      {icon ? <span className="mono" style={{ opacity: 0.7 }}>{icon}</span> : null}
      {children}
    </button>
  );
};

window.Panel = function Panel({ title, meta, actions, flush, children, style }) {
  return (
    <section className="panel" style={style}>
      {(title || actions) ? (
        <div className="panel-h">
          {title ? <h3>{title}</h3> : null}
          {meta ? <span className="meta">{meta}</span> : null}
          {actions ? <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>{actions}</div> : null}
        </div>
      ) : null}
      <div className={"panel-b" + (flush ? " flush" : "")}>{children}</div>
    </section>
  );
};

window.KPI = function KPI({ label, value, unit, delta, deltaKind }) {
  return (
    <div className="kpi">
      <div className="lbl">{label}</div>
      <div className="num">
        {value}
        {unit ? <small>{unit}</small> : null}
      </div>
      {delta ? <div className={"delta " + (deltaKind || "")}>{delta}</div> : null}
    </div>
  );
};

window.Sparkline = function Sparkline({ data, width = 110, height = 28, kind = "agent" }) {
  if (!data || !data.length) return null;
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const pts = data.map((v, i) => [i * step, height - ((v - min) / range) * (height - 4) - 2]);
  const path = "M " + pts.map(p => p.join(",")).join(" L ");
  const stroke = kind === "conflict" ? "var(--conflict)" : "var(--agent)";
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <path d={path} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
};

// Big SVG donut for utility score
window.UtilityRing = function UtilityRing({ value = 0.84, size = 168 }) {
  const r = (size - 16) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - value);
  return (
    <svg width={size} height={size} style={{ display: "block" }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--paper-deep)" strokeWidth="10" />
      <circle cx={size/2} cy={size/2} r={r} fill="none"
        stroke="var(--agent)" strokeWidth="10" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={off}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: "stroke-dashoffset 600ms ease" }} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        style={{ fontFamily: "var(--serif)", fontSize: 36, fill: "var(--ink)", letterSpacing: "-0.02em" }}>
        {value.toFixed(3)}
      </text>
      <text x="50%" y="68%" textAnchor="middle"
        style={{ fontFamily: "var(--mono)", fontSize: 10, fill: "var(--muted)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
        U(A)
      </text>
    </svg>
  );
};

// LED status dot for pipeline steps
window.StatusDot = function StatusDot({ status }) {
  const map = {
    ok:   { color: "var(--ok)",       glyph: "✓" },
    run:  { color: "var(--agent)",    glyph: "▸" },
    wait: { color: "var(--muted-2)",  glyph: "·" },
    fail: { color: "var(--conflict)", glyph: "✕" },
  };
  const s = map[status] || map.wait;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      width: 18, height: 18, borderRadius: "50%",
      background: status === "run" ? "color-mix(in oklch, var(--agent) 18%, transparent)" : "transparent",
      border: `1.5px solid ${s.color}`,
      color: s.color, fontFamily: "var(--mono)", fontSize: 11,
      animation: status === "run" ? "pulse 1.6s ease-in-out infinite" : "none",
    }}>{s.glyph}</span>
  );
};
