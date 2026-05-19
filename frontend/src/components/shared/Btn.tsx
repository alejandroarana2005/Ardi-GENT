interface BtnProps {
  kind?: "default" | "primary" | "ghost" | "danger";
  children: React.ReactNode;
  onClick?: () => void;
  icon?: string;
  disabled?: boolean;
}

export function Btn({ kind = "default", children, onClick, icon, disabled }: BtnProps) {
  const cls = "btn" + (kind !== "default" ? " " + kind : "");
  return (
    <button className={cls} onClick={onClick} disabled={disabled}>
      {icon ? <span className="mono" style={{ opacity: 0.7 }}>{icon}</span> : null}
      {children}
    </button>
  );
}
