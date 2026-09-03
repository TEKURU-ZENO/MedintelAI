/**
 * EarlyLearnerShell.tsx — Profile shell for ages 2–5
 *
 * Design intent: cartoon/gamified, giant tap targets, joyful colors,
 * minimal text. Content is filled in by Phase 2 module system.
 */
import { useAuth } from "../../auth/AuthContext";
import { useNavigate } from "react-router-dom";

export default function EarlyLearnerShell() {
  const { user, logout, themeMode, toggleTheme } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-b from-yellow-100 via-pink-50 to-purple-100">
      {/* Top Bar */}
      <header className="flex items-center justify-between px-6 py-4 bg-white/70 backdrop-blur-sm border-b border-pink-100">
        <div className="flex items-center gap-3">
          <span className="text-3xl">✍️</span>
          <div>
            <p className="text-xs text-gray-500 font-medium">Hello!</p>
            <p className="text-lg font-bold text-purple-700">
              {user?.full_name?.split(" ")[0] ?? "Friend"} 👋
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Streak badge */}
          <div className="flex items-center gap-1 bg-orange-100 rounded-full px-3 py-1">
            <span className="text-lg">🔥</span>
            <span className="font-bold text-orange-600 text-sm">
              {user?.user_streak ?? 0}
            </span>
          </div>
          <button
            id="early-nav-insights"
            onClick={() => navigate("/insights")}
            className="text-2xl hover:scale-110 transition-transform"
            title="My Stars"
          >
            🌟
          </button>
          <button
            onClick={toggleTheme}
            className="w-8 h-8 rounded-full flex items-center justify-center text-lg hover:bg-surface-hover transition-colors"
            title={themeMode === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
          >
            {themeMode === "light" ? "🌙" : "☀️"}
          </button>
          <button
            onClick={logout}
            className="text-xs text-gray-400 hover:text-red-500 transition-colors"
          >
            Exit
          </button>
        </div>
      </header>

      {/* Stars / Level */}
      <div className="flex justify-center gap-2 mt-6">
        {Array.from({ length: Math.min(user?.level ?? 1, 5) }).map((_, i) => (
          <span key={i} className="text-3xl">⭐</span>
        ))}
      </div>

      {/* Main Content Area */}
      <main className="px-4 py-6 max-w-lg mx-auto space-y-5">
        {/* ── PRIMARY: Writing Studio ────────────────────────────────────── */}
        <button
          id="early-studio-cta"
          onClick={() => navigate("/studio")}
          className="w-full bg-gradient-to-r from-indigo-400 to-violet-500 rounded-3xl p-5
            flex items-center gap-4 shadow-lg active:scale-95 transition-transform"
        >
          <span className="text-5xl">✍️</span>
          <div className="text-left">
            <p className="font-extrabold text-white text-xl">Let's Draw!</p>
            <p className="text-white/80 text-sm">Free writing — anything you like 🎨</p>
          </div>
        </button>

        {/* ── SECONDARY: Guided Practice ───────────────────────────────── */}
        <p className="text-center text-xs text-gray-400 font-medium uppercase tracking-wide">Guided exercises</p>
        <div className="grid grid-cols-2 gap-4">
          <ModuleCard
            emoji="🔤"
            label="Letters"
            color="from-pink-400 to-rose-400"
            id="module-alphabet"
            onClick={() => navigate("/practice?module=alphabet_practice&difficulty=beginner")}
          />
          <ModuleCard
            emoji="📝"
            label="Words"
            color="from-purple-400 to-indigo-400"
            id="module-words"
            onClick={() => navigate("/practice?module=word_practice&difficulty=beginner")}
          />
        </div>

        {/* ── TERTIARY: Insights ───────────────────────────────────────── */}
        <button
          id="early-insights-cta"
          onClick={() => navigate("/insights")}
          className="w-full bg-gradient-to-r from-yellow-300 to-pink-300 rounded-3xl p-5
            flex items-center gap-4 shadow-md active:scale-95 transition-transform"
        >
          <span className="text-4xl">🌟</span>
          <div className="text-left">
            <p className="font-extrabold text-white text-lg">My Stars!</p>
            <p className="text-white/80 text-xs">See how great you're doing!</p>
          </div>
        </button>
      </main>
    </div>
  );
}

// ── Sub-component ─────────────────────────────────────────────────────────────

function ModuleCard({
  emoji,
  label,
  color,
  id,
  onClick,
}: {
  emoji: string;
  label: string;
  color: string;
  id: string;
  onClick?: () => void;
}) {
  return (
    <button
      id={id}
      onClick={onClick}
      className={`bg-gradient-to-br ${color} rounded-3xl p-6 flex flex-col items-center gap-3 shadow-lg active:scale-95 transition-transform`}
    >
      <span className="text-5xl">{emoji}</span>
      <span className="text-white font-extrabold text-lg">{label}</span>
    </button>
  );
}
