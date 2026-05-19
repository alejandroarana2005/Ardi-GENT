import { useState, useEffect, useCallback } from "react";
import {
  listSchedules, getSchedule, getAssignments,
  listTimeslots, listClassrooms, listProfessors, listSubjects,
} from "../api/endpoints";
import type {
  ScheduleDetailResponse, AssignmentResponse,
  TimeSlotResponse, ClassroomResponse, ProfessorResponse, SubjectResponse,
} from "../api/types";

export interface ScheduleData {
  schedule:    ScheduleDetailResponse;
  assignments: AssignmentResponse[];
  timeslots:   TimeSlotResponse[];
  classrooms:  ClassroomResponse[];
  professors:  ProfessorResponse[];
  subjects:    SubjectResponse[];
}

export function useScheduleData() {
  const [data,      setData]      = useState<ScheduleData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error,     setError]     = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const list = await listSchedules({ status: "completed", limit: 1 });
      if (list.items.length === 0) {
        setData(null);
        return;
      }
      const id = list.items[0].schedule_id;

      const [schedule, assignments, timeslots, classrooms, professors, subjects] =
        await Promise.all([
          getSchedule(id),
          getAssignments(id),
          listTimeslots().catch(():  TimeSlotResponse[]  => []),
          listClassrooms().catch((): ClassroomResponse[] => []),
          listProfessors().catch((): ProfessorResponse[] => []),
          listSubjects().catch(():   SubjectResponse[]   => []),
        ]);

      setData({ schedule, assignments, timeslots, classrooms, professors, subjects });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return { data, isLoading, error, refetch: fetchAll };
}
