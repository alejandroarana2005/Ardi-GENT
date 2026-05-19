interface UtilityRingProps {
  value?: number;
  size?: number;
}

export function UtilityRing({ value = 0.84, size = 168 }: UtilityRingProps) {
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
}
