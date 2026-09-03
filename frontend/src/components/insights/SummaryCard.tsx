/**
 * SummaryCard.tsx — Home-screen analytics summary
 *
 * Shows: level badge, XP bar, streak, engagement badge, active days
 * Profile-aware rendering.
 */

import type { DashboardSummaryResponse } from "../../api/analytics";
import type { ProfileType } from "../../utils/ageUtils";

interface Props {
  data:        DashboardSummaryResponse;
  profileType: ProfileType;
}

const ENGAGEMENT_CONFIG = {
  high:   { label: "High Engagement",   dot: "bg-green-500",  text: "text-green-700 dark:text-green-300",  badge: "bg-green-100 dark:bg-green-950/40 border border-green-200/20"  },
  medium: { label: "Good Engagement",   dot: "bg-amber-400",  text: "text-amber-700 dark:text-amber-300",  badge: "bg-amber-100 dark:bg-amber-950/40 border border-amber-200/20"  },
  low:    { label: "Low Engagement",    dot: "bg-red-400",    text: "text-red-700 dark:text-red-300",    badge: "bg-red-100 dark:bg-red-950/40 border border-red-200/20"    },
};

const TREND_CONFIG = {
  improving: { icon: "📈", label: "Improving",  color: "text-green-600 dark:text-green-400" },
  stable:    { icon: "➡️", label: "Stable",     color: "text-blue-500 dark:text-blue-400"  },
  declining: { icon: "📉", label: "Declining",  color: "text-red-500 dark:text-red-400"   },
};

const STREAK_EMOJI = { active: "🔥", at_risk: "⚠️", broken: "💤" };

export default function SummaryCard({ data, profileType }: Props) {
  const xpInLevel    = data.total_xp % 100;
  const xpPct        = xpInLevel;                            // out of 100
  const engConf      = ENGAGEMENT_CONFIG[data.engagement_level];
  const trendConf    = TREND_CONFIG[data.accuracy_trend];
  const streakEmoji  = STREAK_EMOJI[data.streak_status];

  const isEarly = profileType === "early_learner";
  const isChild = profileType === "child";

  return (
    <div className="rounded-3xl bg-surface shadow-sm hover:shadow-md border border-border p-6 flex flex-col gap-5 transition-all duration-300">
      {/* Header: Level + XP */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`rounded-xl px-3 py-1.5 font-bold text-white text-xs tracking-wide shadow-sm
            ${isEarly ? "bg-purple-500" : isChild ? "bg-indigo-500" : "bg-indigo-600 dark:bg-indigo-500"}`}>
            Level {data.level}
          </div>
          <span className="text-xs text-textSecondary font-semibold">{data.total_xp} XP total</span>
        </div>
        {/* Engagement badge */}
        <span className={`text-xs font-bold px-3 py-1 rounded-full
          ${engConf.badge} ${engConf.text} flex items-center gap-1.5`}>
          <span className={`w-1.5 h-1.5 rounded-full ${engConf.dot} inline-block`} />
          {engConf.label}
        </span>
      </div>

      {/* XP Progress bar */}
      <div>
        <div className="flex justify-between text-xs text-textSecondary mb-1.5 font-medium">
          <span>{xpInLevel} / 100 XP</span>
          <span>{100 - xpInLevel} to level {data.level + 1}</span>
        </div>
        <div className="h-3 bg-border rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 bg-gradient-to-r
              ${isEarly ? "from-purple-400 to-pink-400" : isChild ? "from-indigo-400 to-purple-400" : "from-indigo-500 to-indigo-700"}`}
            style={{ width: `${xpPct}%` }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 sm:gap-4 text-center">
        {/* Streak */}
        <div className="rounded-2xl bg-surface-hover border border-border/50 py-3.5 px-1 sm:px-2 hover:scale-[1.02] transition-transform duration-300">
          <div className="text-xl sm:text-2xl">{streakEmoji}</div>
          <div className="text-base sm:text-xl font-bold text-textPrimary leading-none mt-1.5">
            {data.current_streak}
          </div>
          <div className="text-[10px] sm:text-xs text-textSecondary mt-1 font-semibold leading-tight">
            {data.streak_status === "at_risk" ? "At risk!" : "Day streak"}
          </div>
        </div>

        {/* Accuracy */}
        <div className="rounded-2xl bg-surface-hover border border-border/50 py-3.5 px-1 sm:px-2 hover:scale-[1.02] transition-transform duration-300">
          <div className={`text-lg sm:text-xl ${trendConf.color}`}>{trendConf.icon}</div>
          <div className="text-base sm:text-xl font-bold text-textPrimary leading-none mt-1.5">
            {Math.round(data.rolling_accuracy * 100)}%
          </div>
          <div className={`text-[10px] sm:text-xs mt-1 font-semibold leading-tight ${trendConf.color}`}>{trendConf.label}</div>
        </div>

        {/* Active days */}
        <div className="rounded-2xl bg-surface-hover border border-border/50 py-3.5 px-1 sm:px-2 hover:scale-[1.02] transition-transform duration-300">
          <div className="text-xl sm:text-2xl">📅</div>
          <div className="text-base sm:text-xl font-bold text-textPrimary leading-none mt-1.5">
            {data.active_days_this_week}/7
          </div>
          <div className="text-[10px] sm:text-xs text-textSecondary mt-1 font-semibold leading-tight">Days active</div>
        </div>
      </div>

      {/* At-risk warning */}
      {data.streak_status === "at_risk" && (
        <div className="rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200/20 px-3 py-2 text-xs text-amber-700 dark:text-amber-400 font-medium">
          ⚠️ {isEarly ? "Practice today to keep your streak! 🔥" : "Practice today to keep your streak alive."}
        </div>
      )}

      {/* Difficulty + Promotion readiness */}
      <div className="flex items-center justify-between text-xs text-textSecondary pt-2 border-t border-border/50 font-medium">
        <span>Current difficulty: <strong className="text-textPrimary capitalize">{data.current_difficulty}</strong></span>
        <span>
          Promotion readiness: <strong className={data.promotion_readiness >= 0.85 ? "text-green-500" : "text-textPrimary"}>
            {Math.round(data.promotion_readiness * 100)}%
          </strong>
        </span>
      </div>
    </div>
  );
}
