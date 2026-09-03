/**
 * src/pages/FreeWritingStudio.tsx
 *
 * The new core identity of AksharabyasaAI.
 * Three acts: Goal setting → Free Writing → Quality Report
 *
 * Product philosophy:
 *   Write freely → Analyze writing behavior → Guide improvement
 */
import { useRef, useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import StudioCanvas, { type Stroke, captureThumbnailFromRef } from "../components/studio/StudioCanvas";
import WritingQualityPanel from "../components/studio/WritingQualityPanel";
import SoftGoalPicker from "../components/studio/SoftGoalPicker";
import { studioApi, type WritingQualityReport, type SessionIntent, type SoftGoal } from "../api/studio";

type PageState = "goal_setting" | "writing" | "analyzing" | "results";

const SESSION_INTENT: SessionIntent = "practice";  // default; could be set by intent picker

export default function FreeWritingStudio() {
  const navigate = useNavigate();
  const { profileType } = useAuth();

  const [pageState, setPageState]     = useState<PageState>("goal_setting");
  const [softGoal, setSoftGoal]       = useState<SoftGoal | null>(null);
  const [strokes, setStrokes]         = useState<Stroke[]>([]);
  const [sessionId, setSessionId]     = useState<string | null>(null);
  const [report, setReport]           = useState<WritingQualityReport | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const canvasRef      = useRef<HTMLCanvasElement>(null);
  const startTimeRef   = useRef<number>(Date.now());
  const autoSaveRef    = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Timer ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (pageState !== "writing") return;
    const interval = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [pageState]);

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  // ── Start session ──────────────────────────────────────────────────────────
  const handleStartWriting = useCallback(async () => {
    try {
      const res = await studioApi.start({
        session_intent: SESSION_INTENT,
        soft_goal: softGoal ?? undefined,
        canvas_width: 480,
        canvas_height: 380,
      });
      setSessionId(res.data.session_id);
      startTimeRef.current = Date.now();
      setPageState("writing");

      // Auto-save every 15s
      autoSaveRef.current = setInterval(async () => {
        if (strokes.length > 0 && res.data.session_id) {
          await studioApi.save(res.data.session_id, strokes).catch(() => {});
        }
      }, 15000);
    } catch {
      setError("Couldn't start session. Check your connection.");
    }
  }, [softGoal, strokes]);

  // Cleanup autosave
  useEffect(() => {
    return () => { if (autoSaveRef.current) clearInterval(autoSaveRef.current); };
  }, []);

  // ── Complete session ───────────────────────────────────────────────────────
  const handleDone = useCallback(async () => {
    if (!sessionId || strokes.length === 0) {
      setError("Draw something first!");
      return;
    }
    if (autoSaveRef.current) { clearInterval(autoSaveRef.current); autoSaveRef.current = null; }

    setPageState("analyzing");
    setError(null);

    // Addition 3: capture canvas thumbnail
    const thumbnail = captureThumbnailFromRef(canvasRef) ?? undefined;

    try {
      const durationSeconds = Math.floor((Date.now() - startTimeRef.current) / 1000);
      const res = await studioApi.complete(sessionId, {
        strokes: strokes.map(s => ({ points: s.points, startTime: s.startTime })),
        duration_seconds: durationSeconds,
        thumbnail_base64: thumbnail,
      });
      setReport(res.data.report);
      setPageState("results");
    } catch {
      setError("Analysis failed. Please try again.");
      setPageState("writing");
    }
  }, [sessionId, strokes]);

  // ── Profile-aware copy ─────────────────────────────────────────────────────
  const heroTitle =
    profileType === "early_learner" ? "Let's Draw! 🎨"
    : profileType === "child"       ? "Free Writing Studio ✍️"
    :                                  "Free Writing Studio";

  const heroSubtitle =
    profileType === "early_learner" ? "Draw anything you like — let's see what you make!"
    : profileType === "child"       ? "Write anything. No rules, no grades. Just your writing."
    :                                  "Write freely. We'll analyze your handwriting quality — not correctness.";

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#F0F2F5] flex flex-col">

      {/* Nav */}
      <header className="flex items-center justify-between px-5 py-4 bg-white/80 backdrop-blur border-b border-gray-100">
        <button
          onClick={() => navigate("/dashboard")}
          className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          ← Back
        </button>
        <span className="text-sm font-semibold text-gray-700">Writing Studio</span>
        {pageState === "writing" && (
          <span className="text-xs font-mono text-indigo-400 bg-indigo-50 px-2 py-0.5 rounded-full">
            {formatTime(elapsedSeconds)}
          </span>
        )}
        {pageState !== "writing" && <div className="w-16" />}
      </header>

      <main className="flex-1 flex flex-col items-center justify-start px-4 py-8 gap-8 max-w-xl mx-auto w-full">

        {/* ── ACT 1: Goal Setting ────────────────────────────────────────── */}
        {pageState === "goal_setting" && (
          <div className="w-full space-y-8 animate-in fade-in duration-300">
            {/* Hero */}
            <div className="text-center space-y-2">
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">{heroTitle}</h1>
              <p className="text-sm text-gray-500 max-w-xs mx-auto">{heroSubtitle}</p>
            </div>

            {/* Soft Goal Picker — Addition 4 */}
            <SoftGoalPicker
              selectedGoal={softGoal}
              onSelect={setSoftGoal}
              profileType={profileType ?? "child"}
            />

            {/* CTA */}
            <div className="space-y-3">
              <button
                onClick={handleStartWriting}
                className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-semibold rounded-2xl transition-all duration-200 shadow-md hover:shadow-lg text-base"
              >
                {profileType === "early_learner" ? "Let's Go! 🚀" : "Open the Canvas →"}
              </button>
              {softGoal === null && (
                <p className="text-center text-xs text-gray-400">
                  No goal needed — you can just write freely
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── ACT 2: Writing ─────────────────────────────────────────────── */}
        {pageState === "writing" && (
          <div className="w-full space-y-6 animate-in fade-in duration-300">
            {softGoal && (
              <div className="text-center">
                <span className="text-xs bg-indigo-50 text-indigo-500 font-medium px-3 py-1 rounded-full border border-indigo-100">
                  Focus: {softGoal.replace("_", " ")}
                </span>
              </div>
            )}

            <StudioCanvas
              profileType={profileType ?? "child"}
              onStrokesChange={setStrokes}
              width={480}
              height={380}
            />

            {error && (
              <p className="text-center text-xs text-red-500">{error}</p>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => navigate("/dashboard")}
                className="flex-1 py-3 border border-gray-200 text-sm text-gray-500 rounded-xl hover:bg-gray-50 transition-colors"
              >
                Save & Exit
              </button>
              <button
                onClick={handleDone}
                disabled={strokes.length === 0}
                className="flex-2 flex-grow py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-200 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl transition-all duration-200 shadow-sm"
              >
                {profileType === "early_learner" ? "See my writing! ✨" : "Done — Analyze →"}
              </button>
            </div>
          </div>
        )}

        {/* ── Analyzing ──────────────────────────────────────────────────── */}
        {pageState === "analyzing" && (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <div className="text-4xl animate-bounce">✍️</div>
            <p className="text-sm text-gray-500 font-medium">
              {profileType === "early_learner"
                ? "Looking at your beautiful drawing…"
                : "Analyzing your handwriting quality…"}
            </p>
            <div className="flex gap-1">
              {[0, 1, 2].map(i => (
                <div
                  key={i}
                  className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {/* ── ACT 3: Results ─────────────────────────────────────────────── */}
        {pageState === "results" && report && (
          <div className="w-full space-y-6 animate-in fade-in duration-500">
            {/* Result header */}
            <div className="text-center space-y-1">
              <h2 className="text-xl font-bold text-gray-900">
                {profileType === "early_learner" ? "Here's your writing! 🌟"
                 : profileType === "child"       ? "Your Writing Report"
                 :                                  "Session Complete"}
              </h2>
              <p className="text-xs text-gray-400">
                {elapsedSeconds > 0 && `${formatTime(elapsedSeconds)} of writing`}
                {strokes.length > 0 && ` · ${strokes.length} strokes`}
              </p>
            </div>

            <WritingQualityPanel report={report} profileType={profileType ?? "child"} />

            {/* Journey callout */}
            <div className="text-center py-4 px-5 bg-indigo-50 rounded-2xl border border-indigo-100 space-y-1">
              <p className="text-sm text-indigo-700 font-medium">
                {profileType === "early_learner"
                  ? "Your drawing has been saved to your journey! 🌈"
                  : "Added to your writing journey 🌱"}
              </p>
              <p className="text-xs text-indigo-400">
                Your handwriting quality is being tracked over time
              </p>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => navigate("/insights")}
                className="flex-1 py-3 border border-gray-200 text-sm text-gray-600 rounded-xl hover:bg-gray-50 transition-colors"
              >
                View Journey →
              </button>
              <button
                onClick={() => {
                  setPageState("goal_setting");
                  setStrokes([]);
                  setReport(null);
                  setSessionId(null);
                  setElapsedSeconds(0);
                  setSoftGoal(null);
                }}
                className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl transition-colors"
              >
                Write Again ✍️
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
