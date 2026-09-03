/**
 * EngagementSection.tsx — Streak, consistency, session stats
 * Abandon rate is hidden for early_learner and child profiles.
 */

import type { EngagementMetricsResponse } from "../../api/analytics";
import type { ProfileType } from "../../utils/ageUtils";

interface Props { data: EngagementMetricsResponse; profileType: ProfileType }

const PATTERN_LABEL: Record<string, string> = {
  consistent:    "Consistent daily practice 🌟",
  weekday_only:  "Weekday focused — try weekends too",
  weekend_heavy: "Weekend focused — daily practice is better",
  irregular:     "Irregular — try a daily habit",
};

export default function EngagementSection({ data, profileType }: Props) {
  const showAbandon = profileType === "adult";
  const dots = Array.from({ length: data.total_days_window });

  return (
    <div className="rounded-3xl bg-surface shadow-sm border border-border p-6 flex flex-col gap-5 transition-all duration-300">
      <h3 className="font-semibold text-textPrimary text-sm">Practice Consistency</h3>

      {/* Streak */}
      <div className="flex items-center gap-4 py-1.5 px-3 bg-surface-hover border border-border/40 rounded-2xl">
        <div className="text-center">
          <div className="text-3xl font-black text-orange-500 flex items-center justify-center gap-0.5">
            {data.current_streak}
            <span className="text-xl">🔥</span>
          </div>
          <p className="text-[10px] text-textSecondary font-semibold uppercase tracking-wider">Current</p>
        </div>
        <div className="w-px h-10 bg-border" />
        <div className="text-center">
          <div className="text-xl font-bold text-textSecondary">{data.longest_streak}</div>
          <p className="text-[10px] text-textSecondary font-semibold uppercase tracking-wider">Best</p>
        </div>
        <div className="flex-1 text-right">
          <span className={`text-xs font-bold px-3 py-1 rounded-full
            ${data.streak_status === "active" ? "bg-green-100 dark:bg-green-950/40 text-green-700 dark:text-green-300 border border-green-200/10"
            : data.streak_status === "at_risk" ? "bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200/10"
            : "bg-surface-hover text-textSecondary border border-border/30"}`}>
            {data.streak_status === "active"  ? "🔥 Active"
           : data.streak_status === "at_risk" ? "⚠️ At Risk"
           :                                    "💤 Broken"}
          </span>
        </div>
      </div>

      {/* At-risk banner */}
      {data.at_risk && (
        <div className="rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200/20 px-3 py-2.5 text-xs text-amber-700 dark:text-amber-400 font-medium animate-pulse">
          ⚠️ Practice today to keep your streak alive!
        </div>
      )}

      {/* 14-day dot calendar */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-xs text-textSecondary font-medium">Last {data.total_days_window} days activity</p>
          <p className="text-xs font-bold text-indigo">
            {data.active_days} / {data.total_days_window} days active
          </p>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {dots.map((_, i) => {
            const isActive = i >= data.total_days_window - data.active_days;
            return (
              <div
                key={i}
                className={`w-5 h-5 rounded-md transition-all duration-300 hover:scale-110 ${isActive ? "bg-indigo shadow-glowIndigo" : "bg-border/60"}`}
                title={isActive ? "Active day" : "No session recorded"}
              />
            );
          })}
        </div>
        <p className="text-xs text-textSecondary font-semibold italic">{PATTERN_LABEL[data.practice_pattern] || "Keep up the work!"}</p>
      </div>

      {/* Session stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-2xl bg-surface-hover border border-border/40 p-4 text-center">
          <div className="text-xl font-bold text-textPrimary">
            {data.avg_session_seconds > 0
              ? `${Math.round(data.avg_session_seconds)}s`
              : "—"}
          </div>
          <p className="text-xs text-textSecondary font-medium mt-1">Avg Session Time</p>
        </div>
        {showAbandon && (
          <div className="rounded-2xl bg-surface-hover border border-border/40 p-4 text-center">
            <div className={`text-xl font-bold ${data.abandon_rate > 0.30 ? "text-danger" : "text-textPrimary"}`}>
              {Math.round(data.abandon_rate * 100)}%
            </div>
            <p className="text-xs text-textSecondary font-medium mt-1">Abandon Rate</p>
          </div>
        )}
        {!showAbandon && (
          <div className="rounded-2xl bg-surface-hover border border-border/40 p-4 text-center">
            <div className="text-xl font-bold text-indigo">
              {Math.round(data.consistency_score * 100)}%
            </div>
            <p className="text-xs text-textSecondary font-medium mt-1">Consistency</p>
          </div>
        )}
      </div>
    </div>
  );
}
