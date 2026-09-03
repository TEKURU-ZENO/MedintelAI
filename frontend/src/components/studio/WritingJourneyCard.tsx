/**
 * src/components/studio/WritingJourneyCard.tsx
 *
 * Dashboard card showing the learner's free writing progress trend.
 * Used in Dashboard shells (primary CTA area) and Insights page.
 * Shows sparkline + trend language + CTA to open Studio.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { studioApi, type JourneyResponse, type QualityBand, type Trend, type SparklinePoint } from "../../api/studio";
import type { ProfileType } from "../../utils/ageUtils";

interface Props {
  profileType: ProfileType;
}

const BAND_COLORS: Record<QualityBand, string> = {
  developing:  "bg-amber-400",
  building:    "bg-blue-400",
  strong:      "bg-indigo-500",
  exceptional: "bg-purple-500",
};

const TREND_LABEL: Record<Trend, { text: string; emoji: string; color: string }> = {
  improving:  { text: "improving",   emoji: "↑", color: "text-emerald-600" },
  stable:     { text: "steady",      emoji: "→", color: "text-gray-500"    },
  declining:  { text: "needs focus", emoji: "↓", color: "text-amber-600"   },
};

function Sparkline({ data }: { data: SparklinePoint[] }) {
  if (!data.length) return null;
  const max = Math.max(...data.map(d => d.score), 1);

  return (
    <div className="flex items-end gap-1 h-8">
      {data.map((pt, i) => (
        <div
          key={i}
          className={`flex-1 rounded-sm transition-all duration-500 ${BAND_COLORS[pt.band] ?? "bg-gray-200"}`}
          style={{
            height: `${Math.max(15, (pt.score / max) * 100)}%`,
            opacity: 0.7 + (i / data.length) * 0.3,
          }}
          title={`${pt.date}: ${pt.score}`}
        />
      ))}
    </div>
  );
}

export default function WritingJourneyCard({ profileType }: Props) {
  const navigate = useNavigate();
  const [journey, setJourney] = useState<JourneyResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    studioApi.journey()
      .then(res => setJourney(res.data))
      .catch(() => setJourney(null))
      .finally(() => setLoading(false));
  }, []);

  const isFirstSession = !loading && (!journey || journey.total_sessions === 0);

  const heading =
    profileType === "early_learner" ? "Your Writing Journey 🌈"
    : profileType === "child"       ? "Your Writing Journey"
    :                                  "Handwriting Development";

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800">{heading}</h2>
        {journey && journey.total_sessions > 0 && (
          <span className="text-xs text-gray-400">{journey.total_sessions} sessions</span>
        )}
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-2 animate-pulse">
          <div className="h-8 bg-gray-100 rounded-lg" />
          <div className="h-3 w-2/3 bg-gray-100 rounded" />
        </div>
      )}

      {/* First session — warm onboarding state */}
      {isFirstSession && (
        <div className="space-y-3">
          <div className="text-center py-4">
            <p className="text-3xl mb-2">✍️</p>
            <p className="text-sm text-gray-500">
              {profileType === "early_learner"
                ? "Start drawing to begin your journey! 🌟"
                : profileType === "child"
                ? "Your writing journey starts with your first session."
                : "Start a Free Writing session to begin tracking your handwriting quality."}
            </p>
          </div>
        </div>
      )}

      {/* Journey data */}
      {journey && journey.total_sessions > 0 && (
        <div className="space-y-3">
          {/* Sparkline */}
          {journey.sparkline.length > 0 && (
            <div className="space-y-1">
              <Sparkline data={journey.sparkline} />
              <div className="flex justify-between text-xs text-gray-300">
                <span>{journey.sparkline[0]?.date ?? ""}</span>
                <span>Today</span>
              </div>
            </div>
          )}

          {/* Trend statements */}
          {profileType !== "early_learner" && (
            <div className="space-y-1">
              {(["smoothness", "spacing"] as const).map((key) => {
                const trend = journey.trend[`${key}_trend` as keyof typeof journey.trend] as Trend;
                const tl = TREND_LABEL[trend];
                return (
                  <div key={key} className="flex items-center justify-between text-xs">
                    <span className="text-gray-400 capitalize">{key}</span>
                    <span className={`font-medium ${tl.color}`}>
                      {tl.emoji} {tl.text}
                    </span>
                  </div>
                );
              })}
              {journey.trend.consistency_growth !== 0 && (
                <div className="text-xs text-gray-400 pt-0.5">
                  {journey.trend.consistency_growth > 0
                    ? `↑ ${journey.trend.consistency_growth}% overall improvement`
                    : `${journey.trend.consistency_growth}% — keep at it`}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* CTA */}
      <button
        onClick={() => navigate("/studio")}
        className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white text-sm font-semibold rounded-xl transition-all duration-200 shadow-sm hover:shadow-md"
      >
        {isFirstSession
          ? profileType === "early_learner" ? "Start Drawing! 🎨" : "Open Writing Studio →"
          : profileType === "early_learner" ? "Write Again! ✍️" : "Write Today →"}
      </button>
    </div>
  );
}
