import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Btn }         from "../components/shared/Btn";
import { useSchedule } from "../context/ScheduleContext";
import { useScheduleData } from "../hooks/useScheduleData";
import type {
  AssignmentResponse, ClassroomResponse,
  ProfessorResponse, SubjectResponse, TimeSlotResponse,
} from "../api/types";
import { timeAgo } from "../lib/dateUtils";

// ─── Constantes ───────────────────────────────────────────────────────────────

const DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
const DAY_LABEL: Record<string, string> = {
  Monday:"Lun", Tuesday:"Mar", Wednesday:"Mié",
  Thursday:"Jue", Friday:"Vie", Saturday:"Sáb",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(t: string): string { return t.slice(0, 5); }

function colorForSubject(code: string): string {
  const hash = [...code].reduce((a, c) => a + c.charCodeAt(0), 0);
  const palette = [
    "#f5e6d3","#dfeae1","#e4dded","#f0d6cc",
    "#d4e7eb","#ede1d0","#e8d8e3","#dde5d5",
  ];
  return palette[hash % palette.length];
}

// ─── SelectFilter ─────────────────────────────────────────────────────────────

interface SelectFilterProps {
  value:       string | null;
  onChange:    (v: string | null) => void;
  options:     Array<{ value: string; label: string }>;
  placeholder: string;
}

function SelectFilter({ value, onChange, options, placeholder }: SelectFilterProps) {
  return (
    <select
      value={value ?? ""}
      onChange={e => onChange(e.target.value || null)}
      style={{
        fontFamily: "var(--sans)", fontSize: 13,
        padding: "7px 10px", borderRadius: "var(--radius)",
        border: "1px solid var(--border-strong)",
        background: value ? "var(--agent-soft)" : "var(--surface)",
        color:      value ? "var(--agent-ink)"  : "var(--ink)",
        cursor: "pointer", minWidth: 170,
      }}
    >
      <option value="">{placeholder}</option>
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

// ─── Modal de detalle ─────────────────────────────────────────────────────────

interface ModalProps {
  assignment:   AssignmentResponse;
  subjectMap:   Record<string, SubjectResponse>;
  classroomMap: Record<string, ClassroomResponse>;
  professorMap: Record<string, ProfessorResponse>;
  slotMap:      Record<string, TimeSlotResponse>;
  onClose:      () => void;
}

function AssignmentModal({ assignment: a, subjectMap, classroomMap, professorMap, slotMap, onClose }: ModalProps) {
  const subject   = subjectMap[a.subject_code];
  const classroom = classroomMap[a.classroom_code];
  const slot      = slotMap[a.timeslot_code];
  const professor = subject?.professor_code ? professorMap[subject.professor_code] : null;

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  return (
    <div
      style={{
        position: "fixed", inset: 0,
        background: "rgba(28,26,22,0.50)",
        zIndex: 50, display: "flex", alignItems: "center",
        justifyContent: "center", padding: 24,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)", width: "100%", maxWidth: 480,
          maxHeight: "88vh", overflowY: "auto",
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* cabecera modal */}
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "14px 18px", borderBottom: "1px solid var(--border)",
          background: "var(--surface-2)",
        }}>
          <span style={{ flex: 1, fontSize: 14, fontFamily: "var(--sans)", fontWeight: 600, color: "var(--ink)" }}>
            Detalle de asignación
          </span>
          <button className="btn ghost" onClick={onClose} style={{ padding: "2px 8px" }}>✕</button>
        </div>

        {/* cuerpo modal */}
        <div style={{ padding: "18px 18px 24px" }}>
          <MRow label="Materia"   value={`${a.subject_code}${subject ? ` — ${subject.name}` : ""}`} />
          <MRow label="Grupo"     value={String(a.group_number)} />
          <MRow label="Sesión"    value={`${a.session_number} de ${subject?.weekly_subgroups ?? "—"}`} />

          <div style={{ height: 14 }} />

          <MRow label="Día"       value={slot ? (DAY_LABEL[slot.day] ?? slot.day) : "—"} />
          <MRow label="Franja"    value={slot ? `${fmt(slot.start_time)} – ${fmt(slot.end_time)}` : "—"} />
          <MRow label="Aula"      value={`${a.classroom_code}${classroom ? ` — ${classroom.name}` : ""}`} />
          <MRow label="Capacidad" value={classroom ? `${classroom.capacity} estudiantes` : "—"} />

          <div style={{ height: 14 }} />

          <MRow
            label="Profesor"
            value={
              professor
                ? `${subject!.professor_code} — ${professor.name}`
                : (subject?.professor_code ?? "—")
            }
          />
          <MRow label="Carrera"   value={subject?.faculty ?? "—"} />

          <div style={{ height: 14 }} />

          <MRow label="U(A) contribución" value={a.utilidad_score.toFixed(4)} />

          <div style={{ marginTop: 20 }}>
            <Btn onClick={onClose}>Cerrar</Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

function MRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between",
      padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 13,
    }}>
      <span style={{ color: "var(--muted)" }}>{label}</span>
      <span style={{ textAlign: "right", maxWidth: "65%" }}>{value}</span>
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────

export function Horario() {
  const navigate       = useNavigate();
  const { startCycle } = useSchedule();
  const { data, isLoading, error, refetch } = useScheduleData();

  const [filters, setFilters] = useState<{
    professor: string | null;
    classroom: string | null;
    faculty:   string | null;
  }>({ professor: null, classroom: null, faculty: null });

  const [selected, setSelected] = useState<AssignmentResponse | null>(null);

  // ── Lookup maps ──────────────────────────────────────────────────────────
  const subjectMap = useMemo(() =>
    Object.fromEntries((data?.subjects ?? []).map(s => [s.code, s])),
  [data]);

  const classroomMap = useMemo(() =>
    Object.fromEntries((data?.classrooms ?? []).map(c => [c.code, c])),
  [data]);

  const professorMap = useMemo(() =>
    Object.fromEntries((data?.professors ?? []).map(p => [p.code, p])),
  [data]);

  const slotMap = useMemo(() =>
    Object.fromEntries((data?.timeslots ?? []).map(ts => [ts.code, ts])),
  [data]);

  // ── Grid: franjas únicas ordenadas ───────────────────────────────────────
  const uniqueRanges = useMemo(() => {
    const seen = new Set<string>();
    const out: Array<{ start: string; end: string }> = [];
    for (const ts of data?.timeslots ?? []) {
      const s = fmt(ts.start_time);
      if (!seen.has(s)) { seen.add(s); out.push({ start: s, end: fmt(ts.end_time) }); }
    }
    return out.sort((a, b) => a.start.localeCompare(b.start));
  }, [data]);

  // Map "Day|HH:MM" → timeslot_code para lookup O(1)
  const cellKey = useMemo(() => {
    const m = new Map<string, string>();
    for (const ts of data?.timeslots ?? []) {
      m.set(`${ts.day}|${fmt(ts.start_time)}`, ts.code);
    }
    return m;
  }, [data]);

  // ── Filtros ──────────────────────────────────────────────────────────────
  const uniqueFaculties = useMemo(() =>
    [...new Set((data?.subjects ?? []).map(s => s.faculty))].sort(),
  [data]);

  const filteredAssignments = useMemo(() => {
    if (!data) return [] as AssignmentResponse[];
    return data.assignments.filter(a => {
      if (filters.classroom && a.classroom_code !== filters.classroom) return false;
      if (filters.professor || filters.faculty) {
        const sub = subjectMap[a.subject_code];
        if (filters.professor && sub?.professor_code !== filters.professor) return false;
        if (filters.faculty   && sub?.faculty         !== filters.faculty)   return false;
      }
      return true;
    });
  }, [data, filters, subjectMap]);

  // Map timeslot_code → assignments[] para lookup O(1)
  const byCode = useMemo(() => {
    const m = new Map<string, AssignmentResponse[]>();
    for (const a of filteredAssignments) {
      const arr = m.get(a.timeslot_code) ?? [];
      arr.push(a);
      m.set(a.timeslot_code, arr);
    }
    return m;
  }, [filteredAssignments]);

  function cellItems(day: string, startTime: string): AssignmentResponse[] {
    const code = cellKey.get(`${day}|${startTime}`);
    return code ? (byCode.get(code) ?? []) : [];
  }

  const hasFilters    = !!(filters.professor || filters.classroom || filters.faculty);
  const totalCount    = data?.assignments.length ?? 0;
  const filteredCount = filteredAssignments.length;

  // ── Acciones ─────────────────────────────────────────────────────────────
  async function handleNewCycle() {
    try { await startCycle(); } catch { /* error surfaced in consola */ }
    navigate("/consola");
  }

  // ── Estado de carga ───────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="page" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 360 }}>
        <span className="mono" style={{ color: "var(--muted)", fontSize: 13 }}>
          Cargando horario…
        </span>
      </div>
    );
  }

  if (error) {
    console.error("[Horario]", error);
    return (
      <div className="page">
        <div className="panel">
          <div className="panel-h"><h3>Error al cargar el horario</h3></div>
          <div className="panel-b">
            <div style={{ color: "var(--muted)", marginBottom: 16, fontSize: 13 }}>
              No se pudieron cargar los datos. Comprueba que el servidor esté disponible.
            </div>
            <Btn onClick={refetch}>Reintentar</Btn>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", maxWidth: 480, padding: "60px 0" }}>
          <div style={{ fontSize: 48, marginBottom: 20, opacity: 0.4 }}>📅</div>
          <h2 style={{ marginBottom: 12 }}>No hay horario generado</h2>
          <p style={{ color: "var(--muted)", marginBottom: 28, lineHeight: 1.6 }}>
            Genera un ciclo BDI para ver el horario semanal aquí.
          </p>
          <Btn kind="primary" icon="▸" onClick={handleNewCycle}>
            Ir a Consola BDI
          </Btn>
        </div>
      </div>
    );
  }

  const { schedule } = data;

  return (
    <div className="page">

      {/* Cabecera */}
      <div className="page-head">
        <div>
          <div className="mono" style={{ fontSize: 10, color: "var(--muted)", letterSpacing: "0.12em" }}>
            HORARIO SEMANAL
          </div>
          <h1>Semestre {schedule.semester} · {totalCount} asignaciones</h1>
          <p className="lede">
            <span className="mono">ID: {schedule.schedule_id.slice(0, 8)}…</span>
            {"  ·  "}{timeAgo(schedule.created_at)}
            {hasFilters && (
              <span style={{ color: "var(--agent-ink)", marginLeft: 14 }}>
                Mostrando {filteredCount} de {totalCount} asignaciones
              </span>
            )}
          </p>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          <Btn icon="↻" onClick={refetch}>Actualizar</Btn>
          <Btn kind="primary" icon="▸" onClick={handleNewCycle}>Generar nuevo</Btn>
        </div>
      </div>

      {/* Barra de filtros */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <SelectFilter
          value={filters.professor}
          onChange={v => setFilters(f => ({ ...f, professor: v }))}
          options={data.professors.map(p => ({ value: p.code, label: p.name }))}
          placeholder="Todos los profesores"
        />
        <SelectFilter
          value={filters.classroom}
          onChange={v => setFilters(f => ({ ...f, classroom: v }))}
          options={data.classrooms.map(c => ({ value: c.code, label: `${c.code} — ${c.name}` }))}
          placeholder="Todas las aulas"
        />
        <SelectFilter
          value={filters.faculty}
          onChange={v => setFilters(f => ({ ...f, faculty: v }))}
          options={uniqueFaculties.map(f => ({ value: f, label: f }))}
          placeholder="Todas las carreras"
        />
        {hasFilters && (
          <Btn kind="ghost" onClick={() => setFilters({ professor: null, classroom: null, faculty: null })}>
            Limpiar filtros
          </Btn>
        )}
      </div>

      {/* Grid semanal */}
      <div className="panel" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>

          {/* Cabecera días */}
          <div style={{
            display: "grid",
            gridTemplateColumns: `92px repeat(${DAY_ORDER.length}, 1fr)`,
            minWidth: 720,
            background: "var(--surface-2)",
            borderBottom: "1px solid var(--border)",
          }}>
            <div style={{ padding: "10px 12px", borderRight: "1px solid var(--border)" }} />
            {DAY_ORDER.map(day => (
              <div key={day} style={{
                padding: "10px 12px",
                borderLeft: "1px solid var(--border)",
                fontSize: 11, letterSpacing: "0.12em",
                textTransform: "uppercase", color: "var(--muted)",
              }}>
                {DAY_LABEL[day]}
              </div>
            ))}
          </div>

          {/* Filas de franjas */}
          {uniqueRanges.length === 0 ? (
            <div style={{ padding: "36px 24px", color: "var(--muted)", fontSize: 13, textAlign: "center" }}>
              No hay franjas horarias disponibles.
            </div>
          ) : (
            uniqueRanges.map(({ start, end }, ri) => (
              <div key={start} style={{
                display: "grid",
                gridTemplateColumns: `92px repeat(${DAY_ORDER.length}, 1fr)`,
                minWidth: 720,
                minHeight: 80,
                borderTop: ri > 0 ? "1px solid var(--border)" : undefined,
              }}>
                {/* Etiqueta de franja */}
                <div style={{
                  padding: "10px 12px",
                  background: "var(--surface-2)",
                  borderRight: "1px solid var(--border)",
                  display: "flex", flexDirection: "column", justifyContent: "center",
                }}>
                  <div className="mono" style={{ fontSize: 11, fontWeight: 500, color: "var(--ink-2)" }}>
                    {start}
                  </div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--muted-2)", marginTop: 2 }}>
                    {end}
                  </div>
                </div>

                {/* Celda por día */}
                {DAY_ORDER.map(day => {
                  const items = cellItems(day, start);
                  return (
                    <div key={day} style={{
                      borderLeft: "1px solid var(--border)",
                      padding: 4,
                      display: "flex", flexDirection: "column", gap: 3,
                    }}>
                      {items.map(a => (
                        <button
                          key={a.id}
                          onClick={() => setSelected(a)}
                          style={{
                            textAlign: "left", padding: "5px 7px",
                            background: colorForSubject(a.subject_code),
                            border: "1px solid rgba(0,0,0,0.09)",
                            borderRadius: 3, cursor: "pointer", fontFamily: "inherit",
                            width: "100%",
                          }}
                        >
                          <div className="mono" style={{ fontSize: 10, fontWeight: 600, color: "var(--ink-2)" }}>
                            {a.subject_code}
                          </div>
                          <div className="mono" style={{ fontSize: 10, color: "var(--muted-2)", marginTop: 2 }}>
                            {a.classroom_code}
                          </div>
                        </button>
                      ))}
                    </div>
                  );
                })}
              </div>
            ))
          )}

        </div>
      </div>

      {/* Modal */}
      {selected && (
        <AssignmentModal
          assignment={selected}
          subjectMap={subjectMap}
          classroomMap={classroomMap}
          professorMap={professorMap}
          slotMap={slotMap}
          onClose={() => setSelected(null)}
        />
      )}

    </div>
  );
}
