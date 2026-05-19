interface KPIProps {
  label: string;
  value: string | number;
  unit?: string;
  delta?: string;
  deltaKind?: "up" | "down" | "";
}

export function KPI({ label, value, unit, delta, deltaKind }: KPIProps) {
  return (
    <div className="kpi">
      <div className="lbl">{label}</div>
      <div className="num">
        {value}
        {unit ? <small>{unit}</small> : null}
      </div>
      {delta ? <div className={"delta " + (deltaKind ?? "")}>{delta}</div> : null}
    </div>
  );
}
