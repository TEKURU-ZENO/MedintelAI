/**
 * src/api/analytics.ts — Analytics API client + TypeScript types
 *
 * Matches schemas/analytics.py exactly.
 * All analytics calls go through analyticsApi — never raw api.get() in components.
 */

import { api } from "./client";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export type SeverityType = "positive" | "low" | "medium" | "high";

export interface InsightItem {
  code:     string;
  severity: SeverityType;
  message:  string;
}

export interface DashboardSummaryResponse {
  current_streak:        number;
  streak_status:         "active" | "at_risk" | "broken";
  engagement_level:      "high" | "medium" | "low";
  confidence_level:      "high" | "medium" | "low" | "unknown";
  frustration_level:     "high" | "medium" | "low";
  rolling_accuracy:      number;
  accuracy_trend:        "improving" | "stable" | "declining";
  current_difficulty:    string;
  promotion_readiness:   number;
  total_sessions:        number;
  total_xp:              number;
  level:                 number;
  active_days_this_week: number;
}

export interface ProgressTrendResponse {
  module_type:     string;
  weekly_accuracy: number[];
  trend:           "improving" | "stable" | "declining";
  velocity:        "fast" | "steady" | "slow";
  rolling_average: number;
  best_letters:    string[];
  worst_letters:   string[];
}

export interface EngagementMetricsResponse {
  current_streak:       number;
  longest_streak:       number;
  streak_status:        "active" | "at_risk" | "broken";
  at_risk:              boolean;
  consistency_score:    number;
  active_days:          number;
  total_days_window:    number;
  practice_pattern:     "consistent" | "weekday_only" | "weekend_heavy" | "irregular";
  avg_session_seconds:  number;
  abandon_rate:         number;
  engagement_level:     "high" | "medium" | "low";
}

export interface LearningInsightResponse {
  strengths:         InsightItem[];
  weaknesses:        InsightItem[];
  behavioral:        InsightItem[];
  confidence_level:  "high" | "medium" | "low" | "unknown";
  frustration_level: "high" | "medium" | "low";
  engagement:        "high" | "medium" | "low";
}

export type RecommendedFocus =
  | "ready_to_advance"
  | "needs_more_practice"
  | "maintain_consistency"
  | "review_basics";

export interface ModulePerformanceResponse {
  module_type:         string;
  label:               string;
  sessions_completed:  number;
  avg_accuracy:        number;
  accuracy_trend:      "improving" | "stable" | "declining";
  current_difficulty:  string;
  promotion_readiness: number;
  recommended_focus:   RecommendedFocus;
  last_practiced:      string | null;
}

// ──────────────────────────────────────────────────────────────────────────────
// API client
// ──────────────────────────────────────────────────────────────────────────────

export const analyticsApi = {
  /** Home-screen analytics snapshot */
  summary: () =>
    api.get<DashboardSummaryResponse>("/analytics/summary"),

  /** Weekly accuracy trend for a module */
  progress: (moduleType = "alphabet_practice") =>
    api.get<ProgressTrendResponse>(`/analytics/progress?module_type=${moduleType}`),

  /** Streak, consistency, session stats */
  engagement: () =>
    api.get<EngagementMetricsResponse>("/analytics/engagement"),

  /** Structured InsightItem intelligence */
  insights: () =>
    api.get<LearningInsightResponse>("/analytics/insights"),

  /** Per-module performance cards */
  modules: () =>
    api.get<ModulePerformanceResponse[]>("/analytics/modules"),
};
