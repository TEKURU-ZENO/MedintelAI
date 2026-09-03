/**
 * useStrokeTracker.ts — Pointer Events stroke capture hook
 *
 * Uses the Pointer Events API exclusively (not separate mouse/touch handlers).
 * This gives us:
 *   - Stylus / Apple Pencil support
 *   - Pressure data
 *   - Tablet / Chromebook compatibility
 *   - Unified mouse + touch in one handler
 *
 * Tracks:
 *   - Strokes with [x, y, timestamp] points
 *   - Inactivity analytics: time_before_first_stroke, pause_between_strokes
 *   - Current drawing state
 */

import { useRef, useState, useCallback, useEffect } from "react";
import type { StrokeData } from "../api/sessions";

export interface InactivityAnalytics {
  time_before_first_stroke_ms: number | null;
  pause_between_strokes_ms: number[];        // gap between each stroke
  total_hesitation_ms: number;
}

export interface StrokeTrackerState {
  strokes:      StrokeData[];
  isDrawing:    boolean;
  analytics:    InactivityAnalytics;
  strokeCount:  number;
  currentPoints: React.MutableRefObject<[number, number, number][]>;
}

interface UseStrokeTrackerOptions {
  canvasRef:         React.RefObject<HTMLCanvasElement | null>;
  onStrokeEnd?:      (stroke: StrokeData, allStrokes: StrokeData[]) => void;
  onStrokesChange?:  (strokes: StrokeData[]) => void;
  disabled?:         boolean;
}

export function useStrokeTracker({
  canvasRef,
  onStrokeEnd,
  onStrokesChange,
  disabled = false,
}: UseStrokeTrackerOptions) {
  const [strokes,   setStrokes]   = useState<StrokeData[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);

  // Internal refs (no re-render on update)
  const currentPoints  = useRef<[number, number, number][]>([]);
  const nextId         = useRef(1);
  const sessionStartMs = useRef<number>(Date.now());
  const firstStrokeMs  = useRef<number | null>(null);
  const lastStrokeEndMs = useRef<number | null>(null);
  const pausesBetween  = useRef<number[]>([]);

  const getCanvasPos = useCallback(
    (e: PointerEvent): [number, number] => {
      const canvas = canvasRef.current;
      if (!canvas) return [0, 0];
      const rect   = canvas.getBoundingClientRect();
      const scaleX = canvas.width  / rect.width;
      const scaleY = canvas.height / rect.height;
      return [
        (e.clientX - rect.left) * scaleX,
        (e.clientY - rect.top)  * scaleY,
      ];
    },
    [canvasRef],
  );

  // ── Pointer event handlers ─────────────────────────────────────────────────

  const onPointerDown = useCallback(
    (e: PointerEvent) => {
      if (disabled) return;
      e.preventDefault();
      canvasRef.current?.setPointerCapture(e.pointerId);

      const now = Date.now();
      // Track inactivity: time before FIRST stroke ever
      if (firstStrokeMs.current === null) {
        firstStrokeMs.current = now;
      }
      // Track pause between strokes
      if (lastStrokeEndMs.current !== null) {
        pausesBetween.current.push(now - lastStrokeEndMs.current);
      }

      const [x, y] = getCanvasPos(e);
      currentPoints.current = [[x, y, now]];
      setIsDrawing(true);
    },
    [disabled, getCanvasPos, canvasRef],
  );

  const onPointerMove = useCallback(
    (e: PointerEvent) => {
      if (!isDrawing || disabled) return;
      e.preventDefault();
      const [x, y] = getCanvasPos(e);
      currentPoints.current.push([x, y, Date.now()]);
    },
    [isDrawing, disabled, getCanvasPos],
  );

  const onPointerUp = useCallback(
    (_e: PointerEvent) => {
      if (!isDrawing) return;
      setIsDrawing(false);

      if (currentPoints.current.length < 2) {
        currentPoints.current = [];
        return;
      }

      const newStroke: StrokeData = {
        id:     nextId.current++,
        points: currentPoints.current.map(([x, y]) => [x, y]),
      };
      currentPoints.current = [];
      lastStrokeEndMs.current = Date.now();

      setStrokes((prev) => {
        const updated = [...prev, newStroke];
        onStrokesChange?.(updated);
        onStrokeEnd?.(newStroke, updated);
        return updated;
      });
    },
    [isDrawing, onStrokeEnd, onStrokesChange],
  );

  // ── Register pointer events on the canvas ─────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.addEventListener("pointerdown", onPointerDown, { passive: false });
    canvas.addEventListener("pointermove", onPointerMove, { passive: false });
    canvas.addEventListener("pointerup",   onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);
    return () => {
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup",   onPointerUp);
      canvas.removeEventListener("pointercancel", onPointerUp);
    };
  }, [canvasRef, onPointerDown, onPointerMove, onPointerUp]);

  // ── Analytics ─────────────────────────────────────────────────────────────

  const getAnalytics = useCallback((): InactivityAnalytics => {
    const timeBeforeFirst = firstStrokeMs.current !== null
      ? firstStrokeMs.current - sessionStartMs.current
      : null;
    const total = pausesBetween.current.reduce((a, b) => a + b, 0);
    return {
      time_before_first_stroke_ms: timeBeforeFirst,
      pause_between_strokes_ms:    [...pausesBetween.current],
      total_hesitation_ms:         total,
    };
  }, []);

  const clearStrokes = useCallback(() => {
    setStrokes([]);
    nextId.current = 1;
    onStrokesChange?.([]);
  }, [onStrokesChange]);

  const resetSession = useCallback(() => {
    clearStrokes();
    sessionStartMs.current  = Date.now();
    firstStrokeMs.current   = null;
    lastStrokeEndMs.current = null;
    pausesBetween.current   = [];
  }, [clearStrokes]);

  return {
    strokes,
    isDrawing,
    getAnalytics,
    clearStrokes,
    resetSession,
    strokeCount: strokes.length,
    currentPoints,
  };
}
