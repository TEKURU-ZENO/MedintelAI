/**
 * useGuidanceEngine.ts — Real-Time Guidance Engine (Frontend Orchestrator)
 *
 * This hook is the single source of truth for all guidance state in a session.
 * AlphabetModule uses this — it does NOT manage any guidance logic itself.
 *
 * Architecture split (per spec):
 *   Frontend (this hook) owns:
 *     - <16ms feedback loop (local lightweight scoring)
 *     - Stroke locking visuals
 *     - Instant hints
 *     - Coaching state machine
 *     - Ghost replay triggers
 *
 *   Backend owns:
 *     - Authoritative scoring (POST /sessions/{id}/guidance-event)
 *     - Persistence
 *     - Inactivity analytics
 *     - Session progression
 *
 * Coaching State Machine:
 *   idle → guiding → (after stroke) → correcting | celebrating | replaying
 *   Any state → idle (on new stroke start)
 */

import { useState, useCallback, useRef } from "react";
import { sessionsApi, type StrokeData } from "../api/sessions";
import type { FeedbackType } from "../components/shared/FeedbackPanel";
import { useGhostReplay } from "./useGhostReplay";

export type CoachingState =
  | "idle"
  | "guiding"
  | "correcting"
  | "celebrating"
  | "replaying";

export interface StrokeResult {
  strokeId:          number;
  combinedScore:     number;
  directionMatch:    boolean;
  tracePercent:      number;
  unlocked:          boolean;
  failsafeUnlock:    boolean;
  attemptNumber:     number;
  feedbackType:      FeedbackType;
  feedbackMessage:   string;
}

export interface GuidanceState {
  coachingState:      CoachingState;
  currentStrokeId:    number;           // which stroke is currently active
  completedStrokes:   number[];         // stroke IDs successfully completed
  failedStrokes:      number[];         // stroke IDs that used failsafe
  strokeResults:      StrokeResult[];   // history of all scored strokes
  tracePercent:       number;           // 0–100 weighted trace coverage
  feedbackType:       FeedbackType;
  feedbackMessage:    string;
  isSubmitting:       boolean;          // waiting for backend guidance-event response
  totalStrokes:       number;           // total reference strokes for this letter
}

interface UseGuidanceEngineOptions {
  sessionId:       number | null;
  moduleType:      string;
  targetItem:      string;
  referenceStrokes: any[];             // from letterData.strokes
  isDrawing:        boolean;
  profileType?:     string;
  onAllStrokesDone?: () => void;       // called when all strokes complete
  onCoachingEvent?:  (eventName: string) => void;
}

export function useGuidanceEngine({
  sessionId,
  moduleType,
  targetItem,
  referenceStrokes,
  isDrawing,
  profileType: _profileType = "adult",
  onAllStrokesDone,
  onCoachingEvent,
}: UseGuidanceEngineOptions) {
  const totalStrokes = referenceStrokes.length;

  const [state, setState] = useState<GuidanceState>({
    coachingState:    "idle",
    currentStrokeId:  1,
    completedStrokes: [],
    failedStrokes:    [],
    strokeResults:    [],
    tracePercent:     0,
    feedbackType:     "idle",
    feedbackMessage:  "Start tracing the first stroke ✏️",
    isSubmitting:     false,
    totalStrokes,
  });

  // Per-stroke attempt count tracking (mirrors backend state)
  const attemptCounts = useRef<Record<string, number>>({});
  const lastStrokeStartMs = useRef<number | null>(null);

  // Ghost replay hook — tracks when to show replay based on state
  const { replayLevel, dismissReplay } = useGhostReplay({
    strokeId:       state.currentStrokeId,
    failedAttempts: attemptCounts.current[String(state.currentStrokeId)] ?? 0,
    lastScore:      state.strokeResults.at(-1)?.combinedScore ?? null,
    isDrawing,
    disabled:       moduleType !== "alphabet_practice",
  });

  // ── Local lightweight score (runs synchronously, < 1ms) ──────────────────
  // Used for instant feedback BEFORE the backend responds.
  const localQuickScore = useCallback(
    (stroke: StrokeData, refStrokeId: number): number => {
      const refStroke = referenceStrokes.find((s) => s.id === refStrokeId);
      if (!refStroke || stroke.points.length < 2) return 0;

      // Quick check 1: net direction cosine similarity
      const drawnDx = stroke.points[stroke.points.length - 1][0] - stroke.points[0][0];
      const drawnDy = stroke.points[stroke.points.length - 1][1] - stroke.points[0][1];
      const refStart = refStroke.points[0];
      const refEnd   = refStroke.points[refStroke.points.length - 1];
      const refDx = refEnd[0] - refStart[0];
      const refDy = refEnd[1] - refStart[1];
      const mag1 = Math.sqrt(drawnDx**2 + drawnDy**2);
      const mag2 = Math.sqrt(refDx**2 + refDy**2);
      if (mag1 < 0.1 || mag2 < 0.1) return 0.3;
      const cos = (drawnDx*refDx + drawnDy*refDy) / (mag1 * mag2);
      const dirScore = (cos + 1) / 2;   // map [-1,1] → [0,1]

      // Quick check 2: stroke length ratio (not too short, not too long)
      const drawnLen = mag1;
      const refLen   = mag2;
      const lenRatio = Math.min(drawnLen / Math.max(refLen, 1), refLen / Math.max(drawnLen, 1));

      return (dirScore * 0.6 + lenRatio * 0.4);
    },
    [referenceStrokes],
  );

  // ── Handle a completed stroke ─────────────────────────────────────────────
  const handleStrokeComplete = useCallback(
    async (stroke: StrokeData) => {
      if (!sessionId || state.isSubmitting) return;

      const strokeId = state.currentStrokeId;
      const key = String(strokeId);
      attemptCounts.current[key] = (attemptCounts.current[key] ?? 0) + 1;

      const hesitationMs = lastStrokeStartMs.current
        ? Date.now() - lastStrokeStartMs.current
        : null;

      // ── INSTANT local feedback (< 1ms, no network) ────────────────────────
      const quickScore = localQuickScore(stroke, strokeId);
      const instantFeedback = quickScore >= 0.65
        ? { type: "encouragement" as FeedbackType, message: "Looking good…" }
        : { type: "correction"   as FeedbackType, message: "Adjusting…" };

      setState((prev) => ({
        ...prev,
        coachingState:  "guiding",
        feedbackType:   instantFeedback.type,
        feedbackMessage: instantFeedback.message,
        isSubmitting:   true,
        tracePercent:   Math.round(quickScore * 100),
      }));

      // Normalize stroke points to 0–100 canvas grid
      const canvas = document.querySelector("canvas");
      const scaleX = canvas ? 100 / canvas.width  : 1;
      const scaleY = canvas ? 100 / canvas.height : 1;
      const normalizedPoints = stroke.points.map(([x, y]) => [
        Math.round(x * scaleX * 100) / 100,
        Math.round(y * scaleY * 100) / 100,
      ]);

      try {
        // ── AUTHORITATIVE backend validation ─────────────────────────────────
        const res = await sessionsApi.reportGuidanceEvent(sessionId, {
          event_type:          "stroke_complete",
          stroke_id:           strokeId,
          drawn_points:        normalizedPoints,
          reference_stroke_id: strokeId,
          hesitation_ms:       hesitationMs,
          module_type:         moduleType,
          target_item:         targetItem,
        });

        const data = res.data;
        const result: StrokeResult = {
          strokeId,
          combinedScore:   data.scores.combined_score,
          directionMatch:  data.direction_match,
          tracePercent:    data.trace_percent,
          unlocked:        data.unlock_next_stroke,
          failsafeUnlock:  data.failsafe_unlock,
          attemptNumber:   data.attempt_number,
          feedbackType:    data.feedback_type as FeedbackType,
          feedbackMessage: data.feedback_message,
        };

        const nextStrokeId  = data.unlock_next_stroke ? strokeId + 1 : strokeId;
        const allDone       = data.unlock_next_stroke && nextStrokeId > totalStrokes;
        const newCompleted  = data.unlock_next_stroke
          ? [...state.completedStrokes, strokeId]
          : state.completedStrokes;
        const newFailed     = data.failsafe_unlock
          ? [...state.failedStrokes, strokeId]
          : state.failedStrokes;

        // ── Phase 6.2 Coaching Events ────────────────────────────────────────
        if (data.failsafe_unlock) {
          onCoachingEvent?.("failsafe_triggered");
        } else if (!data.unlock_next_stroke) {
          if (!data.direction_match) {
            onCoachingEvent?.("direction_failure");
          } else {
            onCoachingEvent?.("off_path");
          }
        } else if (allDone) {
          // If average score is very high, strong success. Else minor.
          const avg = [...state.strokeResults, result].reduce((s, r) => s + r.combinedScore, 0) / totalStrokes;
          onCoachingEvent?.(avg >= 0.85 ? "success_strong" : "success_minor");
        }

        const coaching: CoachingState = allDone
          ? "celebrating"
          : data.feedback_type === "celebration"
          ? "celebrating"
          : data.unlock_next_stroke
          ? "idle"
          : "correcting";

        setState((prev) => ({
          ...prev,
          coachingState:    coaching,
          currentStrokeId:  nextStrokeId,
          completedStrokes: newCompleted,
          failedStrokes:    newFailed,
          strokeResults:    [...prev.strokeResults, result],
          tracePercent:     data.trace_percent,
          feedbackType:     data.feedback_type as FeedbackType,
          feedbackMessage:  data.feedback_message,
          isSubmitting:     false,
        }));

        dismissReplay();

        if (allDone) {
          onAllStrokesDone?.();
        }
      } catch {
        // Network error — fall back to local score
        const localUnlock = quickScore >= 0.60 ||
          (attemptCounts.current[key] ?? 0) >= 3;

        const nextStrokeId  = localUnlock ? strokeId + 1 : strokeId;
        const allDone       = localUnlock && nextStrokeId > totalStrokes;
        const newCompleted  = localUnlock
          ? [...state.completedStrokes, strokeId]
          : state.completedStrokes;
        const newFailed     = (attemptCounts.current[key] ?? 0) >= 3
          ? [...state.failedStrokes, strokeId]
          : state.failedStrokes;

        setState((prev) => ({
          ...prev,
          coachingState:   allDone ? "celebrating" : (localUnlock ? "idle" : "correcting"),
          currentStrokeId: nextStrokeId,
          completedStrokes: newCompleted,
          failedStrokes:    newFailed,
          feedbackType:    localUnlock ? "encouragement" : "correction",
          feedbackMessage: localUnlock 
            ? (allDone ? "Letter complete!" : "Nice trace — scored locally") 
            : "Connection issue — please try again",
          isSubmitting:    false,
        }));

        if (allDone) {
          onAllStrokesDone?.();
        }
      }

      lastStrokeStartMs.current = null;
    },
    [sessionId, state, totalStrokes, localQuickScore, dismissReplay, onAllStrokesDone],
  );

  const handleStrokeStart = useCallback(() => {
    lastStrokeStartMs.current = Date.now();
    setState((prev) => ({
      ...prev,
      coachingState:  "guiding",
      feedbackType:   "idle",
      feedbackMessage: "Keep tracing…",
    }));
    onCoachingEvent?.("stroke_start");
  }, [onCoachingEvent]);

  const resetGuidance = useCallback(() => {
    setState({
      coachingState:    "idle",
      currentStrokeId:  1,
      completedStrokes: [],
      failedStrokes:    [],
      strokeResults:    [],
      tracePercent:     0,
      feedbackType:     "idle",
      feedbackMessage:  "Start tracing the first stroke ✏️",
      isSubmitting:     false,
      totalStrokes,
    });
    attemptCounts.current = {};
  }, [totalStrokes]);

  return {
    state,
    replayLevel,
    dismissReplay,
    handleStrokeComplete,
    handleStrokeStart,
    resetGuidance,
  };
}
