/**
 * AlphabetModule.tsx — Phase 3 upgrade
 *
 * Wired to useGuidanceEngine for:
 *   - Per-stroke scoring (backend authoritative + local instant)
 *   - Stroke locking (can't proceed until current stroke passes)
 *   - Failsafe unlock after MAX_ATTEMPTS
 *   - Coaching state display (FeedbackPanel driven by coachingState)
 *   - Ghost replay (GhostReplay driven by replayLevel)
 *   - Live trace % overlay on canvas
 *   - Adaptive difficulty fetch before session start
 */
import { useState, useEffect } from "react";
import PracticeCanvas from "../shared/PracticeCanvas";
import FeedbackPanel from "../shared/FeedbackPanel";
import GhostReplay from "../shared/GhostReplay";
import { sessionsApi, type StrokeData } from "../../api/sessions";
import { useGuidanceEngine } from "../../hooks/useGuidanceEngine";
import { useRef } from "react";
import type { ProfileType } from "../../utils/ageUtils";
import { audioPlayer } from "../../utils/audioPlayer";
import { coachingEngine } from "../../utils/coachingEngine";

interface Props {
  sessionId:   number;
  targetItem:  string;
  profileType: ProfileType;
  audioMetadata?: any;
  onComplete:  (strokes: StrokeData[], accuracy: number) => void;
  onCancel:    () => void;
  width?:      number;
  height?:     number;
}

export default function AlphabetModule({
  sessionId,
  targetItem,
  profileType,
  audioMetadata,
  onComplete,
  onCancel,
  width = 500,
  height = 500,
}: Props) {
  const [letterData, setLetterData] = useState<any>(null);
  const [loading, setLoading]       = useState(true);
  const allStrokes = useRef<StrokeData[]>([]);

  useEffect(() => {
    setLoading(true);
    sessionsApi
      .itemData("alphabet_practice", targetItem)
      .then((res) => setLetterData(res.data))
      .finally(() => setLoading(false));
  }, [targetItem]);

  // Handle initial audio playback
  useEffect(() => {
    if (!loading && audioMetadata) {
      coachingEngine.handleEvent("session_start", audioMetadata);
      if (audioMetadata.profile?.autoplay) {
        const audioUrl = audioMetadata.item_audio?.[targetItem];
        if (audioUrl) {
          audioPlayer.play(audioUrl);
        }
      }
    }
  }, [loading, targetItem, audioMetadata]);

  const handleListen = () => {
    const audioUrl = audioMetadata?.item_audio?.[targetItem];
    if (audioUrl) {
      audioPlayer.play(audioUrl);
    }
  };

  // ── Guidance Engine ────────────────────────────────────────────────────────
  const {
    state: guidance,
    replayLevel,
    dismissReplay,
    handleStrokeComplete,
    handleStrokeStart: _handleStrokeStart,
    resetGuidance: _resetGuidance
  } = useGuidanceEngine({
    sessionId,
    moduleType:      "alphabet_practice",
    targetItem,
    referenceStrokes: letterData?.strokes ?? [],
    isDrawing:        false,  // updated below
    profileType,
    onAllStrokesDone: () => {
      // All strokes done → compute overall accuracy from stroke results
      if (guidance.strokeResults.length === 0) return;
      const avg = guidance.strokeResults.reduce((s, r) => s + r.combinedScore, 0)
                  / guidance.strokeResults.length;
      onComplete(allStrokes.current, avg);
    },
    onCoachingEvent: (eventName: string) => {
      coachingEngine.handleEvent(eventName, audioMetadata);
    }
  });

  // Get paths for the current active stroke
  const activeStroke = letterData?.strokes?.find(
    (s: any) => s.id === guidance.currentStrokeId
  );
  const activeStrokePath = activeStroke?.path ?? null;
  const startPoint: [number, number] | undefined =
    activeStroke?.start_point ?? undefined;

  // Submit manually (if auto-detect of all-strokes-done doesn't fire)
  const handleManualSubmit = () => {
    if (allStrokes.current.length === 0) return;
    const avg = guidance.strokeResults.length > 0
      ? guidance.strokeResults.reduce((s, r) => s + r.combinedScore, 0)
        / guidance.strokeResults.length
      : 0.5;
    onComplete(allStrokes.current, avg);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400 text-sm animate-pulse">Loading letter data…</div>
      </div>
    );
  }

  const letterColor =
    profileType === "early_learner" ? "text-purple-700"
    : profileType === "child"       ? "text-indigo-700"
    :                                  "text-gray-800";

  const letterSize =
    profileType === "early_learner" ? "text-8xl"
    : profileType === "child"       ? "text-7xl"
    :                                  "text-5xl";

  const totalStrokes = letterData?.strokes?.length ?? 1;

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Target letter + stroke progress */}
      <div className="text-center relative">
        <p className="text-xs uppercase tracking-widest text-gray-400 font-semibold mb-1">
          Trace this letter
        </p>
        <div className="flex items-center justify-center gap-4">
          <span className={`font-black ${letterSize} ${letterColor} leading-none`}>
            {targetItem}
          </span>
          {audioMetadata?.item_audio?.[targetItem] && (
            <button 
              onClick={handleListen}
              className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 hover:bg-indigo-100 flex items-center justify-center text-xl transition-colors shadow-sm"
              title="Listen to pronunciation"
            >
              🔊
            </button>
          )}
        </div>
        {/* Stroke progress dots */}
        {totalStrokes > 1 && (
          <div className="flex items-center justify-center gap-2 mt-2">
            {Array.from({ length: totalStrokes }).map((_, i) => {
              const strokeId = i + 1;
              const done   = guidance.completedStrokes.includes(strokeId);
              const active = guidance.currentStrokeId === strokeId;
              return (
                <div
                  key={strokeId}
                  className={`rounded-full transition-all duration-300 ${
                    done    ? "w-4 h-4 bg-green-500"
                    : active ? "w-4 h-4 bg-indigo-500 ring-2 ring-indigo-300"
                    :          "w-3 h-3 bg-gray-200"
                  }`}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Canvas with ghost replay overlay */}
      <div className="relative">
        <PracticeCanvas
          key={targetItem}
          onStrokeEnd={handleStrokeComplete}
          onStrokesChange={(s) => { allStrokes.current = s; }}
          svgGuidePath={letterData?.svg_path}
          activeStrokePath={activeStrokePath}
          startPoint={startPoint}
          completedStrokes={guidance.completedStrokes}
          tracePercent={guidance.tracePercent}
          profileType={profileType}
          disabled={guidance.isSubmitting}
          width={width}
          height={height}
        />
        {/* Ghost replay overlay */}
        {replayLevel > 0 && activeStrokePath && (
          <div className="absolute inset-0">
            <GhostReplay
              svgPath={activeStrokePath}
              level={replayLevel}
              onDismiss={dismissReplay}
            />
          </div>
        )}
      </div>

      {/* Feedback panel — driven by coaching state */}
      <FeedbackPanel
        message={guidance.feedbackMessage}
        feedbackType={guidance.feedbackType}
        profileType={profileType}
        visible={true}
      />

      {/* Stroke hint text */}
      {activeStroke?.hint && guidance.coachingState !== "celebrating" && (
        <p className="text-xs text-gray-400 text-center max-w-xs">
          💡 {activeStroke.hint}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-3 w-full max-w-xs">
        <button
          onClick={onCancel}
          className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          onClick={handleManualSubmit}
          disabled={allStrokes.current.length === 0 || guidance.isSubmitting}
          className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-200
                     text-white rounded-xl text-sm font-semibold transition-colors"
        >
          {guidance.coachingState === "celebrating" ? "🎉 Done!" : "Submit ✓"}
        </button>
      </div>
    </div>
  );
}
