/**
 * PromotionBadge.tsx — Shown when promotion_readiness >= 0.85
 */
interface Props { nextDifficulty: string }

export default function PromotionBadge({ nextDifficulty }: Props) {
  return (
    <div className="mt-2 rounded-lg bg-gradient-to-r from-yellow-500 to-orange-500
      px-3 py-1.5 text-xs font-bold text-white text-center animate-pulse shadow-sm">
      🏆 Ready for {nextDifficulty}!
    </div>
  );
}

/**
 * ModuleGrid.tsx — Per-module performance cards with recommended_focus signals
 */
import type { ModulePerformanceResponse } from "../../api/analytics";

const FOCUS_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  ready_to_advance:     { icon: "🏆", label: "Ready to advance!",       color: "text-green-600 dark:text-green-400"  },
  needs_more_practice:  { icon: "🎯", label: "Keep practicing",         color: "text-amber-600 dark:text-amber-400"  },
  maintain_consistency: { icon: "✨", label: "On track — keep it up",   color: "text-blue-600 dark:text-blue-400"   },
  review_basics:        { icon: "⬇️", label: "Review basics",           color: "text-red-500 dark:text-red-400"    },
};

const NEXT_DIFFICULTY: Record<string, string> = {
  beginner:     "Intermediate",
  intermediate: "Advanced",
  advanced:     "Master",
};

const TREND_ICON: Record<string, string> = {
  improving: "📈", stable: "➡️", declining: "📉",
};

interface GridProps { modules: ModulePerformanceResponse[] }

export function ModuleGrid({ modules }: GridProps) {
  if (modules.length === 0) {
    return (
      <div className="rounded-3xl bg-surface shadow-sm border border-border p-6 text-center">
        <p className="text-sm text-textSecondary font-medium">Start your first practice session to see module stats.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="font-semibold text-textPrimary text-sm">Module Performance</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {modules.map((mod) => {
          const focus = FOCUS_CONFIG[mod.recommended_focus] || FOCUS_CONFIG.needs_more_practice;
          const readinessPct = Math.round(mod.promotion_readiness * 100);
          const showPromotion = mod.promotion_readiness >= 0.85;
          const nextDiff = NEXT_DIFFICULTY[mod.current_difficulty] ?? "Next";

          return (
            <div key={mod.module_type}
              className="rounded-3xl bg-surface shadow-sm border border-border p-5 flex flex-col gap-4 hover:shadow-md transition-all duration-300">
              {/* Module label + trend */}
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-textPrimary">{mod.label}</span>
                <span className="text-sm">{TREND_ICON[mod.accuracy_trend]}</span>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-3 text-center text-xs text-textSecondary border-t border-b border-border/40 py-2.5 my-0.5">
                <div>
                  <div className="text-base font-bold text-textPrimary">
                    {Math.round(mod.avg_accuracy * 100)}%
                  </div>
                  <div className="text-[10px] font-medium text-textSecondary uppercase tracking-wider">accuracy</div>
                </div>
                <div>
                  <div className="text-base font-bold text-textPrimary">{mod.sessions_completed}</div>
                  <div className="text-[10px] font-medium text-textSecondary uppercase tracking-wider">sessions</div>
                </div>
                <div>
                  <div className="text-base font-bold text-textPrimary capitalize">{mod.current_difficulty}</div>
                  <div className="text-[10px] font-medium text-textSecondary uppercase tracking-wider">level</div>
                </div>
              </div>

              {/* Promotion readiness bar */}
              <div>
                <div className="flex justify-between text-xs text-textSecondary mb-1.5 font-medium">
                  <span>Promotion readiness</span>
                  <span className={showPromotion ? "text-green-600 dark:text-green-400 font-bold" : ""}>{readinessPct}%</span>
                </div>
                <div className="h-2 bg-border rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500
                      ${showPromotion ? "bg-success" : "bg-indigo"}`}
                    style={{ width: `${readinessPct}%` }}
                  />
                </div>
              </div>

              {/* Recommended focus signal */}
              <div className={`text-xs font-bold ${focus.color}`}>
                {focus.icon} {focus.label}
              </div>

              {/* Promotion badge */}
              {showPromotion && <PromotionBadge nextDifficulty={nextDiff} />}

              {/* Last practiced */}
              {mod.last_practiced && (
                <p className="text-[10px] text-textTertiary font-medium">
                  Last practiced: {new Date(mod.last_practiced).toLocaleDateString()}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
