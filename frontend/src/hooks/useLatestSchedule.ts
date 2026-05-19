import { useState, useEffect, useCallback } from "react";
import { listSchedules, getSchedule, getMetrics } from "../api/endpoints";
import type { ScheduleDetailResponse, MetricsResponse } from "../api/types";

export interface LatestScheduleResult {
  schedule: ScheduleDetailResponse | null;
  metrics:  MetricsResponse | null;
  isLoading: boolean;
  error:    string | null;
  refetch:  () => Promise<void>;
}

export function useLatestSchedule(semester?: string): LatestScheduleResult {
  const [schedule,  setSchedule]  = useState<ScheduleDetailResponse | null>(null);
  const [metrics,   setMetrics]   = useState<MetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error,     setError]     = useState<string | null>(null);

  const fetchLatest = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const list = await listSchedules({ semester, status: "completed", limit: 1 });

      if (list.items.length === 0) {
        setSchedule(null);
        setMetrics(null);
        return;
      }

      const id = list.items[0].schedule_id;
      const [detail, metricsData] = await Promise.all([
        getSchedule(id),
        getMetrics(id).catch(() => null),
      ]);

      setSchedule(detail);
      setMetrics(metricsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  }, [semester]);

  useEffect(() => {
    fetchLatest();
  }, [fetchLatest]);

  return { schedule, metrics, isLoading, error, refetch: fetchLatest };
}
