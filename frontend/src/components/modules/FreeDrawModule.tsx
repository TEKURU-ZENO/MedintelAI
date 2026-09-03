/**
 * FreeDrawModule.tsx — Free Draw module adapter
 * No guidance, no target. Just open canvas. Max fun for early learners.
 */
import { useState } from "react";
import PracticeCanvas from "../shared/PracticeCanvas";
import FeedbackPanel from "../shared/FeedbackPanel";
import { type StrokeData } from "../../api/sessions";
import type { ProfileType } from "../../utils/ageUtils";

interface Props {
  profileType: ProfileType;
  onComplete: (strokes: StrokeData[], accuracy: number) => void;
  onCancel: () => void;
  width?: number;
  height?: number;
}

export default function FreeDrawModule({ profileType, onComplete, onCancel, width = 600, height = 500 }: Props) {
  const [strokes, setStrokes] = useState<StrokeData[]>([]);

  const message =
    profileType === "early_learner" ? "Draw anything you like! 🎨"
    : profileType === "child"       ? "Free canvas — draw whatever you want!"
    :                                  "Open practice — no constraints.";

  const handleFinish = () => {
    // Free draw: accuracy is always 1.0 (any drawing is valid)
    onComplete(strokes, strokes.length > 0 ? 1.0 : 0.0);
  };

  return (
    <div className="flex flex-col items-center gap-6">
      <FeedbackPanel
        message={message}
        feedbackType="idle"
        profileType={profileType}
        visible={true}
      />

      <PracticeCanvas
        onStrokesChange={setStrokes}
        profileType={profileType}
        width={width}
        height={height}
      />

      <p className="text-xs text-gray-400">
        {strokes.length} stroke{strokes.length !== 1 ? "s" : ""} drawn
      </p>

      <div className="flex gap-3 w-full max-w-xs">
        <button
          onClick={onCancel}
          className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          onClick={handleFinish}
          disabled={strokes.length === 0}
          className="flex-1 py-2.5 bg-green-600 hover:bg-green-700 disabled:bg-green-200 text-white rounded-xl text-sm font-semibold transition-colors"
        >
          Finish 🎨
        </button>
      </div>
    </div>
  );
}
