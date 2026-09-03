/**
 * src/components/studio/StudioCanvas.tsx
 *
 * The free writing canvas. No guides, no overlays, no reference paths.
 * Just a breathing white surface and the learner's hand.
 *
 * Built on PracticeCanvas's RAF loop architecture but stripped of all
 * guided-mode concerns. Larger default size. Exports thumbnail capture.
 */
import { useRef, useEffect, useCallback, useState } from "react";
import type { ProfileType } from "../../utils/ageUtils";

export interface StrokePoint { x: number; y: number; t: number }
export interface Stroke { points: StrokePoint[]; startTime: number }

interface Props {
  profileType: ProfileType;
  onStrokesChange?: (strokes: Stroke[]) => void;
  width?: number;
  height?: number;
  isDisabled?: boolean;
}

const COLORS: Record<ProfileType, string> = {
  early_learner: "#6366f1",  // indigo — vibrant and friendly
  child:         "#6366f1",
  adult:         "#374151",  // dark gray — clean and professional
};

export default function StudioCanvas({
  profileType,
  onStrokesChange,
  width = 480,
  height = 380,
  isDisabled = false,
}: Props) {
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const rafRef     = useRef<number | null>(null);
  const isDrawing  = useRef(false);
  const currentPts = useRef<StrokePoint[]>([]);
  const allStrokes = useRef<Stroke[]>([]);
  const [strokeCount, setStrokeCount] = useState(0);
  const [isPulsing, setIsPulsing] = useState(false);  // subtle "alive" feedback

  const strokeColor = COLORS[profileType] ?? COLORS.child;

  // ── RAF render loop ───────────────────────────────────────────────────────
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineCap  = "round";
    ctx.lineJoin = "round";

    // Render all completed strokes
    for (const stroke of allStrokes.current) {
      if (stroke.points.length < 2) continue;
      ctx.beginPath();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth   = profileType === "early_learner" ? 4 : 3;
      ctx.globalAlpha = 0.9;
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
      for (let i = 1; i < stroke.points.length; i++) {
        const prev = stroke.points[i - 1];
        const curr = stroke.points[i];
        // Smooth quadratic bezier interpolation
        const mx = (prev.x + curr.x) / 2;
        const my = (prev.y + curr.y) / 2;
        ctx.quadraticCurveTo(prev.x, prev.y, mx, my);
      }
      ctx.stroke();
    }

    // Render active stroke (being drawn now)
    if (currentPts.current.length >= 2) {
      ctx.beginPath();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth   = profileType === "early_learner" ? 4 : 3;
      ctx.globalAlpha = 1.0;
      ctx.moveTo(currentPts.current[0].x, currentPts.current[0].y);
      for (let i = 1; i < currentPts.current.length; i++) {
        const prev = currentPts.current[i - 1];
        const curr = currentPts.current[i];
        const mx   = (prev.x + curr.x) / 2;
        const my   = (prev.y + curr.y) / 2;
        ctx.quadraticCurveTo(prev.x, prev.y, mx, my);
      }
      ctx.stroke();
    }

    rafRef.current = requestAnimationFrame(render);
  }, [strokeColor, profileType]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(render);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [render]);

  // ── Pointer handlers ───────────────────────────────────────────────────────
  const getPoint = (e: React.PointerEvent<HTMLCanvasElement>): StrokePoint => {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top, t: Date.now() };
  };

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (isDisabled) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    isDrawing.current = true;
    currentPts.current = [getPoint(e)];
    setIsPulsing(true);
  }, [isDisabled]);

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!isDrawing.current || isDisabled) return;
    currentPts.current.push(getPoint(e));
  }, [isDisabled]);

  const onPointerUp = useCallback(() => {
    if (!isDrawing.current) return;
    isDrawing.current = false;

    if (currentPts.current.length >= 2) {
      const newStroke: Stroke = {
        points: [...currentPts.current],
        startTime: currentPts.current[0].t,
      };
      allStrokes.current = [...allStrokes.current, newStroke];
      setStrokeCount(allStrokes.current.length);
      onStrokesChange?.(allStrokes.current);
    }
    currentPts.current = [];
    setIsPulsing(false);
  }, [onStrokesChange]);

  const clearCanvas = () => {
    allStrokes.current = [];
    currentPts.current = [];
    setStrokeCount(0);
    onStrokesChange?.([]);
  };

  // ── Thumbnail capture (Addition 3) ────────────────────────────────────────
  const captureThumbnail = useCallback((): string | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    try {
      return canvas.toDataURL("image/png");
    } catch {
      return null;
    }
  }, []);

  // Expose captureThumbnail via ref callback pattern
  useEffect(() => {
    (canvasRef.current as any)._captureThumbnail = captureThumbnail;
  }, [captureThumbnail]);

  return (
    <div className="relative flex flex-col items-center gap-3">
      {/* Canvas with breathing border */}
      <div
        className={[
          "relative rounded-2xl overflow-hidden transition-all duration-500",
          isPulsing
            ? "shadow-[0_0_0_3px_rgba(99,102,241,0.3),0_8px_30px_rgba(99,102,241,0.12)]"
            : "shadow-md border border-gray-100",
        ].join(" ")}
      >
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
          style={{ background: "#FAFAFA", touchAction: "none", display: "block", cursor: isDisabled ? "default" : "crosshair" }}
        />

        {/* Stroke count ghost */}
        {strokeCount > 0 && (
          <div className="absolute bottom-2 right-3 text-xs text-gray-300 font-mono select-none">
            {strokeCount} {strokeCount === 1 ? "stroke" : "strokes"}
          </div>
        )}

        {/* Placeholder hint when empty */}
        {strokeCount === 0 && !isDrawing.current && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <p className="text-gray-300 text-sm select-none">
              {profileType === "early_learner" ? "Draw anything! 🎨"
               : profileType === "child"       ? "Start writing…"
               :                                  "Write freely — no rules."}
            </p>
          </div>
        )}
      </div>

      {/* Controls */}
      {strokeCount > 0 && !isDisabled && (
        <button
          onClick={clearCanvas}
          className="text-xs text-gray-400 hover:text-red-400 transition-colors underline underline-offset-2"
        >
          Clear canvas
        </button>
      )}
    </div>
  );
}

/** Helper to capture thumbnail from a StudioCanvas ref */
export function captureThumbnailFromRef(ref: React.RefObject<HTMLCanvasElement | null>): string | null {
  return (ref.current as any)?._captureThumbnail?.() ?? null;
}
