import type { CSSProperties, ReactNode } from "react";

interface PanelProps {
  title?: string;
  meta?: string;
  actions?: ReactNode;
  flush?: boolean;
  children: ReactNode;
  style?: CSSProperties;
}

export function Panel({ title, meta, actions, flush, children, style }: PanelProps) {
  return (
    <section className="panel" style={style}>
      {(title || actions) ? (
        <div className="panel-h">
          {title ? <h3>{title}</h3> : null}
          {meta  ? <span className="meta">{meta}</span> : null}
          {actions ? <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>{actions}</div> : null}
        </div>
      ) : null}
      <div className={"panel-b" + (flush ? " flush" : "")}>{children}</div>
    </section>
  );
}
