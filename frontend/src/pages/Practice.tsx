/**
 * Practice.tsx — Session Orchestrator
 *
 * Reads URL params to know which module + difficulty to load.
 * Manages full session lifecycle:
 *   1. POST /sessions/start   → get session_id
 *   2. Load correct module adapter
 *   3. Auto-save strokes every 10s
 *   4. POST /sessions/{id}/complete → show RewardBanner
 *   5. refreshProfile() → sync XP/level into context
 *   6. Navigate back to dashboard
 *
 * Practice.tsx ONLY orchestrates — zero module-specific logic here.
 * Each module adapter (Alphabet, Word, FreeDraw) handles its own rendering.
 */
import { useEffect, useState, useCallback, useRef } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { sessionsApi, type StrokeData, type PracticeSession } from "../api/sessions";
import AlphabetModule from "../components/modules/AlphabetModule";
import WordModule from "../components/modules/WordModule";
import FreeDrawModule from "../components/modules/FreeDrawModule";
import RewardBanner from "../components/shared/RewardBanner";
import type { ProfileType } from "../utils/ageUtils";
import { recommendationsApi } from "../api/recommendations";
import { audioPlayer } from "../utils/audioPlayer";
import { getResponsiveCanvasSize } from "../constants/ui";

type PageState = "loading" | "practicing" | "submitting" | "reward" | "error";

export default function Practice() {
  const [searchParams] = useSearchParams();
  const navigate       = useNavigate();
  const { profileType, refreshProfile } = useAuth();

  const moduleType  = searchParams.get("module") ?? "alphabet_practice";
  const manualItem  = searchParams.get("item");
  const usePlan     = searchParams.get("use_plan") === "true";
  // difficulty will be fetched adaptively unless overridden via URL
  const forcedDifficulty = searchParams.get("difficulty");

  const [pageState,    setPageState]    = useState<PageState>("loading");
  const [session,      setSession]      = useState<PracticeSession | null>(null);
  const [targetItem,   setTargetItem]   = useState<string>("");
  const [difficulty,   setDifficulty]   = useState<string>(forcedDifficulty ?? "beginner");
  const [reward,       setReward]       = useState<any>(null);
  const [errorMsg,     setErrorMsg]     = useState("");
  const [audioMeta,    setAudioMeta]    = useState<any>(null);
  const sessionStart   = useRef<number>(Date.now());
  const autoSaveTimer  = useRef<ReturnType<typeof setInterval> | null>(null);
  const latestStrokes  = useRef<StrokeData[]>([]);

  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const canvasDim = getResponsiveCanvasSize(moduleType, windowWidth);

  // ── Init: fetch next item + start session ─────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      try {
        // 0. If usePlan, fetch session plan
        let resolvedDifficulty = forcedDifficulty;
        let item = manualItem ?? "";
        
        if (usePlan) {
          try {
            const planRes = await recommendationsApi.session(moduleType);
            resolvedDifficulty = planRes.data.difficulty;
            setDifficulty(resolvedDifficulty);
            if (planRes.data.items && planRes.data.items.length > 0) {
              item = planRes.data.items[0];
            }
            if ((planRes.data as any).audio_metadata) {
              setAudioMeta((planRes.data as any).audio_metadata);
              // Preload all audio
              const m = (planRes.data as any).audio_metadata;
              const urls = [
                ...Object.values(m.item_audio || {}),
                ...Object.values(m.coach_audio || {}),
                ...Object.values(m.celebration_audio || {})
              ].filter(Boolean) as string[];
              audioPlayer.preload(urls);
            }
          } catch {
            // fallback
          }
        }

        // 1. Fetch adaptive difficulty if still missing
        if (!resolvedDifficulty) {
          try {
            const diffRes = await sessionsApi.recommendedDifficulty(moduleType);
            resolvedDifficulty = diffRes.data.difficulty;
            setDifficulty(resolvedDifficulty || "beginner");
          } catch {
            resolvedDifficulty = "beginner";
          }
        }

        // 2. Determine target item if still missing (skip for free_draw)
        if (!item && moduleType !== "free_draw") {
          const res = await sessionsApi.nextItem(moduleType, resolvedDifficulty!);
          item = res.data.item ?? "";
        }
        if (cancelled) return;
        setTargetItem(item);

        // 2. Start the session
        const startRes = await sessionsApi.start({
          module_type: moduleType,
          target_item: item || null,
          difficulty: resolvedDifficulty!,
        });
        if (cancelled) return;
        setSession(startRes.data);
        sessionStart.current = Date.now();
        setPageState("practicing");
      } catch (err: any) {
        if (!cancelled) {
          setErrorMsg(err.response?.data?.detail ?? "Failed to start session.");
          setPageState("error");
        }
      }
    };

    init();
    return () => { cancelled = true; };
  }, [moduleType, difficulty, manualItem]);

  // ── Auto-save strokes every 10 seconds ────────────────────────────────────
  useEffect(() => {
    if (!session || pageState !== "practicing") return;

    autoSaveTimer.current = setInterval(() => {
      if (latestStrokes.current.length > 0) {
        sessionsApi.saveStrokes(session.id, latestStrokes.current).catch(() => {});
      }
    }, 10_000);

    return () => {
      if (autoSaveTimer.current) clearInterval(autoSaveTimer.current);
    };
  }, [session, pageState]);

  // ── Module completion handler ─────────────────────────────────────────────
  const handleComplete = useCallback(
    async (strokes: StrokeData[], accuracy: number) => {
      if (!session) return;
      if (autoSaveTimer.current) clearInterval(autoSaveTimer.current);
      setPageState("submitting");

      const durationSeconds = Math.round((Date.now() - sessionStart.current) / 1000);

      try {
        const res = await sessionsApi.complete(session.id, {
          accuracy_score:  accuracy,
          duration_seconds: durationSeconds,
          stroke_data:     strokes,
          total_strokes:   strokes.length,
          total_points:    strokes.reduce((n, s) => n + s.points.length, 0),
        });
        
        // Fire 'completed' feedback if this was a planned session
        if (usePlan && targetItem) {
          recommendationsApi.feedback({
            item: targetItem,
            action: "completed",
            outcome_accuracy: accuracy,
            module_type: moduleType,
          }).catch(() => {});
        }

        setReward(res.data);
        setPageState("reward");
        await refreshProfile();   // sync XP/level into AuthContext
      } catch (err: any) {
        setErrorMsg(err.response?.data?.detail ?? "Failed to submit session.");
        setPageState("error");
      }
    },
    [session, refreshProfile],
  );

  // ── Abandon on back navigation ────────────────────────────────────────────
  const handleCancel = useCallback(async () => {
    if (session && pageState === "practicing") {
      await sessionsApi
        .abandon(session.id, latestStrokes.current)
        .catch(() => {});
    }
    navigate("/dashboard");
  }, [session, pageState, navigate]);

  // ── Track latest strokes for auto-save ───────────────────────────────────


  return (
    <div className="min-h-screen bg-background relative overflow-hidden flex flex-col items-center justify-center transition-colors duration-300">
      {/* Floating Exit Button */}
      <div className="absolute top-8 right-8 z-50">
        <button
          onClick={handleCancel}
          className="w-10 h-10 rounded-full bg-surface shadow-sm hover:shadow-md text-textTertiary hover:text-textPrimary flex items-center justify-center transition-all duration-250 ease-out hover:-translate-y-0.5"
        >
          ✕
        </button>
      </div>

      {/* Focus Mode Ambient Blurs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] bg-indigo-500/10 dark:bg-indigo-600/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[45vw] h-[45vw] bg-purple-500/10 dark:bg-purple-600/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Content Focus Container */}
      <main className="w-full max-w-2xl mx-auto px-6 py-10 z-10 flex flex-col items-center justify-center bg-surface/50 dark:bg-slate-900/40 backdrop-blur-md border border-border/40 shadow-lg rounded-[32px] transition-all duration-300">

        {/* Loading */}
        {pageState === "loading" && (
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <div className="text-4xl animate-pulse">📖</div>
            <p className="text-gray-400 text-sm">Preparing your session…</p>
          </div>
        )}

        {/* Submitting */}
        {pageState === "submitting" && (
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <div className="text-4xl animate-spin">⭐</div>
            <p className="text-gray-500 text-sm">Calculating your score…</p>
          </div>
        )}

        {/* Error */}
        {pageState === "error" && (
          <div className="text-center space-y-4 py-16">
            <p className="text-2xl">⚠️</p>
            <p className="text-red-600 font-medium">{errorMsg}</p>
            <button
              onClick={() => navigate("/dashboard")}
              className="bg-indigo-600 text-white px-6 py-2 rounded-xl text-sm font-semibold"
            >
              Back to Dashboard
            </button>
          </div>
        )}

        {/* Module adapter */}
        {pageState === "practicing" && (
          <>
            {moduleType === "alphabet_practice" && session && (
              <AlphabetModule
                sessionId={session.id}
                targetItem={targetItem}
                profileType={(profileType ?? "adult") as ProfileType}
                audioMetadata={audioMeta}
                onComplete={handleComplete}
                onCancel={handleCancel}
                width={canvasDim.width}
                height={canvasDim.height}
              />
            )}
            {moduleType === "word_practice" && session && (
              <WordModule
                sessionId={session.id}
                targetItem={targetItem}
                difficulty={difficulty}
                profileType={(profileType ?? "adult") as ProfileType}
                onComplete={handleComplete}
                onCancel={handleCancel}
                width={canvasDim.width}
                height={canvasDim.height}
              />
            )}
            {moduleType === "free_draw" && (
              <FreeDrawModule
                profileType={(profileType ?? "adult") as ProfileType}
                onComplete={handleComplete}
                onCancel={handleCancel}
                width={canvasDim.width}
                height={canvasDim.height}
              />
            )}
            {!["alphabet_practice", "word_practice", "free_draw"].includes(moduleType) && (
              <div className="text-center py-16 text-gray-400">
                <p className="text-2xl mb-3">🚧</p>
                <p className="font-medium">This module is coming in Phase 3!</p>
                <button onClick={handleCancel} className="mt-4 text-indigo-600 text-sm hover:underline">
                  Go back
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {/* Reward overlay */}
      {pageState === "reward" && reward && (
        <RewardBanner
          xpEarned={reward.xp_earned}
          totalXp={reward.total_xp}
          newLevel={reward.new_level}
          levelUp={reward.level_up}
          newStreak={reward.new_streak}
          profileType={(profileType ?? "adult") as ProfileType}
          onDismiss={() => navigate("/dashboard")}
        />
      )}
    </div>
  );
}
