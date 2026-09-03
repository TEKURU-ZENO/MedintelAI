/**
 * RewardBanner.tsx — XP award + level-up celebration
 *
 * Shown after POST /sessions/{id}/complete returns.
 * Phase 6 will add confetti + sound for early_learner and child profiles.
 *
 * Props:
 *   xpEarned       — XP awarded this session
 *   totalXp        — user's new total XP
 *   newLevel       — user's level after award
 *   levelUp        — whether a level boundary was crossed
 *   newStreak      — current streak after this session
 *   profileType    — drives visual intensity
 *   onDismiss      — callback when user closes banner
 */

interface Props {
  xpEarned: number;
  totalXp: number;
  newLevel: number;
  levelUp: boolean;
  newStreak: number;
  profileType?: "early_learner" | "child" | "adult";
  onDismiss: () => void;
}

const XP_PER_LEVEL = 100;

export default function RewardBanner({
  xpEarned,
  totalXp,
  newLevel,
  levelUp,
  newStreak,
  profileType = "adult",
  onDismiss,
}: Props) {
  const xpInLevel  = totalXp % XP_PER_LEVEL;
  const xpPercent  = Math.min((xpInLevel / XP_PER_LEVEL) * 100, 100);

  if (profileType === "early_learner") {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-3xl shadow-2xl p-8 max-w-sm w-full text-center space-y-4">
          <div className="text-6xl">{levelUp ? "🏆" : "⭐"}</div>
          <h2 className="text-3xl font-extrabold text-purple-700">
            {levelUp ? "Level Up!" : "Amazing!"}
          </h2>
          <p className="text-5xl font-black text-yellow-500">+{xpEarned} XP</p>
          {newStreak > 1 && (
            <p className="text-xl font-bold text-orange-500">
              🔥 {newStreak} day streak!
            </p>
          )}
          <button
            onClick={onDismiss}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-extrabold py-4 rounded-2xl text-xl transition-colors"
          >
            Keep Going! 🚀
          </button>
        </div>
      </div>
    );
  }

  if (profileType === "child") {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-4xl">{levelUp ? "🎊" : "✅"}</span>
            <div>
              <h2 className="text-xl font-bold text-gray-800">
                {levelUp ? `Level ${newLevel} reached!` : "Session complete!"}
              </h2>
              <p className="text-sm text-gray-500">Great work!</p>
            </div>
          </div>

          {/* XP earned */}
          <div className="bg-indigo-50 rounded-xl p-4 text-center">
            <p className="text-3xl font-black text-indigo-600">+{xpEarned} XP</p>
          </div>

          {/* XP Progress Bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-500 font-medium">
              <span>Level {newLevel}</span>
              <span>{xpInLevel} / {XP_PER_LEVEL} XP</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2.5">
              <div
                className="bg-gradient-to-r from-indigo-500 to-purple-500 h-2.5 rounded-full transition-all duration-700"
                style={{ width: `${xpPercent}%` }}
              />
            </div>
          </div>

          {newStreak > 1 && (
            <div className="flex items-center gap-2 text-orange-600 font-semibold text-sm">
              <span>🔥</span>
              <span>{newStreak} day streak! Keep it up!</span>
            </div>
          )}

          <button
            onClick={onDismiss}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 rounded-xl transition-colors"
          >
            Continue →
          </button>
        </div>
      </div>
    );
  }

  // Adult — clean, no fanfare
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-lg p-6 max-w-sm w-full space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">
            {levelUp ? `Level ${newLevel} reached` : "Session complete"}
          </h2>
          <span className="text-indigo-600 font-bold">+{xpEarned} XP</span>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-400">
            <span>Level {newLevel}</span>
            <span>{xpInLevel} / {XP_PER_LEVEL} XP</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-1.5">
            <div
              className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${xpPercent}%` }}
            />
          </div>
        </div>

        {newStreak > 1 && (
          <p className="text-xs text-gray-500">🔥 {newStreak}-day streak</p>
        )}

        <button
          onClick={onDismiss}
          className="w-full bg-gray-900 hover:bg-gray-700 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  );
}
