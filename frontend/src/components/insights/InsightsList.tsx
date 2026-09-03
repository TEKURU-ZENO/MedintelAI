/**
 * InsightsList.tsx — Structured intelligence: strengths / weaknesses / behavioral
 *
 * Consumes list[InsightItem] — severity drives icon + color.
 * Never renders raw strings — always uses InsightItem.severity for visual treatment.
 */

import type { InsightItem, LearningInsightResponse } from "../../api/analytics";
import type { ProfileType } from "../../utils/ageUtils";

interface Props {
  data:        LearningInsightResponse;
  profileType: ProfileType;
}

const SEVERITY_CONFIG = {
  positive: { icon: "✅", bg: "bg-green-50 dark:bg-green-950/25",  border: "border-green-100 dark:border-green-900/40", text: "text-green-700 dark:text-green-300"  },
  low:      { icon: "💡", bg: "bg-blue-50 dark:bg-blue-950/25",   border: "border-blue-100 dark:border-blue-900/40",  text: "text-blue-700 dark:text-blue-300"   },
  medium:   { icon: "⚠️", bg: "bg-amber-50 dark:bg-amber-950/25",  border: "border-amber-100 dark:border-amber-900/40", text: "text-amber-700 dark:text-amber-300"  },
  high:     { icon: "🔴", bg: "bg-red-50 dark:bg-red-950/25",    border: "border-red-100 dark:border-red-900/40",   text: "text-red-700 dark:text-red-300"    },
};

const CONFIDENCE_LABEL = {
  high:    { text: "High Confidence",   color: "text-green-600 dark:text-green-400" },
  medium:  { text: "Medium Confidence", color: "text-amber-600 dark:text-amber-400" },
  low:     { text: "Low Confidence",    color: "text-red-500 dark:text-red-400"   },
  unknown: { text: "Building profile…", color: "text-textTertiary"  },
};

function InsightRow({ item }: { item: InsightItem }) {
  const conf = SEVERITY_CONFIG[item.severity] || SEVERITY_CONFIG.low;
  return (
    <div className={`flex items-start gap-2.5 rounded-xl px-3 py-2.5
      border ${conf.bg} ${conf.border}`}>
      <span className="text-sm mt-0.5 shrink-0">{conf.icon}</span>
      <span className={`text-xs leading-relaxed font-medium ${conf.text}`}>{item.message}</span>
    </div>
  );
}

function Section({
  title,
  items,
  emptyText,
}: {
  title:     string;
  items:     InsightItem[];
  emptyText: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-xs uppercase tracking-wider text-textSecondary font-bold">{title}</h4>
      {items.length === 0 ? (
        <p className="text-xs text-textTertiary italic px-1">{emptyText}</p>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((item, i) => <InsightRow key={`${item.code}-${i}`} item={item} />)}
        </div>
      )}
    </div>
  );
}

export default function InsightsList({ data, profileType }: Props) {
  const isEarly = profileType === "early_learner";
  const conf = CONFIDENCE_LABEL[data.confidence_level] || CONFIDENCE_LABEL.unknown;

  return (
    <div className="rounded-3xl bg-surface shadow-sm border border-border p-6 flex flex-col gap-5 transition-all duration-300">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-textPrimary text-sm">
          {isEarly ? "⭐ My Learning" : "Learning Insights"}
        </h3>
        <span className={`text-xs font-bold ${conf.color}`}>{conf.text}</span>
      </div>

      {data.confidence_level === "unknown" && (
        <div className="rounded-2xl bg-indigoLight border border-indigo/25 px-4 py-3 text-xs text-indigo font-medium">
          💡 Complete a few guided practice sessions to unlock behavioral insights.
        </div>
      )}

      <Section
        title="✅ Strengths"
        items={data.strengths}
        emptyText="Keep practicing to discover your strengths!"
      />
      <Section
        title="⚠️ Areas to improve"
        items={data.weaknesses}
        emptyText="No major weaknesses detected yet."
      />
      <Section
        title="💡 Observations"
        items={data.behavioral}
        emptyText="More sessions needed to detect behavioral patterns."
      />
    </div>
  );
}
