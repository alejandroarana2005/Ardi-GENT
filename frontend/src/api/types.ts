// ─── Recursos ────────────────────────────────────────────────────────────────
export interface ResourceResponse {
  id: number;
  code: string;
  name: string;
}

// ─── Salones ──────────────────────────────────────────────────────────────────
export interface ClassroomResponse {
  id: number;
  code: string;
  name: string;
  capacity: number;
  resources: ResourceResponse[];
}

// ─── Franjas horarias ────────────────────────────────────────────────────────
export interface TimeSlotResponse {
  id: number;
  code: string;
  day: string;
  start_time: string;   // "HH:MM:SS"
  end_time: string;
  duration: number;
}

// ─── Docentes ────────────────────────────────────────────────────────────────
export interface ProfessorResponse {
  id: number;
  code: string;
  name: string;
  max_weekly_hours: number;
  contract_type: string;
}

// ─── Materias ────────────────────────────────────────────────────────────────
export interface SubjectResponse {
  id: number;
  code: string;
  name: string;
  credits: number;
  study_hours: number;
  weekly_subgroups: number;
  groups: number;
  enrollment: number;
  faculty: string;
  professor_code: string | null;
}

// ─── Asignaciones ────────────────────────────────────────────────────────────
export interface AssignmentResponse {
  id: number;
  subject_code: string;
  classroom_code: string;
  timeslot_code: string;
  group_number: number;
  session_number: number;
  utilidad_score: number;
}

// ─── Horarios ────────────────────────────────────────────────────────────────
export interface ScheduleRequest {
  semester: string;          // "2024-A"
  solver_hint?: string;      // "backtracking" | "milp" | "tabu_search"
}

export interface ScheduleResponse {
  schedule_id: string;
  semester: string;
  solver_used: string;
  utility_score: number;
  elapsed_seconds: number;
  is_feasible: boolean;
  status: string;            // "running" | "completed" | "failed" | "accepted"
  assignment_count: number;
  created_at: string;        // ISO 8601
}

export interface LayerTimes {
  layer1_ms: number | null;
  layer2_ms: number | null;
  layer3_ms: number | null;
  layer4_ms: number | null;
  layer5_ms: number | null;
}

export interface ScheduleDetailResponse {
  schedule_id: string;
  semester: string;
  status: string;
  solver_used: string;
  utility_score: number;
  is_feasible: boolean;
  total_courses: number;
  assigned_courses: number;
  hard_constraint_violations: number;
  soft_constraint_violations: number;
  solve_time_ms: number;
  elapsed_seconds: number;
  assignments: AssignmentResponse[] | null;
  layer_times?: LayerTimes | null;
  created_at: string;
}

// ─── Eventos dinámicos ───────────────────────────────────────────────────────
export interface DynamicEventRequest {
  schedule_id: string;
  event_type:
    | "CLASSROOM_UNAVAILABLE"
    | "PROFESSOR_CANCELLED"
    | "ENROLLMENT_SURGE"
    | "SLOT_BLOCKED"
    | "NEW_COURSE_ADDED";
  payload?: Record<string, unknown>;
}

export interface DynamicEventResponse {
  id: number;
  schedule_id: string;
  event_type: string;
  affected_assignments: number;
  repair_elapsed_seconds: number;
  new_schedule_id: string | null;
  created_at: string;
}

// ─── Métricas ────────────────────────────────────────────────────────────────
export interface MetricsResponse {
  schedule_id: string;
  utility_score: number;
  u_occupancy: number;
  u_preference: number;
  u_distribution: number;
  u_resources: number;
  penalty: number;
  total_assignments: number;
  feasible_assignments: number;
  hard_constraint_violations: number;
  soft_constraint_violations: number;
  avg_occupancy_ratio: number;
  weights_used: Record<string, number>;
  soft_constraint_counts: Record<string, number>;
}

// ─── Lista de horarios ───────────────────────────────────────────────────────
export interface ScheduleListItem {
  schedule_id: string
  semester: string
  status: string
  solver_used: string | null
  utility_score: number | null
  is_feasible: boolean | null
  total_courses: number | null
  assigned_courses: number | null
  hard_constraint_violations: number | null
  elapsed_seconds: number | null
  created_at: string
}

export interface ScheduleListResponse {
  items: ScheduleListItem[]
  total: number
  limit: number
  offset: number
}

// ─── Health ──────────────────────────────────────────────────────────────────
export interface HealthResponse {
  status: string;
  version: string;
  db_connected: boolean;
  agent: string;
}
