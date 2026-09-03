/**
 * Showcase.tsx — Premium Showcase Mode
 *
 * A deterministic, unauthenticated showcase view designed for client demos.
 * Pre-filled with beautiful progress, completed skills, and a mock recommendation.
 */
import { useNavigate } from "react-router-dom";
import RecommendationsCard from "../components/insights/RecommendationsCard";

export default function Showcase() {
  const navigate = useNavigate();

  const dummyRecData = {
    user_id: 1,
    profile_type: "child",
    learning_style: "visual",
    style_label: "Visual Learner",
    session_plan: {
      items: ["APPLE", "BANANA"],
      difficulty: "intermediate",
      focus_mode: "confidence_boost",
      session_length_s: 300,
      reasoning: "You've been tracing letters wonderfully. Let's combine them into common sight words to boost your confidence.",
      audio_metadata: null
    },
    recommended_items: [
      { item: "APPLE", priority: "high", reason: "Ready for double letters" },
      { item: "BANANA", priority: "medium", reason: "Good pattern practice" },
      { item: "S", priority: "low", reason: "Review curved strokes" }
    ]
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* Header */}
      <header className="pt-8 px-8 mb-12">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-full flex items-center justify-center text-white font-bold text-xl shadow-glowIndigo">
                S
            </div>
            <span className="font-display font-bold text-textPrimary text-xl tracking-tight">Aksharabyasa</span>
            <span className="ml-2 px-2 py-0.5 bg-indigoLight text-indigo text-xs font-bold rounded-md uppercase tracking-wider">Showcase Mode</span>
          </div>
          <button
            onClick={() => navigate("/")}
            className="text-sm text-textTertiary hover:text-textPrimary transition-colors"
          >
            Exit Showcase
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 space-y-16">
        
        {/* Welcome */}
        <section className="text-center max-w-2xl mx-auto space-y-4">
            <h1 className="text-5xl font-display font-bold text-textPrimary leading-tight">
                Watch literacy unfold, <br/> stroke by stroke.
            </h1>
            <p className="text-lg text-textSecondary font-medium leading-relaxed">
                This is a simulated journey. In production, this progression is generated entirely autonomously by the Learning Journey Engine based on live telemetry.
            </p>
        </section>

        {/* Milestone Pin */}
        <section className="max-w-3xl mx-auto">
            {/* @ts-ignore */}
            <RecommendationsCard data={dummyRecData} profileType="child" />
        </section>

        {/* Curriculum Graph Visualization (Mock) */}
        <section>
            <h2 className="text-2xl font-display font-bold text-textPrimary mb-8 text-center">Curriculum Graph</h2>
            
            <div className="flex flex-col items-center gap-8 relative">
                {/* Connecting Lines (CSS trick) */}
                <div className="absolute top-12 bottom-12 w-1 bg-indigoLight -z-10" />

                {/* Node 1 */}
                <div className="flex flex-col items-center group">
                    <div className="w-16 h-16 bg-success rounded-full flex items-center justify-center text-white text-2xl shadow-glowSage z-10 transition-transform duration-400 spring group-hover:scale-110">
                        ✓
                    </div>
                    <div className="bg-surface shadow-sm rounded-2xl px-6 py-4 mt-4 text-center border border-gray-100 hover:shadow-md transition-shadow">
                        <p className="font-display font-bold text-textPrimary">Straight Lines</p>
                        <p className="text-xs text-textSecondary font-medium">100% Mastery</p>
                    </div>
                </div>

                {/* Node 2 */}
                <div className="flex flex-col items-center group">
                    <div className="w-16 h-16 bg-success rounded-full flex items-center justify-center text-white text-2xl shadow-glowSage z-10 transition-transform duration-400 spring group-hover:scale-110">
                        ✓
                    </div>
                    <div className="bg-surface shadow-sm rounded-2xl px-6 py-4 mt-4 text-center border border-gray-100 hover:shadow-md transition-shadow">
                        <p className="font-display font-bold text-textPrimary">Angular Capitals</p>
                        <p className="text-xs text-textSecondary font-medium">85% Mastery</p>
                    </div>
                </div>

                {/* Node 3 (Active) */}
                <div className="flex flex-col items-center group">
                    <div className="w-16 h-16 bg-surface border-4 border-indigo text-indigo rounded-full flex items-center justify-center text-2xl shadow-glowIndigo z-10 transition-transform duration-400 spring group-hover:scale-110">
                        ✍️
                    </div>
                    <div className="bg-indigo text-white shadow-md rounded-2xl px-8 py-5 mt-4 text-center hover:shadow-lg transition-all duration-250 hover:-translate-y-1 cursor-pointer" onClick={() => navigate("/practice?module=word_practice")}>
                        <p className="font-display font-bold text-lg">CVC Words</p>
                        <p className="text-xs text-indigoLight font-medium mt-1">Current Focus • 40% Mastery</p>
                    </div>
                </div>

                {/* Node 4 (Locked) */}
                <div className="flex flex-col items-center group opacity-50 grayscale">
                    <div className="w-16 h-16 bg-surface border-4 border-gray-200 text-gray-400 rounded-full flex items-center justify-center text-2xl z-10">
                        🔒
                    </div>
                    <div className="bg-surface shadow-sm rounded-2xl px-6 py-4 mt-4 text-center border border-gray-100">
                        <p className="font-display font-bold text-textPrimary">Complex Words</p>
                        <p className="text-xs text-textSecondary font-medium">Requires CVC Mastery</p>
                    </div>
                </div>
            </div>
        </section>
      </main>
    </div>
  );
}
