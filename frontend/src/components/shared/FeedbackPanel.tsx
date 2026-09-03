/**
 * FeedbackPanel.tsx — Event-driven adaptive feedback display
 *
 * feedbackType drives rendering behaviour, not just text:
 *   encouragement  → warm, positive (green/blue)
 *   correction     → constructive (amber)
 *   celebration    → success (purple/gold)
 *   warning        → needs attention (red)
 *   idle           → waiting for input (grey, subtle)
 *
 * Future phases attach:
 *   - TTS playback (Phase 7)
 *   - Sound effects (Phase 6)
 *   - Animations (Phase 6)
 */

export type FeedbackType =
  | "encouragement"
  | "correction"
  | "celebration"
  | "warning"
  | "idle";

interface Props {
  message: string;
  feedbackType: FeedbackType;
  profileType?: "early_learner" | "child" | "adult";
  visible?: boolean;
}

const CONFIG: Record<
  FeedbackType,
  { bg: string; border: string; text: string; icon: string }
> = {
  encouragement: {
    bg:     "bg-green-50",
    border: "border-green-200",
    text:   "text-green-800",
    icon:   "👍",
  },
  correction: {
    bg:     "bg-amber-50",
    border: "border-amber-200",
    text:   "text-amber-800",
    icon:   "💡",
  },
  celebration: {
    bg:     "bg-purple-50",
    border: "border-purple-200",
    text:   "text-purple-800",
    icon:   "🎉",
  },
  warning: {
    bg:     "bg-red-50",
    border: "border-red-200",
    text:   "text-red-700",
    icon:   "⚠️",
  },
  idle: {
    bg:     "bg-gray-50",
    border: "border-gray-200",
    text:   "text-gray-500",
    icon:   "✏️",
  },
};

export default function FeedbackPanel({
  message,
  feedbackType,
  profileType = "adult",
  visible = true,
}: Props) {
  if (!visible || !message) return null;

  const c = CONFIG[feedbackType] ?? CONFIG.idle;

  const textSize =
    profileType === "early_learner" ? "text-lg font-bold"
    : profileType === "child"       ? "text-base font-semibold"
    :                                  "text-sm font-medium";

  const iconSize =
    profileType === "early_learner" ? "text-3xl"
    : profileType === "child"       ? "text-2xl"
    :                                  "text-xl";

  const padding =
    profileType === "early_learner" ? "px-6 py-4"
    : profileType === "child"       ? "px-5 py-3"
    :                                  "px-4 py-3";

  return (
    <div
      className={`
        flex items-center gap-3 rounded-xl border
        ${c.bg} ${c.border} ${padding}
        transition-all duration-300 ease-in-out
      `}
      role="status"
      aria-live="polite"
    >
      <span className={iconSize} aria-hidden="true">{c.icon}</span>
      <p className={`${textSize} ${c.text}`}>{message}</p>
    </div>
  );
}
