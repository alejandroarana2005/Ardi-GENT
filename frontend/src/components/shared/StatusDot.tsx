type DotStatus = "ok" | "run" | "wait" | "fail";

interface StatusDotProps {
  status: DotStatus;
}

const MAP: Record<DotStatus, { color: string; glyph: string }> = {
  ok:   { color: "var(--ok)",       glyph: "✓" },
  run:  { color: "var(--agent)",    glyph: "▸" },
  wait: { color: "var(--muted-2)",  glyph: "·" },
  fail: { color: "var(--conflict)", glyph: "✕" },
};

export function StatusDot({ status }: StatusDotProps) {
  const s = MAP[status] ?? MAP.wait;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      width: 18, height: 18, borderRadius: "50%",
      background: status === "run" ? "color-mix(in oklch, var(--agent) 18%, transparent)" : "transparent",
      border: `1.5px solid ${s.color}`,
      color: s.color, fontFamily: "var(--mono)", fontSize: 11,
      animation: status === "run" ? "pulse 1.6s ease-in-out infinite" : "none",
      flexShrink: 0,
    }}>{s.glyph}</span>
  );
}
