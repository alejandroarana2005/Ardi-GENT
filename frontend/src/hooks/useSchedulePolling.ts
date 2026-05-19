import { useState, useEffect, useRef } from "react";
import { getSchedule, getMetrics } from "../api/endpoints";
import type { MetricsResponse, ScheduleDetailResponse, LayerTimes } from "../api/types";

export type PollingStatus = "idle" | "running" | "completed" | "failed";

interface UseSchedulePollingResult {
  status: PollingStatus;
  metrics: MetricsResponse | null;
  scheduleDetail: ScheduleDetailResponse | null;
  layerTimes: LayerTimes | null;
  error: string | null;
  elapsedMs: number;
  isPolling: boolean;
}

const POLL_INTERVAL_MS = 3_000;
const MAX_WAIT_MS      = 180_000;

export function useSchedulePolling(scheduleId: string | null): UseSchedulePollingResult {
  const [status,         setStatus]         = useState<PollingStatus>("idle");
  const [metrics,        setMetrics]        = useState<MetricsResponse | null>(null);
  const [scheduleDetail, setScheduleDetail] = useState<ScheduleDetailResponse | null>(null);
  const [error,          setError]          = useState<string | null>(null);
  const [elapsedMs,      setElapsedMs]      = useState(0);

  const cancelledRef  = useRef(false);
  const startTimeRef  = useRef<number | null>(null);

  useEffect(() => {
    if (!scheduleId) {
      setStatus("idle");
      setMetrics(null);
      setScheduleDetail(null);
      setError(null);
      setElapsedMs(0);
      startTimeRef.current = null;
      return;
    }

    const sid = scheduleId;

    cancelledRef.current = false;
    startTimeRef.current = Date.now();
    setStatus("running");
    setMetrics(null);
    setScheduleDetail(null);
    setError(null);
    setElapsedMs(0);

    // 1-second live counter so the progress bar and header pill update smoothly
    const liveInterval = setInterval(() => {
      if (!cancelledRef.current && startTimeRef.current !== null) {
        setElapsedMs(Date.now() - startTimeRef.current);
      }
    }, 1_000);

    async function poll(): Promise<void> {
      if (cancelledRef.current) return;

      const elapsed = startTimeRef.current !== null
        ? Date.now() - startTimeRef.current
        : 0;

      if (elapsed >= MAX_WAIT_MS) {
        clearInterval(liveInterval);
        setStatus("failed");
        setError("Timeout: el agente tardó más de 3 minutos.");
        return;
      }

      try {
        const schedule = await getSchedule(sid);
        if (cancelledRef.current) return;

        setScheduleDetail(schedule);

        if (schedule.status === "completed" || schedule.status === "accepted") {
          clearInterval(liveInterval);
          setElapsedMs(Date.now() - (startTimeRef.current ?? Date.now()));
          setStatus("completed");
          try {
            const m = await getMetrics(sid);
            if (!cancelledRef.current) setMetrics(m);
          } catch {
            // best-effort
          }
          return;
        }

        if (schedule.status === "failed") {
          clearInterval(liveInterval);
          setStatus("failed");
          setError("El agente no pudo generar un horario factible.");
          return;
        }

        // Still running — schedule next poll
        setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelledRef.current) return;
        clearInterval(liveInterval);
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        setStatus("failed");
      }
    }

    poll();

    return () => {
      cancelledRef.current = true;
      clearInterval(liveInterval);
    };
  }, [scheduleId]);

  return {
    status,
    metrics,
    scheduleDetail,
    layerTimes: scheduleDetail?.layer_times ?? null,
    error,
    elapsedMs,
    isPolling: status === "running",
  };
}
