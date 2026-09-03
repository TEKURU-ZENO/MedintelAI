/**
 * src/components/studio/WritingQualityPanel.tsx
 *
 * Post-session quality report display.
 * Philosophy: Never show percentages. Never say "wrong."
 * Show quality bands, trends, and one focus area.
 * Animated metric reveals for premium feel.
 */
import { useEffect, useState } from "react";
import type { WritingQualityReport, QualityBand } from "../../api/studio";
import type { ProfileType } from "../../utils/ageUtils";

interface Props {
  report: WritingQualityReport;
  profileType: ProfileType;
}

// ── Band config ────────────────────────────────────────────────────────────────
const BAND_CONFIG: Record<QualityBand, { label: string; emoji: string; color: string; bg: string }> = {
  developing:  { label: "Developing",  emoji: "🌱", color: "text-amber-700",  bg: "bg-amber-50  ring-amber-200" },
  building:    { label: "Building",    emoji: "🔨", color: "text-blue-700",   bg: "bg-blue-50   ring-blue-200"  },
  strong:      { label: "Strong",      emoji: "⭐", color: "text-indigo-700", bg: "bg-indigo-50 ring-indigo-200"},
  exceptional: { label: "Exceptional", emoji: "🏆", color: "text-purple-700", bg: "bg-purple-50 ring-purple-200"},
};

const STRENGTH_LABELS: Record<string, { label: string; emoji: string }> = {
  smoothness:  { label: "Stroke Smoothness", emoji: "🌊" },
  confidence:  { label: "Writing Confidence", emoji: "💪" },
  spacing:     { label: "Letter Spacing",    emoji: "💭" },
  baseline:    { label: "Line Alignment",    emoji: "📏" },
};

// ── Animated metric bar ───────────────────────────────────────────────────────
function MetricBar({ value, color }: { value: number; color: string }) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setWidth(Math.round(value * 100)), 200);
    return () => clearTimeout(t);
  }, [value]);

  return (
    <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${color}`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function WritingQualityPanel({ report, profileType }: Props) {
  const [visible, setVisible] = useState(false);
  useEffect(() => { const t = setTimeout(() => setVisible(true), 100); return () => clearTimeout(t); }, []);

  const band   = BAND_CONFIG[report.quality_band];
  const strength = STRENGTH_LABELS[report.primary_strength] ?? { label: report.primary_strength, emoji: "✨" };
  const focus    = STRENGTH_LABELS[report.primary_focus_area] ?? { label: report.primary_focus_area, emoji: "🎯" };

  const metrics = [
    { label: "Smoothness",       value: report.motor.smoothness_score,           color: "bg-indigo-400" },
    { label: "Confidence",       value: report.motor.stroke_confidence,           color: "bg-violet-400" },
    { label: "Line Alignment",   value: report.spatial.baseline_consistency,      color: "bg-sky-400"    },
    { label: "Spacing",          value: report.spatial.spacing_regularity,        color: "bg-emerald-400"},
  ];

  return (
    <div className={`w-full max-w-md mx-auto space-y-5 transition-all duration-500 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>

      {/* Band Badge */}
      <div className="text-center">
        <div className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold ring-1 ${band.bg} ${band.color}`}>
          <span className="text-lg">{band.emoji}</span>
          <span>{band.label} Writer</span>
        </div>
      </div>

      {/* Feedback messages */}
      <div className="space-y-2">
        {report.feedback_messages.map((msg, i) => (
          <div
            key={i}
            className="flex items-start gap-2 px-4 py-3 bg-white rounded-xl border border-gray-100 shadow-xs text-sm text-gray-700"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            {msg}
          </div>
        ))}
      </div>

      {/* Strength → Focus split */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 bg-indigo-50 rounded-xl border border-indigo-100 text-center">
          <p className="text-xs text-indigo-400 font-medium uppercase tracking-wide mb-1">Today's Strength</p>
          <p className="text-sm font-semibold text-indigo-700">{strength.emoji} {strength.label}</p>
        </div>
        <div className="p-3 bg-amber-50 rounded-xl border border-amber-100 text-center">
          <p className="text-xs text-amber-400 font-medium uppercase tracking-wide mb-1">
            {profileType === "adult" ? "Focus Area" : "Keep Working On"}
          </p>
          <p className="text-sm font-semibold text-amber-700">{focus.emoji} {focus.label}</p>
        </div>
      </div>

      {/* Metric bars — no numbers */}
      {profileType !== "early_learner" && (
        <div className="p-4 bg-white rounded-xl border border-gray-100 shadow-xs space-y-3">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Writing Quality Signals</p>
          {metrics.map((m) => (
            <div key={m.label} className="space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">{m.label}</span>
              </div>
              <MetricBar value={m.value} color={m.color} />
            </div>
          ))}
          <p className="text-xs text-gray-300 italic">Bars show relative quality — not scores or grades</p>
        </div>
      )}

      {/* Emotional state (visible only for adult — parents see more data) */}
      {profileType === "adult" && report.emotional_snapshot.fatigue_estimate > 0.4 && (
        <div className="px-4 py-3 bg-orange-50 border border-orange-100 rounded-xl text-sm text-orange-700">
          🍃 Slight fatigue detected in this session — shorter sessions may yield better quality.
        </div>
      )}
    </div>
  );
}
