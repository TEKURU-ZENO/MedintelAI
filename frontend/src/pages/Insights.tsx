/**
 * Insights.tsx — Parent/Student Insights Dashboard (Phase 4)
 *
 * - Fetches all 5 analytics endpoints in parallel with Promise.allSettled
 * - Shows section-by-section loading skeletons
 * - Graceful per-section degradation (partial failure = partial data)
 * - Profile-aware section ordering
 * - Route: /insights (protected)
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { analyticsApi } from "../api/analytics";
import type {
  DashboardSummaryResponse,
  ProgressTrendResponse,
  EngagementMetricsResponse,
  LearningInsightResponse,
  ModulePerformanceResponse,
} from "../api/analytics";
import type { ProfileType } from "../utils/ageUtils";
import SummaryCard from "../components/insights/SummaryCard";
import ProgressSection from "../components/insights/ProgressSection";
import EngagementSection from "../components/insights/EngagementSection";
import InsightsList from "../components/insights/InsightsList";
import { ModuleGrid } from "../components/insights/ModuleGrid";
import RecommendationsCard from "../components/insights/RecommendationsCard";
import { recommendationsApi } from "../api/recommendations";
import type { FullRecommendationResponse } from "../api/recommendations";

// ──────────────────────────────────────────────────────────────────────────────

function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-2xl bg-white shadow-sm border border-gray-100 p-5 flex flex-col gap-3 animate-pulse">
      <div className="h-4 bg-gray-100 rounded w-2/5" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`h-3 bg-gray-100 rounded ${i === lines - 1 ? "w-3/4" : "w-full"}`} />
      ))}
    </div>
  );
}

function ErrorCard({ section }: { section: string }) {
  return (
    <div className="rounded-2xl bg-gray-50 border border-dashed border-gray-200 p-4 text-center">
      <p className="text-xs text-gray-400">
        Couldn't load {section}. Complete more practice sessions to see data here.
      </p>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────

export default function Insights() {
  const navigate = useNavigate();
  const { profileType: rawPt, themeMode, toggleTheme } = useAuth();
  const pt: ProfileType = rawPt ?? "adult";

  const [loading, setLoading]         = useState(true);
  const [summary,     setSummary]     = useState<DashboardSummaryResponse | null>(null);
  const [progress,    setProgress]    = useState<ProgressTrendResponse    | null>(null);
  const [engagement,  setEngagement]  = useState<EngagementMetricsResponse | null>(null);
  const [insights,    setInsights]    = useState<LearningInsightResponse  | null>(null);
  const [modules,     setModules]     = useState<ModulePerformanceResponse[] | null>(null);
  const [recommendations, setRecommendations] = useState<FullRecommendationResponse | null>(null);

  // Track per-section errors
  const [errs, setErrs] = useState({
    summary: false, progress: false, engagement: false,
    insights: false, modules: false, recommendations: false,
  });

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      analyticsApi.summary(),
      analyticsApi.progress(),
      analyticsApi.engagement(),
      analyticsApi.insights(),
      analyticsApi.modules(),
      recommendationsApi.full(),
    ]).then(([sumR, progR, engR, insR, modR, recR]) => {
      if (sumR.status  === "fulfilled") setSummary(sumR.value.data);
      else setErrs(e => ({ ...e, summary: true }));

      if (progR.status === "fulfilled") setProgress(progR.value.data);
      else setErrs(e => ({ ...e, progress: true }));

      if (engR.status  === "fulfilled") setEngagement(engR.value.data);
      else setErrs(e => ({ ...e, engagement: true }));

      if (insR.status  === "fulfilled") setInsights(insR.value.data);
      else setErrs(e => ({ ...e, insights: true }));

      if (modR.status  === "fulfilled") setModules(modR.value.data);
      else setErrs(e => ({ ...e, modules: true }));

      if (recR.status === "fulfilled") setRecommendations(recR.value.data);
      else setErrs(e => ({ ...e, recommendations: true }));
    }).finally(() => setLoading(false));
  }, []);

  const greeting =
    pt === "early_learner" ? `⭐ Great job practicing!`
    : pt === "child"        ? `📚 Here's your progress!`
    :                          `📊 Your Learning Insights`;

  return (
    <div className="min-h-screen bg-background flex flex-col transition-colors duration-300">
      {/* Nav */}
      <header className="flex items-center justify-between px-6 py-4 bg-surface border-b border-border transition-colors duration-300">
        <div className="max-w-5xl mx-auto w-full flex items-center justify-between">
          <button
            onClick={() => navigate("/dashboard")}
            className="text-sm text-textSecondary hover:text-textPrimary transition-colors font-medium flex items-center gap-1"
          >
            ← Back to Dashboard
          </button>
          
          <div className="flex items-center gap-4">
            <button
              onClick={toggleTheme}
              className="w-8 h-8 rounded-full flex items-center justify-center text-lg hover:bg-surface-hover transition-colors"
              title={themeMode === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
            >
              {themeMode === "light" ? "🌙" : "☀️"}
            </button>
            <span className="text-sm font-bold text-textPrimary">Learning Analytics</span>
          </div>
        </div>
      </header>

      <main className="flex-1 px-6 py-8 max-w-5xl mx-auto w-full space-y-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-3xl font-display font-bold text-textPrimary">{greeting}</h1>
          <p className="text-sm text-textSecondary mt-0.5">
            {pt === "adult"
              ? "Your behavioral analytics and learning intelligence."
              : "Keep practicing to see more insights here!"}
          </p>
        </div>

        {/* Dynamic Responsive Layout Grid */}
        {loading ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2"><SkeletonCard lines={4} /></div>
              <div><SkeletonCard lines={3} /></div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-7"><SkeletonCard lines={5} /></div>
              <div className="lg:col-span-5"><SkeletonCard lines={4} /></div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            
            {/* ROW 1: Summary (2/3) + Recommendations (1/3) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
              <div className="lg:col-span-2 flex flex-col">
                {summary ? <SummaryCard data={summary} profileType={pt} />
                  : errs.summary ? <ErrorCard section="summary" />
                  : null}
              </div>
              <div className="flex flex-col">
                {recommendations ? <RecommendationsCard data={recommendations} profileType={pt} />
                  : errs.recommendations ? <ErrorCard section="recommendations" />
                  : null}
              </div>
            </div>

            {/* ROW 2: Progress (7/12) + Engagement (5/12) */}
            {(progress || engagement) && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                {progress ? (
                  <>
                    <div className="lg:col-span-7 flex flex-col">
                      <ProgressSection data={progress} profileType={pt} />
                    </div>
                    {engagement && (
                      <div className="lg:col-span-5 flex flex-col">
                        <EngagementSection data={engagement} profileType={pt} />
                      </div>
                    )}
                  </>
                ) : (
                  engagement && (
                    <div className="lg:col-span-12 flex flex-col">
                      <EngagementSection data={engagement} profileType={pt} />
                    </div>
                  )
                )}
              </div>
            )}

            {/* ROW 3: Modules (1/2) + InsightsList (1/2) */}
            {(modules || insights) && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
                {modules ? (
                  <>
                    <div className="flex flex-col">
                      <ModuleGrid modules={modules} />
                    </div>
                    {insights && (
                      <div className="flex flex-col">
                        <InsightsList data={insights} profileType={pt} />
                      </div>
                    )}
                  </>
                ) : (
                  insights && (
                    <div className="lg:col-span-2 flex flex-col">
                      <InsightsList data={insights} profileType={pt} />
                    </div>
                  )
                )}
              </div>
            )}

          </div>
        )}
      </main>
    </div>
  );
}
