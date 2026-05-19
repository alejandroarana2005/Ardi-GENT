import type { ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ScheduleProvider } from "./context/ScheduleContext";
import { Sidebar }          from "./components/layout/Sidebar";
import { Topbar }           from "./components/layout/Topbar";
import { Dashboard }        from "./pages/Dashboard";
import { ConsolaBDI }       from "./pages/ConsolaBDI";
import { Horario }          from "./pages/Horario";
import { Conflictos }       from "./pages/Conflictos";
import { Restricciones }    from "./pages/Restricciones";
import { Reportes }         from "./pages/Reportes";
import { Versiones }        from "./pages/Versiones";

function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app">
      <Sidebar />
      <div className="main">
        <Topbar />
        {children}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ScheduleProvider>
        <Routes>
          <Route path="/"              element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard"     element={<Layout><Dashboard /></Layout>} />
          <Route path="/horario"       element={<Layout><Horario /></Layout>} />
          <Route path="/conflictos"    element={<Layout><Conflictos /></Layout>} />
          <Route path="/consola"       element={<Layout><ConsolaBDI /></Layout>} />
          <Route path="/restricciones" element={<Layout><Restricciones /></Layout>} />
          <Route path="/reportes"      element={<Layout><Reportes /></Layout>} />
          <Route path="/versiones"     element={<Layout><Versiones /></Layout>} />
        </Routes>
      </ScheduleProvider>
    </BrowserRouter>
  );
}
