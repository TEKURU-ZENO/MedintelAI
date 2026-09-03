import { recommendationsApi } from "../../api/recommendations";
import type { FullRecommendationResponse } from "../../api/recommendations";
import type { ProfileType } from "../../utils/ageUtils";
import { useNavigate } from "react-router-dom";

interface Props {
  data: FullRecommendationResponse;
  profileType: ProfileType;
}

const PRIORITY_CONFIG = {
  high:   { icon: "✨", bg: "bg-coral/10 dark:bg-coral/20",   text: "text-coral",   border: "border-coral/20" },
  medium: { icon: "📈", bg: "bg-sunflower/10 dark:bg-sunflower/20", text: "text-yellow-600 dark:text-sunflower", border: "border-sunflower/20" },
  low:    { icon: "💡", bg: "bg-skyBlue/10 dark:bg-skyBlue/20",  text: "text-skyBlue",  border: "border-skyBlue/20" },
};

const MODE_LABELS = {
  standard: "Standard Journey",
  deep_focus: "Deep Mastery",
  confidence_boost: "Confidence Boost",
  quick_win: "Quick Win",
};

export default function RecommendationsCard({ data, profileType }: Props) {
  const navigate = useNavigate();
  const isEarly = profileType === "early_learner";

  const handleStartSession = () => {
    // Fire feedback asynchronously (fire and forget)
    if (data.recommended_items.length > 0) {
      recommendationsApi.feedback({
        item: data.recommended_items[0].item,
        action: "accepted"
      }).catch(() => {}); // silent catch
    }
    navigate("/practice?module=alphabet_practice&use_plan=true");
  };

  if (data.recommended_items.length === 0) {
    return null;
  }

  return (
    <div className="rounded-3xl bg-surface shadow-sm hover:shadow-md transition-all duration-400 ease-out p-6 flex flex-col gap-6 relative overflow-hidden group border border-border">
      
      {/* Decorative background element */}
      <div className="absolute -top-12 -right-12 w-48 h-48 bg-indigoLight rounded-full blur-3xl opacity-50 -z-10 group-hover:bg-indigo/10 transition-colors duration-700" />

      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-indigo/10 dark:bg-indigo/20 flex items-center justify-center text-xl">
              🎯
          </div>
          <h3 className="font-display font-bold text-textPrimary text-xl tracking-tight">
            {isEarly ? "What to practice next" : "Your Next Milestone"}
          </h3>
        </div>
        <p className="text-xs text-textSecondary font-medium leading-relaxed max-w-sm">
          {data.session_plan.reasoning}
        </p>
      </div>

      {/* Pins Grid (Masonry Inspired) */}
      <div className="flex flex-wrap gap-2.5">
        {data.recommended_items.map((item, i) => {
          const conf = PRIORITY_CONFIG[item.priority] || PRIORITY_CONFIG.low;
          return (
            <div 
                key={`${item.item}-${i}`} 
                className={`flex items-center gap-3 rounded-2xl px-4 py-2.5 ${conf.bg} border ${conf.border} transition-all duration-250 ease-out hover:-translate-y-0.5 hover:shadow-sm`}
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                    <span className={`text-lg font-display font-black ${conf.text}`}>{item.item}</span>
                    <span className="text-xs">{conf.icon}</span>
                </div>
                <span className="text-[10px] text-textSecondary font-semibold mt-0.5 max-w-[120px] truncate">{item.reason}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Area */}
      <div className="mt-2 flex items-center justify-between border-t border-border/50 pt-4">
        <div className="flex flex-col">
            <span className="text-[10px] font-bold text-textTertiary uppercase tracking-widest">
            {MODE_LABELS[data.session_plan.focus_mode as keyof typeof MODE_LABELS] || "Practice Session"}
            </span>
            <span className="text-sm font-semibold text-textPrimary mt-0.5">
            {Math.round(data.session_plan.session_length_s / 60)} min session
            </span>
        </div>
        
        <button
          onClick={handleStartSession}
          className="bg-indigo text-white font-semibold rounded-2xl px-5 py-2.5 text-xs hover:bg-indigoHover transition-all duration-250 shadow-glowIndigo hover:scale-105 active:scale-95"
        >
          Start Journey →
        </button>
      </div>
    </div>
  );
}
