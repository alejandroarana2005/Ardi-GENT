import { apiClient } from "./client";
import type {
  HealthResponse,
  ScheduleRequest,
  ScheduleResponse,
  ScheduleDetailResponse,
  ScheduleListResponse,
  AssignmentResponse,
  MetricsResponse,
  DynamicEventRequest,
  DynamicEventResponse,
  SubjectResponse,
  ClassroomResponse,
  ProfessorResponse,
  TimeSlotResponse,
} from "./types";

// ─── Health ──────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>("/health");
  return data;
}

// ─── Schedule ────────────────────────────────────────────────────────────────

export async function createSchedule(req: ScheduleRequest): Promise<ScheduleResponse> {
  const { data } = await apiClient.post<ScheduleResponse>("/schedule", req);
  return data;
}

export async function getSchedule(id: string): Promise<ScheduleDetailResponse> {
  const { data } = await apiClient.get<ScheduleDetailResponse>(`/schedule/${id}`);
  return data;
}

export async function listSchedules(params?: {
  semester?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ScheduleListResponse> {
  const { data } = await apiClient.get<ScheduleListResponse>("/schedules", { params });
  return data;
}

export async function getAssignments(scheduleId: string): Promise<AssignmentResponse[]> {
  const { data } = await apiClient.get<AssignmentResponse[]>(`/schedule/${scheduleId}/assignments`);
  return data;
}

export async function acceptSchedule(scheduleId: string): Promise<{ schedule_id: string; status: string }> {
  const { data } = await apiClient.put(`/schedule/${scheduleId}/accept`);
  return data;
}

export async function deleteSchedule(scheduleId: string): Promise<{ schedule_id: string; status: string }> {
  const { data } = await apiClient.delete(`/schedule/${scheduleId}`);
  return data;
}

// ─── Metrics ─────────────────────────────────────────────────────────────────

export async function getMetrics(scheduleId: string): Promise<MetricsResponse> {
  const { data } = await apiClient.get<MetricsResponse>(`/metrics/${scheduleId}`);
  return data;
}

// ─── Dynamic events ──────────────────────────────────────────────────────────

export async function reportEvent(req: DynamicEventRequest): Promise<DynamicEventResponse> {
  const { data } = await apiClient.post<DynamicEventResponse>("/events", req);
  return data;
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export async function getReportJson(scheduleId: string): Promise<unknown> {
  const { data } = await apiClient.get(`/reports/${scheduleId}/json`);
  return data;
}

export function getReportHtmlUrl(scheduleId: string): string {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
  return `${base}/reports/${scheduleId}/html`;
}

export function getReportPdfUrl(scheduleId: string): string {
  const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
  return `${base}/reports/${scheduleId}/pdf`;
}

// ─── Catalog endpoints (para Fase 3) ─────────────────────────────────────────

export async function listSubjects(): Promise<SubjectResponse[]> {
  const { data } = await apiClient.get<SubjectResponse[]>("/subjects");
  return data;
}

export async function listClassrooms(): Promise<ClassroomResponse[]> {
  const { data } = await apiClient.get<ClassroomResponse[]>("/classrooms");
  return data;
}

export async function listProfessors(): Promise<ProfessorResponse[]> {
  const { data } = await apiClient.get<ProfessorResponse[]>("/professors");
  return data;
}

export async function listTimeslots(): Promise<TimeSlotResponse[]> {
  const { data } = await apiClient.get<TimeSlotResponse[]>("/timeslots");
  return data;
}
