/**
 * EmptyJourneyState.tsx — Ambient Empty State
 * 
 * Used when a user has no telemetry/progress yet.
 * Replaces generic "No data" with a warm, encouraging welcome.
 */

export default function EmptyJourneyState({ title = "Your journey begins here ✨", subtitle = "Take your first step. Let's trace your first letter together." }: { title?: string; subtitle?: string }) {
  return (
    <div className="w-full flex flex-col items-center justify-center py-20 px-6 text-center bg-surface rounded-3xl shadow-sm border border-gray-100 relative overflow-hidden group">
        
      {/* Ambient background doodles (SVG blobs) */}
      <div className="absolute top-[-20%] left-[-10%] w-64 h-64 bg-sage/10 rounded-full blur-3xl group-hover:scale-110 transition-transform duration-700 ease-out" />
      <div className="absolute bottom-[-20%] right-[-10%] w-64 h-64 bg-indigoLight rounded-full blur-3xl group-hover:scale-110 transition-transform duration-700 ease-out" />

      {/* Floating Center Icon */}
      <div className="w-20 h-20 bg-indigo/5 rounded-3xl flex items-center justify-center text-4xl shadow-sm mb-6 animate-[bounce_3s_ease-in-out_infinite] z-10">
          🌱
      </div>

      <h3 className="text-2xl font-display font-bold text-textPrimary z-10">
        {title}
      </h3>
      <p className="text-sm text-textSecondary font-medium mt-2 max-w-sm mx-auto z-10">
        {subtitle}
      </p>

    </div>
  );
}
