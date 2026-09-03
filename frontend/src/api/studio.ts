/**
 * src/api/studio.ts — Free Writing Studio API client
 *
 * Typed client for all /studio/* endpoints.
 * Includes Addition 1 (intent), Addition 3 (thumbnail), Addition 4 (soft goal).
 */
import { api } from "./client";

// ── Types ─────────────────────────────────────────────────────────────────────

export type SessionIntent = "journaling" | "practice" | "doodling" | "warmup" | "story";
export type SoftGoal =
  | "smoother_writing"
  | "spacing"
  | "confidence"
  | "free_drawing"
  | "storytelling";
export type QualityBand = "developing" | "building" | "strong" | "exceptional";
export type Trend = "improving" | "stable" | "declining";

export interface MotorMetrics {
  smoothness_score:    number;
  velocity_variance:   number;
  hesitation_ratio:    number;
  stroke_confidence:   number;
  avg_stroke_length:   number;
  stroke_count:        number;
}

export interface SpatialMetrics {
  baseline_consistency: number;
  slant_consistency:    number;
  spacing_regularity:   number;
  canvas_utilization:   number;
  vertical_compression: number;
}

export interface EmotionalSnapshot {
  frustration_index:  number;
  confidence_level:   number;
  fatigue_estimate:   number;
  focus_score:        number;
}

export interface WritingQualityReport {
  session_id:            string;
  overall_quality_score: number;
  quality_band:          QualityBand;
  primary_strength:      string;
  primary_focus_area:    string;
  motor:                 MotorMetrics;
  spatial:               SpatialMetrics;
  emotional_snapshot:    EmotionalSnapshot;
  feedback_messages:     string[];
}

export interface SparklinePoint {
  date:  string;
  score: number;
  band:  QualityBand;
}

export interface WritingProgressTrend {
  smoothness_trend:     Trend;
  spacing_trend:        Trend;
  confidence_trend:     Trend;
  consistency_growth:   number;
  fatigue_pattern:      boolean;
  sessions_analyzed:    number;
  best_session_score:   number;
  best_session_date:    string | null;
  is_improving:         boolean;
}

export interface JourneyResponse {
  trend:          WritingProgressTrend;
  sparkline:      SparklinePoint[];
  total_sessions: number;
}

// ── Request Bodies ─────────────────────────────────────────────────────────────

export interface StartSessionBody {
  session_intent?: SessionIntent;
  soft_goal?:      SoftGoal;
  canvas_width?:   number;
  canvas_height?:  number;
}

export interface CompleteSessionBody {
  strokes:           object[];
  duration_seconds:  number;
  thumbnail_base64?: string;   // Addition 3
}

// ── API client ─────────────────────────────────────────────────────────────────

export const studioApi = {
  /** Create a new Free Writing session */
  start: (body: StartSessionBody) =>
    api.post<{ session_id: string; status: string; intent: string; soft_goal: string | null }>(
      "/studio/start",
      body
    ),

  /** Auto-save strokes mid-session */
  save: (sessionId: string, strokes: object[]) =>
    api.post<{ status: string; stroke_count: number }>(
      `/studio/${sessionId}/save`,
      { strokes }
    ),

  /** Complete session and receive WritingQualityReport */
  complete: (sessionId: string, body: CompleteSessionBody) =>
    api.post<{ session_id: string; report: WritingQualityReport }>(
      `/studio/${sessionId}/complete`,
      body
    ),

  /** Get writing journey trend + sparkline */
  journey: () =>
    api.get<JourneyResponse>("/studio/journey"),

  /** List past sessions (paginated) */
  sessions: (page = 1) =>
    api.get<{ page: number; sessions: object[] }>(`/studio/sessions?page=${page}`),
};
