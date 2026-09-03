/**
 * AdultShell.tsx — Profile shell for ages 16+
 *
 * Design intent: Pinterest-style minimalist learning dashboard.
 * Heavy border radii, floating shadows, focus on elegant discovery.
 */
import { useAuth } from "../../auth/AuthContext";
import { useNavigate } from "react-router-dom";

export default function AdultShell() {
  const { user, logout, themeMode, toggleTheme } = useAuth();
  const navigate = useNavigate();

  const firstName = user?.full_name?.split(" ")[0] ?? "Learner";
  const streak = user?.user_streak ?? 0;
  const level = user?.level ?? 1;
  const xp = user?.xp_points ?? 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <header className="pt-8 px-8">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center text-white font-bold text-xl shadow-glowIndigo">
                A
            </div>
            <span className="font-display font-bold text-textPrimary text-xl tracking-tight">Aksharabyasa</span>
          </div>
          <div className="flex items-center gap-6">
            <button
              onClick={() => navigate("/insights")}
              className="text-sm text-textSecondary hover:text-indigo font-medium transition-all duration-250 ease-out hover:-translate-y-0.5"
            >
              Analytics
            </button>
            <button
              onClick={() => navigate("/showcase")}
              className="text-sm text-textSecondary hover:text-coral font-medium transition-all duration-250 ease-out hover:-translate-y-0.5"
            >
              Showcase
            </button>
            <div className="h-4 w-[1px] bg-border" />
            <button
              onClick={toggleTheme}
              className="w-8 h-8 rounded-full flex items-center justify-center text-lg hover:bg-surface-hover transition-colors"
              title={themeMode === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
            >
              {themeMode === "light" ? "🌙" : "☀️"}
            </button>
            <div className="h-4 w-[1px] bg-border" />
            <button
              onClick={logout}
              className="text-sm text-textTertiary hover:text-textPrimary transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-12 space-y-12">
        {/* Welcome Section */}
        <div className="space-y-2">
            <h1 className="text-4xl font-display font-bold text-textPrimary">
                Welcome back, {firstName}.
            </h1>
            <p className="text-textSecondary font-medium">Ready to continue your learning journey?</p>
        </div>

        {/* Stats Row - Masonry Inspired Pins */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StatCard label="Current Streak" value={`${streak} days`} icon="🔥" color="bg-coral/10 text-coral" />
          <StatCard label="Mastery Level" value={`Level ${level}`} icon="📈" color="bg-sage/10 text-success" />
          <StatCard label="Total Experience" value={xp.toLocaleString()} icon="⭐" color="bg-sunflower/20 text-yellow-600" />
        </div>

        {/* ── PRIMARY: Writing Studio Hero ─────────────────────────────── */}
        <button
          id="adult-studio-cta"
          onClick={() => navigate("/studio")}
          className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 rounded-3xl p-8
            flex items-center justify-between group transition-all duration-400 ease-out hover:-translate-y-1 shadow-lg hover:shadow-xl"
        >
          <div className="flex items-center gap-6">
            <div className="w-16 h-16 rounded-2xl bg-white/20 flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-300">
              ✍️
            </div>
            <div className="text-left">
              <p className="text-xl font-display font-bold text-white">Open Writing Studio</p>
              <p className="text-white/75 text-sm mt-1">Write freely. We analyze quality, not correctness.</p>
            </div>
          </div>
          <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-white text-xl group-hover:bg-white/30 transition-colors">
            ›
          </div>
        </button>

        {/* ── SECONDARY: Guided Practice ───────────────────────────────── */}
        <div>
          <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-display font-bold text-textPrimary">Guided Practice</h2>
              <span className="text-xs text-gray-400 font-medium">Optional structured exercises</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <ModulePin
                icon="🔤"
                label="Alphabet Tracing"
                description="Perfect individual character strokes"
                onClick={() => navigate("/practice?module=alphabet_practice&difficulty=intermediate")}
                color="bg-skyBlue/10"
            />
            <ModulePin
                icon="📖"
                label="Spelling Practice"
                description="Write and analyze whole words"
                onClick={() => navigate("/practice?module=word_practice&difficulty=intermediate")}
                color="bg-lavender/10"
            />
            <ModulePin
                icon="🎨"
                label="Free Canvas"
                description="Unconstrained open practice"
                onClick={() => navigate("/practice?module=free_draw")}
                color="bg-indigoLight"
            />
          </div>
        </div>

        {/* Insights Pin */}
        <button
          onClick={() => navigate("/insights")}
          className="w-full bg-surface rounded-3xl shadow-sm hover:shadow-md p-8
            flex items-center justify-between group transition-all duration-400 ease-out hover:-translate-y-1"
        >
          <div className="flex items-center gap-6">
            <div className="w-16 h-16 rounded-2xl bg-indigoLight flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-400 spring">
                📊
            </div>
            <div className="text-left">
              <p className="text-lg font-display font-bold text-textPrimary">View Your Learning Progress</p>
              <p className="text-sm text-textSecondary mt-1">Reflect on your strengths, weaknesses, and behavioral patterns.</p>
            </div>
          </div>
          <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center group-hover:bg-indigo group-hover:text-white transition-colors duration-250">
            <span className="text-xl">›</span>
          </div>
        </button>
      </main>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, icon, color }: { label: string; value: string; icon: string; color: string }) {
  return (
    <div className="bg-surface rounded-3xl shadow-xs p-6 flex flex-col gap-4 hover:shadow-sm transition-all duration-250 ease-out hover:-translate-y-1">
      <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-2xl ${color}`}>
          {icon}
      </div>
      <div>
        <p className="text-3xl font-display font-bold text-textPrimary">{value}</p>
        <p className="text-sm text-textSecondary font-medium mt-1">{label}</p>
      </div>
    </div>
  );
}

function ModulePin({ icon, label, description, onClick, color }: { icon: string; label: string; description: string; onClick?: () => void; color: string }) {
  return (
    <button 
      onClick={onClick}
      className="bg-surface rounded-3xl shadow-sm hover:shadow-md p-6 flex flex-col gap-4 transition-all duration-400 ease-out hover:-translate-y-2 text-left group"
    >
      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-3xl ${color} group-hover:scale-110 transition-transform duration-400 spring`}>
          {icon}
      </div>
      <div>
        <p className="font-display font-bold text-textPrimary text-lg">{label}</p>
        <p className="text-sm text-textSecondary mt-1 line-clamp-2 leading-relaxed">{description}</p>
      </div>
      <div className="mt-auto pt-4 flex items-center text-indigo text-sm font-semibold opacity-0 group-hover:opacity-100 transition-opacity duration-250">
          Start Session <span className="ml-1 group-hover:translate-x-1 transition-transform">→</span>
      </div>
    </button>
  );
}
