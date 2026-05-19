interface PillProps {
  kind?: "default" | "agent" | "conflict" | "ok";
  children: React.ReactNode;
}

export function Pill({ kind = "default", children }: PillProps) {
  const cls = "pill" + (kind !== "default" ? " " + kind : "");
  return (
    <span className={cls}>
      <span className="led"></span>
      {children}
    </span>
  );
}
