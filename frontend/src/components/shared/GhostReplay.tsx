/**
 * GhostReplay.tsx — Animated SVG path ghost replay component
 *
 * Animates the correct stroke path using stroke-dashoffset animation.
 * Shows at three intensity levels:
 *   Level 1 (inactivity) — faint, slow animation
 *   Level 2 (failed attempts) — normal speed, more visible
 *   Level 3 (low accuracy) — bright, with hint text
 *
 * Uses CSS animation on stroke-dashoffset to "draw" the path.
 */
import { useEffect, useRef } from "react";
import type { ReplayLevel } from "../../hooks/useGhostReplay";

interface Props {
  svgPath:     string;       // SVG path 'd' attribute for the stroke
  level:       ReplayLevel;  // 0 = hidden, 1/2/3 = increasing visibility
  strokeColor?: string;
  onDismiss?:  () => void;
}

const LEVEL_CONFIG = {
  1: { opacity: 0.35, speed: "3s", color: "#818cf8", label: null },
  2: { opacity: 0.65, speed: "2s", color: "#6366f1", label: "Watch the stroke path" },
  3: { opacity: 0.90, speed: "1.5s", color: "#4f46e5", label: "Follow this guide carefully" },
};

export default function GhostReplay({ svgPath, level, onDismiss }: Props) {
  const pathRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    if (!pathRef.current || level === 0) return;
    const path   = pathRef.current;
    const length = path.getTotalLength();
    path.style.strokeDasharray  = `${length}`;
    path.style.strokeDashoffset = `${length}`;
    // Force reflow
    void path.getBoundingClientRect();
    path.style.transition = `stroke-dashoffset ${LEVEL_CONFIG[level]?.speed ?? "2s"} ease-in-out`;
    path.style.strokeDashoffset = "0";
  }, [level, svgPath]);

  if (level === 0) return null;

  const cfg = LEVEL_CONFIG[level];

  return (
    <div className="relative">
      {/* SVG overlay */}
      <svg
        viewBox="0 0 100 100"
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ opacity: cfg.opacity }}
        aria-hidden="true"
      >
        <path
          ref={pathRef}
          d={svgPath}
          fill="none"
          stroke={cfg.color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Arrow at end of stroke to show direction */}
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="5" refY="5"
            markerWidth="6" markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={cfg.color} />
          </marker>
        </defs>
      </svg>

      {/* Hint label for Level 2+ */}
      {cfg.label && (
        <div className="absolute bottom-0 left-0 right-0 text-center pb-2">
          <span className="inline-block bg-indigo-600 text-white text-xs font-semibold px-3 py-1 rounded-full shadow">
            {cfg.label}
          </span>
        </div>
      )}

      {/* Dismiss button for Level 3 */}
      {level === 3 && onDismiss && (
        <button
          onClick={onDismiss}
          className="absolute top-2 right-2 text-xs text-gray-400 hover:text-gray-600 bg-white/80 rounded-full px-2 py-0.5"
        >
          Got it
        </button>
      )}
    </div>
  );
}
