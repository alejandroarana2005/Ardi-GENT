/* Mock data shaped to match HAIA's Pydantic schemas (semester, schedules,
 * BDI pipeline, AHP weights, dynamic events). All Spanish for Unibagué. */

window.HAIA_DATA = (() => {
  const SEMESTRE = "2024-A";

  const PROFS = [
    { code: "P-001", name: "Dra. Liliana Herrera",  contract: "tiempo_completo", load: 18, max: 20 },
    { code: "P-002", name: "Dr. Andrés La Cruz",    contract: "tiempo_completo", load: 16, max: 20 },
    { code: "P-003", name: "Dr. Julián Cortés",     contract: "medio_tiempo",    load: 11, max: 12 },
    { code: "P-004", name: "Mg. Ana García-León",   contract: "tiempo_completo", load: 19, max: 20 },
    { code: "P-005", name: "Dr. Erick Severeyn",    contract: "hora_catedra",    load:  6, max:  8 },
    { code: "P-006", name: "Mg. Sara Patiño",       contract: "tiempo_completo", load: 17, max: 20 },
    { code: "P-007", name: "Esp. Ricardo Molina",   contract: "hora_catedra",    load:  8, max:  8 },
    { code: "P-008", name: "Mg. Carolina Vélez",    contract: "medio_tiempo",    load: 10, max: 12 },
  ];

  const AULAS = [
    { code: "A-201", name: "Aula 201 Bloque A", capacity: 35, resources: ["projector"] },
    { code: "A-202", name: "Aula 202 Bloque A", capacity: 30, resources: ["projector", "tv"] },
    { code: "L-301", name: "Lab. Software 301", capacity: 25, resources: ["computers", "software_lab", "projector"] },
    { code: "L-302", name: "Lab. Electrónica",  capacity: 20, resources: ["electronics_lab", "specialized_equipment"] },
    { code: "A-105", name: "Aula 105 Bloque B", capacity: 40, resources: ["projector"] },
    { code: "A-110", name: "Aula 110 Bloque B", capacity: 50, resources: ["projector", "tv"] },
    { code: "L-303", name: "Lab. Redes 303",    capacity: 22, resources: ["computers", "specialized_equipment"] },
  ];

  const MATERIAS = [
    { code: "ISIS-301", name: "Estructuras de Datos",       prof: "P-001", grupos: 2, sesiones: 2, mat: 64, fac: "ingenieria" },
    { code: "ISIS-405", name: "Inteligencia Artificial",    prof: "P-002", grupos: 1, sesiones: 2, mat: 32, fac: "ingenieria" },
    { code: "ISIS-410", name: "Bases de Datos",             prof: "P-004", grupos: 2, sesiones: 2, mat: 58, fac: "ingenieria" },
    { code: "ISIS-220", name: "Programación II",            prof: "P-006", grupos: 3, sesiones: 2, mat: 92, fac: "ingenieria" },
    { code: "MATE-201", name: "Cálculo Vectorial",          prof: "P-003", grupos: 2, sesiones: 2, mat: 71, fac: "ciencias" },
    { code: "ELEC-310", name: "Sistemas Digitales",         prof: "P-005", grupos: 1, sesiones: 2, mat: 18, fac: "ingenieria" },
    { code: "ISIS-501", name: "Ingeniería de Software",     prof: "P-008", grupos: 2, sesiones: 1, mat: 47, fac: "ingenieria" },
    { code: "ISIS-330", name: "Redes de Computadores",      prof: "P-007", grupos: 1, sesiones: 2, mat: 25, fac: "ingenieria" },
    { code: "MATE-101", name: "Álgebra Lineal",             prof: "P-003", grupos: 3, sesiones: 2, mat: 110, fac: "ciencias" },
    { code: "ISIS-450", name: "Sistemas Operativos",        prof: "P-002", grupos: 1, sesiones: 2, mat: 28, fac: "ingenieria" },
  ];

  const DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
  const SLOTS = [
    { code: "S1", label: "06:00–08:00" },
    { code: "S2", label: "08:00–10:00" },
    { code: "S3", label: "10:00–12:00" },
    { code: "S4", label: "14:00–16:00" },
    { code: "S5", label: "16:00–18:00" },
    { code: "S6", label: "18:00–20:00" },
  ];

  // Generate plausible assignments
  const ASIGNACIONES = [
    { mat: "ISIS-301", g: 1, s: 1, aula: "A-201", day: "Lunes",     slot: "S2", prof: "P-001", u: 0.91 },
    { mat: "ISIS-301", g: 1, s: 2, aula: "A-201", day: "Miércoles", slot: "S2", prof: "P-001", u: 0.89 },
    { mat: "ISIS-301", g: 2, s: 1, aula: "A-202", day: "Martes",    slot: "S3", prof: "P-001", u: 0.85 },
    { mat: "ISIS-301", g: 2, s: 2, aula: "A-202", day: "Jueves",    slot: "S3", prof: "P-001", u: 0.84 },
    { mat: "ISIS-405", g: 1, s: 1, aula: "L-301", day: "Lunes",     slot: "S4", prof: "P-002", u: 0.96 },
    { mat: "ISIS-405", g: 1, s: 2, aula: "L-301", day: "Miércoles", slot: "S4", prof: "P-002", u: 0.94 },
    { mat: "ISIS-410", g: 1, s: 1, aula: "L-301", day: "Martes",    slot: "S2", prof: "P-004", u: 0.88 },
    { mat: "ISIS-410", g: 1, s: 2, aula: "L-301", day: "Jueves",    slot: "S2", prof: "P-004", u: 0.87 },
    { mat: "ISIS-410", g: 2, s: 1, aula: "L-303", day: "Lunes",     slot: "S5", prof: "P-004", u: 0.79 },
    { mat: "ISIS-410", g: 2, s: 2, aula: "L-303", day: "Miércoles", slot: "S5", prof: "P-004", u: 0.81 },
    { mat: "ISIS-220", g: 1, s: 1, aula: "A-105", day: "Lunes",     slot: "S3", prof: "P-006", u: 0.93 },
    { mat: "ISIS-220", g: 1, s: 2, aula: "A-105", day: "Viernes",   slot: "S3", prof: "P-006", u: 0.90 },
    { mat: "ISIS-220", g: 2, s: 1, aula: "A-110", day: "Martes",    slot: "S4", prof: "P-006", u: 0.78 },
    { mat: "ISIS-220", g: 2, s: 2, aula: "A-110", day: "Jueves",    slot: "S4", prof: "P-006", u: 0.76 },
    { mat: "ISIS-220", g: 3, s: 1, aula: "A-110", day: "Miércoles", slot: "S6", prof: "P-006", u: 0.62 },
    { mat: "ISIS-220", g: 3, s: 2, aula: "A-110", day: "Viernes",   slot: "S6", prof: "P-006", u: 0.61 },
    { mat: "MATE-201", g: 1, s: 1, aula: "A-201", day: "Martes",    slot: "S2", prof: "P-003", u: 0.84 },
    { mat: "MATE-201", g: 1, s: 2, aula: "A-201", day: "Jueves",    slot: "S2", prof: "P-003", u: 0.82 },
    { mat: "MATE-201", g: 2, s: 1, aula: "A-202", day: "Miércoles", slot: "S3", prof: "P-003", u: 0.71 },
    { mat: "MATE-201", g: 2, s: 2, aula: "A-202", day: "Viernes",   slot: "S3", prof: "P-003", u: 0.68 },
    { mat: "ELEC-310", g: 1, s: 1, aula: "L-302", day: "Lunes",     slot: "S5", prof: "P-005", u: 0.74 },
    { mat: "ELEC-310", g: 1, s: 2, aula: "L-302", day: "Miércoles", slot: "S5", prof: "P-005", u: 0.72 },
    { mat: "ISIS-501", g: 1, s: 1, aula: "A-105", day: "Viernes",   slot: "S2", prof: "P-008", u: 0.86 },
    { mat: "ISIS-501", g: 2, s: 1, aula: "A-105", day: "Viernes",   slot: "S4", prof: "P-008", u: 0.83 },
    { mat: "ISIS-330", g: 1, s: 1, aula: "L-303", day: "Martes",    slot: "S5", prof: "P-007", u: 0.88 },
    { mat: "ISIS-330", g: 1, s: 2, aula: "L-303", day: "Jueves",    slot: "S5", prof: "P-007", u: 0.85 },
    { mat: "MATE-101", g: 1, s: 1, aula: "A-110", day: "Lunes",     slot: "S2", prof: "P-003", u: 0.92 },
    { mat: "MATE-101", g: 1, s: 2, aula: "A-110", day: "Miércoles", slot: "S2", prof: "P-003", u: 0.91 },
    { mat: "MATE-101", g: 2, s: 1, aula: "A-105", day: "Martes",    slot: "S6", prof: "P-003", u: 0.55 },
    { mat: "MATE-101", g: 2, s: 2, aula: "A-105", day: "Jueves",    slot: "S6", prof: "P-003", u: 0.54 },
    { mat: "MATE-101", g: 3, s: 1, aula: "A-201", day: "Sábado",    slot: "S2", prof: "P-003", u: 0.48 },
    { mat: "MATE-101", g: 3, s: 2, aula: "A-201", day: "Sábado",    slot: "S3", prof: "P-003", u: 0.47 },
    { mat: "ISIS-450", g: 1, s: 1, aula: "L-301", day: "Martes",    slot: "S6", prof: "P-002", u: 0.66 },
    { mat: "ISIS-450", g: 1, s: 2, aula: "L-301", day: "Jueves",    slot: "S6", prof: "P-002", u: 0.65 },
  ];

  // Constraints catalog (HC + SC, La Cruz et al. 2024 codes)
  const RESTRICCIONES = [
    { code: "HC-01", name: "No solapamiento de docente",       type: "hard", desc: "Un docente no puede tener dos asignaciones en la misma franja.",  active: true,  satisf: 100 },
    { code: "HC-02", name: "No solapamiento de aula",          type: "hard", desc: "Un aula no puede albergar dos clases en la misma franja.",       active: true,  satisf: 100 },
    { code: "HC-03", name: "Capacidad de aula ≥ matrícula",    type: "hard", desc: "El aula asignada debe tener capacidad para todos los estudiantes.", active: true,  satisf: 100 },
    { code: "HC-04", name: "Recursos requeridos disponibles",  type: "hard", desc: "El aula debe poseer todos los recursos requeridos por la materia.", active: true,  satisf: 100 },
    { code: "HC-05", name: "Disponibilidad del docente",       type: "hard", desc: "La franja debe estar dentro de la disponibilidad declarada.",      active: true,  satisf: 100 },
    { code: "SC-01", name: "Preferencia horaria del docente",  type: "soft", desc: "Maximizar la preferencia declarada por cada docente (0–1).",        active: true,  satisf: 87  },
    { code: "SC-02", name: "Distribución temporal balanceada", type: "soft", desc: "Evitar concentrar la carga del estudiante en franjas contiguas.",   active: true,  satisf: 79  },
    { code: "SC-03", name: "Ocupación cercana a 1.0",          type: "soft", desc: "Aulas con relación matrícula/capacidad cercana al 100%.",          active: true,  satisf: 91  },
    { code: "SC-04", name: "Recursos opcionales presentes",    type: "soft", desc: "Premiar aulas que ofrecen recursos opcionales solicitados.",      active: true,  satisf: 73  },
    { code: "SC-05", name: "Días contiguos del docente",       type: "soft", desc: "Compactar la carga del docente en pocos días.",                   active: false, satisf: 0   },
    { code: "SC-06", name: "Sin franja 06:00 si es posible",   type: "soft", desc: "Penalizar la primera franja del día.",                           active: true,  satisf: 65  },
  ];

  // Conflicts (current schedule)
  const CONFLICTOS = [
    { id: "C-014", type: "PROFESSOR_CANCELLED", subject: "ISIS-450", afected: 2, ts: "Hace 4 min",  severity: "alta",  desc: "Dr. Severeyn reportó incapacidad médica para el martes 14:00–18:00." },
    { id: "C-013", type: "CLASSROOM_UNAVAILABLE", subject: "L-301",  afected: 6, ts: "Hace 32 min", severity: "alta",  desc: "Mantenimiento eléctrico no programado en Lab. Software 301." },
    { id: "C-012", type: "ENROLLMENT_SURGE",    subject: "MATE-101", afected: 1, ts: "Hace 1 h",    severity: "media", desc: "Grupo 3 superó la capacidad del aula A-201 (110 → 35)." },
    { id: "C-011", type: "SLOT_BLOCKED",        subject: "—",        afected: 4, ts: "Ayer 17:42", severity: "baja",   desc: "Decanatura bloqueó franja S6 del viernes para evento institucional." },
  ];

  // BDI pipeline state for Consola Agente — 5 capas
  const PIPELINE = [
    { n: 1, key: "perception",    name: "Capa 1 · Percepción",         desc: "DataLoader · Forecaster · Validator", status: "ok",  ms: 412,  detail: { entradas: 312, validas: 312, alertas: 0 } },
    { n: 2, key: "preprocessing", name: "Capa 2 · Preprocesamiento",   desc: "DomainFilter · AC-3 · Decomposer",     status: "ok",  ms: 1804, detail: { dominio_inicial: 91200, podado: 64530, factible: true } },
    { n: 3, key: "solver",        name: "Capa 3 · Solver",             desc: "CSP Backtracking · MILP · Tabu",       status: "run", ms: 6342, detail: { motor: "csp_backtracking", expansiones: 18432, backtracks: 412 } },
    { n: 4, key: "optimization",  name: "Capa 4 · Optimización",       desc: "Simulated Annealing · U(A) · AHP",     status: "wait",ms: 0,    detail: {} },
    { n: 5, key: "dynamic",       name: "Capa 5 · Dinámica",           desc: "Repair · Periodic Reopt · Versions",   status: "wait",ms: 0,    detail: {} },
  ];

  // BDI mental state
  const BELIEFS = [
    "instance.semester = '2024-A'",
    "instance.subjects = 10  ·  groups = 18",
    "instance.classrooms = 7  ·  timeslots = 36",
    "instance.professors = 8  ·  available_hours = 248",
    "ac3.feasible = true",
    "domain_size = 26 670 (-70.7% vs raw)",
    "active_schedule_id = sch_2024A_v07",
    "last_event = PROFESSOR_CANCELLED@C-014",
  ];
  const DESIRES = [
    { code: "D1", name: "Maximizar U(A)",            weight: 0.40, status: "active" },
    { code: "D2", name: "Satisfacer todas las HC",   weight: 1.00, status: "fulfilled" },
    { code: "D3", name: "Minimizar perturbación",    weight: 0.25, status: "active" },
    { code: "D4", name: "Reducir tiempo de cómputo", weight: 0.15, status: "active" },
    { code: "D5", name: "Equidad entre docentes",    weight: 0.20, status: "monitoring" },
  ];
  const INTENTIONS = [
    { code: "I1", step: "Percibir",  status: "completed", t: "412 ms" },
    { code: "I2", step: "Preparar",  status: "completed", t: "1.80 s" },
    { code: "I3", step: "Resolver",  status: "running",   t: "6.34 s" },
    { code: "I4", step: "Optimizar", status: "pending",   t: "—" },
    { code: "I5", step: "Persistir", status: "pending",   t: "—" },
  ];

  // AHP weights
  const AHP = {
    weights: { w1: 0.40, w2: 0.25, w3: 0.20, w4: 0.15 },
    lambda_: 1.5,
    cr: 0.058,
    matrix: [
      [1,   2,   3,   4],
      [1/2, 1,   2,   2],
      [1/3, 1/2, 1,   1],
      [1/4, 1/2, 1,   1],
    ],
    labels: ["Ocupación", "Preferencia", "Distribución", "Recursos"],
  };

  // Versions
  const VERSIONES = [
    { id: "sch_2024A_v07", parent: "sch_2024A_v06", solver: "csp_backtracking", U: 0.842, t: "12.4s", date: "07 May, 14:32", note: "Reparación tras incapacidad P-005",     active: true,  hcv: 0, scv: 11 },
    { id: "sch_2024A_v06", parent: "sch_2024A_v05", solver: "tabu_search",      U: 0.831, t: "9.1s",  date: "07 May, 09:08", note: "Reasignación L-301 (mantenimiento)",     active: false, hcv: 0, scv: 13 },
    { id: "sch_2024A_v05", parent: "sch_2024A_v04", solver: "milp",             U: 0.819, t: "47.3s", date: "06 May, 18:11", note: "Sobrecupo MATE-101 G3",                 active: false, hcv: 0, scv: 14 },
    { id: "sch_2024A_v04", parent: "sch_2024A_v03", solver: "csp_backtracking", U: 0.811, t: "11.0s", date: "06 May, 11:50", note: "Calibración AHP — w1: 0.35→0.40",      active: false, hcv: 0, scv: 16 },
    { id: "sch_2024A_v03", parent: "sch_2024A_v02", solver: "csp_backtracking", U: 0.788, t: "10.6s", date: "05 May, 16:24", note: "Bloqueo franja S6 viernes",            active: false, hcv: 0, scv: 18 },
    { id: "sch_2024A_v02", parent: "sch_2024A_v01", solver: "tabu_search",      U: 0.751, t: "8.3s",  date: "05 May, 12:01", note: "Inicial · post-AC3",                   active: false, hcv: 0, scv: 22 },
    { id: "sch_2024A_v01", parent: null,            solver: "csp_backtracking", U: 0.703, t: "14.7s", date: "04 May, 09:30", note: "Asignación inicial del semestre",      active: false, hcv: 0, scv: 31 },
  ];

  return {
    SEMESTRE, PROFS, AULAS, MATERIAS, DAYS, SLOTS,
    ASIGNACIONES, RESTRICCIONES, CONFLICTOS,
    PIPELINE, BELIEFS, DESIRES, INTENTIONS,
    AHP, VERSIONES,
  };
})();
