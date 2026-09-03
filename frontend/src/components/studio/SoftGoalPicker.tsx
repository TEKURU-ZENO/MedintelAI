/**
 * src/components/studio/SoftGoalPicker.tsx — Addition 4
 *
 * Optional pre-session goal selector. Non-pressuring, playful.
 * Renders as a horizontal pill selector. Skippable.
 */
import type { SoftGoal } from "../../api/studio";

interface Props {
  selectedGoal: SoftGoal | null;
  onSelect: (goal: SoftGoal | null) => void;
  profileType: "early_learner" | "child" | "adult";
}

const GOALS: { id: SoftGoal; emoji: string; label: string; childLabel: string; earlyLabel: string }[] = [
  { id: "smoother_writing", emoji: "🌊", label: "Smoother strokes",   childLabel: "Smoother writing",  earlyLabel: "Smooth lines!" },
  { id: "spacing",          emoji: "💭", label: "Better spacing",      childLabel: "More space",         earlyLabel: "More room!" },
  { id: "confidence",       emoji: "💪", label: "Build confidence",    childLabel: "Feel confident",     earlyLabel: "Be brave!" },
  { id: "free_drawing",     emoji: "🎨", label: "Free expression",     childLabel: "Just draw!",         earlyLabel: "Draw anything!" },
  { id: "storytelling",     emoji: "📖", label: "Write a story",       childLabel: "Tell a story",       earlyLabel: "Make a story!" },
];

export default function SoftGoalPicker({ selectedGoal, onSelect, profileType }: Props) {
  const getLabel = (g: typeof GOALS[0]) => {
    if (profileType === "early_learner") return g.earlyLabel;
    if (profileType === "child") return g.childLabel;
    return g.label;
  };

  const heading =
    profileType === "early_learner" ? "What do you want to do today? 🌈"
    : profileType === "child"       ? "What's your focus today? (optional)"
    :                                  "Set a writing intention (optional)";

  return (
    <div className="w-full max-w-lg mx-auto">
      <p className="text-center text-sm font-medium text-gray-500 mb-3">{heading}</p>

      <div className="flex flex-wrap justify-center gap-2">
        {GOALS.map((goal) => {
          const active = selectedGoal === goal.id;
          return (
            <button
              key={goal.id}
              onClick={() => onSelect(active ? null : goal.id)}
              className={[
                "flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200",
                active
                  ? "bg-indigo-100 text-indigo-700 ring-2 ring-indigo-300 scale-105"
                  : "bg-white text-gray-600 border border-gray-200 hover:border-indigo-300 hover:text-indigo-600 hover:scale-102",
              ].join(" ")}
              aria-pressed={active}
            >
              <span>{goal.emoji}</span>
              <span>{getLabel(goal)}</span>
            </button>
          );
        })}
      </div>

      {selectedGoal && (
        <p className="text-center text-xs text-indigo-400 mt-2 animate-pulse">
          ✓ Focus set — write freely and we'll track your progress
        </p>
      )}
    </div>
  );
}
