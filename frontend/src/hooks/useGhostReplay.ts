/**
 * useGhostReplay.ts — Stage-based ghost replay trigger hook
 *
 * Three escalating trigger levels (as per architectural spec):
 *   Level 1 — 5s inactivity on current stroke
 *   Level 2 — 2 failed attempts on this stroke
 *   Level 3 — accuracy < 40% on this stroke (combined_score < 0.40)
 *
 * The hook does NOT animate itself — it signals WHEN to replay.
 * GhostReplay.tsx component owns the animation.
 * This prevents over-helping advanced users.
 */

import { useState, useEffect, useRef, useCallback } from "react";

export type ReplayLevel = 0 | 1 | 2 | 3;  // 0 = no replay

interface UseGhostReplayOptions {
  strokeId:        number;           // current stroke being practiced
  failedAttempts:  number;           // how many times this stroke has been retried
  lastScore:       number | null;    // combined_score from last guidance event (0–1)
  isDrawing:       boolean;          // reset inactivity timer while user is drawing
  inactivityMs?:   number;           // Level 1 threshold (default 5000)
  failThreshold?:  number;           // Level 2 fail count (default 2)
  scoreThreshold?: number;           // Level 3 score threshold (default 0.40)
  disabled?:       boolean;
}

export function useGhostReplay({
  strokeId,
  failedAttempts,
  lastScore,
  isDrawing,
  inactivityMs   = 5000,
  failThreshold  = 2,
  scoreThreshold = 0.40,
  disabled       = false,
}: UseGhostReplayOptions) {
  const [replayLevel, setReplayLevel] = useState<ReplayLevel>(0);
  const inactivityTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset everything when the stroke changes
  useEffect(() => {
    setReplayLevel(0);
    if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
  }, [strokeId]);

  // ── Level 1: Inactivity timer ──────────────────────────────────────────────
  useEffect(() => {
    if (disabled || isDrawing) {
      // User is actively drawing — reset the inactivity timer
      if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
      return;
    }

    inactivityTimer.current = setTimeout(() => {
      setReplayLevel((prev) => Math.max(prev, 1) as ReplayLevel);
    }, inactivityMs);

    return () => {
      if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
    };
  }, [isDrawing, strokeId, disabled, inactivityMs]);

  // ── Level 2: Failed attempts ───────────────────────────────────────────────
  useEffect(() => {
    if (disabled) return;
    if (failedAttempts >= failThreshold) {
      setReplayLevel((prev) => Math.max(prev, 2) as ReplayLevel);
    }
  }, [failedAttempts, failThreshold, disabled]);

  // ── Level 3: Low accuracy score ───────────────────────────────────────────
  useEffect(() => {
    if (disabled) return;
    if (lastScore !== null && lastScore < scoreThreshold) {
      setReplayLevel((prev) => Math.max(prev, 3) as ReplayLevel);
    }
  }, [lastScore, scoreThreshold, disabled]);

  const dismissReplay = useCallback(() => {
    setReplayLevel(0);
    // Restart inactivity timer after dismissal
    if (inactivityTimer.current) clearTimeout(inactivityTimer.current);
  }, []);

  return { replayLevel, dismissReplay };
}
