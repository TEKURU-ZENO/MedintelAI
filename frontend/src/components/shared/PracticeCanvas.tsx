/**
 * PracticeCanvas.tsx — Unified Drawing Canvas (Phase 3 upgrade)
 *
 * Changes from Phase 2:
 *  - Uses Pointer Events API exclusively (stylus/tablet/Apple Pencil support)
 *  - Accepts `lockedStrokes` — strokes rendered faded that user can't draw yet
 *  - Accepts `completedStrokes` — rendered in green with ✓ indicator
 *  - Accepts `tracePercent` — displayed as overlay
 *  - Ghost guide now shows only the ACTIVE stroke, not all strokes
 *  - Drawing is delegated to useStrokeTracker hook (no internal mouse/touch logic)
 *
 * Props:
 *   onStrokeEnd         — called after each stroke completes (for guidance event)
 *   onStrokesChange     — called with all strokes (for auto-save)
 *   svgGuidePath        — full letter SVG (rendered faded as background)
 *   activeStrokePath    — current stroke SVG path only (rendered as active guide)
 *   startPoint          — start dot for current stroke
 *   lockedStrokes       — stroke IDs that are greyed/locked
 *   completedStrokes    — stroke IDs shown in green
 *   tracePercent        — 0–100 overlay
 *   profileType         — drives ink colour + border
 *   disabled            — freeze canvas
 */
import { useRef, useEffect, useCallback } from "react";
import { useStrokeTracker } from "../../hooks/useStrokeTracker";
import type { StrokeData } from "../../api/sessions";
import type { ProfileType } from "../../utils/ageUtils";

interface Props {
  onStrokeEnd?:        (stroke: StrokeData, allStrokes: StrokeData[]) => void;
  onStrokesChange?:    (strokes: StrokeData[]) => void;
  svgGuidePath?:       string;        // full letter background guide
  activeStrokePath?:   string;        // current stroke only (rendered solid)
  startPoint?:         [number, number];
  lockedStrokes?:      number[];
  completedStrokes?:   number[];
  tracePercent?:       number;
  width?:              number;
  height?:             number;
  disabled?:           boolean;
  profileType?:        ProfileType;
}

export default function PracticeCanvas({
  onStrokeEnd,
  onStrokesChange,
  svgGuidePath,
  activeStrokePath,
  startPoint,
  completedStrokes = [],
  tracePercent,
  width    = 400,
  height   = 400,
  disabled = false,
  profileType = "adult",
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const lineWidth =
    profileType === "early_learner" ? 7
    : profileType === "child"       ? 5
    :                                  3.5;

  // ── Stroke tracker (Pointer Events, inactivity analytics) ─────────────────
  const { strokes, clearStrokes, currentPoints, isDrawing } = useStrokeTracker({
    canvasRef,
    disabled,
    onStrokeEnd,
    onStrokesChange,
  });

  // ── Canvas redraw ─────────────────────────────────────────────────────────
  const redraw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx   = canvas.getContext("2d")!;
    const sw    = canvas.width;
    const sh    = canvas.height;
    const scaleX = sw / 100;
    const scaleY = sh / 100;

    // Read dynamic CSS variables for theme and dark-mode adaptation
    const style = window.getComputedStyle(canvas);
    const defaultInk = style.getPropertyValue("--color-canvasInk").trim() || "#1e293b";
    const canvasGuide = style.getPropertyValue("--color-canvasGuide").trim() || "rgba(200, 210, 240, 0.4)";
    const canvasGlow = style.getPropertyValue("--color-canvasGlow").trim() || "rgba(99, 102, 241, 0.15)";
    const indigoColor = style.getPropertyValue("--color-indigo").trim() || "#4f46e5";
    const lavenderColor = style.getPropertyValue("--color-lavender").trim() || "#d8b4fe";
    const successColor = style.getPropertyValue("--color-success").trim() || "#22c55e";

    const inkColor =
      profileType === "early_learner" ? lavenderColor
      : profileType === "child"       ? indigoColor
      :                                  defaultInk;

    ctx.clearRect(0, 0, sw, sh);

    // ── Background SVG guide (full letter, very faint) ────────────────────
    if (svgGuidePath) {
      ctx.save();
      ctx.scale(scaleX, scaleY);
      const path = new Path2D(svgGuidePath);
      ctx.strokeStyle = canvasGuide;
      ctx.lineWidth   = 6 / scaleX;
      ctx.lineCap     = "round";
      ctx.setLineDash([8, 6]);
      ctx.stroke(path);
      ctx.restore();
      ctx.setLineDash([]);
    }

    // ── Active stroke guide (current stroke only, more visible) ──────────
    if (activeStrokePath) {
      ctx.save();
      ctx.scale(scaleX, scaleY);
      const activePath = new Path2D(activeStrokePath);
      ctx.strokeStyle = canvasGlow;
      ctx.lineWidth   = 5 / scaleX;
      ctx.lineCap     = "round";
      ctx.setLineDash([6, 5]);
      ctx.stroke(activePath);
      ctx.restore();
      ctx.setLineDash([]);
    }

    // ── Start point indicator ─────────────────────────────────────────────
    if (startPoint) {
      const sx = startPoint[0] * scaleX;
      const sy = startPoint[1] * scaleY;
      ctx.beginPath();
      ctx.arc(sx, sy, 7, 0, Math.PI * 2);
      ctx.fillStyle = indigoColor;
      ctx.fill();
      // Pulsing ring
      ctx.beginPath();
      ctx.arc(sx, sy, 11, 0, Math.PI * 2);
      ctx.strokeStyle = indigoColor;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // ── Drawn strokes ─────────────────────────────────────────────────────
    strokes.forEach((stroke) => {
      if (stroke.points.length < 2) return;
      const isCompleted = completedStrokes.includes(stroke.id);
      ctx.beginPath();
      ctx.strokeStyle = isCompleted ? successColor : inkColor;
      ctx.lineWidth   = lineWidth;
      ctx.lineCap     = "round";
      ctx.lineJoin    = "round";
      ctx.moveTo(stroke.points[0][0], stroke.points[0][1]);
      stroke.points.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
      ctx.stroke();

      // Green checkmark at end of completed strokes
      if (isCompleted) {
        const end = stroke.points[stroke.points.length - 1];
        ctx.fillStyle = successColor;
        ctx.font      = `${14 * (lineWidth / 4)}px sans-serif`;
        ctx.fillText("✓", end[0] + 5, end[1] - 5);
      }
    });

    // ── Currently drawing stroke (real-time, zero-rerender) ───────────────
    if (currentPoints && currentPoints.current.length > 1) {
      ctx.beginPath();
      ctx.strokeStyle = inkColor;
      ctx.lineWidth   = lineWidth;
      ctx.lineCap     = "round";
      ctx.lineJoin    = "round";
      ctx.moveTo(currentPoints.current[0][0], currentPoints.current[0][1]);
      currentPoints.current.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
      ctx.stroke();
    }
  }, [
    svgGuidePath, activeStrokePath, startPoint,
    strokes, completedStrokes, lineWidth, currentPoints, profileType
  ]);

  // ── RAF Render Loop ───────────────────────────────────────────────────────
  useEffect(() => {
    let animationFrameId: number;
    const renderLoop = () => {
      redraw();
      animationFrameId = requestAnimationFrame(renderLoop);
    };
    
    if (isDrawing) {
      renderLoop(); // Continuous 60fps draw while pointer is down
    } else {
      redraw(); // Single static redraw on pointer up
    }
    
    return () => cancelAnimationFrame(animationFrameId);
  }, [isDrawing, redraw]);

  // ── Border style ──────────────────────────────────────────────────────────
  const borderStyle =
    profileType === "early_learner"
      ? "rounded-[32px] shadow-md bg-canvasSurface ring-4 ring-white dark:ring-slate-800"
      : profileType === "child"
      ? "rounded-3xl shadow-md bg-canvasSurface border border-border"
      : "rounded-3xl shadow-md bg-canvasSurface border border-border";

  return (
    <div className="relative flex flex-col items-center gap-2">
      <div className="relative">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className={`touch-none cursor-crosshair transition-all duration-700 ease-out ${borderStyle} ${
            disabled ? "opacity-60 cursor-not-allowed" : "hover:shadow-md"
          }`}
          style={{ maxWidth: "100%", aspectRatio: `${width}/${height}` }}
        />
        {/* Trace percent overlay */}
        {tracePercent !== undefined && tracePercent > 0 && (
          <div className="absolute top-2 right-3 text-xs font-bold text-indigo-600 bg-white/80 rounded-full px-2 py-0.5 shadow-sm">
            {Math.round(tracePercent)}%
          </div>
        )}
      </div>

      {!disabled && (
        <button
          onClick={clearStrokes}
          className="text-xs text-gray-400 hover:text-red-500 transition-colors"
        >
          ✕ Clear
        </button>
      )}
    </div>
  );
}
