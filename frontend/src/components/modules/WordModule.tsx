/**
 * WordModule.tsx — Phase 6.3 Spelling MVP
 *
 * Implements the full Literacy Workflow:
 * Hear word → Understand sound → Trace letter → Micro-feedback → Complete word → Celebrate
 */
import { useState, useEffect, useRef } from "react";
import PracticeCanvas from "../shared/PracticeCanvas";
import FeedbackPanel from "../shared/FeedbackPanel";
import { sessionsApi, type StrokeData } from "../../api/sessions";
import { spellingApi, type LiteracySessionConfig, type SpellingProgressionState } from "../../api/spelling";
import type { ProfileType } from "../../utils/ageUtils";
import { useGuidanceEngine } from "../../hooks/useGuidanceEngine";
import { audioPlayer } from "../../utils/audioPlayer";
// import { coachingEngine } from "../../utils/coachingEngine";

interface Props {
  sessionId: number;
  targetItem: string;
  difficulty: string;
  profileType: ProfileType;
  onComplete: (strokes: StrokeData[], accuracy: number) => void;
  onCancel: () => void;
  width?: number;
  height?: number;
}

export default function WordModule({
  sessionId,
  targetItem,
  profileType,
  onComplete,
  onCancel,
  width = 500,
  height = 500,
}: Props) {
  const [config, setConfig] = useState<LiteracySessionConfig | null>(null);
  const [spellingState, setSpellingState] = useState<SpellingProgressionState>({
    target: targetItem.toUpperCase(),
    progress: [],
    next_expected: targetItem[0].toUpperCase(),
    state: "idle",
    accuracy: 0,
    attempts_on_current: 0,
  });

  const [activeLetterData, setActiveLetterData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  
  const allStrokes = useRef<StrokeData[]>([]);
  const combinedStrokes = useRef<StrokeData[]>([]); // all strokes for the whole word

  // 1. Fetch Orchestration Config
  useEffect(() => {
    spellingApi.getConfig(targetItem, "visual", profileType)
      .then(res => {
        setConfig(res.data);
        // Preload audio
        const { pronunciations, coach_audio } = res.data.audio;
        const urls = [
          pronunciations.word,
          ...Object.values(pronunciations.letters),
          ...Object.values(coach_audio)
        ];
        audioPlayer.preload(urls);

        // Auto-play the word pronunciation
        if (res.data.assist_profile.auto_repeat_pronunciation || profileType === "early_learner") {
          setTimeout(() => audioPlayer.play(pronunciations.word), 500);
        }
      })
      .catch(console.error);
  }, [targetItem, profileType]);

  // 2. Fetch Active Letter Data for Tracing
  useEffect(() => {
    if (!spellingState.next_expected) return;
    setLoading(true);
    sessionsApi.itemData("alphabet_practice", spellingState.next_expected)
      .then(res => setActiveLetterData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [spellingState.next_expected]);

  // 3. Guidance Engine for the Active Letter
  const {
    state: guidance,
    handleStrokeComplete,
    handleStrokeStart: _handleStrokeStart,
    resetGuidance
  } = useGuidanceEngine({
    sessionId,
    moduleType: "alphabet_practice",
    targetItem: spellingState.next_expected || "A",
    referenceStrokes: activeLetterData?.strokes ?? [],
    isDrawing: false,
    profileType,
    onAllStrokesDone: async () => {
      // Letter completed! Validate attempt.
      if (!spellingState.next_expected) return;
      
      try {
        const res = await spellingApi.validateAttempt(
          targetItem, 
          spellingState.progress, 
          spellingState.next_expected
        );
        const newState = res.data;
        
        // Save strokes
        combinedStrokes.current = [...combinedStrokes.current, ...allStrokes.current];
        allStrokes.current = [];
        resetGuidance();

        // Micro-celebration
        if (newState.state === "partial_success" && config?.audio.coach_audio.celebrate_minor) {
            audioPlayer.play(config.audio.coach_audio.celebrate_minor);
        } else if (newState.state === "correct" && config?.audio.coach_audio.celebrate_strong) {
            audioPlayer.play(config.audio.coach_audio.celebrate_strong);
        }

        setSpellingState(newState);

        if (newState.state === "correct") {
          setTimeout(() => {
            onComplete(combinedStrokes.current, newState.accuracy);
          }, 1500);
        }

      } catch (err) {
        console.error("Failed to validate attempt", err);
      }
    },
    onCoachingEvent: (_eventName: string) => {
      // Could wire to coachingEngine here if we build a proper audioMetadata mapping
    }
  });

  const activeStroke = activeLetterData?.strokes?.find(
    (s: any) => s.id === guidance.currentStrokeId
  );
  const activeStrokePath = activeStroke?.path ?? null;
  const startPoint: [number, number] | undefined = activeStroke?.start_point ?? undefined;

  const handleListenWord = () => {
    if (config?.audio.pronunciations.word) {
      audioPlayer.play(config.audio.pronunciations.word);
    }
  };

  const handleListenLetter = () => {
    if (config?.audio.pronunciations.letters[spellingState.next_expected || ""]) {
      audioPlayer.play(config.audio.pronunciations.letters[spellingState.next_expected || ""]);
    }
  };

  if (!config) {
    return <div className="text-center py-16 animate-pulse text-gray-400">Loading spelling curriculum...</div>;
  }

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Target Word Display */}
      <div className="text-center w-full relative">
        <div className="flex justify-center items-center gap-4 mb-2">
            <p className="text-xs uppercase tracking-widest text-gray-400 font-semibold">
            Spell this word
            </p>
            <button onClick={handleListenWord} className="text-xl w-8 h-8 rounded-full bg-indigo-50 text-indigo-600 hover:bg-indigo-100 flex items-center justify-center transition-colors">
                🔊
            </button>
        </div>
        
        <div className="flex justify-center gap-2 text-5xl font-black">
          {targetItem.toUpperCase().split("").map((char, idx) => {
            const isCompleted = idx < spellingState.progress.length;
            const isActive = idx === spellingState.progress.length;
            
            return (
              <span 
                key={idx} 
                className={`
                  transition-colors duration-300
                  ${isCompleted ? "text-green-500" : isActive ? "text-indigo-600 border-b-4 border-indigo-600 pb-1" : "text-gray-200"}
                `}
              >
                {char}
              </span>
            );
          })}
        </div>
      </div>

      {/* Trace Area */}
      {spellingState.state !== "correct" && (
        <div className="relative flex flex-col items-center gap-4">
          {config.assist_profile.show_ghost_word && (
            <div className="flex items-center gap-2">
                <span className="text-gray-400 text-sm">Now tracing:</span>
                <span className="font-bold text-xl text-indigo-600">{spellingState.next_expected}</span>
                <button onClick={handleListenLetter} className="text-sm w-6 h-6 rounded-full bg-indigo-50 text-indigo-600 hover:bg-indigo-100 flex items-center justify-center transition-colors">
                    🔊
                </button>
            </div>
          )}
          
          <div className="relative">
            {loading ? (
                <div className="w-[320px] h-[320px] bg-gray-50 border border-gray-100 rounded-2xl flex items-center justify-center">
                    <span className="animate-pulse text-gray-400">Loading letter...</span>
                </div>
            ) : (
                <PracticeCanvas
                    key={`${spellingState.next_expected}-${spellingState.progress.length}`}
                    onStrokeEnd={handleStrokeComplete}
                    onStrokesChange={(s) => { allStrokes.current = s; }}
                    svgGuidePath={activeLetterData?.svg_path}
                    activeStrokePath={activeStrokePath}
                    startPoint={startPoint}
                    completedStrokes={guidance.completedStrokes}
                    tracePercent={guidance.tracePercent}
                    profileType={profileType}
                    // @ts-ignore
                    disabled={guidance.isSubmitting || spellingState.state === "correct"}
                    width={width}
                    height={height}
                />
            )}
          </div>

          <FeedbackPanel
            message={guidance.feedbackMessage}
            feedbackType={guidance.feedbackType}
            profileType={profileType}
            visible={true}
          />
        </div>
      )}

      {spellingState.state === "correct" && (
        <div className="py-12 text-center animate-bounce">
            <span className="text-6xl mb-4 block">🎉</span>
            <p className="text-2xl font-bold text-green-600">You spelled {targetItem}!</p>
        </div>
      )}

      <div className="flex gap-3 w-full max-w-xs mt-4">
        <button
          onClick={onCancel}
          className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
      </div>
    </div>
  );
}
