/**
 * src/api/sessions.ts — Session & Module API Client
 */
import { api } from "./client";

export interface SessionStartPayload {
  module_type: string;
  target_item?: string | null;
  language?: string;
  difficulty?: string;
}

export interface SessionCompletePayload {
  accuracy_score: number;
  detailed_scores?: Record<string, number> | null;
  duration_seconds: number;
  stroke_data?: StrokeData[] | null;
  total_strokes?: number | null;
  total_points?: number | null;
}

export interface StrokeData {
  id: number;
  points: [number, number, number?][];  // [x, y, timestamp?]
  pressure?: number[];
}

export interface PracticeSession {
  id: number;
  user_id: number;
  module_type: string;
  target_item: string | null;
  language: string;
  difficulty: string;
  attempt_number: number;
  module_version: string;
  status: "started" | "in_progress" | "completed" | "abandoned";
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  is_completed: boolean;
  accuracy_score: number | null;
  detailed_scores: Record<string, number> | null;
  total_strokes: number | null;
  total_points: number | null;
  xp_earned: number;
}

export interface SessionCompleteResponse {
  session: PracticeSession;
  xp_earned: number;
  total_xp: number;
  new_level: number;
  level_up: boolean;
  new_streak: number;
  daily_xp_remaining: number;
}

export interface ModuleDefinition {
  module_type: string;
  label: string;
  description: string;
  icon: string;
  difficulty_levels: string[];
  profile_types: string[];
  xp_per_session: number;
  version: string;
}

export const sessionsApi = {
  /** Start a new practice session */
  start: (data: SessionStartPayload) =>
    api.post<PracticeSession>("/sessions/start", data),

  /** Complete a session and receive XP reward */
  complete: (sessionId: number, data: SessionCompletePayload) =>
    api.post<SessionCompleteResponse>(`/sessions/${sessionId}/complete`, data),

  /** Abandon a session (saves partial strokes) */
  abandon: (sessionId: number, strokeData?: StrokeData[]) =>
    api.post<PracticeSession>(`/sessions/${sessionId}/abandon`, {
      stroke_data: strokeData ?? null,
    }),

  /** Auto-save in-progress strokes */
  saveStrokes: (sessionId: number, strokeData: StrokeData[]) =>
    api.patch<PracticeSession>(`/sessions/${sessionId}/strokes`, {
      stroke_data: strokeData,
    }),

  /** Session history */
  history: (limit = 20, moduleType?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (moduleType) params.append("module_type", moduleType);
    return api.get<PracticeSession[]>(`/sessions/history?${params}`);
  },

  /** Available modules for current user */
  modules: () =>
    api.get<{ profile_type: string; modules: ModuleDefinition[] }>("/sessions/modules"),

  /** Get recommended next item */
  nextItem: (moduleType: string, difficulty = "beginner") =>
    api.get(`/sessions/modules/${moduleType}/item?difficulty=${difficulty}`),

  /** Get specific item tracing data */
  itemData: (moduleType: string, item: string) =>
    api.get(`/sessions/modules/${moduleType}/data/${encodeURIComponent(item)}`),

  /** Report a stroke guidance event for authoritative backend scoring */
  reportGuidanceEvent: (sessionId: number, data: {
    event_type: string;
    stroke_id: number;
    drawn_points: number[][];
    reference_stroke_id?: number;
    hesitation_ms?: number | null;
    module_type?: string;
    target_item?: string;
  }) =>
    api.post(`/sessions/${sessionId}/guidance-event`, data),

  /** Get recommended difficulty based on recent session history */
  recommendedDifficulty: (moduleType: string) =>
    api.get(`/sessions/modules/${moduleType}/recommended-difficulty`),
};
