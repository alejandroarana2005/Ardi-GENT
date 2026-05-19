/* global React, ReactDOM, Sidebar, TopBar, ScreenDashboard, ScreenAgente, ScreenHorario,
   ScreenConflictos, ScreenRestricciones, ScreenReportes, ScreenVersiones, useTweaks,
   TweaksPanel, TweakSection, TweakColor, TweakRadio */
const { useState: useStateApp, useMemo: useMemoApp } = React;

const PALETTES = /*EDITMODE-BEGIN*/{
  "palette": "petroleo",
  "density": "comfortable"
}/*EDITMODE-END*/;

const PALETTE_DEFS = {
  petroleo: {
    label: "Petróleo + Terracota",
    agent:    "oklch(0.52 0.085 200)",
    agentSoft:"oklch(0.94 0.025 200)",
    agentInk: "oklch(0.32 0.055 200)",
    conflict: "oklch(0.60 0.16 35)",
    conflictSoft:"oklch(0.94 0.04 40)",
    conflictInk: "oklch(0.40 0.12 35)",
  },
  bosque: {
    label: "Bosque + Cobre",
    agent:    "oklch(0.50 0.085 155)",
    agentSoft:"oklch(0.94 0.025 145)",
    agentInk: "oklch(0.32 0.06 145)",
    conflict: "oklch(0.58 0.15 50)",
    conflictSoft:"oklch(0.94 0.04 55)",
    conflictInk: "oklch(0.38 0.10 50)",
  },
  indigo: {
    label: "Índigo + Carmín",
    agent:    "oklch(0.48 0.10 265)",
    agentSoft:"oklch(0.94 0.03 265)",
    agentInk: "oklch(0.30 0.07 265)",
    conflict: "oklch(0.56 0.17 18)",
    conflictSoft:"oklch(0.94 0.04 20)",
    conflictInk: "oklch(0.38 0.13 18)",
  },
  monocromo: {
    label: "Monocromo grafito",
    agent:    "oklch(0.36 0.01 250)",
    agentSoft:"oklch(0.94 0.005 250)",
    agentInk: "oklch(0.25 0.01 250)",
    conflict: "oklch(0.55 0.16 28)",
    conflictSoft:"oklch(0.94 0.04 28)",
    conflictInk: "oklch(0.36 0.10 28)",
  },
};

function App() {
  const [route, setRoute] = useStateApp("dashboard");
  const [agentRunning, setAgentRunning] = useStateApp(true);
  const [t, setTweak] = useTweaks(PALETTES);

  const data = window.HAIA_DATA;

  // Apply palette via CSS vars
  useMemoApp(() => {
    const p = PALETTE_DEFS[t.palette] || PALETTE_DEFS.petroleo;
    const r = document.documentElement.style;
    r.setProperty("--agent", p.agent);
    r.setProperty("--agent-soft", p.agentSoft);
    r.setProperty("--agent-ink", p.agentInk);
    r.setProperty("--conflict", p.conflict);
    r.setProperty("--conflict-soft", p.conflictSoft);
    r.setProperty("--conflict-ink", p.conflictInk);
  }, [t.palette]);

  const props = { data, agentRunning, goto: setRoute };

  return (
    <div className="app">
      <Sidebar route={route} setRoute={setRoute} />
      <main className="main" data-screen-label={"HAIA · " + route}>
        <TopBar route={route} agentRunning={agentRunning} onRun={() => setAgentRunning(r => !r)} />
        {route === "dashboard"     ? <ScreenDashboard     {...props} /> : null}
        {route === "horario"       ? <ScreenHorario       {...props} /> : null}
        {route === "agente"        ? <ScreenAgente        {...props} onToggle={() => setAgentRunning(r => !r)} /> : null}
        {route === "conflictos"    ? <ScreenConflictos    {...props} /> : null}
        {route === "restricciones" ? <ScreenRestricciones {...props} /> : null}
        {route === "reportes"      ? <ScreenReportes      {...props} /> : null}
        {route === "versiones"     ? <ScreenVersiones     {...props} /> : null}
      </main>

      <TweaksPanel title="Tweaks">
        <TweakSection title="Paleta de acentos">
          <TweakColor
            label="Combinación"
            value={t.palette}
            options={Object.keys(PALETTE_DEFS).map(k => [PALETTE_DEFS[k].agent, PALETTE_DEFS[k].conflict])}
            onChange={(_, idx) => setTweak("palette", Object.keys(PALETTE_DEFS)[idx])}
          />
          <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>
            {PALETTE_DEFS[t.palette]?.label}
          </div>
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
