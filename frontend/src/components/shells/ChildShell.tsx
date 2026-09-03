/**
 * ChildShell.tsx — Profile shell for ages 6–15
 *
 * Design intent: motivational, progress-oriented.
 * XP bar, streak counter, level badge, module cards.
 * Content is filled in by Phase 2 module system.
 */
import { useAuth } from "../../auth/AuthContext";
import { useNavigate } from "react-router-dom";

const XP_PER_LEVEL = 100;

export default function ChildShell() {
  const { user, logout, themeMode, toggleTheme } = useAuth();
  const navigate = useNavigate();

  const xp = user?.xp_points ?? 0;
  const level = user?.level ?? 1;
  const xpInLevel = xp % XP_PER_LEVEL;
  const xpPercent = Math.min((xpInLevel / XP_PER_LEVEL) * 100, 100);
  const streak = user?.user_streak ?? 0;
  const firstName = user?.full_name?.split(" ")[0] ?? "Champion";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✍️</span>
          <div>
            <h1 className="font-bold text-gray-800 text-lg leading-none">
              AksharabyasaAI
            </h1>
            <p className="text-xs text-indigo-600 font-semibold">
              Welcome back, {firstName}! Keep it up 🌟
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Streak */}
          <div
            className="flex items-center gap-1.5 bg-orange-50 border border-orange-200 rounded-full px-3 py-1"
            title="Daily streak"
          >
            <span>🔥</span>
            <span className="text-orange-600 font-bold text-sm">{streak} days</span>
          </div>
          <button
            id="child-nav-progress"
            onClick={() => navigate("/insights")}
            className="text-sm text-indigo-600 font-semibold hover:text-indigo-800 transition-colors"
          >
            📊 My Progress
          </button>
          <button
            onClick={toggleTheme}
            className="w-8 h-8 rounded-full flex items-center justify-center text-lg hover:bg-surface-hover transition-colors"
            title={themeMode === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
          >
            {themeMode === "light" ? "🌙" : "☀️"}
          </button>
          <button
            id="child-logout"
            onClick={logout}
            className="text-sm text-gray-400 hover:text-red-500 transition-colors font-medium"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Level & XP Bar */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="bg-indigo-600 text-white text-xs font-bold px-2.5 py-1 rounded-full">
                LVL {level}
              </span>
              <span className="text-sm font-semibold text-gray-700">
                {firstName}'s Progress
              </span>
            </div>
            <span className="text-xs text-gray-400 font-medium">
              {xpInLevel} / {XP_PER_LEVEL} XP
            </span>
          </div>
          {/* XP Progress Bar */}
          <div className="w-full bg-gray-100 rounded-full h-3">
            <div
              className="bg-gradient-to-r from-indigo-500 to-purple-500 h-3 rounded-full transition-all duration-500"
              style={{ width: `${xpPercent}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">
            {XP_PER_LEVEL - xpInLevel} XP to reach Level {level + 1}
          </p>
        </div>

        {/* ── PRIMARY: Writing Studio Hero ─────────────────────────────── */}
        <button
          id="child-studio-cta"
          onClick={() => navigate("/studio")}
          className="w-full bg-gradient-to-r from-indigo-500 via-indigo-600 to-purple-600 rounded-2xl p-6
            flex items-center justify-between group transition-all duration-350 hover:shadow-lg hover:-translate-y-0.5 active:scale-98 shadow-md"
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-white/20 flex items-center justify-center text-3xl group-hover:scale-105 transition-transform duration-300">
              ✍️
            </div>
            <div className="text-left">
              <p className="text-base font-bold text-white">Open Writing Studio</p>
              <p className="text-white/80 text-xs mt-0.5">Write freely or draw anything you like! 🎨</p>
            </div>
          </div>
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-white text-lg group-hover:bg-white/30 transition-colors">
            ›
          </div>
        </button>

        {/* Module Selection */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-gray-800">
              Guided Practice
            </h2>
            <span className="text-xs text-gray-400 font-medium">Structured workouts</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <ModuleCard emoji="🔤" label="Alphabet" description="Trace A–Z" color="indigo" id="child-module-alphabet" onClick={() => navigate("/practice?module=alphabet_practice&difficulty=beginner")} />
            <ModuleCard emoji="📖" label="Words" description="Spell words" color="purple" id="child-module-words" onClick={() => navigate("/practice?module=word_practice&difficulty=beginner")} />
            <ModuleCard emoji="🎨" label="Free Draw" description="Old canvas" color="green" id="child-module-free" onClick={() => navigate("/practice?module=free_draw")} />
          </div>
        </div>

        {/* Phase 4: Insights CTA */}
        <button
          id="child-insights-cta"
          onClick={() => navigate("/insights")}
          className="w-full bg-indigo-50 rounded-2xl border border-indigo-200 p-4
            flex items-center gap-3 hover:bg-indigo-100 transition-colors"
        >
          <span className="text-2xl">📊</span>
          <div className="text-left">
            <p className="text-sm font-bold text-indigo-800">My Progress</p>
            <p className="text-xs text-indigo-400">See your strengths and what to improve</p>
          </div>
          <span className="ml-auto text-indigo-300 text-xl">›</span>
        </button>
      </main>
    </div>
  );
}

// ── Sub-component ─────────────────────────────────────────────────────────────

const colorMap: Record<string, { card: string; badge: string }> = {
  indigo: { card: "border-indigo-100 hover:border-indigo-300", badge: "bg-indigo-100 text-indigo-600" },
  purple: { card: "border-purple-100 hover:border-purple-300", badge: "bg-purple-100 text-purple-600" },
  blue: { card: "border-blue-100 hover:border-blue-300", badge: "bg-blue-100 text-blue-600" },
  green: { card: "border-green-100 hover:border-green-300", badge: "bg-green-100 text-green-600" },
};

function ModuleCard({
  emoji, label, description, color, id, onClick
}: {
  emoji: string; label: string; description: string;
  color: string; id: string; onClick?: () => void;
}) {
  const c = colorMap[color] ?? colorMap.indigo;
  return (
    <button id={id} onClick={onClick}
      className={`bg-white rounded-2xl border-2 ${c.card} p-4 text-left transition-all hover:shadow-md active:scale-95 space-y-2`}>
      <span className="text-3xl">{emoji}</span>
      <div>
        <p className="font-bold text-gray-800 text-sm">{label}</p>
        <p className="text-xs text-gray-500">{description}</p>
      </div>
    </button>
  );
}
