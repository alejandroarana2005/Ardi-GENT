interface TagProps {
  kind?: "hard" | "soft" | "ok" | "warn";
  children: React.ReactNode;
}

export function Tag({ kind, children }: TagProps) {
  return <span className={"tag" + (kind ? " " + kind : "")}>{children}</span>;
}
