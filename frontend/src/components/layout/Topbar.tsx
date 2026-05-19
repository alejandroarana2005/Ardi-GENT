import { useLocation, useNavigate } from "react-router-dom";
import { Pill }        from "../shared/Pill";
import { Btn }         from "../shared/Btn";
import { useSchedule } from "../../context/ScheduleContext";

const TITLES: Record<string, [string, string]> = {
  "/dashboard":     ["Panel",        "Resumen del semestre"],
  "/horario":       ["Horario",      "Vista semanal · 2024-A"],
  "/consola":       ["Agente",       "Consola BDI · 5 capas"],
  "/conflictos":    ["Conflictos",   "Eventos dinámicos & reparación"],
  "/restricciones": ["Restricciones","Catálogo HC/SC y pesos AHP"],
  "/reportes":      ["Reportes",     "Métricas y exportables"],
  "/versiones":     ["Versiones",    "Historial y comparación"],
};

export function Topbar() {
  const { pathname } = useLocation();
  const navigate     = useNavigate();
  const [crumb, title] = TITLES[pathname] ?? ["", ""];
  const { pollingStatus, startCycle, cancelTracking } = useSchedule();

  const isRunning = pollingStatus === "running";

  async function handleRun() {
    try {
      await startCycle();
      navigate("/consola");
    } catch {
      navigate("/consola");
    }
  }

  return (
    <header className="topbar">
      <div>
        <div className="crumb">HAIA · {crumb}</div>
        <div className="title serif">{title}</div>
      </div>

      <div className="grow" />

      <span className="pill">
        <span className="led" style={{ background: "var(--ink-2)" }}></span>
        <span style={{ fontFamily: "var(--mono)" }}>Semestre</span>
        <span style={{ fontFamily: "var(--mono)", color: "var(--ink)" }}>2024-A</span>
      </span>

      {isRunning
        ? <Pill kind="agent">Agente · ejecutando</Pill>
        : <Pill kind="ok">Agente · inactivo</Pill>}

      <Btn icon="◷" onClick={() => navigate("/versiones")}>Historial</Btn>
      <Btn kind="primary" onClick={isRunning ? cancelTracking : handleRun}>
        {isRunning ? "Cancelar ciclo" : "Ejecutar ciclo"}
      </Btn>
    </header>
  );
}
