/**
 * ProgressSection.tsx — Weekly accuracy trend + best/worst letters
 */

import type { ProgressTrendResponse } from "../../api/analytics";
import type { ProfileType } from "../../utils/ageUtils";

interface Props { data: ProgressTrendResponse; profileType: ProfileType }

const VELOCITY_CONFIG = {
  fast:   { icon: "⚡", label: "Fast learner",  color: "text-green-600 dark:text-green-400" },
  steady: { icon: "🏃", label: "Steady pace",   color: "text-blue-500 dark:text-blue-400"  },
  slow:   { icon: "🐢", label: "Building pace", color: "text-amber-500 dark:text-amber-400" },
};

export default function ProgressSection({ data, profileType: _profileType }: Props) {
  const velConf = VELOCITY_CONFIG[data.velocity] || VELOCITY_CONFIG.steady;
  const nonZero = data.weekly_accuracy.filter(w => w > 0);
  const peak    = nonZero.length > 0 ? Math.max(...nonZero) : 0;

  return (
    <div className="rounded-3xl bg-surface shadow-sm border border-border p-6 flex flex-col gap-5 transition-all duration-300">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-textPrimary text-sm">Accuracy Progress</h3>
        <span className={`text-xs font-semibold ${velConf.color}`}>
          {velConf.icon} {velConf.label}
        </span>
      </div>

      {/* Rolling average highlight */}
      <div className="text-center py-3 bg-surface-hover rounded-2xl border border-border/40">
        <div className="text-5xl font-black text-indigo shadow-glowIndigo">
          {Math.round(data.rolling_average * 100)}%
        </div>
        <p className="text-xs text-textSecondary mt-1.5 font-medium">5-session rolling average</p>
      </div>

      {/* 4-week bar chart (text-only, Phase 4.5 adds sparkline) */}
      <div>
        <p className="text-xs text-textSecondary mb-3 font-medium">Weekly Accuracy Trend (Last 4 weeks)</p>
        <div className="flex items-end gap-3 h-24 px-2">
          {data.weekly_accuracy.map((acc, i) => {
            const pct = peak > 0 ? (acc / peak) * 100 : 0;
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-2">
                <div
                  className="w-full rounded-t-lg bg-gradient-to-t from-indigo-500 to-indigo-700 dark:from-indigo-600 dark:to-indigo-400 hover:from-indigo-600 hover:to-indigo-800 transition-all duration-500 shadow-sm"
                  style={{ height: `${Math.max(pct, acc > 0 ? 8 : 0)}%` }}
                />
                <span className="text-xs text-textSecondary font-semibold">
                  {acc > 0 ? `${Math.round(acc * 100)}%` : "—"}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Best / worst letters */}
      {(data.best_letters.length > 0 || data.worst_letters.length > 0) && (
        <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border/50">
          {data.best_letters.length > 0 && (
            <div className="rounded-2xl bg-green-50 dark:bg-green-950/20 border border-green-100 dark:border-green-900/40 p-4">
              <p className="text-xs text-green-600 dark:text-green-400 font-bold mb-2">✅ Top Traced Letters</p>
              <div className="flex flex-wrap gap-2">
                {data.best_letters.map(l => (
                  <span key={l} className="text-sm font-extrabold bg-green-500 text-white
                    w-8 h-8 rounded-xl flex items-center justify-center shadow-sm">{l}</span>
                ))}
              </div>
            </div>
          )}
          {data.worst_letters.length > 0 && (
            <div className="rounded-2xl bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/40 p-4">
              <p className="text-xs text-amber-600 dark:text-amber-400 font-bold mb-2">⚠️ Focus Areas</p>
              <div className="flex flex-wrap gap-2">
                {data.worst_letters.map(l => (
                  <span key={l} className="text-sm font-extrabold bg-amber-500 text-white
                    w-8 h-8 rounded-xl flex items-center justify-center shadow-sm">{l}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
