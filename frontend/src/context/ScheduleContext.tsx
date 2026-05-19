import { createContext, useContext, useState, type ReactNode } from "react";
import { useSchedulePolling, type PollingStatus } from "../hooks/useSchedulePolling";
import { createSchedule } from "../api/endpoints";
import type { MetricsResponse, ScheduleDetailResponse, LayerTimes } from "../api/types";

interface ScheduleContextValue {
  activeScheduleId: string | null;
  pollingStatus: PollingStatus;
  metrics: MetricsResponse | null;
  scheduleDetail: ScheduleDetailResponse | null;
  layerTimes: LayerTimes | null;
  error: string | null;
  elapsedMs: number;
  isPolling: boolean;
  startCycle: () => Promise<string>;
  cancelTracking: () => void;
}

const ScheduleContext = createContext<ScheduleContextValue | null>(null);

export function ScheduleProvider({ children }: { children: ReactNode }) {
  const [activeScheduleId, setActiveScheduleId] = useState<string | null>(null);

  const { status, metrics, scheduleDetail, layerTimes, error, elapsedMs, isPolling } =
    useSchedulePolling(activeScheduleId);

  async function startCycle(): Promise<string> {
    const res = await createSchedule({ semester: "2024-A" });
    setActiveScheduleId(res.schedule_id);
    return res.schedule_id;
  }

  function cancelTracking(): void {
    setActiveScheduleId(null);
  }

  return (
    <ScheduleContext.Provider value={{
      activeScheduleId,
      pollingStatus: status,
      metrics,
      scheduleDetail,
      layerTimes,
      error,
      elapsedMs,
      isPolling,
      startCycle,
      cancelTracking,
    }}>
      {children}
    </ScheduleContext.Provider>
  );
}

export function useSchedule(): ScheduleContextValue {
  const ctx = useContext(ScheduleContext);
  if (!ctx) throw new Error("useSchedule must be used inside ScheduleProvider");
  return ctx;
}
