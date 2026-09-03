/**
 * recommendations.ts — API client for Phase 5 ML Recommendations
 */
import { api } from "./client";

export interface ItemRecommendation {
  item: string;
  priority_score: number;
  reason: string;
  priority: "high" | "medium" | "low";
  confidence: number;
  source: string;
}

export interface SessionPlan {
  items: string[];
  session_length_s: number;
  focus_mode: "standard" | "deep_focus" | "confidence_boost" | "quick_win";
  reasoning: string;
  difficulty: string;
  confidence: number;
  source: string;
  learning_style: string;
  session_config: string;
}

export interface FullRecommendationResponse {
  learning_style: string;
  style_label: string;
  style_recommendation: string;
  style_confidence: number;
  style_source: string;
  recommended_difficulty: string;
  difficulty_confidence: number;
  difficulty_source: string;
  recommended_items: ItemRecommendation[];
  session_plan: SessionPlan;
  data_completeness: number;
  overall_confidence: number;
  source: string;
}

export interface RecommendationFeedbackRequest {
  recommendation_id?: string;
  item: string;
  action: "accepted" | "skipped" | "completed";
  outcome_accuracy?: number;
  module_type?: string;
}

export interface RecommendationFeedbackResponse {
  stored: boolean;
  message: string;
}

export const recommendationsApi = {
  full: (moduleType: string = "alphabet_practice") =>
    api.get<FullRecommendationResponse>(`/recommendations/full?module_type=${moduleType}`),
  
  session: (moduleType: string = "alphabet_practice") =>
    api.get<SessionPlan>(`/recommendations/session?module_type=${moduleType}`),

  feedback: (data: RecommendationFeedbackRequest) =>
    api.post<RecommendationFeedbackResponse>("/recommendations/feedback", data),
};
